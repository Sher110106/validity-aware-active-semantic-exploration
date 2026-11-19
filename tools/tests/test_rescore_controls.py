"""The host side of Amendment 5 in rescore_paper.py, tested with made-up run folders, made-up host output and a fake rsync:
the listing and the rule for a run that is still running (the controls have no `.active_` marker), the copy list and its
checks, the assessment of A5.3 (and its agreement with assess_e8), the relaunch rule, the pinned S of official_nov, the block
for the summary, the NOTES section, and the proof that without an e9 folder the filed outputs do not move."""
import copy
import json
import os
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "live_policy", "host"))
sys.path.insert(1, os.path.join(HERE, "..", "live_policy"))
sys.path.insert(2, HERE)
import equal_path_check as ep  # noqa: E402
import paper_compare as pc  # noqa: E402
import rescore_paper as rp  # noqa: E402
import test_rescore_paper as trp  # noqa: E402  (its fixtures for e8 runs, summaries and the fake rsync)
from test_paper_compare_controls import B853, HALF, HIT, OBS, PLC, REF_NODES, make_run, obj, write_graph  # noqa: E402

E8 = "e8_00853_s{}_official_105m"
PTS = [(0, 0.0, HALF), (30, 200.0, HALF), (50, 330.0, HIT), (60, 400.0, HIT), (80, 520.0, HIT), (100, 640.0, HIT), (115, 700.0, HIT)]
PTS_90 = PTS[:5] + [(90, 580.0, HIT)]
MISS = [obj("sofa", 9.0)]                                      # F1 0 against REF_NODES
PTS_MISS = [(m, t, MISS) for m, t, _ in PTS]


@pytest.fixture
def unpinned(monkeypatch):
    """The made-up official_nov runs of these tests are not the filed ones; the pinned check has its own tests."""
    monkeypatch.setattr(rp, "check_pinned_official_s", lambda s: None)


# --- what the host call prints ------------------------------------------------------------------------------------

def e9_text(names=(), ended=(), runner="none", unit="none", outcomes=None, status=None, noise=()):
    """The output of fetch_e9_listing's ssh call: names, queue log, runner check, queue-unit check, recorded outcomes."""
    rc = {"none": "RC 1", "alive": "RC 0", "unknown": "RC 2"}[runner]
    units = {"none": "UNITS_OK\n\n", "alive": "UNITS_OK\ne9-queue-20261119T1200.scope loaded active running e9 queue\n",
             "unknown": "UNITS_UNKNOWN\n"}[unit]
    log = "".join(f"2026-11-19 12:00:00 {n}: runner ended (exit 0); stage folders 5; ok\n" for n in ended)
    log += "2026-11-19 11:00:00 e9_00853_s42_placebo_115m: runner started (pid 1)\n"
    out = "".join(f"runner_{n}.out:2026-11-19T12:00:00+05:30 [asp-noetic] finished {n}: {o}\n" for n, o in (outcomes or {}).items())
    out += "".join(f"status_asp-noetic.{n}.json:      \"outcome\": \"{o}\",\n" for n, o in (status or {}).items())
    return ("\n".join(list(names) + list(noise)) + "\n=====QUEUELOG=====\n" + log + "=====RUNNER_RC=====\n" + rc +
            "\n=====UNITS=====\n" + units + "=====OUTCOMES=====\n" + out)


def final_text(names, **kw):
    """Every run finished: nobody alive."""
    return e9_text(names, **kw)


# --- the listing and the rule for a run that is still running -----------------------------------------------------

NAMES = [PLC.format(42), OBS.format(42), OBS.format(43) + "_relaunch1"]
NOISE = ["e1_00853_s42_placebo_60m", "dryrun_e9_00853_s42_placebo_5m", "dryrun_e9_00853_s42_observed_only_5m", "e9_00853_s45_placebo_115m",
         "e9_00853_s42_placebo_115m_relaunch2", "e9_00853_s42_placebo_5m", "e9_00871_s42_placebo_115m", E8.format(42),
         "dryrun_e8_00853_s42_official_5m", ".active_" + E8.format(43), "queue_e9_00853_s42_placebo_115m.json", "e9_queue.log",
         "runner_e9_00853_s42_placebo_115m.out"]


def test_the_e9_listing_picks_by_the_anchored_patterns_and_never_a_dry_run():
    l = rp.parse_e9_listing(e9_text(NAMES, noise=NOISE, runner="alive", ended=[PLC.format(42)]))
    assert l["runs"] == sorted(NAMES)


def test_a_live_run_with_no_marker_is_still_running_and_is_not_copied():
    """The runner writes .active_<name> only for runs that call an LLM: here there is no marker of any kind."""
    text = e9_text(NAMES, runner="alive", ended=[PLC.format(42)])
    assert ".active_" not in text
    l = rp.parse_e9_listing(text)
    assert l["active"] == sorted([OBS.format(42), OBS.format(43) + "_relaunch1"]) and l["final"] is False
    assert l["queue_ended"] == [PLC.format(42)] and l["runner_alive"] is True and l["queue_unit_alive"] is False
    assert rp.e8_copy_folders(l) == ["live_campaign/" + PLC.format(42)]


def test_a_stray_active_marker_of_a_control_run_decides_nothing():
    """Markers are not read for the controls: a finished run with a leftover marker is finished, a live one without is not."""
    names = NAMES + [".active_" + PLC.format(42)]
    l = rp.parse_e9_listing(e9_text(names, ended=[PLC.format(42)], runner="alive"))
    assert PLC.format(42) not in l["active"] and OBS.format(42) in l["active"]


def test_a_run_is_finished_if_the_queue_log_says_the_runner_ended_even_while_another_job_runs():
    l = rp.parse_e9_listing(e9_text(NAMES, runner="alive", unit="alive", ended=NAMES))
    assert l["active"] == [] and l["final"] is False                  # all three have ended, but the queue is alive: not final
    assert rp.e8_copy_folders(l) == sorted("live_campaign/" + n for n in NAMES)


def test_with_neither_a_runner_nor_a_queue_unit_alive_every_run_is_finished_and_the_reading_is_final():
    l = rp.parse_e9_listing(final_text(NAMES))
    assert l["active"] == [] and l["final"] is True and l["runner_alive"] is False and l["queue_unit_alive"] is False


@pytest.mark.parametrize("runner,unit,active", [("alive", "none", True), ("none", "alive", True), ("alive", "alive", True),
                                                ("unknown", "none", True), ("none", "unknown", True), ("unknown", "unknown", True),
                                                ("none", "none", False)])
def test_a_run_not_in_the_log_is_finished_only_if_no_runner_and_no_queue_unit_is_alive_and_both_checks_worked(runner, unit, active):
    l = rp.parse_e9_listing(e9_text([PLC.format(42)], runner=runner, unit=unit))
    assert (l["active"] == [PLC.format(42)]) is active and l["final"] is (not active)
    assert rp.e8_copy_folders(l) == ([] if active else ["live_campaign/" + PLC.format(42)])


def test_a_missing_section_or_a_failed_check_counts_as_alive():
    l = rp.parse_e9_listing("\n".join(NAMES))                           # an old-style text: no sections at all
    assert l["active"] == sorted(NAMES) and l["final"] is False and l["runner_alive"] is None and l["queue_unit_alive"] is None
    l = rp.parse_e9_listing(e9_text(NAMES).replace("RC 1", "RC 255"))
    assert l["runner_alive"] is None and l["active"] == sorted(NAMES)
    assert rp.parse_e9_listing("")["runs"] == []


def test_the_log_line_must_name_the_run_and_say_runner_ended():
    text = e9_text([PLC.format(42), OBS.format(42)], runner="alive").replace(
        "=====RUNNER_RC=====", f"2026-11-19 12:30:00 {OBS.format(42)}: waiting; runner ended soon\n2026-11-19 12:31:00 other: runner ended\n=====RUNNER_RC=====")
    l = rp.parse_e9_listing(text)
    assert OBS.format(42) not in l["queue_ended"] and l["active"] == sorted([PLC.format(42), OBS.format(42)])


def test_the_state_changes_when_a_run_finishes_so_a_copy_across_that_moment_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(rp, "NEW_COPY", tmp_path)
    before = rp.e9_state(rp.parse_e9_listing(e9_text([PLC.format(42)], runner="alive")))
    after = rp.e9_state(rp.parse_e9_listing(e9_text([PLC.format(42)], runner="alive", ended=[PLC.format(42)])))
    assert before != after and rp.e9_state(rp.parse_e9_listing(final_text([PLC.format(42)]))) != after
    f = "live_campaign/" + PLC.format(42)
    files = [f"{f}/stages/0/navigation_stats.json"]
    got = rp.copy_settled([f], None, "S_e9", after, lambda: after, trp._fake_rsync(files), rules_fn=rp.e9_rsync_rules, allowed=rp.ALLOWED_E9)
    assert got == files and (tmp_path / files[0]).read_text() == "NEW"
    (tmp_path / files[0]).write_text("OLD")
    with pytest.raises(rp.HostError, match="changed during the copy"):
        rp.copy_settled([f], None, "S2_e9", before, lambda: after, trp._fake_rsync(files), rules_fn=rp.e9_rsync_rules, allowed=rp.ALLOWED_E9)
    assert (tmp_path / files[0]).read_text() == "OLD"
    assert not list(tmp_path.rglob(".rescore_attempt.json"))


def test_the_two_listings_never_take_each_others_names():
    assert rp.parse_e8_listing("\n".join(NAMES + NOISE))["runs"] == [E8.format(42)]
    assert not [n for n in rp.parse_e9_listing(e9_text(NAMES, noise=NOISE))["runs"] if n.startswith("e8_")]


def test_recorded_outcomes_come_from_the_runners_output_first_and_the_status_copy_second():
    n1, n2, n3 = PLC.format(42), PLC.format(43), OBS.format(44)
    l = rp.parse_e9_listing(e9_text([n1], outcomes={n1: "skipped_exists", n2: "launch_failed"},
                                    status={n1: "target_reached", n3: "skipped_host_memory"}))
    assert l["outcomes"] == {n1: "skipped_exists", n2: "launch_failed", n3: "skipped_host_memory"}


def test_the_e9_listing_call_asks_the_host_for_everything_the_rule_needs_and_fails_loudly(monkeypatch):
    class R:
        returncode, stdout, stderr = 1, "", "boom"
    monkeypatch.setattr(rp, "ssh", lambda *a, **k: R())
    with pytest.raises(rp.HostError):
        rp.fetch_e9_listing()
    cmds = []

    class OK:
        returncode, stdout, stderr = 0, e9_text(NAMES, runner="alive"), ""
    monkeypatch.setattr(rp, "ssh", lambda c, *a, **k: cmds.append(c) or OK())
    assert rp.fetch_e9_listing()["active"]
    c = cmds[0]
    for want in ("grep e9_", "e9_queue.log", "pgrep -u \"$(id -u)\" -f 'live_runner\\.py'", "systemctl --user list-units --state=active",
                 "'e9-queue-*.scope'", "runner_e9_*.out", "status_asp-noetic.e9_*.json", "id -u"):
        assert want in c, want
    assert "e8_" not in c and ".active_" not in c
    import re
    assert re.search(r"live_runner\.py", c) is None                    # the pgrep pattern does not match this very command line
    rp.fetch_e8_listing()
    assert "grep e8_" in cmds[1] and ".active_e8_*" in cmds[1]          # the e8 call is the one it was


# --- the copy list and its checks --------------------------------------------------------------------------------

def test_e9_copy_rules_bring_stats_graphs_and_the_log_only():
    f = "live_campaign/" + PLC.format(42)
    rules = rp.e9_rsync_rules([f])
    for want in ("--include=/live_campaign/", f"--include=/{f}/stages/*/navigation_stats.json", f"--include=/{f}/logs/roslaunch.log",
                 f"--include=/{f}/stages/*/habitat_scene_graph_original_graph*.yaml"):
        assert want in rules
    assert rules[-1] == "--exclude=*"
    assert not any(w in r.lower() for r in rules for w in ("dsg", "prompts", "live_policy", "usage", "excluded"))


def test_transfer_list_for_e9_allows_its_files_and_refuses_the_rest():
    ok = ["live_campaign/x/stages/0/navigation_stats.json", "live_campaign/x/logs/roslaunch.log",
          "live_campaign/x/stages/0/habitat_scene_graph_original_graph0.yaml", "live_campaign/x/stages/0/habitat_scene_graph_original_graph1.yaml"]
    assert rp.check_transfer_list(ok, allowed=rp.ALLOWED_E9) == ok
    for bad in ("live_campaign/x/prompts/usage.jsonl", "live_campaign/x/stages/0/live_policy.jsonl", "live_campaign/x/stages/0/foo_dsg.json.zst",
                "live_campaign/EXCLUDED_x.json", "live_campaign/x/config/commit.txt"):
        with pytest.raises(ValueError):
            rp.check_transfer_list([bad], allowed=rp.ALLOWED_E9)


def test_the_e9_runs_go_to_the_ged_job_like_the_e8_runs():
    w = [{"folder": "live_campaign/" + PLC.format(42), "scene": "00853", "path": "p"},
         {"folder": "live_campaign/" + OBS.format(42), "scene": "00853", "path": "q"}]
    reuse, compute = rp.plan_ged(w, trp.ged_pool([]), lambda p: [{"stage": 0, "path_m": 0.0, "nav_s": 0.0}] if p == "p" else [])
    assert reuse == [] and [x["folder"] for x in compute] == ["live_campaign/" + PLC.format(42)]


# --- the scoring command ------------------------------------------------------------------------------------------

def test_the_score_command_names_each_control_arm_from_the_folder_name_and_is_unchanged_without_control_runs():
    plain = rp.build_score_argv(Path("/o"), trp.ROWS, trp.BUD, "primary_s", Path("/g.json"), [])
    assert plain == rp.build_score_argv(Path("/o"), trp.ROWS, trp.BUD, "primary_s", Path("/g.json"), [], [])
    assert plain == rp.build_score_argv(Path("/o"), trp.ROWS, trp.BUD, "primary_s", Path("/g.json"), [], ())
    paths = [rp.NEW_COPY / "live_campaign" / n for n in (PLC.format(42), OBS.format(43) + "_relaunch1")]
    argv = rp.build_score_argv(Path("/o"), trp.ROWS, trp.BUD, "primary_s", Path("/g.json"), [rp.NEW_COPY / "live_campaign" / E8.format(42)], paths)
    assert f"placebo_nov=00853={paths[0]}" in argv and f"observed_only_nov=00853={paths[1]}" in argv
    assert f"official_nov=00853={rp.NEW_COPY}/live_campaign/{E8.format(42)}" in argv
    assert argv.count("--add-run") == plain.count("--add-run") + 3
    assert argv[-2:] == ["--ged-json", "/g.json"] and not any(a.startswith("--no-") or a == "--only" for a in argv)


# --- A5.3, assess_control -------------------------------------------------------------------------------------------

def ctl_run(camp, name, end_s=700.0, **kw):
    return trp._e8_run(camp, name, end_s=end_s, **kw)          # same stages as an e8 fixture: 0, 30, 60, 90, 100, 105 m


def test_a_clean_run_that_reached_b_and_100_m_counts_and_is_not_marked(tmp_path):
    a = rp.assess_control(ctl_run(tmp_path, PLC.format(42)), B853)
    assert a["counts_in_cells"] and a["reached_b"] and a["reached_100m"] and a["no_final_value"] is False
    assert a["arm"] == "placebo_nov" and a["reasons"] == [] and a["notes"] == [] and a["end_path_m"] == 105
    assert a["evidence"] == {"out_of_memory_lines": 0, "nvblox_died_lines": 0}


def test_a_run_short_of_b_counts_and_keeps_10_and_50_and_a_run_short_of_100_m_has_no_s(tmp_path):
    a = rp.assess_control(ctl_run(tmp_path, PLC.format(42), end_s=632.0), B853)
    assert a["counts_in_cells"] and a["reached_b"] is False and a["reached_100m"] is True
    assert any("no 100% value" in n for n in a["notes"])
    run = make_run(tmp_path / "short", OBS.format(42), PTS_90, log="ok\n")
    b = rp.assess_control(run, B853)
    assert b["counts_in_cells"] and b["reached_100m"] is False and b["end_path_m"] == 90
    assert any("ended before 100 m (90.0 m): no value at 100 m, so no S" in n for n in b["notes"])


@pytest.mark.parametrize("kw,word", [({"oom": True}, "out of memory"), ({"died": True}, "nvblox_node has died"),
                                     ({"oom": True, "died": True}, "out of memory")])
def test_a_gpu_line_marks_the_run_and_leaves_it_in_the_cells(tmp_path, kw, word):
    a = rp.assess_control(ctl_run(tmp_path, PLC.format(42), **kw), B853)
    assert a["counts_in_cells"] is True and a["no_final_value"] is True and a["reasons"] == []
    assert any(word in n for n in a["notes"]) and any("no value at 100% of B or later and none at 100 m; its other cells are reported" in n for n in a["notes"])
    assert a["reached_b"] is True                                   # what it reached is reported as it was


def test_a_control_run_with_no_log_is_marked_as_official_nov_would_be_left_out(tmp_path):
    run = ctl_run(tmp_path, OBS.format(42))
    (run / "logs" / "roslaunch.log").unlink()
    a = rp.assess_control(run, B853)
    assert a["no_final_value"] is True and a["counts_in_cells"] is True
    assert a["evidence"] == {"out_of_memory_lines": None, "nvblox_died_lines": None}
    assert any("no logs/roslaunch.log" in n and "read as one with a line of A5.3" in n and "no value at 100% of B or later and none at 100 m" in n
               for n in a["notes"])
    e = rp.assess_e8(trp._e8_run(tmp_path / "e8", E8.format(42)), B853, tmp_path / "e8")
    (tmp_path / "e8" / E8.format(42) / "logs" / "roslaunch.log").unlink()
    e = rp.assess_e8(tmp_path / "e8" / E8.format(42), B853, tmp_path / "e8")
    assert e["counts_in_cells"] is False and any("no logs/roslaunch.log" in r for r in e["reasons"])     # the same fault there leaves the run out


def test_the_last_stage_needs_both_graphs_here_too(tmp_path):
    a = rp.assess_control(ctl_run(tmp_path, PLC.format(42), end_s=700.0, last_g1=False), B853)
    assert a["reached_b"] is False and a["end_s"] == 580.0 and a["end_path_m"] == 100 and a["reached_100m"] is True


def test_no_llm_check_applies_a_run_with_no_usage_policy_log_or_marker_counts(tmp_path):
    a = rp.assess_control(ctl_run(tmp_path, PLC.format(42), usage=None, policy=False), B853)
    assert a["counts_in_cells"] and a["reasons"] == []
    b = rp.assess_control(ctl_run(tmp_path, PLC.format(43), usage="other_provider", dropped=True, marker="x"), B853)
    assert b["counts_in_cells"] and b["reasons"] == []              # A5.3 drops the two rules about LLM calls (and E1's marker)


def test_a_run_not_finished_and_a_missing_folder_are_not_scored(tmp_path):
    a = rp.assess_control(ctl_run(tmp_path, PLC.format(42)), B853, active=True)
    assert a["open"] and a["counts_in_cells"] is False and a["end_s"] is None and "not finished" in a["notes"][0]
    b = rp.assess_control(tmp_path / PLC.format(44), B853)
    assert b["counts_in_cells"] is False and b["reasons"] == ["the run folder is not in the local copy"]


def test_b_is_pinned_for_the_control_runs_too(tmp_path):
    run = ctl_run(tmp_path, PLC.format(42))
    with pytest.raises(rp.HostError):
        rp.assess_control(run, 640.0)


@pytest.mark.parametrize("kw", [{}, {"oom": True}, {"died": True}, {"end_s": 600.0}, {"end_s": 632.1751}, {"end_s": 632.1750}, {"last_g1": False}])
def test_the_reach_and_gpu_checks_are_assess_e8s(tmp_path, kw):
    e = rp.assess_e8(trp._e8_run(tmp_path / "e8", E8.format(42), **kw), B853, tmp_path / "e8")
    c = rp.assess_control(ctl_run(tmp_path / "e9", PLC.format(42), **kw), B853)
    for k in ("reached_b", "end_s", "end_stage"):
        assert e[k] == c[k]
    assert (e["evidence"]["out_of_memory_lines"], e["evidence"]["nvblox_died_lines"]) == \
           (c["evidence"]["out_of_memory_lines"], c["evidence"]["nvblox_died_lines"])
    assert (not e["counts_in_cells"]) == bool(c["no_final_value"])   # what A3.2 leaves out, A5.3 marks


# --- the relaunch rule (item 7) -----------------------------------------------------------------------------------------

def listing_for(tmp, names, **kw):
    return rp.parse_e9_listing(final_text(names, **kw))


@pytest.mark.parametrize("outcome", ["skipped_exists", "skipped_campaign_cap", "skipped_host_memory", "launch_failed"])
def test_a_relaunch_replaces_an_original_the_runner_recorded_as_skipped_or_failed(tmp_path, outcome):
    (tmp_path / OBS.format(44) / "config").mkdir(parents=True)               # a folder was left behind
    r = ctl_run(tmp_path, OBS.format(44) + "_relaunch1")
    for how in ({"outcomes": {OBS.format(44): outcome}}, {"status": {OBS.format(44): outcome}}):
        l = listing_for(tmp_path, [OBS.format(44), r.name], **how)
        assert rp.e9_runs_to_assess(tmp_path, l) == ([r.name], [OBS.format(44)])


@pytest.mark.parametrize("outcome", [None, "target_reached", "stopped_by_control_file", "pipeline_exited", "stalled", "host_memory_low"])
def test_a_folder_with_no_stage_whose_launcher_started_is_a_run_that_happened(tmp_path, outcome):
    (tmp_path / OBS.format(44) / "config").mkdir(parents=True)               # launched, wrote no stage
    r = ctl_run(tmp_path, OBS.format(44) + "_relaunch1")
    l = listing_for(tmp_path, [OBS.format(44), r.name], outcomes={} if outcome is None else {OBS.format(44): outcome})
    with pytest.raises(rp.HostError) as e:
        rp.e9_runs_to_assess(tmp_path, l)
    assert OBS.format(44) in str(e.value) and r.name in str(e.value) and "launch_failed" in str(e.value)
    # alone, with no stage and no relaunch, it is scored as a run with no values
    names, dropped = rp.e9_runs_to_assess(tmp_path, listing_for(tmp_path, [OBS.format(44)], outcomes={OBS.format(44): "target_reached"}))
    assert names == [OBS.format(44)] and dropped == []
    a = rp.assess_control(tmp_path / OBS.format(44), B853)
    assert a["counts_in_cells"] and a["end_s"] is None and a["reached_100m"] is False


def test_a_relaunch_with_no_original_folder_is_accepted_only_on_the_runners_record(tmp_path):
    r = ctl_run(tmp_path, PLC.format(43) + "_relaunch1")
    assert rp.e9_runs_to_assess(tmp_path, listing_for(tmp_path, [r.name], outcomes={PLC.format(43): "skipped_exists"})) == ([r.name], [])
    with pytest.raises(rp.HostError):
        rp.e9_runs_to_assess(tmp_path, listing_for(tmp_path, [r.name]))
    with pytest.raises(rp.HostError):
        rp.e9_runs_to_assess(tmp_path, listing_for(tmp_path, [r.name], outcomes={PLC.format(43): "target_reached"}))


def test_two_started_folders_of_one_seed_stop_the_run_and_name_both(tmp_path):
    a, b = ctl_run(tmp_path, PLC.format(42)), ctl_run(tmp_path, PLC.format(42) + "_relaunch1")
    with pytest.raises(rp.HostError) as e:
        rp.e9_runs_to_assess(tmp_path, listing_for(tmp_path, [a.name, b.name], outcomes={a.name: "target_reached"}))
    assert a.name in str(e.value) and b.name in str(e.value)


# --- the block, the notes and the summary ---------------------------------------------------------------------------

def score_all(camp, names_arms, B=B853):
    write_graph(camp.parent / "ref.yaml", REF_NODES)
    ref = pc.load_reference(camp.parent / "ref.yaml")
    refs = {r: {"00853": ref} for r in ep.REFS}
    recs = [pc.score_run(pc.RunSpec(n, arm, "00853", camp / n, 42), refs, {"00853": B}, []) for n, arm in names_arms]
    return {"meta": {"budgets": {"00853": B, "00871": 1300.2523394823074}, "time_tol_s": pc.TIME_TOL}, "runs": recs,
            "cells": pc.aggregate(recs), "seconds_per_metre": pc.seconds_per_metre(recs)}


def world(tmp, void=None, short=None, skip=None, official=True, no_log=None, running=(), runner="none", unit="none"):
    """Six control runs and the three official_nov runs, as the copy step leaves them under live_campaign/. `running` names
    runs that have not finished (a runner is then alive and the log does not say they ended)."""
    camp = tmp / "live_campaign"
    names_arms = []
    if official:
        for s in (2, 3, 4):
            make_run(camp, f"e8_00853_s4{s}_official_105m", PTS, log="ok\n")
            names_arms.append((f"e8_00853_s4{s}_official_105m", "official_nov"))
    for arm, fmt in (("placebo_nov", PLC), ("observed_only_nov", OBS)):
        for s in (42, 43, 44):
            n = fmt.format(s)
            if n == skip:
                continue
            make_run(camp, n, PTS_90 if n == short else PTS, log=None if n == no_log else "CUDA out of memory\n" if n == void else "ok\n")
            names_arms.append((n, arm))
    ctl_names = [n for n, a in names_arms if a != "official_nov"]
    if running:
        runner = "alive"
    listing = rp.parse_e9_listing(e9_text(ctl_names, ended=[n for n in ctl_names if n not in running], runner=runner, unit=unit))
    ctl, paths = rp.assess_controls(camp, listing, B853)
    return camp, names_arms, ctl, paths


def official_names(names_arms):
    return [n for n, a in names_arms if a == "official_nov"]


def test_assess_controls_holds_back_a_run_that_is_not_finished_and_returns_the_folders_that_count(tmp_path):
    camp, names_arms, ctl, paths = world(tmp_path, running=[PLC.format(43)])
    assert len(ctl["runs"]) == 6 and PLC.format(43) not in [p.name for p in paths] and len(paths) == 5
    r = next(a for a in ctl["runs"] if a["run"] == PLC.format(43))
    assert r["open"] is True and r["counts_in_cells"] is False
    camp, names_arms, ctl, paths = world(tmp_path / "b")
    assert [p.name for p in paths] == sorted(n for n, a in names_arms if a != "official_nov")


@pytest.mark.usefixtures("unpinned")
def test_the_block_holds_everything_a_slide_builder_needs(tmp_path):
    camp, names_arms, ctl, paths = world(tmp_path, void=PLC.format(43), short=OBS.format(44))
    j = score_all(camp, names_arms)
    blk = rp.controls_block(ctl, j, [], official_names(names_arms))
    json.dumps(blk)                                                          # it goes into rescore_summary.json
    assert blk["amendment"] == 5 and blk["B_s"] == 632.1751 and blk["absent"] == [] and blk["interim"] is False and blk["still_running"] == []
    assert sorted(blk["readout1_cells"]) == ["observed_only_nov", "placebo_nov"]
    for arm in pc.CTRL_ARMS:
        ro = blk["readout1_cells"][arm]
        assert sorted(ro) == ["apr", "frontier_made", "hm3d"]
        assert sorted(ro["apr"]) == ["10", "100", "50"] and sorted(ro["apr"]["10"]) == ["ged", "n_runs", "runmax", "stage"]
        assert sorted(ro["apr"]["10"]["stage"]) == ["max", "mean", "min", "n"]
    assert blk["readout1_cells"]["placebo_nov"]["apr"]["100"]["stage"]["n"] == 2          # s43 is marked: no value at 100% of B
    assert blk["readout1_cells"]["placebo_nov"]["apr"]["50"]["stage"]["n"] == 3
    assert blk["readout1_cells"]["observed_only_nov"]["apr"]["100"]["stage"]["n"] == 2     # the 90 m run ended at 580 s, before B
    r2 = blk["readout2_equal_path"]
    assert r2["arms"] == ["official_nov", "placebo_nov", "observed_only_nov"] and r2["lengths_m"] == [50, 60, 80, 100]
    assert r2["tables"]["apr"]["placebo_nov"]["100"]["n"] == 2 and r2["tables"]["hm3d"]["observed_only_nov"]["100"]["n"] == 2
    assert blk["readout3_sec_per_m"]["placebo_nov"]["n"] == 3 and blk["S_lengths_m"] == [50, 60, 80, 100]
    s = blk["S"]["apr"]
    assert s["placebo_nov"][PLC.format(43)] is None and s["observed_only_nov"][OBS.format(44)] is None
    assert s["placebo_nov"][PLC.format(42)] == pytest.approx(100.0) and len(s["official_nov"]) == 3
    assert blk["statements"] == {"placebo_nov": "no statement", "observed_only_nov": "no statement"}
    assert blk["slide"]["kind"] == "tables_only" and blk["slide_sentence"] is None and blk["per_reference"] == {"placebo_nov": {}, "observed_only_nov": {}}
    assert blk["decision"]["arms"]["placebo_nov"]["S"]["apr"][PLC.format(43)] is None
    marked = [r for r in blk["evidence_table"] if r["marked_no_value_at_100pct_of_B_and_100m"]]
    assert [r["run"] for r in marked] == [PLC.format(43)] and marked[0]["out_of_memory_lines"] == 1
    assert [r["reached_100m"] for r in blk["evidence_table"] if r["run"] == OBS.format(44)] == [False]
    assert all("calls" not in r and "members_dropped_pct" not in r for r in blk["evidence_table"])      # no LLM columns
    assert set(blk["labels"].values()) == {"final"}


@pytest.mark.usefixtures("unpinned")
def test_the_block_reaches_a_statement_and_a_slide_sentence_when_all_runs_have_s_and_nothing_runs(tmp_path):
    camp, names_arms, ctl, paths = world(tmp_path)
    j = score_all(camp, names_arms)
    blk = rp.controls_block(ctl, j, [], official_names(names_arms))
    # all nine runs share one path of F1 values: S is 100 everywhere, so the arms tie and nothing is above
    assert blk["statements"] == {"placebo_nov": "does not read above", "observed_only_nov": "does not read above"}
    assert blk["slide_sentence"] == ("With random guesses, or none, the same pipeline reads as high: "
                                     "November's lead over frontier is not shown to come from the LLM's guesses.")
    assert blk["per_reference"]["placebo_nov"] == {"apr": "not above", "hm3d": "not above"}


@pytest.mark.usefixtures("unpinned")
@pytest.mark.parametrize("kw", [{"running": [OBS.format(44)]}, {"unit": "alive"}, {"runner": "alive"}, {"unit": "unknown"}, {"runner": "unknown"}])
def test_while_a_runner_or_a_queue_unit_may_be_alive_every_part_is_interim_and_nothing_is_stated(tmp_path, kw):
    camp, names_arms, ctl, paths = world(tmp_path, **kw)
    j = score_all(camp, [x for x in names_arms if x[0] in {p.name for p in paths} or x[1] == "official_nov"])
    blk = rp.controls_block(ctl, j, [], official_names(names_arms))
    assert blk["interim"] is True and blk["interim_reasons"] and set(blk["labels"].values()) == {"interim"}
    assert {"readout1_cells", "readout2_equal_path", "readout3_sec_per_m", "S", "statements", "decision", "slide", "slide_sentence",
            "evidence_table", "runs", "per_reference", "other_readings_of_seed_43"} <= set(blk["labels"])
    assert blk["statements"] == {"placebo_nov": "no statement", "observed_only_nov": "no statement"}
    assert blk["slide_sentence"] is None and blk["slide"]["kind"] == "interim" and blk["slide"]["judged_arms"] == []
    assert all(a["interim"] and not a["judged"] and a["per_reference"] == {} and a["why_no_statement"].startswith("interim:")
               for a in blk["decision"]["arms"].values())
    assert blk["S"]["apr"]["placebo_nov"]                                        # the S values are still there, labelled interim
    json.dumps(blk)
    if kw.get("running"):
        assert blk["still_running"] == kw["running"]


@pytest.mark.usefixtures("unpinned")
def test_a_missing_run_is_listed_as_absent_and_a_counted_run_without_a_score_has_no_s(tmp_path):
    camp, names_arms, ctl, paths = world(tmp_path, skip=OBS.format(44))
    j = score_all(camp, names_arms)
    blk = rp.controls_block(ctl, j, [], official_names(names_arms) + [E8.format(45)])
    assert blk["absent"] == [{"arm": "observed_only_nov", "seed": 44}]
    assert blk["S"]["apr"]["official_nov"][E8.format(45)] is None                       # an official run that did not score: no S
    # only the three named runs enter the comparison: the extra one with no S changes nothing, the arm with two runs is not judged
    assert blk["statements"]["observed_only_nov"] == "no statement" and blk["statements"]["placebo_nov"] == "does not read above"


@pytest.mark.usefixtures("unpinned")
def test_the_other_readings_of_seed_43_are_shown_beside_and_decide_nothing(tmp_path):
    camp, names_arms, ctl, paths = world(tmp_path)
    j = score_all(camp, names_arms)
    without = score_all(camp, [x for x in names_arms if x[0] != E8.format(43)])
    stopped_camp = tmp_path / "cut"
    for s in (2, 3, 4):
        make_run(stopped_camp, f"e8_00853_s4{s}_official_105m", PTS if s != 3 else PTS[:4], log="ok\n")
    stopped = score_all(stopped_camp, [(f"e8_00853_s4{s}_official_105m", "official_nov") for s in (2, 3, 4)])
    alts = [{"kind": "stopped", "run": E8.format(43), "stage": 22, "folder": "alt_nov_stopped", "pc_json": stopped},
            {"kind": "without", "run": E8.format(43), "folder": "alt_nov_without", "pc_json": without}]
    blk = rp.controls_block(ctl, j, alts, official_names(names_arms))
    st, wo = blk["other_readings_of_seed_43"]
    assert st["kind"] == "stopped" and st["decides"] == "nothing" and st["official_nov_S"]["apr"][E8.format(43)] is None
    assert st["official_nov_mean_S"]["apr"] == pytest.approx(100.0)
    assert wo["kind"] == "without" and sorted(wo["official_nov_S"]["hm3d"]) == [E8.format(42), E8.format(44)]
    assert blk["statements"] == rp.controls_block(ctl, j, [], official_names(names_arms))["statements"]


def test_control_alt_readings_loads_the_files_the_alternatives_wrote(tmp_path):
    (tmp_path / "alt_a").mkdir()
    (tmp_path / "alt_a" / "paper_compare.json").write_text(json.dumps({"runs": [], "cells": []}))
    nov = {"alternatives": {"rows": [{"kind": "without", "run": "r", "folder": "alt_a", "cells": {}}]}}
    got = rp.control_alt_readings(nov, tmp_path)
    assert got == [{"kind": "without", "run": "r", "stage": None, "folder": "alt_a", "pc_json": {"runs": [], "cells": []}}]
    assert rp.control_alt_readings(None, tmp_path) == []


def summary_with(blk):
    s = trp._summary(True)
    s["nov_controls"] = blk
    return s


NOTES_ARGS = ({"00853": 632.0, "00871": 809.084},)


@pytest.mark.usefixtures("unpinned")
def test_notes_carry_the_amendment_5_section_with_every_table(tmp_path):
    camp, names_arms, ctl, paths = world(tmp_path, void=PLC.format(43), short=OBS.format(44), skip=OBS.format(42), no_log=PLC.format(44))
    j = score_all(camp, names_arms)
    blk = rp.controls_block(ctl, j, [], official_names(names_arms))
    text = rp.write_notes(summary_with(blk), trp._cmp(False), {"00853": 632.0, "00871": 809.084}, pc)
    assert "and for the control arms Amendment 5" in text.split("\n")[2]
    sec = text.split("## Control arms (Amendment 5)")[1].split("\n## ")[0]
    assert "never pooled with October's `placebo` arm" in sec and "5 of 6 runs count in the cells" in sec and "INTERIM" not in sec
    assert "- Not on the host: `observed_only_nov` seed 42. It has no S." in sec
    assert f"| `{PLC.format(43)}` | finished |" in sec and "| yes | yes | yes |" in sec           # marked row
    assert f"| `{PLC.format(44)}` | finished |" in sec and "no logs/roslaunch.log" in sec and "read as one with a line of A5.3" in sec
    assert "What the A5.3 checks read in each run's files:" in sec and f"| `{PLC.format(43)}` | 1 | 0 |" in sec and f"| `{PLC.format(44)}` | - | - |" in sec
    assert "LLM" not in sec.split("What the A5.3 checks")[1].split("**Readout 1")[0]       # no columns about LLM calls
    for needle in ("**Readout 1 (A5.5)", "`placebo_nov`:", "`observed_only_nov`:", "| apr | F1, stage value |", "| hm3d | GED |",
                   "**Readout 2 (A5.5)", "registered (A5.5)", "first made after the results were seen (deviation 66)",
                   "Reference apr:", "Reference frontier_made:", "| 50 m | 60 m | 80 m | 100 m |",
                   "**Readout 3 (A5.5)", "s/m", "**The reading (A5.6).**", "S against apr:", "S against hm3d:",
                   "every comparison of S is made at full precision, never on the rounded figures"):
        assert needle in sec, needle
    assert f"| `placebo_nov` | `{PLC.format(43)}` | none | yes (marked) |" in sec and f"| `observed_only_nov` | `{OBS.format(44)}` | none | no |" in sec
    assert "`observed_only_nov`: **no statement.**" in sec and "Slide: No arm was judged: the slide shows the S tables only." in sec
    assert "Its S values:" in sec and "What this cannot show" in sec


@pytest.mark.usefixtures("unpinned")
def test_notes_for_an_interim_block_say_so_everywhere_list_the_runs_still_running_and_state_nothing(tmp_path):
    camp, names_arms, ctl, paths = world(tmp_path, running=[PLC.format(44)])
    j = score_all(camp, [x for x in names_arms if x[1] == "official_nov" or x[0] in {p.name for p in paths}])
    blk = rp.controls_block(ctl, j, [], official_names(names_arms))
    sec = rp.write_notes(summary_with(blk), trp._cmp(False), {"00853": 632.0, "00871": 809.084}, pc).split("## Control arms (Amendment 5)")[1].split("\n## ")[0]
    assert "**INTERIM: a live_runner.py process is alive on the host" in sec and "Every table below is interim" in sec
    assert f"- Still running (not copied, not scored): `{PLC.format(44)}`." in sec
    for head in ("**Readout 1 (A5.5) (interim),**", "**Readout 2 (A5.5) (interim),**", "**Readout 3 (A5.5) (interim),**", "**The reading (A5.6) (interim).**"):
        assert head in sec, head
    assert sec.count("no statement (interim: a live_runner.py process") == 2
    assert "Slide: Interim: no statement and no slide sentence" in sec and "reads above" not in sec and "With random guesses" not in sec


@pytest.mark.usefixtures("unpinned")
def test_notes_give_the_statement_and_the_slide_sentence_of_a_judged_arm(tmp_path):
    camp, names_arms, ctl, paths = world(tmp_path)
    j = score_all(camp, names_arms)
    blk = rp.controls_block(ctl, j, [], official_names(names_arms))
    sec = rp.write_notes(summary_with(blk), trp._cmp(False), {"00853": 632.0, "00871": 809.084}, pc).split("## Control arms (Amendment 5)")[1]
    assert "`placebo_nov`: apr: not above, hm3d: not above. Statement: **does not read above**." in sec
    assert ('Slide: "With random guesses, or none, the same pipeline reads as high: November\'s lead over frontier is not shown to come '
            'from the LLM\'s guesses."') in sec


@pytest.mark.usefixtures("unpinned")
def test_notes_name_a_replaced_original_with_the_runners_record(tmp_path):
    camp, names_arms, ctl, paths = world(tmp_path)
    ctl["never_started"] = [OBS.format(44)]
    ctl["listing"]["outcomes"] = {OBS.format(44): "skipped_exists"}
    j = score_all(camp, names_arms)
    blk = rp.controls_block(ctl, j, [], official_names(names_arms))
    sec = rp.write_notes(summary_with(blk), trp._cmp(False), {"00853": 632.0, "00871": 809.084}, pc)
    assert f"recorded as skipped or launch_failed (A5.3): `{OBS.format(44)}` (skipped_exists) is not scored." in sec


@pytest.mark.usefixtures("unpinned")
def test_the_other_readings_table_is_in_the_notes(tmp_path):
    camp, names_arms, ctl, paths = world(tmp_path)
    j = score_all(camp, names_arms)
    alts = [{"kind": "without", "run": E8.format(43), "folder": "alt_nov_without_x", "pc_json": j}]
    blk = rp.controls_block(ctl, j, alts, official_names(names_arms))
    sec = rp.write_notes(summary_with(blk), trp._cmp(False), {"00853": 632.0, "00871": 809.084}, pc)
    assert "**S of `official_nov` under the other readings of one run.**" in sec and "They decide nothing." in sec
    assert "| without the run |" in sec and "`alt_nov_without_x/` |" in sec and "s42: 100.0" in sec


# --- the pinned S of official_nov (item 5) -------------------------------------------------------------------------------

def s_of(vals_apr, vals_hm3d):
    return {"apr": {"official_nov": dict(zip(pc.OFFICIAL_NOV_RUNS, vals_apr))}, "hm3d": {"official_nov": dict(zip(pc.OFFICIAL_NOV_RUNS, vals_hm3d))}}


PINNED_A = [53.55291686668735, 52.48222944405994, 61.725399191409466]
PINNED_H = [29.045779047403908, 28.467900509194806, 30.39810010214091]


def test_the_rescore_stops_if_official_novs_s_differs_from_the_pinned_figures():
    assert rp.check_pinned_official_s(s_of(PINNED_A, PINNED_H)) is None
    assert rp.check_pinned_official_s(s_of([v + 5e-10 for v in PINNED_A], PINNED_H)) is None            # inside the tolerance
    for bad in (s_of([PINNED_A[0] + 1e-6] + PINNED_A[1:], PINNED_H), s_of(PINNED_A, PINNED_H[:2] + [PINNED_H[2] - 0.01]),
                s_of(PINNED_A[:2] + [None], PINNED_H), {"apr": {}, "hm3d": {}}, {}):
        with pytest.raises(rp.HostError) as e:
            rp.check_pinned_official_s(bad)
        assert "pinned" in str(e.value)
    short = s_of(PINNED_A, PINNED_H)
    del short["hm3d"]["official_nov"][pc.OFFICIAL_NOV_RUNS[1]]
    with pytest.raises(rp.HostError):
        rp.check_pinned_official_s(short)


def test_controls_block_stops_on_made_up_official_runs_whose_s_is_not_the_pinned_one(tmp_path):
    camp, names_arms, ctl, paths = world(tmp_path)                  # official S = 100, not the filed figures
    with pytest.raises(rp.HostError, match="differs from the pinned figures"):
        rp.controls_block(ctl, score_all(camp, names_arms), [], official_names(names_arms))


# --- end to end on the filed JSON (item 10) --------------------------------------------------------------------------------

FILED = rp.DEFAULT_OUT
needs_filed = pytest.mark.skipif(not (FILED / "rescore_summary.json").exists(), reason="filed results not present")


def e2e_world(tmp, real, special=None, **kw):
    """Control runs whose F1 is 0 everywhere (so S = 0 against both references), scored by paper_compare's own score_run,
    appended to the filed JSON. `special` maps a name to (points, log)."""
    camp = tmp / "live_campaign"
    write_graph(tmp / "ref.yaml", REF_NODES)
    ref = pc.load_reference(tmp / "ref.yaml")
    refs = {r: {"00853": ref} for r in ep.REFS}
    B = real["meta"]["budgets"]["00853"]
    names_arms, recs = [], []
    for arm, fmt in (("placebo_nov", PLC), ("observed_only_nov", OBS)):
        for s in (42, 43, 44):
            n = fmt.format(s)
            pts, log = (special or {}).get(n, (PTS_MISS, "ok\n"))
            make_run(camp, n, pts, log=log)
            names_arms.append((n, arm))
            recs.append(pc.score_run(pc.RunSpec(n, arm, "00853", camp / n, s), refs, {"00853": B}, []))
    pj = copy.deepcopy(real)
    pj["runs"] += recs
    pj["cells"] += pc.aggregate(recs)
    pj["seconds_per_metre"] = pc.seconds_per_metre([r for r in pj["runs"] if "error" not in r])
    names = [n for n, _ in names_arms]
    ended = names if not kw.get("running") else [n for n in names if n not in kw["running"]]
    listing = rp.parse_e9_listing(e9_text(names, ended=ended, runner="alive" if kw.get("running") else kw.get("runner", "none")))
    ctl, paths = rp.assess_controls(camp, listing, B)
    nov = [r["run"] for r in real["runs"] if r["arm"] == "official_nov"]
    return pj, ctl, nov


@needs_filed
def test_end_to_end_on_the_filed_json_six_pinned_s_values_and_the_statement(tmp_path):
    real = json.loads((FILED / "paper_compare.json").read_text())
    pj, ctl, nov = e2e_world(tmp_path, real)
    blk = rp.controls_block(ctl, pj, [], nov)
    for ref, vals in (("apr", PINNED_A), ("hm3d", PINNED_H)):
        assert [blk["S"][ref]["official_nov"][r] for r in pc.OFFICIAL_NOV_RUNS] == vals          # the six figures, at full precision
        for arm in pc.CTRL_ARMS:
            assert sorted(blk["S"][ref][arm].values()) == [0.0, 0.0, 0.0]
    for arm in pc.CTRL_ARMS:
        assert blk["per_reference"][arm] == {"apr": "separated above", "hm3d": "separated above"}
        assert blk["statements"][arm] == "reads above"
    assert blk["slide_sentence"] == ("With random guesses, or none, the same pipeline reads lower on this home: "
                                     "here the LLM's guesses add to ASP's score.")
    assert blk["interim"] is False and set(blk["labels"].values()) == {"final"} and blk["absent"] == []
    assert blk["readout1_cells"]["placebo_nov"]["apr"]["100"]["stage"]["n"] == 3
    json.dumps(blk)
    notes = rp.write_notes(summary_with(blk), trp._cmp(False), {"00853": 632.0, "00871": 809.084}, pc)
    assert "Statement: **reads above**." in notes


@needs_filed
def test_end_to_end_a_control_run_with_no_log_has_no_s_and_its_arm_gets_no_statement(tmp_path):
    real = json.loads((FILED / "paper_compare.json").read_text())
    pj, ctl, nov = e2e_world(tmp_path, real, special={OBS.format(43): (PTS_MISS, None)})
    blk = rp.controls_block(ctl, pj, [], nov)
    assert blk["S"]["apr"]["observed_only_nov"][OBS.format(43)] is None and blk["S"]["hm3d"]["observed_only_nov"][OBS.format(43)] is None
    marked = [r for r in blk["evidence_table"] if r["marked_no_value_at_100pct_of_B_and_100m"]]
    assert [r["run"] for r in marked] == [OBS.format(43)] and marked[0]["out_of_memory_lines"] is None
    assert blk["statements"] == {"placebo_nov": "reads above", "observed_only_nov": "no statement"}
    assert "2 of its runs have S" in blk["decision"]["arms"]["observed_only_nov"]["why_no_statement"]
    assert blk["slide_sentence"] == ("With random guesses, the same pipeline reads lower on this home: "
                                     "here the LLM's guesses add to ASP's score.")
    # its other cells are reported: n at 10% and 50% of B is 3, at 100% of B it is 2
    c = blk["readout1_cells"]["observed_only_nov"]["apr"]
    assert c["10"]["stage"]["n"] == 3 and c["50"]["stage"]["n"] == 3 and c["100"]["stage"]["n"] == 2


@needs_filed
def test_end_to_end_while_a_run_is_still_running_nothing_is_stated(tmp_path):
    real = json.loads((FILED / "paper_compare.json").read_text())
    pj, ctl, nov = e2e_world(tmp_path, real, running=[OBS.format(44)])
    blk = rp.controls_block(ctl, pj, [], nov)
    assert blk["interim"] is True and blk["statements"] == {"placebo_nov": "no statement", "observed_only_nov": "no statement"}
    assert blk["slide_sentence"] is None and blk["still_running"] == [OBS.format(44)]


@needs_filed
def test_end_to_end_a_missing_or_changed_official_run_stops_the_rescore_or_judges_no_arm(tmp_path):
    real = json.loads((FILED / "paper_compare.json").read_text())
    pj, ctl, nov = e2e_world(tmp_path, real)
    changed = copy.deepcopy(pj)
    run = next(r for r in changed["runs"] if r["run"] == pc.OFFICIAL_NOV_RUNS[0])
    for st in run["stages"]:
        st["scores"]["apr"]["f1"] = min(1.0, st["scores"]["apr"]["f1"] + 0.01)
    with pytest.raises(rp.HostError, match="pinned"):
        rp.controls_block(ctl, changed, [], nov)
    gone = copy.deepcopy(pj)
    gone["runs"] = [r for r in gone["runs"] if r["run"] != pc.OFFICIAL_NOV_RUNS[1]]
    with pytest.raises(rp.HostError, match="pinned"):
        rp.controls_block(ctl, gone, [], nov)


# --- archive_previous and the output of the rescore (item 9) ---------------------------------------------------------------

def test_archive_previous_moves_equal_path_and_budget_sensitivity_aside_with_the_rest(tmp_path):
    out = tmp_path
    for n in ("paper_compare.json", "paper_compare.md", "NOTES.md", "rescore_summary.json", "comparison_vs_1112.json"):
        (out / n).write_text("old " + n)
    for folder in ("equal_path", "budget_sensitivity", "alt_B_with_capped", "alt_nov_without_x"):
        (out / folder).mkdir()
        (out / folder / f"{folder}.json").write_text("old " + folder)
    rp.archive_previous(out, "S1")
    dest = out / "previous_S1"
    for folder in ("equal_path", "budget_sensitivity", "alt_B_with_capped", "alt_nov_without_x"):
        assert not (out / folder).exists() and (dest / folder / f"{folder}.json").read_text() == "old " + folder
    assert (dest / "NOTES.md").read_text() == "old NOTES.md"


def test_archive_previous_with_nothing_filed_does_nothing(tmp_path):
    (tmp_path / "equal_path").mkdir()
    rp.archive_previous(tmp_path, "S2")
    assert (tmp_path / "equal_path").exists() and not (tmp_path / "previous_S2").exists()


# --- nothing moves without an e9 folder ---------------------------------------------------------------------------------

@needs_filed
def test_without_any_e9_folder_the_filed_notes_are_reproduced_byte_for_byte():
    s = json.loads((FILED / "rescore_summary.json").read_text())
    assert "nov_controls" not in s
    cmp_ = json.loads((FILED / "comparison_vs_1112.json").read_text())
    old = json.loads((rp.OLD_OUT / "paper_compare.json").read_text())["meta"]["budgets"]
    assert rp.write_notes(s, cmp_, old, pc) == (FILED / "NOTES.md").read_text()
    assert "Amendment 5" not in (FILED / "NOTES.md").read_text()


@needs_filed
def test_without_any_e9_folder_the_filed_tables_are_reproduced_by_the_scorers_code():
    j = json.loads((FILED / "paper_compare.json").read_text())
    scored = [r for r in j["runs"] if "error" not in r]
    assert pc.aggregate(scored) == j["cells"] and pc.seconds_per_metre(scored) == j["seconds_per_metre"]
    assert (FILED / "paper_compare.md").read_text().endswith(pc.build_markdown(j))
    assert not [r for r in j["runs"] if r["arm"] in pc.CTRL_ARMS] and not [c for c in j["cells"] if c["arm"] in pc.CTRL_ARMS]
    assert not [r for r in j["runs"] if "no_final_value" in r or "roslaunch" in r]
    ro = rp.nov_readouts(j)
    assert ro == rp.nov_readouts(j, "official_nov") and sorted(ro) == ["apr", "frontier_made", "hm3d"]
    assert rp.nov_readouts(j, "placebo_nov") == {} and rp.nov_readouts(j, "observed_only_nov") == {}


@needs_filed
def test_the_filed_november_cells_are_untouched_by_the_shared_assessment_code():
    s = json.loads((FILED / "rescore_summary.json").read_text())
    j = json.loads((FILED / "paper_compare.json").read_text())
    assert s["nov"]["readouts"] == rp.nov_readouts(j)
    assert rp.nov_cells(j) == s["nov"]["alternatives"]["as_run"]
    for r in s["nov"]["runs"]:                                            # every filed e8 assessment keeps its keys: no new one was added
        assert set(r) == {"run", "open", "reached_b", "end_s", "end_stage", "counts_in_cells", "reasons", "notes", "evidence"}


def test_the_parser_has_no_option_that_picks_lengths_references_or_runs():
    dests = {a.dest for a in rp.build_parser()._actions}
    assert dests == {"help", "mode", "out_dir", "no_copy", "ged_recheck", "nov_also_stopped", "nov_also_without"}
    assert set(pc.S_LENGTHS) == set(ep.REG_LENGTHS) == {50, 60, 80, 100} and pc.S_REFERENCES == ("apr", "hm3d")


def test_the_final_command_of_the_last_filing_still_parses():
    a = rp.build_parser().parse_args(["--mode", "final", "--nov-also-stopped", E8.format(43) + "=22", "--nov-also-without", E8.format(43)])
    assert a.mode == "final" and a.nov_also_stopped == E8.format(43) + "=22" and a.nov_also_without == E8.format(43)
