"""Tests for the exploratory equal-path and budget-sensitivity readouts (tools/live_policy/equal_path_check.py)."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "live_policy"))
import equal_path_check as ep  # noqa: E402
import paper_compare as pc  # noqa: E402

REAL = ep.RESULTS / "paper_compare.json"
# sha256 of json.dumps(tables, sort_keys=True) of the "tables" of the equal_path.json written on 2026-11-18
# (scene 00853, arms official, official_nov, filter_only, placebo, frontier_60m, frontier_end; apr, hm3d, frontier_made).
OLD_00853_TABLES_SHA256 = "d1c907232aa94cf28b8f18d1880a60ab5a5f8ded25065df44c54c70448394b81"
needs_real = pytest.mark.skipif(not REAL.exists(), reason="paper_compare.json not present")


def stages(*pairs):
    return [{"stage": i, "path_m": p, "time_s": 6.0 * p, "scores": {"apr": {"f1": f}}} for i, (p, f) in enumerate(pairs)]


def make_run(scene, arm, pts, name=None):
    """pts: (time_s, path_m, f1) per stage; the same f1 under all three references."""
    st = [{"stage": i, "time_s": t, "path_m": p, "n_graphs": 2, "sources": ["run"],
           "scores": {r: {"f1": f, "precision": f, "recall": f} for r in ep.REFS}} for i, (t, p, f) in enumerate(pts)]
    return {"run": name or f"{arm}_{scene}_{len(pts)}_{pts[-1][0]}", "arm": arm, "scene": scene, "stages": st,
            "final_time_s": pts[-1][0], "final_path_m": pts[-1][1], "sec_per_m": pts[-1][0] / pts[-1][1] if pts[-1][1] else None}


def make_json(runs, budgets):
    """A paper_compare.json built by paper_compare's own aggregate, so its registered cells do not come from the code under test."""
    records = []
    for r in runs:
        full = [{**s, "graphs": {0: None, 1: None}, "scores": {k: {**v, "ged": None} for k, v in s["scores"].items()}} for s in r["stages"]]
        end_s = pc.complete_end_s(full) if r["arm"] == pc.NOV_ARM else None
        records.append({**r, "readouts": pc.build_readouts(full, dict.fromkeys(ep.REFS), budgets[r["scene"]], pc.TIME_TOL, end_s)})
    return {"meta": {"budgets": budgets, "time_tol_s": pc.TIME_TOL}, "runs": records, "cells": pc.aggregate(records),
            "seconds_per_metre": pc.seconds_per_metre(records)}


BUDGETS = {"00853": 632.1750566959381, "00871": 1300.2523394823074}
NOV = "e8_00853_s4{}_official_105m"


def synthetic():
    runs = [
        # ends 0.0000567 s short of B: the tolerance would admit it, the registered rule for this arm does not
        make_run("00853", "official_nov", [(0, 0, .1), (300, 50, .4), (632.1750, 105, .7)], NOV.format(2)),
        make_run("00853", "official_nov", [(0, 0, .1), (320, 55, .5), (640, 108, .8)], NOV.format(3)),
        make_run("00853", "frontier_end", [(0, 0, .1), (300, 40, .3), (700, 90, .6)]),
        make_run("00853", "frontier_60m", [(0, 0, .1), (400, 60, .5)]),        # ends before every 100% and L > 60 m
        make_run("00871", "frontier_end", [(0, 0, .2), (650, 90, .4), (1300.0, 150, .6), (1300.2515, 160, .65), (1500, 190, .7)]),
        make_run("00871", "frontier_end", [(0, 0, .2), (700, 100, .5), (1300.1, 120, .55)]),
        make_run("00871", "crashed_frontier_1st", [(0, 0, .1), (200, 20, .2)]),
    ]
    return make_json(runs, BUDGETS)


# --------------------------------------------------------------------------
# Equal path
# --------------------------------------------------------------------------

def test_value_is_read_at_the_last_stage_at_or_under_the_length():
    st = stages((0.0, 0.05), (20.0, 0.20), (48.0, 0.40), (61.0, 0.55))
    assert ep.value_at(st, 50, "apr") == 0.40
    assert ep.value_at(st, 48, "apr") == 0.40
    assert ep.value_at(st, 61, "apr") == 0.55
    assert ep.value_at(st, 10, "apr") == 0.05


def test_a_run_that_ends_short_has_no_value_and_a_missing_reference_gives_none():
    st = stages((0.0, 0.05), (20.0, 0.20), (48.0, 0.40))
    assert ep.value_at(st, 50, "apr") is None
    assert ep.value_at(st, 40, "hm3d") is None
    assert ep.value_at([], 10, "apr") is None


def test_table_gives_mean_range_and_n_over_the_runs_that_reach_the_length():
    pcj = {"runs": [{"scene": "00853", "arm": "official_nov", "stages": stages((0.0, 0.0), (50.0, 0.40), (100.0, 0.60))},
                    {"scene": "00853", "arm": "official_nov", "stages": stages((0.0, 0.0), (55.0, 0.50))},
                    {"scene": "00871", "arm": "official_nov", "stages": stages((0.0, 0.0), (55.0, 0.90))},
                    {"scene": "00853", "arm": "frontier_end", "stages": stages((0.0, 0.0), (60.0, 0.45))}]}
    t = ep.table(pcj, "00853", "apr", arms=("official_nov", "frontier_end"), lengths=(55, 100))
    assert t["official_nov"]["55"] == {"mean": pytest.approx(45.0), "min": pytest.approx(40.0), "max": pytest.approx(50.0), "n": 2, "n_runs": 2}
    assert t["official_nov"]["100"]["n"] == 1 and t["official_nov"]["100"]["mean"] == pytest.approx(60.0)
    assert t["frontier_end"]["55"]["mean"] == pytest.approx(0.0) and t["frontier_end"]["100"] == {"mean": None, "min": None, "max": None, "n": 0, "n_runs": 1}
    md = ep.equal_path_md({"apr": t}, "00853", (55, 100), {})
    assert "| official_nov | 45.0 [40.0-50.0] n=2 | 60.0 [60.0-60.0] n=1 of 2 |" in md
    assert "| frontier_end | 0.0 [0.0-0.0] n=1 | - |" in md        # no run has a value at 100 m


def test_equal_path_covers_both_scenes_every_arm_all_references_and_the_longer_lengths():
    doc, md = ep.equal_path_doc(synthetic())
    assert doc["registered"] is False and list(doc["scenes"]) == ["00853", "00871"]
    assert doc["scenes"]["00853"]["lengths"] == [20, 30, 40, 50, 55, 60, 70, 80, 90, 100]
    assert doc["scenes"]["00871"]["lengths"] == [20, 30, 40, 50, 55, 60, 70, 80, 90, 100, 120, 150, 190]
    assert doc["scenes"]["00853"]["arms"] == ["official_nov", "frontier_60m", "frontier_end"]
    assert doc["scenes"]["00871"]["arms"] == ["frontier_end", "crashed_frontier_1st"]           # an arm outside ARMS is kept
    for scene in doc["scenes"].values():
        assert list(scene["tables"]) == ["apr", "hm3d", "frontier_made"]
    t = doc["scenes"]["00871"]["tables"]["hm3d"]["frontier_end"]
    assert t["150"] =={"mean": pytest.approx(60.0), "min": pytest.approx(60.0), "max": pytest.approx(60.0), "n": 1, "n_runs": 2}
    assert t["190"]["n"] == 1 and t["190"]["mean"] == pytest.approx(70.0)   # only the first run reaches 190 m
    assert t["20"]["mean"] == pytest.approx(20.0) and t["20"]["n"] == 2
    assert "| frontier_end | 20.0 [20.0-20.0] n=2 |" in md and "## Scene 00871" in md


def test_a_run_with_no_value_at_l_is_counted_in_n_runs_not_in_n():
    doc, md = ep.equal_path_doc(synthetic())
    c = doc["scenes"]["00853"]["tables"]["apr"]["frontier_60m"]["70"]          # the run ends at 60 m
    assert c == {"mean": None, "min": None, "max": None, "n": 0, "n_runs": 1}
    assert doc["scenes"]["00853"]["tables"]["apr"]["frontier_60m"]["60"]["n"] == 1
    assert doc["scenes"]["00853"]["tables"]["apr"]["official_nov"]["100"]["n"] == 2   # both reach 100 m (105 m and 108 m)


def test_seconds_per_metre_line_per_arm_under_each_scene():
    doc, md = ep.equal_path_doc(synthetic())
    s = doc["scenes"]["00853"]["sec_per_m"]["official_nov"]
    assert s["n"] == 2 and s["n_runs"] == 2 and s["mean"] == pytest.approx((632.175 / 105 + 640 / 108) / 2)
    sec = md.split("## Scene 00853")[1].split("## Scene 00871")[0]
    assert "### Seconds of navigation time per metre" in sec
    assert f"- official_nov: {s['mean']:.2f} s/m [{s['min']:.2f}-{s['max']:.2f}], n=2" in sec
    assert "- frontier_60m: 6.67 s/m" in sec


def test_banner_comes_first_in_both_documents():
    pcj = synthetic()
    for md in (ep.equal_path_doc(pcj)[1], ep.budget_doc(pcj)[1]):
        assert md.split("\n")[2] == ep.BANNER
    for needle in ("Not a registered readout", "2026-11-19", "after the results were seen", "on no registered table", "DEVIATIONS_NOVEMBER.md"):
        assert needle in ep.BANNER


@needs_real
def test_the_old_00853_equal_path_cells_did_not_move():
    pcj = json.loads(REAL.read_text())
    old = {ref: ep.table(pcj, "00853", ref, ep.ARMS, ep.LENGTHS) for ref in ep.REFS}
    assert hashlib.sha256(json.dumps(old, sort_keys=True).encode()).hexdigest() == OLD_00853_TABLES_SHA256
    doc, _ = ep.equal_path_doc(pcj)           # the new document holds the same cells for those arms
    for ref in ep.REFS:
        for arm in ep.ARMS:
            assert doc["scenes"]["00853"]["tables"][ref][arm] == old[ref][arm]


# --------------------------------------------------------------------------
# Budget sensitivity
# --------------------------------------------------------------------------

def test_budget_cells_at_the_registered_b_equal_the_registered_cells():
    pcj = synthetic()
    doc, md = ep.budget_doc(pcj)                                   # raises if they differ
    for scene, label in (("00853", "632.1751"), ("00871", "1300.25")):
        assert doc["scenes"][scene]["registered_B_label"] == label
        assert ep.registered_mismatches(pcj, scene, doc["scenes"][scene]["tables"], label) == []
    reg = {(c["scene"], c["arm"], c["reference"], c["fraction"]): c for c in pcj["cells"] if c["variant"] == "B"}
    c = reg[("00853", "official_nov", "apr", "100")]
    assert c["stage_value_x100"]["n"] == 1 and c["n_runs"] == 2    # the run ending 5.7e-5 s short has no 100% value
    mine = doc["scenes"]["00853"]["tables"]["apr"]["official_nov"]["632.1751"]["100"]
    assert mine == {**c["stage_value_x100"], "n_runs": 2}
    assert "(registered)" in md


def test_the_registered_b_is_read_at_the_exact_second_not_at_the_rounded_label():
    pcj = synthetic()
    assert ep.read_budgets(pcj, "00871")["1300.25"] == BUDGETS["00871"]
    exact = ep.budget_table(pcj, "00871", "apr", ["frontier_end"], {"x": BUDGETS["00871"]})["frontier_end"]["x"]["100"]
    rounded = ep.budget_table(pcj, "00871", "apr", ["frontier_end"], {"x": 1300.25})["frontier_end"]["x"]["100"]
    # a stage at 1300.2515 s is inside the registered window (1300.2523 + tol) and outside 1300.25 + tol
    assert exact["n"] == 1 and exact["mean"] == pytest.approx(65.0)
    assert rounded["n"] == 1 and rounded["mean"] == pytest.approx(60.0)


def test_budget_script_stops_when_a_cell_at_the_registered_b_differs():
    pcj = synthetic()
    bad = copy.deepcopy(pcj)
    bad["runs"][2]["stages"][1]["scores"]["apr"]["f1"] = 0.99        # the registered cells keep the old value
    with pytest.raises(ValueError, match="differ from paper_compare.json"):
        ep.budget_doc(bad)
    missing = copy.deepcopy(pcj)
    missing["cells"] = [c for c in missing["cells"] if not (c["arm"] == "frontier_end" and c["scene"] == "00853")]
    assert ep.registered_mismatches(missing, "00853", ep.budget_doc(pcj)[0]["scenes"]["00853"]["tables"], "632.1751")


def test_a_run_that_ended_before_t_has_no_value_and_n_runs_keeps_it():
    pcj = synthetic()
    t = ep.budget_table(pcj, "00853", "apr", ["frontier_60m", "frontier_end", "official_nov"], {"600": 600.0, "500": 500.0, "700": 700.0})
    ten = {"mean": pytest.approx(10.0), "min": pytest.approx(10.0), "max": pytest.approx(10.0), "n": 1, "n_runs": 1}
    assert t["frontier_60m"]["600"]["10"] == ten
    assert t["frontier_60m"]["600"]["50"] == ten                                # t = 300 s: the stage at 0 s is the last at or before it
    assert t["frontier_60m"]["600"]["100"] == {"mean": None, "min": None, "max": None, "n": 0, "n_runs": 1}   # ends at 400 s < 600 s
    assert t["frontier_60m"]["500"]["100"]["n"] == 0
    assert t["frontier_end"]["600"]["100"]["mean"] == pytest.approx(30.0)      # t = 600 s: last stage at or before is 300 s -> .3
    assert t["official_nov"]["600"]["100"] == {"mean": pytest.approx(45.0), "min": pytest.approx(40.0), "max": pytest.approx(50.0), "n": 2, "n_runs": 2}
    assert t["official_nov"]["700"]["100"] == {"mean": None, "min": None, "max": None, "n": 0, "n_runs": 2}   # both November runs end before 700 s
    assert "n=1 of 2" in ep.budget_doc(pcj)[1]


def test_both_scenes_all_arms_all_references_and_paper_values_beside_asp_and_frontier():
    doc, md = ep.budget_doc(synthetic())
    assert doc["scenes"]["00853"]["budgets_s"].keys() == {"500", "550", "600", "632.1751", "650", "700", "750"}
    assert doc["scenes"]["00871"]["budgets_s"].keys() == {"600", "650", "700", "750", "800", "900", "1000", "1100", "1200", "1300.25"}
    assert doc["scenes"]["00871"]["arms"] == ["frontier_end", "crashed_frontier_1st"]
    for scene in doc["scenes"].values():
        assert list(scene["tables"]) == ["apr", "hm3d", "frontier_made"]
    assert doc["scenes"]["00871"]["paper_fig4_f1_x100"]["Frontier"] == [29.2, 55.7, 65.3]
    row = next(l for l in md.split("## Scene 00871")[1].splitlines() if l.startswith("| frontier_end | Frontier | 750 |"))
    assert "29.2" in row and "55.7" in row and "65.3" in row
    nov = next(l for l in md.split("## Scene 00853")[1].splitlines() if l.startswith("| official_nov | Ours(ASP) | 600 |"))
    assert "34.4" in nov and "60.8" in nov and "66.7" in nov
    crashed = next(l for l in md.splitlines() if l.startswith("| crashed_frontier_1st | - | 700 |"))
    cols = crashed.strip("| ").split(" | ")
    assert [cols[4], cols[6], cols[8]] == ["-", "-", "-"]                       # no paper method: no paper values


def test_budget_key_formatting():
    assert [ep.key_of(x) for x in (600, 632.1751, 1300.25, 700.0)] == ["600", "632.1751", "1300.25", "700"]


@needs_real
def test_real_json_cells_at_the_registered_b_equal_the_registered_cells():
    pcj = json.loads(REAL.read_text())
    doc, _ = ep.budget_doc(pcj)                                    # raises on any difference
    for scene, label in (("00853", "632.1751"), ("00871", "1300.25")):
        tables = doc["scenes"][scene]["tables"]
        assert ep.registered_mismatches(pcj, scene, tables, label) == []
        n = sum(len(by_b[label]) for t in tables.values() for by_b in t.values())
        assert n == len([c for c in pcj["cells"] if c["scene"] == scene and c["variant"] == "B"])
