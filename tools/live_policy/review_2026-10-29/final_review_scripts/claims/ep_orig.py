from graph_planning import GraphPlanner
from mid_planning import MidPlanner
from llm_completion import LLMManager
from calculate_uncertainty import UncertaintyCalculator
import rospy
import habitat_sim
from cv_bridge import CvBridge
import tf2_ros
from sensor_msgs.msg import Image, CameraInfo
from nav_msgs.msg import Path
import numpy as np
import cv2
from geometry_msgs.msg import TransformStamped, PoseStamped
import math
import quaternion
import os
from pynput import keyboard
from dataclasses import dataclass
import time
import json
import shutil
import signal
import time
from scipy.spatial.transform import Rotation as R
import yaml
from typing import List, Optional

@dataclass
class CameraConfig:
    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int
    near_clip: float
    max_range: float

@dataclass
class PipelineConfig:
    SEED: int
    SCENE_DATASET_CONFIG: str
    SCENE_ID: str
    SCENE_NUMBER: int
    AGENT_HEIGHT: float
    RGB_TOPIC: str
    DEPTH_TOPIC: str
    MID_PATH_TOPIC: str
    TARGET_POSE_TOPIC: str
    OCCUPANCY_PC_TOPIC: str
    SCENE_GRAPH_COUNT: int
    ESDF_THRESHOLD: float
    WORLD_FRAME: str
    HABITAT_FRAME: str
    AGENT_FRAME: str
    BASE_DIRECTORY: str
    WORKING_DIRECTORY: Optional[str]
    MAPPING_DIRECTORY: str
    DSG_SOURCE_PATHS: Optional[List[str]]
    FILE_WAIT_TIMEOUT_S: int
    MIN_DSG_FILE_SIZE_BYTES: int
    GOOGLE_API_KEY: Optional[str]
    LLM_MODEL_NAME: str
    LLM_COMPLETION_PROMPT: str
    LLM_ENSEMBLE_COUNT: int
    LLM_REFINE_TIMES: int
    MAX_PARALLEL_WORKERS: int
    TURN_STEP_DEG: float
    MOVE_STEP_M: float
    DISTANCE_THRESHOLD_M: float
    TURN_THRESHOLD_RAD: float
    INFLATION_RADIUS: float
    MINIMUM_NAVIGATION_DURATION: float
    PATH_LENGTH_FACTOR: int
    UNKNOWN_CELL_THRESHOLD: float
    UNCERTAINTY_SAMPLES: int
    UNCERTAINTY_PERTURBATIONS: int
    UNCERTAINTY_NOISE_LOW: float
    UNCERTAINTY_NOISE_HIGH: float
    MINIMUM_DISTANCE_DIFFERENCE: float
    UNCERTAINTY_ROOM_WEIGHT: float
    CAMERA_CONFIG: CameraConfig
    MOVE_COST_LAMBDA: float

# -----------------------------------------------------------------------------
# UTILITY FUNCTIONS (Transformations, etc.)
# -----------------------------------------------------------------------------
def get_around_x_matrix(angle):
    """Returns a 4x4 rotation matrix around the X-axis."""
    return np.array([
        [1, 0, 0, 0],
        [0, np.cos(angle), -np.sin(angle), 0],
        [0, np.sin(angle), np.cos(angle), 0],
        [0, 0, 0, 1]
    ])

def get_around_z_matrix(angle):
    """Returns a 4x4 rotation matrix around the Z-axis."""
    # Axis is the Z-axis: [0, 0, 1]
    rot_q = np.array([
        [np.cos(angle), -np.sin(angle), 0, 0],
        [np.sin(angle), np.cos(angle), 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])
    return rot_q

def transform_habitat_pose_to_z_up(agent_s):
    """
    Transforms a Habitat agent_state pose (Y-up) into a Z-up coordinate system.
    This is used to align the Habitat world with a standard ROS world frame.
    """
    # Rotation matrix to switch from Y-up to Z-up
    rot_q = get_around_x_matrix(-np.pi/2)
    # Rotation matrix to make walls aligned with horizontal and vertical axes
    rot_q_2 = get_around_z_matrix(np.pi/4)

    # Create a homogeneous transformation matrix from the agent state
    homogeneous_matrix = np.eye(4)
    homogeneous_matrix[:3, :3] = quaternion.as_rotation_matrix(agent_s.rotation)
    homogeneous_matrix[:3, 3] = agent_s.position

    # Apply the coordinate system rotation
    new_matrix = homogeneous_matrix @ rot_q @ rot_q_2

    # Extract the new position and orientation
    new_position = new_matrix[:3, 3]
    new_orientation = quaternion.from_rotation_matrix(new_matrix[:3, :3])

    return new_position, new_orientation

def transform_habitat_pose_to_z_front(agent_s):
    """
    Transforms a Habitat agent_state pose (Z-back) into a Z-forward coordinate system.
    Required by mapping pipeline.
    """
    # Rotation matrix to switch from Y-up to Z-front
    rot_q = get_around_x_matrix(-np.pi)

    # Create a homogeneous transformation matrix from the agent state
    homogeneous_matrix = np.eye(4)
    homogeneous_matrix[:3, :3] = quaternion.as_rotation_matrix(agent_s.rotation)
    homogeneous_matrix[:3, 3] = agent_s.position

    # Apply the coordinate system rotation
    new_matrix = homogeneous_matrix @ rot_q

    # Extract the new position and orientation
    new_position = new_matrix[:3, 3]
    new_orientation = quaternion.from_rotation_matrix(new_matrix[:3, :3])

    return new_position, new_orientation


# -----------------------------------------------------------------------------
# Main Pipeline
# -----------------------------------------------------------------------------
class ExplorationPipeline:
    """Manages the entire exploration workflow."""

    def __init__(self, config):
        self.config = config
        self.config.DSG_SOURCE_PATHS = [os.path.join(self.config.MAPPING_DIRECTORY, f'graph{i}_dsg.json') for i in range(self.config.SCENE_GRAPH_COUNT)]
        self.state = "IDLE"  # States: IDLE, SCANNING, PLANNING, WAITING_FOR_MID_PATH, NAVIGATING
        self.stop_requested = False

        # --- ROS Initialization ---
        rospy.init_node('exploration_pipeline', anonymous=True)
        self.bridge = CvBridge()
        self.tf_broadcaster = tf2_ros.TransformBroadcaster()
        self.rgb_pub = rospy.Publisher(self.config.RGB_TOPIC, Image, queue_size=10)
        self.depth_pub = rospy.Publisher(self.config.DEPTH_TOPIC, Image, queue_size=10)
        self.rgb_info_pub   = rospy.Publisher('/dominic/forward/color/camera_info', CameraInfo, queue_size=10)
        self.depth_info_pub = rospy.Publisher('/dominic/forward/depth/camera_info', CameraInfo, queue_size=10)
        self.target_pose_pub = rospy.Publisher(self.config.TARGET_POSE_TOPIC, PoseStamped, queue_size=1, latch=True)
        self.mid_path_sub = rospy.Subscriber(
            self.config.MID_PATH_TOPIC, Path, self.mid_path_callback
        )
        self.rate = rospy.Rate(10)
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        # --- Pipeline Components ---
        self.llm_manager = LLMManager(config)
        self.uncertainty_calc = UncertaintyCalculator(config)
        self.global_planner = GraphPlanner(config)
        self.mid_planner = MidPlanner(config, self.tf_buffer)
        self.rosbag_process = None
        self.skip_dsg_wait = False

        # --- State Variables ---
        self.local_path = None
        self.current_target_index = -1
        self.stage = 0
        self.history_position = []
        self.previous_dsg_sizes = {}
        self.navigation_start_time = None

        # Path length saving
        self.total_path_length = 0
        self.previous_total_path_length = 0

        # Navigation time saving
        self.total_navigation_time = 0.0
        self.previous_total_navigation_time = 0.0

        # Exact path saving (both in world frame and habitat frame)
        self.current_stage_path_habitat = []
        self.current_stage_path_world = []

        # --- Habitat Simulation Setup ---
        self.sim = self._initialize_simulator()
        self.agent = self.sim.initialize_agent(0)
        self.agent_initial_state = self.agent.get_state()
        # Fix: We want the world frame to have 0 height
        self.agent_initial_state.position[1] = 0
        initial_state = self.agent.get_state()
        if self.config.SCENE_NUMBER == 871:
            # 00871
            initial_state.position = np.array([-5.5, self.config.AGENT_HEIGHT, -3.0])
        elif self.config.SCENE_NUMBER == 853:
            # 00853
            initial_state.position = np.array([-0.5, self.config.AGENT_HEIGHT, 4.5])
        elif self.config.SCENE_NUMBER == 573:
            # 00573
            initial_state.position = np.array([0.1, self.config.AGENT_HEIGHT, 1.5])
        elif self.config.SCENE_NUMBER == 69:
            # 00069
            initial_state.position = np.array([0.6, self.config.AGENT_HEIGHT, 1.5])
        else:
            rospy.logwarn("Unknown scene number. Using default initial position.")
        self.agent.set_state(initial_state)

        self.rng = np.random.default_rng(self.config.SEED)

        # Delay about 0.5 seconds to ensure we don't hit tf error when we start to navigate
        self.pending_mid_path_for_navigation = None
        self.navigation_ready_time = None


    def publish_habitat_to_world_tf(self, timestamp):
        """
        Publishes the habitat-to-world transform.
        """
        pos, orient = transform_habitat_pose_to_z_up(self.agent_initial_state)
        
        t = TransformStamped()
        t.header.stamp = timestamp
        t.header.frame_id = self.config.HABITAT_FRAME
        t.child_frame_id = self.config.WORLD_FRAME
        t.transform.translation.x = pos[0]
        t.transform.translation.y = pos[1]
        t.transform.translation.z = pos[2]
        t.transform.rotation.x = orient.x
        t.transform.rotation.y = orient.y
        t.transform.rotation.z = orient.z
        t.transform.rotation.w = orient.w
        
        self.tf_broadcaster.sendTransform(t)

    def publish_agent_tf(self, timestamp):
        """Publishes the agent's dynamic pose within the Habitat frame."""
        agent_state = self.agent.get_state()
        pos, orient = transform_habitat_pose_to_z_front(agent_state)
        t = TransformStamped()
        t.header.stamp = timestamp
        t.header.frame_id = self.config.HABITAT_FRAME
        t.child_frame_id = self.config.AGENT_FRAME
        t.transform.translation.x = pos[0]
        t.transform.translation.y = pos[1]
        t.transform.translation.z = pos[2]
        t.transform.rotation.w = orient.w
        t.transform.rotation.x = orient.x
        t.transform.rotation.y = orient.y
        t.transform.rotation.z = orient.z
        self.tf_broadcaster.sendTransform(t)

    def _initialize_simulator(self):
        """Sets up the Habitat simulator configuration."""
        sim_cfg = habitat_sim.SimulatorConfiguration()
        sim_cfg.scene_dataset_config_file = self.config.SCENE_DATASET_CONFIG
        sim_cfg.scene_id = self.config.SCENE_ID
        sim_cfg.scene_light_setup = habitat_sim.gfx.DEFAULT_LIGHTING_KEY

        # Sensor specifications
        rgb_sensor_spec = habitat_sim.CameraSensorSpec()
        rgb_sensor_spec.uuid = "color_sensor"
        rgb_sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
        rgb_sensor_spec.resolution = [480, 640]
        rgb_sensor_spec.position = [0.0, 0.0, 0.0]

        depth_sensor_spec = habitat_sim.CameraSensorSpec()
        depth_sensor_spec.uuid = "depth_sensor"
        depth_sensor_spec.sensor_type = habitat_sim.SensorType.DEPTH
        depth_sensor_spec.resolution = [480, 640]
        depth_sensor_spec.position = [0.0, 0.0, 0.0]

        agent_cfg = habitat_sim.AgentConfiguration()
        agent_cfg.sensor_specifications = [rgb_sensor_spec, depth_sensor_spec]

        return habitat_sim.Simulator(habitat_sim.Configuration(sim_cfg, [agent_cfg]))
    
    def _build_view_matrix(self, pos, yaw_degrees, world_up):
        """
        Builds a 4x4 view matrix from a yaw angle and fixed -10-degree pitch.
        """
        pitch_radians = -np.pi/18
        yaw_radians = np.radians(yaw_degrees)
        z_axis = np.array([
            np.cos(yaw_radians) * np.cos(pitch_radians),
            np.sin(yaw_radians) * np.cos(pitch_radians),
            np.sin(pitch_radians)
        ])
        z_axis = z_axis / np.linalg.norm(z_axis)
        x_axis = np.cross(z_axis, world_up) # Right = Forward x Up
        x_axis /= np.linalg.norm(x_axis)
        y_axis = np.cross(z_axis, x_axis) # Down = Forward x Right
        y_axis = y_axis / np.linalg.norm(y_axis)

        transformation = np.identity(4)
        transformation[0, :3] = x_axis
        transformation[1, :3] = y_axis
        transformation[2, :3] = z_axis

        t = transformation[:3, :3] @ (-pos)
        transformation[:3, 3] = t

        orientation_matrix = np.linalg.inv(transformation)[:3, :3]
        camera_quat = R.from_matrix(orientation_matrix).as_quat()
        
        return transformation, camera_quat
    
    def _wait_for_and_copy_dsg_files(self):
        """
        Waits for DSG files to be updated by comparing their current size to the
        size recorded in the previous cycle.
        """
        source_paths = self.config.DSG_SOURCE_PATHS
        dest_dir = self.config.WORKING_DIRECTORY
        copied_paths = []

        for src_path in source_paths:
            rospy.loginfo(f"Waiting for updated and stable mapping file: {src_path}")
            previous_size = self.previous_dsg_sizes.get(src_path, -1)

            start_time = time.time()

            while time.time() - start_time < self.config.FILE_WAIT_TIMEOUT_S:
                if not os.path.exists(src_path):
                    time.sleep(1)
                    continue

                current_size = os.path.getsize(src_path)

                # The logic now compares to the size from the previous cycle.
                has_been_updated = (current_size != previous_size)
                is_large_enough = (current_size > self.config.MIN_DSG_FILE_SIZE_BYTES)

                if has_been_updated and is_large_enough:
                    # Wait for 3 seconds to see if the file is still growing (saving needs 2 seconds)
                    time.sleep(3)
                    size_after_wait = os.path.getsize(src_path)

                    if current_size == size_after_wait:
                        # The size is stable. It's safe to copy.
                        dest_path = os.path.join(dest_dir, os.path.basename(src_path))
                        shutil.copy(src_path, dest_path)
                        rospy.loginfo(f"Copied file to {dest_path}")
                        copied_paths.append(dest_path)

                        # Update the dictionary with the new stable size for the next cycle.
                        self.previous_dsg_sizes[src_path] = current_size
                        break

                # If file hasn't been updated or isn't stable, wait and retry.
                time.sleep(2)
            else:
                rospy.logerr(f"Timeout! Did not find an updated and stable file at '{src_path}'.")

        return copied_paths

    def _transform_path_to_habitat(self, path, tf_buffer):
        transformed_path = []
        for point in path:
            raw_pose = PoseStamped()
            raw_pose.header.frame_id = "world"
            raw_pose.header.stamp = rospy.Time(0)
            raw_pose.pose.position.x = point[0]
            raw_pose.pose.position.y = point[1]
            raw_pose.pose.position.z = point[2]

            target_frame = "world_habitat"
            transformed_pose_stamped = None

            try:
                transformed_pose_stamped = tf_buffer.transform(
                    raw_pose,
                    target_frame,
                    timeout=rospy.Duration(1.0)
                )

            except tf2_ros.LookupException:
                rospy.logerr("Transform not found. Waiting for transform...")

            if transformed_pose_stamped is not None:
                position = np.array([
                    transformed_pose_stamped.pose.position.x,
                    transformed_pose_stamped.pose.position.y,
                    transformed_pose_stamped.pose.position.z])
                transformed_path.append(position)

        return transformed_path
    
    def _transform_pose_to_world(self, habitat_pose, tf_buffer):
        raw_pose = PoseStamped()
        raw_pose.header.frame_id = "world_habitat"
        raw_pose.header.stamp = rospy.Time(0)
        raw_pose.pose.position.x = habitat_pose[0]
        raw_pose.pose.position.y = habitat_pose[1]
        raw_pose.pose.position.z = habitat_pose[2]
        raw_pose.pose.orientation.w = 1.0

        target_frame = "world"
        transformed_pose_stamped = None
        world_position = None

        try:
            transformed_pose_stamped = tf_buffer.transform(
                raw_pose,
                target_frame,
                timeout=rospy.Duration(1.0)
            )

        except tf2_ros.LookupException:
            rospy.logerr("Transform not found. Waiting for transform...")
            return None

        if transformed_pose_stamped is not None:
            world_position = np.array([
                transformed_pose_stamped.pose.position.x,
                transformed_pose_stamped.pose.position.y,
                transformed_pose_stamped.pose.position.z
            ])

        return world_position

    def _set_navigation_path_from_world_path(self, world_path_points):
        if not world_path_points:
            self.local_path = None
            self.current_target_index = -1
            return

        # Convert path from world frame to habitat frame
        self.local_path = self._transform_path_to_habitat(world_path_points, self.tf_buffer)

        # Pick a good starting waypoint
        current_pos = self.agent.get_state().position
        min_dist = float('inf')
        closest_index = 0
        for i, waypoint in enumerate(self.local_path):
            delta_pos = waypoint - current_pos
            delta_pos[1] = 0  # ignore height
            dist = np.linalg.norm(delta_pos)
            if dist < min_dist:
                min_dist = dist
                closest_index = i

        # Find first index outside the navigation radius
        target_index = closest_index
        for i in range(closest_index, len(self.local_path)):
            waypoint = self.local_path[i]
            delta_pos = waypoint - current_pos
            delta_pos[1] = 0
            dist = np.linalg.norm(delta_pos)

            if dist > self.config.DISTANCE_THRESHOLD_M:
                target_index = i
                break

        # If everything is within the threshold, it means we already reached the target
        if target_index == closest_index and min_dist < self.config.DISTANCE_THRESHOLD_M:
            target_index = len(self.local_path)

        self.current_target_index = target_index


    def mid_path_callback(self, msg):
        """Receives the mid-level path from MidPlanner and integrates it."""
        if not msg.poses:
            rospy.logwarn("Received empty mid-level path. Ignoring.")
            return

        mid_path_world = []
        for pose in msg.poses:
            point = np.array([
                pose.pose.position.x,
                pose.pose.position.y,
                pose.pose.position.z
            ])
            mid_path_world.append(point)

        if self.state == "WAITING_FOR_MID_PATH":
            self.pending_mid_path_for_navigation = mid_path_world
            self.navigation_ready_time = rospy.get_time() + 0.5

        elif self.state == "NAVIGATING":
            self._set_navigation_path_from_world_path(mid_path_world)

    def make_camera_info_msg(self, width, height, fx, fy, cx, cy, frame_id):
        cam_info = CameraInfo()
        cam_info.width = width
        cam_info.height = height
        cam_info.distortion_model = ""  # or "" if you don't want any model
        cam_info.D = [0.0, 0.0, 0.0, 0.0, 0.0]  # no distortion

        # Intrinsic matrix
        cam_info.K = [
            fx, 0.0, cx,
            0.0, fy, cy,
            0.0, 0.0, 1.0
        ]

        # Rectification matrix (identity)
        cam_info.R = [
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0
        ]

        # Projection matrix (K with zeros in the last column)
        cam_info.P = [
            fx, 0.0, cx, 0.0,
            0.0, fy, cy, 0.0,
            0.0, 0.0, 1.0, 0.0
        ]

        cam_info.header.frame_id = frame_id
        return cam_info


    def publish_sensor_images(self):
        """Gets sensor data from Habitat, converts, and publishes to ROS."""
        observations = self.sim.get_sensor_observations()
        timestamp = rospy.Time.now()

        # Publish RGB image
        rgb_image = cv2.cvtColor(observations['color_sensor'], cv2.COLOR_RGBA2RGB)
        rgb_msg = self.bridge.cv2_to_imgmsg(rgb_image, encoding='rgb8')
        rgb_msg.header.stamp = timestamp
        rgb_msg.header.frame_id = self.config.AGENT_FRAME
        self.rgb_pub.publish(rgb_msg)

        # Publish Depth image
        depth_image = observations['depth_sensor']
        depth_msg = self.bridge.cv2_to_imgmsg(depth_image, encoding='32FC1')
        depth_msg.header.stamp = timestamp
        depth_msg.header.frame_id = self.config.AGENT_FRAME
        self.depth_pub.publish(depth_msg)

        # Publish camera info
        rgb_cam_info = self.make_camera_info_msg(
            width=self.config.CAMERA_CONFIG.width, height=self.config.CAMERA_CONFIG.height,
            fx=self.config.CAMERA_CONFIG.fx, fy=self.config.CAMERA_CONFIG.fy, cx=self.config.CAMERA_CONFIG.cx, cy=self.config.CAMERA_CONFIG.cy,
            frame_id=self.config.AGENT_FRAME
        )

        depth_cam_info = self.make_camera_info_msg(
            width=self.config.CAMERA_CONFIG.width, height=self.config.CAMERA_CONFIG.height,
            fx=self.config.CAMERA_CONFIG.fx, fy=self.config.CAMERA_CONFIG.fy, cx=self.config.CAMERA_CONFIG.cx, cy=self.config.CAMERA_CONFIG.cy,
            frame_id=self.config.AGENT_FRAME
        )

        rgb_cam_info.header.stamp = timestamp
        depth_cam_info.header.stamp = timestamp
        self.rgb_info_pub.publish(rgb_cam_info)
        self.depth_info_pub.publish(depth_cam_info)

    def _agent_turn(self, degrees):
        """Turns the agent by a specified angle."""
        state = self.agent.get_state()
        rot = habitat_sim.utils.common.quat_from_angle_axis(
            math.radians(degrees), np.array([0, 1, 0])
        )
        state.rotation = rot * state.rotation
        self.agent.set_state(state)

    def _agent_forward(self, dist):
        """Moves the agent forward by a specified distance."""
        state = self.agent.get_state()
        forward_vector = quaternion.as_rotation_matrix(state.rotation) @ np.array([0, 0, -1])
        forward_vector[1] = 0
        state.position += forward_vector * dist
        self.agent.set_state(state)

    def _record_agent_position(self):
        """Records the agent's current position in both frames."""
        current_pos_habitat = self.agent.get_state().position
        
        # Avoid recording duplicate points if the agent only turns
        if np.array_equal(self.current_stage_path_habitat[-1], current_pos_habitat):
            return

        current_pos_world = self._transform_pose_to_world(current_pos_habitat, self.tf_buffer)

        self.current_stage_path_habitat.append(current_pos_habitat.tolist())
        self.current_stage_path_world.append(current_pos_world.tolist())

    def start_rosbag_recording(self, stage_num):
        """Starts a rosbag recording process for a specific stage and type."""
        pass
        # if self.rosbag_process:
        #     rospy.logwarn("A rosbag process is already running. Stopping it before starting a new one.")
        #     self.stop_rosbag_recording()

        # working_dir = os.path.join(self.config.BASE_DIRECTORY, str(stage_num))
        # os.makedirs(working_dir, exist_ok=True) # Ensure the directory exists

        # bag_filename = os.path.join(working_dir, f"stage_{stage_num}.bag")
        # rospy.loginfo(f"Starting rosbag recording. Saving to: {bag_filename}")

        # # List of topics to record
        # topics = [
        #     '/clio_visualizer/graph0/dsg_markers',
        #     '/clio_visualizer/graph1/dsg_markers',
        #     '/clio_visualizer/graph0/dsg_mesh',
        #     '/clio_visualizer/graph1/dsg_mesh',
        #     '/clio_visualizer/graph0/khronos_objects/static_objects',
        #     '/clio_visualizer/graph1/khronos_objects/static_objects',
        #     '/semantic_inference/semantic/image_raw/visualization',
        #     '/tf',
        #     '/planned_mid_path',
        #     '/planned_local_path',
        #     '/target_visualization_pose'
        # ]

        # # Construct the command
        # command = ['rosbag', 'record', '-O', bag_filename] + topics

        # # Start the process
        # self.rosbag_process = subprocess.Popen(command)

    def stop_rosbag_recording(self):
        """Stops the currently running rosbag process gracefully."""
        if self.rosbag_process:
            rospy.loginfo(f"Stopping rosbag recording for stage {self.stage}.")
            self.rosbag_process.send_signal(signal.SIGINT)
            self.rosbag_process.wait()
            self.rosbag_process = None
            rospy.loginfo("Rosbag process stopped and file saved.")

    def run_pipeline(self):
        """The main execution loop for the pipeline."""
        while not rospy.is_shutdown() and not self.stop_requested:
            self.config.WORKING_DIRECTORY = os.path.join(self.config.BASE_DIRECTORY, str(self.stage))
            os.makedirs(self.config.WORKING_DIRECTORY, exist_ok=True)
            # Always publish data
            timestamp = rospy.Time.now()
            self.publish_habitat_to_world_tf(timestamp)
            self.publish_agent_tf(timestamp)

            if self.state == "IDLE":
                pass

            elif self.state == "SCANNING":
                self.execute_scanning()

            elif self.state == "PLANNING":
                self.execute_planning()
            
            elif self.state == "WAITING_FOR_MID_PATH":
                self.publish_sensor_images()

                if (
                    self.pending_mid_path_for_navigation is not None
                    and self.navigation_ready_time is not None
                    and rospy.get_time() >= self.navigation_ready_time
                ):
                    self._start_navigation_from_mid_path(self.pending_mid_path_for_navigation)
                    self.pending_mid_path_for_navigation = None
                    self.navigation_ready_time = None

            elif self.state == "NAVIGATING":
                self.publish_sensor_images()
                self.execute_navigation()

            self.rate.sleep()

        rospy.loginfo("Shutdown requested, stopping any active rosbag recording...")
        self.stop_rosbag_recording()
        self.sim.close()
        rospy.loginfo("Pipeline shutdown.")

    def _start_navigation_from_mid_path(self, mid_path_world):
        """Starts navigation from the received mid-level path."""
        if self.state != "WAITING_FOR_MID_PATH":
            return

        # 1. Use the received mid-level path as the navigation path
        self._set_navigation_path_from_world_path(mid_path_world)

        # 2. Start recording path
        self.current_stage_path_habitat = []
        self.current_stage_path_world = []

        start_pos_habitat = self.agent.get_state().position
        start_pos_world = self._transform_pose_to_world(start_pos_habitat, self.tf_buffer)

        self.current_stage_path_habitat.append(start_pos_habitat.tolist())
        self.current_stage_path_world.append(start_pos_world.tolist())

        self.start_rosbag_recording(stage_num=self.stage + 1)

        # 3. Change state to NAVIGATING
        self.state = "NAVIGATING"
        self.navigation_start_time = rospy.get_time()

    def execute_scanning(self):
        """Performs a 360-degree turn to scan the environment."""
        rospy.loginfo("State: SCANNING - Performing 360-degree scan.")
        total_rotation = 0
        while total_rotation < 360:
            if self.stop_requested:
                rospy.logwarn("Scan interrupted by shutdown request.")
                break
            self._agent_turn(self.config.TURN_STEP_DEG)
            timestamp = rospy.Time.now()
            self.publish_habitat_to_world_tf(timestamp)
            self.publish_agent_tf(timestamp)
            self.publish_sensor_images()
            total_rotation += self.config.TURN_STEP_DEG
            self.rate.sleep()
        rospy.loginfo("Scan complete.")
        self.stop_rosbag_recording()
        self.state = "PLANNING"

    def execute_planning(self):
        """Executes the full planning stack."""
        rospy.loginfo("State: PLANNING - Initiating planning sequence.")
        copied_dsg_paths = []
        if self.skip_dsg_wait:
            rospy.loginfo("Skipping DSG wait and re-using existing files for re-planning.")
            # Get the paths to the DSG files already in the current stage's directory
            copied_dsg_paths = [os.path.join(self.config.WORKING_DIRECTORY, os.path.basename(p)) for p in self.config.DSG_SOURCE_PATHS]
            self.skip_dsg_wait = False
        else:
            # This is the normal behavior after a scan
            copied_dsg_paths = self._wait_for_and_copy_dsg_files()

        if not copied_dsg_paths:
            rospy.logerr("Failed to get new DSG files from mapping pipeline. Returning to IDLE.")
            self.state = "IDLE"
            return

        try:
            # 1. LLM Scene Completion
            generated_graphs = self.llm_manager.complete_scene_graph(
                copied_dsg_paths
            )

            # 2. Uncertainty Calculation
            current_position = self.agent.get_state().position
            current_world_position = self._transform_pose_to_world(current_position, self.tf_buffer)
            self.history_position.append(current_world_position)

            # Return top candidates
            top_candidates = self.uncertainty_calc.select_next_target(generated_graphs, self.history_position)

            # Select real target based on reachability
            best_final_pose_list, best_final_new_pose_list = [], []
            max_final_ig = -float('inf')

            rospy.loginfo(f"Evaluating reachability for {len(top_candidates)} candidates...")

            # Publish transforms for planner
            timestamp = rospy.Time.now()
            self.publish_habitat_to_world_tf(timestamp)
            self.publish_agent_tf(timestamp)

            for pose in top_candidates:
                target_pos = pose[:3]
                
                # Check where the planner actually lands
                actual_end_pos, path_len = self.mid_planner.get_reachable_endpoint(target_pos)
                
                if actual_end_pos is None:
                    rospy.logwarn("Mid-level planner could not reach the target position. Skipping this candidate.")
                    continue
                
                dist = np.linalg.norm(actual_end_pos[:2] - target_pos[:2])

                if dist <= 0.1:
                    # If the planner can actually reach the target, keep original pose
                    final_pose = pose
                    final_ig = self.uncertainty_calc.calculate_specific_pose_ig(pose, path_len)
                    final_new_pose = pose
                else:
                    # Recalculate everything.
                    direction = target_pos - actual_end_pos
                    yaw = math.atan2(direction[1], direction[0])
                    yaw_deg = math.degrees(yaw)
                    
                    new_pose = np.array([actual_end_pos[0], actual_end_pos[1], actual_end_pos[2], yaw_deg])
                    
                    # Use the path_len returned by planner for the new penalty
                    final_ig = self.uncertainty_calc.calculate_specific_pose_ig(new_pose, path_len)
                    # We use new_pose to decide whether old_pose is potentially reachable
                    final_pose = pose
                    final_new_pose = new_pose
                
                # Store all the best ones
                if final_ig - max_final_ig > 1e-6:
                    max_final_ig = final_ig
                    best_final_pose_list = [final_pose]
                    best_final_new_pose_list = [final_new_pose]
                elif abs(final_ig - max_final_ig) <= 1e-6:
                    best_final_pose_list.append(final_pose)
                    best_final_new_pose_list.append(final_new_pose)

            # Prepare the data for JSON serialization (convert numpy arrays to lists)
            data_to_save = {
                "final_pose": [best_final_pose.tolist() for best_final_pose in best_final_pose_list],
                "new_pose": [best_final_new_pose.tolist() for best_final_new_pose in best_final_new_pose_list],
                "best_ig": max_final_ig
            }

            json_filepath = os.path.join(self.config.WORKING_DIRECTORY, "pose_log.json")
            # Append the data as a new line in a JSON file
            with open(json_filepath, "a") as f:
                f.write(json.dumps(data_to_save) + "\n")

            rospy.loginfo(f"After final reachability check, selected target pose with IG: {max_final_ig}")

            target_pose = self.rng.choice(best_final_pose_list)

            # Visualize the target pose in RViz
            world_up_vector = np.array([0, 0, 1])

            # get the quaternion
            _, q = self._build_view_matrix(target_pose[:3], target_pose[3], world_up_vector)

            # Create and publish the PoseStamped message
            target_pose_msg = PoseStamped()
            target_pose_msg.header.stamp = rospy.Time.now()
            target_pose_msg.header.frame_id = self.config.WORLD_FRAME

            target_pose_msg.pose.position.x = target_pose[0]
            target_pose_msg.pose.position.y = target_pose[1]
            target_pose_msg.pose.position.z = target_pose[2]

            # Assign the calculated orientation
            target_pose_msg.pose.orientation.x = q[0]
            target_pose_msg.pose.orientation.y = q[1]
            target_pose_msg.pose.orientation.z = q[2]
            target_pose_msg.pose.orientation.w = q[3]
            
            self.target_pose_pub.publish(target_pose_msg)

            # 3. Global Planning
            high_level_path = self.global_planner.plan(
                generated_graphs[0], current_world_position, target_pose
            )

            # 4. Mid-level Planning and Local-level planning
            self.mid_planner.set_high_level_path(high_level_path)
            # The state will be changed to WAITING_FOR_MID_PATH and wait for local path to arrive.
            self.state = "WAITING_FOR_MID_PATH"
            # Plan once using existing occupancy grid
            if self.mid_planner.current_grid is not None:
                self.mid_planner.planning_active = True
                self.mid_planner.plan_path()
                self.mid_planner.planning_active = False

        except Exception as e:
            rospy.logerr(f"Error during planning: {e}. Retrying...")
            self.skip_dsg_wait = True

    def _end_navigation_stage(self, reason):
        """Centralized method to end the current navigation stage for any reason."""
        rospy.loginfo(f"{reason}. Ending stage {self.stage} and transitioning to SCANNING.")

        # Save all the paths
        next_stage_directory = os.path.join(self.config.BASE_DIRECTORY, str(self.stage + 1))
        os.makedirs(next_stage_directory, exist_ok=True)
        path_filepath = os.path.join(next_stage_directory, "executed_path.json")
        path_data = {
            "habitat_frame_path": self.current_stage_path_habitat,
            "world_frame_path": self.current_stage_path_world
        }
        with open(path_filepath, "w") as json_file:
            json.dump(path_data, json_file)

        # Save the path length and time for this navigation stage
        json_filepath = os.path.join(self.config.WORKING_DIRECTORY, "navigation_stats.json")
        stats_data = {
            "total_path_length_meters": self.previous_total_path_length,
            "total_navigation_time_seconds": self.previous_total_navigation_time
        }
        with open(json_filepath, "w") as json_file:
            json.dump(stats_data, json_file)

        navigation_duration_s = rospy.get_time() - self.navigation_start_time
        self.total_navigation_time += navigation_duration_s
        self.previous_total_path_length = self.total_path_length
        self.previous_total_navigation_time = self.total_navigation_time

        # Reset all planners and path variables
        self.mid_planner.set_high_level_path(None)
        self.local_path = None
        self.current_target_index = -1
        
        # Transition to the next stage
        self.state = "SCANNING"
        self.stage += 1

    def execute_navigation(self):
        """Follows the generated local path."""
        # Cannot find path, need to turn at least certain seconds
        if not self.local_path:
            rospy.logwarn("No local path available. Cannot execute navigation.")
            return

        # Finish navigation
        if self.current_target_index >= len(self.local_path):
            self._end_navigation_stage(reason="Navigation completed")
            return

        target_pos = self.local_path[self.current_target_index]
        current_pos = self.agent.get_state().position
        agent_state = self.agent.get_state()

        delta_pos = target_pos - current_pos
        # Crucial fix
        delta_pos[1] = 0
        distance = np.linalg.norm(delta_pos)

        # Check if waypoint is reached
        if distance < self.config.DISTANCE_THRESHOLD_M:
            self.current_target_index += 1
            return

        # --- Orient towards the target ---
        target_angle = math.atan2(delta_pos[2], delta_pos[0]) # Habitat is Y-up, so XZ plane
        current_forward = quaternion.as_rotation_matrix(agent_state.rotation) @ np.array([0, 0, -1])
        current_angle = math.atan2(current_forward[2], current_forward[0])
        angle_diff = target_angle - current_angle
        # Normalize angle to [-pi, pi]
        while angle_diff > math.pi: angle_diff -= 2 * math.pi
        while angle_diff <= -math.pi: angle_diff += 2 * math.pi

        if abs(angle_diff) > self.config.TURN_THRESHOLD_RAD:
            turn_direction = -np.sign(angle_diff)
            self._agent_turn(turn_direction * self.config.TURN_STEP_DEG)
            self._record_agent_position()
        else:
            self._agent_forward(self.config.MOVE_STEP_M)
            self.total_path_length += self.config.MOVE_STEP_M
            self._record_agent_position()

        timestamp = rospy.Time.now()
        self.publish_habitat_to_world_tf(timestamp)
        self.publish_agent_tf(timestamp)
        self.publish_sensor_images()

    def start_pipeline(self):
        if self.state == "IDLE":
            rospy.loginfo("User pressed 's'. Starting pipeline...")
            self.state = "SCANNING"
            self.start_rosbag_recording(stage_num=self.stage)
        else:
            rospy.logwarn(f"Cannot start, pipeline is already in '{self.state}' state.")

    def stop_pipeline(self):
        rospy.loginfo("Escape pressed. Requesting shutdown.")
        self.stop_requested = True

def setup_keyboard_listener(pipeline_instance):
    """Configures and starts the keyboard listener in a separate thread."""
    # Requires double-press of Esc within this window to exit
    ESC_EXIT_WINDOW_S = 0.5
    last_esc_press_time = 0.0

    def on_press(key):
        try:
            if key.char == 's':
                pipeline_instance.start_pipeline()
                return

        except AttributeError:
            pass

    def on_release(key):
        nonlocal last_esc_press_time

        if key == keyboard.Key.esc:
            now = time.time()

            # If Esc pressed twice within ESC_EXIT_WINDOW_S -> exit
            if now - last_esc_press_time < ESC_EXIT_WINDOW_S:
                print("Esc pressed twice quickly. Requesting shutdown.")
                pipeline_instance.stop_pipeline()
                return False
            else:
                print(f"Esc pressed. Press Esc again within {ESC_EXIT_WINDOW_S} seconds to shut down.")
                last_esc_press_time = now

    print("\n" + "="*40)
    print("      INTEGRATED EXPLORATION PIPELINE      ")
    print("="*40)
    print(" Press 's' to start the exploration cycle.")
    print(" Press 'Esc' to shut down.")
    print("="*40 + "\n")

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()


if __name__ == '__main__':
    try:
        with open("../config/pipeline_config.yaml", "r") as f:
            raw_cfg = yaml.safe_load(f)
        camera_cfg = CameraConfig(**raw_cfg["CAMERA_CONFIG"])
        config = PipelineConfig(**{**raw_cfg, "CAMERA_CONFIG": camera_cfg})
        pipeline = ExplorationPipeline(config)
        setup_keyboard_listener(pipeline)
        pipeline.run_pipeline()
    except rospy.ROSInterruptException:
        rospy.loginfo("ROS interrupt received. Shutting down.")
    except Exception as e:
        rospy.logfatal(f"An unhandled exception occurred: {e}")