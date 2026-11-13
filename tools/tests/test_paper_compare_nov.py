"""The November ASP row (PREREGISTRATION_PAPER.md, Amendment 3 and its Note), in paper_compare.py:
the arm `official_nov`, its name pattern, its readouts, the footnote, and the proof that nothing
changes when no e8 run exists (golden hashes taken from the code as it stood before the arm)."""
import hashlib
import json
import os
import sys

import pytest
import yaml

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "live_policy"))
import paper_compare as pc  # noqa: E402


def obj(name, x, y=0.0, z=0.0):
    return {"name": name, "position": f"[{x}, {y}, {z}]", "node_type": "object"}


def write_graph(path, nodes):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"id": i, **n} for i, n in enumerate(nodes)]
    path.write_text(yaml.safe_dump({"nodes": rows, "edges": []}))
    return path


def make_stage(run, n, nav=None, g0=None, g1=None):
    d = run / "stages" / str(n)
    d.mkdir(parents=True, exist_ok=True)
    if nav is not None:
        (d / "navigation_stats.json").write_text(json.dumps(
            {"total_path_length_meters": nav[0], "total_navigation_time_seconds": nav[1]}))
    for gi, nodes in ((0, g0), (1, g1)):
        if nodes is not None:
            write_graph(d / f"habitat_scene_graph_original_graph{gi}.yaml", nodes)


REF_NODES = [obj("bed", 0.0), obj("lamp", 1.0)]
HIT = [obj("bed", 0.1), obj("lamp", 1.1)]       # F1 1.0
HALF = [obj("bed", 0.1), obj("sofa", 5.0)]      # F1 0.5
NOV = "e8_00853_s{}_official_105m"


# --- the fixture used for the golden hashes ------------------------------------------------

def build_golden_fixture(tmp):
    """A small campaign copy with October official runs, an e4 run, a frontier-end run and a
    tour reference. It holds no e8 run."""
    import csv
    root = tmp / "root"
    camp = root / "runs" / "live_campaign"
    write_graph(camp / "hm3d_refs_work" / "00853_hm3d_reference.yaml", REF_NODES)
    rows = []
    for seed, g in ((42, HIT), (43, HALF)):
        name = f"e1_00853_s{seed}_official_60m"
        run = camp / name
        make_stage(run, 0, nav=(0.0, 0.0), g0=HALF, g1=HALF)
        make_stage(run, 1, nav=(20.0, 130.0), g0=g, g1=g)
        make_stage(run, 2, nav=(60.0, 400.0), g0=g, g1=g)
        rows.append({"run": name, "arm": "official", "scene": "00853", "seed": str(seed), "status": "counted"})
    table = tmp / "run_table.csv"
    with open(table, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    e4 = root / "runs" / "frontier_seeds" / "e4_00853_s42_frontier_60m"
    make_stage(e4, 0, nav=(0.0, 0.0), g0=HALF, g1=HALF)
    make_stage(e4, 1, nav=(60.0, 380.0), g0=HIT, g1=HALF)
    fe = tmp / "e7_00853_s42_frontier_end"
    make_stage(fe, 0, nav=(0.0, 0.0), g0=HALF, g1=HALF)
    make_stage(fe, 1, nav=(50.0, 300.0), g0=HIT, g1=HALF)
    make_stage(fe, 2, nav=(90.0, 640.0), g0=HIT, g1=HIT)
    apr = tmp / "apr_00853_a"
    write_graph(apr / "stages" / "3" / "habitat_scene_graph_original_graph0.yaml", REF_NODES)
    ged = tmp / "ged.json"
    ged.write_text(json.dumps({"runs": [{"run_dir": "/workspace/runs/x/e7_00853_s42_frontier_end", "scene": "00853",
                                         "stages": [{"stage": 1, "ged_apr": 120.0, "ged_hm3d": 200.0},
                                                    {"stage": 2, "ged_apr": 90.0, "ged_hm3d": 150.0}]}]}))
    return root, table, fe, apr, ged


def run_golden(tmp, extra=()):
    root, table, fe, apr, ged = build_golden_fixture(tmp)
    out = tmp / "out"
    argv = ["--root", str(root), "--run-table", str(table), "--no-fallback", "--add-run", f"frontier_end=00853={fe}",
            "--apr", f"00853={apr}", "--budget", "00853=632.1750566959381", "--budget", "00871=809.084",
            "--ged-json", str(ged), "--out-dir", str(out), *extra]
    assert pc.main(argv) == 0
    norm = lambda p: (out / p).read_text().replace(str(tmp), "<TMP>")
    return norm("paper_compare.json"), norm("paper_compare.md")


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


# Taken from paper_compare.py as it stood before the November arm was added.
GOLDEN_JSON = "94c62d765bf22da722aa1b185189167797b03a14dc032d440d710d1b949348f1"
GOLDEN_MD = "ea7436d1327eed594cb00a15f9297cb8fe2de485cdcd0b2a3dc01b5f98c80d0b"


def test_golden_hashes_for_the_pre_november_code(tmp_path):
    js, md = run_golden(tmp_path)
    print("GOLDEN_JSON", sha(js))
    print("GOLDEN_MD", sha(md))
    assert sha(js) == GOLDEN_JSON and sha(md) == GOLDEN_MD


# --- the arm and its name pattern -----------------------------------------------------------

@pytest.mark.parametrize("name", ["e8_00853_s42_official_105m", "e8_00853_s43_official_105m", "e8_00853_s44_official_105m",
                                  "e8_00853_s42_official_105m_relaunch1", "e8_00853_s44_official_105m_relaunch1"])
def test_pattern_takes_the_three_seeds_with_or_without_relaunch1(name):
    assert pc.NOV_RE.match(name)


@pytest.mark.parametrize("name", ["dryrun_e8_00853_s42_official_5m", "e8_00853_s42_official_5m", "e8_00853_s45_official_105m",
                                  "e8_00871_s42_official_105m", "e8_00853_s42_official_105m_relaunch2",
                                  "e8_00853_s42_official_105m_FAILED_ATTEMPT1", "xe8_00853_s42_official_105m",
                                  "e8_00853_s42_official_105m_relaunch1x", "e1_00853_s42_official_60m", "e8_00853_s42_placebo_105m"])
def test_pattern_is_anchored_and_refuses_everything_else(name):
    assert not pc.NOV_RE.match(name)


def test_arm_sits_right_after_official_and_has_the_papers_asp_column():
    assert pc.ARM_ORDER.index("official_nov") == pc.ARM_ORDER.index("official") + 1
    assert pc.paper_method("official_nov") == "Semantic (Ours)" == pc.paper_method("official")
    assert pc.ARM_LABELS["official_nov"] == "ASP + DeepSeek, November"
    assert "official_nov" not in pc.COUNTED_ARMS          # October's counted set does not take it


def _campaign(tmp, names):
    for n in names:
        make_stage(tmp / "runs" / "live_campaign" / n, 0, nav=(0.0, 0.0), g0=HALF, g1=HALF)


def _empty_table(tmp):
    t = tmp / "t.csv"
    t.write_text("run,arm,scene,seed,status\n")
    return t






def test_run_table_row_for_an_e8_name_cannot_enter_as_october_official(tmp_path):
    t = tmp_path / "t.csv"
    t.write_text("run,arm,scene,seed,status\n" + f"{NOV.format(42)},official,00853,42,counted\n")
    with pytest.raises(ValueError, match="official_nov"):
        pc.default_runs(tmp_path, t)


# --- no pooling -------------------------------------------------------------------------------

def _rec(arm, name, seed, f1_10, f1_100):
    def entry(f):
        return {"t_s": 1.0, "stage": 1, "stage_time_s": 1.0, "f1": f, "f1_runmax": f, "precision": f, "recall": f,
                "ged": None, "null_reason": None if f is not None else "run_ended_before_t"}
    ro = {"hm3d": {"B": {"10": entry(f1_10), "50": entry(f1_10), "100": entry(f1_100)}}}
    return {"run": name, "arm": arm, "scene": "00853", "seed": seed, "readouts": ro}


def test_official_and_official_nov_with_the_same_seed_stay_in_separate_rows_with_their_own_n():
    recs = [_rec("official", "e1_00853_s42_official_60m", 42, 0.2, None),
            _rec("official", "e1_00853_s43_official_60m", 43, 0.4, None),
            _rec("official_nov", NOV.format(42), 42, 0.6, 0.9)]
    cells = pc.aggregate(recs)
    off = [c for c in cells if c["arm"] == "official" and c["fraction"] == "10" and c["variant"] == "B"][0]
    nov = [c for c in cells if c["arm"] == "official_nov" and c["fraction"] == "10" and c["variant"] == "B"][0]
    assert off["n_runs"] == 2 and off["stage_value_x100"]["mean"] == pytest.approx(30.0)
    assert nov["n_runs"] == 1 and nov["stage_value_x100"]["mean"] == pytest.approx(60.0)
    nov100 = [c for c in cells if c["arm"] == "official_nov" and c["fraction"] == "100" and c["variant"] == "B"][0]
    off100 = [c for c in cells if c["arm"] == "official" and c["fraction"] == "100" and c["variant"] == "B"][0]
    assert nov100["stage_value_x100"]["n"] == 1 and off100["stage_value_x100"]["n"] == 0
    assert nov["paper_method"] == off["paper_method"] == "Semantic (Ours)" and nov["paper_f1_x100"] == off["paper_f1_x100"]


def test_aggregate_refuses_a_name_in_the_wrong_arm():
    with pytest.raises(ValueError, match="official_nov"):
        pc.aggregate([_rec("official", NOV.format(42), 42, 0.2, None)])
    with pytest.raises(ValueError, match="official_nov"):
        pc.aggregate([_rec("official_nov", "e1_00853_s42_official_60m", 42, 0.2, None)])


# --- readouts of the November row ---------------------------------------------------------------

B853 = 632.1750566959381


def _nov_run(tmp, name, end_s, g1_last=True):
    run = tmp / name
    make_stage(run, 0, nav=(0.0, 0.0), g0=HALF, g1=HALF)
    make_stage(run, 1, nav=(30.0, 200.0), g0=HIT, g1=HALF)
    make_stage(run, 2, nav=(60.0, 400.0), g0=HIT, g1=HIT)
    make_stage(run, 3, nav=(105.0, end_s), g0=HIT, g1=HIT if g1_last else None)
    return run


def _score(tmp, run, arm="official_nov", budget=B853):
    p = write_graph(tmp / "ref.yaml", REF_NODES)
    spec = pc.RunSpec(run.name, arm, "00853", run, 42)
    return pc.score_run(spec, {"hm3d": {"00853": pc.load_reference(p)}}, {"00853": budget}, [])


def test_a_run_that_reached_b_has_a_100_value(tmp_path):
    rec = _score(tmp_path, _nov_run(tmp_path, NOV.format(42), 700.0))
    ro = rec["readouts"]["hm3d"]["B"]
    assert ro["100"]["f1"] == 1.0 and ro["100"]["stage"] == 2   # the last stage at or before B (400 s), not the one after
    assert ro["10"]["f1"] is not None and ro["50"]["f1"] is not None
    assert rec["readouts"]["hm3d"]["0.8B"]["100"]["f1"] == 1.0


def test_a_run_one_short_of_b_keeps_10_and_50_and_has_no_100(tmp_path):
    rec = _score(tmp_path, _nov_run(tmp_path, NOV.format(42), 600.0))
    ro = rec["readouts"]["hm3d"]["B"]
    assert ro["100"]["f1"] is None and ro["100"]["null_reason"] == "run_ended_before_t"
    assert ro["10"]["f1"] is not None and ro["50"]["f1"] is not None


def test_the_last_stage_without_graph1_does_not_count_as_reaching_b(tmp_path):
    """A3.2: the stage that reaches B must hold stats and both graph files."""
    run = _nov_run(tmp_path, NOV.format(42), 700.0, g1_last=False)
    rec = _score(tmp_path, run)
    assert rec["readouts"]["hm3d"]["B"]["100"]["f1"] is None
    assert rec["reached_end_s"] == 400.0
    # an October-style arm on the same files is scored as before: one graph is enough
    assert _score(tmp_path, run, arm="official")["readouts"]["hm3d"]["B"]["100"]["f1"] == 1.0
    assert "reached_end_s" not in _score(tmp_path, run, arm="official")


def test_b_times_1_2_is_empty_when_the_run_is_too_short(tmp_path):
    rec = _score(tmp_path, _nov_run(tmp_path, NOV.format(42), 700.0))
    ro = rec["readouts"]["hm3d"]["1.2B"]
    assert ro["100"]["f1"] is None and ro["50"]["f1"] is not None
    cells = [c for c in pc.aggregate([rec]) if c["variant"] == "1.2B" and c["fraction"] == "100"]
    assert cells[0]["stage_value_x100"] == {"mean": None, "min": None, "max": None, "n": 0}




def test_explicit_run_with_the_wrong_name_is_refused(tmp_path):
    run = _nov_run(tmp_path, "e1_00853_s42_official_60m", 700.0)
    with pytest.raises(SystemExit):
        pc.main(["--no-default-runs", "--no-fallback", "--add-run", f"official_nov=00853={run}", "--budget", "00853=632",
                 "--out-dir", str(tmp_path / "o")])
    nov = _nov_run(tmp_path, NOV.format(43), 700.0)
    with pytest.raises(SystemExit):
        pc.main(["--no-default-runs", "--no-fallback", "--add-run", f"official=00853={nov}", "--budget", "00853=632",
                 "--out-dir", str(tmp_path / "o")])




# --- the footnote -----------------------------------------------------------------------------

OLD_FOOT = ("A run has no value at a t past its last stage, so its 100% readout is null, "
            "and a 50% readout is null when the run ended sooner.")


def test_footnote_is_unchanged_without_november_runs(tmp_path):
    _, md = run_golden(tmp_path)
    assert "- ASP runs stop at 60 m of path, which took " in md and OLD_FOOT in md
    assert "105 m" not in md and "October" not in md




# =====================================================================================
# Review round: e8 runs enter only through --add-run
# =====================================================================================

import re  # noqa: E402


def _argv(tmp, root, table, apr, ged, add=(), budget="632.1750566959381", extra=()):
    argv = ["--root", str(root), "--run-table", str(table), "--no-fallback", "--apr", f"00853={apr}",
            "--budget", f"00853={budget}", "--out-dir", str(tmp / "out"), *extra]
    for arm, path in add:
        argv += ["--add-run", f"{arm}=00853={path}"]
    return argv


def test_default_runs_never_pick_an_e8_run(tmp_path):
    _campaign(tmp_path, [NOV.format(42), NOV.format(43) + "_relaunch1", "dryrun_e8_00853_s42_official_5m"])
    for nov in (True, False):
        specs = pc.default_runs(tmp_path, _empty_table(tmp_path), nov=nov)
        assert not [s for s in specs if s.arm == pc.NOV_ARM or pc.NOV_RE.match(s.name)]


def test_a_root_full_of_e8_folders_scores_none_of_them_and_names_them(tmp_path, capsys):
    """The reviewer's root: s42 with an out-of-memory line, s43 still open, a relaunch, s44 just short of B."""
    root, table, fe, apr, ged = build_golden_fixture(tmp_path)
    camp = root / "runs" / "live_campaign"
    for name, end in ((NOV.format(42), 700.0), (NOV.format(43), 700.0), (NOV.format(42) + "_relaunch1", 700.0), (NOV.format(44), 632.15)):
        _nov_run(camp, name, end)
    (camp / NOV.format(42) / "logs").mkdir(parents=True)
    (camp / NOV.format(42) / "logs" / "roslaunch.log").write_text("CUDA out of memory\n")
    (camp / f"EXCLUDED_{NOV.format(42)}.json").write_text("{}")
    assert pc.main(_argv(tmp_path, root, table, apr, ged)) == 0
    res = json.loads((tmp_path / "out" / "paper_compare.json").read_text())
    assert not [r for r in res["runs"] if r["arm"] == "official_nov"] and not [c for c in res["cells"] if c["arm"] == "official_nov"]
    err = capsys.readouterr().err
    line = [l for l in err.splitlines() if "not scored here" in l]
    assert len(line) == 1 and "November runs are assessed by rescore_paper.py" in line[0]
    for n in (NOV.format(42), NOV.format(43), NOV.format(42) + "_relaunch1", NOV.format(44)):
        assert n in line[0]


def test_no_line_is_printed_when_the_root_holds_no_e8_run(tmp_path, capsys):
    root, table, fe, apr, ged = build_golden_fixture(tmp_path)
    assert pc.main(_argv(tmp_path, root, table, apr, ged)) == 0
    assert "not scored here" not in capsys.readouterr().err


def test_no_nov_default_flag_is_kept_as_a_no_op(tmp_path):
    root, table, fe, apr, ged = build_golden_fixture(tmp_path)
    assert pc.main(_argv(tmp_path, root, table, apr, ged, extra=["--no-nov-default"])) == 0


def test_cli_scores_three_added_runs_into_one_labelled_row_and_leaves_october_alone(tmp_path):
    root, table, fe, apr, ged = build_golden_fixture(tmp_path)
    add = []
    for seed, end in ((42, 700.0), (43, 650.0), (44, 600.0)):
        add.append(("official_nov", _nov_run(root / "runs" / "live_campaign", NOV.format(seed), end)))
    assert pc.main(_argv(tmp_path, root, table, apr, ged, add=add + [("frontier_end", fe)])) == 0
    res = json.loads((tmp_path / "out" / "paper_compare.json").read_text())
    pick = lambda arm, f: [c for c in res["cells"] if c["arm"] == arm and c["reference"] == "hm3d" and c["variant"] == "B" and c["fraction"] == f][0]
    assert pick("official", "10")["n_runs"] == 2 and pick("official_nov", "10")["n_runs"] == 3
    assert pick("official_nov", "100")["stage_value_x100"]["n"] == 2
    md = (tmp_path / "out" / "paper_compare.md").read_text()
    assert "| 00853 | ASP + DeepSeek, November | Ours(ASP) |" in md and "official_nov" not in md


def test_footnote_names_both_stops_when_a_november_run_is_scored(tmp_path):
    root, table, fe, apr, ged = build_golden_fixture(tmp_path)
    run = _nov_run(root / "runs" / "live_campaign", NOV.format(42), 700.0)
    assert pc.main(_argv(tmp_path, root, table, apr, ged, add=[("official_nov", run)])) == 0
    md = (tmp_path / "out" / "paper_compare.md").read_text()
    assert "- ASP runs stop at 60 m of path" not in md
    assert "October's ASP runs stop at 60 m of path" in md and "ran to about 105 m of path" in md
    assert "a November run has a 100% value only if it reached B" in md


# --- one folder per seed ------------------------------------------------------------------------

def test_a_relaunch_beside_a_started_original_is_an_error_that_names_both(tmp_path):
    camp = tmp_path / "c"
    a, b = _nov_run(camp, NOV.format(42), 700.0), _nov_run(camp, NOV.format(42) + "_relaunch1", 700.0)
    with pytest.raises(ValueError) as e:
        pc.check_nov_pairs([a, b])
    assert a.name in str(e.value) and b.name in str(e.value)
    root, table, fe, apr, ged = build_golden_fixture(tmp_path)
    with pytest.raises(SystemExit) as ex:
        pc.main(_argv(tmp_path, root, table, apr, ged, add=[("official_nov", a), ("official_nov", b)]))
    assert NOV.format(42) in str(ex.value) and "_relaunch1" in str(ex.value)


def test_a_relaunch_replaces_an_original_that_never_started(tmp_path):
    camp = tmp_path / "c"
    first = camp / NOV.format(42)
    (first / "config").mkdir(parents=True)                      # launched, wrote no stage
    relaunch = _nov_run(camp, NOV.format(42) + "_relaunch1", 700.0)
    assert pc.check_nov_pairs([first, relaunch]) == [relaunch]
    other = _nov_run(camp, NOV.format(43), 700.0)
    assert pc.check_nov_pairs([other, relaunch]) == [other, relaunch]       # different seeds: nothing to do


def test_the_same_folder_twice_is_refused(tmp_path):
    a = _nov_run(tmp_path, NOV.format(42), 700.0)
    with pytest.raises(ValueError):
        pc.check_nov_pairs([a, a])


# --- strict reach ---------------------------------------------------------------------------------

def test_a_run_a_millisecond_short_of_b_has_no_100_value(tmp_path):
    rec = _score(tmp_path, _nov_run(tmp_path, NOV.format(42), B853 - 0.0009))
    assert rec["readouts"]["hm3d"]["B"]["100"]["f1"] is None and rec["reached_b"] is False
    ok = _score(tmp_path, _nov_run(tmp_path, NOV.format(43), B853), budget=B853)
    assert ok["readouts"]["hm3d"]["B"]["100"]["f1"] is not None and ok["reached_b"] is True
    # October's arm keeps its tolerance
    assert _score(tmp_path, _nov_run(tmp_path, "e1_x", B853 - 0.0009), arm="official")["readouts"]["hm3d"]["B"]["100"]["f1"] is not None


# --- names and scene -------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["e8_00853_s42_official_105m_FAILED", "dryrun_e8_00853_s42_official_5m", "e8_00853_s45_official_105m",
                                  "e8_00871_s42_official_105m", NOV.format(42)])
def test_no_e8_name_enters_the_run_table_in_any_arm(tmp_path, name):
    t = tmp_path / "t.csv"
    t.write_text("run,arm,scene,seed,status\n" + f"{name},official,00853,42,counted\n")
    with pytest.raises(ValueError):
        pc.default_runs(tmp_path, t)


@pytest.mark.parametrize("arm,name,scene", [("official", "dryrun_e8_00853_s42_official_5m", "00853"),
                                            ("official", "e8_00853_s42_official_105m_FAILED", "00853"),
                                            ("filter_only", "e8_00853_s42_official_105m", "00853"),
                                            ("official_nov", "e8_00853_s42_official_105m", "00871"),
                                            ("official_nov", "e8_00853_s45_official_105m", "00853"),
                                            ("official_nov", "dryrun_e8_00853_s42_official_5m", "00853"),
                                            ("official_nov", "e1_00853_s42_official_60m", "00853")])
def test_add_run_refuses_wrong_names_and_the_wrong_scene(tmp_path, arm, name, scene):
    run = _nov_run(tmp_path, name, 700.0)
    with pytest.raises(SystemExit):
        pc.main(["--no-default-runs", "--no-fallback", "--add-run", f"{arm}={scene}={run}", "--budget", f"{scene}=632",
                 "--out-dir", str(tmp_path / "o")])


def test_aggregate_refuses_the_wrong_scene_and_the_wider_name_family():
    bad = _rec("official_nov", NOV.format(42), 42, 0.2, None)
    bad["scene"] = "00871"
    with pytest.raises(ValueError):
        pc.aggregate([bad])
    with pytest.raises(ValueError):
        pc.aggregate([_rec("official", "dryrun_e8_00853_s42_official_5m", 42, 0.2, None)])
