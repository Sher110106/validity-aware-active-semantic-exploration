"""Tests for tools/live_policy/results_semantic_1113/supplement/supplement.py on a small synthetic case.

The supplement imports the frozen scorer only inside `load_scorer`; these tests call its pure functions
with stand-in objects, so they need no result file and no replay folder.
"""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

HERE = Path(__file__).resolve().parent
PATH = HERE.parent / "live_policy" / "results_semantic_1113" / "supplement" / "supplement.py"
spec = importlib.util.spec_from_file_location("_test_supplement", PATH)
sup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sup)

CLASSES = {"bed": "bed", "sofa": "sofa", "wall": "wall", "fridge": "fridge"}


def normalise(name):
    return CLASSES.get(name)


def is_structure(c):
    return c == "wall"


def obj(name, flag=None):
    return NS(name=name, is_predicted=flag, canon=normalise(name) if normalise(name) and not is_structure(normalise(name)) else None)


def room(rt):
    return NS(room_type=rt)


def member(objs=(), rooms=()):
    return NS(new_objects=list(objs), new_rooms=list(rooms),
              l1_claims=frozenset(r.room_type for r in rooms if r.room_type not in (None, "dining")),
              l2_claims=frozenset(o.canon for o in objs if o.canon))


def test_label_kind():
    assert sup.label_kind("bed", normalise, is_structure) == "class"
    assert sup.label_kind("wall", normalise, is_structure) == "structure"
    assert sup.label_kind("zzz", normalise, is_structure) == "other"


def test_label_counts_split_and_sum():
    m1 = member([obj("bed", True), obj("wall", True), obj("zzz", None)], [room("bedroom"), room(None), room("dining")])
    m2 = member([obj("sofa", False)], [])
    c = sup.label_counts([m1, m2], normalise, is_structure)
    assert c["members"] == 2
    assert c["new_objects"] == 4
    assert (c["objects_class"], c["objects_structure"], c["objects_other"]) == (2, 1, 1)
    assert c["objects_class"] + c["objects_structure"] + c["objects_other"] == c["new_objects"]
    assert (c["objects_flagged"], c["objects_unflagged"]) == (2, 2)
    assert (c["new_rooms"], c["rooms_untyped"], c["rooms_dining"]) == (3, 1, 1)


def test_label_counts_empty():
    c = sup.label_counts([], normalise, is_structure)
    assert all(v == 0 for v in c.values())


def test_looser_differences():
    state = NS(open_types={"bedroom"}, open_types_loose={"bedroom", "kitchen"},
               open_classes={"bed"}, open_classes_loose={"bed", "fridge"})
    d = sup.looser_differences(state)
    assert d == {"types": ["kitchen"], "classes": ["fridge"]}
    same = NS(open_types={"a"}, open_types_loose={"a"}, open_classes=set(), open_classes_loose=set())
    assert sup.looser_differences(same) == {"types": [], "classes": []}


def test_members_proposing():
    a = member([obj("fridge"), obj("fridge"), obj("bed")], [room("kitchen")])
    b = member([obj("bed")], [])
    c = sup.members_proposing([a, b], ["kitchen"], ["fridge"])
    assert c == {"members": 2, "members_with_type_claim": 1, "members_with_class_claim": 1,
                 "new_objects_of_those_classes": 2}
    z = sup.members_proposing([b], ["kitchen"], ["fridge"])
    assert z["members_with_type_claim"] == 0 and z["members_with_class_claim"] == 0


def test_matched_equals_plain():
    recs = [{"model": {"0": {"L1": 1.0, "extra": {"l1_matched": 1.0}},
                       "1": {"L1": None, "extra": {}},
                       "2": {"L1": 0.5, "extra": {"l1_matched": 0.0}}}}]
    assert sup.matched_equals_plain(recs) == {"members_with_l1_score": 2, "members_where_one_claim_score_differs": 1}


def test_balance_counts(tmp_path):
    root = tmp_path / "m4"
    for k, status, err in ((0, "ok", None), (1, "ok", None), (2, "error", "boom")):
        d = root / "mymodel" / "effort_medium" / "row1" / f"member_{k}"
        d.mkdir(parents=True)
        (d / "record.json").write_text(json.dumps({"status": status, "error": err}))
    ledger = tmp_path / "usage.jsonl"
    ledger.write_text("\n".join(json.dumps(x) for x in (
        {"model": "mymodel", "status": "ok"}, {"model": "mymodel", "status": "error"},
        {"model": "other", "status": "error"})) + "\n")
    out = sup.balance_counts(root, "mymodel", ledger, {"row1": {0: "ok", 1: "ok", 2: "dropped"}})
    assert out == {"members": 3, "members_dropped": 1, "ledger_lines": 2, "ledger_lines_not_ok": 1,
                   "member_records": 3, "member_records_with_error": 1, "member_records_status_not_ok": 1}


def test_saved_supplement_adds_up():
    p = PATH.with_name("supplement.json")
    if not p.exists():
        pytest.skip("supplement.json not written yet")
    d = json.loads(p.read_text())
    for m, c in d["labels"].items():
        assert c["objects_class"] + c["objects_structure"] + c["objects_other"] == c["new_objects"], m
        assert c["objects_flagged"] + c["objects_unflagged"] == c["new_objects"], m
        assert c["rooms_untyped"] + c["rooms_dining"] <= c["new_rooms"], m
