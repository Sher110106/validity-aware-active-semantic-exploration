"""Pinned uncertainty calculator used by the offline decision replay.

This is a local copy of the operative reference implementation captured from
the pinned ASP checkout. It is intentionally kept separate from the project
extensions: decision replay must use the author's geometry and entropy code,
not a reimplementation. The copy makes the offline test and replay path
portable; it does not change any recorded run.
"""

import yaml
import numpy as np
import ast
import datetime
import re
from scipy.spatial.transform import Rotation as R
import copy
import math
from dataclasses import dataclass
import json
import datetime
import os
from collections import Counter

@dataclass
class CameraConfig:
    fx: float = 320.0
    fy: float = 320.0
    cx: float = 320.0
    cy: float = 240.0
    width: int = 640
    height: int = 480
    near_clip: float = 0.5
    max_range: float = 3.0

class Camera:
    """
    Coordinate system -- Consistent with Clio
    (X-right, Y-down, Z-forward).
    """
    def __init__(self, config, position, yaw_degrees=0, world_up=np.array([0, 0, 1])):
        self.config = config
        self.position = position
        self.view_matrix, self.camera_quat = self._build_view_matrix(position, yaw_degrees, world_up)
        self.frustum_normals = self._calculate_frustum_normals()

    def _get_camera_orientation(self):
        return self.camera_quat

    def _build_view_matrix(self, pos, yaw_degrees, world_up):
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

    def _calculate_frustum_normals(self):
        cfg = self.config
        scale_factor = cfg.fx / cfg.fy

        p_tl = np.array([-cfg.cx, -cfg.cy * scale_factor, cfg.fx])
        p_tr = np.array([cfg.width - cfg.cx, -cfg.cy * scale_factor, cfg.fx])
        p_br = np.array([cfg.width - cfg.cx, (cfg.height - cfg.cy) * scale_factor, cfg.fx])
        p_bl = np.array([-cfg.cx, (cfg.height - cfg.cy) * scale_factor, cfg.fx])

        normals = np.zeros((4, 3))
        normals[0] = np.cross(p_tr, p_tl)
        normals[1] = np.cross(p_br, p_tr)
        normals[2] = np.cross(p_bl, p_br)
        normals[3] = np.cross(p_tl, p_bl)

        for i in range(4):
            normals[i] /= np.linalg.norm(normals[i])

        return normals

    def points_are_in_view(self, points_world):
        points_cam = points_world @ self.view_matrix[:3, :3].T + self.view_matrix[:3, 3]
        z_vals = points_cam[:, 2]

        valid_z = (z_vals > self.config.near_clip) & (np.linalg.norm(points_cam, axis=1) < self.config.max_range)
        if not np.any(valid_z):
            return False

        relevant_points = points_cam[valid_z]
        dots = self.frustum_normals @ relevant_points.T
        is_inside = np.all(dots <= 0, axis=0)

        return np.any(is_inside)

class UncertaintyCalculator:
    """
    Calculates the most informative next viewpoint to explore based on a set of
    latent complete scene graphs.
    """
    def __init__(self, config):
        self.config = config
        self.rng = np.random.default_rng(self.config.SEED)
        self.camera_config = config.CAMERA_CONFIG
        self.optimized_groups = None
        self.mapping = None

    def select_next_target(self, scene_graph_files, history_pos):
        """
        Main entry point. Calculates uncertainty over a set of scene graphs and
        returns the viewpoint with the highest information gain.
        """
        print("Starting uncertainty calculation to select next target...")

        # 1. Build scene graph groups (original + perturbations) and mapping for each file
        groups = self._build_scene_graph_groups(scene_graph_files)
        self.mapping = self._get_object_to_parent_mapping(scene_graph_files)

        # 2. Determine the sampling bounds from all graph nodes
        min_pos, max_pos = self._get_sampling_bounds(groups)

        # 3. Sample potential viewpoints and calculate observations for each
        sample_observations = self._gather_sample_observations(groups, self.mapping, min_pos, max_pos)

        # 4. Calculate information gain for each sample and find the best one
        current_pos = history_pos[-1]
        best_sample_pose_list = self._find_best_viewpoint(sample_observations, current_pos)

        best_filtered_list = []

        for pose in best_sample_pose_list:
            is_far_enough = all(
                np.linalg.norm(pose[:3] - hist_pos) > self.config.MINIMUM_DISTANCE_DIFFERENCE
                for hist_pos in history_pos
            )

            if is_far_enough:
                best_filtered_list.append(pose)

        # Prepare the data for JSON serialization (convert numpy arrays to lists)
        data_to_save = {
            "timestamp": datetime.datetime.now().isoformat(),
            "best_sample_poses": [pose.tolist() for pose in best_sample_pose_list],
            "best_filtered_poses": [pose.tolist() for pose in best_filtered_list]
        }

        json_filepath = os.path.join(self.config.WORKING_DIRECTORY, "pose_log.json")
        # Append the data as a new line in a JSON file
        with open(json_filepath, "a") as f:
            f.write(json.dumps(data_to_save) + "\n")

        # Rarely useful. The information gain metric usually yields only one viewpoint, or viewpoints that are very close to each other.
        if best_filtered_list:
            # print(f"Found {len(best_filtered_list)} valid viewpoints that meet the distance criteria. They are {best_filtered_list}")
            return best_filtered_list
        else:
            # print("No valid viewpoints found that meet the distance criteria. Selecting random viewpoint instead.")
            return best_sample_pose_list

    def _get_object_to_parent_mapping_for_one_graph(self, scene_graph):
        """
        Creates a mapping from an object ID to its parent's name.
        """
        nodes = scene_graph.get('nodes', [])
        edges = scene_graph.get('edges', [])

        # 1. Create a lookup dictionary for node IDs to names for efficient access.
        # This avoids repeatedly searching the nodes list.
        node_id_to_name = {node['id']: node['name'] for node in nodes}
        node_id_to_type = {node['id']: node.get('node_type', 'unknown') for node in nodes}

        # 2. Create the mapping from object ID to the parent's name.
        object_to_parent_name = {}
        for id1, id2 in edges:
            type1 = node_id_to_type[id1]
            type2 = node_id_to_type[id2]

            child_id, parent_id = None, None

            if type1 == 'object' and type2 == 'room':
                child_id, parent_id = id1, id2
            elif type2 == 'object' and type1 == 'room':
                child_id, parent_id = id2, id1
            else:
                continue

            # Ensure the parent ID exists in our name lookup map before access.
            if parent_id in node_id_to_name:
                parent_name = node_id_to_name[parent_id]
                object_to_parent_name[child_id] = parent_name
            else:
                # Not likely to happen
                print(f"Warning: Parent node with ID {parent_id} not found for child {child_id}.")

        return object_to_parent_name

    def _get_object_to_parent_mapping(self, filepaths):
        """
        Processes a list of scene graph YAML files to generate object-to-parent mappings.
        """
        all_mappings = []
        for filepath in filepaths:
            scene_graph = self._load_scene_graph(filepath)
            mapping = self._get_object_to_parent_mapping_for_one_graph(scene_graph)
            all_mappings.append(mapping)
        return all_mappings


    def _load_scene_graph(self, scene_graph_file):
        with open(scene_graph_file, 'r') as file:
            return yaml.safe_load(file)

    def _smart_eval(self, expr):
        if not isinstance(expr, str):
            return expr
        try:
            return ast.literal_eval(expr)
        except (SyntaxError, ValueError):
            # NumPy 2 renders ``str(list(np_array))`` as
            # ``[np.float64(...), ...]`` whereas the pinned runtime used
            # plain float literals. Normalize only these scalar wrappers so
            # cached graphs remain replayable across NumPy generations.
            normalized = re.sub(r"np\.float(?:16|32|64)\(([^()]+)\)", r"\1", expr)
            return ast.literal_eval(normalized)

    def _segment_intersects_aabb_2d(self, p0_xy, p1_xy, bmin_xy, bmax_xy, eps=1e-9):
        """
        True if 2D segment p0->p1 intersects axis-aligned box [bmin, bmax] in XY.
        """
        p0 = np.asarray(p0_xy, dtype=float)
        p1 = np.asarray(p1_xy, dtype=float)
        bmin = np.asarray(bmin_xy, dtype=float)
        bmax = np.asarray(bmax_xy, dtype=float)

        d = p1 - p0
        t0, t1 = 0.0, 1.0

        for i in range(2):
            if abs(d[i]) < eps:
                if p0[i] < bmin[i] or p0[i] > bmax[i]:
                    return False
            else:
                inv = 1.0 / d[i]
                t_near = (bmin[i] - p0[i]) * inv
                t_far  = (bmax[i] - p0[i]) * inv
                if t_near > t_far:
                    t_near, t_far = t_far, t_near
                t0 = max(t0, t_near)
                t1 = min(t1, t_far)
                if t0 > t1:
                    return False

        return True

    def _perturb_scene_graph(self, scene_graph, seed):
        # Create a local RNG for this specific call
        local_rng = np.random.default_rng(seed)
        sg = copy.deepcopy(scene_graph)

        noise_low = self.config.UNCERTAINTY_NOISE_LOW
        noise_high = self.config.UNCERTAINTY_NOISE_HIGH

        static_bounds = []
        for node in sg.get('nodes', []):
            is_door = 'door' in node.get('name', '').lower()
            if node.get('node_type') == 'structure' or is_door:
                pos = np.array(self._smart_eval(node['position']), dtype=float)
                dims = np.array(self._smart_eval(node['dimension']), dtype=float)

                min_pt = pos - dims / 2.0
                max_pt = pos + dims / 2.0
                static_bounds.append((min_pt, max_pt))

        for node in sg.get('nodes', []):
            # Skip non-objects or doors
            if node.get('node_type') == 'object' and 'door' not in node.get('name', '').lower():

                original_pos_str = node['position']
                pos = np.array(self._smart_eval(original_pos_str), dtype=float)
                dims = np.array(self._smart_eval(node['dimension']), dtype=float)

                # Retry up to 5 times to find a valid spot
                max_attempts = 5
                for attempt in range(max_attempts):

                    noise = np.zeros(3)
                    noise[:2] = local_rng.uniform(noise_low, noise_high, size=2)

                    new_pos = pos + noise
                    p0_xy = pos[:2]
                    p1_xy = new_pos[:2]

                    crossed_wall = False
                    for wall_min, wall_max in static_bounds:

                        bmin_xy = wall_min[:2]
                        bmax_xy = wall_max[:2]

                        # This function checks whether the trajectory of the perturbation crosses any wall
                        if self._segment_intersects_aabb_2d(p0_xy, p1_xy, bmin_xy, bmax_xy):
                            crossed_wall = True
                            break

                    if crossed_wall:
                        continue

                    node['position'] = str(list(new_pos))
                    break
        return sg

    def _build_scene_graph_groups(self, scene_graph_files):
        all_groups = []
        for path in scene_graph_files:
            original = self._load_scene_graph(path)
            group = [original]
            for k in range(self.config.UNCERTAINTY_PERTURBATIONS):
                group.append(self._perturb_scene_graph(original, seed=self.config.SEED + k))
            all_groups.append(group)
        return all_groups

    def _get_sampling_bounds(self, groups):
        min_position, max_position = None, None
        for group in groups:
            for scene_graph in group:
                positions = [self._smart_eval(n['position']) for n in scene_graph['nodes']]
                positions_array = np.array(positions)
                file_min = positions_array.min(axis=0)
                file_max = positions_array.max(axis=0)
                if min_position is None:
                    min_position, max_position = file_min, file_max
                else:
                    min_position = np.minimum(min_position, file_min)
                    max_position = np.maximum(max_position, file_max)

        # Clamp Z-axis for agent height
        min_position[2] = self.config.AGENT_HEIGHT
        max_position[2] = self.config.AGENT_HEIGHT

        return min_position, max_position

    def _preprocess_groups(self, groups):
        optimized_groups = []

        for group in groups:
            optimized_group = []
            for sg in group:
                # Extract targets and occluders once per graph
                targets = []
                occluders = []

                for node in sg.get('nodes', []):
                    if node['node_type'] == 'object' or node['node_type'] == 'structure':
                        pos = np.array(self._smart_eval(node['position']), dtype=float)
                        dims = np.array(self._smart_eval(node['dimension']), dtype=float)

                        orient_str = node.get('orientation')
                        if orient_str is None:
                            orient = np.eye(3)
                        else:
                            orient = np.array(self._smart_eval(orient_str), dtype=float)

                        obj_data = {
                            'id': node['id'],
                            'name': node.get('name', 'unknown'),
                            'pos': pos,
                            'dims': dims,
                            'orient': orient
                        }

                        name_lower = obj_data['name'].lower()
                        is_door = 'door' in name_lower

                        if node['node_type'] == 'object' and not is_door:
                            targets.append(obj_data)
                        elif node['node_type'] == 'structure' or is_door:
                            occluders.append(obj_data)

                optimized_group.append({'targets': targets, 'occluders': occluders})
            optimized_groups.append(optimized_group)

        return optimized_groups

    def _visible_testing(self, optimized_sg, camera):
        visible_objects_id = []
        visible_objects_name = {}

        target_objects = optimized_sg['targets']
        potential_occluders = optimized_sg['occluders']

        for target_obj in target_objects:
            corners = self._calculate_bounding_box_corners(target_obj['dims'], target_obj['pos'], target_obj['orient'])
            center = target_obj['pos'].reshape(1, 3)
            # Stack center + corners for better visiblity checking
            all_points = np.vstack((center, corners))
            is_in_frustum = camera.points_are_in_view(all_points)

            if not is_in_frustum:
                continue

            is_occluded = False
            dist_to_target = np.linalg.norm(target_obj['pos'] - camera.position)

            if dist_to_target < 1e-6:
                visible_objects_id.append(target_obj['id'])
                continue

            ray_dir = (target_obj['pos'] - camera.position) / dist_to_target

            for occluder_obj in potential_occluders:
                if target_obj['id'] == occluder_obj['id']:
                    continue

                # Ray-Box Intersection
                intersects, intersection_dist = self._ray_intersects_obb(
                    ray_origin=camera.position,
                    ray_direction=ray_dir,
                    box_center=occluder_obj['pos'],
                    box_dims=occluder_obj['dims'],
                    box_orientation_matrix=occluder_obj['orient']
                )

                if intersects and intersection_dist < dist_to_target:
                    is_occluded = True
                    break

            if not is_occluded:
                visible_objects_id.append(target_obj['id'])
                visible_objects_name[target_obj['name']] = visible_objects_name.get(target_obj['name'], 0) + 1

        return visible_objects_id, camera.position, camera._get_camera_orientation(), visible_objects_name


    def _gather_sample_observations(self, groups, mapping, min_position, max_position):
        # Done it once, save this for choosing viewpoints
        self.optimized_groups = self._preprocess_groups(groups)
        object_centers = [t['pos'] for t in self.optimized_groups[0][0]['targets']]
        obj_positions_arr = np.array(object_centers) if object_centers else np.empty((0,3))

        target_samples = self.config.UNCERTAINTY_SAMPLES
        max_range = self.camera_config.max_range
        batch_size = target_samples * 10

        low_bounds = np.append(min_position, 0.0)
        high_bounds = np.append(max_position, 360.0)

        print(f"Sampling {self.config.UNCERTAINTY_SAMPLES} viewpoints within bounds: {low_bounds} to {high_bounds}")

        # Vectorized Generation
        candidates = self.rng.uniform(low=low_bounds, high=high_bounds, size=(batch_size, 4))

        # First filter out some candidates based on distance to objects
        if len(obj_positions_arr) > 0:
            cand_pos = candidates[:, :3]
            diff = cand_pos[:, np.newaxis, :] - obj_positions_arr[np.newaxis, :, :]
            dist_sq = np.sum(diff**2, axis=2)
            min_dist_sq_per_candidate = np.min(dist_sq, axis=1)
            valid_mask = min_dist_sq_per_candidate < (max_range + 0.5)**2
            promising_candidates = candidates[valid_mask]
        else:
            promising_candidates = candidates

        sample_observations = []

        for sample in promising_candidates:
            if len(sample_observations) >= target_samples:
                break

            pos = sample[:3]
            yaw_deg = float(sample[3])

            group_obs_for_sample = []
            any_visible = False

            # Create camera outside to avoid redundant calculations
            camera = Camera(config=self.camera_config, position=pos, yaw_degrees=yaw_deg)

            for i, opt_group in enumerate(self.optimized_groups):
                names_list = []
                rooms_list = []
                for opt_sg in opt_group:
                    ids, _, _, name_counts = self._visible_testing(opt_sg, camera)

                    if name_counts:
                        any_visible = True

                    final_room_observation = set()
                    if ids:
                        parent_names = [mapping[i][obj_id] for obj_id in ids if obj_id in mapping[i]]
                        if parent_names:
                            majority_vote_room = Counter(parent_names).most_common(1)[0][0]
                            final_room_observation = {majority_vote_room}

                    names_list.append(name_counts)
                    rooms_list.append(final_room_observation)

                group_obs_for_sample.append({
                    'sample': sample,
                    'names_list': names_list,
                    'rooms_list': rooms_list
                })

            if any_visible:
                sample_observations.append(group_obs_for_sample)

        return sample_observations

    def _calculate_ig_components(self, group_obs_list, list_extractor):
        total_counts = {}
        group_entropies = []

        for group_obs in group_obs_list:
            # Extract the list of observations (e.g., names_list) for one group
            counts_list = list_extractor(group_obs)
            group_counts = {}
            for item in counts_list:
                obs = frozenset(item.items() if isinstance(item, dict) else item)
                group_counts[obs] = group_counts.get(obs, 0) + 1
                total_counts[obs] = total_counts.get(obs, 0) + 1

            gtot = sum(group_counts.values())
            H_g = -sum((c / gtot) * math.log2(c / gtot) for c in group_counts.values()) if gtot > 0 else 0.0
            group_entropies.append(H_g)

        H_y_epsilon = float(sum(group_entropies) / max(len(group_entropies), 1))
        tot = sum(total_counts.values())
        H_y = -sum((c / tot) * math.log2(c / tot) for c in total_counts.values()) if tot > 0 else 0.0

        return {"H_y_epsilon": H_y_epsilon, "H_y": H_y}

    def _find_best_viewpoint(self, sample_observations, current_pos):
        """
        Calculates the combined information gain for each sample and returns the pose
        with the highest gain.
        """
        scored_candidates = []

        for i, group_obs_list in enumerate(sample_observations):
            # Calculate IG for OBJECTS
            obj_uncertainty = self._calculate_ig_components(group_obs_list, lambda obs: obs['names_list'])
            obj_ig = obj_uncertainty["H_y"] - obj_uncertainty["H_y_epsilon"]

            # Calculate IG for ROOMS
            room_uncertainty = self._calculate_ig_components(group_obs_list, lambda obs: obs['rooms_list'])
            room_ig = room_uncertainty["H_y"] - room_uncertainty["H_y_epsilon"]

            # Calculate the final weighted Information Gain
            total_ig = obj_ig + self.config.UNCERTAINTY_ROOM_WEIGHT * room_ig

            # Check if this sample is better than the current best
            sample_pose = group_obs_list[0]['sample']

            d = np.linalg.norm(sample_pose[:3] - current_pos[:3])
            # linear penalty based on distance
            total_ig = total_ig - self.config.MOVE_COST_LAMBDA * d
            scored_candidates.append((total_ig, sample_pose))

            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            top_n_count = 10
            top_candidates = scored_candidates[:top_n_count]

            best_pose_list = [cand[1] for cand in top_candidates]

            # Get the highest score
            best_ig = top_candidates[0][0] if top_candidates else 0.0

        print(f"Highest Combined Information Gain found at first stage: {best_ig:.4f}")
        return best_pose_list

    def calculate_specific_pose_ig(self, pose, path_distance):
        """
        Recalculates IG for a specific single pose (position + yaw)
        using the stored scene graphs.
        """
        pos = pose[:3]
        yaw_deg = float(pose[3])

        new_config = copy.deepcopy(self.camera_config)
        # Give extra range to viewpoints that maybe far away from actual target
        new_config.near_clip = 0.1
        new_config.max_range = 4.0
        camera = Camera(config=new_config, position=pos, yaw_degrees=yaw_deg)

        group_obs_list = []

        for i, opt_group in enumerate(self.optimized_groups):
            names_list = []
            rooms_list = []
            for opt_sg in opt_group:
                ids, _, _, name_counts = self._visible_testing(opt_sg, camera)

                final_room_observation = set()
                if ids:
                    parent_names = [self.mapping[i][obj_id] for obj_id in ids if obj_id in self.mapping[i]]
                    if parent_names:
                        majority_vote_room = Counter(parent_names).most_common(1)[0][0]
                        final_room_observation = {majority_vote_room}

                names_list.append(name_counts)
                rooms_list.append(final_room_observation)

            group_obs_list.append({
                'sample': pose,
                'names_list': names_list,
                'rooms_list': rooms_list
            })

        # Calculate IG
        obj_uncertainty = self._calculate_ig_components(group_obs_list, lambda obs: obs['names_list'])
        obj_ig = obj_uncertainty["H_y"] - obj_uncertainty["H_y_epsilon"]

        room_uncertainty = self._calculate_ig_components(group_obs_list, lambda obs: obs['rooms_list'])
        room_ig = room_uncertainty["H_y"] - room_uncertainty["H_y_epsilon"]

        total_ig = obj_ig + self.config.UNCERTAINTY_ROOM_WEIGHT * room_ig

        # Move cost not applied at second stage

        return total_ig

    def _calculate_bounding_box_corners(self, dimension, position, orientation_matrix):
        half_dim = dimension / 2.0
        corners_local = np.array([
            [-half_dim[0], -half_dim[1], -half_dim[2]],
            [+half_dim[0], -half_dim[1], -half_dim[2]],
            [+half_dim[0], +half_dim[1], -half_dim[2]],
            [-half_dim[0], +half_dim[1], -half_dim[2]],
            [-half_dim[0], -half_dim[1], +half_dim[2]],
            [+half_dim[0], -half_dim[1], +half_dim[2]],
            [+half_dim[0], +half_dim[1], +half_dim[2]],
            [-half_dim[0], +half_dim[1], +half_dim[2]],
        ])
        rotated_corners = np.dot(orientation_matrix, corners_local.T).T
        world_corners = rotated_corners + position

        return world_corners

    def _ray_intersects_obb(self, ray_origin, ray_direction, box_center, box_dims, box_orientation_matrix):
        """
        Checks if a ray intersects an Oriented Bounding Box (OBB) using the slab method.
        """
        inv_orientation = box_orientation_matrix.T
        ray_origin_local = inv_orientation @ (ray_origin - box_center)
        ray_direction_local = inv_orientation @ ray_direction
        half_dims = box_dims / 2.0
        min_bounds = -half_dims
        max_bounds = +half_dims

        t_min = 0.0
        t_max = np.inf

        for i in range(3):
            if abs(ray_direction_local[i]) < 1e-6:
                if ray_origin_local[i] < min_bounds[i] or ray_origin_local[i] > max_bounds[i]:
                    return False, None
            else:
                t1 = (min_bounds[i] - ray_origin_local[i]) / ray_direction_local[i]
                t2 = (max_bounds[i] - ray_origin_local[i]) / ray_direction_local[i]

                if t1 > t2:
                    t1, t2 = t2, t1

                t_min = max(t_min, t1)
                t_max = min(t_max, t2)

                if t_min > t_max:
                    return False, None

        if t_min <= t_max and t_max >= 0:
            intersection_distance = max(0.0, t_min)
            return True, intersection_distance

        return False, None
