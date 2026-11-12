"""Tests for the coverage tour (tools/live_policy/host/coverage_tour.py).

Part 1 tests the pure waypoint logic in tour_waypoints.py with fake distances.
Part 2 drives the real TourPipeline on top of the author's real
frontier_baseline.py, with ROS and habitat replaced by small fakes: two rooms
joined by a corridor, plus an island nobody can reach. It needs the author's
scripts (default /tmp/asp_author_scripts, or set ASP_AUTHOR_SCRIPTS) and is
skipped when they are absent. No docker, ROS or habitat needed.
"""
import ast
import importlib.util
import json
import math
import os
import sys
import types
from pathlib import Path
from unittest import mock

import numpy as np
import pytest
import yaml  # imported here so the sys.modules patch below never removes it

TOOLS = Path(__file__).resolve().parent.parent
HOST = TOOLS / "live_policy" / "host"
AUTHOR = Path(os.environ.get("ASP_AUTHOR_SCRIPTS", "/tmp/asp_author_scripts"))
sys.path.insert(0, str(HOST))

import tour_waypoints as tw  # noqa: E402

INF = math.inf


# ---------------------------------------------------------------------------
# Part 1: pure functions
# ---------------------------------------------------------------------------

def line_dist(a, b):
    return abs(a[0] - b[0])


def test_new_files_parse_as_python_39():
    for name in ("coverage_tour.py", "tour_waypoints.py"):
        ast.parse((HOST / name).read_text(), feature_version=(3, 9))


def test_grid_covers_bounds_in_x_major_order():
    g = tw.grid_points([0, -5, 0], [3, 9, 3], 1.5, y=0.2)
    assert g.shape == (9, 3)
    assert set(g[:, 1]) == {0.2}
    assert g[:3, 0].tolist() == [0.0, 0.0, 0.0]          # x-major: x fixed while z runs
    assert g[:3, 2].tolist() == [0.0, 1.5, 3.0]
    assert g[-1].tolist() == [3.0, 0.2, 3.0]             # the upper bound is on the grid


def test_grid_stops_before_the_bound_when_spacing_does_not_divide():
    g = tw.grid_points([0, 0, 0], [4.0, 0, 1.0], 1.5, y=0)
    assert sorted(set(g[:, 0])) == [0.0, 1.5, 3.0]
    assert sorted(set(g[:, 2])) == [0.0]


def test_grid_keeps_the_last_point_despite_float_error():
    g = tw.grid_points([0.1, 0, 0.1], [0.1 + 3 * 0.3, 0, 0.1], 0.3, y=0)
    assert len(g) == 4


def test_grid_empty_and_bad_inputs():
    assert tw.grid_points([2, 0, 2], [1, 0, 1], 1.5, 0).shape == (0, 3)
    assert tw.grid_points([math.nan, 0, 0], [1, 0, 1], 1.5, 0).shape == (0, 3)
    with pytest.raises(ValueError):
        tw.grid_points([0, 0, 0], [1, 0, 1], 0, 0)


def snap_with(table, default=None):
    """Snap that looks the answer up by the grid point's (x, z)."""
    def snap(p):
        return table.get((p[0], p[2]), default if default is not None else p)
    return snap


def test_select_drops_by_rule_and_counts_add_up():
    grid = np.array([[float(i), 0.0, 0.0] for i in range(8)])
    table = {
        (0.0, 0.0): np.array([0.0, 0.0, 0.0]),            # kept
        (1.0, 0.0): np.array([math.nan] * 3),             # snap failed
        (2.0, 0.0): np.array([2.0, 0.5, 0.0]),            # dy == 0.5: dropped (needs < 0.5)
        (3.0, 0.0): np.array([3.0, 0.49, 0.0]),           # dy just under: kept
        (4.0, 0.0): np.array([4.0, 0.0, 0.75]),           # snap 0.75: kept (needs <= 0.75)
        (5.0, 0.0): np.array([5.0, 0.0, 0.76]),           # snap too far: dropped
        (6.0, 0.0): np.array([6.0, 0.0, 0.0]),            # unreachable
        (7.0, 0.0): np.array([3.0, 0.0, 0.0]),            # lands on a kept point: moved 4 m
    }
    reach = lambda p: INF if p[0] == 6.0 else 1.0
    kept, counts = tw.select_waypoints(grid, snap_with(table), reach, floor_y=0.0)
    assert [k[0] for k in kept] == [0.0, 3.0, 4.0]
    assert counts == {"grid_points": 8, "dropped_not_navigable": 4,
                      "dropped_unreachable": 1, "dropped_duplicates": 0, "kept": 3}
    assert counts["kept"] + counts["dropped_not_navigable"] + counts["dropped_unreachable"] \
        + counts["dropped_duplicates"] == counts["grid_points"]


def test_select_drops_points_within_the_separation_of_a_kept_point():
    grid = np.array([[0.0, 0, 0], [1.0, 0, 0], [2.0, 0, 0], [2.4, 0, 0], [3.5, 0, 0]])
    ident = lambda p: np.array(p, dtype=float)
    kept, counts = tw.select_waypoints(grid, ident, lambda p: 1.0, floor_y=0.0, min_separation=0.75)
    assert [k[0] for k in kept] == [0.0, 1.0, 2.0, 3.5]
    assert counts["dropped_duplicates"] == 1
    # exactly 0.75 apart counts as within
    grid = np.array([[0.0, 0, 0], [0.75, 0, 0], [1.51, 0, 0]])
    kept, counts = tw.select_waypoints(grid, ident, lambda p: 1.0, floor_y=0.0)
    assert [k[0] for k in kept] == [0.0, 1.51]
    assert counts["dropped_duplicates"] == 1


def test_select_duplicate_test_is_horizontal_only_and_uses_snapped_points():
    grid = np.array([[0.0, 0, 0], [5.0, 0, 0]])
    snap = lambda p: np.array([0.0, 0.3, 0.2]) if p[0] == 5.0 else np.array(p, dtype=float)
    # the second grid point is 5 m away but snaps within 0.75 m of the first; the snap
    # itself moved 5 m, so it is not navigable and never reaches the duplicate test
    kept, counts = tw.select_waypoints(grid, snap, lambda p: 1.0, floor_y=0.0, max_snap=10.0)
    assert len(kept) == 1 and counts["dropped_duplicates"] == 1   # height 0.3 is ignored


def test_select_unreachable_is_tested_before_duplicates():
    grid = np.array([[0.0, 0, 0], [0.1, 0, 0]])
    ident = lambda p: np.array(p, dtype=float)
    kept, counts = tw.select_waypoints(grid, ident, lambda p: INF if p[0] > 0 else 1.0, floor_y=0.0)
    assert len(kept) == 1
    assert counts["dropped_unreachable"] == 1 and counts["dropped_duplicates"] == 0


def test_select_empty_grid():
    kept, counts = tw.select_waypoints(np.empty((0, 3)), lambda p: p, lambda p: 1.0, floor_y=0.0)
    assert kept.shape == (0, 3) and counts["kept"] == 0 and counts["grid_points"] == 0


def test_order_mode_a_is_greedy_nearest_from_the_start():
    pts = [[5, 0, 0], [1, 0, 0], [3, 0, 0], [2, 0, 0], [10, 0, 0]]
    assert tw.order_waypoints(pts, [0, 0, 0], line_dist, "a") == [1, 3, 2, 0, 4]


def test_order_mode_b_starts_at_the_farthest_then_greedy():
    pts = [[5, 0, 0], [1, 0, 0], [3, 0, 0], [2, 0, 0], [10, 0, 0]]
    assert tw.order_waypoints(pts, [0, 0, 0], line_dist, "b") == [4, 0, 2, 3, 1]


def test_order_uses_the_distance_callable_not_straight_lines():
    # p0 is 1 m away through a wall (geodesic 10); p1 is 3 m away in the open.
    pts = [[1, 0, 0], [0, 0, 3]]
    wall = {(0, 0): 10.0, (1, 0): 3.0}

    def dist(a, b):
        if np.allclose(a, [0, 0, 0]):
            return wall[(0, 0)] if np.allclose(b, pts[0]) else wall[(1, 0)]
        return 5.0

    assert tw.order_waypoints(pts, [0, 0, 0], dist, "a") == [1, 0]
    assert tw.order_waypoints(pts, [0, 0, 0], dist, "b") == [0, 1]


def test_order_ties_go_to_the_lower_index():
    pts = [[2, 0, 0], [-2, 0, 0], [2, 0, 5]]
    assert tw.order_waypoints(pts, [0, 0, 0], line_dist, "a")[0] == 0
    assert tw.order_waypoints(pts, [0, 0, 0], line_dist, "b")[0] == 0


def test_order_empty_and_single_point():
    for mode in ("a", "b"):
        assert tw.order_waypoints([], [0, 0, 0], line_dist, mode) == []
        assert tw.order_waypoints([[4, 0, 0]], [0, 0, 0], line_dist, mode) == [0]


def test_order_does_not_chase_a_non_finite_distance():
    pts = [[1, 0, 0], [2, 0, 0], [3, 0, 0]]
    dist = lambda a, b: INF if b[0] == 1 else abs(a[0] - b[0])
    assert tw.order_waypoints(pts, [0, 0, 0], dist, "a")[0] == 1       # not the inf one
    assert tw.order_waypoints(pts, [0, 0, 0], dist, "b")[0] == 2       # inf is not "farthest"
    assert sorted(tw.order_waypoints(pts, [0, 0, 0], dist, "a")) == [0, 1, 2]


def test_order_rejects_an_unknown_mode():
    with pytest.raises(ValueError):
        tw.order_waypoints([[1, 0, 0]], [0, 0, 0], line_dist, "c")


def square_world():
    """3 x 3 m open floor plus an island 10 m away that no path reaches."""
    def snap(p):
        x, z = p[0], p[2]
        if 9 <= x <= 12:
            return np.array([min(max(x, 9), 12), 0.0, min(max(z, 0), 3)])
        return np.array([min(max(x, 0), 3), 0.0, min(max(z, 0), 3)])

    def dist(a, b):
        if (a[0] >= 9) != (b[0] >= 9):
            return INF
        return float(np.hypot(a[0] - b[0], a[2] - b[2]))

    return snap, dist


def test_plan_tour_end_to_end_with_counts():
    snap, dist = square_world()
    ways, counts = tw.plan_tour([0, 0, 0], [12, 3, 3], [0, 0, 0], 0.0, snap, dist,
                                spacing=1.5, mode="a")
    # x in {0, 1.5, 3} reach; 4.5, 6, 7.5 snap to x=3 (1.5 m, too far); 9, 10.5, 12 are the island
    assert counts["grid_points"] == 27
    assert counts["kept"] == 9 and len(ways) == 9
    assert counts["dropped_unreachable"] == 9
    assert counts["dropped_not_navigable"] == 9
    assert counts["dropped_duplicates"] == 0
    assert counts["listed"] == 9
    assert ways[0].tolist() == [0.0, 0.0, 0.0]                      # chain starts at the start
    assert all(ways[:, 0] <= 3.0)


def test_plan_tour_mode_b_leads_with_the_farthest_waypoint():
    snap, dist = square_world()
    ways, _ = tw.plan_tour([0, 0, 0], [12, 3, 3], [0, 0, 0], 0.0, snap, dist, mode="b")
    assert ways[0].tolist() == [3.0, 0.0, 3.0]                      # the far corner
    assert len({tuple(w) for w in ways}) == len(ways)               # each stop once


def test_plan_tour_limit_keeps_the_first_stops_of_the_full_order():
    snap, dist = square_world()
    full, _ = tw.plan_tour([0, 0, 0], [3, 3, 3], [0, 0, 0], 0.0, snap, dist, mode="a")
    short, counts = tw.plan_tour([0, 0, 0], [3, 3, 3], [0, 0, 0], 0.0, snap, dist, mode="a",
                                 max_waypoints=4)
    assert short.tolist() == full[:4].tolist()
    assert counts["listed"] == 4 and counts["kept"] == len(full)


def test_plan_tour_with_nothing_navigable():
    ways, counts = tw.plan_tour([0, 0, 0], [3, 3, 3], [0, 0, 0], 0.0,
                                lambda p: np.full(3, np.nan), lambda a, b: 1.0)
    assert ways.shape == (0, 3) and counts["kept"] == 0 and counts["listed"] == 0


def test_plan_tour_with_a_single_point():
    ways, counts = tw.plan_tour([0, 0, 0], [0, 0, 0], [0, 0, 0], 0.0,
                                lambda p: np.array(p, dtype=float), line_dist)
    assert ways.tolist() == [[0.0, 0.0, 0.0]] and counts["grid_points"] == 1


def test_read_settings_defaults_and_values():
    s = tw.read_settings({})
    assert (s.mode, s.spacing, s.archive_every, s.max_waypoints) == ("a", 1.5, 10, None)
    assert s.waypoints_out is None and s.summary_out is None
    s = tw.read_settings({"APR_MODE": "B", "APR_SPACING": "2", "APR_ARCHIVE_EVERY": "5",
                          "APR_MAX_WAYPOINTS": "7", "APR_WAYPOINTS_OUT": "/w.json",
                          "APR_SUMMARY_OUT": "/s.json"})
    assert (s.mode, s.spacing, s.archive_every, s.max_waypoints) == ("b", 2.0, 5, 7)
    assert (s.waypoints_out, s.summary_out) == ("/w.json", "/s.json")
    empty = tw.read_settings({"APR_MODE": "", "APR_SPACING": " ", "APR_MAX_WAYPOINTS": ""})
    assert (empty.mode, empty.spacing, empty.max_waypoints) == ("a", 1.5, None)


@pytest.mark.parametrize("env,name", [
    ({"APR_MODE": "c"}, "APR_MODE"),
    ({"APR_SPACING": "0"}, "APR_SPACING"),
    ({"APR_SPACING": "nan"}, "APR_SPACING"),
    ({"APR_SPACING": "wide"}, "APR_SPACING"),
    ({"APR_ARCHIVE_EVERY": "0"}, "APR_ARCHIVE_EVERY"),
    ({"APR_ARCHIVE_EVERY": "1.5"}, "APR_ARCHIVE_EVERY"),
    ({"APR_MAX_WAYPOINTS": "0"}, "APR_MAX_WAYPOINTS"),
])
def test_read_settings_rejects_bad_values(env, name):
    with pytest.raises(ValueError, match=name):
        tw.read_settings(env)


def test_should_copy_dsg_every_n_stops_and_at_the_end():
    assert [s for s in range(25) if tw.should_copy_dsg(s, 10)] == [0, 10, 20]
    assert tw.should_copy_dsg(7, 10, final=True)
    assert all(tw.should_copy_dsg(s, 1) for s in range(5))


def test_tally_counts_each_outcome():
    assert tw.tally(["reached", "reached", "unreachable", "pending", "navigating"]) == \
        {"reached": 2, "unreachable": 1, "unfinished": 2}
    assert tw.tally([]) == {"reached": 0, "unreachable": 0, "unfinished": 0}


def test_write_json_atomic_matches_json_dump_and_leaves_no_temp_file(tmp_path):
    data = {"total_path_length_meters": np.float64(1.5), "total_navigation_time_seconds": 2.0,
            "p": np.array([1.0, 2.0])}
    path = tmp_path / "a" / "stats.json"
    tw.write_json_atomic(str(path), data)
    assert path.read_text() == json.dumps({"total_path_length_meters": 1.5,
                                           "total_navigation_time_seconds": 2.0,
                                           "p": [1.0, 2.0]})
    assert [p.name for p in path.parent.iterdir()] == ["stats.json"]


# ---------------------------------------------------------------------------
# Part 2: the real TourPipeline on the author's real FrontierPipeline, with fakes
# ---------------------------------------------------------------------------

class Rot:
    """Stands in for a quaternion: it holds a 3 x 3 rotation matrix."""
    def __init__(self, m):
        self.m = np.asarray(m, dtype=float)

    def __mul__(self, other):
        return Rot(self.m @ other.m)


def fake_quat_from_angle_axis(angle, axis):
    axis = np.asarray(axis, dtype=float)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return Rot(np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * (k @ k))


class FakeShortestPath:
    def __init__(self):
        self.requested_start = None
        self.requested_end = None
        self.points = []
        self.geodesic_distance = INF


class FakePathfinder:
    """Rooms A and B joined by a corridor, and an island C. The floor is at y = 0."""
    BOXES = {"A": (0, 6, 0, 6), "CORR": (6, 8, 2.5, 3.5), "B": (8, 12, 0, 6), "C": (20, 24, 0, 6)}
    ISLAND = {"A": 0, "CORR": 0, "B": 0, "C": 1}
    is_loaded = True
    navigable_area = 123.0
    num_islands = 2

    def __init__(self):
        self.blocked_ends = set()

    def get_bounds(self):
        return np.array([0.0, 0.0, 0.0]), np.array([24.0, 3.0, 6.0])

    def _nearest(self, p):
        best = None
        for name, (x0, x1, z0, z1) in self.BOXES.items():
            q = np.array([min(max(p[0], x0), x1), 0.0, min(max(p[2], z0), z1)])
            d = float(np.linalg.norm(q - np.asarray(p, dtype=float)))
            if best is None or d < best[0]:
                best = (d, name, q)
        return best

    def snap_point(self, p):
        return self._nearest(p)[2].astype(np.float32)

    def _inside(self, p):
        return any(x0 <= p[0] <= x1 and z0 <= p[2] <= z1 for x0, x1, z0, z1 in self.BOXES.values())

    def _leg_free(self, a, b):
        return all(self._inside(a + (b - a) * t) for t in np.linspace(0, 1, 60))

    def find_path(self, path):
        s_info, e_info = self._nearest(path.requested_start), self._nearest(path.requested_end)
        s, e = s_info[2], e_info[2]
        if self.ISLAND[s_info[1]] != self.ISLAND[e_info[1]]:
            return False
        if (round(float(path.requested_end[0]), 3), round(float(path.requested_end[2]), 3)) in self.blocked_ends:
            return False
        legs = [s, e]
        if not self._leg_free(s, e):
            door = [np.array([6.0, 0, 3.0]), np.array([8.0, 0, 3.0])]
            if np.linalg.norm(door[0] - s) > np.linalg.norm(door[1] - s):
                door.reverse()
            legs = [s] + door + [e]
        if not all(self._leg_free(a, b) for a, b in zip(legs, legs[1:])):
            return False
        path.points = [leg.astype(np.float32) for leg in legs]
        path.geodesic_distance = float(sum(np.linalg.norm(b - a) for a, b in zip(legs, legs[1:])))
        return True


class FakeAgent:
    def __init__(self, position):
        self.position = np.array(position, dtype=float)
        self.rotation = Rot(np.eye(3))

    def get_state(self):
        return types.SimpleNamespace(position=self.position.copy(), rotation=self.rotation)

    def set_state(self, state, reset_sensors=True):
        self.position = np.array(state.position, dtype=float)
        self.rotation = state.rotation


class FakeSim:
    def __init__(self):
        self.pathfinder = FakePathfinder()
        self.agent = FakeAgent([1.0, 1.1, 1.0])
        self.closed = False

    def initialize_agent(self, idx):
        return self.agent

    def close(self):
        self.closed = True


class Clock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


STUB_NAMES = ["rospy", "tf2_ros", "tf2_geometry_msgs", "message_filters", "nav_msgs", "nav_msgs.msg",
              "sensor_msgs", "sensor_msgs.msg", "geometry_msgs", "geometry_msgs.msg", "cv2", "pynput",
              "cv_bridge", "sklearn", "sklearn.cluster", "visualization_msgs", "visualization_msgs.msg",
              "std_msgs", "std_msgs.msg", "mid_planning"]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def modules():
    if not (AUTHOR / "frontier_baseline.py").exists() or not (AUTHOR / "frontier_config.yaml").exists():
        pytest.skip(f"author scripts not found in {AUTHOR}")
    stubs = {name: mock.MagicMock(name=name) for name in STUB_NAMES}
    quaternion = types.ModuleType("quaternion")
    quaternion.as_rotation_matrix = lambda q: q.m
    stubs["quaternion"] = quaternion
    habitat = types.ModuleType("habitat_sim")
    habitat.ShortestPath = FakeShortestPath
    habitat.utils = types.SimpleNamespace(common=types.SimpleNamespace(
        quat_from_angle_axis=fake_quat_from_angle_axis))
    stubs["habitat_sim"] = habitat
    with mock.patch.dict(sys.modules, stubs):
        fb = _load("frontier_baseline", AUTHOR / "frontier_baseline.py")
        ct = _load("coverage_tour", HOST / "coverage_tour.py")
        yield types.SimpleNamespace(fb=fb, ct=ct, rospy=stubs["rospy"])


class Rig:
    """One TourPipeline with fakes wired in, a fake clock and a captured log."""

    def __init__(self, modules, tmp_path, monkeypatch, env, dsg_growth=True):
        self.fb, self.ct, self.rospy = modules.fb, modules.ct, modules.rospy
        self.tmp = tmp_path
        self.logs = []
        self.clock = Clock()
        self.finished_ticks = 0
        self.ticks = 0
        self.dsg_growth = dsg_growth
        self.pipeline = None

        mapping = tmp_path / "map"
        mapping.mkdir()
        self.mapping = mapping
        for key in ("ASP_START_JITTER_SEED", "APR_MODE", "APR_SPACING", "APR_ARCHIVE_EVERY",
                    "APR_MAX_WAYPOINTS", "APR_WAYPOINTS_OUT", "APR_SUMMARY_OUT"):
            monkeypatch.delenv(key, raising=False)
        self.waypoints_out = tmp_path / "waypoints.json"
        self.summary_out = tmp_path / "tour_summary.json"
        monkeypatch.setenv("APR_WAYPOINTS_OUT", str(self.waypoints_out))
        monkeypatch.setenv("APR_SUMMARY_OUT", str(self.summary_out))
        for key, value in env.items():
            monkeypatch.setenv(key, str(value))

        rig = self
        r = self.rospy
        r.loginfo = lambda msg, *a, **k: rig.logs.append(("info", str(msg)))
        r.loginfo_once = r.loginfo
        r.logwarn = lambda msg, *a, **k: rig.logs.append(("warn", str(msg)))
        r.logerr = lambda msg, *a, **k: rig.logs.append(("error", str(msg)))
        r.get_time = self.clock.time
        r.is_shutdown = lambda: rig.finished_ticks >= 2

        class Rate:
            def __init__(self, hz):
                pass

            def sleep(self):
                rig.clock.sleep(0.1)
                if rig.pipeline is not None and rig.pipeline.state == "FINISHED":
                    rig.finished_ticks += 1

        r.Rate = Rate
        r.Subscriber = mock.MagicMock(name="Subscriber")

        fb = self.fb
        monkeypatch.setattr(fb, "time", types.SimpleNamespace(time=self.clock.time, sleep=self.clock.sleep))
        monkeypatch.setattr(fb.FrontierPipeline, "_initialize_simulator", lambda s: FakeSim())
        monkeypatch.setattr(fb.FrontierPipeline, "_transform_pose_to_world",
                            lambda s, p: np.array(p, dtype=float))
        monkeypatch.setattr(fb.FrontierPipeline, "publish_tfs", lambda s: None)
        monkeypatch.setattr(fb.FrontierPipeline, "publish_sensor_images", lambda s: rig._observe())

        raw = yaml.safe_load((AUTHOR / "frontier_config.yaml").read_text())
        raw.update(SCENE_NUMBER=0,  # none of the author's start poses; the fake agent's own start
                   BASE_DIRECTORY=str(tmp_path / "stages"), MAPPING_DIRECTORY=str(mapping))
        self.config = fb.PipelineConfig(**{**raw, "CAMERA_CONFIG": fb.CameraConfig(**raw["CAMERA_CONFIG"])})
        self.pipeline = self.ct.TourPipeline(self.config)
        self.sim = self.pipeline.sim
        self._observe()

    def _observe(self):
        """The mapper writes its graph files; they grow while the robot looks around."""
        self.ticks += self.dsg_growth
        for name in self.config.SCENE_GRAPH_FILENAMES:
            (self.mapping / name).write_text("x" * (1500 + self.ticks))

    def run(self):
        self.pipeline.start_pipeline()
        self.pipeline.run_pipeline()

    def stage(self, n):
        return self.tmp / "stages" / str(n)

    def summary(self):
        return json.loads(self.summary_out.read_text())

    def messages(self, level=None):
        return [m for lv, m in self.logs if level in (None, lv)]


@pytest.fixture
def rig(modules, tmp_path, monkeypatch):
    def make(env=None, **kw):
        return Rig(modules, tmp_path, monkeypatch, env or {}, **kw)
    return make


def test_tour_visits_every_waypoint_and_archives_like_the_explorer(rig):
    r = rig({"APR_MAX_WAYPOINTS": 6, "APR_ARCHIVE_EVERY": 4})
    r.run()
    s = r.summary()

    assert r.pipeline.state == "FINISHED" and r.sim.closed
    assert "Exploration complete. No more frontiers found. Stopping." in r.messages("info")
    assert s["complete"] is True
    assert s["waypoints_listed"] == 6 and s["waypoints_reached"] == 6
    assert s["waypoints_unreachable"] == 0 and s["reached_fraction"] == 1.0
    assert [w["outcome"] for w in s["waypoints"]] == ["reached"] * 6
    assert s["final_stage"] == 6

    # stage directories 0..6, each with the explorer's two keys
    for n in range(7):
        stats = json.loads((r.stage(n) / "navigation_stats.json").read_text())
        assert set(stats) == {"total_path_length_meters", "total_navigation_time_seconds"}
    final = json.loads((r.stage(6) / "navigation_stats.json").read_text())
    assert final["total_navigation_time_seconds"] == pytest.approx(s["total_navigation_time_seconds"])
    assert final["total_path_length_meters"] == pytest.approx(s["total_path_length_meters"])

    # DSG files at stages 0 and 4 (every 4) and at the final stage 6, nowhere else
    has_dsg = [all((r.stage(n) / f).exists() for f in r.config.SCENE_GRAPH_FILENAMES) for n in range(7)]
    assert has_dsg == [True, False, False, False, True, False, True]
    assert not any((r.stage(n) / "graph0_dsg.json").exists() for n in (1, 2, 3, 5))

    # navigation time is the explorer's: ticks spent moving, 0.1 s each, no scan or archive time
    times = [w["navigation_time_s"] for w in s["waypoints"]]
    assert sum(times) == pytest.approx(s["total_navigation_time_seconds"])
    assert all(t > 0 and abs(t * 10 - round(t * 10)) < 1e-6 for t in times)
    assert s["total_path_length_meters"] == pytest.approx(sum(w["executed_path_m"] for w in s["waypoints"]))


def test_each_stage_records_a_path_that_ends_at_its_waypoint(rig):
    r = rig({"APR_MAX_WAYPOINTS": 5})
    r.run()
    s = r.summary()
    for w in s["waypoints"]:
        path = json.loads((r.stage(w["stage_end"]) / "executed_path.json").read_text())
        assert set(path) == {"habitat_frame_path", "world_frame_path"}
        end = np.array(path["habitat_frame_path"][-1])
        assert math.hypot(end[0] - w["waypoint"][0], end[2] - w["waypoint"][2]) <= 0.25 + 1e-6
        assert w["stage_end"] == w["stage_start"] + 1


def test_waypoint_list_filters_follow_the_fake_navmesh(rig):
    r = rig()
    wp = json.loads(r.waypoints_out.read_text())
    c = wp["counts"]
    assert wp["floor_y"] == pytest.approx(0.0)
    assert wp["start_habitat"] == [1.0, 1.1, 1.0]
    assert c["grid_points"] == 85                      # x 0..24 step 1.5 (17) by z 0..6 (5)
    assert c["dropped_unreachable"] == 20              # island C: x 19.5..24 snaps in, no path
    assert c["kept"] == len(wp["waypoints"]) == c["listed"] == 45    # A 25, corridor 1, B 15, x=7.5 snapped into B 4
    assert c["grid_points"] == c["kept"] + c["dropped_not_navigable"] \
        + c["dropped_unreachable"] + c["dropped_duplicates"]
    assert all(abs(w[1]) < 1e-6 for w in wp["waypoints"])
    assert all(w[0] < 13 for w in wp["waypoints"])                   # none on the island
    assert wp["navmesh"]["navigable_area"] == 123.0 and wp["navmesh"]["num_islands"] == 2.0
    assert wp["navmesh"]["start_island_area"] is None      # the fake has no get_island
    assert any("grid points 85, kept 45" in m for m in r.messages("info"))


def geodesic_from_start(r, waypoints):
    pf = r.sim.pathfinder
    start = pf.snap_point(np.array([1.0, 1.1, 1.0]))
    out = []
    for w in waypoints:
        p = FakeShortestPath()
        p.requested_start, p.requested_end = start, np.array(w, dtype=np.float32)
        assert pf.find_path(p)
        out.append(p.geodesic_distance)
    return out


def test_mode_a_chain_starts_at_the_nearest_waypoint_to_the_start(rig):
    r = rig({"APR_MODE": "a"})
    wa = json.loads(r.waypoints_out.read_text())["waypoints"]
    d = geodesic_from_start(r, wa)
    assert d[0] == pytest.approx(min(d), rel=1e-5)
    assert len(set(map(tuple, wa))) == len(wa) == 45


def test_mode_b_first_stop_is_the_farthest_by_geodesic_distance(rig):
    r = rig({"APR_MODE": "b"})
    wb = json.loads(r.waypoints_out.read_text())["waypoints"]
    d = geodesic_from_start(r, wb)
    assert d[0] == pytest.approx(max(d), rel=1e-5)
    assert len(set(map(tuple, wb))) == len(wb) == 45



def test_mode_b_tour_walks_the_corridor_corners_with_the_explorers_own_steps(rig):
    r = rig({"APR_MODE": "b", "APR_MAX_WAYPOINTS": 2})
    r.run()
    s = r.summary()
    assert s["waypoints_reached"] == 2
    path = np.array(json.loads((r.stage(1) / "executed_path.json").read_text())["habitat_frame_path"])
    assert path[0].tolist() == [1.0, 1.1, 1.0]
    in_corridor = path[(path[:, 0] > 6.3) & (path[:, 0] < 7.7)]
    assert len(in_corridor) > 5 and np.all(np.abs(in_corridor[:, 2] - 3.0) < 0.5)
    steps = np.linalg.norm(np.diff(path, axis=0), axis=1)
    assert steps.max() <= 0.075 + 1e-6                   # MOVE_STEP_M, no jumps
    assert path[:, 1].tolist() == [1.1] * len(path)      # the explorer keeps its height


def test_robot_still_starts_at_the_author_start_pose_in_mode_b(rig):
    r = rig({"APR_MODE": "b", "APR_MAX_WAYPOINTS": 2})
    assert r.pipeline.agent.get_state().position.tolist() == [1.0, 1.1, 1.0]
    r.pipeline.start_pipeline()
    r.pipeline.execute_scanning()
    r.pipeline.execute_planning()
    first = r.pipeline.local_path[-1]
    assert first[0] > 6                                  # the far room, not the near one


def test_planning_hands_a_navmesh_path_to_the_explorers_navigation(rig):
    r = rig({"APR_MAX_WAYPOINTS": 3})
    p = r.pipeline
    p.start_pipeline()
    p.execute_scanning()
    assert p.state == "PLANNING"
    p.execute_planning()
    assert p.state == "NAVIGATING"
    assert p.current_target_index == 0
    assert all(isinstance(pt, np.ndarray) and pt.shape == (3,) for pt in p.local_path)
    assert p.local_path[-1].tolist() == pytest.approx(p.tour[0]["waypoint"])
    assert p.current_stage_path_habitat == [[1.0, 1.1, 1.0]]
    assert p.mid_path_request_time is None
    assert p.navigation_start_time == r.clock.now
    part = r.summary()                                    # a partial summary is written at each stop
    assert part["complete"] is False and part["waypoints_unfinished"] == 3
    assert part["waypoints"][0]["outcome"] == "navigating"
    assert (r.stage(0) / "graph0_dsg.json").exists()      # stage 0 is always copied
    assert not r.messages("error")


def test_mid_path_messages_cannot_replace_the_local_path(rig):
    r = rig({"APR_MAX_WAYPOINTS": 3})
    p = r.pipeline
    subscribed = [c.args[2] for c in r.rospy.Subscriber.call_args_list if len(c.args) >= 3]
    assert any(getattr(cb, "__func__", None) is r.ct.TourPipeline.mid_path_callback for cb in subscribed)
    p.start_pipeline()
    p.execute_scanning()
    p.execute_planning()
    before = [pt.copy() for pt in p.local_path]
    pose = types.SimpleNamespace(pose=types.SimpleNamespace(
        position=types.SimpleNamespace(x=9.0, y=9.0, z=9.0)))
    p.mid_path_callback(types.SimpleNamespace(poses=[pose, pose]))
    assert p.current_target_index == 0
    assert all(np.array_equal(a, b) for a, b in zip(p.local_path, before)) and len(p.local_path) == len(before)
    p.mid_planner.plan_path.assert_not_called()


def test_a_waypoint_with_no_path_is_logged_and_skipped(rig):
    r = rig({"APR_MAX_WAYPOINTS": 5})
    victim = r.pipeline.tour[2]["waypoint"]
    r.sim.pathfinder.blocked_ends.add((round(victim[0], 3), round(victim[2], 3)))
    r.run()
    s = r.summary()
    assert [w["outcome"] for w in s["waypoints"]] == ["reached", "reached", "unreachable", "reached", "reached"]
    assert s["waypoints_reached"] == 4 and s["waypoints_unreachable"] == 1
    assert s["reached_fraction"] == pytest.approx(0.8)
    assert s["final_stage"] == 4                         # a skipped waypoint adds no stage
    assert any("has no navmesh path" in m for m in r.messages("warn"))
    assert s["complete"] is True


def test_every_waypoint_unreachable_still_finishes_with_a_final_archive(rig):
    r = rig({"APR_MAX_WAYPOINTS": 3})
    for w in r.pipeline.tour:
        r.sim.pathfinder.blocked_ends.add((round(w["waypoint"][0], 3), round(w["waypoint"][2], 3)))
    r.run()
    s = r.summary()
    assert s["waypoints_reached"] == 0 and s["waypoints_unreachable"] == 3 and s["final_stage"] == 0
    assert (r.stage(0) / "graph0_dsg.json").exists() and (r.stage(0) / "navigation_stats.json").exists()
    assert r.pipeline.state == "FINISHED"


def test_final_stage_gets_its_graph_even_when_the_map_did_not_change(rig):
    r = rig({"APR_MAX_WAYPOINTS": 2, "APR_ARCHIVE_EVERY": 1000}, dsg_growth=False)
    r.run()
    # stage 0 copied the graph; at the final stage the size equals the last copy, so the
    # explorer's own wait times out and the tour copies the file itself
    assert any("Timeout" in m for m in r.messages("error"))
    assert (r.stage(2) / "graph0_dsg.json").exists() and (r.stage(2) / "graph1_dsg.json").exists()
    assert any("copying again with the explorer's stable-file wait" in m for m in r.messages("warn"))
    assert not (r.stage(1) / "graph0_dsg.json").exists()


def test_no_waypoints_at_all_finishes_at_once(rig):
    r = rig({"APR_MAX_WAYPOINTS": 1})
    r.pipeline.tour = []
    r.pipeline.next_index = 0
    r.run()
    s = r.summary()
    assert s["waypoints_listed"] == 0 and s["reached_fraction"] is None and s["complete"] is True
    assert r.pipeline.state == "FINISHED"


def test_bad_settings_fail_before_the_simulator_is_built(rig):
    with pytest.raises(ValueError, match="APR_MODE"):
        rig({"APR_MODE": "x"})


def test_a_missing_navmesh_stops_the_run(modules, tmp_path, monkeypatch):
    class Bare(FakePathfinder):
        is_loaded = False

    monkeypatch.setattr(sys.modules[__name__], "FakePathfinder", Bare)
    with pytest.raises(RuntimeError, match="navmesh"):
        Rig(modules, tmp_path, monkeypatch, {})


# --- Review fixes (2026-11-06) -----------------------------------------------

def test_densify_puts_a_point_every_step_and_keeps_the_ends():
    pts = tw.densify([[0, 0, 0], [1.0, 0, 0], [1.0, 0, 0.25]], step=0.1)
    assert pts[0].tolist() == [0, 0, 0] and pts[-1].tolist() == [1.0, 0, 0.25]
    gaps = [float(np.linalg.norm(b - a)) for a, b in zip(pts, pts[1:])]
    assert max(gaps) <= 0.1 + 1e-9
    assert [1.0, 0.0, 0.0] in [p.tolist() for p in pts]   # the corner itself is kept
    assert len(tw.densify([[2, 0, 2]])) == 1 and tw.densify([]) == []


class DetourBedPathfinder(FakePathfinder):
    """Detour's findNearestPoly rule: a polygon under the query point scores
    (|dy| - climb)^2; any other scores its 3D distance squared. A bed top at
    y = 0.55 sits on its own island beside the start, as in HM3D."""
    BOXES = dict(FakePathfinder.BOXES, BED=(1.2, 2.5, 0.5, 2.0))
    ISLAND = dict(FakePathfinder.ISLAND, BED=2)
    HEIGHT = {"BED": 0.55}
    CLIMB = 0.2

    def _nearest(self, p):
        p = np.asarray(p, dtype=float)
        best = None
        for name, (x0, x1, z0, z1) in self.BOXES.items():
            y = self.HEIGHT.get(name, 0.0)
            q = np.array([min(max(p[0], x0), x1), y, min(max(p[2], z0), z1)])
            over = x0 <= p[0] <= x1 and z0 <= p[2] <= z1
            d = max(0.0, abs(p[1] - y) - self.CLIMB) ** 2 if over else float(np.sum((p - q) ** 2))
            if best is None or d < best[0]:
                best = (d, name, q)
        return math.sqrt(best[0]), best[1], best[2]


def test_a_bed_beside_the_start_does_not_capture_the_floor_or_the_tour(modules, tmp_path, monkeypatch):
    # From camera height (1.1 m) the bed top wins the snap at the start, (1.0, 1.1, 1.0):
    # 0.2^2 + 0.55^2 = 0.34 against (1.1 - 0.2)^2 = 0.81 for the floor below.
    bed = DetourBedPathfinder()
    assert bed.snap_point(np.array([1.0, 1.1, 1.0]))[1] == pytest.approx(0.55)
    monkeypatch.setattr(sys.modules[__name__], "FakePathfinder", DetourBedPathfinder)
    r = Rig(modules, tmp_path, monkeypatch, {"APR_MAX_WAYPOINTS": 12})
    assert r.pipeline.tour_info["floor_y"] == pytest.approx(0.0)
    r.run()
    s = r.summary()
    assert s["waypoints_unreachable"] == 0 and s["waypoints_reached"] == 12
    assert not any("has no navmesh path" in m for m in r.messages("warn"))


def test_too_few_waypoints_stops_the_run_before_the_tour(modules, tmp_path, monkeypatch):
    monkeypatch.setattr(modules.ct, "MIN_KEPT_WAYPOINTS", 10 ** 6)
    with pytest.raises(RuntimeError, match="Wrong floor"):
        Rig(modules, tmp_path, monkeypatch, {})
