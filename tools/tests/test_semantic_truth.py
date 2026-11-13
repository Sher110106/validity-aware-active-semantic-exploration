"""Tests for semantic/region_truth.py and semantic/extract_preds.py.

Synthetic houses only, built in a temp folder, with a fake label layer. The last test is a smoke
check on the real saved data: it prints counts of rows, members, new rooms and new objects, and
makes no comparison of guesses with truth. Modules load by file path (see region_truth.py).
"""
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

HERE = Path(__file__).resolve().parent
SEM = HERE.parent / "live_policy" / "semantic"


def _load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, SEM / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


# the same alias the modules use for model.py, so that dataclasses are one set of classes
M = sys.modules.get("semantic_model") or _load("model", "semantic_model")
rt = _load("region_truth", "semantic_region_truth_under_test")
ep = _load("extract_preds", "semantic_extract_preds_under_test")


# ------------------------------------------------------------------------------ fake labels

class FakeLabels:
    STRUCT = {"wall", "floor", "door"}
    TABLE = {"bed": "bed", "nightstand": "nightstand", "toilet": "toilet", "sink": "sink",
             "sofa": "sofa", "oven": "oven", "stove": "stove", "lamp": "lamp", "chair": "chair",
             "cabinet": "cabinet", "washer": "washer", "table": "table", "bedside lamp": "lamp",
             "wall": "wall", "floor": "floor", "door": "door", "duvet": "duvet", "shower door": "door"}
    DETECTOR = {"bed": "duvet"}     # the detector's own word for an annotated name (a bed is a "duvet")

    @staticmethod
    def answers_to(raw_name):
        names = {raw_name.lower(), FakeLabels.DETECTOR.get(raw_name.lower(), raw_name.lower())}
        cs = {FakeLabels.normalise(n) for n in names}
        return frozenset(c for c in cs if c is not None and c not in FakeLabels.STRUCT)
    MARKERS = {"bathroom": [("toilet",), ("bathtub",), ("shower",)], "bedroom": [("bed",)],
               "kitchen": [("oven",), ("stove",), ("stovetop",)],
               "laundry": [("washing", "machine"), ("washer",), ("dryer",)],
               "living": [("couch",), ("sofa",)], "dining": [("dining", "table")]}

    @staticmethod
    def normalise(label):
        return FakeLabels.TABLE.get(label.lower().replace("_", " ").strip())  # "shower floor", "stovetop": None

    @staticmethod
    def is_structure(canon):
        return canon in FakeLabels.STRUCT

    @staticmethod
    def room_type(name):
        s = name.lower().replace("_", " ").replace("-", " ")
        words = s.split()
        if any(k in s for k in ("bath", "toilet", "restroom", "washroom", "shower")) or "wc" in words:
            return "bathroom"
        if "bed" in s:
            return "bedroom"
        if "kitchen" in s:
            return "kitchen"
        if "laundry" in s or "utility" in s:
            return "laundry"
        if any(k in s for k in ("living", "lounge", "family", "sitting")):
            return "living"
        if "dining" in s:
            return "dining"
        return None

    @staticmethod
    def marker_types(raw_name):
        w = raw_name.lower().split()
        out = set()
        for t, pats in FakeLabels.MARKERS.items():
            for pat in pats:
                n = len(pat)
                if any(tuple(w[i:i + n]) == pat for i in range(len(w) - n + 1)):
                    out.add(t)
        return frozenset(out)


@pytest.fixture(autouse=True)
def fake_labels(monkeypatch):
    monkeypatch.setattr(rt, "labels", FakeLabels)
    monkeypatch.setattr(ep, "labels", FakeLabels)
    ep.SKIPPED.clear()


# --------------------------------------------------------------------------- synthetic house
#
# Grid 100 x 100 cells of 0.05 m, origin (0, 0). Regions (x range, y range in metres):
#   1 bathroom  cells ix 0..39  iy 0..39   x 0.00-2.00  y 0.00-2.00
#   2 bedroom   cells ix 39..79 iy 0..39   x 1.95-4.00  y 0.00-2.00   (shares column 39 with region 1)
#   3 kitchen   cells ix 0..39  iy 50..79  x 0.00-2.00  y 2.50-4.00   (0.5 m gap above region 1)
#   4 other     cells ix 60..99 iy 50..99  x 3.00-5.00  y 2.50-5.00
# Floor masks are smaller than the `any` masks (the `any` mask takes in the walls):
#   1 floor     iy 0..34 (rows 35..39, y 1.75-2.00, are `any` only)
#   2 floor     ix 39..79, iy 0..34   (column 39 is in the floors of both 1 and 2)
#   3 floor     none: the `any` mask is used
#   4 floor     ix 65..99 (columns 60..64, x 3.00-3.25, are `any` only)

def _mask(ix0, ix1, iy0, iy1):
    m = np.zeros((100, 100), dtype=bool)
    m[iy0:iy1 + 1, ix0:ix1 + 1] = True
    return m


def _obj(oid, name, region, centre=None, size=0.2):
    d = {"id": oid, "name": name, "region": region, "n_tri": 0}
    if centre is not None:
        d.update(n_tri=12, world_min=[centre[0] - size / 2, centre[1] - size / 2, 0.0],
                 world_max=[centre[0] + size / 2, centre[1] + size / 2, 1.0])
    return d


OBJECTS = [
    _obj(1, "toilet", 1, (0.5, 0.5)),
    _obj(2, "shower floor", 1),                    # marker, no geometry, no canonical class
    _obj(3, "sink", 1, (1.5, 0.5)),
    _obj(4, "wall", 1, (0.0, 1.0)),                # structure: never a reference object
    _obj(5, "shower door", 1, (0.2, 1.5)),         # marker with geometry that answers only to a structure class
    _obj(10, "bed", 2, (3.0, 1.0)),
    _obj(11, "nightstand", 2, (3.5, 0.5)),
    _obj(12, "bedside lamp", 2, (3.2, 1.5)),       # marks nothing
    _obj(20, "oven", 3, (0.5, 3.0)),
    _obj(21, "stove", 3, (1.0, 3.0)),
    _obj(22, "stovetop", 3, (1.5, 3.0)),           # marker with geometry but no canonical class
    _obj(23, "washer", 3),                         # marker with a class but no geometry
    _obj(24, "cabinet", 3, (1.8, 3.5)),
    _obj(30, "chair", 4, (3.5, 3.0)),
    _obj(31, "lamp", 4, (4.0, 4.0)),
]


@pytest.fixture()
def truth(tmp_path):
    masks = np.stack([_mask(0, 39, 0, 39), _mask(39, 79, 0, 39), _mask(0, 39, 50, 79), _mask(60, 99, 50, 99)])
    floors = np.stack([_mask(0, 39, 0, 34), _mask(39, 79, 0, 34), np.zeros((100, 100), dtype=bool),
                       _mask(65, 99, 50, 99)])
    np.savez(tmp_path / "99999_region_footprints.npz", scene=np.array("99999"),
             origin_xy=np.array([0.0, 0.0]), cell_size=np.array(0.05), axis_names=np.array(["x", "y"]),
             vertical_axis=np.array("z"), region_ids=np.array([1, 2, 3, 4]), floor_masks=floors,
             any_masks=masks, habitat_to_world_R=np.eye(3), habitat_to_world_t=np.zeros(3))
    (tmp_path / "99999_semantic_geometry.json").write_text(json.dumps(
        {"scene": "99999", "n_objects": len(OBJECTS), "objects": {str(o["id"]): o for o in OBJECTS}}))
    # region 4 has no centroid field; the others carry one that is not the footprint centre
    (tmp_path / "99999_regions.json").write_text(json.dumps(
        {"scene": "99999", "regions": [{"region_id": r, "centroid_xy": [r + 0.25, 7.0]} for r in (1, 2, 3)]
         + [{"region_id": 4}]}))
    return rt.load_scene_truth("99999", truth_dir=tmp_path)


# --------------------------------------------------------------------------- geometry rules

def test_inside_edges_and_overlap(truth):
    assert truth.inside((0.01, 0.01)) == {1}
    assert truth.inside((0.0, 0.0)) == {1}                    # lower edge belongs to the cell it opens
    assert truth.inside((1.97, 1.0)) == {1, 2}                # column 39 is in both footprints
    assert truth.inside((1.9499999, 1.0)) == {1}              # column 38
    assert truth.inside((2.0, 1.0)) == {2}                    # column 40: region 2 only
    assert truth.inside((1.0, 1.9999)) == {1}                 # last row of region 1
    assert truth.inside((1.0, 2.0)) == frozenset()            # the gap
    assert truth.inside((-0.01, 1.0)) == frozenset()          # outside the grid
    assert truth.inside((50.0, 50.0)) == frozenset()


def test_distance_is_zero_inside_and_exact_outside(truth):
    assert truth.distance((1.0, 1.0), 1) == 0.0
    assert truth.distance((1.97, 1.0), 1) == 0.0 and truth.distance((1.97, 1.0), 2) == 0.0   # overlap
    assert truth.distance((1.0, 2.2), 1) == pytest.approx(0.2)
    assert truth.distance((1.0, 2.2), 3) == pytest.approx(0.3)
    assert truth.distance((-0.3, 1.0), 1) == pytest.approx(0.3)           # outside the grid
    assert truth.distance((-0.3, -0.4), 1) == pytest.approx(0.5)          # off the corner
    assert truth.distance((-50.0, 1.0), 1) == pytest.approx(50.0)
    assert truth.distance((0.001, 0.001), 3) > 2.0
    with pytest.raises(KeyError):
        truth.distance((0, 0), 77)


def test_reaches_at_half_a_metre(truth):
    assert truth.reaches((1.0, 1.0)) == {1}
    assert truth.reaches((1.97, 1.0)) == {1, 2}
    assert truth.reaches((-0.49, 1.0)) == {1}                 # outside the grid, 0.49 m away
    assert truth.reaches((-0.51, 1.0)) == frozenset()
    assert truth.reaches((-0.3, -0.3)) == {1}                 # 0.42 m off the corner
    assert truth.reaches((-0.4, -0.4)) == frozenset()         # 0.57 m off the corner
    assert truth.reaches((1.0, 2.2)) == {1, 3}                # inside the gap: both within 0.5 m
    assert truth.reaches((1.0, 2.2)) >= truth.inside((1.0, 2.2))
    assert truth.reaches((2.8, 3.0)) == {4}                   # 0.2 m from region 4; region 3 is 0.8 away


def test_nonfinite_point_is_an_error(truth):
    with pytest.raises(ValueError):
        truth.inside((float("nan"), 0.0))


# --------------------------------------------------------------------------- region contents

def test_region_types_from_markers(truth):
    R = truth.regions
    assert R[1].types == {"bathroom"}                       # toilet; "shower floor" has no geometry
    assert {m.object_id for m in R[1].markers} == {1, 2, 5}
    assert R[2].types == {"bedroom"}                        # "bedside lamp" marks nothing
    assert {m.object_id for m in R[2].markers} == {10}
    assert R[3].types == {"kitchen", "laundry"}             # a region carries every type it has a marker for
    assert R[4].types == frozenset()                        # "other"


def test_markers_carry_answers_to(truth):
    m = {x.object_id: x for x in truth.regions[1].markers}
    assert m[1].answers_to == {"toilet"} and m[1].xy == pytest.approx((0.5, 0.5))
    assert m[2].xy is None and m[2].answers_to == frozenset() and m[2].types == {"bathroom"}
    assert m[5].xy == pytest.approx((0.2, 1.5)) and m[5].answers_to == frozenset()   # "door" is structure
    m3 = {x.object_id: x for x in truth.regions[3].markers}
    assert m3[23].xy is None and m3[23].answers_to == {"washer"}
    assert m3[22].xy == pytest.approx((1.5, 3.0)) and m3[22].answers_to == frozenset()
    assert m3[20].answers_to == {"oven"} and m3[20].xy == pytest.approx((0.5, 3.0))
    m2 = {x.object_id: x for x in truth.regions[2].markers}
    assert m2[10].answers_to == {"bed", "duvet"}            # the detector calls a bed a duvet


def test_reference_objects(truth):
    ref = {r: {o.object_id for o in reg.ref_objects} for r, reg in truth.regions.items()}
    assert ref[1] == {1, 3}                  # no wall; no "shower floor" (no geometry); no "shower door" (structure only)
    assert ref[2] == {10, 11, 12}
    assert ref[3] == {20, 21, 24}            # no stovetop (answers to nothing), no washer (no geometry)
    assert ref[4] == {30, 31}
    assert all(o.answers_to for reg in truth.regions.values() for o in reg.ref_objects)
    bed = next(o for o in truth.regions[2].ref_objects if o.object_id == 10)
    assert bed.canon == "bed" and bed.answers_to == {"bed", "duvet"}
    assert bed.marker_of == {"bedroom"} and bed.xy == pytest.approx((3.0, 1.0))
    lamp = next(o for o in truth.regions[2].ref_objects if o.object_id == 12)
    assert lamp.canon == "lamp" and lamp.answers_to == {"lamp"} and lamp.marker_of == frozenset()


def test_structure_classes_never_survive_in_answers_to(monkeypatch):
    class Leaky(FakeLabels):
        answers_to = staticmethod(lambda name: frozenset({"wall", "bed", "duvet", "door"}))
    monkeypatch.setattr(rt, "labels", Leaky)
    assert rt._answers_to("anything") == {"bed", "duvet"}


def test_centroid_is_the_regions_json_field(truth):
    assert truth.regions[1].centroid_xy == pytest.approx((1.25, 7.0))
    assert truth.regions[3].centroid_xy == pytest.approx((3.25, 7.0))
    assert truth.regions[4].centroid_xy == pytest.approx((4.0, 3.75))   # field absent: footprint centre


def test_inside_floor_uses_the_floor_mask_and_falls_back_to_any(truth):
    assert truth.inside_floor((1.0, 1.0)) == {1}
    assert truth.inside((1.0, 1.9)) == {1} and truth.inside_floor((1.0, 1.9)) == frozenset()   # `any` only (rows 35..39)
    assert truth.inside_floor((1.97, 1.0)) == {1, 2}              # column 39 is in both floors
    assert truth.inside_floor((1.0, 3.0)) == {3}                  # region 3 has no floor: its `any` mask
    assert truth.inside((3.1, 3.0)) == {4} and truth.inside_floor((3.1, 3.0)) == frozenset()
    assert truth.inside_floor((4.0, 3.0)) == {4}
    assert truth.inside_floor((-1.0, 1.0)) == frozenset()         # outside the grid
    assert truth.regions_without_floor == [3]
    # reaches() is unchanged: it follows the `any` mask
    assert truth.reaches((1.0, 1.9)) == {1}


# ------------------------------------------------------------------------------- stage state

def N(nid, kind, name, xy, canon=None, rtype=None, flag=None):
    return M.Node(node_id=nid, kind=kind, name=name, xy=xy, z=0.5, is_predicted=flag, room_type=rtype, canon=canon)


def mk_row(objects=(), rooms=(), path=()):
    obs = M.ObservedGraph(rooms=tuple(rooms), objects=tuple(objects),
                          node_ids=frozenset(n.node_id for n in list(rooms) + list(objects)))
    return M.Row(row_id="t", scene="99999", seed=1, arm="official", stage=3, cluster="99999_s1_official",
                 round=1, is_gemini_row=False, observed=obs, path_xy=tuple(path))


def test_nothing_seen_everything_open(truth):
    st = rt.stage_state(truth, mk_row())
    assert st.seen == frozenset() and st.partly_seen == frozenset() and st.unobserved == {1, 2, 3, 4}
    assert st.unseen == {1, 2, 3, 4}
    assert st.mapped_objects == frozenset()
    assert st.open_types == {"bathroom", "bedroom", "kitchen", "laundry"}
    assert st.open_types_loose == st.open_types
    # a bed answers to bed and to duvet
    assert st.open_classes == {"toilet", "sink", "bed", "duvet", "nightstand", "lamp", "oven", "stove", "cabinet", "chair"}
    assert st.open_classes_loose == st.open_classes


def test_bed_mapped_by_a_duvet_node(truth):
    st = rt.stage_state(truth, mk_row(objects=[N(1, "object", "duvet", (3.0, 1.0), canon="duvet")]))
    assert 10 in st.mapped_objects                          # the detector's word maps the annotated bed
    assert st.partly_seen == {2}
    assert "bed" not in st.open_classes and "duvet" not in st.open_classes   # both closed by the one mapped bed
    assert "bed" in st.open_classes_loose and "duvet" in st.open_classes_loose
    assert "bedroom" not in st.open_types                    # the bed is the region's only bedroom marker
    far = rt.stage_state(truth, mk_row(objects=[N(1, "object", "duvet", (3.0, 1.51), canon="duvet")]))
    assert 10 not in far.mapped_objects and {"bed", "duvet"} <= far.open_classes


def test_mapped_at_049_not_at_051_not_by_other_class(truth):
    near = rt.stage_state(truth, mk_row(objects=[N(1, "object", "bed", (3.49, 1.0), canon="bed")]))
    far = rt.stage_state(truth, mk_row(objects=[N(1, "object", "bed", (3.51, 1.0), canon="bed")]))
    other = rt.stage_state(truth, mk_row(objects=[N(1, "object", "nightstand", (3.0, 1.0), canon="nightstand")]))
    diag = rt.stage_state(truth, mk_row(objects=[N(1, "object", "bed", (3.0 + 0.35, 1.0 + 0.35), canon="bed")]))
    nocanon = rt.stage_state(truth, mk_row(objects=[N(1, "object", "bed", (3.0, 1.0), canon=None)]))
    assert 10 in near.mapped_objects
    assert 10 not in far.mapped_objects
    assert 10 not in other.mapped_objects                   # the nightstand node maps the nightstand, not the bed
    assert 10 in diag.mapped_objects                        # hypot(0.35, 0.35) = 0.495 -> mapped
    assert 10 not in nocanon.mapped_objects


def test_only_object_nodes_map(truth):
    # a node that is not of kind "object" never maps, whatever its class
    st = rt.stage_state(truth, mk_row(objects=[N(1, "room", "bed", (3.0, 1.0), canon="bed")]))
    assert st.mapped_objects == frozenset()


def test_diagonal_distance_is_euclidean(truth):
    inside = rt.stage_state(truth, mk_row(objects=[N(1, "object", "bed", (3.3, 1.3), canon="bed")]))   # 0.424 m
    outside = rt.stage_state(truth, mk_row(objects=[N(1, "object", "bed", (3.4, 1.4), canon="bed")]))  # 0.566 m
    assert 10 in inside.mapped_objects and 10 not in outside.mapped_objects


def test_seen_by_a_path_point(truth):
    st = rt.stage_state(truth, mk_row(path=[(1.0, 1.0)]))
    assert st.seen == {1} and st.unobserved == {2, 3, 4}


def test_path_point_in_the_any_mask_but_not_the_floor_mask_does_not_see(truth):
    st = rt.stage_state(truth, mk_row(path=[(1.0, 1.9), (3.1, 3.0)]))   # wall bands of regions 1 and 4
    assert st.seen == frozenset() and st.partly_seen == frozenset() and st.unobserved == {1, 2, 3, 4}


def test_path_point_in_a_region_without_floor_uses_the_any_mask(truth):
    st = rt.stage_state(truth, mk_row(path=[(1.0, 3.0)]))
    assert st.seen == {3} and st.unobserved == {1, 2, 4}


def test_seen_by_a_path_point_in_an_overlap(truth):
    st = rt.stage_state(truth, mk_row(path=[(1.97, 1.0)]))
    assert st.seen == {1, 2} and st.unobserved == {3, 4}


def test_a_path_point_that_reaches_does_not_see(truth):
    st = rt.stage_state(truth, mk_row(path=[(1.0, 2.2)]))   # inside the gap, within 0.5 m of 1 and 3
    assert st.seen == frozenset() and st.unobserved == {1, 2, 3, 4}


def test_seen_by_a_room_node_inside(truth):
    st = rt.stage_state(truth, mk_row(rooms=[N(100, "room", "bedroom", (3.0, 1.0), rtype="bedroom")]))
    assert st.seen == {2}


def test_room_node_rule_uses_the_any_mask(truth):
    # (1.0, 1.9) is in region 1's `any` mask but not its floor mask: a room node there still sees it
    st = rt.stage_state(truth, mk_row(rooms=[N(100, "room", "x", (1.0, 1.9))]))
    assert st.seen == {1}


def test_seen_by_two_mapped_objects(truth):
    objs = [N(1, "object", "oven", (0.5, 3.0), canon="oven"), N(2, "object", "stove", (1.0, 3.1), canon="stove")]
    st = rt.stage_state(truth, mk_row(objects=objs))
    assert st.seen == {3}
    assert {20, 21} <= st.mapped_objects


def test_two_nodes_for_one_object_do_not_count_twice(truth):
    objs = [N(1, "object", "oven", (0.5, 3.0), canon="oven"), N(2, "object", "oven", (0.55, 3.0), canon="oven")]
    st = rt.stage_state(truth, mk_row(objects=objs))
    assert st.partly_seen == {3} and st.seen == frozenset()


def test_partly_seen_by_one_mapped_object(truth):
    st = rt.stage_state(truth, mk_row(objects=[N(1, "object", "oven", (0.5, 3.0), canon="oven")]))
    assert st.partly_seen == {3} and st.seen == frozenset() and st.unobserved == {1, 2, 4}
    assert st.unseen == {1, 2, 3, 4}


def test_partly_seen_by_a_room_node_within_reach(truth):
    st = rt.stage_state(truth, mk_row(rooms=[N(100, "room", "x", (2.8, 3.0))]))
    assert st.partly_seen == {4} and st.seen == frozenset() and st.unobserved == {1, 2, 3}


def test_room_node_in_a_gap_reaches_two_regions(truth):
    st = rt.stage_state(truth, mk_row(rooms=[N(100, "room", "x", (1.0, 2.2))]))
    assert st.partly_seen == {1, 3} and st.unobserved == {2, 4}


def test_unobserved_otherwise(truth):
    st = rt.stage_state(truth, mk_row(objects=[N(1, "object", "chair", (9.0, 9.0), canon="chair")],
                                      rooms=[N(100, "room", "x", (-5.0, -5.0))], path=[(20.0, 20.0)]))
    assert st.unobserved == {1, 2, 3, 4} and st.seen == frozenset() and st.partly_seen == frozenset()


def test_open_type_needs_an_unmapped_marker_in_an_unseen_region(truth):
    # the bed is mapped; region 2 is partly seen; its only bedroom marker is mapped, so bedroom is not open ...
    st = rt.stage_state(truth, mk_row(objects=[N(1, "object", "bed", (3.0, 1.0), canon="bed")]))
    assert st.partly_seen == {2}
    assert "bedroom" not in st.open_types
    assert "bedroom" in st.open_types_loose          # ... but the loose set only needs an unseen region of the type
    assert st.open_types == {"bathroom", "kitchen", "laundry"}
    assert "bed" not in st.open_classes and "bed" in st.open_classes_loose
    assert {"nightstand", "lamp"} <= st.open_classes   # the other two objects of region 2 are still unmapped


def test_type_closed_by_a_room_node_of_that_type_within_reach(truth):
    near = rt.stage_state(truth, mk_row(rooms=[N(100, "room", "bathroom", (-0.3, 1.0), rtype="bathroom")]))
    assert near.partly_seen == {1}                           # the room node reaches region 1 without being inside
    assert "bathroom" not in near.open_types                 # the toilet is unmapped, but a bathroom node reaches the region
    assert "bathroom" in near.open_types_loose               # the loose set is unchanged
    assert near.open_types == {"bedroom", "kitchen", "laundry"}
    other_type = rt.stage_state(truth, mk_row(rooms=[N(100, "room", "bedroom", (-0.3, 1.0), rtype="bedroom")]))
    assert "bathroom" in other_type.open_types               # a room node of another type does not close it
    untyped = rt.stage_state(truth, mk_row(rooms=[N(100, "room", "x", (-0.3, 1.0), rtype=None)]))
    assert "bathroom" in untyped.open_types
    far = rt.stage_state(truth, mk_row(rooms=[N(100, "room", "bathroom", (-5.0, -5.0), rtype="bathroom")]))
    assert "bathroom" in far.open_types                      # a node of the type that does not reach the region
    gap = rt.stage_state(truth, mk_row(rooms=[N(100, "room", "bathroom", (1.0, 2.2), rtype="bathroom")]))
    assert gap.partly_seen == {1, 3}                         # reaches regions 1 and 3
    assert gap.open_types == {"bedroom", "kitchen", "laundry"}   # closes bathroom in 1; region 3's types stay open


# Two bedrooms with a hallway between them (grid 100 x 60, origin (0, 0), 0.05 m cells):
#   1 bedroom A   ix 0..39   (x 0.00-2.00)   bed at (1.0, 1.0)
#   2 hallway     ix 40..45  (x 2.00-2.30)   a chair; no marker
#   3 bedroom B   ix 46..85  (x 2.30-4.30)   bed at (3.3, 1.0)
# All rows iy 0..39 (y 0.00-2.00). The floor masks equal the `any` masks.

@pytest.fixture()
def two_bedrooms(tmp_path):
    def m(ix0, ix1):
        a = np.zeros((60, 100), dtype=bool)
        a[0:40, ix0:ix1 + 1] = True
        return a
    masks = np.stack([m(0, 39), m(40, 45), m(46, 85)])
    np.savez(tmp_path / "88888_region_footprints.npz", scene=np.array("88888"),
             origin_xy=np.array([0.0, 0.0]), cell_size=np.array(0.05), axis_names=np.array(["x", "y"]),
             vertical_axis=np.array("z"), region_ids=np.array([1, 2, 3]), floor_masks=masks, any_masks=masks,
             habitat_to_world_R=np.eye(3), habitat_to_world_t=np.zeros(3))
    objs = [_obj(1, "bed", 1, (1.0, 1.0)), _obj(2, "nightstand", 1, (0.5, 0.5)),
            _obj(3, "chair", 2, (2.15, 1.5)),
            _obj(4, "bed", 3, (3.3, 1.0)), _obj(5, "nightstand", 3, (3.8, 0.5))]
    (tmp_path / "88888_semantic_geometry.json").write_text(json.dumps(
        {"scene": "88888", "n_objects": len(objs), "objects": {str(o["id"]): o for o in objs}}))
    (tmp_path / "88888_regions.json").write_text(json.dumps(
        {"scene": "88888", "regions": [{"region_id": r, "centroid_xy": [0.0, 0.0]} for r in (1, 2, 3)]}))
    t = rt.load_scene_truth("88888", truth_dir=tmp_path)
    assert t.regions[1].types == {"bedroom"} and t.regions[3].types == {"bedroom"} and t.regions[2].types == frozenset()
    return t


def test_bedroom_node_in_a_seen_bedroom_does_not_close_the_unseen_one_next_door(two_bedrooms):
    # a path point in bedroom A sees it; the bedroom node stands inside A, 0.4 m from B's footprint
    node = N(100, "room", "bedroom", (1.9, 1.0), rtype="bedroom")
    assert two_bedrooms.inside(node.xy) == {1} and 3 in two_bedrooms.reaches(node.xy)
    st = rt.stage_state(two_bedrooms, mk_row(rooms=[node], path=[(1.0, 1.0)]))
    assert 1 in st.seen and 3 in st.partly_seen
    assert "bedroom" in st.open_types                  # B: bed unmapped; the node is inside another bedroom region
    assert "bedroom" in st.open_types_loose


def test_bedroom_node_in_a_hallway_within_reach_closes_the_bedroom(two_bedrooms):
    # the node stands in the hallway (region 2, no bedroom) and reaches both bedrooms
    node = N(100, "room", "bedroom", (2.15, 1.0), rtype="bedroom")
    assert two_bedrooms.inside(node.xy) == {2} and two_bedrooms.reaches(node.xy) == {1, 2, 3}
    st = rt.stage_state(two_bedrooms, mk_row(rooms=[node]))
    assert st.seen == {2} and st.partly_seen == {1, 3}
    assert "bedroom" not in st.open_types              # both unseen bedrooms are closed, though no bed is mapped
    assert "bedroom" in st.open_types_loose            # the loose set is unchanged
    # a node of another type in the same hallway closes nothing
    other = rt.stage_state(two_bedrooms, mk_row(rooms=[N(100, "room", "kitchen", (2.15, 1.0), rtype="kitchen")]))
    assert "bedroom" in other.open_types


def test_bedroom_node_inside_the_region_closes_it(two_bedrooms):
    # A's bed is mapped (A is partly seen and closed by its marker); B is the only unmapped bedroom left
    bed_a = N(1, "object", "bed", (1.0, 1.0), canon="bed")
    no_node = rt.stage_state(two_bedrooms, mk_row(objects=[bed_a]))
    assert no_node.partly_seen == {1} and no_node.unobserved == {2, 3}
    assert "bedroom" in no_node.open_types             # B: nothing maps its bed, no node closes it
    node = N(100, "room", "bedroom", (3.0, 1.0), rtype="bedroom")     # inside B, far from A and the hallway
    assert two_bedrooms.inside(node.xy) == {3}
    st = rt.stage_state(two_bedrooms, mk_row(objects=[bed_a], rooms=[node]))
    assert 3 in st.seen
    assert "bedroom" not in st.open_types              # A closed by its marker, B closed by the node inside it


def test_type_closed_by_one_mapped_marker_even_if_another_is_unmapped(truth):
    # region 3: the oven is mapped, the stove and the stovetop are not; kitchen is closed
    st = rt.stage_state(truth, mk_row(objects=[N(1, "object", "oven", (0.5, 3.0), canon="oven")]))
    assert 20 in st.mapped_objects and 21 not in st.mapped_objects and 22 not in st.mapped_objects
    assert st.partly_seen == {3}
    assert "kitchen" not in st.open_types and "kitchen" in st.open_types_loose
    assert "laundry" in st.open_types                        # the washer marker has no geometry: never mapped
    # region 1: the toilet is mapped, the shower floor and the shower door are not; bathroom is closed
    st1 = rt.stage_state(truth, mk_row(objects=[N(1, "object", "toilet", (0.5, 0.5), canon="toilet")]))
    assert 1 in st1.mapped_objects and 2 not in st1.mapped_objects and 5 not in st1.mapped_objects
    assert st1.partly_seen == {1} and "bathroom" not in st1.open_types


def test_marker_with_empty_answers_to_is_never_mapped(truth):
    # the stovetop answers to nothing: a stove node 0.12 m from it maps nothing
    st = rt.stage_state(truth, mk_row(objects=[N(1, "object", "stove", (1.62, 3.0), canon="stove")]))
    assert 22 not in st.mapped_objects and 21 not in st.mapped_objects
    assert "kitchen" in st.open_types
    # the shower door answers only to a structure class: even a node carrying that class maps nothing
    st2 = rt.stage_state(truth, mk_row(objects=[N(1, "object", "door", (0.2, 1.5), canon="door")]))
    assert 5 not in st2.mapped_objects and st2.mapped_objects == frozenset()


def test_marker_without_geometry_is_never_mapped(truth):
    objs = [N(i, "object", "washer", (0.5 + i, 3.0), canon="washer") for i in range(3)]
    st = rt.stage_state(truth, mk_row(objects=objs))
    assert 23 not in st.mapped_objects
    assert "laundry" in st.open_types


def test_a_seen_region_opens_nothing(truth):
    st = rt.stage_state(truth, mk_row(path=[(1.0, 1.0)]))       # region 1 seen, nothing mapped
    assert "bathroom" not in st.open_types and "bathroom" not in st.open_types_loose
    assert "toilet" not in st.open_classes and "toilet" not in st.open_classes_loose
    assert "bedroom" in st.open_types


def test_open_class_held_by_an_unmapped_object_in_an_unseen_region(truth):
    # the lamp of region 4 (class "lamp") is mapped; region 2 still holds an unmapped lamp
    st = rt.stage_state(truth, mk_row(objects=[N(1, "object", "lamp", (4.0, 4.0), canon="lamp")]))
    assert 31 in st.mapped_objects
    assert "lamp" in st.open_classes                         # region 2's lamp
    # map region 2's lamp as well: no unmapped lamp remains
    st2 = rt.stage_state(truth, mk_row(objects=[N(1, "object", "lamp", (4.0, 4.0), canon="lamp"),
                                                N(2, "object", "lamp", (3.2, 1.5), canon="lamp")]))
    assert "lamp" not in st2.open_classes and "lamp" in st2.open_classes_loose


def test_state_partitions_the_regions(truth):
    st = rt.stage_state(truth, mk_row(objects=[N(1, "object", "oven", (0.5, 3.0), canon="oven")],
                                      rooms=[N(100, "room", "x", (2.8, 3.0))], path=[(3.0, 1.0)]))
    assert st.seen | st.partly_seen | st.unobserved == {1, 2, 3, 4}
    assert not (st.seen & st.partly_seen) and not (st.seen & st.unobserved) and not (st.partly_seen & st.unobserved)


# ----------------------------------------------------------------------------- graph reading

def node(nid, ntype, name, pos, flag=None, extra=None):
    d = {"id": nid, "name": name, "node_type": ntype, "position": pos if isinstance(pos, str) else str(list(pos)),
         "dimension": "[0.1, 0.1, 0.1]"}
    if flag is not None:
        d["is_predicted"] = flag
    if extra:
        d.update(extra)
    return d


def write_graph(path, nodes):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"edges": [], "nodes": nodes}))
    return path


OBS_NODES = [
    node(1, "object", "bed", (0.0, 0.0, 0.5), False),
    node(2, "object", "nightstand", (5.0, 5.0, 0.5), False),
    node(3, "structure", "wall", (1.0, 1.0, 1.0)),
    node(4, "nothing", "Nothing", (2.0, 2.0, 1.0)),
    node(100, "room", "bedroom", (1.0, 1.0, 0.0)),
    node(101, "room", "living room", (6.0, 1.0, 0.0)),
]


@pytest.fixture()
def observed(tmp_path):
    return ep.read_graph(write_graph(tmp_path / "obs.yaml", OBS_NODES))


def test_read_graph(observed):
    assert [n.node_id for n in observed.objects] == [1, 2]
    assert [n.node_id for n in observed.rooms] == [100, 101]
    assert observed.node_ids == {1, 2, 3, 4, 100, 101}      # every node, whatever its type
    bed = observed.objects[0]
    assert bed.canon == "bed" and bed.xy == (0.0, 0.0) and bed.z == 0.5 and bed.is_predicted is False
    assert observed.rooms[0].room_type == "bedroom" and observed.rooms[1].room_type == "living"
    assert observed.rooms[0].is_predicted is None


COMPLETION = OBS_NODES + [
    # objects
    node(2, "object", "sofa", (7.0, 5.0, 0.5)),                  # repeats observed id 2, but 2 m from every observed object: NEW
    node(14, "object", "bed", (0.3, 0.0, 0.5)),                  # fresh id, 0.3 m from an observed object: NOT new
    node(15, "object", "table", (0.5, 0.0, 0.5)),                # exactly 0.5 m: not new
    node(16, "object", "table", (0.51, 0.0, 0.5)),               # 0.51 m: new
    node(10, "object", "lamp", (9.0, 9.0, 0.5), True),           # new, flagged
    node(11, "object", "blorp", (9.0, 8.0, 0.5), False),         # new, no canonical class
    node(12, "object", "lamp", (9.1, 9.0, 0.5)),                 # new, same class as node 10
    node(13, "object", "wall", (8.0, 8.0, 0.5), False),          # new, structure class
    node(17, "object", "chair", "[nan, 1.0, 2.0]"),              # broken position: skipped
    node(18, "object", "chair", "garbage"),                      # broken position: skipped
    node(19, "object", "chair", "[1.0, 2.0]"),                   # broken position: skipped
    node(20, "structure", "wall", (30.0, 30.0, 0.5)),            # not an object: dropped
    # rooms
    node(101, "room", "kitchen", (6.0, 3.0, 0.0)),               # repeats observed id 101, but 2 m from every observed room: NEW
    node(102, "room", "bathroom", (1.3, 1.0, 0.0)),              # fresh id, 0.3 m from an observed room: NOT new
    node(103, "room", "nursery", (9.0, 9.0, 0.0)),               # new, no type
    node(104, "room", "dining room", (9.0, 5.0, 0.0)),           # new, dining
    node(105, "room", "bathroom", (9.0, 1.0, 0.0)),              # new
    node(106, "room", "bathroom", "oops"),                       # broken position: skipped
]


def test_read_member_new_object_and_room_rules(tmp_path, observed):
    mem = ep.read_member(write_graph(tmp_path / "m.yaml", COMPLETION), observed, 2)
    assert mem.member == 2
    assert sorted(n.node_id for n in mem.new_objects) == [2, 10, 11, 12, 13, 16]
    new_sofa = next(n for n in mem.new_objects if n.node_id == 2)
    assert new_sofa.name == "sofa" and new_sofa.xy == (7.0, 5.0)
    assert sorted(n.node_id for n in mem.new_rooms) == [101, 103, 104, 105]
    assert 14 not in {n.node_id for n in mem.new_objects}    # 0.3 m from an observed object
    assert 15 not in {n.node_id for n in mem.new_objects}    # exactly 0.5 m
    assert 102 not in {n.node_id for n in mem.new_rooms}     # 0.3 m from an observed room


def test_read_member_old_nodes_are_not_new_even_with_their_own_ids(tmp_path, observed):
    mem = ep.read_member(write_graph(tmp_path / "m.yaml", OBS_NODES), observed, 0)
    assert mem.new_objects == () and mem.new_rooms == ()
    assert mem.l1_claims == frozenset() and mem.l2_claims == frozenset() and mem.l3_items == ()


def test_read_member_claims_items_and_counts(tmp_path, observed):
    mem = ep.read_member(write_graph(tmp_path / "m.yaml", COMPLETION), observed, 0)
    assert mem.l1_claims == {"kitchen", "bathroom"}          # dining is typed but never claimed; nursery has no type
    assert mem.n_rooms_untyped == 1
    assert mem.l2_claims == {"sofa", "lamp", "table"}
    assert mem.n_objects_unlabelled == 2                     # "blorp" and the structure-class "wall"
    assert mem.n_objects_flagged == 1 and mem.n_objects_unflagged == 5   # the flag as written, not a rule
    rooms = sorted((i.label, i.xy) for i in mem.l3_items if i.kind == "room")
    objs = sorted((i.label, i.xy) for i in mem.l3_items if i.kind == "object")
    # item 51 of DEVIATIONS_NOVEMBER: a new room typed dining is left out of the L3 items, and counted
    assert rooms == [("bathroom", (9.0, 1.0)), ("kitchen", (6.0, 3.0))]
    assert mem.n_rooms_dining == 1
    assert objs == [("lamp", (9.0, 9.0)), ("lamp", (9.1, 9.0)), ("sofa", (7.0, 5.0)), ("table", (0.51, 0.0))]
    assert len(mem.l3_items) == 6


def test_broken_positions_are_skipped_and_counted(tmp_path, observed):
    ep.SKIPPED.clear()
    mem = ep.read_member(write_graph(tmp_path / "m.yaml", COMPLETION), observed, 0)
    assert ep.SKIPPED["object_unparseable_position"] == 3
    assert ep.SKIPPED["room_unparseable_position"] == 1
    assert {17, 18, 19, 106}.isdisjoint({n.node_id for n in mem.new_objects} | {n.node_id for n in mem.new_rooms})


def test_broken_node_in_the_observed_graph_is_skipped_not_guessed(tmp_path):
    nodes = OBS_NODES + [node(7, "object", "chair", "[a, b, c]")]
    g = ep.read_graph(write_graph(tmp_path / "o.yaml", nodes))
    assert 7 in g.node_ids and 7 not in {n.node_id for n in g.objects}
    assert ep.SKIPPED["object_unparseable_position"] == 1


def test_all_new_when_the_observed_graph_has_no_nodes_of_that_kind(tmp_path):
    g = ep.read_graph(write_graph(tmp_path / "o.yaml", [node(1, "structure", "wall", (0, 0, 0))]))
    mem = ep.read_member(write_graph(tmp_path / "m.yaml", [node(2, "object", "bed", (0, 0, 0)),
                                                           node(3, "room", "bedroom", (0, 0, 0))]), g, 0)
    assert len(mem.new_objects) == 1 and len(mem.new_rooms) == 1


def test_not_a_graph_is_an_error(tmp_path, observed):
    p = tmp_path / "bad.yaml"
    p.write_text("- just\n- a list\n")
    with pytest.raises(ValueError):
        ep.read_member(p, observed, 0)


# ---------------------------------------------------------------------- frame, rows, members

FRAME = """# The sample frame
# Round 1: stage 3
r1_e1 /workspace/runs/live_campaign/e1_00853_s42_official_60m 3
r1_e2 /workspace/runs/live_campaign/e2_00871_s43_filter_only_60m 3
# Round 4: the Gemini rows
fa1_x /workspace/runs/live_campaign/e1_00871_s42_official_60m_FAILED_ATTEMPT1_false_exit_host_oom 2
"""


def path_json(pts):
    return json.dumps({"habitat_frame_path": [[0, 0, 0]] * len(pts), "world_frame_path": [list(p) for p in pts]})


@pytest.fixture()
def campaign(tmp_path):
    runs = tmp_path / "runs"
    frame = tmp_path / "frame.txt"
    frame.write_text(FRAME)
    paths = {1: [(1.0, 1.0, 1.1), (1.5, 1.0, 1.1)], 2: [(2.0, 1.0, 1.1)], 3: [(3.0, 1.0, 1.1), (3.5, 1.0, 1.1)]}
    for run, nstage in (("e1_00853_s42_official_60m", 3), ("e2_00871_s43_filter_only_60m", 3),
                        ("e1_00871_s42_official_60m_FAILED_ATTEMPT1_false_exit_host_oom", 2)):
        for k in range(0, nstage + 1):
            sd = runs / run / "stages" / str(k)
            sd.mkdir(parents=True)
            if k >= 1:
                (sd / "executed_path.json").write_text(path_json(paths[k]))
        write_graph(runs / run / "stages" / str(nstage) / "habitat_scene_graph_original_graph0.yaml", OBS_NODES)
    return runs, frame, paths


def new_lamp(nid, x):
    return OBS_NODES + [node(nid, "object", "lamp", (x, 9.0, 0.5))]


def test_parse_frame(campaign):
    _, frame, _ = campaign
    assert ep.parse_frame(frame) == [
        ("r1_e1", "e1_00853_s42_official_60m", 3, 1),
        ("r1_e2", "e2_00871_s43_filter_only_60m", 3, 1),
        ("fa1_x", "e1_00871_s42_official_60m_FAILED_ATTEMPT1_false_exit_host_oom", 2, 4)]


def test_load_row_fields_and_path(campaign):
    runs, frame, paths = campaign
    row = ep.load_row("r1_e1", runs_root=runs, frame_path=frame)
    assert (row.scene, row.seed, row.arm, row.stage, row.round) == ("00853", 42, "official", 3, 1)
    assert row.cluster == "00853_s42_official" and row.is_gemini_row is False
    # the first point of stage 1, then every point of stages 1..3 in order
    assert row.path_xy == ((1.0, 1.0), (1.0, 1.0), (1.5, 1.0), (2.0, 1.0), (3.0, 1.0), (3.5, 1.0))
    assert [n.node_id for n in row.observed.rooms] == [100, 101]
    r2 = ep.load_row("r1_e2", runs_root=runs, frame_path=frame)
    assert r2.arm == "filter_only" and r2.cluster == "00871_s43_filter_only" and r2.seed == 43


def test_first_attempt_row_joins_the_official_cluster(campaign):
    runs, frame, _ = campaign
    row = ep.load_row("fa1_x", runs_root=runs, frame_path=frame)
    assert row.cluster == "00871_s42_official" and row.arm == "official"
    assert row.round == 4 and row.is_gemini_row is True and row.stage == 2
    assert row.path_xy == ((1.0, 1.0), (1.0, 1.0), (1.5, 1.0), (2.0, 1.0))


def test_unknown_row_is_an_error(campaign):
    runs, frame, _ = campaign
    with pytest.raises(KeyError):
        ep.load_row("nope", runs_root=runs, frame_path=frame)


def test_missing_path_file_is_an_error(campaign):
    runs, frame, _ = campaign
    (runs / "e1_00853_s42_official_60m" / "stages" / "2" / "executed_path.json").unlink()
    with pytest.raises(OSError):
        ep.load_row("r1_e1", runs_root=runs, frame_path=frame)


def test_members_official_use_the_stage_files(campaign):
    runs, frame, _ = campaign
    sd = runs / "e1_00853_s42_official_60m" / "stages" / "3"
    for m in (0, 1, 3):                                   # member 2 missing: its parse failed
        write_graph(sd / f"habitat_scene_graph_new_graph_{m}.yaml", new_lamp(40 + m, float(m)))
    write_graph(sd / "habitat_scene_graph_new_graph_5.yaml", new_lamp(99, 5.0))   # track 1: never read
    row = ep.load_row("r1_e1", runs_root=runs, frame_path=frame)
    mems = ep.members_for(row, "deepseek", runs_root=runs, frame_path=frame)
    assert [m.member for m in mems] == [0, 1, 3]
    assert all(len(m.new_objects) == 1 for m in mems)
    assert mems[2].new_objects[0].node_id == 43


def test_members_filter_only_use_the_highest_raw_attempt(campaign):
    runs, frame, _ = campaign
    sd = runs / "e2_00871_s43_filter_only_60m" / "stages" / "3"
    for m in range(4):   # the filtered files on disk: they must not be used
        write_graph(sd / f"habitat_scene_graph_new_graph_{m}.yaml", OBS_NODES)
    write_graph(sd / "live_policy_raw" / "attempt_2" / "habitat_scene_graph_new_graph_0.yaml", new_lamp(50, 1.0))
    write_graph(sd / "live_policy_raw" / "attempt_10" / "habitat_scene_graph_new_graph_0.yaml", new_lamp(60, 2.0))
    write_graph(sd / "live_policy_raw" / "attempt_10" / "habitat_scene_graph_new_graph_1.yaml", new_lamp(61, 3.0))
    write_graph(sd / "live_policy_raw" / "attempt_10" / "habitat_scene_graph_new_graph_4.yaml", new_lamp(62, 4.0))  # track 1
    row = ep.load_row("r1_e2", runs_root=runs, frame_path=frame)
    mems = ep.members_for(row, "deepseek", runs_root=runs, frame_path=frame)
    assert [m.member for m in mems] == [0, 1]
    assert [m.new_objects[0].node_id for m in mems] == [60, 61]      # attempt_10, not attempt_2; not the filtered files


def test_filter_only_without_a_raw_folder_gives_no_members(campaign):
    runs, frame, _ = campaign
    sd = runs / "e2_00871_s43_filter_only_60m" / "stages" / "3"
    write_graph(sd / "habitat_scene_graph_new_graph_0.yaml", new_lamp(50, 1.0))   # filtered file only
    row = ep.load_row("r1_e2", runs_root=runs, frame_path=frame)
    assert ep.members_for(row, "deepseek", runs_root=runs, frame_path=frame) == []
    assert ep.SKIPPED["raw_attempt_missing"] == 1


def test_members_gemini_prefers_static2_and_skips_other_rows(campaign, tmp_path):
    runs, frame, _ = campaign
    g = tmp_path / "gem"
    run = "e1_00871_s42_official_60m_FAILED_ATTEMPT1_false_exit_host_oom"
    write_graph(g / "gemini_static" / run / "2" / "gemini_new_graph_0.yaml", new_lamp(70, 1.0))
    write_graph(g / "gemini_static2" / run / "2" / "gemini_new_graph_1.yaml", new_lamp(71, 2.0))
    write_graph(g / "gemini_static2" / run / "2" / "gemini_new_graph_3.yaml", new_lamp(73, 4.0))
    row = ep.load_row("fa1_x", runs_root=runs, frame_path=frame)
    assert ep.gemini_dir(row, gemini_root=g, frame_path=frame) == g / "gemini_static2" / run / "2"
    mems = ep.members_for(row, "gemini", runs_root=runs, gemini_root=g, frame_path=frame)
    assert [m.member for m in mems] == [1, 3]
    # without a static2 folder for the row, gemini_static is used
    for f in (g / "gemini_static2" / run / "2").glob("*.yaml"):
        f.unlink()
    mems = ep.members_for(row, "gemini", runs_root=runs, gemini_root=g, frame_path=frame)
    assert [m.member for m in mems] == [0]
    other = ep.load_row("r1_e1", runs_root=runs, frame_path=frame)
    assert ep.members_for(other, "gemini", runs_root=runs, gemini_root=g, frame_path=frame) == []


def test_members_claude_layout_and_root_is_a_parameter(campaign, tmp_path):
    runs, frame, _ = campaign
    root = tmp_path / "claude"
    for m in (0, 2):
        write_graph(root / "claude-opus-5-5" / "r1_e1" / f"member_{m}" / "parsed_graph.yaml", new_lamp(80 + m, float(m)))
        (root / "claude-opus-5-5" / "r1_e1" / f"member_{m}" / "parse.json").write_text('{"ok": true}')
    write_graph(root / "claude-haiku-5-5" / "r1_e1" / "member_1" / "parsed_graph.yaml", new_lamp(90, 1.0))
    (root / "claude-haiku-5-5" / "r1_e1" / "member_1" / "parse.json").write_text('{"ok": true}')
    row = ep.load_row("r1_e1", runs_root=runs, frame_path=frame)
    opus = ep.members_for(row, "claude-opus-5-5", runs_root=runs, claude_root=root, frame_path=frame)
    haiku = ep.members_for(row, "claude-haiku-5-5", runs_root=runs, claude_root=root, frame_path=frame)
    assert [m.member for m in opus] == [0, 2] and [m.member for m in haiku] == [1]
    with pytest.raises(ValueError):
        ep.members_for(row, "claude-opus-5-5", runs_root=runs, frame_path=frame)
    with pytest.raises(ValueError):
        ep.members_for(row, "gpt", runs_root=runs, frame_path=frame)


def test_unreadable_member_file_is_skipped_and_counted(campaign):
    runs, frame, _ = campaign
    sd = runs / "e1_00853_s42_official_60m" / "stages" / "3"
    write_graph(sd / "habitat_scene_graph_new_graph_0.yaml", new_lamp(40, 1.0))
    (sd / "habitat_scene_graph_new_graph_1.yaml").write_text("not: [valid")
    row = ep.load_row("r1_e1", runs_root=runs, frame_path=frame)
    mems = ep.members_for(row, "deepseek", runs_root=runs, frame_path=frame)
    assert [m.member for m in mems] == [0] and ep.SKIPPED["member_unreadable"] == 1


# ------------------------------------------------------------------------- smoke, real data

REAL_RUNS = ep.RUNS_ROOT


@pytest.mark.skipif(not (REAL_RUNS / "e1_00853_s42_official_60m").is_dir(), reason="saved campaign not on this machine")
def test_smoke_real_data(capsys):
    """Counts only: truth loads, 44 rows load, members read. No comparison with truth."""
    use_labels = _real_labels_or_stub()
    rt.labels = use_labels
    ep.labels = use_labels
    ep.SKIPPED.clear()
    scenes = {}
    for scene in ("00853", "00871"):
        t = rt.load_scene_truth(scene)
        scenes[scene] = t
        types = {}
        for r in t.regions.values():
            for ty in (r.types or {"other"}):
                types[ty] = types.get(ty, 0) + 1
        print(f"scene {scene}: {len(t.regions)} regions, "
              f"{sum(len(r.ref_objects) for r in t.regions.values())} reference objects, "
              f"{sum(len(r.markers) for r in t.regions.values())} markers "
              f"({sum(not m.answers_to for r in t.regions.values() for m in r.markers)} answer to nothing, "
              f"{sum(m.xy is None for r in t.regions.values() for m in r.markers)} without geometry), "
              f"regions by type {dict(sorted(types.items()))}, regions without floor {t.regions_without_floor}, "
              f"{t.skipped_objects} objects outside the grid regions")
        rj = json.loads((rt.TRUTH_DIR / f"{scene}_regions.json").read_text())["regions"]
        assert sorted(int(r["region_id"]) for r in rj if not r.get("has_floor_triangles", True)) == \
            sorted(t.regions_without_floor)       # the mask rule and regions.json agree on which regions lack a floor
    frame = ep.parse_frame()
    assert len(frame) == 44
    totals = {"deepseek": 0, "gemini": 0}
    short = {"deepseek": 0, "gemini": 0}
    for row_id, _run, _stage, _rnd in frame:
        row = ep.load_row(row_id)
        st = rt.stage_state(scenes[row.scene], row)       # runs; its sets are not printed or compared
        assert st.seen | st.partly_seen | st.unobserved == frozenset(scenes[row.scene].regions)
        line = f"{row_id:30s} obs {len(row.observed.rooms):2d}r/{len(row.observed.objects):3d}o path {len(row.path_xy):4d}"
        for model in (("deepseek", "gemini") if row.is_gemini_row else ("deepseek",)):
            mems = ep.members_for(row, model)
            totals[model] += len(mems)
            short[model] += len(mems) < 4
            line += f" | {model}: {len(mems)} members, new rooms {[len(m.new_rooms) for m in mems]}, " \
                    f"new objects {[len(m.new_objects) for m in mems]}"
        print(line)
    print(f"members found: {totals}; rows with fewer than 4: {short}; skipped counters: {dict(ep.SKIPPED)}")
    with capsys.disabled():
        pass
    assert totals["deepseek"] > 0 and totals["gemini"] > 0


def _real_labels_or_stub():
    try:
        real = rt._sibling("labels")
    except Exception as exc:   # e.g. canon_labels.json not built yet
        print(f"real labels.py did not load ({exc!r}); the smoke check uses a stub")
        real = None
    if real is not None:
        print("smoke check uses the real labels.py"
              + ("" if hasattr(real, "answers_to") else " (it has no answers_to yet)"))
        return real

    class Stub:   # counts of members and of new rooms and objects do not depend on the label table
        normalise = staticmethod(lambda s: s.lower().strip() or None)
        is_structure = staticmethod(lambda c: c in {"wall", "floor", "ceiling", "door", "window", "stairs"})
        room_type = staticmethod(lambda n: None)
        marker_types = staticmethod(lambda n: frozenset())
        answers_to = staticmethod(lambda n: frozenset())
    print("smoke check uses the stub label layer")
    return Stub


# ---- added with the wiring: open_type_regions, Claude drops, live members, the labels switch

def test_open_type_regions_agree_with_open_types_in_every_scenario(truth, two_bedrooms):
    scenarios = [(truth, mk_row()),
                 (truth, mk_row(objects=[N(1, "object", "bed", (3.0, 1.0), canon="bed")])),
                 (truth, mk_row(rooms=[N(100, "room", "bathroom", (-0.3, 1.0), rtype="bathroom")])),
                 (truth, mk_row(rooms=[N(100, "room", "bathroom", (1.0, 2.2), rtype="bathroom")])),
                 (two_bedrooms, mk_row(rooms=[N(100, "room", "bedroom", (2.15, 1.0), rtype="bedroom")])),
                 (two_bedrooms, mk_row(rooms=[N(100, "room", "bedroom", (1.9, 1.0), rtype="bedroom")], path=[(1.0, 1.0)]))]
    for t, row in scenarios:
        st = rt.stage_state(t, row)
        assert {k for k, v in st.open_type_regions.items() if v} == set(st.open_types)
        for typ, regs in st.open_type_regions.items():
            assert regs <= st.unseen and all(typ in t.regions[r].types for r in regs)


def test_open_type_regions_keeps_only_the_unclosed_bedroom(two_bedrooms):
    node = N(100, "room", "bedroom", (1.9, 1.0), rtype="bedroom")
    st = rt.stage_state(two_bedrooms, mk_row(rooms=[node], path=[(1.0, 1.0)]))
    assert st.open_type_regions == {"bedroom": frozenset({3})}        # A is seen; B stays open next to the node


def test_claude_member_status_and_drops(tmp_path):
    root = tmp_path / "claude" / "claude-opus-5-5" / "row1"
    def member(k, parse, graph=True):
        d = root / f"member_{k}"
        d.mkdir(parents=True)
        if parse is not None:
            (d / "parse.json").write_text(parse)
        if graph:
            write_graph(d / "parsed_graph.yaml", OBS_NODES)
    member(0, '{"ok": true}')
    member(1, '{"ok": false}')                 # the parse failed: dropped
    member(2, None)                            # no parse.json: cannot be confirmed, dropped
    (root / "member_3").mkdir()                # a folder with nothing in it: not finished
    status = ep.claude_member_status(tmp_path / "claude", "claude-opus-5-5", "row1")
    assert status == {0: "ok", 1: "dropped", 2: "dropped", 3: "unfinished"}   # nothing in the folder: not final
    member_ok_graph_missing = root.parent / "row2" / "member_0"
    member_ok_graph_missing.mkdir(parents=True)
    (member_ok_graph_missing / "parse.json").write_text('{"ok": true}')    # ok, but no parsed_graph.yaml
    assert ep.claude_member_status(tmp_path / "claude", "claude-opus-5-5", "row2")[0] == "dropped"
    assert ep.claude_member_status(tmp_path / "claude", "claude-opus-5-5", "row3") == {k: "absent" for k in range(4)}
    assert ep.claude_member_status(tmp_path / "claude", "claude-haiku-5-5", "row1") == {k: "absent" for k in range(4)}


def test_live_member_files_and_raw_member_files(tmp_path):
    run = "e2_00853_s42_filter_only_60m"
    sd = tmp_path / run / "stages" / "4"
    for k in (0, 1, 5):
        write_graph(sd / f"habitat_scene_graph_new_graph_{k}.yaml", OBS_NODES)
    assert sorted(ep.live_member_files(run, 4, tmp_path)) == [0, 1, 5]
    assert sorted(ep.raw_member_files(run, 4, tmp_path)) == [0, 1, 5]           # no raw folder: the stage files
    for k in (0, 1, 2, 5, 6):
        write_graph(sd / "live_policy_raw" / "attempt_1" / f"habitat_scene_graph_new_graph_{k}.yaml", OBS_NODES)
    write_graph(sd / "live_policy_raw" / "attempt_0" / "habitat_scene_graph_new_graph_3.yaml", OBS_NODES)
    raw = ep.raw_member_files(run, 4, tmp_path)
    assert sorted(raw) == [0, 1, 2, 5, 6] and all("attempt_1" in str(p) for p in raw.values())


def test_load_stage_row_and_run_info(tmp_path):
    run = "e1_00871_s43_placebo_60m"
    for k in (0, 1, 2):
        write_graph(tmp_path / run / "stages" / str(k) / "habitat_scene_graph_original_graph0.yaml", OBS_NODES)
    (tmp_path / run / "stages" / "1" / "executed_path.json").write_text(
        json.dumps({"world_frame_path": [[1.0, 2.0, 1.1], [1.5, 2.0, 1.1]]}))
    (tmp_path / run / "stages" / "2" / "executed_path.json").write_text(
        json.dumps({"world_frame_path": [[1.5, 2.0, 1.1], [2.0, 2.0, 1.1]]}))
    assert ep.run_info(run) == ("00871", 43, "placebo")
    assert ep.run_info("e3_00853_s42_oracle_visible_60m_rerun1") == ("00853", 42, "oracle_visible")
    with pytest.raises(ValueError):
        ep.run_info("e4_00853_s42_frontier_60m")
    assert ep.stage_numbers(run, tmp_path) == [0, 1, 2]
    r0, r2 = ep.load_stage_row(run, 0, tmp_path), ep.load_stage_row(run, 2, tmp_path)
    assert r0.path_xy == ((1.0, 2.0),)                        # stage 0: the start pose alone
    assert r2.path_xy == ((1.0, 2.0), (1.0, 2.0), (1.5, 2.0), (1.5, 2.0), (2.0, 2.0))
    assert r2.row_id == f"{run}#st02" and (r2.scene, r2.seed, r2.arm, r2.stage, r2.round) == ("00871", 43, "placebo", 2, 0)


def test_the_labels_switch_reaches_the_truth(tmp_path, monkeypatch):
    import importlib.util as _u
    _spec = _u.spec_from_file_location("_real_labels_for_switch", os.path.join(SEM, "labels.py"))
    real_labels = _u.module_from_spec(_spec)
    _spec.loader.exec_module(real_labels)
    monkeypatch.setattr(rt, "labels", real_labels)
    objs = [{"id": 1, "name": "bed", "region": 1, "n_tri": 5, "world_min": [0, 0, 0], "world_max": [1, 1, 1]},
            {"id": 2, "name": "refrigerator", "region": 1, "n_tri": 5, "world_min": [2, 0, 0], "world_max": [3, 1, 1]}]
    import numpy as np
    mask = np.zeros((1, 10, 10), dtype=bool)
    mask[0, 2:6, 2:6] = True
    np.savez(tmp_path / "77777_region_footprints.npz", cell_size=0.05, region_ids=np.array([1]), any_masks=mask,
             floor_masks=mask, origin_xy=np.array([0.0, 0.0]))
    (tmp_path / "77777_semantic_geometry.json").write_text(json.dumps(
        {"scene": "77777", "n_objects": 2, "objects": {str(o["id"]): o for o in objs}}))
    (tmp_path / "77777_regions.json").write_text(json.dumps({"scene": "77777", "regions": [{"region_id": 1, "centroid_xy": [0.0, 0.0]}]}))
    both = rt.load_scene_truth("77777", truth_dir=tmp_path)
    prim = rt.load_scene_truth("77777", truth_dir=tmp_path, include_extended=False)
    answers = lambda t: {o.raw_name: set(o.answers_to) for o in t.regions[1].ref_objects}      # noqa: E731
    assert answers(both)["bed"] == {"bed", "duvet"} and answers(prim)["bed"] == {"bed"}
    assert answers(both)["refrigerator"] == answers(prim)["refrigerator"] == {"fridge"}


def _claude_member(d, record=None, parse=None, graph=True):
    d.mkdir(parents=True, exist_ok=True)
    if record is not None:
        (d / "record.json").write_text(json.dumps({"status": record}))
    if parse is not None:
        (d / "parse.json").write_text(json.dumps({"ok": parse}))
    if graph:
        write_graph(d / "parsed_graph.yaml", OBS_NODES)


def test_claude_status_reads_record_json_and_both_layouts(tmp_path):
    for layout in ("effort_medium/", ""):
        root = tmp_path / ("a" if layout else "b")
        base = root / "claude-haiku-5-5" / (layout + "row1")
        _claude_member(base / "member_0", "ok", True)
        _claude_member(base / "member_1", "dropped_refusal", None, graph=False)
        _claude_member(base / "member_2", "dropped_turn_limit", None, graph=False)
        _claude_member(base / "member_3", "dropped_error", None, graph=False)
        assert ep.claude_member_status(root, "claude-haiku-5-5", "row1") == {0: "ok", 1: "dropped", 2: "dropped", 3: "dropped"}
        _claude_member(base.parent / "row2" / "member_0", "cap_stopped", None, graph=False)
        _claude_member(base.parent / "row2" / "member_1", "error", None, graph=False)
        st = ep.claude_member_status(root, "claude-haiku-5-5", "row2")
        assert st == {0: "unfinished", 1: "unfinished", 2: "absent", 3: "absent"}


def test_status_ok_with_parse_json_false_is_a_dropped_member(tmp_path):
    base = tmp_path / "claude-opus-5-5" / "effort_medium" / "row1"
    _claude_member(base / "member_0", "ok", False)                   # the replay wrote a graph, but it did not parse
    _claude_member(base / "member_1", "ok", True)
    _claude_member(base / "member_2", "ok", None, graph=False)       # ok in the record, nothing to read
    _claude_member(base / "member_3", None, False, graph=False)      # no record: parse.json decides
    st = ep.claude_member_status(tmp_path, "claude-opus-5-5", "row1")
    assert st == {0: "dropped", 1: "ok", 2: "dropped", 3: "dropped"}


def test_member_files_follow_the_layout_and_skip_dropped(tmp_path, campaign):
    runs, frame, _ = campaign
    base = tmp_path / "claude-opus-5-5" / "effort_medium" / "r1_e1"
    _claude_member(base / "member_0", "ok", True)
    _claude_member(base / "member_1", "ok", False)
    row = ep.load_row("r1_e1", runs_root=runs, frame_path=frame)
    files = ep.member_files(row, "claude-opus-5-5", runs_root=runs, claude_root=tmp_path, frame_path=frame)
    assert [m for m, _ in files] == [0] and "effort_medium" in str(files[0][1])


def test_regions_with_cells_counts_only_regions_whose_mask_has_a_cell(tmp_path, monkeypatch):
    import importlib.util as _u
    _spec = _u.spec_from_file_location("_real_labels_for_cells", os.path.join(SEM, "labels.py"))
    real_labels = _u.module_from_spec(_spec)
    _spec.loader.exec_module(real_labels)
    monkeypatch.setattr(rt, "labels", real_labels)
    import numpy as np
    mask = np.zeros((2, 10, 10), dtype=bool)
    mask[0, 2:6, 2:6] = True                                          # region 2 has an empty mask
    np.savez(tmp_path / "66666_region_footprints.npz", cell_size=0.05, region_ids=np.array([1, 2]), any_masks=mask,
             floor_masks=mask, origin_xy=np.array([0.0, 0.0]))
    objs = [{"id": 1, "name": "bed", "region": 1, "n_tri": 5, "world_min": [0, 0, 0], "world_max": [1, 1, 1]}]
    (tmp_path / "66666_semantic_geometry.json").write_text(json.dumps({"scene": "66666", "n_objects": 1, "objects": {"1": objs[0]}}))
    (tmp_path / "66666_regions.json").write_text(json.dumps({"scene": "66666", "regions": [
        {"region_id": 1, "centroid_xy": [0.0, 0.0]}, {"region_id": 2, "centroid_xy": [1.0, 1.0]}]}))
    t = rt.load_scene_truth("66666", truth_dir=tmp_path)
    assert len(t.regions) == 2 and t.regions_with_cells() == {1}
