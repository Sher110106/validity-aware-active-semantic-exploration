"""Amendment 5 in equal_path_check.py: readout 2 (F1 at 50, 60, 80 and 100 m) and S for the control arms, read with A5.3,
and the proof that without a control run the filed outputs of 11-18 do not move."""
import json
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "live_policy"))
sys.path.insert(1, HERE)
import equal_path_check as ep  # noqa: E402
import paper_compare as pc  # noqa: E402
from test_paper_compare_controls import B853, HALF, HIT, OBS, PLC, REF_NODES, make_run, write_graph  # noqa: E402

REAL = ep.RESULTS / "paper_compare.json"
needs_real = pytest.mark.skipif(not REAL.exists(), reason="paper_compare.json not present")
OFF = "e8_00853_s4{}_official_105m"
# path, time, graph: F1 0.5 until 50 m, 1.0 from 50 m. S of a run that reaches 100 m: (1 + 1 + 1 + 1) / 4 x 100 = 100
PTS = [(0, 0.0, HALF), (30, 200.0, HALF), (50, 330.0, HIT), (60, 400.0, HIT), (80, 520.0, HIT), (100, 640.0, HIT), (115, 700.0, HIT)]
PTS_LATE = [(0, 0.0, HALF), (30, 200.0, HALF), (55, 330.0, HALF), (60, 400.0, HALF), (80, 520.0, HIT), (100, 640.0, HIT), (115, 700.0, HIT)]
PTS_90 = PTS[:5] + [(90, 580.0, HIT)]


def scene_refs(tmp):
    write_graph(tmp / "ref.yaml", REF_NODES)
    ref = pc.load_reference(tmp / "ref.yaml")
    return {r: {"00853": ref} for r in ep.REFS}


def build_json(tmp, specs):
    """specs: (arm, name, points, roslaunch text or None). Each run is scored by paper_compare's own score_run."""
    recs, camp, refs = [], tmp / "camp", scene_refs(tmp)
    for arm, name, pts, log in specs:
        run = make_run(camp, name, pts, log=log)
        recs.append(pc.score_run(pc.RunSpec(name, arm, "00853", run, 42), refs, {"00853": B853}, []))
    return {"meta": {"budgets": {"00853": B853, "00871": 1300.2523394823074}, "time_tol_s": pc.TIME_TOL}, "runs": recs,
            "cells": pc.aggregate(recs), "seconds_per_metre": pc.seconds_per_metre(recs)}


def six_and_official(tmp, void=None, short=None):
    specs = [("official_nov", OFF.format(s), PTS, "ok\n") for s in (2, 3, 4)]
    for arm, fmt in (("placebo_nov", PLC), ("observed_only_nov", OBS)):
        for s in (42, 43, 44):
            name = fmt.format(s)
            pts = PTS_90 if short == name else PTS_LATE if s == 44 else PTS
            specs.append((arm, name, pts, "CUDA out of memory\n" if void == name else "ok\n"))
    return build_json(tmp, specs)


def rec_of(j, name):
    return next(r for r in j["runs"] if r["run"] == name)


# --- one run's value at L ---------------------------------------------------------------------------------

def test_a_control_run_reads_the_last_stage_at_or_under_l_and_needs_its_last_full_stage_to_reach_l(tmp_path):
    j = build_json(tmp_path, [("placebo_nov", PLC.format(42), PTS_90, "ok\n")])
    r = rec_of(j, PLC.format(42))
    assert ep.run_value(r, 50, "apr") == 1.0 and ep.run_value(r, 80, "apr") == 1.0
    assert ep.run_value(r, 40, "apr") == 0.5                      # the stage at 30 m
    assert ep.run_value(r, 90, "apr") == 1.0 and ep.run_value(r, 100, "apr") is None      # it stops at 90 m
    assert ep.complete_end_path(r["stages"]) == 90


def test_the_last_stage_without_both_graphs_does_not_count_as_reaching_l(tmp_path):
    camp = tmp_path / "camp"
    run = make_run(camp, OBS.format(42), PTS[:5] + [(100, 640.0, HIT)], log="ok\n", last_g1=False)
    rec = pc.score_run(pc.RunSpec(run.name, "observed_only_nov", "00853", run, 42), scene_refs(tmp_path), {"00853": B853}, [])
    assert ep.run_value(rec, 100, "hm3d") is None and ep.run_value(rec, 80, "hm3d") == 1.0
    # official_nov takes the same rule (item 4): the last stage with both graphs must reach L, and the value comes from it
    assert ep.run_value(dict(rec, arm="official_nov"), 100, "hm3d") is None and ep.run_value(dict(rec, arm="official_nov"), 80, "hm3d") == 1.0
    # an October-style arm on the same record still reads one graph as enough (the rule as filed)
    assert ep.run_value(dict(rec, arm="official"), 100, "hm3d") == 1.0


def test_a_marked_control_run_has_no_value_at_100_m_and_keeps_the_shorter_lengths(tmp_path):
    j = build_json(tmp_path, [("placebo_nov", PLC.format(42), PTS, "nvblox_node has died\n")])
    r = rec_of(j, PLC.format(42))
    assert r["no_final_value"] is True and r["reached_end_path_m"] == 115
    assert ep.run_value(r, 100, "apr") is None and ep.run_value(r, 80, "apr") == 1.0 and ep.run_value(r, 60, "apr") == 1.0
    assert ep.run_s(r, "apr") is None


def test_other_arms_are_read_by_value_at_whatever_their_record_says():
    st = [{"stage": 0, "path_m": 0.0, "n_graphs": 1, "scores": {"apr": {"f1": 0.1}}},
          {"stage": 1, "path_m": 60.0, "n_graphs": 1, "scores": {"apr": {"f1": 0.6}}}]
    for arm in ("frontier_end", "official", "placebo"):
        assert ep.run_value({"arm": arm, "stages": st, "no_final_value": True}, 60, "apr") == ep.value_at(st, 60, "apr") == 0.6


def test_official_nov_and_the_controls_read_a_value_only_from_a_complete_stage():
    full = lambda i, p, f: {"stage": i, "path_m": p, "n_graphs": 2, "scores": {"apr": {"f1": f}}}
    part = lambda i, p, f: {"stage": i, "path_m": p, "n_graphs": 1, "scores": {"apr": {"f1": f}}}
    st = [full(0, 0.0, 0.1), full(1, 50.0, 0.4), part(2, 80.0, 0.9), full(3, 100.0, 0.6), part(4, 110.0, 0.99)]
    for arm in ("official_nov", "placebo_nov", "observed_only_nov"):
        r = {"arm": arm, "stages": st}
        assert ep.run_value(r, 80, "apr") == 0.4          # the stage at 80 m has one graph: the last complete one below it is read
        assert ep.run_value(r, 100, "apr") == 0.6
        assert ep.run_value(r, 105, "apr") is None          # the last complete stage ends at 100 m: no value at 105 m
        assert ep.run_value(r, 110, "apr") is None
        assert ep.run_value({"arm": arm, "stages": [part(0, 0.0, 0.1)]}, 0, "apr") is None
    assert ep.run_value({"arm": "frontier_end", "stages": st}, 80, "apr") == 0.9        # the rule as filed


# --- readout 2 -----------------------------------------------------------------------------------------------

def test_readout_2_has_the_four_arms_three_references_four_lengths_and_the_right_labels(tmp_path):
    j = six_and_official(tmp_path)
    j["runs"] += [pc.score_run(pc.RunSpec("e7_00853_s42_frontier_end", "frontier_end", "00853",
                                           make_run(tmp_path / "camp", "e7_00853_s42_frontier_end", PTS, log=None), 42),
                               scene_refs(tmp_path), {"00853": B853}, [])]
    r = ep.readout2(j)
    assert r["arms"] == ["official_nov", "placebo_nov", "observed_only_nov", "frontier_end"] and r["lengths_m"] == [50, 60, 80, 100]
    assert sorted(r["tables"]) == ["apr", "frontier_made", "hm3d"]
    assert r["registered"] == {"official_nov": False, "placebo_nov": True, "observed_only_nov": True, "frontier_end": False}
    assert r["labels"]["placebo_nov"] == r["labels"]["observed_only_nov"] == "registered (A5.5)"
    assert r["labels"]["official_nov"] == r["labels"]["frontier_end"] == "first made after the results were seen (deviation 66)"
    for ref in ep.REFS:
        for arm in r["arms"]:
            assert sorted(r["tables"][ref][arm], key=int) == ["50", "60", "80", "100"]
    c = r["tables"]["apr"]["placebo_nov"]
    assert c["50"]["n"] == 3 and c["50"]["n_runs"] == 3 and c["100"]["n"] == 3
    assert c["50"]["mean"] == pytest.approx((100 + 100 + 50) / 3)      # seed 44 reads 0.5 at 50 m (its stage at 55 m)


def test_readout_2_leaves_out_an_arm_with_no_run_and_counts_a_run_with_no_value_in_n_runs_only(tmp_path):
    j = six_and_official(tmp_path, short=PLC.format(43))
    r = ep.readout2(j)
    assert "frontier_end" not in r["arms"]
    c = r["tables"]["apr"]["placebo_nov"]["100"]
    assert c["n"] == 2 and c["n_runs"] == 3
    assert r["tables"]["apr"]["placebo_nov"]["80"]["n"] == 3


# --- S ----------------------------------------------------------------------------------------------------------

def test_s_is_the_mean_of_f1_at_the_four_lengths_and_none_without_100_m(tmp_path):
    j = six_and_official(tmp_path, void=PLC.format(42), short=OBS.format(43))
    s = ep.s_values(j)
    assert sorted(s) == ["apr", "hm3d"] and sorted(s["apr"]) == ["observed_only_nov", "official_nov", "placebo_nov"]
    assert s["apr"]["placebo_nov"][PLC.format(43)] == pytest.approx(100.0)
    assert s["apr"]["placebo_nov"][PLC.format(44)] == pytest.approx((50 + 50 + 100 + 100) / 4)     # 0.5 at 50 and 60 m
    assert s["apr"]["placebo_nov"][PLC.format(42)] is None                  # marked: no value at 100 m
    assert s["hm3d"]["observed_only_nov"][OBS.format(43)] is None            # stopped at 90 m
    assert s["hm3d"]["observed_only_nov"][OBS.format(42)] == pytest.approx(100.0)
    assert all(v == pytest.approx(100.0) for v in s["apr"]["official_nov"].values())


def test_the_decision_runs_on_s_taken_from_a_scored_json(tmp_path):
    d = pc.decide_controls(ep.s_values(six_and_official(tmp_path)))
    assert d["arms"]["placebo_nov"]["judged"] and d["arms"]["observed_only_nov"]["judged"]
    # official S = 100, 100, 100; placebo S = 100, 100, 75: the tie at 100 stops "separated", the mean is higher
    assert d["arms"]["placebo_nov"]["per_reference"]["apr"] == pc.ABOVE_AVG
    assert d["arms"]["observed_only_nov"]["statement"] == "in between"
    d = pc.decide_controls(ep.s_values(six_and_official(tmp_path / "b", short=PLC.format(43))))
    assert d["arms"]["placebo_nov"]["statement"] == "no statement"


# --- the registered cells still equal the budget table -----------------------------------------------------------

def test_the_budget_script_agrees_with_the_registered_cells_when_control_runs_are_in_the_json(tmp_path):
    j = six_and_official(tmp_path, void=PLC.format(42))
    doc, md = ep.budget_doc(j)                       # raises if its cells at the registered B differ from paper_compare's
    t = doc["scenes"]["00853"]["tables"]["apr"]
    assert t["placebo_nov"][doc["scenes"]["00853"]["registered_B_label"]]["100"]["n"] == 2       # the marked run is out at 100% of B
    assert t["placebo_nov"][doc["scenes"]["00853"]["registered_B_label"]]["50"]["n"] == 3
    assert "placebo_nov" in md and "observed_only_nov" in md


def test_the_equal_path_document_names_the_control_rows_only_when_there_are_some(tmp_path):
    doc, md = ep.equal_path_doc(six_and_official(tmp_path))
    assert "control arms of Amendment 5" in md and "placebo_nov" in doc["scenes"]["00853"]["arms"]
    assert doc["registered"] is False
    plain, md2 = ep.equal_path_doc(build_json(tmp_path / "p", [("official_nov", OFF.format(2), PTS, "ok\n")]))
    assert "Amendment 5" not in md2


# --- nothing moves without a control run ----------------------------------------------------------------------------

@needs_real
def test_the_filed_equal_path_and_budget_outputs_are_reproduced_exactly():
    real = json.loads(REAL.read_text())
    doc, md = ep.equal_path_doc(real)
    assert json.loads(json.dumps(doc)) == json.loads((ep.RESULTS / "equal_path" / "equal_path.json").read_text())
    assert md == (ep.RESULTS / "equal_path" / "equal_path.md").read_text()
    bdoc, bmd = ep.budget_doc(real)
    assert json.loads(json.dumps(bdoc)) == json.loads((ep.RESULTS / "budget_sensitivity" / "budget_sensitivity.json").read_text())
    assert bmd == (ep.RESULTS / "budget_sensitivity" / "budget_sensitivity.md").read_text()


@needs_real
def test_readout_2_for_the_two_old_arms_equals_their_filed_equal_path_cells():
    real = json.loads(REAL.read_text())
    filed = json.loads((ep.RESULTS / "equal_path" / "equal_path.json").read_text())["scenes"]["00853"]["tables"]
    r = ep.readout2(real)
    assert r["arms"] == ["official_nov", "frontier_end"]
    for ref in ep.REFS:
        for arm in r["arms"]:
            for length in ("50", "60", "80", "100"):
                assert r["tables"][ref][arm][length] == filed[ref][arm][length]


@needs_real
def test_official_novs_s_agrees_with_the_filed_cell_means():
    real = json.loads(REAL.read_text())
    filed = json.loads((ep.RESULTS / "equal_path" / "equal_path.json").read_text())["scenes"]["00853"]["tables"]
    s = ep.s_values(real)
    for ref in ("apr", "hm3d"):
        vals = list(s[ref]["official_nov"].values())
        assert len(vals) == 3 and all(v is not None for v in vals)
        assert sum(vals) / 3 == pytest.approx(sum(filed[ref]["official_nov"][L]["mean"] for L in ("50", "60", "80", "100")) / 4)


# --- the six pinned S values (items 4 and 5) ------------------------------------------------------------------

PINNED = {"apr": [53.55291686668735, 52.48222944405994, 61.725399191409466],
          "hm3d": [29.045779047403908, 28.467900509194806, 30.39810010214091]}


def test_the_pinned_constants_are_these_six_numbers_at_full_precision():
    for ref, vals in PINNED.items():
        assert [pc.OFFICIAL_NOV_S_PINNED[ref][r] for r in pc.OFFICIAL_NOV_RUNS] == vals


@needs_real
def test_the_three_official_nov_s_values_have_not_moved():
    real = json.loads(REAL.read_text())
    s = ep.s_values(real)
    for ref, vals in PINNED.items():
        got = [s[ref]["official_nov"][r] for r in pc.OFFICIAL_NOV_RUNS]
        assert got == pytest.approx(vals, abs=1e-9, rel=0)
        assert [round(v, 2) for v in got] == [round(v, 2) for v in vals]
    assert [round(s["apr"]["official_nov"][r], 2) for r in pc.OFFICIAL_NOV_RUNS] == [53.55, 52.48, 61.73]
    assert [round(s["hm3d"]["official_nov"][r], 2) for r in pc.OFFICIAL_NOV_RUNS] == [29.05, 28.47, 30.40]
    # and the filed JSON's own stage records are all complete for these runs, so the one rule changes none of them
    for r in real["runs"]:
        if r["arm"] == "official_nov":
            assert all(st["n_graphs"] == 2 for st in r["stages"])


# --- the output root (item 9) --------------------------------------------------------------------------------------

def test_main_writes_under_the_output_root_and_leaves_the_filed_folder_alone(tmp_path, capsys):
    import hashlib

    def digest():
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ep.RESULTS.glob("equal_path/*")) + sorted(ep.RESULTS.glob("budget_sensitivity/*"))}
    before = digest()
    root = tmp_path / "trial" / "deeper"                         # does not exist yet
    root.mkdir(parents=True)
    (root / "paper_compare.json").write_text(json.dumps(six_and_official(tmp_path / "w")))
    assert ep.main(["--out-root", str(root)]) == 0
    for folder in ("equal_path", "budget_sensitivity"):
        assert (root / folder / f"{folder}.json").exists() and (root / folder / f"{folder}.md").exists()
    assert "placebo_nov" in (root / "equal_path" / "equal_path.md").read_text()
    assert digest() == before


def test_main_creates_a_missing_output_root_and_reads_the_filed_json_when_the_root_has_none(tmp_path):
    if not REAL.exists():
        pytest.skip("paper_compare.json not present")
    root = tmp_path / "not" / "yet"
    assert ep.main(["--out-root", str(root)]) == 0
    assert json.loads((root / "equal_path" / "equal_path.json").read_text()) == json.loads((ep.RESULTS / "equal_path" / "equal_path.json").read_text())


def test_main_with_no_argument_writes_into_the_filed_folder(tmp_path, monkeypatch):
    filed = tmp_path / "filed"
    filed.mkdir()
    (filed / "paper_compare.json").write_text(json.dumps(six_and_official(tmp_path / "w")))
    monkeypatch.setattr(ep, "RESULTS", filed)                     # stands in for the filed folder
    assert ep.main([]) == 0
    assert (filed / "equal_path" / "equal_path.json").exists() and (filed / "budget_sensitivity" / "budget_sensitivity.json").exists()
