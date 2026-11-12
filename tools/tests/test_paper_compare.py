"""Tests for tools/live_policy/paper_compare.py: the author's F1 rule, readouts, cells, CLI."""
import csv
import json
import os
import random
import subprocess
import sys

import numpy as np
import pytest
import yaml

HERE = os.path.dirname(__file__)
SCRIPT = os.path.join(HERE, "..", "live_policy", "paper_compare.py")
sys.path.insert(0, os.path.join(HERE, "..", "live_policy"))
sys.path.insert(0, os.path.join(HERE, "..", "evaluator"))
import paper_compare as pc  # noqa: E402

HTML = pc.DEFAULT_PAPER_HTML


def obj(name, x, y=0.0, z=0.0, node_type="object"):
    return {"name": name, "position": f"[{x}, {y}, {z}]", "node_type": node_type}


def write_graph(path, nodes):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"id": i, **n} for i, n in enumerate(nodes)]
    path.write_text(yaml.safe_dump({"nodes": rows, "edges": []}))
    return path


def pairs(items):
    return [(n, np.array([x, 0.0, 0.0])) for n, x in items]


# --- the author's rule on toy graphs -----------------------------------------

def test_prediction_order_decides_the_match():
    gt = pairs([("chair", 0.0), ("chair", 0.6)])
    p1, p2 = ("chair", 0.35), ("chair", 0.7)
    # P1 takes the nearer reference (0.6, distance 0.25); P2 then has only 0.0 left, 0.7 away.
    f1, precision, recall = pc.f1_score(gt, pairs([p1, p2]))
    assert (precision, recall) == (0.5, 0.5) and f1 == pytest.approx(0.5)
    # Reverse order: P2 takes 0.6, P1 then takes 0.0 (0.35 away): both match.
    assert pc.f1_score(gt, pairs([p2, p1])) == (1.0, 1.0, 1.0)


def test_threshold_is_strict():
    gt = pairs([("lamp", 0.0)])
    assert pc.f1_score(gt, pairs([("lamp", 0.5)]))[0] == 0.0
    assert pc.f1_score(gt, pairs([("lamp", 0.4999)]))[0] == 1.0


def test_only_same_name_matches():
    gt = pairs([("table", 0.0)])
    assert pc.f1_score(gt, pairs([("chair", 0.0)])) == (0.0, 0.0, 0.0)


def test_one_reference_object_matches_once():
    gt = pairs([("cup", 0.0)])
    f1, precision, recall = pc.f1_score(gt, pairs([("cup", 0.0), ("cup", 0.1)]))
    assert precision == 0.5 and recall == 1.0 and f1 == pytest.approx(2 / 3)


def test_empty_sides_score_zero():
    assert pc.f1_score([], pairs([("cup", 0.0)])) == (0.0, 0.0, 0.0)
    assert pc.f1_score(pairs([("cup", 0.0)]), []) == (0.0, 0.0, 0.0)


def test_parse_objects_drops_doors_and_other_node_types(tmp_path):
    p = write_graph(tmp_path / "g.yaml", [
        obj("door", 0.0), obj("sofa", 1.0), obj("sofa", 2.0, node_type="structure"),
        obj("hall", 3.0, node_type="room"), obj("nothing", 4.0, node_type="nothing"),
        obj("Door", 5.0)])
    names = [n for n, _ in pc.parse_objects(p)]
    # 'door' is excluded; the author's test is case-sensitive, so 'Door' stays.
    assert names == ["sofa", "Door"]


def test_door_in_both_graphs_changes_nothing(tmp_path):
    ref = write_graph(tmp_path / "r.yaml", [obj("bed", 0.0), obj("door", 1.0)])
    pred_with = write_graph(tmp_path / "p1.yaml", [obj("bed", 0.1), obj("door", 1.0), obj("door", 9.0)])
    pred_without = write_graph(tmp_path / "p2.yaml", [obj("bed", 0.1)])
    r = pc.parse_objects(ref)
    assert pc.f1_score(r, pc.parse_objects(pred_with)) == pc.f1_score(r, pc.parse_objects(pred_without)) == (1.0, 1.0, 1.0)


def test_f1_agrees_with_tools_evaluator_on_random_graphs(tmp_path):
    from graph_io import load_eval_graph
    from matching import match_objects
    rng = random.Random(7)
    names = ["bed", "chair", "lamp"]
    for k in range(25):
        def nodes(n):
            return [obj(rng.choice(names), round(rng.uniform(0, 3), 2), round(rng.uniform(0, 3), 2)) for _ in range(n)]
        ref = write_graph(tmp_path / f"r{k}.yaml", nodes(rng.randint(1, 12)))
        pred = write_graph(tmp_path / f"p{k}.yaml", nodes(rng.randint(1, 12)))
        mine = pc.f1_score(pc.parse_objects(ref), pc.parse_objects(pred))
        theirs = match_objects(load_eval_graph(ref).objects, load_eval_graph(pred).objects, threshold=0.5)
        assert mine == (theirs.f1, theirs.precision, theirs.recall)


# --- stages: graph averaging, missing files ----------------------------------

def make_stage(run, n, nav=None, g0=None, g1=None, raw_nav=None):
    d = run / "stages" / str(n)
    d.mkdir(parents=True, exist_ok=True)
    if nav is not None:
        (d / "navigation_stats.json").write_text(json.dumps(
            {"total_path_length_meters": nav[0], "total_navigation_time_seconds": nav[1]}))
    if raw_nav is not None:
        (d / "navigation_stats.json").write_text(json.dumps(raw_nav))
    for gi, nodes in ((0, g0), (1, g1)):
        if nodes is not None:
            write_graph(d / f"habitat_scene_graph_original_graph{gi}.yaml", nodes)


REF_NODES = [obj("bed", 0.0), obj("lamp", 1.0)]
HIT = [obj("bed", 0.1), obj("lamp", 1.1)]       # F1 1.0
HALF = [obj("bed", 0.1), obj("sofa", 5.0)]      # P 0.5, R 0.5, F1 0.5


def refs_for(tmp_path, scene="00853"):
    p = write_graph(tmp_path / "ref.yaml", REF_NODES)
    return {"hm3d": {scene: pc.load_reference(p)}}


def score(tmp_path, run, budget=100.0, scene="00853", **kw):
    spec = pc.RunSpec(run.name, "official", scene, run)
    return pc.score_run(spec, refs_for(tmp_path, scene), {scene: budget}, kw.get("fallback", []))


def test_stage_value_is_the_mean_over_graph0_and_graph1(tmp_path):
    run = tmp_path / "run"
    make_stage(run, 0, nav=(0.0, 0.0), g0=HIT, g1=HALF)
    rec = score(tmp_path, run)
    s = rec["stages"][0]["scores"]["hm3d"]
    assert s["f1"] == pytest.approx(0.75)
    assert s["precision"] == pytest.approx(0.75) and s["recall"] == pytest.approx(0.75)
    assert rec["stages"][0]["n_graphs"] == 2


def test_missing_graph1_scores_graph0_alone(tmp_path):
    run = tmp_path / "run"
    make_stage(run, 0, nav=(0.0, 0.0), g0=HALF)
    make_stage(run, 1, nav=(1.0, 5.0), g1=HIT)
    rec = score(tmp_path, run)
    assert [s["scores"]["hm3d"]["f1"] for s in rec["stages"]] == [pytest.approx(0.5), 1.0]
    assert [s["n_graphs"] for s in rec["stages"]] == [1, 1]


def test_stages_without_stats_or_graphs_are_skipped(tmp_path):
    run = tmp_path / "run"
    make_stage(run, 0, nav=(0.0, 0.0), g0=HIT)
    make_stage(run, 1, g0=HIT)                                   # no navigation_stats.json
    make_stage(run, 2, nav=(2.0, 9.0))                           # no graph YAML
    make_stage(run, 3, raw_nav={"total_navigation_time_seconds": 20.0}, g0=HIT)   # no path length
    make_stage(run, 4, raw_nav={"total_path_length_meters": 4.0}, g0=HIT)         # no time
    make_stage(run, 5, nav=(5.0, 30.0), g0=HIT)
    rec = score(tmp_path, run)
    assert [s["stage"] for s in rec["stages"]] == [0, 5]
    assert {(k["stage"], k["reason"]) for k in rec["skipped_stages"]} == {
        (1, "no_navigation_stats"), (2, "no_graph_yaml"), (3, "no_path_length"), (4, "no_navigation_time")}
    assert rec["final_stage"] == 5 and rec["final_time_s"] == 30.0 and rec["final_path_m"] == 5.0
    assert rec["sec_per_m"] == pytest.approx(6.0)


def test_stages_sort_numerically(tmp_path):
    run = tmp_path / "run"
    for n in (0, 2, 10):
        make_stage(run, n, nav=(float(n), 10.0 * n), g0=HIT)
    assert [s["stage"] for s in score(tmp_path, run)["stages"]] == [0, 2, 10]


def test_fallback_root_fills_missing_files(tmp_path):
    run = tmp_path / "copy" / "scene_ref"
    make_stage(run, 7, g0=HIT)                                    # copy has graph0 only
    mirror = tmp_path / "mirror"
    make_stage(mirror / "scene_ref", 7, nav=(9.0, 50.0), g0=HIT, g1=HALF)
    no_fb = score(tmp_path, run)
    assert no_fb["stages"] == []
    with_fb = score(tmp_path, run, fallback=[mirror])
    assert [s["stage"] for s in with_fb["stages"]] == [7]
    assert with_fb["stages"][0]["n_graphs"] == 2
    filled = {(m["file"], m["filled_from_fallback"]) for m in with_fb["missing_files"]}
    assert ("navigation_stats.json", True) in filled


# --- readouts ----------------------------------------------------------------

def fake_stages(times, f1s):
    return [{"stage": i, "time_s": t, "path_m": t / 5, "scores": {"r": {"f1": f, "precision": f, "recall": f, "ged": None}}}
            for i, (t, f) in enumerate(zip(times, f1s))]


STAGES = fake_stages([0.0, 100.0, 200.0, 300.0], [0.1, 0.5, 0.3, 0.4])


def test_readout_takes_the_last_stage_at_or_before_t():
    r = pc.readout(STAGES, "r", 150.0)
    assert (r["stage"], r["f1"], r["f1_runmax"], r["null_reason"]) == (1, 0.5, 0.5, None)
    r = pc.readout(STAGES, "r", 250.0)
    assert (r["stage"], r["f1"], r["f1_runmax"]) == (2, 0.3, 0.5)      # value fell, running max holds
    assert r["ged"] is None


def test_readout_at_exact_stage_time_counts_that_stage():
    r = pc.readout(STAGES, "r", 300.0)
    assert (r["stage"], r["f1"], r["f1_runmax"]) == (3, 0.4, 0.5)


def test_readout_is_null_when_the_run_never_reached_t():
    r = pc.readout(STAGES, "r", 300.5)
    assert r["f1"] is None and r["f1_runmax"] is None and r["null_reason"] == "run_ended_before_t"
    assert pc.readout(STAGES, "r", 10_000.0)["f1"] is None      # no hold of the last value


def test_readout_is_null_before_the_first_stage():
    late = fake_stages([50.0, 100.0], [0.2, 0.4])
    r = pc.readout(late, "r", 10.0)
    assert r["f1"] is None and r["null_reason"] == "no_stage_at_or_before_t"


def test_readout_with_no_stages_is_null():
    assert pc.readout([], "r", 0.0)["null_reason"] == "no_scored_stages"


def test_time_tolerance_absorbs_rounded_budgets():
    one = fake_stages([632.1256196], [0.5])
    assert pc.readout(one, "r", 632.1256)["f1"] == 0.5          # budget rounded to 4 places
    assert pc.readout(one, "r", 632.2)["f1"] is None


def test_running_max_is_over_stages_not_over_the_whole_run():
    r = pc.readout(STAGES, "r", 50.0)                            # only stage 0 so far
    assert (r["f1"], r["f1_runmax"]) == (0.1, 0.1)


def test_score_run_reads_out_10_50_100_percent_and_the_sensitivity_budgets(tmp_path):
    run = tmp_path / "run"
    make_stage(run, 0, nav=(0.0, 0.0), g0=HALF)
    make_stage(run, 1, nav=(10.0, 40.0), g0=HIT)
    make_stage(run, 2, nav=(20.0, 80.0), g0=HALF)
    rec = score(tmp_path, run, budget=100.0)
    b = rec["readouts"]["hm3d"]["B"]
    assert b["10"]["stage"] == 0                                 # t = 10
    assert b["50"]["stage"] == 1 and b["50"]["f1"] == 1.0        # t = 50
    assert b["100"]["f1"] is None and b["100"]["null_reason"] == "run_ended_before_t"
    lo = rec["readouts"]["hm3d"]["0.8B"]                         # t = 8, 40, 80
    assert (lo["10"]["stage"], lo["50"]["stage"], lo["100"]["stage"]) == (0, 1, 2)
    assert lo["100"]["f1"] == pytest.approx(0.5) and lo["100"]["f1_runmax"] == 1.0
    hi = rec["readouts"]["hm3d"]["1.2B"]                         # t = 12, 60, 120
    assert hi["100"]["f1"] is None
    assert rec["final_time_s"] == 80.0


# --- cells and the paper -----------------------------------------------------

def test_cells_skip_null_runs_and_carry_the_paper_value():
    def rec(arm, f1_at_10, f1_at_100):
        mk = lambda f: {"f1": f, "f1_runmax": f, "precision": f, "recall": f, "ged": None}
        frac = {"10": mk(f1_at_10), "50": mk(f1_at_10), "100": mk(f1_at_100)}
        return {"scene": "00853", "arm": arm, "readouts": {"hm3d": {"B": frac}}}
    cells = pc.aggregate([rec("official", 0.2, None), rec("official", 0.4, None), rec("official", None, None),
                          rec("frontier_60m", 0.1, None), rec("placebo", 0.3, None)])
    by = {(c["arm"], c["fraction"]): c for c in cells}
    c = by[("official", "10")]
    assert c["stage_value_x100"] == {"mean": pytest.approx(30.0), "min": pytest.approx(20.0), "max": pytest.approx(40.0), "n": 2}
    assert c["n_runs"] == 3 and c["paper_f1_x100"] == 34.4 and c["paper_ged"] == 249.5
    assert by[("official", "100")]["stage_value_x100"]["n"] == 0
    assert by[("official", "100")]["paper_f1_x100"] == 66.7
    assert by[("frontier_60m", "50")]["paper_f1_x100"] == 46.5
    assert by[("placebo", "10")]["paper_f1_x100"] is None and by[("placebo", "10")]["paper_method"] is None
    assert all(c["ged"]["n"] == 0 for c in cells)            # no --ged-json given


def test_arm_to_paper_method():
    assert pc.paper_method("frontier_60m") == pc.paper_method("frontier_end") == pc.paper_method("frontier_end_ref") == "Frontier"
    assert pc.paper_method("official") == pc.paper_method("filter_only") == "Semantic (Ours)"
    assert pc.paper_method("placebo") is None and pc.paper_method("oracle_visible") is None
    assert pc.paper_method("apr") is None


def test_parse_paper_fig4_reads_the_flattened_table():
    text = ("GED↓ Scene: 573Scene: 853Frontier19.9231.446.1193.063.0185.018.6279.046.5243.458.8177.0"
            "Semantic (Ours)19.2252.659.0170.568.7163.534.4249.560.8147.066.7147.0"
            "Scene: 871Scene: 69Frontier29.2292.155.7233.065.3203.523.8253.040.6213.059.7149.0 Figure 4: Left")
    got = pc.parse_paper_fig4(text)
    assert got["00573"]["Frontier"] == {"f1": (19.9, 46.1, 63.0), "ged": (231.4, 193.0, 185.0)}
    assert got["00853"]["Semantic (Ours)"]["f1"] == (34.4, 60.8, 66.7)
    assert got["00069"]["Frontier"]["ged"] == (253.0, 213.0, 149.0)


@pytest.mark.skipif(not HTML.exists(), reason="cached arXiv HTML not present")
def test_embedded_paper_table_matches_the_cached_html():
    check = pc.check_paper_table(HTML)
    assert check["checked"] and check["mismatches"] == []


# --- inputs ------------------------------------------------------------------

def test_default_runs_keep_counted_rows_once(tmp_path):
    table = tmp_path / "run_table.csv"
    rows = [
        {"run": "e1_00853_s42_official_60m", "arm": "official", "scene": "00853", "seed": "42", "status": "counted"},
        {"run": "e1_00853_s42_official_60m", "arm": "official", "scene": "00853", "seed": "42", "status": "counted"},
        {"run": "e1_00853_s44_official_60m", "arm": "official", "scene": "00853", "seed": "44", "status": "excluded: stopped at 46.8 m"},
        {"run": "dryrun_x", "arm": "dryrun", "scene": "00069", "seed": "42", "status": "counted"},
        {"run": "e3_00871_s42_oracle_visible_60m", "arm": "oracle_visible", "scene": "00871", "seed": "42", "status": "counted"},
    ]
    with open(table, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (tmp_path / "runs" / "frontier_seeds" / "e4_00853_s42_frontier_60m").mkdir(parents=True)
    specs = pc.default_runs(tmp_path, table)
    assert [(s.name, s.arm) for s in specs] == [
        ("e1_00853_s42_official_60m", "official"), ("e3_00871_s42_oracle_visible_60m", "oracle_visible"),
        ("e4_00853_s42_frontier_60m", "frontier_60m"),
        ("scene00853_frontier_reference", "frontier_end_ref"), ("scene00871_frontier_reference", "frontier_end_ref")]
    assert specs[0].path == tmp_path / "runs" / "live_campaign" / "e1_00853_s42_official_60m"


def test_default_budgets_are_the_reference_run_ends():
    assert pc.DEFAULT_BUDGET == {"00853": 632.1256, "00871": 809.0840}


# --- command line ------------------------------------------------------------

def test_cli_scores_added_runs_with_an_apr_reference(tmp_path):
    run = tmp_path / "e7_00853_s42_frontier_end"
    make_stage(run, 0, nav=(0.0, 0.0), g0=HALF, g1=HALF)
    make_stage(run, 1, nav=(10.0, 60.0), g0=HIT, g1=HIT)
    apr = tmp_path / "apr_00853_a"
    write_graph(apr / "stages" / "3" / "habitat_scene_graph_original_graph0.yaml", REF_NODES)
    out = tmp_path / "out"
    cmd = [sys.executable, SCRIPT, "--root", str(tmp_path / "no_root"), "--no-default-runs", "--no-fallback",
           "--add-run", f"frontier_end=00853={run}", "--apr", f"00853={apr}", "--budget", "00853=60",
           "--out-dir", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    res = json.loads((out / "paper_compare.json").read_text())
    assert list(res["meta"]["references"]) == ["apr"]
    rec = res["runs"][0]
    assert rec["arm"] == "frontier_end" and rec["readouts"]["apr"]["B"]["100"]["f1"] == 1.0
    assert rec["readouts"]["apr"]["B"]["10"]["f1"] == pytest.approx(0.5)
    assert rec["readouts"]["apr"]["B"]["100"]["ged"] is None
    cell = next(c for c in res["cells"] if c["fraction"] == "100" and c["variant"] == "B")
    assert cell["paper_f1_x100"] == 58.8 and cell["ged"]["n"] == 0
    md = (out / "paper_compare.md").read_text()
    assert "## Reference: apr" in md and "frontier_end" in md


def test_cli_stops_when_a_scene_has_no_budget(tmp_path):
    run = tmp_path / "run"
    make_stage(run, 0, nav=(0.0, 0.0), g0=HIT)
    cmd = [sys.executable, SCRIPT, "--no-default-runs", "--add-run", f"apr=00999={run}", "--out-dir", str(tmp_path / "o")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode != 0 and "no budget" in r.stderr


def test_ged_json_values_reach_the_readout_of_the_same_run_and_stage(tmp_path):
    ged = tmp_path / "ged.json"
    ged.write_text(json.dumps({"runs": [{"run_dir": "/workspace/runs/x/myrun", "scene": "00853",
                                         "stages": [{"stage": 3, "ged_hm3d": 210.0, "ged_frontier_made": 99.5}]}]}))
    pc.GED_LOOKUP.clear()
    assert pc.load_ged_json(ged) == 1
    yaml_path = str(tmp_path / "myrun" / "stages" / "3" / "habitat_scene_graph_original_graph0.yaml")
    assert pc.ged_stage_value([yaml_path], "ref.yaml", "hm3d") == 210.0
    assert pc.ged_stage_value([yaml_path], "ref.yaml", "frontier_made") == 99.5
    assert pc.ged_stage_value([yaml_path], "ref.yaml", "apr") is None
    other = str(tmp_path / "myrun" / "stages" / "4" / "habitat_scene_graph_original_graph0.yaml")
    assert pc.ged_stage_value([other], "ref.yaml", "hm3d") is None
    pc.GED_LOOKUP.clear()
