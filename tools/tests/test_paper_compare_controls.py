"""The control arms of PREREGISTRATION_PAPER.md, Amendment 5, in paper_compare.py: the arms `placebo_nov` and
`observed_only_nov`, their name patterns and the guard against pooling, the reach rules of A5.3, and the pure
decision function of A5.6."""
import json
import os
import sys

import pytest
import yaml

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "live_policy"))
sys.path.insert(1, os.path.join(HERE, "..", "live_policy", "host"))
import paper_compare as pc  # noqa: E402

B853 = 632.1750566959381
PLC = "e9_00853_s{}_placebo_115m"
OBS = "e9_00853_s{}_observed_only_115m"
OCT_PLACEBO = "e1_00853_s{}_placebo_60m"


def obj(name, x):
    return {"name": name, "position": f"[{x}, 0.0, 0.0]", "node_type": "object"}


REF_NODES = [obj("bed", 0.0), obj("lamp", 1.0)]
HIT = [obj("bed", 0.1), obj("lamp", 1.1)]       # F1 1.0
HALF = [obj("bed", 0.1), obj("sofa", 5.0)]      # F1 0.5


def write_graph(path, nodes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"nodes": [{"id": i, **n} for i, n in enumerate(nodes)], "edges": []}))


def make_run(camp, name, pts, log=None, last_g1=True):
    """pts: (path m, time s, graph) per stage. log: text of logs/roslaunch.log, or None for no log."""
    run = camp / name
    for n, (m, t, g) in enumerate(pts):
        d = run / "stages" / str(n)
        d.mkdir(parents=True, exist_ok=True)
        (d / "navigation_stats.json").write_text(json.dumps({"total_path_length_meters": m, "total_navigation_time_seconds": t}))
        write_graph(d / "habitat_scene_graph_original_graph0.yaml", g)
        if not (n == len(pts) - 1 and not last_g1):
            write_graph(d / "habitat_scene_graph_original_graph1.yaml", g)
    if log is not None:
        (run / "logs").mkdir(parents=True, exist_ok=True)
        (run / "logs" / "roslaunch.log").write_text(log)
    return run


GOOD = [(0, 0.0, HALF), (30, 200.0, HALF), (50, 330.0, HIT), (60, 400.0, HIT), (80, 520.0, HIT), (100, 640.0, HIT), (115, 700.0, HIT)]


def refs(tmp):
    ref = pc.load_reference(write_graph_return(tmp / "ref.yaml", REF_NODES))
    return {"apr": {"00853": ref}, "hm3d": {"00853": ref}}


def write_graph_return(path, nodes):
    write_graph(path, nodes)
    return path


def score(tmp, run, arm, budget=B853):
    spec = pc.RunSpec(run.name, arm, "00853", run, 42)
    return pc.score_run(spec, refs(tmp), {"00853": budget}, [])


# --- names ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [42, 43, 44])
def test_each_arm_takes_its_three_seeds_with_or_without_relaunch1(seed):
    for fmt, arm in ((PLC, "placebo_nov"), (OBS, "observed_only_nov")):
        for suffix in ("", "_relaunch1"):
            assert pc.CTRL_RE[arm].match(fmt.format(seed) + suffix)
            assert pc.ctrl_arm_of(fmt.format(seed) + suffix) == arm


@pytest.mark.parametrize("name", ["dryrun_e9_00853_s42_placebo_5m", "dryrun_e9_00853_s42_observed_only_5m", "e9_00853_s42_placebo_5m",
                                  "e9_00853_s45_placebo_115m", "e9_00871_s42_placebo_115m", "e9_00853_s42_placebo_115m_relaunch2",
                                  "e9_00853_s42_placebo_115m_FAILED_ATTEMPT_1", "xe9_00853_s42_placebo_115m", "e9_00853_s42_placebo_115mx",
                                  OCT_PLACEBO.format(42), "e1_00853_s42_official_60m", "e8_00853_s42_official_105m",
                                  "e9_00853_s42_official_115m", "e9_00853_s42_oracle_115m"])
def test_the_patterns_are_anchored_and_refuse_everything_else(name):
    assert pc.ctrl_arm_of(name) is None


def test_arm_order_labels_and_paper_column():
    assert pc.ARM_ORDER.index("placebo_nov") == pc.ARM_ORDER.index("official_nov") + 1
    assert pc.ARM_ORDER.index("observed_only_nov") == pc.ARM_ORDER.index("placebo_nov") + 1
    assert pc.ARM_ORDER.index("placebo") > pc.ARM_ORDER.index("observed_only_nov")      # October's placebo is another arm
    for arm in pc.CTRL_ARMS:
        assert pc.paper_method(arm) is None and arm not in pc.COUNTED_ARMS and arm in pc.ARM_LABELS


# --- no pooling: October's placebo and the control arms ----------------------------------------------

def _rec(arm, name, seed, f1):
    entry = {"t_s": 1.0, "stage": 1, "stage_time_s": 1.0, "f1": f1, "f1_runmax": f1, "precision": f1, "recall": f1,
             "ged": None, "null_reason": None}
    return {"run": name, "arm": arm, "scene": "00853", "seed": seed, "readouts": {"hm3d": {"B": {"10": entry, "50": entry, "100": entry}}}}


def test_a_run_named_for_octobers_placebo_cannot_enter_placebo_nov_and_the_reverse():
    with pytest.raises(ValueError):
        pc.check_arm_name("placebo_nov", OCT_PLACEBO.format(42), "00853")
    with pytest.raises(ValueError):
        pc.check_arm_name("placebo", PLC.format(42), "00853")
    with pytest.raises(ValueError):
        pc.aggregate([_rec("placebo_nov", OCT_PLACEBO.format(42), 42, 0.3)])
    with pytest.raises(ValueError):
        pc.aggregate([_rec("placebo", PLC.format(42), 42, 0.3)])
    assert pc.check_arm_name("placebo", OCT_PLACEBO.format(42), "00853") is None
    assert pc.check_arm_name("placebo_nov", PLC.format(42), "00853") is None


def test_no_control_name_enters_any_other_arm_and_no_arm_takes_the_other_controls_name():
    for arm in ("official", "official_nov", "filter_only", "oracle_visible", "frontier_end", "frontier_60m"):
        for name in (PLC.format(42), OBS.format(42), "dryrun_e9_00853_s42_placebo_5m"):
            with pytest.raises(ValueError):
                pc.check_arm_name(arm, name, "00853")
    with pytest.raises(ValueError):
        pc.check_arm_name("placebo_nov", OBS.format(42), "00853")
    with pytest.raises(ValueError):
        pc.check_arm_name("observed_only_nov", PLC.format(42), "00853")
    for name in ("dryrun_e9_00853_s42_placebo_5m", "e9_00853_s45_placebo_115m", OCT_PLACEBO.format(42), "e8_00853_s42_official_105m"):
        with pytest.raises(ValueError):
            pc.check_arm_name("placebo_nov", name, "00853")
        with pytest.raises(ValueError):
            pc.check_arm_name("observed_only_nov", name.replace("placebo", "observed_only"), "00853")
    with pytest.raises(ValueError):
        pc.check_arm_name("placebo_nov", PLC.format(42), "00871")      # 00853 only
    with pytest.raises(ValueError):
        pc.check_arm_name("official_nov", PLC.format(42), "00853")


def test_octobers_placebo_and_the_control_keep_their_own_row_and_own_n():
    cells = pc.aggregate([_rec("placebo", OCT_PLACEBO.format(42), 42, 0.2), _rec("placebo", OCT_PLACEBO.format(43), 43, 0.4),
                          _rec("placebo_nov", PLC.format(42), 42, 0.6), _rec("observed_only_nov", OBS.format(42), 42, 0.1)])
    pick = lambda arm: [c for c in cells if c["arm"] == arm and c["fraction"] == "10" and c["variant"] == "B"][0]
    assert pick("placebo")["n_runs"] == 2 and pick("placebo")["stage_value_x100"]["mean"] == pytest.approx(30.0)
    assert pick("placebo_nov")["n_runs"] == 1 and pick("placebo_nov")["stage_value_x100"]["mean"] == pytest.approx(60.0)
    assert pick("observed_only_nov")["n_runs"] == 1 and pick("observed_only_nov")["paper_method"] is None


def test_run_table_row_with_an_e9_name_is_refused(tmp_path):
    for name in (PLC.format(42), "dryrun_e9_00853_s42_placebo_5m"):
        t = tmp_path / "t.csv"
        t.write_text("run,arm,scene,seed,status\n" + f"{name},placebo,00853,42,counted\n")
        with pytest.raises(ValueError, match="e9"):
            pc.default_runs(tmp_path, t)


@pytest.mark.parametrize("arm,name,scene", [("placebo_nov", OCT_PLACEBO.format(42), "00853"), ("placebo", PLC.format(42), "00853"),
                                            ("placebo_nov", OBS.format(42), "00853"), ("observed_only_nov", PLC.format(42), "00853"),
                                            ("placebo_nov", "dryrun_e9_00853_s42_placebo_5m", "00853"),
                                            ("placebo_nov", PLC.format(42), "00871"), ("official_nov", PLC.format(42), "00853")])
def test_add_run_refuses_wrong_names_arms_and_scenes(tmp_path, arm, name, scene):
    run = make_run(tmp_path, name, GOOD)
    with pytest.raises(SystemExit):
        pc.main(["--no-default-runs", "--no-fallback", "--add-run", f"{arm}={scene}={run}", "--budget", f"{scene}=632",
                 "--out-dir", str(tmp_path / "o")])


# --- one folder per arm and seed -----------------------------------------------------------------------

def test_a_relaunch_beside_a_started_original_is_an_error_that_names_both(tmp_path):
    a, b = make_run(tmp_path, PLC.format(42), GOOD), make_run(tmp_path, PLC.format(42) + "_relaunch1", GOOD)
    with pytest.raises(ValueError) as e:
        pc.check_ctrl_pairs([a, b])
    assert a.name in str(e.value) and b.name in str(e.value)


SKIPPED = {"skipped_exists": 1, "skipped_campaign_cap": 1, "skipped_host_memory": 1, "launch_failed": 1}


@pytest.mark.parametrize("outcome", ["skipped_exists", "skipped_campaign_cap", "skipped_host_memory", "launch_failed"])
def test_a_relaunch_replaces_an_original_the_runner_recorded_as_skipped_or_failed_to_launch(tmp_path, outcome):
    first = tmp_path / PLC.format(42)
    (first / "config").mkdir(parents=True)                       # a folder was left behind
    relaunch = make_run(tmp_path, PLC.format(42) + "_relaunch1", GOOD)
    other_arm = make_run(tmp_path, OBS.format(42), GOOD)          # same seed, other arm: its own group
    outcomes = {PLC.format(42): outcome}
    assert pc.check_ctrl_pairs([first, relaunch, other_arm], outcomes) == [relaunch, other_arm]
    assert pc.check_ctrl_pairs([make_run(tmp_path, PLC.format(43), GOOD), relaunch], outcomes) == [tmp_path / PLC.format(43), relaunch]


@pytest.mark.parametrize("outcome", [None, "target_reached", "stopped_by_control_file", "pipeline_exited", "stalled", "host_memory_low"])
def test_a_folder_with_no_stage_whose_launcher_started_is_a_run_that_happened_and_no_relaunch_replaces_it(tmp_path, outcome):
    first = tmp_path / PLC.format(42)
    (first / "config").mkdir(parents=True)                       # launched, wrote no stage
    relaunch = make_run(tmp_path, PLC.format(42) + "_relaunch1", GOOD)
    outcomes = {} if outcome is None else {PLC.format(42): outcome}
    with pytest.raises(ValueError) as e:
        pc.check_ctrl_pairs([first, relaunch], outcomes)
    assert first.name in str(e.value) and relaunch.name in str(e.value) and "launch_failed" in str(e.value)
    with pytest.raises(ValueError):
        pc.check_ctrl_pairs([first, relaunch])                    # no record at all: never accepted


def test_a_lone_relaunch_needs_the_record_of_its_original_when_records_are_given(tmp_path):
    relaunch = make_run(tmp_path, OBS.format(44) + "_relaunch1", GOOD)
    assert pc.check_ctrl_pairs([relaunch]) == [relaunch]          # the scorer alone has no records: the rescore gives them
    assert pc.check_ctrl_pairs([relaunch], {OBS.format(44): "skipped_host_memory"}) == [relaunch]
    for outcomes in ({}, {OBS.format(44): "target_reached"}):
        with pytest.raises(ValueError, match="relaunch is allowed only"):
            pc.check_ctrl_pairs([relaunch], outcomes)


def test_the_same_folder_twice_and_a_foreign_name_are_refused(tmp_path):
    a = make_run(tmp_path, PLC.format(42), GOOD)
    with pytest.raises(ValueError):
        pc.check_ctrl_pairs([a, a])
    with pytest.raises(ValueError):
        pc.check_ctrl_pairs([make_run(tmp_path, OCT_PLACEBO.format(42), GOOD)])


def test_cli_stops_on_a_relaunch_beside_a_started_original(tmp_path):
    a, b = make_run(tmp_path, OBS.format(44), GOOD), make_run(tmp_path, OBS.format(44) + "_relaunch1", GOOD)
    with pytest.raises(SystemExit) as ex:
        pc.main(["--no-default-runs", "--no-fallback", "--add-run", f"observed_only_nov=00853={a}",
                 "--add-run", f"observed_only_nov=00853={b}", "--budget", "00853=632", "--out-dir", str(tmp_path / "o")])
    assert OBS.format(44) in str(ex.value) and "_relaunch1" in str(ex.value)


# --- the GPU lines: one rule ----------------------------------------------------------------------------

LINES = [("CUDA error: Out Of Memory in allocation", 1, 0), ("OUT OF MEMORY", 1, 0), ("out of memory", 1, 0),
         ("[nvblox_node-3] process has died [pid 123, exit code -11]", 0, 1), ("nvblox_node has died", 0, 1),
         ("NVBLOX_NODE HAS DIED", 0, 1), ("nvblox_node started", 0, 0), ("some other node has died", 0, 0),
         ("the process has died but not nvblox", 0, 0), ("process[nvblox_node-3]: started", 0, 0),
         ("out of memory\n[nvblox_node-3] process has died\nout of memory", 2, 1), ("", 0, 0)]


@pytest.mark.parametrize("text,oom,died", LINES)
def test_roslaunch_lines_count_the_two_lines_case_ignored(tmp_path, text, oom, died):
    run = make_run(tmp_path, PLC.format(42), GOOD, log=text + "\n")
    assert pc.roslaunch_lines(run) == {"out_of_memory_lines": oom, "nvblox_died_lines": died}


def test_roslaunch_lines_of_a_run_with_no_log_are_none(tmp_path):
    assert pc.roslaunch_lines(make_run(tmp_path, PLC.format(42), GOOD)) == {"out_of_memory_lines": None, "nvblox_died_lines": None}


@pytest.mark.parametrize("text,oom,died", LINES)
def test_the_scorers_rule_is_the_e7_checks_rule(tmp_path, text, oom, died):
    import check_paper_runs as cpr
    p = tmp_path / "roslaunch.log"
    p.write_text(text + "\n")
    assert cpr.grep_count(str(p), pc.OOM_PATTERN) == oom and cpr.grep_count(str(p), pc.DIED_PATTERN) == died


# --- reach (A5.3) -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("arm,name", [("placebo_nov", PLC.format(42)), ("observed_only_nov", OBS.format(42))])
def test_a_control_run_that_reached_b_has_a_100_value(tmp_path, arm, name):
    rec = score(tmp_path, make_run(tmp_path, name, GOOD, log="ok\n"), arm)
    ro = rec["readouts"]["apr"]["B"]
    assert ro["100"]["f1"] == 1.0 and ro["10"]["f1"] is not None and ro["50"]["f1"] is not None
    assert rec["reached_b"] is True and rec["no_final_value"] is False and rec["reached_end_path_m"] == 115
    assert rec["roslaunch"] == {"out_of_memory_lines": 0, "nvblox_died_lines": 0}


def test_a_control_run_short_of_b_keeps_10_and_50_and_has_no_100(tmp_path):
    pts = GOOD[:-1][:-1] + [(100, 600.0, HIT)]
    rec = score(tmp_path, make_run(tmp_path, PLC.format(42), pts, log="ok\n"), "placebo_nov")
    ro = rec["readouts"]["apr"]["B"]
    assert ro["100"]["f1"] is None and ro["100"]["null_reason"] == "run_ended_before_t"
    assert ro["10"]["f1"] is not None and ro["50"]["f1"] is not None and rec["reached_b"] is False


def test_reach_is_strict_and_needs_both_graphs(tmp_path):
    one_short = score(tmp_path, make_run(tmp_path, PLC.format(42), GOOD[:5] + [(115, B853 - 0.0009, HIT)], log="ok\n"), "placebo_nov")
    assert one_short["readouts"]["apr"]["B"]["100"]["f1"] is None and one_short["reached_b"] is False
    exact = score(tmp_path, make_run(tmp_path, PLC.format(43), GOOD[:5] + [(115, B853, HIT)], log="ok\n"), "placebo_nov")
    assert exact["readouts"]["apr"]["B"]["100"]["f1"] is not None and exact["reached_b"] is True
    no_g1 = score(tmp_path, make_run(tmp_path, PLC.format(44), GOOD[:5] + [(100, 640.0, HIT)], log="ok\n", last_g1=False), "observed_only_nov")
    assert no_g1["readouts"]["apr"]["B"]["100"]["f1"] is None and no_g1["reached_end_s"] == 520.0
    assert no_g1["reached_end_path_m"] == 80


@pytest.mark.parametrize("text", ["CUDA error: out of memory\n", "[nvblox_node-3] process has died [pid 1]\n", "OUT OF MEMORY\nnvblox_node has died\n"])
def test_a_control_run_with_a_gpu_line_has_no_value_at_100_of_b_and_keeps_its_other_cells(tmp_path, text):
    rec = score(tmp_path, make_run(tmp_path, PLC.format(42), GOOD, log=text), "placebo_nov")
    assert rec["no_final_value"] is True and rec["reached_b"] is True      # it did reach B; the rule still gives no 100% value
    for ref in ("apr", "hm3d"):
        b = rec["readouts"][ref]["B"]
        assert b["100"]["f1"] is None and b["100"]["null_reason"] == "run_ended_before_t"
        assert b["10"]["f1"] is not None and b["50"]["f1"] is not None
    # the sensitivity reads are other times: 0.8 B stays, 1.2 B is beyond B and is null
    assert rec["readouts"]["apr"]["0.8B"]["100"]["f1"] is not None
    assert rec["readouts"]["apr"]["1.2B"]["100"]["f1"] is None


def test_a_gpu_line_on_a_run_that_ended_before_b_changes_nothing_more(tmp_path):
    pts = GOOD[:-2] + [(90, 580.0, HIT)]
    rec = score(tmp_path, make_run(tmp_path, PLC.format(42), pts, log="out of memory\n"), "placebo_nov")
    assert rec["no_final_value"] is True and rec["reached_b"] is False
    assert rec["readouts"]["apr"]["B"]["50"]["f1"] is not None and rec["readouts"]["apr"]["B"]["100"]["f1"] is None


def test_a_control_run_with_no_log_is_marked_like_one_with_a_gpu_line(tmp_path):
    rec = score(tmp_path, make_run(tmp_path, PLC.format(42), GOOD), "placebo_nov")
    assert rec["no_final_value"] is True and rec["roslaunch"] == {"out_of_memory_lines": None, "nvblox_died_lines": None}
    ro = rec["readouts"]["apr"]["B"]
    assert ro["100"]["f1"] is None and ro["10"]["f1"] is not None and ro["50"]["f1"] is not None
    assert rec["readouts"]["apr"]["1.2B"]["100"]["f1"] is None and rec["readouts"]["apr"]["0.8B"]["100"]["f1"] is not None


def test_is_void_reads_a_missing_log_as_void_and_a_clean_one_as_not():
    assert pc.is_void({"out_of_memory_lines": None, "nvblox_died_lines": None}) is True
    assert pc.is_void({"out_of_memory_lines": 0, "nvblox_died_lines": 0}) is False
    assert pc.is_void({"out_of_memory_lines": 0, "nvblox_died_lines": 2}) is True and pc.is_void({"out_of_memory_lines": 1, "nvblox_died_lines": 0}) is True
    assert pc.is_void(None) is False                            # not a control run: no lines were read


@pytest.mark.parametrize("log", ["out of memory\n", "nvblox_node has died\n", None])
def test_a_marked_run_has_no_value_at_any_t_at_or_past_b_and_keeps_every_cell_below_b(tmp_path, log):
    """A5.3 and item 8: the cells at t = B and 1.2 B are empty; 0.8 B, and the 10% and 50% cells of every variant, stay."""
    rec = score(tmp_path, make_run(tmp_path, PLC.format(42), GOOD + [(130, 800.0, HIT)], log=log), "placebo_nov")
    assert rec["no_final_value"] is True
    for ref in ("apr", "hm3d"):
        for variant, mult in pc.VARIANTS:
            for flabel, frac in pc.FRACTIONS:
                t = B853 * mult * frac
                cell = rec["readouts"][ref][variant][flabel]
                if t >= B853:
                    assert cell["f1"] is None and cell["null_reason"] == "run_ended_before_t", (variant, flabel)
                else:
                    assert cell["f1"] is not None, (variant, flabel)
    assert rec["readouts"]["apr"]["1.2B"]["100"]["f1"] is None and rec["readouts"]["apr"]["1.2B"]["50"]["f1"] is not None


def test_a_strict_arm_reads_its_values_only_from_complete_stages(tmp_path):
    """Item 4: a stage with one graph file gives no value, as it gives no reach. Stage 4 (520 s, 80 m) lacks graph1 and is the
    last stage at or before B; the F1 of stage 4 is 0.5 and that of stage 3 is 1.0 (the graph differs, so the two readings differ)."""
    pts = [(0, 0.0, HALF), (30, 200.0, HALF), (50, 330.0, HIT), (60, 400.0, HIT), (80, 520.0, HALF), (100, 640.0, HIT)]
    run = make_run(tmp_path / "camp", PLC.format(42), pts, log="ok\n")
    (run / "stages" / "4" / "habitat_scene_graph_original_graph1.yaml").unlink()
    got = {}
    for arm in ("placebo_nov", "official_nov", "official"):
        spec = pc.RunSpec(run.name, arm, "00853", run, 42)
        got[arm] = pc.score_run(spec, refs(tmp_path), {"00853": B853}, [])["readouts"]["apr"]["B"]["100"]
    assert got["placebo_nov"]["stage"] == got["official_nov"]["stage"] == 3 and got["placebo_nov"]["f1"] == 1.0
    assert got["official"]["stage"] == 4                                      # an October arm reads one graph as enough, as filed


# --- the files and the table -------------------------------------------------------------------------------

def _root(tmp):
    root = tmp / "root"
    write_graph(root / "runs" / "live_campaign" / "hm3d_refs_work" / "00853_hm3d_reference.yaml", REF_NODES)
    write_graph(tmp / "apr" / "stages" / "3" / "habitat_scene_graph_original_graph0.yaml", REF_NODES)
    t = tmp / "t.csv"
    t.write_text("run,arm,scene,seed,status\n")
    return root, t


def _argv(tmp, root, table, add, extra=()):
    argv = ["--root", str(root), "--run-table", str(table), "--no-fallback", "--apr", f"00853={tmp / 'apr'}",
            "--budget", "00853=632.1750566959381", "--out-dir", str(tmp / "out"), *extra]
    for arm, path in add:
        argv += ["--add-run", f"{arm}=00853={path}"]
    return argv


def test_cli_scores_both_control_arms_into_their_own_labelled_rows_and_marks_the_void_run(tmp_path, capsys):
    root, table = _root(tmp_path)
    camp = root / "runs" / "live_campaign"
    add = [("placebo_nov", make_run(camp, PLC.format(42), GOOD, log="ok\n")),
           ("placebo_nov", make_run(camp, PLC.format(43), GOOD, log="CUDA out of memory\n")),
           ("observed_only_nov", make_run(camp, OBS.format(42), GOOD, log="ok\n")),
           ("official", make_run(camp, OCT_PLACEBO.format(42), GOOD))]
    make_run(camp, PLC.format(44), GOOD)                 # on disk but not passed: named on stderr, not scored
    assert pc.main(_argv(tmp_path, root, table, add)) == 0
    res = json.loads((tmp_path / "out" / "paper_compare.json").read_text())
    pick = lambda arm, f: [c for c in res["cells"] if c["arm"] == arm and c["reference"] == "apr" and c["variant"] == "B" and c["fraction"] == f][0]
    assert pick("placebo_nov", "10")["n_runs"] == 2 and pick("placebo_nov", "100")["stage_value_x100"]["n"] == 1
    assert pick("observed_only_nov", "100")["stage_value_x100"]["n"] == 1 and pick("official", "10")["n_runs"] == 1
    md = (tmp_path / "out" / "paper_compare.md").read_text()
    assert "| 00853 | ASP + random guesses (control), November | none |" in md and "placebo_nov" not in md
    assert "Amendment 5's control arms" in md and f"Marked: `{PLC.format(43)}`" in md
    err = capsys.readouterr().err
    assert "control runs are assessed by rescore_paper.py: " + PLC.format(44) in err


def test_no_control_note_and_no_stderr_line_without_control_runs(tmp_path, capsys):
    root, table = _root(tmp_path)
    run = make_run(root / "runs" / "live_campaign", "e8_00853_s42_official_105m", GOOD, log="ok\n")
    assert pc.main(_argv(tmp_path, root, table, [("official_nov", run)])) == 0
    md = (tmp_path / "out" / "paper_compare.md").read_text()
    assert "Amendment 5" not in md and "Marked:" not in md
    assert "control runs" not in capsys.readouterr().err


def test_default_runs_never_pick_an_e9_run(tmp_path):
    camp = tmp_path / "runs" / "live_campaign"
    for n in (PLC.format(42), OBS.format(43) + "_relaunch1", "dryrun_e9_00853_s42_placebo_5m"):
        make_run(camp, n, GOOD)
    t = tmp_path / "t.csv"
    t.write_text("run,arm,scene,seed,status\n")
    assert not [s for s in pc.default_runs(tmp_path, t) if s.arm in pc.CTRL_ARMS or pc.NINE_RE.match(s.name)]
    assert [s.name for s in pc.ctrl_runs(tmp_path)] == sorted([PLC.format(42), OBS.format(43) + "_relaunch1"])


# --- A5.6: the decision, as a table ---------------------------------------------------------------------------

OFF = ["e8_00853_s42_official_105m", "e8_00853_s43_official_105m", "e8_00853_s44_official_105m"]
CTL = {"placebo_nov": [PLC.format(s) for s in (42, 43, 44)], "observed_only_nov": [OBS.format(s) for s in (42, 43, 44)]}


def s_table(off, plc, obs, off_h=None, plc_h=None, obs_h=None):
    """S values for both references; the HM3D values default to the APR ones. A list shorter than 3 holds fewer runs."""
    def arm(names, vals):
        return {n: v for n, v in zip(names, vals)}
    def ref(o, p, b):
        out = {"official_nov": arm(OFF, o)}
        if p is not None:
            out["placebo_nov"] = arm(CTL["placebo_nov"], p)
        if b is not None:
            out["observed_only_nov"] = arm(CTL["observed_only_nov"], b)
        return out
    return {"apr": ref(off, plc, obs), "hm3d": ref(off if off_h is None else off_h, plc if plc_h is None else plc_h,
                                                  obs if obs_h is None else obs_h)}


ABOVE = [60.0, 62.0, 64.0]
LOW = [40.0, 42.0, 44.0]
HIGH = [70.0, 72.0, 74.0]

def test_compare_s_each_branch_and_ties():
    assert pc.compare_s([60, 62, 64], [40, 42, 44]) == pc.SEPARATED
    assert pc.compare_s([50.0001, 60, 70], [40, 45, 50.0]) == pc.SEPARATED
    assert pc.compare_s([50, 60, 70], [40, 45, 50]) == pc.ABOVE_AVG              # a tie at the edge is not separated
    assert pc.compare_s([45, 60, 70], [40, 50, 55]) == pc.ABOVE_AVG              # overlap, official higher on average
    assert pc.compare_s([40, 50, 60], [50, 50, 50]) == pc.NOT_ABOVE              # equal means: not higher, so not above
    assert pc.compare_s([50, 50, 50], [50, 50, 50]) == pc.NOT_ABOVE              # all tied
    assert pc.compare_s([30, 31, 32], [60, 62, 64]) == pc.NOT_ABOVE
    assert pc.compare_s([30, 80, 90], [60, 62, 64]) == pc.ABOVE_AVG
    assert pc.compare_s([60, 62, 64], [40, 42, 44, 99.0]) == pc.ABOVE_AVG        # a fourth control run counts


def test_both_arms_judged_and_separated_above_under_both_references_reads_above_with_both_phrases():
    d = pc.decide_controls(s_table(HIGH, LOW, LOW))
    for arm in pc.CTRL_ARMS:
        a = d["arms"][arm]
        assert a["judged"] and a["per_reference"] == {"apr": pc.SEPARATED, "hm3d": pc.SEPARATED} and a["statement"] == "reads above"
    assert d["slide"]["kind"] == "reads_above_every_judged_arm" and d["slide"]["judged_arms"] == ["placebo_nov", "observed_only_nov"]
    assert d["slide"]["sentence"] == ("With random guesses, or none, the same pipeline reads lower on this home: "
                                      "here the LLM's guesses add to ASP's score.")


def test_the_slide_names_only_the_judged_arms_placebo_alone_and_observed_alone():
    d = pc.decide_controls(s_table(HIGH, LOW, LOW[:2]))                       # observed_only has 2 runs
    assert d["arms"]["placebo_nov"]["statement"] == "reads above" and d["arms"]["observed_only_nov"]["statement"] == "no statement"
    assert d["slide"]["sentence"] == ("With random guesses, the same pipeline reads lower on this home: "
                                      "here the LLM's guesses add to ASP's score.")
    assert d["slide"]["judged_arms"] == ["placebo_nov"]
    d = pc.decide_controls(s_table(HIGH, LOW[:2], LOW))
    assert d["slide"]["sentence"] == ("With no guesses, the same pipeline reads lower on this home: "
                                      "here the LLM's guesses add to ASP's score.")
    assert d["slide"]["judged_arms"] == ["observed_only_nov"]


def test_both_arms_not_above_gives_the_second_sentence_with_both_phrases():
    d = pc.decide_controls(s_table(LOW, HIGH, HIGH))
    for arm in pc.CTRL_ARMS:
        assert d["arms"][arm]["statement"] == "does not read above"
        assert d["arms"][arm]["per_reference"] == {"apr": pc.NOT_ABOVE, "hm3d": pc.NOT_ABOVE}
    assert d["slide"]["kind"] == "does_not_read_above_any_judged_arm"
    assert d["slide"]["sentence"] == ("With random guesses, or none, the same pipeline reads as high: "
                                      "November's lead over frontier is not shown to come from the LLM's guesses.")


def test_one_judged_arm_that_does_not_read_above_names_only_that_arm():
    d = pc.decide_controls(s_table(LOW, HIGH, HIGH[:2]))
    assert d["slide"]["sentence"] == ("With random guesses, the same pipeline reads as high: "
                                      "November's lead over frontier is not shown to come from the LLM's guesses.")
    d = pc.decide_controls(s_table(LOW, HIGH[:1], HIGH))
    assert d["slide"]["sentence"].startswith("With no guesses, the same pipeline reads as high:")


def test_both_arms_judged_with_different_statements_gives_no_sentence_and_both_tables():
    d = pc.decide_controls(s_table(HIGH, LOW, [x + 40 for x in HIGH]))
    assert d["arms"]["placebo_nov"]["statement"] == "reads above" and d["arms"]["observed_only_nov"]["statement"] == "does not read above"
    assert d["slide"]["kind"] == "both_tables_and_statements" and d["slide"]["sentence"] is None
    assert "both S tables and the statements" in d["slide"]["text"]


def test_a_reads_above_arm_beside_an_in_between_arm_gives_no_sentence():
    mixed = [45.0, 80.0, 90.0]                                                   # above on average, not separated
    d = pc.decide_controls(s_table(mixed, [50.0, 55.0, 60.0], [55.0, 56.0, 57.0]))
    assert d["arms"]["placebo_nov"]["statement"] == "in between" and d["arms"]["observed_only_nov"]["statement"] == "in between"
    assert d["slide"]["sentence"] is None and d["slide"]["kind"] == "both_tables_and_statements"
    d = pc.decide_controls(s_table(HIGH, LOW, [65.0, 66.0, 73.0]))
    assert d["arms"]["placebo_nov"]["statement"] == "reads above" and d["arms"]["observed_only_nov"]["statement"] == "in between"
    assert d["slide"]["sentence"] is None


def test_in_between_when_the_two_references_disagree_and_it_says_what_each_gave():
    d = pc.decide_controls(s_table(HIGH, LOW, LOW, off_h=LOW, plc_h=HIGH, obs_h=HIGH))
    a = d["arms"]["placebo_nov"]
    assert a["per_reference"] == {"apr": pc.SEPARATED, "hm3d": pc.NOT_ABOVE} and a["statement"] == "in between"
    assert a["in_between"] == "apr: separated above; hm3d: not above"
    assert d["slide"]["sentence"] is None
    d = pc.decide_controls(s_table(HIGH, LOW, LOW, off_h=[45.0, 80.0, 90.0], plc_h=[60.0, 62.0, 64.0], obs_h=LOW))
    assert d["arms"]["placebo_nov"]["per_reference"] == {"apr": pc.SEPARATED, "hm3d": pc.ABOVE_AVG}
    assert d["arms"]["placebo_nov"]["statement"] == "in between"
    assert d["arms"]["observed_only_nov"]["statement"] == "reads above"          # the arms are judged apart


def test_ties_in_s():
    # a tie between the lowest official S and the highest control S: not separated, but above on average
    d = pc.decide_controls(s_table([50.0, 60.0, 70.0], [40.0, 45.0, 50.0], [40.0, 45.0, 50.0]))
    assert d["arms"]["placebo_nov"]["per_reference"]["apr"] == pc.ABOVE_AVG and d["arms"]["placebo_nov"]["statement"] == "in between"
    # equal means: not above
    d = pc.decide_controls(s_table([40.0, 50.0, 60.0], [50.0, 50.0, 50.0], [50.0, 50.0, 50.0]))
    assert d["arms"]["placebo_nov"]["statement"] == "does not read above"
    # every S equal
    d = pc.decide_controls(s_table([50.0] * 3, [50.0] * 3, [50.0] * 3))
    assert d["arms"]["observed_only_nov"]["per_reference"]["hm3d"] == pc.NOT_ABOVE
    # two control runs tied with each other, both below every official run
    d = pc.decide_controls(s_table(HIGH, [40.0, 40.0, 40.0], [40.0, 40.0, 41.0]))
    assert d["arms"]["placebo_nov"]["statement"] == "reads above"


def test_a_control_arm_with_two_runs_gets_no_statement_and_lists_its_s_values():
    d = pc.decide_controls(s_table(HIGH, LOW[:2], LOW))
    a = d["arms"]["placebo_nov"]
    assert a["judged"] is False and a["statement"] == "no statement" and a["per_reference"] == {}
    assert "2 of its runs have S" in a["why_no_statement"] and "3 are needed" in a["why_no_statement"]
    assert a["S"]["apr"] == {CTL["placebo_nov"][0]: 40.0, CTL["placebo_nov"][1]: 42.0}
    assert d["arms"]["observed_only_nov"]["judged"] is True


def test_a_run_that_stopped_at_90_m_has_no_s_and_the_arm_is_not_judged():
    d = pc.decide_controls(s_table(HIGH, [40.0, 42.0, None], LOW))
    a = d["arms"]["placebo_nov"]
    assert a["statement"] == "no statement" and "2 of its runs have S" in a["why_no_statement"]
    assert a["S"]["apr"][CTL["placebo_nov"][2]] is None                           # listed, with none
    assert d["arms"]["observed_only_nov"]["statement"] == "reads above"           # the other arm is judged on its own
    assert d["slide"]["sentence"].startswith("With no guesses,")


def test_an_official_nov_run_without_s_judges_no_arm_and_the_slide_shows_tables_only():
    d = pc.decide_controls(s_table([60.0, 62.0, None], LOW, LOW))
    for arm in pc.CTRL_ARMS:
        a = d["arms"][arm]
        assert a["statement"] == "no statement" and "an official_nov run has no S" in a["why_no_statement"] and OFF[2] in a["why_no_statement"]
        assert a["S"]["apr"] and a["S"]["hm3d"]
    assert d["slide"] == {"kind": "tables_only", "sentence": None, "judged_arms": [],
                          "text": "No arm was judged: the slide shows the S tables only."}


def test_neither_arm_judged_for_want_of_runs():
    d = pc.decide_controls(s_table(HIGH, LOW[:2], LOW[:1]))
    assert [d["arms"][a]["judged"] for a in pc.CTRL_ARMS] == [False, False]
    assert d["slide"]["kind"] == "tables_only" and d["slide"]["sentence"] is None


def test_an_arm_with_no_run_at_all_and_an_empty_input():
    d = pc.decide_controls(s_table(HIGH, LOW, None))
    assert d["arms"]["observed_only_nov"]["statement"] == "no statement" and d["arms"]["observed_only_nov"]["S"] == {"apr": {}, "hm3d": {}}
    assert d["slide"]["judged_arms"] == ["placebo_nov"]
    d = pc.decide_controls({})
    assert [d["arms"][a]["judged"] for a in pc.CTRL_ARMS] == [False, False] and "official_nov run(s) missing" in d["arms"]["placebo_nov"]["why_no_statement"]
    assert d["slide"]["kind"] == "tables_only"


def test_the_condition_is_read_under_each_reference():
    d = pc.decide_controls(s_table(HIGH, LOW, LOW, plc_h=[40.0, None, None]))
    a = d["arms"]["placebo_nov"]
    assert a["statement"] == "no statement" and a["why_no_statement"].startswith("hm3d:")
    d = pc.decide_controls({"apr": s_table(HIGH, LOW, LOW)["apr"]})                 # no HM3D numbers at all
    assert d["arms"]["placebo_nov"]["statement"] == "no statement" and "hm3d: official_nov run(s) missing" in d["arms"]["placebo_nov"]["why_no_statement"]


def test_a_control_arm_with_four_runs_is_judged_on_those_that_have_s():
    s = s_table(HIGH, LOW, LOW)
    s["apr"]["placebo_nov"]["e9_00853_s42_placebo_115m_relaunch1"] = None
    s["hm3d"]["placebo_nov"]["e9_00853_s42_placebo_115m_relaunch1"] = 99.0       # 4th run with S under HM3D only
    d = pc.decide_controls(s)
    assert d["arms"]["placebo_nov"]["judged"] is True
    assert d["arms"]["placebo_nov"]["per_reference"] == {"apr": pc.SEPARATED, "hm3d": pc.ABOVE_AVG}


def test_the_three_named_official_runs_are_required_not_any_set_of_runs():
    """Item 2: two runs, a renamed run, or an extra run in place of a missing one do not stand for the three."""
    full = s_table(HIGH, LOW, LOW)
    for ref in ("apr", "hm3d"):
        del full[ref]["official_nov"][OFF[1]]                                   # seed 43 missing, two runs left
    d = pc.decide_controls(full)
    for arm in pc.CTRL_ARMS:
        assert d["arms"][arm]["statement"] == "no statement" and OFF[1] in d["arms"][arm]["why_no_statement"]
    assert d["slide"]["kind"] == "tables_only"
    swapped = s_table(HIGH, LOW, LOW)
    for ref in ("apr", "hm3d"):
        swapped[ref]["official_nov"] = {OFF[0]: 70.0, OFF[2]: 74.0, "e8_00853_s43_official_105m_relaunch1": 72.0}
    assert pc.decide_controls(swapped)["arms"]["placebo_nov"]["statement"] == "no statement"
    assert pc.decide_controls({"apr": s_table(HIGH, LOW, LOW)["apr"], "hm3d": {}})["arms"]["placebo_nov"]["statement"] == "no statement"
    one_ref = s_table(HIGH, LOW, LOW)
    del one_ref["hm3d"]["official_nov"][OFF[2]]                                  # missing under one reference only
    d = pc.decide_controls(one_ref)
    assert d["arms"]["placebo_nov"]["statement"] == "no statement" and d["arms"]["placebo_nov"]["why_no_statement"].startswith("hm3d:")
    extra = s_table(HIGH, LOW, LOW)
    extra["apr"]["official_nov"]["e8_00853_s45_official_105m"] = 1.0              # an extra run does not enter the comparison
    assert pc.decide_controls(extra)["arms"]["placebo_nov"]["statement"] == "reads above"
    assert pc.OFFICIAL_NOV_RUNS == ("e8_00853_s42_official_105m", "e8_00853_s43_official_105m", "e8_00853_s44_official_105m")


def test_the_decision_is_pure_and_json_ready():
    s = s_table(HIGH, LOW, LOW)
    before = json.dumps(s, sort_keys=True)
    d = pc.decide_controls(s)
    assert json.dumps(s, sort_keys=True) == before and pc.decide_controls(s) == d
    json.dumps(d)


def test_the_slide_sentences_are_the_amendments():
    text = open(os.path.join(HERE, "..", "live_policy", "PREREGISTRATION_PAPER.md")).read()
    for tmpl in (pc.SLIDE_ABOVE, pc.SLIDE_NOT_ABOVE):
        head, tail = tmpl.split("{what}")
        assert head in text and tail in text
