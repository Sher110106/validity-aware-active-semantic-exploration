"""Tests for tools/live_policy/m2/factorial.py and summarise_factorial.py (PREREGISTRATION_M2.md, sha256 5b8a8400...).

Synthetic inputs throughout, except `test_real_stage_shapes_and_bench_equality`, which uses TWO real bench
stages and checks only shapes, seeds, and that the F1, F5 and F6 sets built here give the bench's own oracle,
placebo and none candidate scores (as the registered R1 picks and oracle draws). It computes and prints no
correlation and no regret. It needs the bench's /tmp farm (m2/rebuild_bench.sh --no-run, or the host script)
and skips without it.
"""
import importlib.util
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import pytest
import yaml

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LPD = HERE.parent / "live_policy"
M2 = LPD / "m2"


def _load(alias, path):
    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


F = _load("m2_factorial_under_test", M2 / "factorial.py")
S = _load("m2_summarise_under_test", M2 / "summarise_factorial.py")
rt, ep, M = F.sem()
LP = F.lp()
FARM_OK = os.path.exists("/tmp/cvp_review/audit/audit/stages.jsonl") and os.path.isdir("/tmp/cvp_review/runs")


# ------------------------------------------------------------------------------ error sample, seeds

def test_error_file_formats(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps([0.5, 1.0, 2.5]))
    (tmp_path / "b.json").write_text(json.dumps({"distances": [0.5, 1.0, 2.5]}))
    (tmp_path / "c.txt").write_text("# model x\n0.5, 1.0\n2.5\n")
    np.save(tmp_path / "d.npy", np.array([0.5, 1.0, 2.5]))
    for n in ("a.json", "b.json", "c.txt", "d.npy"):
        assert F.load_error_sample(str(tmp_path / n)).tolist() == [0.5, 1.0, 2.5]
    (tmp_path / "bad.json").write_text(json.dumps([1.0, -0.1]))
    (tmp_path / "nan.txt").write_text("1.0 nan\n")
    (tmp_path / "empty.json").write_text("[]")
    for n in ("bad.json", "nan.txt", "empty.json"):
        with pytest.raises(ValueError):
            F.load_error_sample(str(tmp_path / n))


def test_seed_key_follows_section_4():
    # §4: [20261113, run_idx, k, g, c]; c = 11 F-room, 21 / 22 / 23 F3 with DeepSeek / Haiku / Opus
    assert F.seed_key(5, 3, 6, 11) == [20261113, 5, 3, 6, 11]
    assert F.ARM_CODE == {"F-room": 11, "F3-deepseek": 21, "F3-haiku": 22, "F3-opus": 23}
    assert F.f3_code("haiku") == 22 and F.f3_code("opus") == 23
    assert F.MASTER_SEED == 20261113 and F.LAMBDA == 0.2


# ------------------------------------------------------------------------------ displacement draw

def test_displacement_is_seed_stable():
    sample = np.array([0.5, 1.0, 1.0, 3.0])
    a = F.draw_displacements(sample, 50, np.random.default_rng(F.seed_key(1, 2, 3, 21)))
    b = F.draw_displacements(sample, 50, np.random.default_rng(F.seed_key(1, 2, 3, 21)))
    c = F.draw_displacements(sample, 50, np.random.default_rng(F.seed_key(1, 2, 4, 21)))
    for x, y in zip(a, b):
        assert np.array_equal(x, y)
    assert not np.array_equal(a[0], c[0])
    rng = np.random.default_rng(F.seed_key(1, 2, 3, 21))      # the documented order: distances, then angles
    dist = sample[rng.integers(0, 4, size=50)]
    theta = rng.uniform(0.0, 2.0 * math.pi, size=50)
    assert np.array_equal(a[2], dist) and np.array_equal(a[3], theta)
    assert np.allclose(a[0], dist * np.cos(theta)) and np.allclose(a[1], dist * np.sin(theta))


def test_displacement_direction_uniform_and_distances_from_sample():
    sample = np.array([0.5, 1.0, 1.0, 3.0])
    dx, dy, dist, theta = F.draw_displacements(sample, 40000, np.random.default_rng(7))
    assert np.allclose(np.hypot(dx, dy), dist)
    assert set(np.unique(dist)) == {0.5, 1.0, 3.0}
    assert abs(np.mean(dist == 1.0) - 0.5) < 0.01 and abs(np.mean(dist == 0.5) - 0.25) < 0.01
    ang = np.arctan2(dy, dx) % (2 * math.pi)
    counts, _ = np.histogram(ang, bins=8, range=(0, 2 * math.pi))
    chi2 = float(((counts - len(ang) / 8) ** 2 / (len(ang) / 8)).sum())
    assert chi2 < 24.3                                         # 7 dof, p = 0.001
    assert abs(np.mean(np.cos(ang))) < 0.02 and abs(np.mean(np.sin(ang))) < 0.02


def _oracle_like():
    nodes = [{"id": 1, "name": "an image of a bedroom", "node_type": "room", "position": "[0.500, 0.500, 1.300]"},
             {"id": 2, "name": "bed", "node_type": "object", "position": "[0.600, 0.600, 0.500]",
              "dimension": "[1.000, 1.000, 1.000]"},
             {"id": 11, "name": "an image of a kitchen", "node_type": "room", "position": "[3.000, 3.000, 1.300]"}]
    guesses = [{"id": 12 + i, "name": f"thing{i}", "node_type": "object", "is_predicted": True,
                "dimension": "[0.400, 0.400, 0.800]", "orientation": "[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]",
                "position": f"[{1.0 + i:.3f}, {2.0:.3f}, 0.400]"} for i in range(5)]
    edges = [[2, 1]] + [[12 + i, 11] for i in range(5)]
    return {"nodes": nodes + guesses, "edges": edges}, {1, 2}


def test_displace_oracle_graph_moves_each_object_on_its_own_draw():
    graph, obs_ids = _oracle_like()
    before = json.dumps(graph, sort_keys=True)
    sample = np.array([0.5, 1.0, 2.0])
    g2, info = F.displace_oracle_graph(graph, obs_ids, sample, np.random.default_rng(3))
    assert json.dumps(graph, sort_keys=True) == before         # input untouched
    assert info["n_moved"] == 5
    assert g2["edges"] == graph["edges"]                       # the room edge stays
    assert [n["id"] for n in g2["nodes"]] == [n["id"] for n in graph["nodes"]]
    moves = []
    for a, b in zip(graph["nodes"], g2["nodes"]):
        if a["id"] in obs_ids or a["node_type"] == "room":
            assert a == b                                      # observed nodes and rooms stay
            continue
        for key in ("name", "dimension", "orientation", "is_predicted", "id"):
            assert a[key] == b[key]                            # id, label and size stay
        va, vb = LP._vec(a["position"]), LP._vec(b["position"])
        assert va[2] == vb[2]                                  # height stays: the move is horizontal
        d = math.hypot(vb[0] - va[0], vb[1] - va[1])
        assert min(abs(d - s) for s in sample) < 2e-3          # one of the sample's distances (3-decimal text)
        moves.append((round(vb[0] - va[0], 2), round(vb[1] - va[1], 2)))
    assert len(set(moves)) == 5                                # every object has its own draw
    g3, _ = F.displace_oracle_graph(graph, obs_ids, sample, np.random.default_rng(3))
    assert g3 == g2                                            # seed-stable
    g4, _ = F.displace_oracle_graph(graph, obs_ids, sample, np.random.default_rng(4))
    assert g4 != g2
    g5, i5 = F.displace_oracle_graph(graph, obs_ids, sample, np.random.default_rng(3), move=False)
    assert g5 == graph and i5["n_moved"] == 0                  # a fallback member is not moved


# ------------------------------------------------------------------------------ F0

def test_f0_graph_holds_every_unmapped_reference_object_with_the_f1_rooms():
    graph, obs_ids = _oracle_like()
    refs = [{"name": f"ref{i}", "position": [0.4 + i, 0.5, 0.45], "dimension": [0.3, 0.3, 0.9]} for i in range(6)]
    un = np.array([True, False, True, True, False, True])
    g0, info = F.build_f0_graph(graph, obs_ids, refs, un)
    assert info["n_objects"] == 4
    ids = [n["id"] for n in g0["nodes"]]
    assert len(set(ids)) == len(ids)
    kept = [n for n in g0["nodes"] if n["id"] <= 11]
    assert [n["id"] for n in kept] == [1, 2, 11]               # observed nodes and both rooms; the F1 guesses are gone
    assert not [n for n in g0["nodes"] if n["name"].startswith("thing")]
    new = [n for n in g0["nodes"] if n["id"] > 11]             # ids run on from the largest kept id
    assert [n["id"] for n in new] == [12, 13, 14, 15]
    assert [n["name"] for n in new] == ["ref0", "ref2", "ref3", "ref5"]
    for n, i in zip(new, (0, 2, 3, 5)):
        assert LP._vec(n["position"]) == pytest.approx(refs[i]["position"], abs=1e-3)   # at its true place
        assert n["is_predicted"] is True
    # each links to the nearest room: ref0 at x 0.4 -> room 1 (0.5, 0.5); ref5 at x 5.4 -> room 11 (3, 3)
    assert [n["id"] for n in new] == sorted(n["id"] for n in new)
    parent = {a: b for a, b in g0["edges"]}
    assert parent[new[0]["id"]] == 1 and parent[new[3]["id"]] == 11
    assert [2, 1] in g0["edges"] and len(g0["edges"]) == 1 + 4     # the F1 guesses' edges are gone
    assert yaml.safe_load(yaml.safe_dump(g0)) == g0
    g0b, _ = F.build_f0_graph(graph, obs_ids, refs, un)
    assert g0b == g0                                           # no draw: nothing to seed


# ------------------------------------------------------------------------------ F-room

class FakeLabels:
    """Just what froom_tables, the truth loader and stage_state need."""
    STRUCT = {"wall", "floor", "door"}
    TABLE = {"bed": "bed", "nightstand": "nightstand", "toilet": "toilet", "sink": "sink", "sofa": "sofa",
             "oven": "oven", "stove": "stove", "lamp": "lamp", "chair": "chair", "cabinet": "cabinet",
             "bedside lamp": "lamp", "wall": "wall", "duvet": "duvet", "shower door": "door"}
    _DETECTOR_LABEL = {"bed": "duvet"}
    VOCAB = frozenset({"duvet", "nightstand", "toilet", "sink", "sofa", "oven", "stove", "lamp", "chair", "cabinet"})
    MARKERS = {"bathroom": [("toilet",), ("bathtub",), ("shower",)], "bedroom": [("bed",)],
               "kitchen": [("oven",), ("stove",), ("stovetop",)], "laundry": [("washer",)],
               "living": [("couch",), ("sofa",)], "dining": [("dining", "table")]}

    @staticmethod
    def normalise(label):
        return FakeLabels.TABLE.get(label.lower().replace("_", " ").strip())

    @staticmethod
    def is_structure(c):
        return c in FakeLabels.STRUCT

    @staticmethod
    def detector_vocab():
        return FakeLabels.VOCAB

    @staticmethod
    def answers_to(raw):
        names = {raw.lower(), FakeLabels._DETECTOR_LABEL.get(raw.lower(), raw.lower())}
        cs = {FakeLabels.normalise(n) for n in names}
        return frozenset(c for c in cs if c is not None and c not in FakeLabels.STRUCT)

    @staticmethod
    def room_type(name):
        s = name.lower()
        for t in ("bath", "bed", "kitchen", "laundry", "living", "dining"):
            if t in s:
                return {"bath": "bathroom", "bed": "bedroom"}.get(t, t)
        return None

    @staticmethod
    def marker_types(raw):
        w = raw.lower().split()
        return frozenset(t for t, pats in FakeLabels.MARKERS.items()
                         for p in pats if any(tuple(w[i:i + len(p)]) == p for i in range(len(w) - len(p) + 1)))


def _mask(ix0, ix1, iy0, iy1):
    m = np.zeros((100, 100), dtype=bool)
    m[iy0:iy1 + 1, ix0:ix1 + 1] = True
    return m


def _obj(oid, name, region, centre, size=0.2):
    return {"id": oid, "name": name, "region": region, "n_tri": 12,
            "world_min": [centre[0] - size / 2, centre[1] - size / 2, 0.0],
            "world_max": [centre[0] + size / 2, centre[1] + size / 2, 1.0]}


# regions: 1 bathroom (toilet, sink)                  ix 0..39  iy 0..39   floor iy 0..34
#          2 bedroom (bed, nightstand, bedside lamp)  ix 39..79 iy 0..39
#          3 kitchen (oven, stove, cabinet)           ix 0..39  iy 50..79  no floor mask
#          4 other (chair)                            ix 60..99 iy 50..99
#          5 living + bathroom (sofa, toilet, lamp)   ix 45..58 iy 80..99
#          6 dining only (dining table)               ix 0..20  iy 85..99
OBJECTS = [_obj(1, "toilet", 1, (0.5, 0.5)), _obj(3, "sink", 1, (1.5, 0.5)), _obj(4, "wall", 1, (0.0, 1.0)),
           _obj(10, "bed", 2, (3.0, 1.0)), _obj(11, "nightstand", 2, (3.5, 0.5)), _obj(12, "bedside lamp", 2, (3.2, 1.5)),
           _obj(20, "oven", 3, (0.5, 3.0)), _obj(21, "stove", 3, (1.0, 3.0)), _obj(24, "cabinet", 3, (1.8, 3.5)),
           _obj(30, "chair", 4, (3.5, 3.0)),
           _obj(40, "sofa", 5, (2.5, 4.5)), _obj(41, "toilet", 5, (2.6, 4.6)), _obj(42, "lamp", 5, (2.7, 4.7)),
           _obj(50, "dining table", 6, (0.5, 4.5))]


@pytest.fixture()
def fake_labels(monkeypatch):
    monkeypatch.setattr(rt, "labels", FakeLabels)
    monkeypatch.setattr(ep, "labels", FakeLabels)


@pytest.fixture()
def truth(tmp_path, fake_labels):
    masks = np.stack([_mask(0, 39, 0, 39), _mask(39, 79, 0, 39), _mask(0, 39, 50, 79), _mask(60, 99, 50, 99),
                      _mask(45, 58, 80, 99), _mask(0, 20, 85, 99)])
    floors = np.stack([_mask(0, 39, 0, 34), _mask(39, 79, 0, 34), np.zeros((100, 100), dtype=bool),
                       _mask(65, 99, 50, 99), _mask(46, 57, 80, 99), _mask(1, 19, 85, 99)])
    np.savez(tmp_path / "99999_region_footprints.npz", scene=np.array("99999"), origin_xy=np.array([0.0, 0.0]),
             cell_size=np.array(0.05), axis_names=np.array(["x", "y"]), vertical_axis=np.array("z"),
             region_ids=np.array([1, 2, 3, 4, 5, 6]), floor_masks=floors, any_masks=masks,
             habitat_to_world_R=np.eye(3), habitat_to_world_t=np.zeros(3))
    (tmp_path / "99999_semantic_geometry.json").write_text(json.dumps(
        {"scene": "99999", "n_objects": len(OBJECTS), "objects": {str(o["id"]): o for o in OBJECTS}}))
    (tmp_path / "99999_regions.json").write_text(json.dumps(
        {"scene": "99999", "regions": [{"region_id": r, "centroid_xy": [1.0 * r, 1.0 * r + 0.5]} for r in range(1, 7)]}))
    return rt.load_scene_truth("99999", truth_dir=tmp_path)


def _observed():
    g, _ = _oracle_like()
    return {"nodes": g["nodes"][:2], "edges": g["edges"][:1]}


def _state(truth, path_xy=((0.5, 0.5),)):
    obs = M.ObservedGraph(rooms=(), objects=(), node_ids=frozenset())
    row = M.Row(row_id="t", scene="99999", seed=1, arm="official", stage=1, cluster="c", round=1, is_gemini_row=False,
                observed=obs, path_xy=tuple(path_xy))
    return rt.stage_state(truth, row)


def test_froom_tables_mean_is_not_rounded_and_pools_a_missing_type(truth):
    t = F.froom_tables(truth, FakeLabels, M.ROOM_TYPES)
    assert t["bedroom"]["n"] == 3 and sorted(t["bedroom"]["pool"]) == ["duvet", "lamp", "nightstand"]   # bed -> detector word
    assert t["kitchen"]["n"] == 3 and t["living"]["n"] == 3
    # bathroom: region 1 holds 2 detector objects, region 5 holds 3: mean 2.5, no rounding
    assert t["bathroom"]["n"] == 2.5 and t["bathroom"]["n_regions"] == 2 and not t["bathroom"]["pooled"]
    assert "wall" not in t["bathroom"]["pool"]
    # laundry: no region of that type, so n and the pool are over all typed regions (1, 2, 3, 5): 2, 3, 3, 3 objects
    lau = t["laundry"]
    assert lau["pooled"] and lau["n_regions"] == 4 and lau["n"] == pytest.approx(11 / 4)
    assert len(lau["pool"]) == 11


def test_stage_state_feeds_froom_categories(truth):
    st = _state(truth, path_xy=[(0.5, 0.5)])                   # in region 1's floor
    assert st.seen == {1} and st.unseen == {2, 3, 4, 5, 6}
    cats = F.froom_categories(truth, st, M.ROOM_TYPES)
    # 2 bedroom, 3 kitchen, 5 bathroom and living (once for each); 4 has no type, 6 only dining, 1 is seen
    assert cats == [(2, "bedroom"), (3, "kitchen"), (5, "bathroom"), (5, "living")]


def test_froom_graph_shape(truth):
    calib = LP.load_calibration()
    st = _state(truth)
    tables = F.froom_tables(truth, FakeLabels, M.ROOM_TYPES)
    obs = _observed()
    g, info = F.build_froom_graph(obs, np.random.default_rng(F.seed_key(0, 1, 0, 11)), calib, truth, st, tables, 12, M.ROOM_TYPES)
    nodes = {n["id"]: n for n in g["nodes"]}
    assert len(nodes) == len(g["nodes"])                       # ids unique
    new_rooms = [n for n in g["nodes"] if n["node_type"] == "room" and n["id"] != 1]
    new_objs = [n for n in g["nodes"] if n["node_type"] == "object" and n["id"] != 2]
    # one room per (region, type), ids from the largest observed id + 1 in region then type order
    assert [n["id"] for n in new_rooms] == [3, 4, 5, 6]
    assert [n["name"] for n in new_rooms] == [F.FROOM_ROOM_NAME[t] for t in ("bedroom", "kitchen", "bathroom", "living")]
    for n in new_rooms:
        assert FakeLabels.room_type(n["name"]) in M.ROOM_TYPES
    cent = {3: truth.regions[2].centroid_xy, 4: truth.regions[3].centroid_xy, 5: truth.regions[5].centroid_xy, 6: truth.regions[5].centroid_xy}
    for n in new_rooms:
        assert LP._vec(n["position"])[:2] == pytest.approx(list(cent[n["id"]]), abs=1e-3)   # at the region's centroid
    assert all(o["id"] > 6 for o in new_objs)                  # objects after all the room ids
    # N = 12 shared by one multinomial draw, in proportion to n_T = 3, 3, 2.5, 3
    assert len(new_objs) == 12 == info["n_objects"] == sum(info["counts"])
    rng = np.random.default_rng(F.seed_key(0, 1, 0, 11))
    w = np.array([3.0, 3.0, 2.5, 3.0])
    assert info["counts"] == rng.multinomial(12, w / w.sum()).tolist()      # the first draw from the member's stream
    # each object has exactly one edge, to its region's FIRST room node (region 5: bathroom, id 5, not living, id 6)
    obj_edges = [e for e in g["edges"] if e[0] in {o["id"] for o in new_objs}]
    assert len(obj_edges) == 12 and len({e[0] for e in obj_edges}) == 12
    assert not [e for e in g["edges"] if e[0] in (3, 4, 5, 6)]  # room nodes carry no edge
    assert g["edges"][:1] == obs["edges"]
    assert {e[1] for e in obj_edges} <= {3, 4, 5}              # never room 6
    region_of_room = {3: 2, 4: 3, 5: 5}
    for o in new_objs:
        room = next(b for a, b in g["edges"] if a == o["id"])
        x, y, z = LP._vec(o["position"])
        assert region_of_room[room] in truth.inside_floor((x, y))   # uniform in the region's floor mask
        assert o["is_predicted"] is True and o["name"] in FakeLabels.VOCAB
        assert [float(v) for v in LP._vec(o["dimension"])] in [list(map(float, d)) for d in calib["dims_pool"]]
        assert z == pytest.approx(0.0 + LP._vec(o["dimension"])[2] / 2, abs=1e-3) or True


def test_froom_height_follows_placebo_graph(truth):
    calib = LP.load_calibration()
    st = _state(truth)
    tables = F.froom_tables(truth, FakeLabels, M.ROOM_TYPES)
    obs = _observed()                                          # observed object 2: z 0.5, height 1.0 -> floor at 0.0
    g, _ = F.build_froom_graph(obs, np.random.default_rng(2), calib, truth, st, tables, 30, M.ROOM_TYPES)
    for o in g["nodes"]:
        if o["node_type"] == "object" and o["id"] != 2:
            assert LP._vec(o["position"])[2] == pytest.approx(0.0 + LP._vec(o["dimension"])[2] / 2, abs=1e-3)
    room_z = [LP._vec(n["position"])[2] for n in g["nodes"] if n["node_type"] == "room" and n["id"] != 1]
    assert room_z == [1.3] * 4                                 # the observed rooms' median height


def test_froom_counts_are_proportional_to_n_t(truth):
    calib = LP.load_calibration()
    st = _state(truth)
    tables = F.froom_tables(truth, FakeLabels, M.ROOM_TYPES)
    g, info = F.build_froom_graph(_observed(), np.random.default_rng(1), calib, truth, st, tables, 40000, M.ROOM_TYPES)
    share = np.array(info["counts"]) / 40000
    assert share == pytest.approx(np.array([3.0, 3.0, 2.5, 3.0]) / 11.5, abs=0.01)


def test_froom_graph_same_yaml_shape_as_placebo(truth):
    calib = LP.load_calibration()
    st = _state(truth)
    tables = F.froom_tables(truth, FakeLabels, M.ROOM_TYPES)
    obs = _observed()
    g, _ = F.build_froom_graph(obs, np.random.default_rng(1), calib, truth, st, tables, 8, M.ROOM_TYPES)
    p = LP.placebo_graph(obs, np.random.default_rng(1), calib)
    assert set(g) == set(p) == {"nodes", "edges"}
    keys = lambda graph, typ: {tuple(sorted(n)) for n in graph["nodes"] if n["node_type"] == typ and n["id"] not in (1, 2)}
    assert keys(g, "room") == keys(p, "room")
    assert keys(g, "object") == keys(p, "object")
    assert yaml.safe_load(yaml.safe_dump(g)) == g              # a plain YAML round trip
    assert all(isinstance(e, list) and len(e) == 2 for e in g["edges"])


def test_froom_seed_stable_rooms_shared_in_a_track_and_objects_differ(truth):
    calib = LP.load_calibration()
    st = _state(truth)
    tables = F.froom_tables(truth, FakeLabels, M.ROOM_TYPES)
    obs = _observed()
    mk = lambda gid: F.build_froom_graph(obs, np.random.default_rng(F.seed_key(2, 3, gid, 11)), calib, truth, st, tables, 10, M.ROOM_TYPES)[0]
    assert mk(0) == mk(0)
    rooms = lambda g: [n for n in g["nodes"] if n["node_type"] == "room"]
    assert mk(0) != mk(1)                                      # members draw independently
    assert rooms(mk(0)) == rooms(mk(1)) == rooms(mk(2))       # room ids, names and places are the same in every member
    assert mk(0) != mk(4)


def test_froom_zero_objects_and_no_unseen_typed_region(truth):
    calib = LP.load_calibration()
    tables = F.froom_tables(truth, FakeLabels, M.ROOM_TYPES)
    obs = _observed()
    g, info = F.build_froom_graph(obs, np.random.default_rng(1), calib, truth, _state(truth), tables, 0, M.ROOM_TYPES)
    assert info["n_rooms"] == 4 and info["n_objects"] == 0 and len(g["edges"]) == len(obs["edges"])
    seen_all = M.StageState(seen=frozenset(range(1, 7)), partly_seen=frozenset(), unobserved=frozenset(),
                            mapped_objects=frozenset(), open_types=frozenset(), open_classes=frozenset(),
                            open_types_loose=frozenset(), open_classes_loose=frozenset())
    g, info = F.build_froom_graph(obs, np.random.default_rng(1), calib, truth, seen_all, tables, 9, M.ROOM_TYPES)
    assert g["nodes"] == obs["nodes"] and g["edges"] == obs["edges"]    # equals the member's F6 graph
    assert info["no_unseen_typed"] is True
    only_untyped = M.StageState(seen=frozenset({1, 2, 3, 5, 6}), partly_seen=frozenset(), unobserved=frozenset({4}),
                                mapped_objects=frozenset(), open_types=frozenset(), open_classes=frozenset(),
                                open_types_loose=frozenset(), open_classes_loose=frozenset())
    g, info = F.build_froom_graph(obs, np.random.default_rng(1), calib, truth, only_untyped, tables, 9, M.ROOM_TYPES)
    assert g["nodes"] == obs["nodes"] and info["no_unseen_typed"] is True   # an unseen region without a type counts for nothing
    partly = M.StageState(seen=frozenset(), partly_seen=frozenset({2}), unobserved=frozenset({3}),
                          mapped_objects=frozenset(), open_types=frozenset(), open_classes=frozenset(),
                          open_types_loose=frozenset(), open_classes_loose=frozenset())
    assert F.froom_categories(truth, partly, M.ROOM_TYPES) == [(2, "bedroom"), (3, "kitchen")]   # unseen = partly seen + unobserved


def test_study_refuses_without_hash_and_with_too_many_workers(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "PREREG_SHA", tmp_path / "none.sha256")
    with pytest.raises(SystemExit):
        F.check_hashed()
    prereg = tmp_path / "P.md"
    prereg.write_text("rules")
    monkeypatch.setattr(F, "PREREG", prereg)
    sha = tmp_path / "P.sha256"
    sha.write_text("0" * 64 + "  P.md\n")
    monkeypatch.setattr(F, "PREREG_SHA", sha)
    with pytest.raises(SystemExit):
        F.check_hashed()
    import hashlib
    h = hashlib.sha256(b"rules").hexdigest()
    sha.write_text(f"{h}  P.md\n")
    assert F.check_hashed() == h
    with pytest.raises(SystemExit):
        F.main(["--out", str(tmp_path / "o"), "--nproc", "49"])
    with pytest.raises(SystemExit):                            # F3 needs an error file
        F.main(["--out", str(tmp_path / "o"), "--arms", "F1,F3", "--nproc", "2"])
    assert F.expand_arms(["F1", "F5", "F3"], ["deepseek", "opus"]) == ["F1", "F5a", "F5b", "F3-deepseek", "F3-opus"]


def test_the_repository_hash_file_matches_the_rules():
    assert F.check_hashed() == "5b8a84004c6f887cf9117bf6a4d6e9edc01aa5a6b0ad64763eeccf31f62d643c"


def test_regret_r1_as_the_bench_defines_it():
    U = np.array([3, 7, 7, 1])
    assert F.regret_r1(np.array([0.1, 0.9, 0.2, 0.5]), U) == 0.0     # picks index 1
    assert F.regret_r1(np.array([0.1, 0.0, 0.2, 0.9]), U) == 6.0     # picks index 3: 7 - 1
    assert F.regret_r1(np.array([1.0, 1.0, 1.0, 1.0]), U) == 4.0     # argmax = first: 7 - 3


# ------------------------------------------------------------------------------ summary

def _rows(spec, n_runs=8, n_stages=6, n_cand=40, seed=0, arm_names=("official", "official", "placebo", "official"),
          extra_arms=None):
    """spec: arm -> callable(rng, yard, d, run) giving a score array. Rows in factorial.py's output shape."""
    rng = np.random.default_rng(seed)
    rows = []
    for ri in range(n_runs):
        for k in range(n_stages):
            yard = rng.integers(0, 9, n_cand).astype(float)
            yard[0], yard[1] = 0.0, 8.0                        # never constant
            d = rng.uniform(0, 5, n_cand)
            arms = {}
            for a, fn in {**spec, **(extra_arms or {})}.items():
                sc = np.asarray(fn(rng, yard, d, ri), float)
                ig = sc + 0.2 * d
                info = {}
                if a == "F-room":
                    info = {"per_member": [{"gid": 0, "no_unseen_typed": False}, {"gid": 1, "no_unseen_typed": k == 0}]}
                if a.startswith("F3-"):
                    info = {"per_member": [{"gid": 0, "fallback": k == 1}, {"gid": 1, "fallback": False}]}
                arms[a] = {"ig": ig.tolist(), "score": sc.tolist(), "pick": int(np.argmax(sc)), "n_obj": [5, 7],
                           "regret": {"Uwall": float(yard.max() - yard[int(np.argmax(sc))]),
                                      "Ucone": float(yard.max() - yard[int(np.argmax(sc))])}, "info": info}
            rows.append({"run": f"r{ri:02d}", "run_idx": ri, "arm": arm_names[ri % 4], "scene": "00853" if ri < n_runs // 2 else "00871",
                         "seed": 42 + ri % 2, "stage": k, "n_cand": n_cand, "top10_match": True,
                         "yard": {"Ucone": yard.tolist(), "Uwall": yard.tolist(), "Ucone_audit": yard.tolist(),
                                  "U360": (yard + rng.normal(0, 0.1, n_cand)).tolist()},
                         "d": d.tolist(), "arms": arms})
    return rows


noise = lambda rng, y, d, ri: rng.normal(size=len(y))
exact = lambda rng, y, d, ri: y                                # a score equal to the yardstick: rho 1
half = lambda rng, y, d, ri: y + rng.normal(0, 2.0, len(y)) * (1 + ri % 3)   # about half-way, varying by run


def _spec(f1=exact, f3=noise, froom=exact, f6=noise):
    return {"F1": f1, "F5a": noise, "F5b": noise, "F6": f6, "F0": noise, "F3-deepseek": f3, "F-room": froom}


def _sum(rows, **kw):
    return S.summarise(rows, rho=S._rho_copy, **kw)


def test_summary_sufficient_and_not_shown_sufficient_branches():
    res = _sum(_rows(_spec()))
    a = res["analysis"]["main"]["all"]
    assert a["n_left_out_by_list"] == 0 and a["n_runs"] == 8
    assert a["arm_mean_rho"]["F1"]["mean"] == pytest.approx(1.0)
    assert abs(a["arm_mean_rho"]["F5"]["mean"]) < 0.1
    assert S.wholly_above(a["differences"]["A"])
    r = a["reading"]
    assert r["read_further"] is True and r["step"] == 2
    assert r["verdicts"]["C"] == "sufficient"                  # F-room = the yardstick: C - 0.5 A is near 0.5
    assert r["verdicts"]["B_deepseek"] == S.VERDICT_NOT_SUFFICIENT   # F3 = noise: B - 0.5 A is near -0.5
    assert S.VERDICT_NOT_SUFFICIENT == "not shown sufficient, on a provisional yardstick"
    assert "F0-F5" in a["differences"] and "F0-F5" not in a["reading_series"]   # F0 is reported, never read


def test_summary_inconclusive_branch():
    res = _sum(_rows(_spec(f3=half, froom=half), n_runs=8, n_stages=4, seed=4))
    a = res["analysis"]["main"]["all"]
    assert S.wholly_above(a["differences"]["A"])
    assert a["reading"]["verdicts"]["C"] == "inconclusive"
    assert a["reading"]["verdicts"]["B_deepseek"] == "inconclusive"


def test_summary_not_read_further_branch():
    res = _sum(_rows(_spec(f1=noise, f3=exact, froom=exact), seed=5))   # the ceiling is no better than the floor
    r = res["analysis"]["main"]["all"]["reading"]
    assert r["read_further"] is False and r["step"] == 1 and r["verdicts"] == {}
    assert "not read further" in r["reading"]
    assert not S.wholly_above(res["analysis"]["main"]["all"]["differences"]["A"])


def test_read_outcome_on_made_up_intervals():
    ci = lambda lo, hi: {"mean": (lo + hi) / 2, "lo": lo, "hi": hi, "n_runs": 24}
    assert S.read_outcome(ci(0.0, 0.5), {"C": ci(0.1, 0.2)})["read_further"] is False     # lo == 0 is not "wholly above"
    assert S.read_outcome(ci(-0.1, 0.5), {})["step"] == 1
    r = S.read_outcome(ci(0.2, 0.6), {"C": ci(0.01, 0.2), "B_a": ci(-0.3, -0.01), "B_b": ci(-0.1, 0.1),
                                      "B_c": ci(0.0, 0.2), "B_d": ci(-0.2, 0.0)})
    assert r["verdicts"] == {"C": "sufficient", "B_a": S.VERDICT_NOT_SUFFICIENT, "B_b": "inconclusive",
                             "B_c": "inconclusive", "B_d": "inconclusive"}


def test_left_out_rule_list_is_saved_and_reused(tmp_path):
    rows = _rows(_spec(), n_runs=4, n_stages=5, seed=1)
    rows[2]["arms"]["F6"]["score"] = [0.0] * 40                # constant score for one listed arm at one stage
    rows[7]["yard"]["Ucone"] = [3.0] * 40                      # constant yardstick: undefined for every arm
    rows[11]["arms"]["F0"]["score"] = [0.0] * 40               # F0 is not on the list: its stage stays in
    path = tmp_path / "left_out.json"
    res = _sum(rows, left_out_path=str(path))
    lo = json.loads(path.read_text())
    assert {x["key"] for x in lo["left_out"]} == {"r00:2", "r01:2"}
    assert lo["left_out"][0]["undefined_for"] == ["F6"]
    assert set(lo["left_out"][1]["undefined_for"]) == {"F1", "F5", "F6", "F-room", "F3-deepseek"}
    a = res["analysis"]["main"]["all"]
    assert a["n_stages_matched"] == 20 and a["n_left_out_by_list"] == 2 and a["n_stages_kept"] == 18
    assert a["kept_stages_without_value_by_arm"]["F0"] == 1
    # the left-out stages are gone for F1 too: run r00's mean is over its other four stages
    run0 = [r for r in rows if r["run"] == "r00" and r["stage"] != 2]
    expect = np.mean([S._rho_copy(r["arms"]["F1"]["score"], r["yard"]["Ucone"]) for r in run0])
    assert a["per_run_mean_rho"]["r00"]["F1"] == pytest.approx(expect)
    # a second pass with new data: the file is read as it stands, not recomputed
    rows2 = _rows(_spec(), n_runs=4, n_stages=5, seed=1)
    rows2[3]["arms"]["F-room"]["score"] = [1.0] * 40           # would be left out if the list were recomputed
    res2 = _sum(rows2, left_out_path=str(path))
    assert res2["left_out"]["source"].startswith("read from")
    assert set(res2["left_out"]["keys"]) == {"r00:2", "r01:2"}
    assert res2["analysis"]["main"]["all"]["n_dropped_extra_undefined"] == 1   # paired drop in this variant, counted
    # the list needs every one of its arms
    with pytest.raises(ValueError):
        S.compute_left_out([{**r, "arms": {k: v for k, v in r["arms"].items() if k != "F-room"}} for r in rows], S._rho_copy)


def test_later_pass_adds_claude_arms_on_the_saved_list(tmp_path):
    first = _rows(_spec(), n_runs=4, n_stages=4, seed=2)
    path = tmp_path / "lo.json"
    _sum(first, left_out_path=str(path))
    later = _rows({"F3-haiku": half, "F3-opus": noise}, n_runs=4, n_stages=4, seed=2)
    p1, p2 = tmp_path / "p1.jsonl", tmp_path / "p2.jsonl"
    p1.write_text("\n".join(json.dumps(r) for r in first))
    # the second pass has the same yardsticks (same seed 2 order is not the same rng, so rebuild them from pass one)
    for a, b in zip(later, first):
        a["yard"], a["d"] = b["yard"], b["d"]
    p2.write_text("\n".join(json.dumps(r) for r in later))
    merged = S.load_rows([str(p1), str(p2)])
    assert len(merged) == 16 and {"F3-haiku", "F3-opus", "F3-deepseek", "F1"} <= set(merged[0]["arms"])
    res = _sum(merged, left_out_path=str(path))
    a = res["analysis"]["main"]["all"]
    assert {"B_haiku", "B_opus", "B_deepseek", "C", "A"} <= set(a["differences"])
    assert {"B_haiku", "B_opus"} <= set(a["reading_series"])
    later[0]["yard"] = {**later[0]["yard"], "Ucone": [0.0] * 40}
    p2.write_text("\n".join(json.dumps(r) for r in later))
    with pytest.raises(ValueError):
        S.load_rows([str(p1), str(p2)])                        # passes must agree on the yardsticks


def test_f5_is_the_mean_of_its_two_sets_and_undefined_if_either_is():
    rows = _rows(_spec(), n_runs=2, n_stages=1, seed=2)
    r = rows[0]
    ra = S._rho_copy(r["arms"]["F5a"]["score"], r["yard"]["Ucone"])
    rb = S._rho_copy(r["arms"]["F5b"]["score"], r["yard"]["Ucone"])
    out = S.stage_rho(r, "score", "Ucone", S._rho_copy)
    assert out["F5"] == pytest.approx((ra + rb) / 2) and "F5a" not in out
    r["arms"]["F5b"]["score"] = [1.0] * 40
    assert S.stage_rho(r, "score", "Ucone", S._rho_copy)["F5"] is None
    rg = S.stage_regret(rows[1], "Ucone")
    assert rg["F5"] == pytest.approx((rows[1]["arms"]["F5a"]["regret"]["Ucone"] + rows[1]["arms"]["F5b"]["regret"]["Ucone"]) / 2)


def test_per_run_value_is_the_mean_of_per_stage_differences():
    rows = _rows(_spec(), n_runs=3, n_stages=4, seed=6)
    res = _sum(rows)
    a = res["analysis"]["main"]["all"]
    expect = []
    for run in ("r00", "r01", "r02"):
        ds = []
        for r in rows:
            if r["run"] == run:
                rr = S.stage_rho(r, "score", "Ucone", S._rho_copy)
                ds.append(rr["F-room"] - rr["F5"])
        expect.append(np.mean(ds))
    assert a["differences"]["C"]["mean"] == pytest.approx(np.mean(expect))   # the mean over runs, each weighing the same


def test_secondary_figures_variants_official_subset_and_clusters():
    rows = _rows(_spec(), n_runs=8, n_stages=4, seed=4)
    res = _sum(rows)
    a, off = res["analysis"]["main"]["all"], res["analysis"]["main"]["official"]
    assert set(a["median_stage_rho"]) == set(a["arms"]) == {"F1", "F5", "F6", "F0", "F3-deepseek", "F-room"}
    assert a["median_stage_rho"]["F1"] == pytest.approx(1.0)
    assert set(a["regret_R1"]) == {"Uwall", "Ucone"}
    assert a["regret_R1"]["Ucone"]["arm_mean"]["F1"]["mean"] == pytest.approx(0.0)   # picks the max of the yardstick
    assert a["regret_R1"]["Ucone"]["arm_mean"]["F5"]["mean"] > 0.5
    assert a["regret_R1"]["Ucone"]["difference_to_F5"]["F1-F5"]["mean"] < 0
    n_official = len({r["run"] for r in rows if r["arm"] == "official"})
    assert off["n_runs"] == n_official < a["n_runs"]
    assert set(res["analysis"]) == {"main", "ig_alone", "audit_Ucone", "U360"}
    assert res["analysis"]["U360"]["all"]["yardstick"] == "U360" and res["analysis"]["ig_alone"]["all"]["score"] == "ig"
    # ig alone: the scores here are ig - 0.2 d, so F1's ig is yardstick + 0.2 d, whose rho with the yardstick differs from 1
    assert res["analysis"]["ig_alone"]["all"]["median_stage_rho"]["F1"] < 1.0
    cl = res["clustered_by_scene_seed"]["main"]
    assert cl["clusters"] == [["00853", 42], ["00853", 43], ["00871", 42], ["00871", 43]]
    assert cl["arm_mean_rho"]["F1"]["mean"] == pytest.approx(a["arm_mean_rho"]["F1"]["mean"])   # same estimate, other interval
    assert cl["differences"]["A"]["lo"] != a["differences"]["A"]["lo"] or cl["differences"]["A"]["hi"] != a["differences"]["A"]["hi"]


def test_counts_objects_ig_zero_and_member_flags():
    spec = _spec()
    spec["F0"] = lambda rng, y, d, ri: -0.2 * d                # ig = 0 at every candidate
    rows = _rows(spec, n_runs=2, n_stages=4, seed=8)
    c = _sum(rows)["counts_all_stages"]
    assert c["ig_zero_stage_share"]["F0"] == {"stages_ig_zero_for_every_candidate": 8, "n_stages": 8, "share": 1.0}
    assert c["ig_zero_stage_share"]["F1"]["share"] == 0.0
    assert c["objects_per_member"]["F1"]["mean_per_member"] == 6.0 and c["objects_per_member"]["F1"]["max"] == 7
    assert c["froom_no_unseen_typed"] == {"members": 2, "members_total": 16, "stages_with_a_member": 2,
                                          "stages_all_members": 0, "stages_total": 8}
    assert c["f3_fallback_members_not_moved"]["F3-deepseek"]["members"] == 2


def test_bootstrap_is_exactly_the_registered_recipe_and_seed_stable():
    x = np.array([0.31, 0.25, 0.4, 0.12, 0.33, 0.2, 0.28, 0.35])
    W1, W2 = S.rademacher(8), S.rademacher(8)
    assert np.array_equal(W1, W2) and W1.shape == (9999, 8) and set(np.unique(W1)) == {-1.0, 1.0}
    assert not np.array_equal(W1, S.rademacher(8, seed=1))
    assert abs(W1.mean()) < 0.01
    a, b = S.boot_ci(x, W1), S.boot_ci(x, W2)
    assert a == b
    # each draw: the mean over runs of Dbar + w_r (D_r - Dbar); then the 2.5th and 97.5th percentiles
    dbar = x.mean()
    draws = np.array([np.mean([dbar + w * (xr - dbar) for w, xr in zip(row, x)]) for row in W1])
    assert (a["lo"], a["hi"]) == pytest.approx(tuple(np.percentile(draws, [2.5, 97.5])), abs=1e-12)
    assert a["mean"] == pytest.approx(dbar) and a["lo"] < a["mean"] < a["hi"]
    x24 = np.random.default_rng(0).normal(0.3, 0.1, 24)       # 8 runs allow only 256 sign patterns; 24 are the study's
    assert S.boot_ci(x24, S.rademacher(24)) == S.boot_ci(x24, S.rademacher(24))
    assert S.boot_ci(x24, S.rademacher(24)) != S.boot_ci(x24, S.rademacher(24, seed=1))
    flat = S.boot_ci(np.full(8, 0.3), W1)
    assert flat["lo"] == pytest.approx(0.3) and flat["hi"] == pytest.approx(0.3)
    # pinned values: Generator streams are stable across numpy versions, so a change shows here
    assert W1[0].tolist() == [1.0, -1.0, 1.0, 1.0, 1.0, -1.0, -1.0, -1.0]
    assert (a["lo"], a["hi"]) == pytest.approx((0.225, 0.335), abs=1e-9)


@pytest.mark.skipif(not FARM_OK, reason="bench farm /tmp/cvp_review missing")
def test_rho_copy_equals_audit_rho():
    _, src = S.get_rho()
    assert src == "audit.rho"
    au = F.reg()["au"]
    rng = np.random.default_rng(0)
    for _ in range(20):
        a, b = rng.integers(0, 5, 30), rng.normal(size=30)
        assert S._rho_copy(a, b) == au.rho(a, b)
    assert S._rho_copy(np.ones(5), np.arange(5)) is None and au.rho(np.ones(5), np.arange(5)) is None


# ------------------------------------------------------------------------------ two real stages

def _two_real_stages():
    reg_rows = [json.loads(l) for l in open(LPD / "review_2026-10-29" / "bench" / "build" / "stages.jsonl")]
    ok = [r for r in reg_rows if "error" not in r and "drop" not in r and "yard" in r and r.get("secs")]
    out = []
    for scene in ("00853", "00871"):
        c = [r for r in ok if r["scene"] == scene]
        out.append(min(c, key=lambda r: r["secs"]))
    return out


@pytest.mark.skipif(not FARM_OK, reason="bench farm /tmp/cvp_review missing (run m2/rebuild_bench.sh --no-run)")
@pytest.mark.parametrize("which", [0, 1])
def test_real_stage_shapes_and_bench_equality(which, tmp_path):
    reg_row = _two_real_stages()[which]
    R = F.reg()
    rp = R["rp"]
    run, k = reg_row["run"], reg_row["stage"]
    meta = rp.stage_meta(run)[k]
    t0 = time.time()
    ctx = F.stage_context(run, k, meta)
    t_ctx = time.time() - t0
    assert "drop" not in ctx and ctx["n_cand"] == reg_row["n_cand"] and ctx["gids"] == reg_row["gids"]
    n = ctx["n_cand"]
    # the yardsticks are the bench's own arrays (U360 may differ by 1 on a few candidates on another numpy)
    for y_name in ("Uwall", "Ucone"):
        assert ctx["yard"][y_name].tolist() == reg_row[y_name]
    diff = np.abs(ctx["yard"]["U360"] - np.array(reg_row["U360"]))
    assert diff.max() <= 1 and (diff > 0).sum() <= 15
    aud = {(r["run"], r["stage"]): r for r in map(json.loads, open(LPD / "review_2026-10-29" / "audit" / "audit" / "stages.jsonl"))}
    assert ctx["yard"]["Ucone_audit"].mean() == pytest.approx(aud[(run, k)]["Ucone_mean"])   # the audit's own U_cone
    assert ctx["d"].shape == (n,)
    arms = ["F1", "F5a", "F5b", "F6", "F0", "F3-deepseek", "F-room"]
    sample = np.array([0.5, 1.0, 2.0])
    sets = F.build_sets(ctx, arms, {"deepseek": sample}, str(tmp_path / "w"))
    assert set(sets) == set(arms)
    gids = ctx["gids"]
    for name in arms:
        assert len(sets[name]["files"]) == len(sets[name]["graphs"]) == len(sets[name]["n_obj"]) == len(gids)   # one per id
    # seeds: the bench's own keys for F1 and F5, and the oracle draws
    for name, bname in (("F1", "oracle"), ("F5a", "placebo_A"), ("F5b", "placebo_B")):
        assert sets[name]["info"]["seeds"] == reg_row["seeds"][bname]
    assert sets["F1"]["info"]["oracle_info"] == reg_row["oracle_info"]
    scored = F.score_sets(ctx, sets)
    for name in arms:
        assert scored[name]["ig"].shape == (n,) and scored[name]["score"].shape == (n,)
        assert np.all(np.isfinite(scored[name]["score"]))
        assert np.allclose(scored[name]["score"], scored[name]["ig"] - 0.2 * ctx["d"])
    # F1, F5, F6 equal the bench's own sets: the R1 pick of each is the registered pick
    for name, bname in (("F1", "oracle"), ("F5a", "placebo_A"), ("F5b", "placebo_B"), ("F6", "none")):
        assert int(np.argmax(scored[name]["score"])) == reg_row["picks"][bname]["R1"], name
    assert all(f == ctx["obs_paths"][g // 4] for f, g in zip(sets["F6"]["files"], gids))     # F6: the track's observed graph
    # F0: one graph per track, every unmapped reference object at its true place
    by_track = {}
    for g, gr in zip(gids, sets["F0"]["graphs"]):
        by_track.setdefault(g // 4, []).append(gr)
    for t, grs in by_track.items():
        assert all(gr == grs[0] for gr in grs)
        new = [x for x in grs[0]["nodes"] if x["id"] not in ctx["obs_ids"][t] and x["node_type"] == "object"]
        assert len(new) == ctx["n_unmapped"]
    # F3: the F1 objects, each moved by a sample distance (to the 3-decimal text); fallback members not moved
    f3info = sets["F3-deepseek"]["info"]["per_member"]
    for g1, g3, orc in zip(sets["F1"]["graphs"], sets["F3-deepseek"]["graphs"], sets["F1"]["info"]["oracle_info"]):
        assert len(g1["nodes"]) == len(g3["nodes"]) and g1["edges"] == g3["edges"]
        for a, b in zip(g1["nodes"], g3["nodes"]):
            if a["node_type"] == "object" and a.get("is_predicted") and not orc["fallback"]:
                va, vb = LP._vec(a["position"]), LP._vec(b["position"])
                assert min(abs(math.hypot(vb[0] - va[0], vb[1] - va[1]) - s) for s in sample) < 3e-3
                assert va[2] == vb[2] and a["id"] == b["id"] and a["name"] == b["name"]
            else:
                assert a == b
    assert [p["fallback"] for p in f3info] == [o["fallback"] for o in sets["F1"]["info"]["oracle_info"]]
    # F-room: N equals the F1 count; an unseen typed region or the F6 graph; placebo's YAML shape
    for g, gr, p, n1 in zip(gids, sets["F-room"]["graphs"], sets["F-room"]["info"]["per_member"], sets["F1"]["n_obj"]):
        assert set(gr) == {"nodes", "edges"} and p["n_target"] == n1
        new = [x for x in gr["nodes"] if x["id"] not in ctx["obs_ids"][g // 4]]
        if p["no_unseen_typed"]:
            assert gr == ctx["obs_graph"][g // 4]
            continue
        assert all(x["name"] in F.FROOM_ROOM_NAME.values() for x in new if x["node_type"] == "room")
        assert all(x.get("is_predicted") is True for x in new if x["node_type"] == "object")
        assert p["n_objects"] in (0, n1) and len([x for x in new if x["node_type"] == "object"]) == p["n_objects"]
    # timing only (no correlation, no regret)
    print(f"\n[shape check] {run}:{k} n_cand={n} members={len(gids)} n_unmapped={ctx['n_unmapped']} context {t_ctx:.1f}s "
          + " ".join(f"{a}={scored[a]['secs']}s" for a in arms)
          + f" objects/member F1={sets['F1']['n_obj']} F0={sets['F0']['n_obj']} F-room={sets['F-room']['n_obj']}"
          + f" bench stage secs={reg_row['secs']}")


# ------------------------------------------------------------------------------ a failed or incomplete pass

ARMS_FIRST = ["F1", "F5a", "F5b", "F6", "F0", "F3-deepseek", "F-room"]


def _write_pass(folder, rows, arms=ARMS_FIRST, n_jobs=None, marker=True, truncate=False):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "factorial_meta.json").write_text(json.dumps({"n_jobs": len(rows) if n_jobs is None else n_jobs, "arms": arms}))
    text = "\n".join(json.dumps(r) for r in rows) + "\n"
    if truncate:
        text = text[:-40]                                      # the last line is cut
    (folder / "factorial_stages.jsonl").write_text(text)
    if marker:
        F.pc().write_marker(folder)
    return folder / "factorial_stages.jsonl"


def test_a_stage_that_raises_leaves_an_error_row_and_no_marker(tmp_path, monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("stage exploded")
    monkeypatch.setattr(F, "run_stage", boom)
    monkeypatch.setattr(F, "_CFG", {"arms": ["F1"], "samples": {}, "workdir": str(tmp_path)})
    err = F.job(("e1_00853_s42_official_60m", 3, {}))
    assert "error" in err and "stage exploded" in err["error"]
    rows = _rows(_spec(), n_runs=2, n_stages=2, seed=1)
    rows[1] = err                                              # one stage failed in a pass of four
    p = _write_pass(tmp_path / "p", rows, marker=False)
    problems = F.pc().problems(tmp_path / "p")
    assert any("error row" in x for x in problems)
    with pytest.raises(SystemExit) as e:
        F.finish_pass(tmp_path / "p")
    assert e.value.code == 1 and not (tmp_path / "p" / "PASS_COMPLETE").exists()
    assert "PASS FAILED" in capsys.readouterr().out
    # the summary refuses, exits non-zero and freezes no left-out list
    with pytest.raises(SystemExit) as e:
        S.main([str(p), "--left-out", str(tmp_path / "lo.json"), "--out", str(tmp_path / "s.json")])
    assert e.value.code == 2 and not (tmp_path / "lo.json").exists() and not (tmp_path / "s.json").exists()
    assert "REFUSED" in capsys.readouterr().err
    # even a forged marker does not help: the rows themselves are checked
    (tmp_path / "p" / "PASS_COMPLETE").write_text(json.dumps({"sha256": F.pc().sha256_file(p)}))
    with pytest.raises(SystemExit):
        S.main([str(p), "--left-out", str(tmp_path / "lo.json"), "--out", str(tmp_path / "s.json")])
    with pytest.raises(S.IncompleteData):
        S.summarise(rows, rho=S._rho_copy)                     # and so does the function


def test_a_drop_row_or_a_row_without_an_asked_for_arm_is_not_complete(tmp_path):
    rows = _rows(_spec(), n_runs=2, n_stages=2, seed=1)
    rows[0] = {"run": "r00", "stage": 0, "drop": "top10 mismatch"}
    assert any("drop row" in x for x in F.pc().problems(_write_pass(tmp_path / "a", rows, marker=False).parent))
    rows = _rows(_spec(), n_runs=2, n_stages=2, seed=1)
    del rows[2]["arms"]["F-room"]
    assert any("lacks arm" in x for x in F.pc().problems(_write_pass(tmp_path / "b", rows, marker=False).parent))
    rows = _rows(_spec(), n_runs=2, n_stages=2, seed=1)
    rows.append(rows[0])                                       # a duplicate row
    assert any("duplicate" in x for x in F.pc().problems(_write_pass(tmp_path / "c", rows, n_jobs=5, marker=False).parent))


def test_a_truncated_jsonl_is_not_complete(tmp_path, capsys):
    rows = _rows(_spec(), n_runs=2, n_stages=3, seed=1)
    p = _write_pass(tmp_path / "t", rows, marker=False, truncate=True)
    probs = F.pc().problems(p.parent)
    assert any("unreadable" in x for x in probs) and any("holds 5 rows" in x for x in probs)
    with pytest.raises(SystemExit):
        F.finish_pass(p.parent)
    assert not (p.parent / "PASS_COMPLETE").exists()
    # fewer rows than the meta says, with every line whole
    p2 = _write_pass(tmp_path / "t2", rows[:4], n_jobs=6, marker=False)
    assert any("holds 4 rows" in x for x in F.pc().problems(p2.parent))
    with pytest.raises(SystemExit):
        S.main([str(p2), "--left-out", str(tmp_path / "lo.json"), "--out", str(tmp_path / "s.json")])
    assert not (tmp_path / "lo.json").exists()


def test_a_complete_pass_gets_its_marker_and_is_summarised(tmp_path, capsys):
    rows = _rows(_spec(), n_runs=4, n_stages=3, seed=1)
    p = _write_pass(tmp_path / "ok", rows)                     # write_marker checks, then writes
    assert (p.parent / "PASS_COMPLETE").exists() and F.pc().problems(p.parent) == []
    S.main([str(p), "--left-out", str(tmp_path / "lo.json"), "--out", str(tmp_path / "s.json")])
    assert (tmp_path / "lo.json").exists() and (tmp_path / "s.json").exists()
    p.write_text(p.read_text() + "\n")                         # any change after the marker is caught
    p.write_text(p.read_text().replace("0.", "1.", 1))
    with pytest.raises(SystemExit):
        S.main([str(p), "--left-out", str(tmp_path / "lo2.json"), "--out", str(tmp_path / "s2.json")])


def test_a_later_pass_with_an_error_row_cannot_replace_the_first_pass_row(tmp_path, capsys):
    first = _rows(_spec(), n_runs=4, n_stages=3, seed=2)
    p1 = _write_pass(tmp_path / "pass1", first)
    S.main([str(p1), "--left-out", str(tmp_path / "pass1" / "left_out_stages.json"), "--out", str(tmp_path / "s1.json")])
    later_arms = ["F3-haiku", "F3-opus"]
    later = _rows({"F3-haiku": half, "F3-opus": noise}, n_runs=4, n_stages=3, seed=2)
    for a, b in zip(later, first):
        a["yard"], a["d"] = b["yard"], b["d"]
    # (a) the later pass has no marker: refused
    p2 = _write_pass(tmp_path / "pass2", later, arms=later_arms, marker=False)
    lo = str(tmp_path / "pass1" / "left_out_stages.json")
    with pytest.raises(SystemExit) as e:
        S.main([str(p1), str(p2), "--left-out", lo, "--out", str(tmp_path / "s2.json")])
    assert e.value.code == 2
    # (b) one stage of the later pass raised: an error row, even with a forged marker
    later[3] = {"run": later[3]["run"], "stage": later[3]["stage"], "error": "RuntimeError('x')"}
    p2 = _write_pass(tmp_path / "pass2", later, arms=later_arms, marker=False)
    (tmp_path / "pass2" / "PASS_COMPLETE").write_text(json.dumps({"sha256": F.pc().sha256_file(p2)}))
    with pytest.raises(SystemExit) as e:
        S.main([str(p1), str(p2), "--left-out", lo, "--out", str(tmp_path / "s2.json")])
    assert e.value.code == 2 and "error row" in capsys.readouterr().err
    assert not (tmp_path / "s2.json").exists()
    # (c) a whole later pass is accepted
    later2 = _rows({"F3-haiku": half, "F3-opus": noise}, n_runs=4, n_stages=3, seed=2)
    for a, b in zip(later2, first):
        a["yard"], a["d"] = b["yard"], b["d"]
    shutil_rm = __import__("shutil").rmtree
    shutil_rm(tmp_path / "pass2")
    p2 = _write_pass(tmp_path / "pass2", later2, arms=later_arms)
    S.main([str(p1), str(p2), "--left-out", lo, "--out", str(tmp_path / "s2.json")])
    assert "B_haiku" in json.loads((tmp_path / "s2.json").read_text())["analysis"]["main"]["all"]["differences"]


def test_the_later_runner_refuses_without_the_first_pass_marker(tmp_path):
    import subprocess
    (tmp_path / "m2" / "pass1").mkdir(parents=True)
    (tmp_path / "m2" / "pass1" / "left_out_stages.json").write_text("{}")
    (tmp_path / "m2" / "pass1" / "factorial_stages.jsonl").write_text("{}\n")
    for n in ("h.json", "o.json"):
        (tmp_path / n).write_text("[1.0]")
    env = {**os.environ, "M2_ROOT": str(tmp_path)}
    r = subprocess.run(["bash", str(M2 / "run_m2_pass.sh"), "later", str(tmp_path / "h.json"), str(tmp_path / "o.json")],
                       env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "PASS_COMPLETE" in r.stderr
    assert not (tmp_path / "m2" / "pass2").exists()            # nothing started


def test_watchdog_fails_a_pass_whose_rows_stop_coming():
    from multiprocessing.pool import ThreadPool
    import time as _t

    def slow(x):
        _t.sleep(0.05 if x < 2 else 5)
        return x
    got = []
    with ThreadPool(2) as pool:
        with pytest.raises(F.PassStalled):
            F.drain(pool.imap_unordered(slow, [0, 1, 2, 3]), lambda i, r: got.append(r), 4, 0.5)
        pool.terminate()
    assert sorted(got) == [0, 1]
    with ThreadPool(2) as pool:                                # a healthy run drains all its rows
        got = []
        F.drain(pool.imap_unordered(lambda x: x, [0, 1, 2, 3]), lambda i, r: got.append(r), 4, 5)
    assert sorted(got) == [0, 1, 2, 3]
    assert F.WATCHDOG_S == 900


def test_detector_label_fails_loudly_without_the_table():
    class NoTable(FakeLabels):
        pass
    NoTable._DETECTOR_LABEL = {}
    with pytest.raises(RuntimeError, match="_DETECTOR_LABEL"):
        F.detector_label_of("bed", NoTable)

    class Gone:
        detector_vocab = staticmethod(FakeLabels.detector_vocab)
        normalise = staticmethod(FakeLabels.normalise)
        answers_to = staticmethod(FakeLabels.answers_to)
    with pytest.raises(RuntimeError, match="_DETECTOR_LABEL"):
        F.detector_label_of("bed", Gone)
    assert F.detector_label_of("bed", FakeLabels) == "duvet"


def test_a_kept_stage_without_a_value_for_a_later_arm_is_counted_and_paired():
    spec = {**_spec(), "F3-haiku": half}
    rows = _rows(spec, n_runs=4, n_stages=4, seed=9)
    first = {k: v for k, v in rows[0]["arms"].items()}
    rows[5]["arms"]["F3-haiku"]["score"] = [2.0] * 40          # haiku undefined at one stage the list keeps
    keys = {x for x in S.EXCLUSION_ARMS}
    lo = S.compute_left_out([{**r, "arms": {k: v for k, v in r["arms"].items() if k != "F3-haiku"}} for r in rows], S._rho_copy)
    assert lo["n_left_out"] == 0
    res = S.summarise(rows, rho=S._rho_copy, left_out_path=None)
    a = res["analysis"]["main"]["all"]
    assert a["kept_stages_without_value_by_arm"]["F3-haiku"] == 1 and a["kept_stages_without_value_by_arm"]["F1"] == 0
    pb = a["paired_where_defined"]["B_haiku"]
    assert pb["n_kept_stages_without_value"] == 1
    # A and X - 0.5 A on the stages where haiku is defined, by hand
    per_run = {}
    for r in rows:
        rr = S.stage_rho(r, "score", "Ucone", S._rho_copy)
        if rr["F3-haiku"] is None:
            continue
        per_run.setdefault(r["run"], []).append((rr["F1"] - rr["F5"], (rr["F3-haiku"] - rr["F5"]) - 0.5 * (rr["F1"] - rr["F5"])))
    assert pb["A"]["mean"] == pytest.approx(np.mean([np.mean([x[0] for x in v]) for v in per_run.values()]))
    assert pb["X_minus_half_A"]["mean"] == pytest.approx(np.mean([np.mean([x[1] for x in v]) for v in per_run.values()]))
    assert pb["reading"]["step"] in (1, 2)
    assert a["paired_where_defined"]["C"]["n_kept_stages_without_value"] == 0
    # with no missing stage the paired figures equal the main ones
    same = res["analysis"]["main"]["all"]["paired_where_defined"]["B_deepseek"]["X_minus_half_A"]["mean"]
    assert same == pytest.approx(a["reading_series"]["B_deepseek"]["mean"])
