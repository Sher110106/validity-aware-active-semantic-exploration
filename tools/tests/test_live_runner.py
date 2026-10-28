"""Tests for the live runner's spend and quality gates (no docker needed)."""
import json
import os
import sys

TOOLS = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(TOOLS, "live_policy"))

import live_runner  # noqa: E402


def make_run(root, name, cost=0.0, usage=(), steps=()):
    run = root / name
    (run / "prompts").mkdir(parents=True)
    (run / "prompts" / "_cost_usd").write_text(f"{cost}\n")
    (run / "prompts" / "usage.jsonl").write_text("".join(json.dumps(u) + "\n" for u in usage))
    for i, available in enumerate(steps):
        stage = run / "stages" / str(i)
        stage.mkdir(parents=True)
        tracks = {"0": {"available": available[0]}, "1": {"available": available[1]}}
        (stage / "live_policy.jsonl").write_text(json.dumps({"tracks": tracks}) + "\n")
    return run


def runner(tmp_path, monkeypatch, cap=5.0):
    monkeypatch.setattr(live_runner, "CAMPAIGN", tmp_path)
    return live_runner.Runner("c", 99, cap, tmp_path)


OK = {"status": 200, "provider": "DeepInfra", "model": "deepseek/deepseek-v4.1-flash-1017", "id": "a"}


def test_provider_gate_flags_any_other_provider_or_model(tmp_path, monkeypatch):
    r = runner(tmp_path, monkeypatch)
    good = make_run(tmp_path, "good", usage=[OK, {**OK, "status": 429, "provider": None}])
    bad = make_run(tmp_path, "bad", usage=[OK, {**OK, "provider": "Together"}])
    old = make_run(tmp_path, "old", usage=[{**OK, "model": "deepseek/deepseek-v4.1-flash"}])
    empty = make_run(tmp_path, "empty", usage=[OK, {**OK, "provider": None, "model": None}])  # 200 error body
    assert r.provider_violations(good) == []
    assert r.provider_violations(empty) == []
    assert len(r.provider_violations(bad)) == 1
    assert len(r.provider_violations(old)) == 1


def test_dropped_member_gate(tmp_path, monkeypatch):
    r = runner(tmp_path, monkeypatch)
    fine = make_run(tmp_path, "fine", steps=[(4, 4), (4, 3), (3, 2), (4, 4), (3, 3)])  # 7/40 dropped
    early = make_run(tmp_path, "early", steps=[(1, 1), (2, 2), (1, 1), (0, 1)])  # too few steps to judge
    lossy = make_run(tmp_path, "lossy", steps=[(2, 1), (1, 2), (2, 2), (1, 1), (2, 1)])  # 25/40 dropped
    one_track = make_run(tmp_path, "one_track", steps=[(4, 4)] * 5)
    for f in (one_track / "stages").glob("*/live_policy.jsonl"):
        f.write_text(json.dumps({"tracks": {"0": {"available": 4}}}) + "\n")  # a step with one tracked graph
    assert not r._dropped_gate(fine)
    assert not r._dropped_gate(early)
    assert r._dropped_gate(lossy)
    assert r.member_stats(one_track) == (20, 20) and not r._dropped_gate(one_track)


def test_campaign_committed_counts_unspent_caps_of_active_runs(tmp_path, monkeypatch):
    r = runner(tmp_path, monkeypatch)
    make_run(tmp_path, "done", cost=0.7)
    make_run(tmp_path, "running", cost=0.2)
    (tmp_path / ".active_running").write_text(json.dumps({"name": "running", "max_cost_usd": 1.5}))
    assert abs(r.campaign_committed() - (0.7 + 0.2 + 1.3)) < 1e-9


def test_run_one_refuses_paid_run_over_campaign_cap(tmp_path, monkeypatch):
    r = runner(tmp_path, monkeypatch, cap=2.0)
    make_run(tmp_path, "done", cost=0.9)
    spec = {"name": "next", "scene": "00853", "seed": 42, "policy": "official", "target_m": 60, "max_cost_usd": 1.5}
    rec = r.run_one(spec, tmp_path / "pristine.yaml")
    assert rec["outcome"] == "skipped_campaign_cap"
    assert not (tmp_path / ".active_next").exists()


def test_failed_process_check_is_not_read_as_exited(tmp_path, monkeypatch):
    import subprocess

    r = runner(tmp_path, monkeypatch)
    results = iter([124, 1, 1, 0, 1, 1, 1])
    outputs = {0: "123\n", 1: "", 124: ""}

    def fake_dexec(*args, **kwargs):
        code = next(results)
        return subprocess.CompletedProcess(args, code, outputs[code], "")

    monkeypatch.setattr(r, "dexec", fake_dexec)
    monkeypatch.setattr(live_runner.time, "sleep", lambda s: None)
    assert r.pids("x") is None  # docker exec timed out
    assert not r.confirmed_gone("x")  # empty, empty, then the process shows up
    assert r.confirmed_gone("x")  # three empty checks in a row


def test_exclude_writes_marker_in_campaign_dir(tmp_path, monkeypatch):
    r = runner(tmp_path, monkeypatch)
    run = make_run(tmp_path, "x")
    run.chmod(0o555)  # run dirs are root-owned on the host
    try:
        r.exclude(run, "provider_violation", [])
    finally:
        run.chmod(0o755)
    assert json.loads((tmp_path / "EXCLUDED_x.json").read_text())["reason"] == "provider_violation"
