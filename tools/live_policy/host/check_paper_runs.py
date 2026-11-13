#!/usr/bin/env python3
"""Acceptance checks for the paper-scale runs (PREREGISTRATION_PAPER.md, Amendment 2 and its Note).

Runs on the host, reads only. For every e7 run and every tour under the workspace it applies:

  A2.1  a valid frontier-to-end run:
        (1) its explorer log holds "Exploration complete", or the queue logged
            path_cap_250m / wall_clock_4h for it;
        (2) its logs/roslaunch.log holds no "out of memory" line and no line saying
            nvblox_node has died (case ignored, anywhere in the log);
        (3) the graph0 of its final stage does not hold the same object nodes
            (name and centre as written) as the graph0 of its stage 0.
  A2.4  a frozen tour: the graph0 of its final stage holds the same object nodes as stage 0.
        Also reported per tour: nvblox death, the count of "Timeout! Did not find" lines,
        the last archived stop whose graph differs from the one before, object-node counts
        at stage 0 and at the end, and waypoints reached against listed (the 80% rule).

It reads no score and writes one JSON to stdout.

Usage: python3 check_paper_runs.py [workspace]
"""
import glob
import json
import os
import re
import sys

import yaml

W = sys.argv[1] if len(sys.argv) > 1 else "/home/sher/active-semantic-perception-workspace"
QUEUE_LOG = os.path.join(W, "runs/apr/paper_queue.log")
GRAPH = "habitat_scene_graph_original_graph0.yaml"


def object_nodes(path):
    """The set of (name, position-as-written) of object nodes in a graph file."""
    with open(path) as f:
        g = yaml.safe_load(f) or {}
    return frozenset((str(n.get("name")), str(n.get("position"))) for n in g.get("nodes", [])
                     if n.get("node_type") == "object")


def stages_with_graph(run):
    out = []
    for d in glob.glob(os.path.join(run, "stages", "*")):
        if os.path.isfile(os.path.join(d, GRAPH)) and os.path.basename(d).isdigit():
            out.append(int(os.path.basename(d)))
    return sorted(out)


def grep_count(path, pattern, flags=re.I):
    if not os.path.isfile(path):
        return None
    rx = re.compile(pattern, flags)
    with open(path, errors="replace") as f:
        return sum(1 for line in f if rx.search(line))


def queue_reasons():
    """name -> list of (timestamp, reason) from the queue's 'finished' lines, in order."""
    out = {}
    if os.path.isfile(QUEUE_LOG):
        for line in open(QUEUE_LOG, errors="replace"):
            m = re.match(r"(\S+) finished (\S+): (.*)", line.strip())
            if m:
                out.setdefault(m.group(2), []).append((m.group(1), m.group(3)))
    return out


def check(run, kind, reasons):
    name = os.path.relpath(run, os.path.join(W, "runs"))
    logs = os.path.join(run, "logs")
    explorer = os.path.join(logs, "frontier_baseline.log")  # the tour links this name to its own log
    st = stages_with_graph(run)
    r = {"run": name, "kind": kind, "stages_total": len(glob.glob(os.path.join(run, "stages", "*"))),
         "stages_with_graph": st[:1] + st[-1:] if st else [], "n_stages_with_graph": len(st)}
    r["exploration_complete"] = bool(grep_count(explorer, r"Exploration complete", 0))
    r["out_of_memory_lines"] = grep_count(os.path.join(logs, "roslaunch.log"), r"out of memory")
    r["nvblox_died_lines"] = grep_count(os.path.join(logs, "roslaunch.log"), r"nvblox_node.*(process has died|has died)")
    r["queue_finished"] = reasons.get(name.replace("\\", "/"), [])
    if st:
        first, last = object_nodes(os.path.join(run, "stages", str(st[0]), GRAPH)), object_nodes(os.path.join(run, "stages", str(st[-1]), GRAPH))
        r["first_stage"], r["final_stage"] = st[0], st[-1]
        r["objects_first"], r["objects_final"] = len(first), len(last)
        r["final_differs_from_first"] = first != last
    else:
        r["final_differs_from_first"] = None
    if kind == "e7":
        capped = any(re.match(r"(path_cap_250m|wall_clock_4h)", reason) for _, reason in r["queue_finished"][-1:])
        r["a2_1_stop"] = bool(r["exploration_complete"] or capped)
        r["a2_1_clean_log"] = r["out_of_memory_lines"] == 0 and r["nvblox_died_lines"] == 0
        r["a2_1_graph_grew"] = bool(r["final_differs_from_first"])
        r["valid"] = bool(r["a2_1_stop"] and r["a2_1_clean_log"] and r["a2_1_graph_grew"])
        r["capped"] = bool(capped and not r["exploration_complete"])
    else:
        r["frozen"] = (r["final_differs_from_first"] is False)
        r["timeout_lines"] = grep_count(os.path.join(logs, "coverage_tour.log"), r"Timeout! Did not find", 0)
        last_change, prev = None, None
        for s in st:
            cur = object_nodes(os.path.join(run, "stages", str(s), GRAPH))
            if prev is not None and cur != prev:
                last_change = s
            prev = cur
        r["last_stop_whose_graph_changed"] = last_change
        summ = os.path.join(run, "config", "tour_summary.json")
        if os.path.isfile(summ):
            s = json.load(open(summ))
            r["waypoints_listed"], r["waypoints_reached"], r["tour_complete"] = s.get("waypoints_listed"), s.get("waypoints_reached"), s.get("complete")
            if s.get("waypoints_listed"):
                r["meets_80_percent_rule"] = (s.get("waypoints_reached") or 0) >= 0.8 * s["waypoints_listed"]
    nav = 0.0
    for f in glob.glob(os.path.join(run, "stages", "*", "navigation_stats.json")):
        try:
            d = json.load(open(f))
            nav = max(nav, float(d.get("total_navigation_time_seconds", 0)))
        except Exception:
            pass
    r["end_navigation_time_s"] = round(nav, 2)
    return r


def main():
    reasons = queue_reasons()
    out = {"workspace": W, "runs": []}
    for run in sorted(glob.glob(os.path.join(W, "runs/frontier_seeds/e7_*"))):
        if os.path.isdir(run):
            out["runs"].append(check(run, "e7", reasons))
    for run in sorted(glob.glob(os.path.join(W, "runs/apr/apr_*"))):
        if os.path.isdir(run):
            out["runs"].append(check(run, "tour", reasons))
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
