#!/usr/bin/env python
"""Coverage tour explorer: builds the author-protocol reference (APR).

PREREGISTRATION_PAPER.md section 2b and Amendment 1. This is the author's
frontier explorer with the frontier planner replaced by a fixed waypoint list.
The 360 degree scan, the turn and move steps, the stage archive and the
navigation-time accounting are the explorer's own (frontier_baseline.py is
imported, not copied). Between stops the robot follows the navmesh shortest
path from pathfinder.find_path. MidPlanner never plans.

Run from exploration/scripts/ with ../config/frontier_config.yaml, next to
frontier_baseline.py. tour_waypoints.py must sit in the same directory.
Leave ASP_START_JITTER_SEED unset: the tour starts at the author's start pose.

Environment:
  APR_MODE            a or b (default a). b visits the farthest waypoint first.
  APR_SPACING         grid spacing in metres (default 1.5)
  APR_ARCHIVE_EVERY   copy the DSG files every this many stops (default 10)
  APR_MAX_WAYPOINTS   keep only the first N stops (short dry run)
  APR_WAYPOINTS_OUT   write the waypoint list and its counts here (JSON)
  APR_SUMMARY_OUT     write the tour summary here (JSON), rewritten at each stop
"""
import json
import math
import os

import numpy as np
import rospy
import yaml

from frontier_baseline import CameraConfig, PipelineConfig, FrontierPipeline, setup_keyboard_listener
# habitat_sim loads after frontier_baseline (cv2, tf2, cv_bridge, sklearn), in the author's order.
import habitat_sim
from tour_waypoints import (FLOOR_TOLERANCE_M, MAX_SNAP_M, MIN_SEPARATION_M, densify, plan_tour,
                            read_settings, should_copy_dsg, tally, write_json_atomic)

# A tour with fewer kept waypoints than this has almost surely snapped to the wrong floor.
MIN_KEPT_WAYPOINTS = int(os.environ.get("APR_MIN_KEPT", "20"))
PATH_STEP_M = 0.1  # MidPlanner publishes one point per 0.1 m grid cell; follow navmesh paths as densely


class TourPipeline(FrontierPipeline):
    """FrontierPipeline that visits a precomputed waypoint list instead of frontiers."""

    def __init__(self, config, settings=None):
        # Read the settings first: a bad value should fail before the simulator loads.
        self.settings = settings if settings is not None else read_settings(os.environ)
        super().__init__(config)  # builds sim, pathfinder, agent and the start pose
        self.tour = []            # one record per listed waypoint, in visit order
        self.next_index = 0       # first record not yet attempted
        self.current_record = None
        self.nav_time_at_start = 0.0
        self.path_length_at_start = 0.0
        self.tour_info = {}
        self.last_stop = None     # navmesh point of the last stop, the start of the next path
        self._build_tour()

    # --- Waypoint list -----------------------------------------------------

    def _snap(self, point):
        return np.array(self.pathfinder.snap_point(np.asarray(point, dtype=np.float32)), dtype=float)

    def _find_path(self, start, end):
        """Navmesh shortest path from start to end, or None if there is none."""
        path = habitat_sim.ShortestPath()
        path.requested_start = np.asarray(start, dtype=np.float32)
        path.requested_end = np.asarray(end, dtype=np.float32)
        if not self.pathfinder.find_path(path) or not np.isfinite(path.geodesic_distance):
            return None
        return path

    def _geodesic(self, a, b):
        path = self._find_path(a, b)
        return math.inf if path is None else float(path.geodesic_distance)

    def _navmesh_info(self, start_snapped):
        """Diagnostics for check C1. navigable_area covers the whole navmesh, so also
        record the start island's area when this habitat-sim build offers it."""
        info = {}
        for name in ("navigable_area", "num_islands"):
            try:
                value = getattr(self.pathfinder, name, None)
                value = value() if callable(value) else value
                info[name] = None if value is None else float(value)
            except Exception:
                info[name] = None
        try:
            island = self.pathfinder.get_island(np.asarray(start_snapped, dtype=np.float32))
            info["start_island"] = int(island)
            info["start_island_area"] = float(self.pathfinder.island_area(island))
        except Exception:
            info["start_island"] = None
            info["start_island_area"] = None
        return info

    def _build_tour(self):
        if not self.pathfinder.is_loaded:
            raise RuntimeError("Habitat navmesh is not loaded; cannot build the tour.")
        start = np.array(self.agent.get_state().position, dtype=float)
        # The agent flies at AGENT_HEIGHT above the floor. Detour scores a polygon under the
        # query point by its height gap, so a snap from camera height can land on a bed or
        # table top, which HM3D puts on its own navmesh island. Snap from the floor instead.
        probe = start.copy()
        probe[1] = start[1] - float(self.config.AGENT_HEIGHT)
        start_snapped = self._snap(probe)
        if not np.all(np.isfinite(start_snapped)):
            raise RuntimeError(f"Start pose {start.tolist()} does not snap to the navmesh.")
        floor_y = float(start_snapped[1])
        snap_moved = math.hypot(start_snapped[0] - start[0], start_snapped[2] - start[2])
        rospy.loginfo(f"Start {np.round(start, 3).tolist()} snapped from the floor to "
                      f"{np.round(start_snapped, 3).tolist()} ({snap_moved:.2f} m away).")
        self.last_stop = start_snapped
        lower, upper = self.pathfinder.get_bounds()

        waypoints, counts = plan_tour(
            np.asarray(lower, dtype=float), np.asarray(upper, dtype=float),
            start_snapped, floor_y, self._snap, self._geodesic,
            spacing=self.settings.spacing, mode=self.settings.mode,
            max_waypoints=self.settings.max_waypoints)
        if counts["kept"] < MIN_KEPT_WAYPOINTS:
            raise RuntimeError(f"Only {counts['kept']} waypoints kept (minimum {MIN_KEPT_WAYPOINTS}); "
                               f"start snapped to {start_snapped.tolist()}. Wrong floor?")
        rospy.loginfo(
            f"Tour mode {self.settings.mode}, spacing {self.settings.spacing} m, floor y {floor_y:.3f}: "
            f"grid points {counts['grid_points']}, kept {counts['kept']}, "
            f"dropped not navigable {counts['dropped_not_navigable']}, "
            f"dropped unreachable {counts['dropped_unreachable']}, "
            f"dropped duplicates {counts['dropped_duplicates']}, listed {counts['listed']}.")

        self.tour = [{"index": i, "waypoint": w.tolist(), "outcome": "pending"}
                     for i, w in enumerate(waypoints)]
        self.tour_info = {
            "mode": self.settings.mode,
            "spacing_m": self.settings.spacing,
            "scene_number": self.config.SCENE_NUMBER,
            "start_habitat": start.tolist(),
            "start_snapped_habitat": start_snapped.tolist(),
            "floor_y": floor_y,
            "start_snap_moved_m": snap_moved,
            "counts": counts,
            "rules": {"floor_tolerance_m": FLOOR_TOLERANCE_M, "max_snap_m": MAX_SNAP_M,
                      "min_separation_m": MIN_SEPARATION_M, "min_kept": MIN_KEPT_WAYPOINTS,
                      "path_step_m": PATH_STEP_M},
            "kept_area_estimate_m2": counts["kept"] * self.settings.spacing ** 2,
            "navmesh": self._navmesh_info(start_snapped),
        }
        if self.settings.waypoints_out:
            write_json_atomic(self.settings.waypoints_out,
                              dict(self.tour_info, waypoints=[r["waypoint"] for r in self.tour]), indent=1)

    # --- MidPlanner must not move the robot --------------------------------

    def mid_path_callback(self, msg):
        """Ignore mid paths. Only execute_planning sets local_path during the tour."""
        return

    # --- Planning ----------------------------------------------------------

    def _next_path(self):
        """Pop waypoints until one has a navmesh path from the last stop.

        Paths start at the last stop's navmesh point, never at a snap of the robot's
        camera-height position (see _build_tour). The robot is within the explorer's
        0.25 m acceptance radius of that point.
        Returns (record, habitat points every 0.1 m) or (None, None) when the list is spent.
        A waypoint with no path is logged, marked unreachable and skipped.
        """
        start = np.asarray(self.last_stop, dtype=float)
        while self.next_index < len(self.tour):
            record = self.tour[self.next_index]
            self.next_index += 1
            path = self._find_path(start, record["waypoint"])
            if path is None or len(path.points) == 0:
                record["outcome"] = "unreachable"
                rospy.logwarn(f"Tour waypoint {record['index'] + 1}/{len(self.tour)} "
                              f"{np.round(record['waypoint'], 3).tolist()} has no navmesh path. Skipping.")
                continue
            record["planned_path_m"] = float(path.geodesic_distance)
            heights = [abs(float(p[1]) - self.tour_info["floor_y"]) for p in path.points]
            record["max_path_height_gap_m"] = max(heights) if heights else 0.0
            # Corner points alone let the 0.25 m acceptance radius cut through door jambs.
            return record, densify(path.points, PATH_STEP_M)
        return None, None

    def _archive_stage(self, copy_dsg):
        """The explorer's stage archive; the DSG copy is optional."""
        if copy_dsg:
            self._archive_results()  # makes the stage directory and waits for stable files
        else:
            os.makedirs(os.path.join(self.config.BASE_DIRECTORY, str(self.stage)), exist_ok=True)
        working_directory = os.path.join(self.config.BASE_DIRECTORY, str(self.stage))
        write_json_atomic(os.path.join(working_directory, "navigation_stats.json"),
                          {"total_path_length_meters": self.total_path_length,
                           "total_navigation_time_seconds": self.total_navigation_time})

    def _copy_missing_dsg(self):
        """Final stage only: make sure both DSG files are there and parse.

        _archive_results copies a file only if its size changed since the last
        copy. If the final map has the same size as the one before it, nothing
        is copied, and the reference graph would be missing. Forget the last
        sizes and run the explorer's own stable-file copy again.
        """
        working_directory = os.path.join(self.config.BASE_DIRECTORY, str(self.stage))
        paths = [os.path.join(working_directory, f) for f in self.config.SCENE_GRAPH_FILENAMES]
        if not all(os.path.exists(p) for p in paths):
            rospy.logwarn("Final stage: a graph file was unchanged since the last copy; "
                          "copying again with the explorer's stable-file wait.")
            self.previous_dsg_sizes.clear()
            self._archive_results()
        for path in paths:
            try:
                with open(path) as f:
                    json.load(f)
            except Exception as e:
                rospy.logerr(f"Final stage: {path} is missing or does not parse ({e}).")

    def _summary(self, complete):
        counts = tally(r["outcome"] for r in self.tour)
        listed = len(self.tour)
        return dict(
            self.tour_info,
            complete=complete,
            final_stage=self.stage,
            waypoints_listed=listed,
            waypoints_reached=counts["reached"],
            waypoints_unreachable=counts["unreachable"],
            waypoints_unfinished=counts["unfinished"],
            reached_fraction=(counts["reached"] / listed) if listed else None,
            total_path_length_meters=self.total_path_length,
            total_navigation_time_seconds=self.total_navigation_time,
            waypoints=self.tour,
        )

    def _write_summary(self, complete):
        if self.settings.summary_out:
            write_json_atomic(self.settings.summary_out, self._summary(complete), indent=1)

    def execute_planning(self):
        rospy.loginfo("State: PLANNING - Next tour waypoint.")
        current_habitat_pos = self.agent.get_state().position
        current_world_pos = self._transform_pose_to_world(current_habitat_pos)
        if current_world_pos is None:
            rospy.logerr("Could not get agent position. Retrying scan.")
            self.state = "SCANNING"
            return

        record, points = self._next_path()
        final = record is None

        # Archive this stage. Every stop gets its directory and navigation_stats.json;
        # the DSG files are copied every APR_ARCHIVE_EVERY stops and at the end.
        self._archive_stage(should_copy_dsg(self.stage, self.settings.archive_every, final))

        if final:
            self._copy_missing_dsg()
            self._write_summary(complete=True)
            # The host watcher greps for "Exploration complete".
            rospy.loginfo("Exploration complete. No more frontiers found. Stopping.")
            self.state = "FINISHED"
            return

        record["outcome"] = "navigating"
        record["stage_start"] = self.stage
        self.current_record = record
        self.nav_time_at_start = self.total_navigation_time
        self.path_length_at_start = self.total_path_length
        rospy.loginfo(f"Tour waypoint {record['index'] + 1}/{len(self.tour)} "
                      f"{np.round(record['waypoint'], 3).tolist()}, planned path {record['planned_path_m']:.2f} m.")
        self._write_summary(complete=False)

        # Follow the navmesh path with the explorer's own execute_navigation.
        self.local_path = points
        self.current_target_index = 0
        self.mid_path_request_time = None

        # Start recording the path for this stage (the position has not changed).
        self.current_stage_path_habitat = [current_habitat_pos.tolist()]
        self.current_stage_path_world = [current_world_pos.tolist()]

        self.navigation_start_time = rospy.get_time()
        self.state = "NAVIGATING"

    def execute_navigation(self):
        stage_before = self.stage
        super().execute_navigation()
        # The explorer adds the stage and its navigation time only when the path ends.
        if self.stage != stage_before and self.current_record is not None:
            record = self.current_record
            record["outcome"] = "reached"
            record["stage_end"] = self.stage
            record["navigation_time_s"] = self.total_navigation_time - self.nav_time_at_start
            record["executed_path_m"] = self.total_path_length - self.path_length_at_start
            self.last_stop = np.asarray(record["waypoint"], dtype=float)
            self.current_record = None
            rospy.loginfo(f"Tour waypoint {record['index'] + 1}/{len(self.tour)} reached "
                          f"in {record['navigation_time_s']:.1f} s.")


if __name__ == '__main__':
    try:
        with open("../config/frontier_config.yaml", "r") as f:
            raw_cfg = yaml.safe_load(f)
        camera_cfg = CameraConfig(**raw_cfg["CAMERA_CONFIG"])
        config = PipelineConfig(**{**raw_cfg, "CAMERA_CONFIG": camera_cfg})
        pipeline = TourPipeline(config)
        setup_keyboard_listener(pipeline)
        pipeline.run_pipeline()
    except rospy.ROSInterruptException:
        rospy.loginfo("ROS interrupt received. Shutting down.")
    except Exception as e:
        rospy.logfatal(f"An unhandled exception occurred: {e}", exc_info=True)
