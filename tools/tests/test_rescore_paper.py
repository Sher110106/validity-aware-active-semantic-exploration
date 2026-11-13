"""Tests for tools/live_policy/host/rescore_paper.py: budget B, the folder map, the validity filter,
pending attempts, C2, GED reuse and the copy list."""
import json
import os
import sys

import pytest
import yaml

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "live_policy", "host"))
sys.path.insert(0, os.path.join(HERE, "..", "live_policy"))
import rescore_paper as rp  # noqa: E402


# --- budget B -----------------------------------------------------------------

def run(name, end, complete=True, capped=False):
    return {"run": name, "end_s": end, "exploration_complete": complete, "capped": capped}


def test_budget_odd_count_is_the_middle_value():
    b = rp.compute_budget("00853", [run("a", 611.8), run("b", 867.6), run("c", 632.2), run("d", 739.2), run("e", 629.2)], 632.1256)
    assert b["primary_s"] == 632.2 and b["primary_rule"] == "median" and b["n_primary"] == 5


def test_budget_even_count_is_the_mean_of_the_two_middle_values():
    b = rp.compute_budget("00871", [run("a", 1000.0), run("b", 1600.0), run("c", 1200.0), run("d", 1400.0)], 809.084)
    assert b["primary_s"] == pytest.approx(1300.0)  # sorted 1000 1200 1400 1600: (1200 + 1400) / 2


def test_budget_two_runs_is_their_mean():
    assert rp.compute_budget("00871", [run("a", 1263.5), run("b", 900.0)], 809.084)["primary_s"] == pytest.approx(1081.75)


def test_capped_run_stays_out_of_the_primary_and_enters_the_second_line():
    runs = [run("a", 1000.0), run("b", 1200.0), run("c", 1400.0), run("cap", 15000.0, complete=False, capped=True)]
    b = rp.compute_budget("00871", runs, 809.084)
    assert b["primary_s"] == 1200.0 and b["n_primary"] == 3 and b["capped_runs"] == ["cap"]
    assert b["with_capped_s"] == pytest.approx(1300.0) and b["second_line_differs"] is True


def test_no_capped_run_means_the_two_lines_agree():
    b = rp.compute_budget("00853", [run("a", 600.0), run("b", 700.0)], 632.1256)
    assert b["second_line_differs"] is False


@pytest.mark.parametrize("runs", [[], [run("only", 1263.5)], [run("only", 1263.5), run("cap", 15000.0, False, True)]])
def test_fewer_than_two_runs_gives_the_registered_fallback(runs):
    b = rp.compute_budget("00871", runs, 809.084)
    assert b["primary_s"] == 809.084 and b["primary_rule"] == "fallback"


def test_two_capped_runs_alone_leave_the_primary_at_the_fallback():
    b = rp.compute_budget("00871", [run("x", 15000.0, False, True), run("y", 14000.0, False, True)], 809.084)
    assert b["primary_rule"] == "fallback" and b["with_capped_rule"] == "median"


# --- the folder map -----------------------------------------------------------

LOG = """\
2026-11-09T17:57:58+05:30 launch frontier_seeds/e7_00871_s42_frontier_end (mem 108 GB, disk 21 GB, GPU free 46941 MB)
[WARN] [1794251077.820435]: Frontier planner returned no target. Exploration finished.
2026-11-09T19:01:16+05:30 finished frontier_seeds/e7_00871_s42_frontier_end: host_memory_stop at 85.3 m
2026-11-09T20:56:03+05:30 skip apr/apr_00871_a: skipped: mem 1 GB, disk 45 GB
2026-11-09T21:01:24+05:30 restarted (by hand: apr:00871:a was skipped) with: apr:00871:a
2026-11-09T21:06:24+05:30 launch apr/apr_00871_a (mem 101 GB, disk 45 GB, GPU free 5250 MB)
2026-11-09T21:51:42+05:30 finished apr/apr_00871_a: exploration_complete at 124.6 m
2026-11-09T21:57:15+05:30 launch apr/apr_00853_b (mem 101 GB)
2026-11-09T22:56:39+05:30 finished apr/apr_00853_b: exploration_complete at 183.3 m
2026-11-09T23:01:47+05:30 launch apr/apr_00871_b (mem 98 GB)
2026-11-09T23:48:06+05:30 finished apr/apr_00871_b: exploration_complete at 137.1 m
2026-11-09T16:25:07+05:30 launch apr/dryrun_apr_00853_a_3wp (mem 109 GB)
2026-11-10T12:13:42+05:30 launch frontier_seeds/e7_00871_s42_frontier_end (mem 102 GB)
2026-11-10T13:05:58+05:30 finished frontier_seeds/e7_00871_s42_frontier_end: stalled: no new stage for 20 min at 57.6 m
2026-11-13T17:07:41+05:30 launch apr/apr_00853_b (mem 100 GB)
2026-11-13T18:04:00+05:30 finished apr/apr_00853_b: exploration_complete at 183.3 m
"""

EXISTING = {"apr/apr_00871_a", "apr/apr_00853_b", "apr/apr_00853_b_FAILED_ATTEMPT_1707", "apr/apr_00871_b",
            "apr/dryrun_apr_00853_a_3wp", "frontier_seeds/e7_00871_s42_frontier_end",
            "frontier_seeds/e7_00871_s42_frontier_end_FAILED_ATTEMPT_1213",
            "frontier_seeds/e7_00853_s42_frontier_end_FAILED_ATTEMPT1_gpu_oom"}


def test_parse_drops_noise_and_hand_restart_lines():
    ev = rp.parse_queue_log(LOG)
    assert {e["kind"] for e in ev} == {"launch", "finished", "skip"}
    assert not any("restarted" in e["name"] for e in ev)
    fin = [e for e in ev if e["kind"] == "finished"][0]
    assert fin["name"] == "frontier_seeds/e7_00871_s42_frontier_end" and fin["rest"].startswith("host_memory_stop")


def test_rerun_renames_the_older_attempt_by_the_next_launch_time():
    fm = rp.folder_map(rp.parse_queue_log(LOG), EXISTING)
    s42 = fm["attempts"]["frontier_seeds/e7_00871_s42_frontier_end"]
    assert [a["folder"] for a in s42] == ["frontier_seeds/e7_00871_s42_frontier_end_FAILED_ATTEMPT_1213",
                                          "frontier_seeds/e7_00871_s42_frontier_end"]
    b853 = fm["attempts"]["apr/apr_00853_b"]
    assert [a["folder"] for a in b853] == ["apr/apr_00853_b_FAILED_ATTEMPT_1707", "apr/apr_00853_b"]
    assert all(a["folder_exists"] for rows in fm["attempts"].values() for a in rows)


def test_single_launch_keeps_the_plain_name_and_the_dry_run_is_left_out():
    fm = rp.folder_map(rp.parse_queue_log(LOG), EXISTING)
    assert [a["folder"] for a in fm["attempts"]["apr/apr_00871_b"]] == ["apr/apr_00871_b"]
    assert not any("dryrun" in n for n in fm["attempts"])


def test_a_skip_is_not_an_attempt():
    fm = rp.folder_map(rp.parse_queue_log(LOG), EXISTING)
    assert len(fm["attempts"]["apr/apr_00871_a"]) == 1 and fm["skips"] == {"apr/apr_00871_a": 1}


def test_unclaimed_folder_is_reported_not_guessed():
    fm = rp.folder_map(rp.parse_queue_log(LOG), EXISTING)
    assert fm["unmapped"] == ["frontier_seeds/e7_00853_s42_frontier_end_FAILED_ATTEMPT1_gpu_oom"]


def test_third_launch_moves_attempt_two_aside_and_takes_the_plain_name():
    log = LOG + ("2026-11-14T09:00:10+05:30 launch frontier_seeds/e7_00871_s42_frontier_end (mem 100 GB)\n"
                 "2026-11-14T10:20:00+05:30 finished frontier_seeds/e7_00871_s42_frontier_end: exploration_complete at 150 m\n")
    existing = EXISTING | {"frontier_seeds/e7_00871_s42_frontier_end_FAILED_ATTEMPT_0900"}
    fm = rp.folder_map(rp.parse_queue_log(log), existing)
    s42 = fm["attempts"]["frontier_seeds/e7_00871_s42_frontier_end"]
    assert [a["folder"].split("e7_00871_s42_frontier_end")[1] for a in s42] == ["_FAILED_ATTEMPT_1213", "_FAILED_ATTEMPT_0900", ""]
    assert [a["status"] for a in s42] == ["finished", "finished", "finished"]


def test_rename_a_minute_off_the_launch_stamp_is_still_found():
    log = ("2026-11-10T04:00:00+05:30 launch frontier_seeds/e7_00871_s43_frontier_end (x)\n"
           "2026-11-10T04:30:00+05:30 finished frontier_seeds/e7_00871_s43_frontier_end: stalled\n"
           "2026-11-10T13:14:03+05:30 launch frontier_seeds/e7_00871_s43_frontier_end (x)\n")
    existing = {"frontier_seeds/e7_00871_s43_frontier_end", "frontier_seeds/e7_00871_s43_frontier_end_FAILED_ATTEMPT_1313"}
    fm = rp.folder_map(rp.parse_queue_log(log), existing)
    a1 = fm["attempts"]["frontier_seeds/e7_00871_s43_frontier_end"][0]
    assert a1["folder"].endswith("_1313") and "within 2 minutes" in a1["matched_by"]


def test_running_third_attempt_is_marked_and_pending():
    log = LOG + "2026-11-14T09:00:10+05:30 launch frontier_seeds/e7_00871_s42_frontier_end (mem 100 GB)\n"
    existing = EXISTING | {"frontier_seeds/e7_00871_s42_frontier_end_FAILED_ATTEMPT_0900"}
    fm = rp.folder_map(rp.parse_queue_log(log), existing)
    assert fm["attempts"]["frontier_seeds/e7_00871_s42_frontier_end"][-1]["status"] == "in_progress"
    assert "frontier_seeds/e7_00871_s42_frontier_end" in {p["name"] for p in rp.pending_items(fm["attempts"])}


def test_pending_counts_attempts_not_yet_launched():
    fm = rp.folder_map(rp.parse_queue_log(LOG), EXISTING)
    names = {p["name"] for p in rp.pending_items(fm["attempts"])}
    assert "frontier_seeds/e7_00871_s42_frontier_end" in names      # 2 of 3 launched
    assert "apr/apr_00871_b" in names                                # rerun not launched
    assert "apr/apr_00853_b" not in names and "apr/apr_00871_a" not in names


def test_deviation_46_table_marks_unlaunched_attempts():
    fm = rp.folder_map(rp.parse_queue_log(LOG), EXISTING)
    t = rp.table_deviation_46(fm["attempts"])
    assert "e7 00871 s42" in t and "not launched yet (queued)" in t
    assert "`e7_00871_s42_frontier_end_FAILED_ATTEMPT_1213` (finished)" in t


# --- the validity filter --------------------------------------------------------

def acc(run, complete=True, oom=0, died=0, differs=True, **kw):
    return {"run": run, "kind": "e7", "exploration_complete": complete, "out_of_memory_lines": oom,
            "nvblox_died_lines": died, "final_differs_from_first": differs, "end_navigation_time_s": 100.0, **kw}


def e7_table(*pairs):
    """pairs: (name, [(launch, reason or None)]) -> attempt_map via a synthetic queue log."""
    lines, existing = [], set()
    for name, atts in pairs:
        for i, (ts, reason) in enumerate(atts):
            lines.append(f"{ts} launch {name} (x)")
            if reason:
                lines.append(f"{ts[:11]}23:59:00+05:30 finished {name}: {reason}")
        for i in range(len(atts) - 1):
            existing.add(f"{name}_FAILED_ATTEMPT_{atts[i + 1][0][11:13]}{atts[i + 1][0][14:16]}")
        existing.add(name)
    return rp.folder_map(rp.parse_queue_log("\n".join(sorted(lines))), existing)["attempts"]


N871 = "frontier_seeds/e7_00871_s42_frontier_end"
N853 = "frontier_seeds/e7_00853_s42_frontier_end"


def test_valid_run_goes_to_frontier_end_and_crashed_attempts_keep_their_rows():
    at = e7_table((N871, [("2026-11-09T10:00:00+05:30", "stalled"), ("2026-11-10T10:00:00+05:30", "stalled"),
                          ("2026-11-13T20:00:00+05:30", "exploration_complete at 120 m")]))
    acceptance = {"runs": [
        acc(f"{N871}_FAILED_ATTEMPT_1000", complete=False, oom=1, died=1),
        acc(f"{N871}_FAILED_ATTEMPT_2000", complete=False, oom=2, died=1),
        acc(N871)]}
    c = rp.classify(at, acceptance)
    assert c["seeds"][0]["state"] == "valid" and c["seeds"][0]["counted"] == 3
    assert c["rows"]["frontier_end"] == [("00871", N871)]
    assert c["rows"]["crashed_frontier_1st"] == [("00871", f"{N871}_FAILED_ATTEMPT_1000")]
    assert c["rows"]["crashed_frontier_rerun"] == [("00871", f"{N871}_FAILED_ATTEMPT_2000")]
    assert "crashed_frontier_3rd" not in c["rows"]


def test_invalid_third_attempt_is_its_own_row_and_the_seed_is_missing():
    at = e7_table((N871, [("2026-11-09T10:00:00+05:30", "stalled"), ("2026-11-10T10:00:00+05:30", "stalled"),
                          ("2026-11-13T20:00:00+05:30", "stalled")]))
    acceptance = {"runs": [acc(f"{N871}_FAILED_ATTEMPT_1000", False, 1, 1), acc(f"{N871}_FAILED_ATTEMPT_2000", False, 1, 1),
                           acc(N871, False, 1, 1)]}
    c = rp.classify(at, acceptance)
    assert c["seeds"][0]["state"] == "missing" and c["seeds"][0]["counted"] is None
    assert "frontier_end" not in c["rows"]
    assert c["rows"]["crashed_frontier_3rd"] == [("00871", N871)]


def test_running_attempt_enters_no_row_and_the_seed_is_pending():
    at = e7_table((N871, [("2026-11-09T10:00:00+05:30", "stalled"), ("2026-11-10T10:00:00+05:30", "stalled"),
                          ("2026-11-13T20:00:00+05:30", None)]))
    acceptance = {"runs": [acc(f"{N871}_FAILED_ATTEMPT_1000", False, 1, 1), acc(f"{N871}_FAILED_ATTEMPT_2000", False, 1, 1),
                           acc(N871, False, 0, 0, False)]}
    c = rp.classify(at, acceptance)
    assert c["seeds"][0]["state"] == "pending"
    assert N871 not in [f for rows in c["rows"].values() for _, f in rows]


@pytest.mark.parametrize("kw", [{"oom": 1}, {"died": 1}, {"differs": False}, {"complete": False}])
def test_each_a2_1_condition_alone_fails_a_run(kw):
    reason = "exploration_complete at 100 m" if "complete" not in kw else "stalled: no new stage"
    v = rp.attempt_validity(acc("x", **kw), reason)
    assert v["valid"] is False and len(v["why_invalid"]) == 1


def test_a_clean_run_that_logged_exploration_complete_is_valid():
    assert rp.attempt_validity(acc("x"), None)["valid"] is True


def test_a_cap_stop_counts_as_a_stop_but_is_flagged_and_stalled_does_not():
    capped = rp.attempt_validity(acc("x", complete=False), "path_cap_250m at 250 m")
    assert capped["valid"] and capped["capped"] and not capped["exploration_complete"]
    stalled = rp.attempt_validity(acc("x", complete=False), "stalled: no new stage for 20 min at 80 m")
    assert not stalled["valid"]
    # the 11-09 hand ruling: the queue logged `stalled`, but the explorer log holds "Exploration complete"
    assert rp.attempt_validity(acc("x", complete=True), "stalled: no new stage for 20 min at 88 m")["valid"]


def test_one_valid_853_seed_with_one_attempt_is_valid_not_pending():
    at = e7_table((N853, [("2026-11-09T10:00:00+05:30", "stalled")]))
    c = rp.classify(at, {"runs": [acc(N853)]})
    assert c["seeds"][0]["state"] == "valid" and rp.pending_items(at) == []


def test_missing_acceptance_entry_is_not_guessed():
    at = e7_table((N853, [("2026-11-09T10:00:00+05:30", "exploration_complete at 80 m")]))
    c = rp.classify(at, {"runs": []})
    assert c["seeds"][0]["counted"] is None and c["rows"] == {}


# --- C2 and tours ----------------------------------------------------------------

def graph(path, objs):
    path.parent.mkdir(parents=True, exist_ok=True)
    nodes = [{"id": i, "name": n, "position": f"[{x}, 0.0, 0.0]", "node_type": "object"} for i, (n, x) in enumerate(objs)]
    path.write_text(yaml.safe_dump({"nodes": nodes, "edges": []}))


def test_c2_status_cases():
    b1 = [{"name": "apr/apr_00871_b", "attempt": 1, "status": "finished", "folder": "apr/apr_00871_b", "folder_exists": True}]
    acc_by = {"apr/apr_00871_b": {"frozen": True, "meets_80_percent_rule": True}}
    assert rp.c2_status(b1, acc_by)["status"] == "awaiting_rerun"
    b2 = [dict(b1[0], folder="apr/apr_00871_b_FAILED_ATTEMPT_1000"), dict(b1[0], attempt=2)]
    assert rp.c2_status(b2, {**acc_by, "apr/apr_00871_b_FAILED_ATTEMPT_1000": {"frozen": True}})["status"] == "not_computable_frozen_again"
    ok = {"apr/apr_00871_b": {"frozen": False, "meets_80_percent_rule": True}}
    assert rp.c2_status(b2, ok)["status"] == "compute"
    low = {"apr/apr_00871_b": {"frozen": False, "meets_80_percent_rule": False}}
    assert rp.c2_status(b2, low)["status"] == "below_80_percent_rule"
    running = [dict(b1[0], status="in_progress")]
    assert rp.c2_status(running, acc_by)["status"] == "in_progress"


def test_c2_uses_the_final_graph0_and_the_authors_f1(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    graph(a / "stages" / "0" / "habitat_scene_graph_original_graph0.yaml", [("chair", 0.0)])
    graph(a / "stages" / "5" / "habitat_scene_graph_original_graph0.yaml", [("chair", 0.0), ("lamp", 2.0), ("bed", 4.0), ("sofa", 6.0)])
    graph(b / "stages" / "0" / "habitat_scene_graph_original_graph0.yaml", [("chair", 9.0)])
    graph(b / "stages" / "7" / "habitat_scene_graph_original_graph0.yaml", [("chair", 0.1), ("lamp", 2.1), ("bed", 4.1), ("table", 8.0)])
    r = rp.compute_c2(a, b)
    assert (r["n_objects_apr_a"], r["n_objects_apr_b"]) == (4, 4)
    assert r["precision"] == r["recall"] == pytest.approx(0.75) and r["f1"] == pytest.approx(0.75)
    assert r["below_0_90"] is True and "damage" in r["reading"]


def test_frozen_test_compares_names_and_centres_as_written(tmp_path):
    g0 = tmp_path / "stages" / "0" / "habitat_scene_graph_original_graph0.yaml"
    g9 = tmp_path / "stages" / "9" / "habitat_scene_graph_original_graph0.yaml"
    graph(g0, [("chair", 0.0), ("lamp", 1.0)])
    graph(g9, [("lamp", 1.0), ("chair", 0.0)])
    assert rp.tour_counts(tmp_path)["frozen_local"] is True
    graph(g9, [("lamp", 1.0), ("chair", 0.0), ("bed", 3.0)])
    c = rp.tour_counts(tmp_path)
    assert c["frozen_local"] is False and (c["object_nodes_first"], c["object_nodes_final"]) == (2, 3)


# --- GED reuse -------------------------------------------------------------------

def ged_pool(entries):
    return {"runs": {n: {"scene": sc, "run_dir": f"/workspace/runs/frontier_seeds/{n}",
                         "rows": {r["stage"]: r for r in rows}} for n, sc, rows in entries}, "refs": []}


def grow(stage, path, nav, v=1.0):
    return {"stage": stage, "path_m": path, "nav_s": nav, "ged_hm3d": v, "ged_frontier_made": v, "ged_apr": v}


def test_ged_is_reused_by_stage_list_even_when_the_folder_was_renamed():
    old = [grow(0, 0.0, 0.0, 5.0), grow(1, 3.0, 20.0, 4.0)]
    pool = ged_pool([("e7_00871_s42_frontier_end", "00871", old)])     # 11-12: attempt 2 under the plain name
    local = {"frontier_seeds/e7_00871_s42_frontier_end_FAILED_ATTEMPT_0900": [{"stage": 0, "path_m": 0.0, "nav_s": 0.0},
                                                                                {"stage": 1, "path_m": 3.0, "nav_s": 20.0}],
             "frontier_seeds/e7_00871_s42_frontier_end": [{"stage": 0, "path_m": 0.0, "nav_s": 0.0},
                                                          {"stage": 1, "path_m": 5.0, "nav_s": 31.0}]}
    wanted = [{"folder": f, "scene": "00871", "path": f} for f in local]
    reuse, compute = rp.plan_ged(wanted, pool, lambda p: local[p])
    assert [w["folder"] for w in reuse] == ["frontier_seeds/e7_00871_s42_frontier_end_FAILED_ATTEMPT_0900"]
    assert [w["folder"] for w in compute] == ["frontier_seeds/e7_00871_s42_frontier_end"]   # same name, other content


def test_ged_needs_all_three_references_in_every_row():
    row = grow(0, 0.0, 0.0)
    del row["ged_apr"]
    pool = ged_pool([("e7_00853_s42_frontier_end", "00853", [row])])
    w = [{"folder": "frontier_seeds/e7_00853_s42_frontier_end", "scene": "00853", "path": "p"}]
    reuse, compute = rp.plan_ged(w, pool, lambda p: [{"stage": 0, "path_m": 0.0, "nav_s": 0.0}])
    assert not reuse and len(compute) == 1


def test_scoring_file_holds_one_entry_per_e7_run_and_no_stale_name():
    old = [grow(0, 0.0, 0.0, 5.0)]
    pool = ged_pool([("e7_00871_s42_frontier_end", "00871", old), ("e4_00871_s42_frontier_60m", "00871", old)])
    w = {"folder": "frontier_seeds/e7_00871_s42_frontier_end_FAILED_ATTEMPT_0900", "scene": "00871", "path": "p",
         "from_entry": "e7_00871_s42_frontier_end"}
    new = {"frontier_seeds/e7_00871_s42_frontier_end": {"scene": "00871", "stages": [grow(0, 0.0, 0.0, 9.0)]}}
    out = rp.build_ged_file(pool, [w], new)
    names = [r["run_dir"].rsplit("/", 1)[1] for r in out["runs"]]
    assert sorted(names) == sorted(["e4_00871_s42_frontier_60m", "e7_00871_s42_frontier_end_FAILED_ATTEMPT_0900",
                                    "e7_00871_s42_frontier_end"])
    plain = next(r for r in out["runs"] if r["run_dir"].endswith("e7_00871_s42_frontier_end"))
    assert plain["stages"][0]["ged_apr"] == 9.0         # the new value, not the 11-12 one


def test_ged_host_script_is_one_niced_cpu_process_with_a_1113_name():
    s = rp.ged_host_script(["apr:00853=/workspace/x.yaml"], ["/workspace/runs/apr/a=00853"], "T1")
    assert "nice -n 19" in s and "ulimit -v" in s and "paper_ged_new_1113_T1.json" in s
    for bad in ("hydra_ros_node", "task_server", "frontier_baseline", "coverage_tour"):
        assert bad not in s


# --- the copy --------------------------------------------------------------------

def test_rsync_rules_list_only_the_allowed_files_and_end_with_exclude_all():
    rules = rp.rsync_rules(["apr/apr_00853_b", "frontier_seeds/e7_00853_s42_frontier_end"])
    assert rules[-1] == "--exclude=*"
    assert not any("dsg" in r.lower() for r in rules)
    assert "--include=/apr/apr_00853_b/stages/*/navigation_stats.json" in rules
    assert "--include=/apr/apr_00853_b/stages/*/habitat_scene_graph_original_graph*.yaml" in rules


def test_transfer_list_rejects_dsg_and_unlisted_files():
    ok = ["Transfer starting: 3 files", "./", "apr/", "apr/x/stages/0/navigation_stats.json",
          "apr/x/stages/0/habitat_scene_graph_original_graph1.yaml", "sent 10 bytes  received 5 bytes"]
    assert len(rp.check_transfer_list(ok)) == 2
    with pytest.raises(ValueError):
        rp.check_transfer_list(["apr/x/stages/0/habitat_scene_graph_original_graph0.yaml", "apr/x/stages/0/foo_dsg.json.zst"])
    with pytest.raises(ValueError):
        rp.check_transfer_list(["apr/x/stages/0/executed_path.json"])
    with pytest.raises(ValueError):
        rp.check_transfer_list(["apr/x/stages/0/habitat_scene_graph_original_graph0.yaml.dsg"])


def test_local_copy_with_another_attempts_content_is_moved_not_mixed(tmp_path, monkeypatch):
    monkeypatch.setattr(rp, "NEW_COPY", tmp_path)
    name = "frontier_seeds/e7_00871_s42_frontier_end"
    old_launch, new_launch = "2026-11-10T12:13:42+05:30", "2026-11-14T09:00:10+05:30"
    local = tmp_path / name
    local.mkdir(parents=True)
    (local / ".rescore_attempt.json").write_text(json.dumps({"name": name, "launch_ts": old_launch, "attempt": 2}))
    at = {name: [{"name": name, "attempt": 2, "launch_ts": old_launch, "folder": f"{name}_FAILED_ATTEMPT_0900"},
                 {"name": name, "attempt": 3, "launch_ts": new_launch, "folder": name}]}
    moves = rp.reconcile_local_copy(at, "T")
    assert (tmp_path / f"{name}_FAILED_ATTEMPT_0900").is_dir() and not local.exists()
    assert moves[0]["why"].startswith("its content is attempt 2")


def test_folder_without_a_marker_is_set_aside(tmp_path, monkeypatch):
    monkeypatch.setattr(rp, "NEW_COPY", tmp_path)
    (tmp_path / "apr" / "apr_00853_b").mkdir(parents=True)
    at = {"apr/apr_00853_b": [{"name": "apr/apr_00853_b", "attempt": 1, "launch_ts": "t", "folder": "apr/apr_00853_b"}]}
    rp.reconcile_local_copy(at, "T")
    assert (tmp_path / "apr" / "_stale_T_apr_00853_b").is_dir()


# --- output text -----------------------------------------------------------------

def test_interim_rows_are_tagged_and_final_rows_are_not():
    md = "| 00853 | frontier_end | x |\n| 00871 | frontier_end | y |\ntext 00871\n"
    out = rp.mark_interim_rows(md, {"00871": "interim: awaiting the third attempts"})
    assert "| 00871 (interim: awaiting the third attempts) | frontier_end | y |" in out
    assert "| 00853 | frontier_end | x |" in out and "text 00871" in out


def cell(scene, arm, mean, n=5):
    s = {"mean": mean, "min": mean, "max": mean, "n": n}
    return {"scene": scene, "arm": arm, "reference": "apr", "variant": "B", "fraction": "50", "n_runs": n,
            "stage_value_x100": s, "running_max_x100": s, "ged": s}


def test_comparison_reports_identical_and_different_cells():
    old = {"cells": [cell("00853", "frontier_end", 39.5), cell("00871", "frontier_end", 43.2, 1)]}
    new = {"cells": [cell("00853", "frontier_end", 39.5), cell("00871", "frontier_end", 44.0, 1)]}
    c = rp.compare_cells(old, new, ("00853", "00871"))
    assert c["00853"]["identical"] == 1 and not c["00853"]["different"]
    assert len(c["00871"]["different"]) == 1 and c["00871"]["different"][0]["diffs"][0][0] == "stage_value_x100.mean"


# --- mode and notes ----------------------------------------------------------------

def test_mode_auto_is_interim_while_anything_is_pending_and_final_refuses():
    state = {"00853": {"complete": True}, "00871": {"complete": False}}
    pend = [{"name": "apr/apr_00871_b", "why": "1 of 2 attempts launched"}]
    assert rp.decide_mode("auto", state, pend) == "interim"
    assert rp.decide_mode("interim", state, pend) == "interim"
    with pytest.raises(rp.HostError):
        rp.decide_mode("final", state, pend)
    done = {"00853": {"complete": True}, "00871": {"complete": True}}
    assert rp.decide_mode("auto", done, []) == "final" and rp.decide_mode("final", done, []) == "final"


def _summary(complete871):
    bud = lambda b, rule, n: {"primary_s": b, "primary_rule": rule, "n_primary": n, "with_capped_s": b,
                              "second_line_differs": False}
    c2 = {"00853": {"status": "compute", "f1": 0.95, "precision": 0.95, "recall": 0.95, "n_objects_apr_a": 10,
                    "n_objects_apr_b": 10, "nvblox_died_lines": 0, "below_0_90": False},
          "00871": {"status": "awaiting_rerun" if not complete871 else "not_computable_frozen_again", "f1": None}}
    return {"mode": "final" if complete871 else "interim", "written_at": "t", "acceptance_file": "a.json", "c2_file": "c.json",
            "classification": {"seeds": [{"name": "frontier_seeds/e7_00871_s42_frontier_end", "counted": 3,
                                          "attempts": [{"attempt": 1, "valid": False, "why_invalid": ["x"]}]}]},
            "budgets": {"00853": bud(632.0, "median", 5), "00871": bud(1300.0 if complete871 else 809.084,
                                                                       "median" if complete871 else "fallback", 4 if complete871 else 1)},
            "c2": c2, "tours": {"apr/apr_00853_a": {"object_nodes_first": 5, "object_nodes_final": 118}},
            "ged": {"reused": [], "computed": [], "recheck": []},
            "scene_state": {"00853": {"complete": True, "e7_pending": [], "tours_pending": []},
                            "00871": {"complete": complete871, "tours_pending": [] if complete871 else ["apr/apr_00871_b"],
                                      "e7_pending": [] if complete871 else ["frontier_seeds/e7_00871_s42_frontier_end"]}}}


def _cmp(b_changed):
    return {s: {"compared": 1, "identical": 1, "different": [], "b_changed": b_changed and s == "00871"} for s in rp.SCENES}


def test_notes_mark_interim_and_say_when_old_numbers_are_superseded():
    old = {"00853": 632.0, "00871": 809.084}
    interim = rp.write_notes(_summary(False), _cmp(False), old, None)
    assert "**00871: interim, awaiting the third attempts of seeds 42 and the APR-b rerun.**" in interim
    final = rp.write_notes(_summary(True), _cmp(True), old, None)
    assert "**00871: final.** B moved from 809.0840 s to 1300.0000 s" in final and "superseded" in final
    assert "not computable: the rerun is frozen too" in final
