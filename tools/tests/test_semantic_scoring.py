"""Tests for score_levels.py, baselines.py and run_semantic.py (PREREGISTRATION_SEMANTIC.md §8-§10).

Synthetic houses and hand-made members only; no model output. Modules load by file path under the
key `_semantic_sibling_<name>`, the key the modules use for each other, so all share one `model`.
"""
import hashlib
import importlib.util
import itertools
import json
import math
import os
import statistics
import subprocess
import sys
import types

import numpy as np
import pytest

HERE = os.path.dirname(__file__)
SEM = os.path.abspath(os.path.join(HERE, "..", "live_policy", "semantic"))


def load(name):
    key = f"_semantic_sibling_{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, os.path.join(SEM, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


M = load("model")
sl = load("score_levels")
bl = load("baselines")
rs = load("run_semantic")
st = load("stats")
DET = frozenset({"oven", "couch", "bed", "tv"})
STRUCT = {"wall", "floor", "ceiling"}
MARKS = {"toilet": {"bathroom"}, "bed": {"bedroom"}, "oven": {"kitchen"}, "couch": {"living"},
         "dining table": {"dining"}}
ANSWERS = {"bed": {"bed", "duvet"}}


def fake_labels():
    def answers_to(name):
        if name in STRUCT or name == "unknown":
            return frozenset()
        return frozenset(ANSWERS.get(name, {name}))
    return types.SimpleNamespace(
        detector_vocab=lambda: DET,
        is_structure=lambda c: c in STRUCT,
        marker_types=lambda n: frozenset(MARKS.get(n, ())),
        answers_to=answers_to,
        normalise=lambda n: n,
        canonical_classes=lambda: frozenset({"bed", "duvet", "nightstand", "couch", "toilet", "oven", "sink"}),
    )


@pytest.fixture(autouse=True)
def swap_labels(monkeypatch):
    fake = fake_labels()
    monkeypatch.setattr(sl, "labels", fake)
    monkeypatch.setattr(bl, "labels", fake)


# ------------------------------------------------------------------------------ the world

class BoxTruth(M.SceneTruth):
    def __init__(self, boxes, regions, scene="T"):
        self.boxes, self.regions, self.scene = boxes, regions, scene

    def distance(self, p, rid):
        x0, y0, x1, y1 = self.boxes[rid]
        return math.hypot(max(x0 - p[0], 0, p[0] - x1), max(y0 - p[1], 0, p[1] - y1))

    def inside(self, p):
        return frozenset(r for r in self.boxes if self.distance(p, r) == 0)

    inside_floor = inside

    def reaches(self, p):
        return frozenset(r for r in self.boxes if self.distance(p, r) <= M.REACH_M)


def obj(oid, rid, name, answers, xy):
    return M.RefObject(object_id=oid, region_id=rid, raw_name=name, answers_to=frozenset(answers), xy=xy)


def mark(oid, rid, name, types_, answers, xy):
    return M.Marker(object_id=oid, region_id=rid, raw_name=name, types=frozenset(types_),
                    answers_to=frozenset(answers), xy=xy)


def region(rid, types_, objs, marks):
    return M.Region(region_id=rid, types=frozenset(types_), centroid_xy=(0.0, 0.0),
                    ref_objects=tuple(objs), markers=tuple(marks))


def world():
    boxes = {1: (0, 0, 4, 4), 2: (4.4, 0, 8, 3), 3: (0, 6, 4, 10), 4: (6, 6, 9, 9), 5: (10, 0, 12, 3)}
    regs = {
        1: region(1, {"bedroom"}, [obj(1, 1, "bed", {"bed", "duvet"}, (2, 2)), obj(2, 1, "nightstand", {"nightstand"}, (1, 1))],
                  [mark(1, 1, "bed", {"bedroom"}, {"bed", "duvet"}, (2, 2))]),
        2: region(2, {"bathroom"}, [obj(3, 2, "toilet", {"toilet"}, (7, 1)), obj(4, 2, "sink", {"sink"}, (5, 1))],
                  [mark(3, 2, "toilet", {"bathroom"}, {"toilet"}, (7, 1))]),
        3: region(3, {"kitchen"}, [obj(5, 3, "oven", {"oven"}, (1, 7)), obj(6, 3, "fridge", {"fridge", "refrigerator"}, (3, 7))],
                  [mark(5, 3, "oven", {"kitchen"}, {"oven"}, (1, 7))]),
        4: region(4, {"living"}, [obj(7, 4, "couch", {"couch"}, (7, 7)), obj(8, 4, "tv", {"tv", "television"}, (8, 8))],
                  [mark(7, 4, "couch", {"living"}, {"couch"}, (7, 7))]),
        5: region(5, set(), [obj(9, 5, "nightstand", {"nightstand"}, (11, 1)), obj(10, 5, "plant", {"plant"}, (11, 2))], []),
    }
    return BoxTruth(boxes, regs)


def fs(*a):
    return frozenset(a)


STATE_A = M.StageState(
    seen=fs(1), partly_seen=fs(2), unobserved=fs(3, 4, 5), mapped_objects=fs(1, 3),
    open_types=fs("kitchen", "living"),
    open_classes=fs("sink", "oven", "fridge", "refrigerator", "couch", "tv", "television", "nightstand", "plant"),
    open_types_loose=fs("bathroom", "kitchen", "living"),
    open_classes_loose=fs("toilet", "sink", "oven", "fridge", "refrigerator", "couch", "tv", "television", "nightstand", "plant"))
STATE_B = M.StageState(
    seen=fs(3, 4, 5), partly_seen=fs(), unobserved=fs(1, 2), mapped_objects=fs(),
    open_types=fs("bedroom", "bathroom"), open_classes=fs("bed", "duvet", "nightstand", "toilet", "sink"),
    open_types_loose=fs("bedroom", "bathroom"), open_classes_loose=fs("bed", "duvet", "nightstand", "toilet", "sink"))


def node(nid, kind, xy, name="x", room_type=None, canon=None):
    return M.Node(node_id=nid, kind=kind, name=name, xy=xy, z=0.0, is_predicted=None, room_type=room_type, canon=canon)


def item(kind, label, xy):
    return M.Item(kind=kind, label=label, xy=xy)


def member(k=0, l1=(), l2=(), items=(), rooms=(), objects=()):
    return M.Member(member=k, new_rooms=tuple(rooms), new_objects=tuple(objects), l1_claims=frozenset(l1),
                    l2_claims=frozenset(l2), l3_items=tuple(items))


def observed(rooms=(), objects=()):
    rs_ = tuple(node(i, "room", (0, 0), room_type=t) for i, t in enumerate(rooms))
    os_ = tuple(node(100 + i, "object", (0, 0), canon=c) for i, c in enumerate(objects))
    return M.ObservedGraph(rooms=rs_, objects=os_, node_ids=frozenset(range(300)))


def mkrow(row_id="r", scene="00853", seed=42, arm="official", stage=8, rnd=1, gem=False, obs=None):
    return M.Row(row_id=row_id, scene=scene, seed=seed, arm=arm, stage=stage, cluster=f"{scene}_s{seed}_{arm}",
                 round=rnd, is_gemini_row=gem, observed=obs or observed(), path_xy=())


# --------------------------------------------------------------------------- L3 hit rule

def test_l3_room_rule_and_reach_edges():
    t = world()
    assert sl.l3_hit(item("room", "kitchen", (2, 8)), t, STATE_A)            # inside an unobserved kitchen
    assert sl.l3_hit(item("room", "kitchen", (2, 5.7)), t, STATE_A)          # 0.3 m off: reaches
    assert not sl.l3_hit(item("room", "kitchen", (2, 5.4)), t, STATE_A)      # 0.6 m off: does not
    assert not sl.l3_hit(item("room", "bathroom", (6, 1)), t, STATE_A)       # region 2 is only partly seen
    assert not sl.l3_hit(item("room", "bedroom", (2, 2)), t, STATE_A)        # region 1 is seen
    assert not sl.l3_hit(item("room", "living", (2, 8)), t, STATE_A)         # right place, wrong type
    assert not sl.l3_hit(item("room", "kitchen", (5, 5)), t, STATE_A)        # reaches nothing


def test_l3_object_rule_uses_answers_to():
    t = world()
    assert sl.l3_hit(item("object", "oven", (2, 8)), t, STATE_A)
    assert not sl.l3_hit(item("object", "couch", (2, 8)), t, STATE_A)        # kitchen holds no couch
    assert sl.l3_hit(item("object", "nightstand", (11, 1)), t, STATE_A)      # region 5, no type, holds one
    assert not sl.l3_hit(item("room", "bedroom", (11, 1)), t, STATE_A)
    # "refrigerator" is not the raw class "fridge", but the fridge answers to it
    assert sl.l3_hit(item("object", "refrigerator", (3, 7)), t, STATE_A)
    assert sl.l3_hit(item("object", "fridge", (3, 7)), t, STATE_A)
    assert sl.l3_hit(item("object", "television", (8, 8)), t, STATE_A)
    # the bed answers to "duvet"; with region 1 unobserved a duvet is a hit, a plain bed too
    assert sl.l3_hit(item("object", "duvet", (2, 2)), t, STATE_B)
    assert sl.l3_hit(item("object", "bed", (2, 2)), t, STATE_B)
    assert not sl.l3_hit(item("object", "duvet", (2, 2)), t, STATE_A)        # region 1 seen in A


def test_l3_reaching_two_regions_one_match_is_enough():
    t = world()
    assert t.reaches((4.2, 1)) == fs(1, 2)
    assert sl.l3_hit(item("object", "toilet", (4.2, 1)), t, STATE_B)         # via region 2
    assert sl.l3_hit(item("room", "bedroom", (4.2, 1)), t, STATE_B)          # via region 1
    assert not sl.l3_hit(item("room", "kitchen", (4.2, 1)), t, STATE_B)


def test_l3_holder_judges_by_holder_region():
    t = world()
    holder = {3: 4, 4: 3, 5: 5}
    assert sl.l3_hit(item("room", "living", (2, 8)), t, STATE_A, holder=holder)   # R3 judged as R4
    assert not sl.l3_hit(item("room", "kitchen", (2, 8)), t, STATE_A, holder=holder)
    assert sl.l3_hit(item("object", "couch", (2, 8)), t, STATE_A, holder=holder)
    assert sl.l3_hit(item("object", "oven", (7, 7)), t, STATE_A, holder=holder)    # R4 judged as R3


def test_possible():
    empty = M.StageState(seen=fs(1), partly_seen=fs(), unobserved=fs(), mapped_objects=fs(),
                         open_types=fs(), open_classes=fs(), open_types_loose=fs(), open_classes_loose=fs())
    t = world()
    assert [sl.possible(lv, t, STATE_A) for lv in ("L1", "L2", "L3")] == [True, True, True]
    assert [sl.possible(lv, t, empty) for lv in ("L1", "L2", "L3")] == [False, False, False]
    only_unobs = M.StageState(seen=fs(), partly_seen=fs(), unobserved=fs(1), mapped_objects=fs(), open_types=fs(),
                              open_classes=fs("bed"), open_types_loose=fs(), open_classes_loose=fs())
    assert [sl.possible(lv, t, only_unobs) for lv in ("L1", "L2", "L3")] == [False, True, True]
    with pytest.raises(ValueError):
        sl.possible("L4", t, STATE_A)


# ----------------------------------------------------------------------- score_member

M0_ITEMS = [
    item("room", "kitchen", (2, 8)),          # hit
    item("room", "bathroom", (6, 1)),         # partly seen region only
    item("object", "oven", (2, 8)),           # hit
    item("object", "couch", (2, 8)),          # miss
    item("object", "tv", (8, 8)),             # hit
    item("object", "toilet", (7, 1)),         # partly seen only
    item("object", "refrigerator", (3, 7)),   # hit through answers_to
    item("object", "duvet", (2, 2)),          # region 1 seen: miss
    item("room", "bedroom", (4.2, 1)),        # reaches regions 1 and 2, neither unobserved
]


def m0():
    return member(0, l1={"kitchen", "bathroom", "bedroom"}, l2={"oven", "sink", "bed", "couch", "toilet"}, items=M0_ITEMS)


def test_score_member_primary_levels():
    ms = sl.score_member(m0(), world(), STATE_A)
    assert (ms.l1_hits, ms.l1_n) == (1, 3)                 # kitchen only
    assert (ms.l2_hits, ms.l2_n) == (3, 5)                 # oven, sink, couch
    assert (ms.l3_hits, ms.l3_n) == (4, 9)
    assert ms.rate("L1") == pytest.approx(1 / 3) and ms.rate("L3") == pytest.approx(4 / 9)


def test_score_member_extra_readouts():
    ex = sl.score_member(m0(), world(), STATE_A).extra
    assert (ex["l1_loose"], ex["l1_loose_n"]) == (pytest.approx(2 / 3), 3)      # + bathroom
    assert (ex["l2_loose"], ex["l2_loose_n"]) == (pytest.approx(4 / 5), 5)      # + toilet
    assert (ex["l3_partly"], ex["l3_partly_n"]) == (pytest.approx(2 / 9), 9)    # bathroom room, toilet object
    assert (ex["l3_rooms"], ex["l3_rooms_n"]) == (pytest.approx(1 / 3), 3)
    assert (ex["l3_objects"], ex["l3_objects_n"]) == (pytest.approx(3 / 6), 6)
    assert (ex["l2_det"], ex["l2_det_n"]) == (pytest.approx(2 / 3), 3)          # oven, bed, couch in vocab; bed not open
    assert (ex["l3_det"], ex["l3_det_n"]) == (pytest.approx(2 / 3), 3)          # objects oven, couch, tv
    # §8: share of items reaching two or more regions
    assert (ex["l3_multi"], ex["l3_multi_n"]) == (pytest.approx(1 / 9), 9)
    assert ex["l3_multi_unobs"] == 0.0
    exb = sl.score_member(m0(), world(), STATE_B).extra
    assert exb["l3_multi"] == pytest.approx(1 / 9) and exb["l3_multi_unobs"] == pytest.approx(1 / 9)


def test_l3_multi_counts_items_not_regions():
    t = world()
    items = [item("room", "kitchen", (4.2, 1)), item("room", "kitchen", (2, 8)), item("room", "kitchen", (11, 1)),
             item("room", "kitchen", (5, 5))]
    ex = sl.score_member(member(items=items), t, STATE_A).extra
    assert ex["l3_multi"] == pytest.approx(1 / 4)          # only (4.2, 1) reaches two regions
    assert ex["l3_multi_n"] == 4


def test_l1_matched_one_claim_one_region():
    t = world()
    rooms = [node(1, "room", (0, 0), room_type="kitchen"), node(2, "room", (0, 0), room_type="kitchen"),
             node(3, "room", (0, 0), room_type="living"), node(4, "room", (0, 0), room_type="bedroom"),
             node(5, "room", (0, 0), room_type="dining"), node(6, "room", (0, 0), room_type=None)]
    mm = member(l1={"kitchen", "living", "bedroom"}, rooms=rooms)
    ex = sl.score_member(mm, t, STATE_A).extra
    assert (ex["l1_matched"], ex["l1_matched_n"]) == (pytest.approx(2 / 4), 4)  # two kitchens, one open kitchen; bedroom's region is seen
    # an observed living room node that reaches region 4 closes it (§5.5)
    near_living = M.ObservedGraph(rooms=(node(9, "room", (7, 7), room_type="living"),), objects=(), node_ids=fs())
    ex2 = sl.score_member(mm, t, STATE_A, near_living).extra
    assert ex2["l1_matched"] == pytest.approx(1 / 4)
    # a mapped kitchen marker closes region 3
    mapped = M.StageState(**{**STATE_A.__dict__, "mapped_objects": fs(1, 3, 5)})
    assert sl.score_member(mm, t, mapped).extra["l1_matched"] == pytest.approx(1 / 4)


def test_max_matching_two_types_one_region():
    assert sl._max_matching([[0], [0, 1], [1]], 2) == 2
    assert sl._max_matching([[0], [0]], 1) == 1
    assert sl._max_matching([[], [0]], 1) == 1


def test_l4_radii_with_answers_to():
    t = world()
    objs = [node(1, "object", (1.3, 7), canon="oven"),            # 0.3 m from the oven
            node(2, "object", (3, 8.5), canon="refrigerator"),    # 1.5 m from the fridge (answers refrigerator)
            node(3, "object", (8, 6.5), canon="couch"),           # 1.118 m from the couch
            node(4, "object", (2, 2), canon="bed")]               # only a mapped bed in a seen region
    ex = sl.score_member(member(objects=objs), t, STATE_A).extra
    assert ex["l4_0p5m_n"] == 4
    assert ex["l4_0p5m"] == pytest.approx(1 / 4) and ex["l4_1p0m"] == pytest.approx(1 / 4)
    assert ex["l4_2p0m"] == pytest.approx(3 / 4) and ex["l4_3p0m"] == pytest.approx(3 / 4)


def test_member_with_no_claim_has_no_score():
    ms = sl.score_member(member(), world(), STATE_A)
    assert ms.l1_n == ms.l2_n == ms.l3_n == 0
    assert [ms.rate(lv) for lv in ("L1", "L2", "L3")] == [None, None, None]
    assert sl.member_rates(ms) == {"L1": None, "L2": None, "L3": None}
    for key in ("l1_loose", "l2_loose", "l3_partly", "l3_rooms", "l3_objects", "l2_det", "l3_det", "l3_multi",
                "l1_matched", "l4_1p0m"):
        assert ex_n(ms, key) == 0 and key not in ms.extra


def ex_n(ms, key):
    return ms.extra[key + "_n"]


# ---------------------------------------------------------------------------- the prior

def write_summary(tmp_path):
    def h(num, split, regions):
        return {"house_id": f"{num}-x", "number": num, "split": split, "regions": regions}
    houses = [
        h("00001", "train", {"0": {"bed": 1, "nightstand": 2, "wall": 4}, "1": {"toilet": 1}, "2": {"bed": 1}}),
        h("00002", "train", {"0": {"bed": 1, "couch": 1}, "1": {"oven": 1, "toilet": 1}}),
        h("00003", "train", {"0": {"nightstand": 1}}),
        h("00003", "val", {"0": {"bed": 5}}),                     # a second split: not counted again
        h("00853", "train", {"0": {"toilet": 9, "bed": 9}}),      # test houses: left out
        h("00871", "train", {"0": {"toilet": 9, "bed": 9}}),
        h("00004", "train", {"0": {"bed": 1}, "1": {"bed": 1}, "2": {"bed": 1}, "-1": {"couch": 3}}),
        h("00005", "train", {"0": {"oven": 1}, "1": {"oven": 1}}),
    ]
    path = tmp_path / "summary.json"
    path.write_text(json.dumps({"houses": houses}))
    return path


@pytest.fixture
def prior(tmp_path):
    return bl.Prior(write_summary(tmp_path))


def test_prior_counts(prior):
    assert prior.n_houses == 5                       # 00003 once; 00853 and 00871 out
    assert prior.room_n["bedroom"] == [2, 1, 0, 3, 0]
    assert prior.room_n["bathroom"] == [1, 1, 0, 0, 0]
    assert prior.room_n["kitchen"] == [0, 1, 0, 0, 2]
    assert prior.room_n["living"] == [0, 1, 0, 0, 0]  # the region -1 couches mark no room
    assert prior.class_n["bed"] == [2, 1, 0, 3, 0]
    assert prior.class_n["nightstand"] == [2, 0, 1, 0, 0]
    assert prior.class_n["couch"] == [0, 1, 0, 3, 0]  # region -1 objects still count for N_c
    assert "wall" not in prior.class_n


def test_prior_answers_to_counts_an_object_once_per_class(prior):
    # a bed answers to bed and to duvet: each bed adds one to both classes
    assert prior.class_n["duvet"] == prior.class_n["bed"] == [2, 1, 0, 3, 0]


def test_prior_room_scores_presence_rule(prior):
    s = prior.room_scores(observed(rooms=["bedroom"]))
    assert s["bedroom"] == pytest.approx(2 / 3)       # houses with N>=1: 2,1,3; N>1: 2,3
    assert s["bathroom"] == pytest.approx(2 / 5)
    assert s["kitchen"] == pytest.approx(2 / 5)
    assert s["living"] == pytest.approx(1 / 5)
    assert s["laundry"] == 0.0 and set(s) == set(M.ROOM_TYPES)
    # many bedroom nodes still count as one (m_T is 0 or 1)
    assert prior.room_scores(observed(rooms=["bedroom"] * 4)) == s


def test_prior_room_zero_rule(prior):
    s = prior.room_scores(observed(rooms=["laundry"]))
    assert s["laundry"] == 0.0                        # m=1 and no house holds a laundry
    assert prior.room_scores(observed(rooms=["living"]))["living"] == 0.0   # one house holds one; none has more


def test_prior_class_scores_and_zero_rule(prior):
    s = prior.class_scores(observed(objects=["bed"]))
    assert s["bed"] == pytest.approx(2 / 3)
    assert s["duvet"] == pytest.approx(3 / 5)         # the observed node's class is "bed", not "duvet"
    assert s["nightstand"] == pytest.approx(2 / 5)
    assert s["sink"] == 0.0
    assert prior.class_scores(observed(objects=["couch"] * 3))["couch"] == 0.0   # N>=3: one house, none above
    assert prior.class_scores(observed(objects=["couch"] * 4))["couch"] == 0.0   # no house has N>=4


def test_prior_top_k_tie_rules(prior):
    obs = observed(rooms=["bathroom", "kitchen", "living", "laundry"])
    s = prior.room_scores(obs)
    # bedroom .6, kitchen .5, then 0 for bathroom (2 houses), living (1), laundry (0): holders break ties
    assert prior.top_k(s, 5, "room") == ["bedroom", "kitchen", "bathroom", "living", "laundry"]
    assert prior.top_k(s, 2, "room") == ["bedroom", "kitchen"]
    cs = prior.class_scores(observed(objects=["bed"]))
    assert prior.top_k(cs, 6, "object") == ["bed", "duvet", "couch", "nightstand", "oven", "toilet"]  # .4 ties: 2 houses each, alphabetical
    assert prior.top_k(cs, 0, "object") == []
    with pytest.raises(ValueError):
        prior.top_k(cs, 1, "x")


def test_b3_member_worked_example(prior):
    obs = observed(rooms=["bathroom", "kitchen", "living", "laundry"], objects=["bed"])
    m = member(2, l1={"a", "b"}, l2={"x", "y", "z"}, items=[item("room", "kitchen", (0, 0))])
    b3 = bl.b3_member(prior, obs, m)
    assert b3.member == 2 and b3.l1_claims == fs("bedroom", "kitchen")
    assert b3.l2_claims == fs("bed", "duvet", "couch") and b3.l3_items == ()
    assert bl.b3_claims(prior, obs, 1, "L1") == fs("bedroom")
    assert bl.b3_member(prior, obs, member(0)).l1_claims == fs()      # no claim: none made


def test_b3l_worked_example(prior):
    obs = observed(rooms=["bathroom", "kitchen", "living", "laundry"], objects=["bed"])
    items = ([item("room", "kitchen", (i, 0)) for i in range(3)] + [item("room", "bedroom", (9, 9)), item("room", "dining", (8, 8))]
             + [item("object", "oven", (1, 1)), item("object", "oven", (2, 1)), item("object", "toilet", (3, 1)),
                item("object", "toilet", (4, 1)), item("object", "couch", (5, 1))])
    out = bl.b3l_items(prior, obs, member(0, items=items))
    # rooms ranked kitchen(3), bedroom(1), dining(1; alphabetical after bedroom) -> bedroom, kitchen, bathroom
    # objects ranked oven(2), toilet(2), couch(1) -> bed, duvet, couch
    assert [(i.kind, i.label) for i in out] == [
        ("room", "bedroom"), ("room", "bedroom"), ("room", "bedroom"), ("room", "kitchen"), ("room", "bathroom"),
        ("object", "bed"), ("object", "bed"), ("object", "duvet"), ("object", "duvet"), ("object", "couch")]
    assert [i.xy for i in out] == [i.xy for i in items]
    mb = bl.b3l_member(prior, obs, member(3, items=items))
    assert mb.member == 3 and mb.l3_items == out and mb.l1_claims == fs()


def test_b2_member():
    m = bl.b2_member(observed(rooms=["bedroom", "dining", "kitchen"], objects=["bed", "oven"]), 1)
    assert m.l1_claims == fs("bedroom", "kitchen") and m.l2_claims == fs("bed", "oven") and m.member == 1


# ----------------------------------------------------------------- seeds, B5 and D

def test_stable_seed_values_and_distinctness():
    expect = int.from_bytes(hashlib.sha256("row1\x1f2\x1fB5".encode()).digest()[:8], "big")
    assert bl.stable_seed("row1", 2, "B5") == expect
    seeds = {bl.stable_seed("row1", 2, "B5"), bl.stable_seed("row1", 3, "B5"), bl.stable_seed("row1", 2, "D"),
             bl.stable_seed("row2", 2, "B5")}
    assert len(seeds) == 4


def test_seeds_stable_across_processes():
    code = (
        "import importlib.util,sys\n"
        "for n in ['model','labels','score_levels','baselines']:\n"
        " k='_semantic_sibling_'+n\n"
        " s=importlib.util.spec_from_file_location(k,%r+'/'+n+'.py')\n"
        " m=importlib.util.module_from_spec(s); sys.modules[k]=m; s.loader.exec_module(m)\n"
        "print(sys.modules['_semantic_sibling_baselines'].stable_seed('e1_x_st08',1,'D'))\n" % SEM)
    outs = set()
    for hs in ("1", "2", "random"):
        env = dict(os.environ, PYTHONHASHSEED=hs)
        outs.add(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True).stdout.strip())
    assert outs == {str(bl.stable_seed("e1_x_st08", 1, "D"))}


def test_b5_deterministic_given_seed_and_near_half():
    t = world()
    items = [item("room", "kitchen", (2, 8)), item("room", "living", (7, 7))]     # both hit as given
    m = member(items=items)
    a = bl.b5_l3(m, t, STATE_A, seed=5)
    assert a == bl.b5_l3(m, t, STATE_A, seed=5)
    assert abs(a - 0.5) < 0.06                    # identity -> 1, swap -> 0
    assert bl.b5_score is bl.b5_l3


def test_b5_one_label_member_unchanged():
    t = world()
    m = member(items=[item("room", "kitchen", (2, 8)), item("room", "kitchen", (7, 7)),
                      item("object", "oven", (2, 8)), item("object", "oven", (7, 7))])
    plain = sl.score_member(m, t, STATE_A).l3_hits / 4
    assert bl.b5_l3(m, t, STATE_A, seed=1) == pytest.approx(plain) == pytest.approx(0.5)
    assert bl.b5_l3(member(), t, STATE_A, seed=1) is None


def test_b5_never_mixes_kinds_and_uses_answers_to():
    t = world()
    # one room and one object: each kind has one label, so nothing moves
    m = member(items=[item("room", "kitchen", (2, 8)), item("object", "refrigerator", (3, 7))])
    assert bl.b5_l3(m, t, STATE_A, draws=50, seed=3) == pytest.approx(1.0)
    # two objects, each a hit where it sits (couch in the living room, oven in the kitchen):
    # identity scores 2 of 2, a swap scores 0 of 2, so the mean is near 0.5
    m2 = member(items=[item("object", "couch", (7, 7)), item("object", "oven", (2, 8))])
    a = bl.b5_l3(m2, t, STATE_A, draws=1000, seed=9)
    assert abs(a - 0.5) < 0.06


def test_random_derangement_has_no_fixed_point():
    rng = np.random.default_rng(0)
    for n in range(2, 9):
        for _ in range(100):
            p = bl.random_derangement(n, rng)
            assert sorted(p.tolist()) == list(range(n))
            assert not np.any(p == np.arange(n))
    with pytest.raises(ValueError):
        bl.random_derangement(1, rng)


def test_d_none_with_fewer_than_two_unobserved_regions():
    t = world()
    one = M.StageState(**{**STATE_A.__dict__, "unobserved": fs(3), "partly_seen": fs(2, 4, 5)})
    assert bl.d_l3(m0(), t, one, seed=1) is None
    none = M.StageState(**{**STATE_A.__dict__, "unobserved": fs()})
    assert bl.d_l3(m0(), t, none, seed=1) is None
    assert bl.d_l3(member(), t, STATE_A, seed=1) is None      # no item, no score


def test_d_swap_of_two_regions_is_exact():
    t = world()
    two = M.StageState(**{**STATE_A.__dict__, "unobserved": fs(3, 4), "partly_seen": fs(2, 5)})
    m = member(items=[item("room", "kitchen", (2, 8)), item("room", "living", (7, 7)), item("object", "oven", (2, 8))])
    assert sl.score_member(m, t, two).l3_hits == 3
    assert bl.d_l3(m, t, two, draws=20, seed=1) == 0.0        # only derangement of two regions is the swap
    m2 = member(items=[item("object", "couch", (2, 8)), item("object", "refrigerator", (7, 7))])
    assert bl.d_l3(m2, t, two, draws=20, seed=1) == pytest.approx(1.0)   # each now judged by the other's content


def test_d_equals_plain_score_when_regions_interchangeable():
    twin = lambda rid, xy: region(rid, {"bedroom"}, [obj(rid * 10, rid, "bed", {"bed", "duvet"}, xy)],
                                  [mark(rid * 10, rid, "bed", {"bedroom"}, {"bed", "duvet"}, xy)])
    boxes = {1: (0, 0, 2, 2), 2: (5, 0, 7, 2), 3: (10, 0, 12, 2)}
    t = BoxTruth(boxes, {1: twin(1, (1, 1)), 2: twin(2, (6, 1)), 3: twin(3, (11, 1))})
    state = M.StageState(seen=fs(), partly_seen=fs(), unobserved=fs(1, 2, 3), mapped_objects=fs(), open_types=fs("bedroom"),
                         open_classes=fs("bed"), open_types_loose=fs(), open_classes_loose=fs())
    m = member(items=[item("room", "bedroom", (1, 1)), item("room", "kitchen", (6, 1)), item("object", "duvet", (11, 1)),
                      item("object", "couch", (11, 1)), item("room", "bedroom", (30, 30))])
    plain = sl.score_member(m, t, state).l3_hits / 5
    assert plain == pytest.approx(2 / 5)
    assert bl.d_l3(m, t, state, draws=50, seed=4) == pytest.approx(plain)
    assert bl.d_score is bl.d_l3


# ------------------------------------------------------------------------- B1 and B4

def test_b1_members_calls_placebo_for_draws_0_to_3():
    calls = []

    def fake(row, k):
        calls.append((row.row_id, k))
        return member(k)
    out = bl.b1_members(mkrow("rowX"), fake)
    assert [m.member for m in out] == [0, 1, 2, 3] and calls == [("rowX", k) for k in range(4)]


def test_placebo_rng_key_is_the_live_arms_first_attempt_key():
    row = mkrow(seed=43, stage=13)
    assert bl.placebo_rng_key(row, 2) == [43, 13, 2]


def test_make_placebo_fn_calls_real_placebo_with_live_seed(monkeypatch):
    lp = bl._load_live_policy()
    obs_raw = {"nodes": [{"id": 1, "name": "bedroom", "node_type": "room", "position": [0.0, 0.0, 1.3]},
                         {"id": 2, "name": "bed", "node_type": "object", "position": [1.0, 0.0, 0.3],
                          "dimension": [1.0, 1.0, 0.5]}], "edges": [[1, 2]]}
    calib = lp.load_calibration()
    fn = bl.make_placebo_fn(lambda row: obs_raw, lambda g, row, k: g)
    row = mkrow(seed=42, stage=8)
    for k in range(4):
        expect = lp.placebo_graph(obs_raw, np.random.default_rng([42, 8, k]), calib)
        assert fn(row, k) == expect
    assert fn(row, 0) != fn(row, 1) or fn(row, 1) != fn(row, 2)      # members differ


def test_b4_partner_rule():
    a = mkrow("a", "00853", 42, "official", 8)
    b = mkrow("b", "00871", 42, "official", 8)
    c = mkrow("c", "00871", 43, "official", 8)
    d = mkrow("d", "00871", 42, "filter_only", 8)
    e = mkrow("e", "00871", 42, "official", 3)
    g = mkrow("g", "00871", 42, "official", 8, rnd=4, gem=True)
    assert bl.b4_partner(a, [a, b, c, d, e, g]).row_id == "b"
    assert bl.b4_partner(b, [a, b, c, d, e, g]).row_id == "a"
    assert bl.b4_partner(c, [a, b, c, d, e]) is None
    assert bl.b4_partner(g, [a, b, g]) is None                         # a Gemini row has no partner
    with pytest.raises(ValueError):
        bl.b4_partner(a, [a, b, mkrow("b2", "00871", 42, "official", 8)])


def test_b4_scores_partner_members_against_this_rows_truth():
    t = world()
    a = mkrow("a", "00853", 42, "official", 8)
    b = mkrow("b", "00871", 42, "official", 8)
    partner_members = {"b": [member(0, l1={"kitchen"}, l2={"oven"}), member(1, l1={"bedroom"}, l2={"bed"}), member(2)]}
    out = bl.b4_scores(a, [a, b], partner_members, t, STATE_A)     # a's state: kitchen is open, bedroom is not
    assert out["0"]["L1"] == 1.0 and out["0"]["L2"] == 1.0
    assert out["1"]["L1"] == 0.0 and out["1"]["L2"] == 0.0
    assert out["2"] == {"L1": None, "L2": None, "L3": None}
    assert bl.b4_scores(a, [a], partner_members, t, STATE_A) == {}
    assert bl.b4_scores(a, [a, b], {}, t, STATE_A) == {}


# ------------------------------------------------------------------------ averaging

def rec(cluster, model_scores, comps=None, possible=(True, True, True), seed=42, arm="official", scene="00853"):
    return {"row_id": f"{cluster}-{id(model_scores)}", "cluster": cluster, "scene": scene, "seed": seed, "arm": arm,
            "stage": 8, "round": 1, "is_gemini_row": False,
            "possible": dict(zip(("L1", "L2", "L3"), possible)), "n_unobserved": 3,
            "model": {str(k): v for k, v in model_scores.items()}, "comparators": comps or {}}


def L1(x):
    return {"L1": x}


def test_averaging_member_row_cluster_with_missing_and_impossible():
    rows = [
        rec("A", {0: L1(0.5), 1: L1(None), 2: L1(1.0)},
            {"B3": {0: L1(0.25), 1: L1(0.9), 2: L1(0.5)}, "B1": {0: L1(0.5), 1: L1(None), 2: L1(0.25)}}),
        rec("A", {0: L1(None)}, {"B3": {0: L1(0.1)}}),                                  # no member has a score
        rec("A", {0: L1(1.0)}, {"B3": {0: L1(0.0)}}, possible=(False, True, True)),     # impossible at L1
        rec("B", {0: L1(0.5)}, {"B3": {0: L1(0.1)}, "B1": {}}),
    ]
    res = rs.analyse(rows, "m", levels=("L1",))["levels"]["L1"]
    assert res["n_rows"] == 4 and res["n_rows_impossible"] == 1
    assert res["model_cluster_scores"] == pytest.approx({"A": 0.75, "B": 0.5})
    b3 = res["comparators"]["B3"]
    # A: members 0 and 2 shared: mean(.25, .5) = .375; B: .4
    assert b3["clusters"] == pytest.approx({"A": 0.375, "B": 0.4}) and b3["n_clusters"] == 2
    assert b3["mean_diff"] == pytest.approx(0.3875) and b3["p"] == pytest.approx(0.25)
    # B1 is paired with the row: A: .75 - mean(.5,.25) = .375. Cluster B has no B1 score: it leaves the contrast
    b1 = res["comparators"]["B1"]
    assert b1["clusters"] == pytest.approx({"A": 0.375}) and b1["n_clusters"] == 1 and b1["p"] == pytest.approx(0.5)
    assert res["comparators"]["B2"]["n_clusters"] == 0 and res["comparators"]["B2"]["p"] is None


def test_pairing_rule_cluster_without_shared_row_leaves_contrast():
    # member-paired: the model scores member 0, the comparator only member 1 -> no shared member, no contrast
    rows = [rec("A", {0: L1(0.5)}, {"B3": {1: L1(0.1)}}), rec("B", {0: L1(0.6)}, {"B3": {0: L1(0.2)}})]
    b3 = rs.analyse(rows, "m", levels=("L1",))["levels"]["L1"]["comparators"]["B3"]
    assert b3["n_clusters"] == 1 and list(b3["clusters"]) == ["B"]


def test_analyse_p_and_interval_all_positive():
    rows = [rec(c, {0: L1(0.6 + 0.01 * i)}, {"B3": {0: L1(0.1)}}) for i, c in enumerate("ABCD")]
    b3 = rs.analyse(rows, "m", levels=("L1",))["levels"]["L1"]["comparators"]["B3"]
    assert b3["p"] == pytest.approx(1 / 16) and len(b3["ci"]) == 2 and b3["ci"][0] <= b3["mean_diff"] <= b3["ci"][1]


def b4_world(diff):
    """12 clusters: scene x seed x arm; B4 score chosen so that model - B4 = diff(scene, seed, arm)."""
    rows = []
    for scene in ("00853", "00871"):
        for seed in (42, 43, 44):
            for arm in ("official", "filter_only"):
                d = diff(scene, seed, arm)
                rows.append(rec(f"{scene}_s{seed}_{arm}", {0: L1(0.5)}, {"B4": {"0": L1(0.5 - d)}},
                                seed=seed, arm=arm, scene=scene))
    return rows


def test_b4_pairs_are_means_of_the_two_clusters():
    diff = lambda sc, sd, arm: 0.1 * (sd - 41) + (0.02 if sc == "00871" else 0.0) + (0.05 if arm == "filter_only" else 0.0)
    out = rs.analyse(b4_world(diff), "m", levels=("L1",))["levels"]["L1"]["comparators"]["B4"]
    assert out["p"] is None and out["n_clusters"] == 12            # the dependent clusters get no test here
    assert sorted(out["pairs"]) == sorted(f"s{s}_{a}" for s in (42, 43, 44) for a in ("official", "filter_only"))
    for s in (42, 43, 44):
        for a in ("official", "filter_only"):
            assert out["pairs"][f"s{s}_{a}"] == pytest.approx(0.1 * (s - 41) + 0.01 + (0.05 if a == "filter_only" else 0))
    gate = rs.wrong_house_gate(out["pairs"])
    assert gate["n_pairs"] == 6 and gate["p"] == pytest.approx(1 / 64) and gate["pass"] is True


def brute_p(vals):
    obs = sum(vals)
    n = sum(1 for sg in itertools.product((1, -1), repeat=len(vals)) if sum(a * b for a, b in zip(sg, vals)) >= obs - 1e-12)
    return n / 2 ** len(vals)


def test_wrong_house_gate_over_six_pairs():
    five_one = {f"p{i}": v for i, v in enumerate([0.1] * 5 + [-0.1])}
    g = rs.wrong_house_gate(five_one)
    assert g["p"] == pytest.approx(brute_p(list(five_one.values()))) == pytest.approx(7 / 64) and g["pass"] is False
    g = rs.wrong_house_gate({f"p{i}": v for i, v in enumerate([0.1, 0.1, 0.1, 0.1, 0.1, -0.05])})
    assert g["p"] == pytest.approx(2 / 64) and g["pass"] is True        # still below .05
    g = rs.wrong_house_gate({f"p{i}": 0.1 for i in range(6)})
    assert g["p"] == pytest.approx(1 / 64) and g["pass"] is True
    g = rs.wrong_house_gate({f"p{i}": 0.1 for i in range(3)})
    assert g["p"] == pytest.approx(1 / 8) and g["pass"] is False        # three pairs can never pass
    assert rs.wrong_house_gate({}) == {"n_pairs": 0, "p": None, "pass": False}


# -------------------------------------------------------------------------- the family

HYP = rs.HYPOTHESIS_COMPARATORS


def mkres(p, upper, pairs=None, levels=("L1", "L2", "L3")):
    """analyse()-shaped result. p, upper: {level: value}; pairs: {level: {pair: value}}."""
    out = {"levels": {}}
    for lv in levels:
        comps = {c: {"p": p[lv], "ci": (-1.0, 1.0)} for c in HYP[lv]}
        comps[rs.NAMED_COMPARATOR[lv]] = {"p": p[lv], "ci": (-1.0, upper[lv])}
        comps["B4"] = {"pairs": (pairs or {}).get(lv, {})}
        out["levels"][lv] = {"comparators": comps}
    return out


def test_hypothesis_p_is_largest_over_comparators_then_holm():
    def res(ps):
        r = {"levels": {}}
        for lv, per in ps.items():
            r["levels"][lv] = {"comparators": {c: {"p": p, "ci": (-1, 1)} for c, p in zip(HYP[lv], per)}}
        return r
    a = res({"L1": (0.005, 0.01), "L2": (0.02, 0.01), "L3": (0.03, 0.01, 0.02)})
    b = res({"L1": (0.2, 0.1), "L2": (0.04, 0.001), "L3": (0.5, 0.2, 0.1)})
    fam = rs.family({"A": a, "B": b}, claude_models=[])
    raw = {k: v["p"] for k, v in fam["hypotheses"].items()}
    assert raw == {"A|L1": 0.01, "A|L2": 0.02, "A|L3": 0.03, "B|L1": 0.2, "B|L2": 0.04, "B|L3": 0.5}
    adj = {k: v["p_holm"] for k, v in fam["hypotheses"].items()}
    assert adj == pytest.approx({"A|L1": 0.06, "A|L2": 0.10, "A|L3": 0.12, "B|L2": 0.12, "B|L1": 0.4, "B|L3": 0.5})
    assert fam["m_hypotheses"] == 6 and fam["thesis"] is None


def test_significant_and_inside_margin_is_supported_not_rejected():
    r = mkres({"L3": 0.001}, {"L3": 0.01}, levels=("L3",))        # upper end below delta .03, and p tiny
    h = rs.family({"claude-x": r})["hypotheses"]["claude-x|L3"]
    assert h["verdict"] == "Supported" and h["named"] == "D" and h["delta"] == 0.03


def test_rejected_inconclusive_and_named_comparator():
    f = lambda p, up, lv="L3": rs.family({"claude-x": mkres({lv: p}, {lv: up}, levels=(lv,))})["hypotheses"][f"claude-x|{lv}"]
    assert f(0.9, 0.02)["verdict"] == "Rejected"
    assert f(0.9, 0.03)["verdict"] == "Inconclusive"          # equal to delta is not below it
    assert f(0.9, 0.04, "L1")["verdict"] == "Rejected"        # delta .05 at L1
    assert f(0.9, 0.05, "L2")["verdict"] == "Inconclusive"
    r = mkres({"L3": 0.9}, {"L3": 0.02}, levels=("L3",))
    r["levels"]["L3"]["comparators"]["B5"]["ci"] = (-1, 0.5)   # a wide B5 interval does not matter: D is named
    assert rs.family({"claude-x": r})["hypotheses"]["claude-x|L3"]["verdict"] == "Rejected"
    r["levels"]["L3"]["comparators"]["D"]["ci"] = (-1, 0.5)
    assert rs.family({"claude-x": r})["hypotheses"]["claude-x|L3"]["verdict"] == "Inconclusive"


def test_missing_comparator_cannot_be_supported():
    r = mkres({"L3": 1e-9}, {"L3": 0.0}, levels=("L3",))
    r["levels"]["L3"]["comparators"]["B3L"] = {"p": None, "ci": None}
    h = rs.family({"claude-x": r})["hypotheses"]["claude-x|L3"]
    assert h["missing"] == ["B3L"] and h["p"] == 1.0 and h["verdict"] == "Rejected"   # p is 1; interval still below delta
    r["levels"]["L3"]["comparators"]["D"] = {"p": None, "ci": None}
    assert rs.family({"claude-x": r})["hypotheses"]["claude-x|L3"]["verdict"] == "Inconclusive"


GOOD = [0.1] * 6
BAD = [0.1, -0.1, 0.1, -0.1, 0.1, -0.1]


def pairs_of(vals):
    return {f"p{i}": v for i, v in enumerate(vals)}


def two_models(spec):
    """spec: {(model, level): ('S'|'R'|'I', gate_pairs or None)}."""
    out = {}
    for m in ("claude-opus-5-5", "claude-haiku-5-5"):
        p, up, pr = {}, {}, {}
        for lv in ("L1", "L2", "L3"):
            kind, pairs = spec.get((m, lv), ("I", None))
            p[lv] = 1e-9 if kind == "S" else 0.9
            up[lv] = 0.0 if kind == "R" else 0.5
            if pairs is not None:
                pr[lv] = pairs_of(pairs)
        out[m] = mkres(p, up, pr)
    return out


def thesis(spec):
    return rs.family(two_models(spec))["thesis"]


O, H = "claude-opus-5-5", "claude-haiku-5-5"


def test_thesis_four_outcomes():
    assert thesis({(O, "L3"): ("S", None)}) == "The claim holds"
    # no L3; Haiku Supported at L1 with the gate passed
    assert thesis({(H, "L1"): ("S", GOOD)}) == "Mixed"
    # Supported at L2 but the gate fails: not mixed
    assert thesis({(H, "L2"): ("S", BAD)}) == "Inconclusive"
    # the gate at the other level does not count
    assert thesis({(H, "L1"): ("S", BAD), (H, "L2"): ("I", GOOD)}) == "Inconclusive"
    assert thesis({(O, "L2"): ("R", None), (O, "L3"): ("R", None), (H, "L2"): ("R", None), (H, "L3"): ("R", None)}) == "The claim fails"
    assert thesis({(O, "L2"): ("R", None), (O, "L3"): ("R", None), (H, "L2"): ("R", None)}) == "Inconclusive"
    assert thesis({}) == "Inconclusive"
    # L3 Supported wins over everything
    assert thesis({(O, "L3"): ("S", None), (H, "L1"): ("S", GOOD)}) == "The claim holds"


def test_family_gate_reads_pairs_for_each_model_and_level():
    fam = rs.family(two_models({(H, "L1"): ("S", GOOD), (O, "L2"): ("I", BAD)}))
    g = fam["wrong_house_gate"]
    assert g[f"{H}|L1"]["pass"] is True and g[f"{O}|L2"]["pass"] is False and f"{H}|L3" not in g


def test_family_from_analyse_output_end_to_end():
    rows = [rec(c, {0: L1(0.6 + 0.01 * i)}, {"B3": {0: L1(0.1)}, "B1": {0: L1(0.2)}}) for i, c in enumerate("ABCDE")]
    res = rs.analyse(rows, "claude-x", levels=("L1",))
    h = rs.family({"claude-x": res})["hypotheses"]["claude-x|L1"]
    assert h["p"] == pytest.approx(1 / 32) and h["verdict"] == "Supported"      # m = 1 hypothesis: Holm leaves it


# ----------------------------------------------------------------------------- MDD

def test_mdd_table_from_placebo_members():
    z = statistics.NormalDist().inv_cdf
    recs = [
        rec("A", {0: L1(0.5), 1: L1(0.3)}, {"B3": {0: L1(0.2), 1: L1(0.3)}, "B5": {0: {"L3": 0.5}}, "D": {0: {"L3": 0.3}}}),
        rec("B", {0: L1(0.4)}, {"B3": {0: L1(0.3)}, "B5": {0: {"L3": 0.2}}, "D": {0: {"L3": 0.2}}}),
        rec("C", {0: L1(0.9)}, {"B3": {0: L1(0.3)}, "B5": {0: {"L3": 0.6}}, "D": {0: {"L3": 0.1}}}),
        rec("D", {0: L1(0.1)}, {"B3": {0: L1(0.5)}, "B5": {0: {"L3": 0.3}}, "D": {0: {"L3": None}}}),   # no D: leaves L3
    ]
    t = rs.mdd_table(recs)
    d = [0.15, 0.1, 0.6, -0.4]                                          # L1: A is mean(.3, 0)
    assert t["L1"]["contrast"] == "B1-B3" and t["L1"]["n_clusters"] == 4
    sd = statistics.stdev(d)
    assert t["L1"]["sd"] == pytest.approx(sd)
    assert t["L1"]["mdd"] == pytest.approx((z(1 - 0.05 / 6) + z(0.8)) * sd / 2.0)
    lo, hi = st.sign_flip_ci(d, 0.95, "two-sided")
    assert t["L1"]["ci"] == (lo, hi)
    d3 = [0.2, 0.0, 0.5]
    assert t["L3"]["contrast"] == "B5-D" and t["L3"]["n_clusters"] == 3
    assert t["L3"]["mdd"] == pytest.approx((z(1 - 0.05 / 6) + z(0.8)) * statistics.stdev(d3) / math.sqrt(3))
    assert t["L2"]["n_clusters"] == 0 and t["L2"]["mdd"] is None


# ------------------------------------------------------------ run() with fakes, and CLI

class Boom:
    def __getattr__(self, name):
        raise AssertionError(f"model output was touched: {name}")


class Reached(Exception):
    pass


def guard_files(monkeypatch, tmp_path, text="the frozen text"):
    md = tmp_path / "PRE.md"
    md.write_text(text)
    sha = hashlib.sha256(md.read_bytes()).hexdigest()
    hashfile = tmp_path / "PRE.sha256"
    hashfile.write_text(sha.upper() + "  PRE.md\n")
    freeze = tmp_path / "FREEZE.sha256"
    monkeypatch.setattr(rs, "PREREG_MD_PATH", md)
    monkeypatch.setattr(rs, "PREREG_HASH_PATH", hashfile)
    monkeypatch.setattr(rs, "FREEZE_PATH", freeze)
    return md, hashfile, freeze, sha


def test_guards_refuse_before_touching_model_output(monkeypatch, tmp_path):
    md, hashfile, freeze, sha = guard_files(monkeypatch, tmp_path)
    monkeypatch.setattr(rs, "extract_preds", Boom())
    monkeypatch.setattr(rs, "region_truth", Boom())
    monkeypatch.setattr(rs, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("run was called")))
    out = tmp_path / "o"
    base = ["--models", "deepseek", "--out", str(out)]
    with pytest.raises(SystemExit) as e:
        rs.main(base)                                          # no hash given
    assert "refused" in str(e.value)
    with pytest.raises(SystemExit):
        rs.main(base + ["--prereg-sha256", "deadbeef"])        # wrong hash
    # right hash, Claude model, no freeze file
    with pytest.raises(SystemExit) as e:
        rs.main(["--models", "deepseek,claude-opus-5-5", "--out", str(out), "--prereg-sha256", sha])
    assert "FREEZE" in str(e.value)
    # the pre-registration text was edited after it was hashed
    md.write_text("an edited text")
    with pytest.raises(SystemExit) as e:
        rs.main(base + ["--prereg-sha256", sha])
    assert "edited" in str(e.value)
    with pytest.raises(SystemExit):
        rs.main(base + ["--prereg-sha256", sha, "--dry"])     # the dry run is guarded too
    md.write_text("the frozen text")
    hashfile.unlink()
    with pytest.raises(SystemExit):
        rs.main(base + ["--prereg-sha256", sha])               # the pre-registration is not hashed
    assert not out.exists()


def test_guards_pass_with_hash_and_freeze(monkeypatch, tmp_path):
    md, hashfile, freeze, sha = guard_files(monkeypatch, tmp_path)
    seen = []

    def fake_run(models, frame, rounds=None, **kw):
        seen.append((list(models), rounds, kw.get("claude_root")))
        raise Reached

    monkeypatch.setattr(rs, "run", fake_run)
    out = tmp_path / "o"
    with pytest.raises(Reached):                               # a non-Claude model needs no freeze
        rs.main(["--models", "deepseek", "--out", str(out), "--prereg-sha256", sha.upper()])
    assert seen == [(["deepseek"], None, None)]
    with pytest.raises(SystemExit):                            # Claude: freeze file missing
        rs.main(["--models", "claude-haiku-5-5", "--out", str(out), "--prereg-sha256", sha, "--claude-root", "/c"])
    sem = tmp_path / "repo" / "tools" / "live_policy" / "semantic"      # a tiny frozen tree for the real freeze check
    (sem / "truth").mkdir(parents=True)
    for name in ("canon_labels.json", "sample_frame.txt"):
        (sem / name).write_text("x")
    monkeypatch.setattr(rs, "FREEZE_SEMANTIC_DIR", sem)
    monkeypatch.setattr(rs, "FREEZE_REPO", tmp_path / "repo")
    rs._sibling("freeze").write(freeze, sem, tmp_path / "repo")
    with pytest.raises(SystemExit) as e:                       # Claude: no root of parsed outputs
        rs.main(["--models", "claude-haiku-5-5", "--out", str(out), "--prereg-sha256", sha])
    assert "claude-root" in str(e.value)
    with pytest.raises(Reached):
        rs.main(["--models", "claude-haiku-5-5", "--out", str(out), "--prereg-sha256", sha, "--rounds", "1,2",
                 "--claude-root", "/c"])
    assert seen[-1] == (["claude-haiku-5-5"], [1, 2], "/c")
    with pytest.raises(SystemExit):
        rs.main(["--models", "gpt", "--out", str(out), "--prereg-sha256", sha])      # unknown model


def test_observed_path_follows_the_frame(monkeypatch, tmp_path):
    fake = types.SimpleNamespace(_frame_index=lambda p: {"r1": ("runX", 8, 1)}, FRAME_PATH="frame", RUNS_ROOT=tmp_path)
    monkeypatch.setattr(rs, "extract_preds", fake)
    p = rs.observed_path(mkrow("r1"))
    assert p == tmp_path / "runX" / "stages" / "8" / "habitat_scene_graph_original_graph0.yaml"
    assert rs.observed_path(mkrow("r1"), tmp_path / "other").parent.parent.parent.parent == tmp_path / "other"


def fake_ctx(tmp_path, rows=None):
    t = world()
    a = mkrow("a", "00853", 42, "official", 8)
    b = mkrow("b", "00871", 42, "official", 8)
    states = {"a": STATE_A, "b": STATE_B}
    summary = write_summary(tmp_path)
    prior = bl.Prior(summary)
    return types.SimpleNamespace(
        rows=rows or [a, b], truths={"00853": t, "00871": t}, truths_primary={"00853": t, "00871": t},
        states=states, states_primary=states, prior=prior, prior_primary=prior, run_of_row={"a": "run", "b": "run"},
        runs_root=tmp_path, frame=tmp_path / "frame.txt", timing={})


def fake_inputs():
    deep = {"a": [member(0, l1={"kitchen"}, l2={"oven"}, items=[item("room", "kitchen", (2, 8))]),
                  member(1, l1={"bedroom"}, l2={"bed"}, items=[item("room", "bedroom", (2, 2))])],
            "b": [member(0, l1={"bedroom"}, l2={"bed"}, items=[item("room", "bedroom", (2, 2))])]}
    pm = {r: [member(k, l1={"kitchen"}, l2={"oven"}, items=[item("room", "kitchen", (2, 8))]) for k in range(4)] for r in "ab"}
    return deep, pm


def test_run_core_end_to_end_with_fakes(tmp_path):
    ctx = fake_ctx(tmp_path)
    deep, pm = fake_inputs()
    inputs = {"deepseek": (deep, {}, None, {}), "claude-opus-5-5": (deep, {}, None, {"a": ALL_OK, "b": ALL_OK})}
    out = rs.run_core(ctx, ["deepseek", "claude-opus-5-5"], inputs, (pm, {}), None, True, False)
    ds = out["models"]["deepseek"]
    assert ds["role"] == "exploratory" and len(ds["records"]) == 2
    ra, rb = ds["records"]
    assert ra["model"]["0"]["L1"] == 1.0 and ra["model"]["1"]["L1"] == 0.0
    assert ra["possible"] == {"L1": True, "L2": True, "L3": True}
    assert set(ra["comparators"]) >= {"B3", "B3L", "B5", "D", "B1", "B2", "B4", "B3_seen", "B3_size", "B3_seen_size"}
    # a's partner is b: b's member (claims bedroom, bed) scored against a's state (STATE_A: neither open)
    assert ra["comparators"]["B4"]["0"]["L1"] == 0.0
    assert set(ra["comparators"]["B1"]) == {"0", "1", "2", "3"} and ra["comparators"]["B5"]["0"]["L3"] is not None
    assert out["finished_rounds"] == [1] and out["family"]["thesis"] is not None
    assert out["models"]["claude-opus-5-5"]["role"] == "confirmatory"
    assert set(out["mdd"]) == {"L1", "L2", "L3"}
    assert set(ds["secondary"]) == {"loose", "l3_partly_seen", "detector_vocab", "synonym_primary_only"}
    assert set(ds["exploratory_family"]["hypotheses"]) == {"deepseek|L1", "deepseek|L2", "deepseek|L3"}
    json.dumps(rs._jsonable({k: v for k, v in out.items() if k not in ("ctx", "members")}))   # serialisable


def sts(*s):
    return {k: v for k, v in enumerate(s)}


ALL_OK = sts("ok", "ok", "ok", "ok")
ALL_DROPPED = sts("dropped", "dropped", "dropped", "dropped")


def test_finished_rounds_come_from_member_statuses():
    r1, r2, r3 = mkrow("a", rnd=1), mkrow("b", rnd=2), mkrow("c", rnd=3)
    # a row whose four members were all dropped stays in its round (a final drop; the row has no score)
    assert rs.finished_rounds([r1], {"m": {"a": ALL_DROPPED}}) == [1]
    # one member present and three absent: the replay has not finished the row, so the round is not finished
    assert rs.finished_rounds([r1, r2], {"m": {"a": ALL_OK, "b": sts("ok", "absent", "absent", "absent")}}) == [1]
    # an unfinished member (cap stop, error) is not a drop
    assert rs.finished_rounds([r1], {"m": {"a": sts("ok", "ok", "ok", "unfinished")}}) == []
    # a mix of ok and dropped is finished
    assert rs.finished_rounds([r1], {"m": {"a": sts("ok", "dropped", "ok", "dropped")}}) == [1]
    # a row the replay never wrote has no statuses: not finished
    assert rs.finished_rounds([r1, r2], {"m": {"a": ALL_OK}}) == [1]
    # the analysis set is the rounds finished for BOTH models
    both = {"m1": {"a": ALL_OK, "b": ALL_OK, "c": ALL_DROPPED}, "m2": {"a": ALL_OK, "b": sts("ok", "ok", "absent", "ok"), "c": ALL_OK}}
    assert rs.finished_rounds([r1, r2, r3], both) == [1, 3]
    assert rs.finished_rounds([r1, r2], {}) == [1, 2]            # no model asked: nothing holds a round back


def test_run_core_takes_finished_rounds_from_statuses_not_member_counts(tmp_path):
    ctx = fake_ctx(tmp_path)
    deep, pm = fake_inputs()
    deep = {"a": [], "b": deep["b"]}                             # row a: every member dropped
    st_ok = {"a": ALL_DROPPED, "b": sts("ok", "dropped", "dropped", "dropped")}
    out = rs.run_core(ctx, ["claude-opus-5-5"], {"claude-opus-5-5": (deep, {}, None, st_ok)}, (pm, {}), None, True, False)
    assert out["finished_rounds"] == [1] and out["rounds_used"] == [1]
    assert len(out["models"]["claude-opus-5-5"]["records"]) == 2     # the dropped row is still a row
    st_cut = {"a": ALL_DROPPED, "b": sts("ok", "absent", "absent", "absent")}
    out = rs.run_core(ctx, ["claude-opus-5-5"], {"claude-opus-5-5": (deep, {}, None, st_cut)}, (pm, {}), None, True, False)
    assert out["finished_rounds"] == []


def test_run_refuses_when_auto_finds_no_finished_round(monkeypatch, tmp_path):
    ctx = fake_ctx(tmp_path)
    deep, pm = fake_inputs()
    cut = {"a": sts("ok", "absent", "absent", "absent"), "b": ALL_OK}
    monkeypatch.setattr(rs, "build_context", lambda *a, **k: ctx)
    monkeypatch.setattr(rs, "placebo_inputs", lambda c: (pm, {}))
    monkeypatch.setattr(rs, "model_inputs", lambda c, m, root, p: (deep, {}, None, cut))
    monkeypatch.setattr(rs, "run_core", lambda *a, **k: (_ for _ in ()).throw(AssertionError("scored with no finished round")))
    with pytest.raises(SystemExit) as e:
        rs.run(["claude-opus-5-5"], tmp_path / "frame.txt", None, runs_root=tmp_path, claude_root=tmp_path)
    assert "no round" in str(e.value) and "--rounds" in str(e.value)
    with pytest.raises(AssertionError):                           # an explicit --rounds is the analyst's choice
        rs.run(["claude-opus-5-5"], tmp_path / "frame.txt", [1], runs_root=tmp_path, claude_root=tmp_path)


# ======================================================================================
# Added with the wiring of run_semantic.py: each test below would have caught a mismatch between a
# module and the frozen spec, or covers a §11 readout.
# ======================================================================================

# ---- §7 and item 51: dining is left out of L1 and of L3 (mismatch: it was an L3 item)

def test_possible_l1_ignores_an_open_dining_room():
    only_dining = M.StageState(**{**STATE_A.__dict__, "open_types": fs("dining"), "open_type_regions": {}})
    assert not sl.possible("L1", world(), only_dining)          # dining is never scored (§5.2, §7)
    both = M.StageState(**{**STATE_A.__dict__, "open_types": fs("dining", "kitchen")})
    assert sl.possible("L1", world(), both)


def test_b3l_never_gives_a_room_the_label_dining():
    # §9: "at L1 the labels are the five scored room types". With dining standing as a sixth type, an observed
    # map that holds all five scored types made the prior's best room label "dining".
    obs = observed(rooms=["bathroom", "bedroom", "kitchen", "laundry", "living"])
    p = bl.Prior.__new__(bl.Prior)
    p.room_n = {t: [1, 1, 1] for t in M.REPORTED_ROOM_TYPES}
    p.room_n["dining"] = [2, 2, 2]                              # dining would win: its share above m = 0 is 1
    p.class_n, p.holders, p.n_houses = {}, {"room": {t: 3 for t in M.REPORTED_ROOM_TYPES}, "object": {}}, 3
    items = [item("room", "kitchen", (0, 0)), item("room", "bedroom", (1, 1))]
    out = bl.b3l_items(p, obs, member(0, items=items))
    assert all(i.label in M.ROOM_TYPES for i in out)


# ---- §5.5 second rule reaches l1_matched (mismatch: it used "reaches" alone)

def test_l1_matched_follows_the_open_regions_of_stage_state():
    t = world()
    rooms = [node(1, "room", (0, 0), room_type="kitchen"), node(2, "room", (0, 0), room_type="kitchen")]
    mm = member(l1={"kitchen"}, rooms=rooms)
    two = M.StageState(**{**STATE_A.__dict__, "open_type_regions": {"kitchen": fs(3, 5)}})
    assert sl.score_member(mm, t, two).extra["l1_matched"] == 1.0        # two kitchens, two open regions
    one = M.StageState(**{**STATE_A.__dict__, "open_type_regions": {"kitchen": fs(3)}})
    assert sl.score_member(mm, t, one).extra["l1_matched"] == 0.5
    none = M.StageState(**{**STATE_A.__dict__, "open_types": fs(), "open_type_regions": {}})
    assert sl.score_member(mm, t, none).extra["l1_matched"] == 0.0       # a state with no open type: no fallback


# ---- §10: the family is six hypotheses, whatever was run

def test_family_holm_counts_six_when_only_one_registered_model_ran():
    r = mkres({"L1": 0.004, "L2": 0.9, "L3": 0.9}, {"L1": 0.5, "L2": 0.5, "L3": 0.5})
    fam = rs.family({"claude-opus-5-5": r})
    h = fam["hypotheses"]["claude-opus-5-5|L1"]
    assert h["p"] == 0.004 and h["p_holm"] == pytest.approx(0.024)       # x 6, not x 3
    assert fam["m_hypotheses"] == 6
    assert "claude-haiku-5-5|L1" not in fam["hypotheses"]


def test_the_claim_fails_needs_both_registered_models():
    r = mkres({lv: 0.9 for lv in ("L1", "L2", "L3")}, {"L1": 0.5, "L2": 0.0, "L3": 0.0})
    assert rs.family({"claude-opus-5-5": r})["thesis"] == "Inconclusive"
    assert rs.family({"claude-opus-5-5": r, "claude-haiku-5-5": r})["thesis"] == "The claim fails"


# ---- §11: the labels switch, B3's two sensitivity forms

def test_prior_variants_seen_counts_and_size_third(prior):
    obs = observed()
    base = prior.room_scores(obs)
    seen = prior.room_scores(obs, counts={"bedroom": 2})                 # two bedrooms seen: m = 2
    n_bed = prior.room_n["bedroom"]
    ge = [n for n in n_bed if n >= 2]
    assert seen["bedroom"] == pytest.approx(sum(1 for n in ge if n > 2) / len(ge))
    cls = prior.class_scores(obs, counts={"bed": 3})
    assert cls["bed"] == bl._share_above(prior.class_n["bed"], 3)
    third = prior.size_third(2)
    assert set(third) <= set(range(prior.n_houses)) and len(third) >= 1
    assert prior.room_scores(obs, houses=third)["kitchen"] == bl._share_above([prior.room_n["kitchen"][i] for i in third], 0)
    # every house falls in exactly one third
    parts = {tuple(prior.size_third(n)) for n in (0, 1, 2, 3, 4, 100)}
    assert sorted(i for p in parts for i in p) == list(range(prior.n_houses))


def test_seen_counts_from_the_truth():
    room_m, class_n = bl.seen_counts(world(), STATE_A)
    assert room_m == {"bedroom": 1} and class_n == {"bed": 1, "duvet": 1, "toilet": 1}   # seen region 1; mapped objects 1 and 3


def test_b3_member_sensitivity_arguments(prior):
    obs = observed()
    m = member(0, l1={"kitchen", "bedroom"}, l2={"bed", "oven"})
    plain = bl.b3_member(prior, obs, m)
    seen = bl.b3_member(prior, obs, m, room_counts={"bedroom": 3, "kitchen": 3, "bathroom": 3, "living": 3, "laundry": 0})
    assert len(plain.l1_claims) == 2 and len(seen.l1_claims) == 2
    det = bl.b3_member(prior, obs, m, allowed={"oven", "couch"})
    assert det.l2_claims <= fs("oven", "couch") and len(det.l2_claims) == 2


# ---- §11: the placement-error sample of PREREGISTRATION_M2.md F3-m

def test_placement_errors_unmapped_unseen_same_class():
    t = world()
    objs = [node(1, "object", (1, 8), canon="oven"),              # oven at (1,7) in unobserved region 3: 1.0 m
            node(2, "object", (3, 3), canon="fridge"),            # fridge at (3,7), answers fridge: 4.0 m
            node(3, "object", (7, 5), canon="toilet"),            # toilet 3 is mapped: no such object: left out
            node(4, "object", (0, 0), canon="bed"),               # bed 1 is mapped and in a seen region: left out
            node(5, "object", (5, 5), canon=None),                # no class: neither a distance nor left out
            node(6, "object", (2, 8), canon="couch")]             # couch at (7,7): 5.099 m
    d, left = sl.placement_errors(member(objects=objs), t, STATE_A)
    assert sorted(round(x, 3) for x in d) == [1.0, 4.0, 5.099] and left == 2
    # the nearest of several; horizontal only (z plays no part)
    two = [node(7, "object", (7, 7), canon="couch")]
    assert sl.placement_errors(member(objects=two), t, STATE_A) == ([0.0], 0)
    # a state that has seen everything: nothing to measure against, every classed guess is left out
    seen_all = M.StageState(**{**STATE_A.__dict__, "partly_seen": fs(), "unobserved": fs()})
    assert sl.placement_errors(member(objects=objs), t, seen_all) == ([], 5)


def test_placement_errors_use_answers_to_of_the_class():
    t = world()
    # a "refrigerator" guess finds the object whose raw name is fridge and answers to refrigerator too
    d, left = sl.placement_errors(member(objects=[node(1, "object", (3, 7.5), canon="refrigerator")]), t, STATE_A)
    assert d == [0.5] and left == 0


# ---- §11 secondary readouts, through secondary_records

def test_secondary_views_rescore_under_their_own_rule(tmp_path):
    ctx = fake_ctx(tmp_path)
    mm = member(0, l1={"bathroom"}, l2={"oven", "toilet"},
                items=[item("room", "bathroom", (6, 1)), item("object", "oven", (1, 7)), item("object", "toilet", (6, 1))])
    deep = {"a": [mm], "b": []}
    pm = {r: [member(k) for k in range(4)] for r in "ab"}
    v = rs.secondary_records(ctx, "deepseek", deep, pm)
    assert set(v) == {"loose", "l3_partly_seen", "detector_vocab", "synonym_primary_only"}
    ra = rs.build_record(ctx.rows[0], ctx.truths["00853"], STATE_A, [mm], ctx.prior)["model"]["0"]
    assert ra["L1"] == 0.0                                    # bathroom: region 2 is only partly seen, so not open
    loose = v["loose"][0]["model"]["0"]
    assert loose["L1"] == 1.0                                 # the plan's looser rule: an unseen bathroom exists
    assert loose["L2"] == pytest.approx(1.0)                  # oven open; toilet: an unseen region holds it (loose)
    assert ra["L2"] == 0.5                                    # toilet is mapped, so not open
    assert ra["L3"] == pytest.approx(1 / 3)                   # only the oven item lands in an unobserved region
    part = v["l3_partly_seen"][0]["model"]["0"]
    assert part["L3"] == pytest.approx(2 / 3)                 # the bathroom room and the toilet reach partly seen region 2
    det = v["detector_vocab"][0]["model"]["0"]
    assert det["L2"] == 1.0 and det["counts"]["l2_n"] == 1    # toilet is not a detector word here
    assert det["counts"]["l3_n"] == 1                         # room items are not detector words
    assert v["detector_vocab"][0]["comparators"]["B3"]["0"]["L2"] is not None
    # the views keep the row's metadata, so analyse() accepts them
    assert v["loose"][0]["cluster"] == "00853_s42_official" and v["loose"][0]["possible"]["L3"] is True
    out = rs.analyse_views(v, "deepseek", rs.view_specs(ctx))
    assert set(out["detector_vocab"]["levels"]) == {"L2", "L3"} and set(out["loose"]["levels"]) == {"L1", "L2"}


def test_sensitivity_comparators_are_member_paired_and_in_the_record(tmp_path):
    ctx = fake_ctx(tmp_path)
    deep, pm = fake_inputs()
    kw = rs.sensitivity_kwargs(ctx, ctx.rows[0])
    assert set(kw) == {"B3_seen", "B3_size", "B3_seen_size"} and "houses" in kw["B3_size"] and "room_counts" in kw["B3_seen"]
    rec = rs.build_record(ctx.rows[0], ctx.truths["00853"], STATE_A, deep["a"], ctx.prior, pm["a"], {}, sens=kw)
    for name in rs.SENSITIVITY_B3:
        assert set(rec["comparators"][name]) == {"0", "1"}
        assert name in rs.MEMBER_PAIRED
    an = rs.analyse([rec], "deepseek", levels=("L1",))
    assert {"B3_seen", "B3_size", "B3_seen_size"} <= set(an["levels"]["L1"]["comparators"])


# ---- the dry run writes counts only

def _walk(x, path=()):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _walk(v, path + (str(k),))
    elif isinstance(x, (list, tuple)):
        for i, v in enumerate(x):
            yield from _walk(v, path + (str(i),))
    else:
        yield path, x


FORBIDDEN_KEYS = {"p", "p_holm", "ci", "mean_diff", "verdict", "thesis", "rate", "sd", "mdd",
                  "half_width", "distances", "records", "analysis", "hits", "diff"}


def test_dry_output_holds_only_counts(tmp_path):
    ctx = fake_ctx(tmp_path)
    deep, pm = fake_inputs()
    inputs = {"deepseek": (deep, {}, None, {}), "placebo": (pm, {}, None, {})}
    out = rs.run_core(ctx, ["deepseek", "placebo"], inputs, (pm, {}), None, True, False)
    dry = rs.dry_summary(out, ["deepseek", "placebo"])
    for path, v in _walk(dry):
        assert not (set(path) & FORBIDDEN_KEYS), path
        if isinstance(v, bool) or isinstance(v, str) or v is None:
            continue
        assert isinstance(v, (int, float)), (path, v)
        if isinstance(v, float):                              # only a median of counts and the timing
            assert path[-1] == "median" or path[0] == "timing", (path, v)
    json.dumps(rs._jsonable(dry))
    # what it says: rows, members, comparators that produced a score, rows left out
    assert dry["frame_rows"] == 2 and dry["models"]["deepseek"]["members_total"] == 3
    assert dry["models"]["deepseek"]["comparators_produced_a_score"]["B3"]["L1"] is True
    assert dry["rows_left_out"] == {"L1": 0, "L2": 0, "L3": 0}
    assert dry["models"]["deepseek"]["error_sample"]["n_distances"] >= 0      # a count, never the distances
    assert dry["mdd_table_ran"]["L1"] >= 0


def test_the_real_run_writes_one_error_sample_file_per_model(tmp_path):
    ctx = fake_ctx(tmp_path)
    objs = [node(1, "object", (1, 8), canon="oven"), node(2, "object", (3, 3), canon="fridge")]
    deep = {"a": [member(0, objects=objs)], "b": []}
    pm = {r: [member(k) for k in range(4)] for r in "ab"}
    out = rs.run_core(ctx, ["deepseek", "placebo"], {"deepseek": (deep, {}, None, {}), "placebo": (pm, {}, None, {})},
                      (pm, {}), None, True, False)
    names = rs.write_real(out, tmp_path / "real", {"models": ["deepseek", "placebo"]})
    assert "error_sample_deepseek.json" in names and "error_sample_placebo.json" in names
    sample = json.loads((tmp_path / "real" / "error_sample_deepseek.json").read_text())
    assert sorted(sample) == [1.0, 4.0]                       # a plain list of metres
    assert json.loads((tmp_path / "real" / "error_sample_placebo.json").read_text()) == []
    assert out["models"]["deepseek"]["error_sample_left_out"] == 0
    summary = json.loads((tmp_path / "real" / "results.json").read_text())
    assert "error_sample" not in summary["models"]["deepseek"] and summary["models"]["deepseek"]["error_sample_n"] == 2


def test_the_dry_run_never_writes_the_error_sample(monkeypatch, tmp_path):
    md, hashfile, freeze, sha = guard_files(monkeypatch, tmp_path)
    ctx = fake_ctx(tmp_path)
    deep, pm = fake_inputs()
    result = rs.run_core(ctx, ["deepseek"], {"deepseek": (deep, {}, None, {})}, (pm, {}), None, True, False)
    monkeypatch.setattr(rs, "run", lambda *a, **k: result)
    out = tmp_path / "dryout"
    assert rs.main(["--models", "deepseek", "--out", str(out), "--prereg-sha256", sha, "--dry"]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["dry_run.json"]


def test_placebo_as_a_model_has_no_b1_and_no_b4(tmp_path):
    ctx = fake_ctx(tmp_path)
    _, pm = fake_inputs()
    out = rs.run_core(ctx, ["placebo"], {"placebo": (pm, {}, None, {})}, (pm, {}), None, False, False)
    r = out["models"]["placebo"]["records"][0]
    assert r["comparators"]["B1"] == {} and r["comparators"]["B4"] == {} and set(r["model"]) == {"0", "1", "2", "3"}
    assert out["placebo_records"] is out["models"]["placebo"]["records"]


def test_extras_summary_reads_the_keys_score_member_writes(tmp_path):
    # mismatch caught: the summary asked for l4_1m, l4_2m, l4_3m; score_member writes l4_1p0m, l4_2p0m, l4_3p0m
    t = world()
    rooms = [node(1, "room", (0, 0), room_type="kitchen")]
    mm = member(l1={"kitchen"}, rooms=rooms, objects=[node(2, "object", (1.3, 7), canon="oven")],
                items=[item("object", "oven", (1.3, 7)), item("room", "kitchen", (2, 8))])
    ex = sl.score_member(mm, t, STATE_A).extra
    for key in rs.EXTRA_LEVEL:
        assert key in ex, key
    ctx = fake_ctx(tmp_path)
    deep, pm = fake_inputs()
    rec = rs.build_record(ctx.rows[0], t, STATE_A, [mm], ctx.prior, [mm], {})
    out = rs.extras_summary([rec])
    assert set(out) == set(rs.EXTRA_LEVEL)
    assert out["l4_0p5m"]["model_clusters"] == {"00853_s42_official": 1.0}
    assert out["l4_3p0m"]["placebo_clusters"] == {"00853_s42_official": 1.0}


def test_dry_counts_regions_that_hold_a_footprint_cell(tmp_path):
    ctx = fake_ctx(tmp_path)
    deep, pm = fake_inputs()
    ctx.truths["00853"].regions_with_cells = lambda: {1, 2, 3}      # one of the five has an empty mask
    out = rs.run_core(ctx, ["deepseek"], {"deepseek": (deep, {}, None, {})}, (pm, {}), None, False, False)
    dry = rs.dry_summary(out, ["deepseek"])
    assert dry["truth"]["00853"]["regions"] == 5 and dry["truth"]["00853"]["regions_with_footprint_cells"] == 3


def test_mdd_table_file_holds_the_registered_fields(tmp_path):
    ctx = fake_ctx(tmp_path)
    deep, pm = fake_inputs()
    out = rs.run_core(ctx, ["deepseek"], {"deepseek": (deep, {}, None, {})}, (pm, {}), None, False, False)
    rs.write_real(out, tmp_path / "real", {})
    f = json.loads((tmp_path / "real" / "mdd_table.json").read_text())
    assert set(f) == {"levels", "alpha", "power", "m_tests"} and set(f["levels"]) == {"L1", "L2", "L3"}
    assert f["alpha"] == 0.05 and f["power"] == 0.8 and f["m_tests"] == 6
    for lv, delta, contrast in (("L1", 0.05, "B1-B3"), ("L2", 0.05, "B1-B3"), ("L3", 0.03, "B5-D")):
        e = f["levels"][lv]
        assert set(e) == {"contrast", "n_clusters", "sd", "mdd", "half_width", "delta"}
        assert e["delta"] == delta and e["contrast"] == contrast
    assert rs.mdd_table_file(out["mdd"]) == f
