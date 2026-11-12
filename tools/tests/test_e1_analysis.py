"""Tests for tools/live_policy/e1_analysis.py name parsing and cell rules."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(__file__)
SCRIPT = os.path.join(HERE, "..", "live_policy", "e1_analysis.py")
sys.path.insert(0, os.path.join(HERE, "..", "live_policy"))
import e1_analysis  # noqa: E402


def test_rerun_names_parse_to_the_same_cell():
    assert e1_analysis.parse("/w/e1_00853_s44_official_60m_rerun1") == ("00853", 44, "official")
    assert e1_analysis.parse("e1_00871_s43_placebo_60m_rerun1") == ("00871", 43, "placebo")
    assert e1_analysis.parse("e3_00871_s42_oracle_visible_60m") == ("00871", 42, "oracle_visible")
    assert e1_analysis.parse("e2_00853_s43_filter_only_60m") == ("00853", 43, "filter_only")
    assert e1_analysis.parse("dryrun_oracle_00871_s42_10m") is None


def run(tmp_path, runs, *extra):
    p = tmp_path / "scores.json"
    p.write_text(json.dumps(runs))
    r = subprocess.run([sys.executable, SCRIPT, str(p), *extra], capture_output=True, text=True)
    return r.returncode, (json.loads(r.stdout) if r.returncode == 0 else r.stderr)


def cell(name, auc, path=60.0):
    return {"run_dir": f"/w/{name}", "final_path_m": path, "hm3d_auc_af_f1_to_60m": auc}


def full(reruns=True):
    runs = []
    for scene in ("00853", "00871"):
        for seed in (42, 43, 44):
            runs.append(cell(f"e1_{scene}_s{seed}_official_60m", 0.14 + seed * 1e-4))
            runs.append(cell(f"e1_{scene}_s{seed}_placebo_60m", 0.13 + seed * 2e-4))
    if reruns:
        runs[-1] = cell("e1_00871_s44_placebo_60m", 0.0, path=46.8)
        runs.append(cell("e1_00871_s44_placebo_60m_rerun1", 0.135))
    return runs


def test_full_design_counts_the_rerun_and_has_400_relabelings(tmp_path):
    code, out = run(tmp_path, full())
    assert code == 0
    assert out["n_relabelings"] == 400
    assert "e1_00871_s44_placebo_60m_rerun1" in out["counted_runs"]
    assert {"run": "e1_00871_s44_placebo_60m", "reason": "stopped at 46.8 m"} in out["dropped"]
    lo, hi = out["permutation_95ci"]
    assert lo <= out["statistic"] <= hi


def test_two_counted_runs_in_one_cell_stop_the_analysis(tmp_path):
    runs = full(reruns=False) + [cell("e1_00853_s42_official_60m_rerun1", 0.15)]
    code, err = run(tmp_path, runs)
    assert code != 0 and "two counted runs" in err


def test_unparsed_and_unregistered_seeds_are_listed(tmp_path):
    runs = full(reruns=False) + [cell("e1_00853_s45_official_60m", 0.2), cell("e1_bad_name", 0.1)]
    code, out = run(tmp_path, runs)
    reasons = {d["run"]: d["reason"] for d in out["dropped"]}
    assert reasons["e1_00853_s45_official_60m"] == "seed 45 not in --seeds"
    assert reasons["e1_bad_name"] == "unparsed name"


def test_scene_without_arm_a_is_left_out_of_every_statistic(tmp_path):
    runs = [cell(f"e3_00871_s{s}_oracle_visible_60m", 0.15 + s * 1e-4) for s in (42, 43)]
    runs += [cell(f"e1_{scene}_s{s}_placebo_60m", 0.13 + s * 2e-4) for scene in ("00853", "00871") for s in (42, 43, 44)]
    code, out = run(tmp_path, runs, "--a", "oracle_visible", "--b", "placebo")
    assert code == 0
    assert out["n_relabelings"] == 10
    one_scene = [r for r in runs if "00871" in r["run_dir"]]
    code1, out1 = run(tmp_path, one_scene, "--a", "oracle_visible", "--b", "placebo")
    for k in ("statistic", "blocked_permutation_p", "n_relabelings", "mde_alpha05_power80", "bootstrap_95ci"):
        assert out[k] == out1[k], k
