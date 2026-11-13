"""Tests for validity.py and room_test.py (PREREGISTRATION_SEMANTIC.md §11), and the real-file checks of the
wired scorer. Synthetic graphs with the real label table and the real validator. No score of a model on a
real file is computed or checked here."""
import csv
import importlib.util
import json
import math
import os
import sys
import types
from pathlib import Path

import pytest
import yaml

HERE = os.path.dirname(__file__)
SEM = os.path.abspath(os.path.join(HERE, "..", "live_policy", "semantic"))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))


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
ep = load("extract_preds")
vl = load("validity")
rt = load("room_test")
sl = load("score_levels")
st = load("stats")
rs = load("run_semantic")
bl = load("baselines")
lb = load("labels")


# ------------------------------------------------------------------------------ synthetic graphs

def room(i, name, x, y, z=1.3):
    return {"id": i, "name": name, "node_type": "room", "position": f"[{x}, {y}, {z}]"}


def obj(i, name, x, y, z=0.3, dim="[1.0, 1.0, 0.5]", flag=True):
    d = {"id": i, "name": name, "node_type": "object", "position": f"[{x}, {y}, {z}]", "is_predicted": flag}
    if dim:
        d["dimension"] = dim
    return d


OBS_NODES = [room(1, "living room", 0.0, 0.0), obj(2, "sofa", 0.0, 0.0, 0.4, "[2.0, 1.0, 0.8]", flag=False)]
OBS_EDGES = [[2, 1]]


def graph(nodes, edges=()):
    return {"nodes": list(OBS_NODES) + list(nodes), "edges": [list(e) for e in OBS_EDGES] + [list(e) for e in edges]}


def observed_row(row_id="r", scene="00853", seed=42, arm="official", stage=3):
    nodes, ids, _ = ep.parse_doc_nodes({"nodes": OBS_NODES, "edges": OBS_EDGES})
    og = M.ObservedGraph(rooms=tuple(n for n in nodes if n.kind == "room"), objects=tuple(n for n in nodes if n.kind == "object"),
                         node_ids=ids)
    return M.Row(row_id=row_id, scene=scene, seed=seed, arm=arm, stage=stage, cluster=f"{scene}_s{seed}_{arm}", round=1,
                 is_gemini_row=False, observed=og, path_xy=())


def obs_norm():
    _, normalize, *_ = vl._asp()
    return normalize({"nodes": OBS_NODES, "edges": OBS_EDGES}, observed=True)


BED_ROOM = room(10, "bedroom", 6.0, 0.0)
BED = obj(11, "bed", 6.0, 1.0)
NIGHT = obj(12, "nightstand", 6.0, -1.0, 0.3, "[0.4, 0.4, 0.5]")        # no parent room: object_parent
LAMP = obj(13, "lamp", 9.0, 9.0, 0.5, dim=None)                          # no dimension: finite_geometry

DOC0 = graph([BED_ROOM, BED, NIGHT, LAMP], [[11, 10]])
DOC1 = graph([BED_ROOM, BED], [[11, 10]])
DOC2 = graph([])


def table(docs=None, live=None):
    docs = docs if docs is not None else {0: DOC0, 1: DOC1, 2: DOC2}
    return vl.guess_table(observed_row(), obs_norm(), docs, live)


def by_label(guesses):
    return {g.node.name: g for g in guesses}


# --------------------------------------------------------------------------- guesses and views

def test_guess_table_validator_outcomes_and_reasons():
    g = by_label(table()[0])
    assert set(g) == {"bedroom", "bed", "nightstand", "lamp"}
    assert g["bedroom"].valid and g["bed"].valid
    assert not g["nightstand"].valid and g["nightstand"].reason == "object_parent"
    assert not g["lamp"].valid and g["lamp"].reason == "finite_geometry"
    assert table()[2] == []                                   # member 2 echoes the observed graph: no guess


def test_the_validator_is_called_as_track_keep_sets_calls_it(monkeypatch):
    seen = {}
    real = vl._asp()

    def spy(completion, observed, config):
        seen["config"] = config
        return real[4](completion, observed, config)

    monkeypatch.setattr(vl, "_asp", lambda: (real[0], real[1], real[2], real[3], spy))
    kept, reasons, rejected = vl.validate_member(obs_norm(), DOC1)
    assert seen["config"] == real[3](allow_parsed_mapping=True) and rejected == ""
    assert {"10", "11"} <= kept and {"1", "2"} <= kept


def test_a_rejected_completion_removes_every_guess_with_the_reason():
    bad = {"nodes": [OBS_NODES[0], BED_ROOM, BED], "edges": [[11, 10]]}      # omits observed node 2
    g = by_label(table({0: bad})[0])
    assert not g["bed"].valid and g["bed"].reason == "rejected:observed_preservation"
    assert not g["bedroom"].valid


def test_support_is_hits_over_four_intended_members():
    g = by_label(table()[0])
    assert g["bed"].support == 0.5 and g["bedroom"].support == 0.5     # members 0 and 1 hold them
    assert g["nightstand"].support == 0.25 and g["lamp"].support == 0.25
    only = by_label(table({0: DOC0})[0])                               # a member alone: 1 of 4, never 1 of 1
    assert only["bed"].support == 0.25


def test_support_uses_the_id_not_the_flag(tmp_path):
    # Gemini sets is_predicted false on its new objects: support_policy would then ignore them
    unflagged = graph([BED_ROOM, obj(11, "bed", 6.0, 1.0, flag=False)], [[11, 10]])
    g = by_label(table({0: unflagged, 1: unflagged})[0])
    assert g["bed"].support == 0.5


def test_views_keep_what_they_say():
    guesses = table()[0]
    names = lambda view: sorted(g.node.name for g in guesses if vl.keeps(g, view))      # noqa: E731
    assert names("raw") == ["bed", "bedroom", "lamp", "nightstand"]
    assert names("V") == ["bed", "bedroom"]
    assert names("V+vote0.5") == ["bed", "bedroom"]
    assert names("V+vote0.75") == [] and names("V+vote1.0") == []
    with pytest.raises(ValueError):
        vl.keeps(guesses[0], "V+wishful")


def test_two_of_eight_counts_members_across_both_tracks():
    track1 = graph([room(60, "bedroom", 7.0, 0.0), obj(61, "bed", 6.1, 1.0)], [[61, 60]])    # another track's ids
    live = {0: DOC0, 1: DOC1, 2: DOC2, 4: track1}
    g = by_label(table(live=live)[0])
    assert g["bed"].n8 == 3 and g["nightstand"].n8 == 1 and g["bedroom"].n8 == 3     # members 0, 1 and 4
    assert vl.keeps(g["bed"], "V+2of8") and not vl.keeps(g["nightstand"], "V+2of8")
    assert by_label(table()[0])["bed"].n8 is None
    # the rule needs the validator too: an invalid guess is out however many members hold it
    assert not vl.keeps(vl.Guess(0, g["lamp"].node, False, "x", 0.25, 5), "V+2of8")


def test_a_guess_that_reuses_an_observed_id_is_an_echoed_observed_node():
    echo = graph([obj(2, "sofa", 9.0, 9.0, 0.4, "[2.0, 1.0, 0.8]")])          # observed id, far from the observed sofa
    g = table({0: echo})[0]
    assert len(g) == 1 and g[0].valid and g[0].support is None
    assert all(vl.keeps(g[0], v) for v in ("raw", "V", "V+vote1.0"))


def test_item_of_and_view_member():
    guesses = table()[0]
    kept = vl.view_member(0, guesses, "V")
    assert kept.l1_claims == {"bedroom"} and kept.l2_claims == {"bed"}
    assert sorted((i.kind, i.label) for i in kept.l3_items) == [("object", "bed"), ("room", "bedroom")]
    removed = vl.view_member(0, guesses, removed=True)
    assert removed.l2_claims == {"nightstand", "lamp"} and removed.l1_claims == frozenset()
    dining = ep.parse_doc_nodes({"nodes": [room(5, "dining room", 1, 1)]})[0][0]
    assert vl.item_of(dining) is None                                  # item 51


# ------------------------------------------------------------------------------------ row record

def _tt():
    """The scoring tests' synthetic house, with the real label table."""
    import test_semantic_scoring as T
    return T.world(), T.STATE_A


def test_row_record_views_removed_and_support_items():
    truth, state = _tt()
    oven = ep.parse_doc_nodes({"nodes": [obj(30, "oven", 1.0, 7.0)]})[0][0]        # inside unobserved region 3
    couch = ep.parse_doc_nodes({"nodes": [obj(31, "nightstand", 2.0, 2.0)]})[0][0]  # in seen region 1
    t = [vl.Guess(0, oven, True, None, 0.5), vl.Guess(0, couch, False, "aabb_conflict", 0.25)]
    rec = vl.row_record({0: t}, truth, state)
    assert rec["n_guesses"] == 2 and rec["n_removed"] == 1 and rec["reasons"] == {"aabb_conflict": 1}
    assert rec["views"]["raw"]["0"]["L3"] == 0.5 and rec["views"]["V"]["0"]["L3"] == 1.0
    assert rec["views"]["V"]["0"]["n_kept"] == 1 and rec["views"]["raw"]["0"]["n_kept"] == 2
    assert rec["views"]["V+vote0.5"]["0"]["n_kept"] == 1 and rec["views"]["V+vote0.75"]["0"]["n_kept"] == 0
    assert rec["views"]["V+vote0.75"]["0"]["L3"] is None               # no item kept: no score
    assert "V+2of8" not in rec["views"]                                 # no live stage
    assert rec["removed"]["0"]["L3"] == 0.0 and rec["removed"]["0"]["L2"] == 1.0     # a nightstand is open (region 5)
    assert sorted(rec["support_items"]) == [[0.25, 0], [0.5, 1]]


# --------------------------------------------------------------------------------------- readouts

def _vrec(cluster, kept, removed, scene="00853", items=()):
    return {"cluster": cluster, "scene": scene,
            "validity": {"n_guesses": 10, "n_removed": 4, "reasons": {"aabb_conflict": 3, "object_parent": 1},
                         "views": {"V": {"0": {"L2": kept, "L3": kept, "l2_hits": 1, "l2_n": 2, "l3_hits": 1.0, "l3_n": 2, "n_kept": 6}}},
                         "removed": {"0": {"L2": removed, "L3": removed}}, "support_items": list(items)}}


def test_share_removed_by_reason():
    out = vl.share_removed([_vrec("A", .5, .5), _vrec("B", .5, .5)])
    assert out["n_guesses"] == 20 and out["n_removed"] == 8 and out["share_removed"] == 0.4
    assert out["by_reason"]["aabb_conflict"] == {"n": 6, "share_of_guesses": 0.3}


def test_kept_vs_removed_interval_and_the_plus_minus_five_band():
    same = [_vrec(c, 0.50 + 0.001 * i, 0.50) for i, c in enumerate("ABCDEF")]
    out = vl.kept_vs_removed(same, "L3")
    assert out["n_clusters"] == 6 and out["verdict"] == "no detectable difference"
    assert -0.05 <= out["ci"][0] <= out["ci"][1] <= 0.05
    far = [_vrec(c, 0.8, 0.4) for c in "ABCDEF"]
    out = vl.kept_vs_removed(far, "L2")
    assert out["mean_diff"] == pytest.approx(0.4) and out["verdict"] == "interval reaches beyond +-0.05"
    assert vl.kept_vs_removed([], "L3")["verdict"] == "no interval"
    # a wide interval is not "no detectable difference": two clusters cannot show it
    two = vl.kept_vs_removed([_vrec("A", .5, .5), _vrec("B", .5, .5)], "L3")
    assert two["ci"] == (-math.inf, math.inf) and two["verdict"] == "interval reaches beyond +-0.05"


def test_reliability_brier_ece_and_the_cross_scene_calibrator():
    a = [[0.25, 0], [0.25, 0], [0.5, 1], [1.0, 1]]
    b = [[0.25, 0], [0.5, 0], [1.0, 1], [1.0, 1]]
    out = vl.reliability({"00853": a, "00871": b})
    allp = [p for p, _ in a + b]
    ally = [y for _, y in a + b]
    assert out["brier"] == pytest.approx(sum((p - y) ** 2 for p, y in zip(allp, ally)) / 8)
    assert [r["lo"] for r in out["curve"]] == [0.25, 0.5, 1.0] and sum(r["n"] for r in out["curve"]) == 8
    ece = sum(r["n"] * abs(r["mean_y"] - r["mean_p"]) for r in out["curve"]) / 8
    assert out["ece"] == pytest.approx(ece)
    # fit on 00871 (0.25 -> 0, 0.5 -> 0, 1.0 -> 1), test on 00853: predictions 0, 0, 0, 1 against 0, 0, 1, 1
    held = out["cross_scene"]["00853"]
    assert held["n_train"] == 4 and held["n_test"] == 4 and held["brier"] == pytest.approx(0.25)
    assert held["brier_raw_support"] == pytest.approx(sum((p - y) ** 2 for p, y in a) / 4)
    assert vl.reliability({"00853": a})["cross_scene"]["00853"]["brier"] is None        # one scene: nothing to fit on


def test_kept_vs_guesses_and_summarise():
    recs = [_vrec(c, 0.5, 0.4, items=[[0.5, 1], [0.25, 0]]) for c in "AB"] + [_vrec("C", 0.6, 0.4, scene="00871", items=[[1.0, 1]])]
    kg = vl.kept_vs_guesses(recs)
    assert kg["V"]["guesses_kept"] == 18 and kg["V"]["l3_hits"] == 3.0 and kg["V"]["l3_items"] == 6
    assert set(kg["V"]["cluster_mean_L3"]) == {"A", "B", "C"}
    s = vl.summarise(recs)
    assert set(s) == {"share_removed", "kept_vs_removed", "reliability", "kept_vs_guesses"}
    assert s["reliability"]["n_items"] == 5
    dc = vl.dry_counts(recs)
    assert dc["guesses"] == 30 and dc["removed"] == 12 and dc["kept_by_view"] == {"V": 18}
    assert all(isinstance(v, (int, dict)) for v in dc.values())


# ------------------------------------------------------------------------------ the room test

def region(rid, types, cx, cy):
    return M.Region(region_id=rid, types=frozenset(types), centroid_xy=(cx, cy), ref_objects=(), markers=())


def state(seen):
    return types.SimpleNamespace(seen=frozenset(seen), partly_seen=frozenset(), unobserved=frozenset({1, 2, 3} - set(seen)))


def new_room(i, rtype, x, y):
    return M.Node(node_id=i, kind="room", name=f"{rtype} room", xy=(x, y), z=1.3, is_predicted=None, room_type=rtype)


TRUTH = types.SimpleNamespace(regions={1: region(1, {"bedroom"}, 0, 0), 2: region(2, {"kitchen"}, 10, 0), 3: region(3, {"bathroom"}, 20, 0)})
STATES = {0: state({1}), 1: state({1}), 2: state({1, 2}), 3: state({1, 2})}


def test_unseen_at_start_and_first_seen():
    assert rt.regions_unseen_at_start(STATES) == [2, 3]
    assert rt.first_seen(STATES, 2) == 2 and rt.first_seen(STATES, 3) == rt.INF
    assert rt.regions_unseen_at_start({}) == []


def test_predicted_before_found_rules():
    rooms = {
        0: {0: [new_room(1, "bedroom", 0.5, 0)], 1: [new_room(2, "bedroom", 0.4, 0)]},            # region 1 is seen: left out
        1: {0: [new_room(3, "kitchen", 10, 1), new_room(4, "bedroom", 20, 0.5)],                  # kitchen near 2; bedroom near 3
            1: [new_room(5, "kitchen", 9, 0), new_room(6, "bedroom", 19, 0)], 2: []},
        2: {0: [new_room(7, "bathroom", 20, 0)], 1: []},                                         # one member for region 3
        3: {0: [new_room(8, "kitchen", 10, 0)], 1: [new_room(9, "kitchen", 10, 0)]},             # after region 2 was seen
    }
    untyped = rt.predicted_before_found(TRUTH, STATES, rooms, 2, False)
    typed = rt.predicted_before_found(TRUTH, STATES, rooms, 2, True)
    assert untyped == {2: True, 3: True} and typed == {2: True, 3: False}      # a bedroom is not a bathroom
    assert rt.predicted_before_found(TRUTH, STATES, rooms, 3, False) == {2: False, 3: False}
    # a stage at which the region is seen does not count: only stage 3 (after region 2 is seen at stage 2) holds kitchens
    late = {3: rooms[3]}
    assert rt.predicted_before_found(TRUTH, STATES, late, 2, False)[2] is False
    # the stage list limits the stages looked at
    assert rt.predicted_before_found(TRUTH, STATES, rooms, 2, False, stages=[0])[2] is False


def test_members_are_counted_once_and_the_radius_is_two_and_a_half_metres():
    region3 = TRUTH.regions[3]
    near = {0: [new_room(1, None, 22.5, 0), new_room(2, None, 20, 2.4)], 1: [new_room(3, None, 22.6, 0)]}
    assert rt.n_members_predicting(near, region3, False) == 1          # two rooms of member 0 count once; 2.6 m is out
    assert rt.n_members_predicting(near, region3, True) == 0           # an untyped room never matches a type
    nan_region = region(9, {"kitchen"}, math.nan, math.nan)
    assert rt.n_members_predicting(near, nan_region, False) == 0


def test_replay_counts_one_of_four_and_two_of_four():
    rows = [M.Row(row_id=f"r{k}", scene="s", seed=1, arm="official", stage=k, cluster="c", round=1, is_gemini_row=False,
                  observed=None, path_xy=()) for k in (1, 3)]
    def mem(k, rooms):
        return M.Member(member=k, new_rooms=tuple(rooms), new_objects=(), l1_claims=frozenset(), l2_claims=frozenset(), l3_items=())
    members = {"r1": [mem(0, [new_room(1, "kitchen", 10, 0)]), mem(1, []), mem(2, []), mem(3, [])],
               "r3": [mem(0, [new_room(2, "bathroom", 20, 0)]), mem(1, [new_room(3, "bathroom", 20, 1)]), mem(2, []), mem(3, [])]}
    out = rt.replay_counts(rows, members, {"s": TRUTH}, {"runX": STATES}, {"r1": "runX", "r3": "runX"})
    ent = out["runs"]["runX"]
    assert ent["n_regions_unseen_at_stage0"] == 2 and ent["n_rows"] == 2
    assert ent["predicted_1of4_untyped"] == [2, 3] and ent["predicted_2of4_untyped"] == [3]
    assert ent["predicted_1of4_typed"] == [2, 3] and ent["predicted_2of4_typed"] == [3]
    assert out["totals"]["of"] == 2 and out["totals"]["predicted_1of4_untyped"] == 2
    # a row with no member is left out
    assert rt.replay_counts(rows, {"r1": [], "r3": []}, {"s": TRUTH}, {"runX": STATES}, {"r1": "runX", "r3": "runX"})["runs"] == {}


def write_stage(run_dir, k, observed0, observed1=None, members=None):
    d = run_dir / "stages" / str(k)
    d.mkdir(parents=True, exist_ok=True)
    (d / "habitat_scene_graph_original_graph0.yaml").write_text(yaml.safe_dump(observed0))
    if observed1 is not None:
        (d / "habitat_scene_graph_original_graph1.yaml").write_text(yaml.safe_dump(observed1))
    for m, g in (members or {}).items():
        (d / f"habitat_scene_graph_new_graph_{m}.yaml").write_text(yaml.safe_dump(g))


def test_live_new_rooms_use_the_members_own_track(tmp_path):
    run = tmp_path / "e1_00853_s42_official_60m"
    o0 = {"nodes": [room(1, "living room", 0, 0)], "edges": []}
    o1 = {"nodes": [room(1, "living room", 10, 0)], "edges": []}
    member = {"nodes": [room(1, "living room", 0, 0), room(9, "bedroom", 0.2, 0.0)], "edges": []}
    write_stage(run, 3, o0, o1, {0: member, 4: member})
    got = rt.live_new_rooms(run.name, 3, tmp_path)
    assert got[0] == []                                               # the room at (0, 0) is the observed one on track 0
    assert [n.name for n in got[4]] == ["living room", "bedroom"]     # on track 1 both are new
    assert rt.live_new_rooms(run.name, 9, tmp_path) == {}


def test_live_new_rooms_without_a_second_track_graph_use_the_first(tmp_path):
    run = tmp_path / "e1_00853_s42_official_60m"
    write_stage(run, 0, {"nodes": [room(1, "living room", 0, 0)], "edges": []}, None,
                {0: {"nodes": [room(1, "living room", 0, 0), room(9, "bedroom", 5, 0)], "edges": []}})
    ep.SKIPPED.clear()
    got = rt.live_new_rooms(run.name, 0, tmp_path)
    assert [n.name for n in got[0]] == ["bedroom"]


def test_live_runs_by_the_run_table(tmp_path):
    (tmp_path / "runs").mkdir()
    for name in ("e1_00853_s42_official_60m", "e1_00853_s44_official_60m", "e3_00871_s42_oracle_visible_60m", "e0_zzz"):
        (tmp_path / "runs" / name / "stages").mkdir(parents=True)
    table_path = tmp_path / "t.csv"
    with open(table_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "arm", "status"])
        w.writerow(["e1_00853_s42_official_60m", "official", "counted"])
        w.writerow(["e1_00853_s44_official_60m", "official", "excluded: stopped at 46.8 m"])
        w.writerow(["e3_00871_s42_oracle_visible_60m", "oracle_visible", "counted"])
        w.writerow(["e9_missing", "official", "counted"])
        w.writerow(["e4_frontier", "frontier", "counted"])
    assert rt.live_runs(tmp_path / "runs", table_path) == ["e1_00853_s42_official_60m", "e3_00871_s42_oracle_visible_60m"]
    assert "e1_00853_s44_official_60m" in rt.live_runs(tmp_path / "runs", table_path, which="all")
    # without a table: every folder of a live arm
    assert rt.live_runs(tmp_path / "runs", tmp_path / "none.csv") == [
        "e1_00853_s42_official_60m", "e1_00853_s44_official_60m", "e3_00871_s42_oracle_visible_60m"]


def test_live_run_result_and_arm_totals(tmp_path):
    run = tmp_path / "e1_00853_s42_official_60m"
    o = {"nodes": [room(1, "living room", 0, 0)], "edges": []}
    kitchen = lambda x: {"nodes": [room(1, "living room", 0, 0), room(9, "kitchen", x, 0.0)], "edges": []}   # noqa: E731
    write_stage(run, 0, o, None, {k: kitchen(10) for k in range(4)})
    write_stage(run, 1, o, o, {k: kitchen(10) for k in range(8)})
    write_stage(run, 2, o, o, {k: kitchen(10) for k in range(8)})
    res = rt.live_run_result(run.name, TRUTH, tmp_path, STATES)
    assert res["n_regions_unseen_at_stage0"] == 2 and res["n_stages_with_members"] == 3 and res["n_stages_with_8_members"] == 2
    assert res["predicted_all_stages_typed"] == [2] and res["predicted_stages_with_8_members_untyped"] == [2]
    arms = rt.by_arm([res, {**res, "arm": "placebo", "predicted_all_stages_typed": [], "predicted_all_stages_untyped": [],
                            "predicted_stages_with_8_members_typed": [], "predicted_stages_with_8_members_untyped": []}])
    assert arms["paper"] == {"predicted": 9, "of": 28}
    assert arms["arms"]["official"]["of"] == 2 and arms["arms"]["official"]["rate_all_stages_typed"] == 0.5
    assert arms["arms"]["placebo"]["rate_all_stages_typed"] == 0.0
    dc = rt.dry_counts(arms, {"deepseek": {"totals": {"runs": 1, "of": 2}, "runs": {"x": {"n_rows": 3}}}})
    assert not any("predicted" in k or "rate" in k for a in dc["live_arms"].values() for k in a)
    assert dc["replay"]["deepseek"] == {"runs": 1, "of": 2, "rows": 3}


# ------------------------------------------------------------ the labels switch, on the real table

def test_answers_to_primary_only_leaves_extended_out():
    assert lb.answers_to("bed") == {"bed", "duvet"}                    # bed -> duvet is extended_sensitivity_only
    assert lb.answers_to("bed", include_extended=False) == {"bed"}
    assert lb.answers_to("refrigerator", include_extended=False) == {"fridge"}    # synonym_primary stays
    assert lb.answers_to("refrigerator") == lb.answers_to("refrigerator", include_extended=False)
    assert lb.answers_to("wall", include_extended=False) == frozenset()


def test_prior_and_truth_follow_the_switch(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"houses": [{"number": "00001", "regions": {"0": {"bed": 1}}},
                                        {"number": "00002", "regions": {"0": {"bed": 2}}}]}))
    both, prim = bl.Prior(p), bl.Prior(p, include_extended=False)
    assert "duvet" in both.class_n and both.class_n["duvet"] == [1, 2]
    assert prim.class_n.get("duvet", [0, 0]) == [0, 0] and prim.class_n["bed"] == [1, 2]


# ------------------------------------------------------------------------------------ real files

RUNS = Path(ep.RUNS_ROOT)
real = pytest.mark.skipif(not RUNS.is_dir(), reason="the saved runs are not on this machine")


@real
def test_real_truth_primary_only_has_no_duvet_bed():
    rtm = load("region_truth")
    full = rtm.load_scene_truth("00853")
    prim = rtm.load_scene_truth("00853", include_extended=False)
    beds_full = [o for g in full.regions.values() for o in g.ref_objects if o.raw_name == "bed"]
    beds_prim = [o for g in prim.regions.values() for o in g.ref_objects if o.raw_name == "bed"]
    assert beds_full and all("duvet" in o.answers_to for o in beds_full)
    assert beds_prim == [] or all("duvet" not in o.answers_to for o in beds_prim)
    # the primary rule gives a reference object only where a class remains
    assert sum(len(g.ref_objects) for g in prim.regions.values()) <= sum(len(g.ref_objects) for g in full.regions.values())


@real
def test_real_placebo_glue_reproduces_the_saved_placebo_members():
    """B1 is placebo_graph on the row's observed graph with default_rng([seed, stage, member]). On the
    placebo runs, whose stage files were made by that call, the glue gives the same graphs."""
    seen = same = 0
    for run in ("e1_00853_s42_placebo_60m", "e1_00871_s44_placebo_60m"):
        seed = int(run.split("_s")[1].split("_")[0])
        for stage in range(1, 8):
            d = RUNS / run / "stages" / str(stage)
            jl = d / "live_policy.jsonl"
            if not jl.is_file() or len(jl.read_text().splitlines()) != 1:      # a retried step used another seed
                continue
            observed = yaml.safe_load((d / "habitat_scene_graph_original_graph0.yaml").read_text())
            row = M.Row(row_id="x", scene="00853", seed=seed, arm="placebo", stage=stage, cluster="c", round=0,
                        is_gemini_row=False, observed=None, path_xy=())
            graphs = bl.placebo_graphs(row, lambda r: observed)
            for k, g in enumerate(graphs):
                f = d / f"habitat_scene_graph_new_graph_{k}.yaml"
                if f.is_file():
                    seen += 1
                    same += yaml.safe_load(yaml.safe_dump(g)) == yaml.safe_load(f.read_text())
    assert seen >= 20 and same == seen


MINI_FRAME = """# Round 1: three rows
e1_00853_s42_official_st08 /w/e1_00853_s42_official_60m 8
e2_00871_s43_filter_st03 /w/e2_00871_s43_filter_only_60m 3
# Round 4: one Gemini row
fa1_00853_s43_official_st02 /w/e1_00853_s43_official_60m_FAILED_ATTEMPT1_false_exit_host_oom 2
"""


@real
def test_real_rows_load_and_every_code_path_runs_in_dry_mode(tmp_path):
    """Three real rows (official, filter_only raw, a Gemini input), DeepSeek, Gemini and the placebo, the
    validity layer and every comparator. Only counts are checked: no score is read."""
    frame = tmp_path / "frame.txt"
    frame.write_text(MINI_FRAME)
    out = rs.run(["deepseek", "gemini", "placebo"], frame, runs_root=RUNS, with_room_test=False)
    dry = rs.dry_summary(out, ["deepseek", "gemini", "placebo"])
    assert dry["frame_rows"] == 3 and dry["prior"]["houses"] == 179
    assert dry["models"]["deepseek"]["members_total"] >= 8 and dry["models"]["gemini"]["rows_with_members"] == 1
    assert dry["models"]["placebo"]["members_per_row"]["min"] == 4
    assert dry["models"]["deepseek"]["validity"]["guesses"] > 0
    assert dry["models"]["deepseek"]["comparators_produced_a_score"]["B1"]["L2"] is True
    for path, v in _flat(dry):
        if isinstance(v, float):
            assert path[-1] == "median" or path[0] == "timing", (path, v)


def _flat(x, path=()):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _flat(v, path + (str(k),))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _flat(v, path + (str(i),))
    else:
        yield path, x


@real
def test_real_stage_state_loader_reaches_any_run_and_stage():
    rtm = load("region_truth")
    truth = rtm.load_scene_truth("00853")
    run = "e3_00871_s42_oracle_visible_60m"
    r = ep.load_stage_row("e1_00853_s42_placebo_60m", 5, RUNS)
    assert r.row_id == "e1_00853_s42_placebo_60m#st05" and r.arm == "placebo" and r.scene == "00853" and r.round == 0
    s5 = rtm.stage_state(truth, r)
    r0 = ep.load_stage_row("e1_00853_s42_placebo_60m", 0, RUNS)
    s0 = rtm.stage_state(truth, r0)
    assert len(r.path_xy) > len(r0.path_xy) == 1                       # stage 0: the start pose alone
    assert s0.seen and s5.seen and (s0.seen | s0.partly_seen | s0.unobserved) == set(truth.regions)
    assert ep.run_info(run) == ("00871", 42, "oracle_visible")
    assert 0 in ep.stage_numbers("e1_00853_s42_placebo_60m", RUNS)


# ---- §8: a row where no hit is possible at a level is left out of the level's readouts

def test_validity_readouts_leave_out_rows_where_no_hit_is_possible():
    imposs = {**_vrec("B", 0.0, 1.0), "possible": {"L1": True, "L2": True, "L3": False}}
    ok = {**_vrec("A", 0.5, 0.5), "possible": {"L1": True, "L2": True, "L3": True}}
    out = vl.kept_vs_removed([ok, imposs], "L3")
    assert out["n_rows"] == 1 and out["n_rows_left_out"] == 1 and set(out["kept"]) == {"A"}
    assert vl.kept_vs_removed([ok, imposs], "L2")["n_rows"] == 2      # still possible at L2
    kg = vl.kept_vs_guesses([ok, imposs])
    assert kg["V"]["l3_items"] == 2 and kg["V"]["l2_claims"] == 4 and set(kg["V"]["cluster_mean_L3"]) == {"A"}
    assert kg["V"]["guesses_kept"] == 12                            # a count of guesses, not a level score
    ok["validity"]["support_items"] = [[0.5, 1]]
    imposs["validity"]["support_items"] = [[0.25, 0]]
    assert vl.summarise([ok, imposs])["reliability"]["n_items"] == 1   # the support curve is read against L3 truth
    # a record without "possible" (a hand-made one) keeps every row
    assert vl.kept_vs_removed([_vrec("A", .5, .5)], "L3")["n_rows"] == 1
