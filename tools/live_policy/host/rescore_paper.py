#!/usr/bin/env python3
"""Rescore the paper-scale runs under Amendment 2 of PREREGISTRATION_PAPER.md (and its Note).

Runs on the Mac. It reads the host over ssh and, for GED only, runs the author's code
in the container on CPU. One command:

    bash tools/live_policy/host/rescore_paper.sh [--mode auto|interim|final]

Steps, in this order (each is logged with a time stamp in rescore_log.jsonl):
  1 acceptance   check_paper_runs.py on the host; its JSON is filed before any scoring
  2 folder map   which folder holds attempt 1, 2 and 3 of every e7 run and every tour
  3 copy         YAML and stats to the laptop copy (rsync, dry run first, explicit include list)
  4 C2           APR-b against APR-a, written to a stamped file before any run is scored
  5 budget B     per scene, by script, as the Note to Amendment 2 says
  6 GED          reuse the 11-12 values where the run's stage list is unchanged; else the host
  7 score        paper_compare.py, rows as the amendment says, then the 11-12 comparison
  8 outputs      tables, JSON and NOTES.md in the results folder

It touches the host read-only, except for files it writes in /workspace/scratch/ (GED outputs
with a _1113 suffix). It never copies a *_dsg.json* file. It starts no GPU job.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LIVE = HERE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(1, str(HERE))
import live_runner  # noqa: E402  (October's exclusion gates: provider, model, dropped members)
from live_runner import (ENSEMBLE_SLOTS, MAX_DROPPED_FRACTION, MIN_STAGES_FOR_DROP_GATE,  # noqa: E402
                         REQUIRED_MODEL_TAG, REQUIRED_PROVIDER, Runner)

HOST = "tyrone"
WS = "/home/sher/active-semantic-perception-workspace"
CONTAINER = "asp-noetic"
QUEUE_LOG = f"{WS}/runs/apr/paper_queue.log"
COPY_ROOT = Path("/Users/sher/cvp_paper_scale_copy")
OLD_COPY = COPY_ROOT / "runs"          # the 11-12 copy; never written
NEW_COPY = COPY_ROOT / "runs_1113"     # this pipeline's copy, one folder per host folder
DEFAULT_OUT = LIVE / "results_paper_compare_1113"
OLD_OUT = LIVE / "results_paper_compare_1112"
OLD_GED_FILES = [LIVE / "results_paper_compare" / "ged" / "paper_ged_existing.json",
                 LIVE / "results_paper_compare" / "ged" / "paper_ged_frontier_ref.json",
                 OLD_OUT / "ged" / "paper_ged_apr_existing_1112.json",
                 OLD_OUT / "ged" / "paper_ged_e7_1112.json"]
CHECKER = HERE / "check_paper_runs.py"

SCENES = ("00853", "00871")
E7_RE = re.compile(r"^frontier_seeds/e7_(\d{5})_s(\d+)_frontier_end$")
TOUR_RE = re.compile(r"^apr/apr_(\d{5})_([ab])$")
SEEDS = (42, 43, 44, 45, 46)
# Attempts the queue was told to run (A2.2). A name absent here has one attempt.
ATTEMPT_CAP = {f"frontier_seeds/e7_00871_s{s}_frontier_end": 3 for s in (42, 43, 44, 45)}
ATTEMPT_CAP.update({"apr/apr_00871_b": 2})
CRASH_ARM = {1: "crashed_frontier_1st", 2: "crashed_frontier_rerun", 3: "crashed_frontier_3rd"}
CAP_REASON = re.compile(r"^(path_cap_250m|wall_clock_4h)")
ALLOWED_FILES = re.compile(r"^(habitat_scene_graph_original_graph\d*\.yaml|navigation_stats\.json|"
                           r"tour_summary\.json|waypoints\.json)$")
# The November ASP runs (Amendment 3 and its Note). Their files come from runs/live_campaign/.
ALLOWED_E8 = re.compile(r"^(habitat_scene_graph_original_graph\d*\.yaml|navigation_stats\.json|live_policy\.jsonl|usage\.jsonl|"
                        r"roslaunch\.log|EXCLUDED_e8_00853_s(42|43|44)_official_105m(_relaunch1)?\.json)$")
NOV_SCENE = "00853"
# A3.3 fixes B for the November runs at 632.1751 s, the figure of 11-12 (the pipeline's own B is 632.17505669...,
# which rounds to it). The pipeline's B must agree to 1e-4: a B that moved stops the November row.
NOV_B_S = 632.1751
NOV_B_PIN_TOL = 1e-4
STALE_MARKER_S = 13 * 3600     # a .active_ marker older than the 12 h run limit plus an hour
DAMAGE_NOTE = ("In both APR-a tours nvblox died partway, and each final graph lacks about the last 60 s of its "
               "tour (results_paper_compare_1112/NOTES.md, items 3 and 4). A C2 below 0.90 therefore mixes that "
               "damage with real movement of the reference, and the slide says so.")


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Host access
# --------------------------------------------------------------------------

class HostError(RuntimeError):
    pass


def ssh(remote_cmd: str, stdin_text: str | None = None, retries: int = 3, timeout: int = 900):
    """Run one command on the host. ssh times out now and then, so retry."""
    last = ""
    for attempt in range(retries):
        try:
            p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", HOST, remote_cmd],
                               input=stdin_text, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            last = "timeout"
            time.sleep(5)
            continue
        if "permission denied" in p.stderr.lower() and "docker" in remote_cmd:
            raise HostError("docker said permission denied: stop and report. " + p.stderr.strip()[:300])
        if p.returncode == 255:
            last = p.stderr.strip()[:300]
            time.sleep(5)
            continue
        return p
    raise HostError(f"ssh failed after {retries} tries: {last}")


# --------------------------------------------------------------------------
# Queue log and folder map
# --------------------------------------------------------------------------

EVENT_RE = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d) (launch|finished|skip) ([^\s:]+)(.*)$")


CONV_RE = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d) converted (\d+) stages of (\S+) and compressed")


def parse_queue_log(text: str) -> list:
    """The launch, finished, skip and converted lines, in order. ROS noise and other lines are dropped.

    The queue writes `converted N stages of <name>` after `finished`: the author's converter makes
    the YAML files then. Before that line the run's YAML is not complete."""
    events = []
    for i, line in enumerate(text.splitlines()):
        m = EVENT_RE.match(line.strip())
        if m:
            events.append({"i": i, "ts": m.group(1), "kind": m.group(2), "name": m.group(3),
                           "rest": m.group(4).lstrip(": ").strip()})
            continue
        m = CONV_RE.match(line.strip())
        if m:
            events.append({"i": i, "ts": m.group(1), "kind": "converted", "name": m.group(3), "rest": m.group(2)})
    return events


def hhmm(ts: str) -> str:
    return ts[11:13] + ts[14:16]


def attempts_by_name(events: list) -> dict:
    """name -> attempts in launch order. An attempt is used up at its `launch` line (A2.2).

    A `finished` line belongs to the latest attempt that has none yet.
    """
    out = {}
    for e in events:
        if e["kind"] == "launch":
            lst = out.setdefault(e["name"], [])
            lst.append({"attempt": len(lst) + 1, "launch_ts": e["ts"], "finish_ts": None, "finish_reason": None,
                        "convert_ts": None})
        elif e["kind"] == "finished":
            lst = out.get(e["name"])
            if lst and lst[-1]["finish_reason"] is None:
                lst[-1]["finish_ts"], lst[-1]["finish_reason"] = e["ts"], e["rest"]
        elif e["kind"] == "converted":
            lst = out.get(e["name"])
            if lst and lst[-1]["finish_reason"] is not None and lst[-1]["convert_ts"] is None:
                lst[-1]["convert_ts"] = e["ts"]
    return out


OPEN_STATES = ("in_progress", "converting")


def is_open(attempt: dict) -> bool:
    """An attempt that is running, or finished but not yet converted: it can still change."""
    return attempt["status"] in OPEN_STATES


def tracked(name: str) -> bool:
    return bool(E7_RE.match(name) or TOUR_RE.match(name))


def _minutes(h: str) -> int:
    return int(h[:2]) * 60 + int(h[2:])


def folder_map(events: list, existing: set) -> dict:
    """Which folder holds each attempt.

    The queue moves the older attempt aside as <name>_FAILED_ATTEMPT_<HHMM> when the next one
    launches, HHMM being that launch's time. The latest launch holds the plain name.
    Returns {"attempts": {name: [attempt dict]}, "unmapped": [folders], "skips": {name: n}}.
    """
    atts = attempts_by_name(events)
    skips = {}
    for e in events:
        if e["kind"] == "skip":
            skips[e["name"]] = skips.get(e["name"], 0) + 1
    claimed, result = set(), {}
    pending_fuzzy = []
    for name, lst in atts.items():
        if not tracked(name):
            continue
        rows = []
        for k, a in enumerate(lst):
            row = dict(a, name=name, folder=None, folder_exists=False, matched_by=None, status=None)
            if k == len(lst) - 1:
                row["folder"], row["matched_by"] = name, "latest launch keeps the plain name"
                row["status"] = ("in_progress" if a["finish_reason"] is None else
                                 "converting" if a["convert_ts"] is None else "finished")
            else:
                row["status"] = "finished" if a["finish_reason"] is not None else "no_finish_line"
                exp = f"{name}_FAILED_ATTEMPT_{hhmm(lst[k + 1]['launch_ts'])}"
                if exp in existing:
                    row["folder"], row["matched_by"] = exp, "renamed when attempt %d launched" % (k + 2)
                else:
                    pending_fuzzy.append(row)
            if row["folder"] is not None:
                claimed.add(row["folder"])
            rows.append(row)
        result[name] = rows
    for row in pending_fuzzy:          # a rename a minute off the launch time stamp
        name = row["name"]
        nxt = atts[name][row["attempt"]]["launch_ts"]
        cands = []
        for e in sorted(existing - claimed):
            m = re.fullmatch(re.escape(name) + r"_FAILED_ATTEMPT_(\d{4})", e)
            if m and abs(_minutes(m.group(1)) - _minutes(hhmm(nxt))) <= 2:
                cands.append(e)
        if len(cands) == 1:
            row["folder"], row["matched_by"] = cands[0], "renamed within 2 minutes of the next launch"
            claimed.add(cands[0])
    for rows in result.values():
        for row in rows:
            row["folder_exists"] = row["folder"] in existing
    unmapped = sorted(e for e in existing if tracked(re.sub(r"_FAILED_ATTEMPT.*$", "", e)) and e not in claimed)
    return {"attempts": result, "unmapped": unmapped, "skips": skips}


def pending_items(attempts: dict) -> list:
    """Names with an attempt still to come: one running, or fewer launches than the queue was given."""
    out = []
    for name, rows in sorted(attempts.items()):
        cap = ATTEMPT_CAP.get(name, 1)
        if is_open(rows[-1]):
            out.append({"name": name, "why": "attempt %d is %s" % (len(rows), "running or has no finish line yet"
                                                                    if rows[-1]["status"] == "in_progress"
                                                                    else "finished but its YAML is not converted yet")})
        elif len(rows) < cap:
            out.append({"name": name, "why": "%d of %d attempts launched" % (len(rows), cap)})
    return out


# --------------------------------------------------------------------------
# Validity (A2.1 as made exact by the Note) and rows
# --------------------------------------------------------------------------

def attempt_validity(acc: dict, finish_reason: str | None) -> dict:
    """A2.1 from one acceptance entry. The queue reason is read per attempt, because a renamed folder
    no longer carries it in the checker's own name-keyed table."""
    capped_reason = bool(finish_reason and CAP_REASON.match(finish_reason))
    complete = bool(acc.get("exploration_complete"))
    stop = complete or capped_reason
    clean = acc.get("out_of_memory_lines") == 0 and acc.get("nvblox_died_lines") == 0
    grew = bool(acc.get("final_differs_from_first"))
    why = []
    if not stop:
        why.append("no 'Exploration complete' and no 250 m / 4 h stop")
    if not clean:
        why.append("roslaunch.log shows out of memory or nvblox_node dead" if acc.get("out_of_memory_lines") is not None
                   else "no roslaunch.log")
    if not grew:
        why.append("final graph0 equals stage-0 graph0" if acc.get("final_differs_from_first") is not None
                   else "no graph")
    return {"valid": bool(stop and clean and grew), "exploration_complete": complete,
            "capped": bool(capped_reason and not complete), "why_invalid": why}


def classify(attempt_map: dict, acceptance: dict) -> dict:
    """Per e7 seed: each attempt's validity, the counted attempt, and the paper_compare rows.

    The counted attempt is the LAST LAUNCHED one, once it has finished and is converted, if it is
    valid (A2.2). Every other invalid attempt keeps its own crashed row; a valid earlier attempt
    stays in no row. An open attempt is left out of everything.
    """
    acc_by = {r["run"]: r for r in acceptance["runs"]}
    seeds, rows = [], {}
    for name, atts in sorted(attempt_map.items()):
        m = E7_RE.match(name)
        if not m:
            continue
        scene, seed = m.group(1), int(m.group(2))
        info = {"name": name, "scene": scene, "seed": seed, "attempts": [], "counted": None, "state": None}
        for a in atts:
            rec = {"attempt": a["attempt"], "folder": a["folder"], "status": a["status"],
                   "finish_reason": a["finish_reason"]}
            acc = acc_by.get(a["folder"]) if a["folder"] else None
            if is_open(a):
                rec["valid"] = None
            elif acc is None:
                rec["valid"], rec["why_invalid"] = None, ["no acceptance entry for this folder"]
            else:
                rec.update(attempt_validity(acc, a["finish_reason"]))
                rec["checker_valid"] = acc.get("valid")
                rec["end_navigation_time_s_checker"] = acc.get("end_navigation_time_s")
            info["attempts"].append(rec)
        # A2.2: only the last launched attempt can count, and only once it has finished and its
        # YAML is converted. No earlier attempt takes its place.
        last = atts[-1]
        if (not is_open(last) and last["folder_exists"]
                and info["attempts"][-1].get("valid")):
            info["counted"] = last["attempt"]
        cap = ATTEMPT_CAP.get(name, 1)
        if info["counted"] is not None:
            info["state"] = "valid"
        elif is_open(last) or len(atts) < cap:
            info["state"] = "pending"
        else:
            info["state"] = "missing"
        for rec in info["attempts"]:
            if rec["valid"] is None:
                continue                      # open, or no acceptance entry: in no row
            if rec["attempt"] == info["counted"]:
                rows.setdefault("frontier_end", []).append((scene, rec["folder"]))
            elif rec["valid"]:
                rec["superseded_valid"] = True    # valid, but not the last launch: in no row (A2.2)
            else:
                arm = CRASH_ARM.get(rec["attempt"], "crashed_frontier_%dth" % rec["attempt"])
                rows.setdefault(arm, []).append((scene, rec["folder"]))
        seeds.append(info)
    return {"seeds": seeds, "rows": rows}


# --------------------------------------------------------------------------
# Budget B
# --------------------------------------------------------------------------

def median_of(values: list) -> float:
    """Median; an even count takes the mean of the two middle values."""
    v = sorted(values)
    n = len(v)
    return float(v[n // 2]) if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def compute_budget(scene: str, runs: list, fallback: float) -> dict:
    """The Note to Amendment 2, A2.3. `runs` hold the valid runs of the scene: run, end_s,
    exploration_complete, capped.

    Primary B: median end time of valid runs that logged "Exploration complete". A valid run
    stopped by a cap does not enter. Fewer than 2 such runs: the registered fallback.
    Second line: capped valid runs enter at their stop time.
    """
    primary = [r for r in runs if r["exploration_complete"] and not r["capped"]]
    alt = list(runs)

    def pick(rs):
        return (median_of([r["end_s"] for r in rs]), "median") if len(rs) >= 2 else (float(fallback), "fallback")

    b, rule = pick(primary)
    b2, rule2 = pick(alt)
    return {"scene": scene, "primary_s": b, "primary_rule": rule, "n_primary": len(primary),
            "primary_runs": [r["run"] for r in primary],
            "with_capped_s": b2, "with_capped_rule": rule2, "n_with_capped": len(alt),
            "capped_runs": [r["run"] for r in runs if r["capped"]],
            "fallback_s": float(fallback), "second_line_differs": not math.isclose(b, b2, rel_tol=0, abs_tol=1e-9)}


# --------------------------------------------------------------------------
# Tours: frozen test, C2
# --------------------------------------------------------------------------

def _yaml_nodes(path) -> list:
    import paper_compare as pc
    import yaml
    with open(path) as f:
        return (yaml.load(f, Loader=pc._LOADER) or {}).get("nodes", []) or []


def object_set(path) -> frozenset:
    """Object nodes as the A2.4 test reads them: name and centre as written."""
    return frozenset((str(n.get("name")), str(n.get("position"))) for n in _yaml_nodes(path)
                     if n.get("node_type") == "object")


def graph_stages(run_dir: Path) -> list:
    sd = Path(run_dir) / "stages"
    out = [int(e.name) for e in sd.iterdir() if e.name.isdigit()
           and (e / "habitat_scene_graph_original_graph0.yaml").exists()] if sd.is_dir() else []
    return sorted(out)


def tour_counts(run_dir: Path) -> dict:
    """Object nodes at stage 0 and at the last stage with a graph, as the checker counts them
    (every object node) and as the F1 counts them (doors left out), plus the local frozen test."""
    import paper_compare as pc
    st = graph_stages(run_dir)
    if not st:
        return {"error": "no graph0 in the local copy"}
    g = lambda s: Path(run_dir) / "stages" / str(s) / "habitat_scene_graph_original_graph0.yaml"
    return {"first_stage": st[0], "final_stage": st[-1],
            "object_nodes_first": len(object_set(g(st[0]))), "object_nodes_final": len(object_set(g(st[-1]))),
            "f1_objects_first": len(pc.parse_objects(g(st[0]))), "f1_objects_final": len(pc.parse_objects(g(st[-1]))),
            "frozen_local": object_set(g(st[0])) == object_set(g(st[-1]))}


def c2_status(b_attempts: list, acc_by: dict) -> dict:
    """Whether C2 can be computed for one scene (A2.5 and the Note's A2.4/A2.5 cases)."""
    last = b_attempts[-1]
    if is_open(last):
        return {"status": "in_progress", "folder": None, "attempt": last["attempt"]}
    if not last["folder_exists"]:
        return {"status": "no_folder", "folder": last["folder"], "attempt": last["attempt"]}
    acc = acc_by.get(last["folder"])
    if acc is None:
        return {"status": "no_acceptance_entry", "folder": last["folder"]}
    base = {"folder": last["folder"], "attempt": last["attempt"], "frozen": acc.get("frozen"),
            "meets_80_percent_rule": acc.get("meets_80_percent_rule"),
            "nvblox_died_lines": acc.get("nvblox_died_lines"), "timeout_lines": acc.get("timeout_lines"),
            "last_stop_whose_graph_changed": acc.get("last_stop_whose_graph_changed"),
            "objects_first": acc.get("objects_first"), "objects_final": acc.get("objects_final")}
    if acc.get("frozen"):
        cap = ATTEMPT_CAP.get(b_attempts[-1]["name"], 1)
        return dict(base, status="awaiting_rerun" if len(b_attempts) < cap else "not_computable_frozen_again")
    if not acc.get("meets_80_percent_rule"):
        return dict(base, status="below_80_percent_rule")
    return dict(base, status="compute")


def compute_c2(apr_a: Path, apr_b: Path) -> dict:
    """F1 of APR-b's final graph0 (prediction) against APR-a's final graph0 (reference), the author's rule."""
    import paper_compare as pc
    ga, gb = pc.resolve_reference_yaml(apr_a), pc.resolve_reference_yaml(apr_b)
    ref, pred = pc.parse_objects(ga), pc.parse_objects(gb)
    f1, p, r = pc.f1_score(ref, pred)
    return {"apr_a_graph": str(ga), "apr_b_graph": str(gb), "apr_a_sha256": sha256_file(ga), "apr_b_sha256": sha256_file(gb),
            "f1": f1, "precision": p, "recall": r, "n_objects_apr_a": len(ref), "n_objects_apr_b": len(pred),
            "below_0_90": f1 < 0.90,
            "reading": ("below 0.90: the reference moves by more than the paper's margins (2.7-7.9 points), "
                        "but this C2 also holds APR-a's damage" if f1 < 0.90 else "at or above 0.90")}


# --------------------------------------------------------------------------
# GED: reuse by stage list, compute the rest on the host
# --------------------------------------------------------------------------

def stage_rows_local(run_dir: Path) -> list:
    """The stages paper_ged.py would score: stats with a path length, and at least one graph."""
    sd = Path(run_dir) / "stages"
    rows = []
    if not sd.is_dir():
        return rows
    for name in sorted((e.name for e in sd.iterdir() if e.name.isdigit()), key=int):
        d = sd / name
        ns = d / "navigation_stats.json"
        if not ns.exists():
            continue
        try:
            stats = json.loads(ns.read_text())
        except ValueError:
            continue
        if stats.get("total_path_length_meters") is None:
            continue
        if not any((d / f"habitat_scene_graph_original_graph{g}.yaml").exists() for g in (0, 1)):
            continue
        rows.append({"stage": int(name), "path_m": stats["total_path_length_meters"],
                     "nav_s": stats.get("total_navigation_time_seconds")})
    return rows


def same_stage_list(a: list, b: list, tol: float = 1e-9) -> bool:
    def close(x, y):
        return x == y if x is None or y is None else math.isclose(x, y, rel_tol=0, abs_tol=tol)
    if len(a) != len(b):
        return False
    for x, y in zip(sorted(a, key=lambda r: int(r["stage"])), sorted(b, key=lambda r: int(r["stage"]))):
        if int(x["stage"]) != int(y["stage"]) or not close(x["path_m"], y["path_m"]) or not close(x["nav_s"], y["nav_s"]):
            return False
    return True


def load_ged_pool(files: list) -> dict:
    """basename -> {"scene", "rows": {stage: row}, "run_dir"}, rows of one run merged across files."""
    pool, refs = {}, []
    for f in files:
        data = json.loads(Path(f).read_text())
        refs.append({"file": str(f), "references": data.get("references", [])})
        for run in data["runs"]:
            ent = pool.setdefault(Path(run["run_dir"]).name, {"scene": run["scene"], "run_dir": run["run_dir"], "rows": {}})
            for row in run["stages"]:
                ent["rows"].setdefault(int(row["stage"]), {}).update(row)
    return {"runs": pool, "refs": refs}


def ged_keys_for(scene: str) -> set:
    return {"ged_hm3d", "ged_frontier_made", "ged_apr"}


def plan_ged(wanted: list, pool: dict, local_rows) -> tuple:
    """wanted: [{"folder", "scene", "path"}]. Returns (reuse, compute).

    An old GED entry is reused when its stage list (stage, path length, time) equals the local one
    and every row holds the three GED keys. The match is by content, never by folder name: the queue
    reuses the plain folder name for the next attempt.
    """
    reuse, compute = [], []
    e7_entries = {n: e for n, e in pool["runs"].items() if n.startswith("e7_")}
    for w in wanted:
        local = local_rows(w["path"])
        if not local:          # an attempt that made no stage has nothing to score: never sent to the host
            continue
        hit = None
        leaf = Path(w["folder"]).name
        for n in sorted(e7_entries, key=lambda n: (n != leaf, n)):
            ent = e7_entries[n]
            if ent["scene"] != w["scene"]:
                continue
            rows = [ent["rows"][s] for s in sorted(ent["rows"])]
            if local and same_stage_list(rows, local) and all(ged_keys_for(w["scene"]) <= set(r) for r in rows):
                hit = n
                break
        if hit:
            reuse.append(dict(w, from_entry=hit, same_name=(hit == leaf)))
        else:
            compute.append(w)
    return reuse, compute


def build_ged_file(pool: dict, reuse: list, computed: dict) -> dict:
    """One file for --ged-json: old entries of every non-e7 run unchanged, and exactly one entry per
    scored e7 run, from reuse or from a new computation. No stale entry can share a folder name."""
    runs = []
    for n, ent in sorted(pool["runs"].items()):
        if not n.startswith("e7_"):
            runs.append({"run_dir": ent["run_dir"], "scene": ent["scene"], "stages": [ent["rows"][s] for s in sorted(ent["rows"])]})
    for w in reuse:
        ent = pool["runs"][w["from_entry"]]
        runs.append({"run_dir": f"/workspace/runs/{w['folder']}", "scene": w["scene"],
                     "stages": [ent["rows"][s] for s in sorted(ent["rows"])],
                     "reused_from": f"{w['from_entry']} (stage list equal)"})
    for folder, ent in sorted(computed.items()):
        runs.append({"run_dir": f"/workspace/runs/{folder}", "scene": ent["scene"], "stages": ent["stages"],
                     "computed": "paper_ged.py on the host, 1113"})
    return {"method": "author ged_score_plot.CustomGED(1,1,1,1), gmatch4py scratch install; "
                      "old values reused by stage list, new values computed 1113", "runs": runs}


def ged_host_script(refs: list, run_specs: list, stamp: str, vlimit_kb: int = 8388608) -> str:
    """The script fed to `docker exec -i <container> bash -s`: one nice'd CPU process."""
    args = " ".join(["--ref " + shlex.quote(r) for r in refs] + [shlex.quote(s) for s in run_specs])
    f = f"paper_ged_new_1113_{stamp}"
    return f"""set -u
cd /workspace/scratch
echo $$ > {f}.pid
ulimit -v {vlimit_kb}
export SETUPTOOLS_USE_DISTUTILS=stdlib PYTHONPATH=/workspace/scratch/gm MPLBACKEND=Agg OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
nice -n 19 /workspace/environments/semantic_perception/bin/python -B paper_ged.py {args} > {f}.json 2> {f}.err
echo $? > {f}.rc
"""


def ged_start_cmd(script: str) -> str:
    """Start the job detached in the container. The call returns at once, so a dropped ssh cannot
    leave a job running unseen, and a retry cannot start a second copy without a check first."""
    return f"docker exec -d {CONTAINER} bash -c {shlex.quote(script)}"


def ged_state_cmd(stamp: str) -> str:
    f = f"{WS}/scratch/paper_ged_new_1113_{stamp}"
    return (f"if [ -f {f}.rc ]; then echo \"RC $(cat {f}.rc)\"; "
            f"elif [ -f {f}.pid ] && docker exec {CONTAINER} test -d /proc/$(cat {f}.pid); then echo RUNNING; "
            f"elif [ -f {f}.pid ]; then echo DEAD; else echo NOTSTARTED; fi")


def parse_ged_state(out: str) -> tuple:
    w = out.strip().split()
    if w and w[0] == "RC" and len(w) > 1 and w[1].lstrip("-").isdigit():
        return ("done", int(w[1]))
    return ({"RUNNING": "running", "DEAD": "dead"}.get(w[0] if w else "", "notstarted"), None)


def run_ged_job(script: str, stamp: str, log=None, poll_s: int = 15, max_wait_s: int = 7200, sleep=time.sleep) -> str:
    """Start the GED job once, then watch its rc file. After an ssh failure, look for the job's pid and
    rc files before any second start. Returns the host path of the JSON, or raises."""
    def state():
        return parse_ged_state(ssh(ged_state_cmd(stamp)).stdout)

    try:
        ssh(ged_start_cmd(script), retries=1, timeout=120)
    except HostError:
        sleep(30)                                   # the start may have gone through: look first
        if state()[0] == "notstarted":
            sleep(30)
            if state()[0] == "notstarted":
                ssh(ged_start_cmd(script), retries=1, timeout=120)    # one more start, and only now
    waited, quiet = 0, 0
    while waited <= max_wait_s:
        st, rc = state()
        if st == "done":
            if rc != 0:
                raise HostError(f"GED on the host ended with rc={rc}; see scratch/paper_ged_new_1113_{stamp}.err")
            return f"{WS}/scratch/paper_ged_new_1113_{stamp}.json"
        if st == "dead":
            raise HostError("the GED job on the host is gone with no rc file; it was not started again. "
                            f"Look at scratch/paper_ged_new_1113_{stamp}.err")
        quiet = quiet + 1 if st == "notstarted" else 0
        if quiet > 8:
            raise HostError("the GED job never started on the host")
        sleep(poll_s)
        waited += poll_s
    raise HostError("the GED job did not finish in time; it was not stopped and not restarted")


# --------------------------------------------------------------------------
# Copy
# --------------------------------------------------------------------------

def rsync_rules(folders: list) -> list:
    rules = []
    for g in sorted({f.split("/")[0] for f in folders}):
        rules.append(f"--include=/{g}/")
    for f in sorted(folders):
        for suffix in ("/", "/stages/", "/stages/*/", "/stages/*/habitat_scene_graph_original_graph*.yaml",
                       "/stages/*/navigation_stats.json", "/config/", "/config/tour_summary.json", "/config/waypoints.json"):
            rules.append(f"--include=/{f}{suffix}")
    rules.append("--exclude=*")
    return rules


def check_transfer_list(lines: list, allowed=None) -> list:
    """Read the file list of a dry run. Raise on any file outside the include list, and on any dsg file."""
    allowed = allowed or ALLOWED_FILES
    files = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(("Transfer starting", "sent ", "total size", "building file list")) or " bytes" in line:
            continue
        if line.endswith("/") or line == ".":
            continue
        base = line.rsplit("/", 1)[-1]
        if "dsg" in line.lower() or not allowed.match(base):
            raise ValueError(f"the rsync file list holds a file outside the include list: {line!r}")
        files.append(line)
    return files


def rsync_cmd(folders: list, dry: bool, dest: Path | None = None, rules: list | None = None) -> list:
    cmd = ["rsync", "-rt", "-v"] + (["-n"] if dry else []) + (rules if rules is not None else rsync_rules(folders))
    return cmd + ["-e", "ssh -o BatchMode=yes -o ConnectTimeout=20", f"{HOST}:{WS}/runs/", str(dest or NEW_COPY) + "/"]


def state_key(events: list, existing) -> tuple:
    """What the queue did, as one comparable value: every launch, finish, skip and conversion line,
    and the folders that exist. A rename shows up as a changed folder set."""
    return (tuple((e["kind"], e["name"], e["ts"], e["rest"]) for e in events), frozenset(existing))


def _local_marker(folder: str):
    p = NEW_COPY / folder / ".rescore_attempt.json"
    try:
        return json.loads(p.read_text()) if p.exists() else None
    except ValueError:
        return None


def folders_to_copy(attempts: dict) -> list:
    """Settled attempts whose local folder is not already a settled copy of that same launch.
    Open attempts (running, or finished with no conversion yet) are never copied."""
    out = []
    for rows in attempts.values():
        for a in rows:
            if not a["folder"] or is_open(a):
                continue
            m = _local_marker(a["folder"])
            if not (m and m.get("launch_ts") == a["launch_ts"] and m.get("settled") is True):
                out.append(a["folder"])
    return sorted(set(out))


def _run_rsync(cmd: list, dry: bool):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=3600)


def copy_settled(folders: list, attempts, stamp: str, before: tuple, fetch_state, run_rsync=_run_rsync,
                 rules_fn=None, allowed=None) -> list:
    """Copy into a staging folder, read the queue again, and merge only if nothing changed.

    `before` is (events, existing) read before the copy. A launch, a finish, a conversion or a
    rename during the copy stops the run with the local copy untouched, so files of a new attempt
    never land in the folder of an old one. `attempts` None means no launch markers (the e8 runs);
    `rules_fn` and `allowed` swap in the e8 include list and file names."""
    if not folders:
        return []
    rules = rules_fn(folders) if rules_fn else None
    staging = NEW_COPY / f"_incoming_{stamp}"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    try:
        dry = run_rsync(rsync_cmd(folders, True, staging, rules), True)
        if dry.returncode != 0:
            raise HostError("rsync dry run failed: " + dry.stderr[:500])
        files = check_transfer_list(dry.stdout.splitlines(), allowed)
        real = run_rsync(rsync_cmd(folders, False, staging, rules), False)
        if real.returncode != 0:
            raise HostError("rsync failed: " + real.stderr[:500])
        check_transfer_list(real.stdout.splitlines(), allowed)
        after = fetch_state()
        if state_key(*after) != state_key(*before):
            raise HostError("the queue launched, finished, converted or renamed something during the copy "
                            "(it changed during the copy); nothing was merged into the local copy. Run again.")
        launch = ({a["folder"]: a for rows in attempts.values() for a in rows if a["folder"]}
                  if attempts is not None else {})
        for f in folders:
            src = staging / f
            if src.exists():
                shutil.copytree(src, NEW_COPY / f, dirs_exist_ok=True)
            if attempts is not None:
                a = launch[f]
                (NEW_COPY / f).mkdir(parents=True, exist_ok=True)
                (NEW_COPY / f / ".rescore_attempt.json").write_text(
                    json.dumps({"name": a["name"], "launch_ts": a["launch_ts"], "attempt": a["attempt"], "settled": True}))
        # the e8 folders and markers sit directly under live_campaign/: bring the markers too
        if attempts is None:
            for m in (staging / "live_campaign").glob("EXCLUDED_*.json") if (staging / "live_campaign").is_dir() else []:
                (NEW_COPY / "live_campaign").mkdir(parents=True, exist_ok=True)
                shutil.copy2(m, NEW_COPY / "live_campaign" / m.name)
        return files
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def tree_fingerprint(folder: Path) -> str:
    """One hash over the YAML, stats and tour files of a run folder (path and content)."""
    h = hashlib.sha256()
    for p in sorted(Path(folder).rglob("*")):
        if p.is_file() and ALLOWED_FILES.match(p.name):
            h.update(str(p.relative_to(folder)).encode() + b"\0" + sha256_file(p).encode() + b"\n")
    return h.hexdigest()


def reconcile_local_copy(attempt_map: dict, stamp: str) -> list:
    """The queue moves a plain folder aside and a new attempt takes the name. The laptop copy keeps a
    marker per folder (.rescore_attempt.json, the launch time of its content). Before a sync, a folder
    whose marker names another launch is renamed to where that launch now lives, so no sync mixes two attempts."""
    moves = []
    by_launch = {(a["name"], a["launch_ts"]): a for rows in attempt_map.values() for a in rows}
    for rows in attempt_map.values():
        for a in rows:
            if not a["folder"]:
                continue
            local = NEW_COPY / a["folder"]
            marker = local / ".rescore_attempt.json"
            if not local.is_dir():
                continue
            if not marker.exists():
                dest = local.with_name(f"_stale_{stamp}_{local.name}")
                local.rename(dest)
                moves.append({"from": str(local), "to": str(dest), "why": "no marker"})
                continue
            have = json.loads(marker.read_text())
            if have.get("launch_ts") == a["launch_ts"]:
                continue
            owner = by_launch.get((have.get("name"), have.get("launch_ts")))
            target = NEW_COPY / owner["folder"] if owner and owner["folder"] else None
            if target is not None and not target.exists():
                local.rename(target)
                moves.append({"from": str(local), "to": str(target), "why": "its content is attempt %d" % owner["attempt"]})
            else:
                dest = local.with_name(f"_stale_{stamp}_{local.name}")
                local.rename(dest)
                moves.append({"from": str(local), "to": str(dest), "why": "owner folder not found or taken"})
    return moves


# --------------------------------------------------------------------------
# The November ASP runs (Amendment 3, its Note): listing, copy, validity
# --------------------------------------------------------------------------

def parse_e8_listing(text: str) -> dict:
    """The e8 runs, running-markers and EXCLUDED markers in runs/live_campaign/, picked only by the
    anchored name pattern. A dry run (dryrun_e8_...) matches nothing. After an `=====AGES=====` line the
    host's clock and each marker's modification time give the marker's age on the host's own clock."""
    import paper_compare as pc
    text, _, ages_text = text.partition("=====AGES=====\n")
    names = [l.strip() for l in text.splitlines() if l.strip()]
    runs = sorted({n for n in names if pc.NOV_RE.match(n)})
    active = sorted({n[len(".active_"):] for n in names if n.startswith(".active_") and pc.NOV_RE.match(n[len(".active_"):])})
    excluded = sorted({n[len("EXCLUDED_"):-len(".json")] for n in names
                       if n.startswith("EXCLUDED_") and n.endswith(".json") and pc.NOV_RE.match(n[len("EXCLUDED_"):-len(".json")])})
    ages = {}
    lines = [l.split() for l in ages_text.splitlines() if l.strip()]
    if lines and len(lines[0]) == 1 and lines[0][0].isdigit():
        now = int(lines[0][0])
        for w in lines[1:]:
            if len(w) == 2 and w[0].startswith(".active_") and w[1].isdigit() and w[0][len(".active_"):] in active:
                ages[w[0][len(".active_"):]] = now - int(w[1])
    return {"runs": runs, "active": active, "excluded": excluded, "ages_s": ages,
            "stale": sorted(n for n, a in ages.items() if a > STALE_MARKER_S)}


def e8_state(listing: dict) -> tuple:
    """The listing as the (events, existing) pair that state_key compares."""
    return ([], frozenset(listing["runs"]) | {".active_" + a for a in listing["active"]}
            | {"EXCLUDED_" + e for e in listing["excluded"]})


def e8_copy_folders(listing: dict) -> list:
    """Runs the runner no longer holds. A running one is never copied."""
    return ["live_campaign/" + r for r in listing["runs"] if r not in listing["active"]]


def e8_rsync_rules(folders: list, excluded: list) -> list:
    """The include list for e8 runs: stats and graphs, the policy log (members dropped), usage.jsonl (provider
    and model of each call), roslaunch.log, and the EXCLUDED markers. Never a dsg file, never prompts_responses."""
    rules = ["--include=/live_campaign/"]
    for f in sorted(folders):
        for suffix in ("/", "/stages/", "/stages/*/", "/stages/*/habitat_scene_graph_original_graph*.yaml",
                       "/stages/*/navigation_stats.json", "/stages/*/live_policy.jsonl", "/logs/", "/logs/roslaunch.log",
                       "/prompts/", "/prompts/usage.jsonl", "/EXCLUDED_*.json"):
            rules.append(f"--include=/{f}{suffix}")
    for e in sorted(excluded):
        rules.append(f"--include=/live_campaign/EXCLUDED_{e}.json")
    rules.append("--exclude=*")
    return rules


def fetch_e8_listing() -> dict:
    p = ssh(f"cd {WS}/runs/live_campaign && (ls -1A | grep e8_ ; true) && echo '=====AGES=====' && date +%s "
            f"&& (stat -c '%n %Y' .active_e8_* 2>/dev/null ; true)")
    if p.returncode != 0:
        raise HostError("cannot list runs/live_campaign: " + p.stderr[:300])
    return parse_e8_listing(p.stdout)


def check_nov_b(pipeline_b: float) -> None:
    """A3.3: B for the November runs is fixed at 632.1751 s. The pipeline's B must agree, or the row stops."""
    if abs(pipeline_b - NOV_B_S) > NOV_B_PIN_TOL:
        raise HostError(f"B for 853 in this run is {pipeline_b!r} s, but A3.3 fixes it at {NOV_B_S} s for the November runs "
                        f"(tolerance {NOV_B_PIN_TOL}); the November row is not scored")


def _jsonl_first_bad(path: Path):
    """Line number of the first line that is not JSON (blank lines are skipped), or None; and the count of good lines."""
    good = 0
    for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except ValueError:
            return i, good
        good += 1
    return None, good


def e8_runs_to_assess(camp_dir: Path, listing: dict) -> tuple:
    """(names to assess, originals that never started). One folder per seed: a relaunch beside an original that
    holds a stage stops the run with an error that names both."""
    import paper_compare as pc
    try:
        kept = pc.check_nov_pairs([Path(camp_dir) / r for r in listing["runs"]])
    except ValueError as e:
        raise HostError(str(e))
    names = [p.name for p in kept]
    return names, [r for r in listing["runs"] if r not in names]


def assess_e8(run_dir: Path, B: float, campaign_dir: Path | None = None, active: bool = False) -> dict:
    """One November run under A3.2 and its Note.

    reached_b: the last stage that holds navigation_stats.json and both graph files shows a navigation time
    of at least B (B is the caller's; the pipeline holds it). A run that did not reach B keeps its 10% and 50%
    values. A run that fails (b) or (c) is left out of every cell and listed with the reason:
    (b) roslaunch.log holds no 'out of memory' line and no 'nvblox_node has died' line (the e7 check's own
    grep_count); (c) no EXCLUDED marker (in the run, or in the campaign folder as the runner writes it), every
    call served by DeepInfra with the pinned model, not more than half the ensemble members dropped (the
    runner's own gates, imported)."""
    import check_paper_runs as cpr
    import paper_compare as pc
    check_nov_b(B)
    run_dir = Path(run_dir)
    res = {"run": run_dir.name, "open": bool(active), "reached_b": False, "end_s": None, "end_stage": None,
           "counts_in_cells": False, "reasons": [], "notes": []}
    if active:
        res["notes"].append("the runner still holds this run (.active marker): not scored")
        return res
    if not run_dir.is_dir():
        res["reasons"].append("the run folder is not in the local copy")
        return res
    stages, _, _ = pc.load_stages(run_dir, [])
    full = [s for s in stages if len(s["graphs"]) == 2]
    if full:
        res["end_s"], res["end_stage"] = full[-1]["time_s"], full[-1]["stage"]
    res["reached_b"] = bool(full and res["end_s"] >= NOV_B_S)      # "at least 632.1751 s": no slack
    if not res["reached_b"]:
        res["notes"].append("ended before B" + (f" ({res['end_s']:.1f} s)" if res["end_s"] is not None else "")
                            + ": no 100% value, the 10% and 50% values stay")
    rl = str(run_dir / "logs" / "roslaunch.log")
    oom = cpr.grep_count(rl, r"out of memory")
    died = cpr.grep_count(rl, r"nvblox_node.*(process has died|has died)")
    if oom is None:
        res["reasons"].append("no logs/roslaunch.log: the GPU check cannot be made")
    else:
        if oom:
            res["reasons"].append(f"roslaunch.log holds {oom} 'out of memory' line(s)")
        if died:
            res["reasons"].append("roslaunch.log says nvblox_node has died")
    markers = sorted(run_dir.glob("EXCLUDED_*"))
    if campaign_dir is not None and (Path(campaign_dir) / f"EXCLUDED_{run_dir.name}.json").exists():
        markers.append(Path(campaign_dir) / f"EXCLUDED_{run_dir.name}.json")
    for m in markers:
        try:
            why = json.loads(m.read_text()).get("reason", "no reason given")
        except ValueError:
            why = "unreadable marker"
        res["reasons"].append(f"EXCLUDED marker: {why}")
    # The runner's own gates read these files leniently (a bad line ends the read, a missing file passes). On a
    # finished copy that would hide a failure, so each file is checked first and a bad copy fails closed.
    usage = run_dir / "prompts" / "usage.jsonl"
    if not usage.is_file():
        res["reasons"].append("no prompts/usage.jsonl: the provider and model of the calls cannot be checked")
    else:
        bad_line, good = _jsonl_first_bad(usage)
        if bad_line is not None:
            res["reasons"].append(f"cannot check: prompts/usage.jsonl line {bad_line} is not valid JSON, so the calls after it are unread")
        elif good == 0:
            res["reasons"].append("cannot check: prompts/usage.jsonl holds no call")
        else:
            bad = Runner.provider_violations(run_dir)
            if bad:
                res["reasons"].append(f"{len(bad)} call(s) served by another provider or model than {REQUIRED_PROVIDER} / {REQUIRED_MODEL_TAG}")
    policy = sorted(run_dir.glob("stages/*/live_policy.jsonl"))
    unreadable = None
    for f in policy:
        bad_line, _ = _jsonl_first_bad(f)
        if bad_line is not None:
            unreadable = f"cannot check: stages/{f.parent.name}/live_policy.jsonl line {bad_line} is not valid JSON, so members dropped are miscounted"
            break
    slots, available = Runner.member_stats(run_dir)
    if not policy:
        res["reasons"].append("cannot check: no stages/*/live_policy.jsonl, so members dropped are unknown")
    elif unreadable:
        res["reasons"].append(unreadable)
    elif slots == 0:
        res["reasons"].append("cannot check: live_policy.jsonl holds no member count")
    elif slots >= MIN_STAGES_FOR_DROP_GATE * ENSEMBLE_SLOTS and 1 - available / slots > MAX_DROPPED_FRACTION:
        res["reasons"].append(f"more than half of the ensemble members dropped ({100 * (1 - available / slots):.0f}%)")
    res["counts_in_cells"] = not res["reasons"]
    return res


def build_score_argv(out_dir: Path, rows: dict, budgets: dict, budget_key: str, ged_file: Path, nov_paths: list) -> list:
    """The paper_compare.py command. With no November run on the host it is the command written before the arm."""
    argv = [sys.executable, str(LIVE / "paper_compare.py"), "--out-dir", str(out_dir)]
    first = ("frontier_end", "crashed_frontier_1st", "crashed_frontier_rerun", "crashed_frontier_3rd")
    for arm in first:
        for scene, folder in sorted(rows.get(arm, [])):
            argv += ["--add-run", f"{arm}={scene}={NEW_COPY / folder}"]
    for arm in sorted(set(rows) - set(first)):
        for scene, folder in sorted(rows[arm]):
            argv += ["--add-run", f"{arm}={scene}={NEW_COPY / folder}"]
    for p in nov_paths:
        argv += ["--add-run", f"official_nov={NOV_SCENE}={p}"]
    for scene in SCENES:
        argv += ["--apr", f"{scene}={NEW_COPY / 'apr' / f'apr_{scene}_a'}", "--budget", f"{scene}={budgets[scene][budget_key]!r}"]
    return argv + ["--ged-json", str(ged_file)]


# --------------------------------------------------------------------------
# Output text
# --------------------------------------------------------------------------

def mark_interim_rows(md: str, scenes: dict) -> str:
    """Tag every table row of an interim scene, so no cell reads as final."""
    out = []
    for line in md.splitlines():
        for scene, label in scenes.items():
            if line.startswith(f"| {scene} |"):
                line = line.replace(f"| {scene} |", f"| {scene} ({label}) |", 1)
        out.append(line)
    return "\n".join(out) + "\n"


def compare_cells(old: dict, new: dict, scenes, tol: float = 1e-9) -> dict:
    """Cell by cell, old paper_compare.json against new, for the given scenes."""
    key = lambda c: (c["scene"], c["arm"], c["reference"], c["variant"], c["fraction"])
    o = {key(c): c for c in old["cells"] if c["scene"] in scenes}
    n = {key(c): c for c in new["cells"] if c["scene"] in scenes}
    out = {s: {"compared": 0, "identical": 0, "different": [], "only_in_1112": [], "only_in_1113": []} for s in scenes}

    def same(x, y):
        if x is None or y is None:
            return x is y
        return math.isclose(x, y, rel_tol=0, abs_tol=tol)

    for k in sorted(set(o) | set(n)):
        scene = k[0]
        if k not in n:
            out[scene]["only_in_1112"].append(list(k))
        elif k not in o:
            out[scene]["only_in_1113"].append(list(k))
        else:
            out[scene]["compared"] += 1
            diffs = []
            if o[k]["n_runs"] != n[k]["n_runs"]:
                diffs.append(("n_runs", o[k]["n_runs"], n[k]["n_runs"]))
            for field in ("stage_value_x100", "running_max_x100", "ged"):
                for stat in ("mean", "min", "max", "n"):
                    if not same(o[k][field][stat], n[k][field][stat]):
                        diffs.append((f"{field}.{stat}", o[k][field][stat], n[k][field][stat]))
            if diffs:
                out[scene]["different"].append({"cell": list(k), "diffs": diffs})
            else:
                out[scene]["identical"] += 1
    return out


def describe_unmapped(folder: str, acc: dict | None) -> dict:
    """A folder the queue log never launched (an attempt from before the log), from its acceptance entry."""
    leaf = folder.split("/", 1)[-1]
    m = re.match(r"e7_(\d{5})_s(\d+)_", leaf)
    acc = acc or {}
    n_graph = acc.get("n_stages_with_graph")
    oom, died = acc.get("out_of_memory_lines"), acc.get("nvblox_died_lines")
    made = ("made no stage graph" if not n_graph else f"made {n_graph} stage graphs")
    d = {"folder": folder, "scene": m.group(1) if m else None, "seed": int(m.group(2)) if m else None,
         "oom_lines": oom, "nvblox_died_lines": died, "graph_stages": n_graph}
    d["sentence"] = (f"The folder `{leaf}` holds an attempt from before the queue log (11-06) that {made}: its roslaunch.log "
                     f"shows {oom} out-of-memory line(s) and {died} line(s) saying nvblox_node died. The queue log has no launch "
                     f"line for it, so it is in no row. " + (f"Seed {int(m.group(2))} of {m.group(1)} is scored from its later attempt."
                                                              if m else ""))
    return d


def tour_table(tours: dict) -> str:
    """A2.4: for every tour, whether nvblox died, the 'Timeout! Did not find' lines, the last archived stop
    whose graph changed, and the object-node counts at stage 0 and at the end."""
    lines = ["| Tour folder | Attempt | Frozen | nvblox died | Timeout lines | Last stop whose graph changed | "
             "Objects, stage 0 | Objects, end | Waypoints reached/listed |", "|---|---|---|---|---|---|---|---|---|"]
    yn = lambda v: "n/a" if v is None else ("yes" if v else "no")
    for folder, t in sorted(tours.items()):
        died = t.get("nvblox_died_lines")
        last = t.get("last_stop_whose_graph_changed")
        wp = (f"{t['waypoints_reached']}/{t['waypoints_listed']}" if t.get("waypoints_listed") is not None else "n/a")
        lines.append(f"| `{folder.split('/', 1)[-1]}` | {t.get('attempt')} | {yn(t.get('checker_frozen'))} | "
                     f"{'n/a' if died is None else ('yes' if died else 'no')} | {t.get('timeout_lines')} | "
                     f"{'none' if last is None else last} | {t.get('object_nodes_first')} | {t.get('object_nodes_final')} | {wp} |")
    return "\n".join(lines)


def table_deviation_46(attempt_map: dict) -> str:
    """The markdown table that completes deviation 46: every e7 871 seed and every tour."""
    def cell(rows, k, cap):
        if k <= len(rows):
            a = rows[k - 1]
            leaf = a["folder"].split("/", 1)[1] if a["folder"] else "(no folder)"
            state = {"in_progress": "running", "converting": "finished, not converted yet",
                     "no_finish_line": "no finish line"}.get(a["status"], "finished")
            ok = "" if a["folder_exists"] else ", folder missing"
            return f"`{leaf}` ({state}{ok})"
        return "not launched yet (queued)" if k <= cap else "none"

    lines = ["| Run | Attempt 1 | Attempt 2 | Attempt 3 |", "|---|---|---|---|"]
    for name in sorted(attempt_map):
        m = E7_RE.match(name)
        t = TOUR_RE.match(name)
        if not ((m and m.group(1) == "00871") or t):
            continue
        label = (f"e7 {m.group(1)} s{m.group(2)}" if m else f"APR-{t.group(2)} {t.group(1)}")
        cap = ATTEMPT_CAP.get(name, 1)
        rows = attempt_map[name]
        lines.append(f"| {label} | " + " | ".join(cell(rows, k, cap) if k <= max(cap, len(rows)) else "none" for k in (1, 2, 3)) + " |")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# The pipeline
# --------------------------------------------------------------------------

class Log:
    def __init__(self, path: Path):
        self.path = path

    def __call__(self, step: str, **kw):
        rec = {"t": now_iso(), "step": step, **kw}
        with open(self.path, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        print(f"[{rec['t']}] {step} " + " ".join(f"{k}={v}" for k, v in kw.items() if not isinstance(v, (dict, list))), flush=True)


def fetch_queue_state() -> tuple:
    """(event lines, existing folder set), read in one ssh call."""
    p = ssh(f"cat {QUEUE_LOG}; echo '=====LISTING====='; cd {WS}/runs && ls -1d apr/* frontier_seeds/*")
    if p.returncode != 0:
        raise HostError("cannot read the queue log: " + p.stderr[:300])
    text, listing = p.stdout.split("=====LISTING=====\n", 1)
    events = parse_queue_log(text)
    existing = {l.strip() for l in listing.splitlines() if l.strip()}
    return events, existing


def decide_mode(requested: str, scene_state: dict, pend: list) -> str:
    """auto: final when no attempt is pending, else interim. final refuses while one is pending."""
    complete = all(v["complete"] for v in scene_state.values())
    if requested == "auto":
        return "final" if complete else "interim"
    if requested == "final" and not complete:
        raise HostError("--mode final, but these attempts are still to come: " + json.dumps(pend))
    return requested


def launch_signature(events: list) -> list:
    return [(e["name"], e["ts"]) for e in events if e["kind"] == "launch"]


def run_pipeline(args) -> int:
    import paper_compare as pc
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ged").mkdir(exist_ok=True)
    log = Log(out / "rescore_log.jsonl")
    old_json = json.loads((OLD_OUT / "paper_compare.json").read_text())
    old_budgets = old_json["meta"]["budgets"]

    # 1 acceptance, filed before anything is scored
    events_a, existing_a = fetch_queue_state()
    p = ssh(f"python3 - {WS}", stdin_text=CHECKER.read_text(), timeout=1800)
    if p.returncode != 0:
        raise HostError("check_paper_runs.py failed on the host: " + p.stderr[:500])
    acceptance = json.loads(p.stdout)
    events, existing = fetch_queue_state()
    if state_key(events, existing) != state_key(events_a, existing_a):
        raise HostError("the queue launched, finished, converted or renamed something while the acceptance check ran; run again")
    acc_path = out / f"acceptance_{stamp}.json"
    acc_path.write_text(p.stdout)
    (out / f"queue_events_{stamp}.txt").write_text("".join(
        f"{e['ts']} {e['kind']} {e['name']} {e['rest']}\n" for e in events))
    log("acceptance", file=acc_path.name, sha256=sha256_file(acc_path), n_runs=len(acceptance["runs"]))
    acc_by = {r["run"]: r for r in acceptance["runs"]}

    # 2 folder map
    fm = folder_map(events, existing)
    attempts = fm["attempts"]
    missing = [a["folder"] or f"{a['name']} attempt {a['attempt']}" for rows in attempts.values() for a in rows if not a["folder_exists"]]
    if missing:
        raise HostError("no host folder found for: " + ", ".join(missing))
    pend = pending_items(attempts)
    table46 = table_deviation_46(attempts)
    pre_queue = [describe_unmapped(f, acc_by.get(f)) for f in fm["unmapped"]]
    (out / f"folder_map_{stamp}.json").write_text(json.dumps(
        {"made_at": now_iso(), "rule": "latest launch keeps the plain name; an older attempt sits in "
         "<name>_FAILED_ATTEMPT_<HHMM of the next launch>; an attempt counts as open until the queue logs "
         "`converted ... of <name>` after its `finished` line", "attempts": attempts, "unmapped_folders": fm["unmapped"],
         "pre_queue_attempts": pre_queue, "skips": fm["skips"], "pending": pend}, indent=1))
    (out / f"folder_map_{stamp}.md").write_text(table46 + "\n" + "".join(
        f"\nNot in the queue log: {p_['sentence']}\n" for p_ in pre_queue))
    log("folder_map", pending=len(pend), unmapped=len(fm["unmapped"]))
    print("\n" + table46 + "\n")
    for p_ in pre_queue:
        print("For the deviations file: " + deviation_sentence(p_) + "\n")

    # 3 copy: into a staging folder, merged only if the queue did not move during the copy
    folders = sorted({a["folder"] for rows in attempts.values() for a in rows if not is_open(a)})
    moves = []
    if not args.no_copy:
        NEW_COPY.mkdir(parents=True, exist_ok=True)
        moves = reconcile_local_copy(attempts, stamp)
        to_copy = folders_to_copy(attempts)
        files = copy_settled(to_copy, attempts, stamp, (events, existing), fetch_queue_state)
        (out / f"rsync_dryrun_{stamp}.txt").write_text("\n".join(files) + ("\n" if files else ""))
        log("rsync", folders_copied=len(to_copy), files=len(files), moves=len(moves),
            list=f"rsync_dryrun_{stamp}.txt")
    # the November runs (Amendment 3): listed and copied only if there are any
    e8_list = fetch_e8_listing()
    if e8_list["runs"] and not args.no_copy:
        f8 = e8_copy_folders(e8_list)
        files8 = copy_settled(f8, None, stamp + "_e8", e8_state(e8_list), lambda: e8_state(fetch_e8_listing()),
                              rules_fn=lambda fs: e8_rsync_rules(fs, e8_list["excluded"]), allowed=ALLOWED_E8)
        (out / f"rsync_dryrun_e8_{stamp}.txt").write_text("\n".join(files8) + ("\n" if files8 else ""))
        log("rsync_e8", runs=len(f8), files=len(files8))
    old_fp = {d.name: tree_fingerprint(d) for g in ("apr", "frontier_seeds") if (OLD_COPY / g).is_dir()
              for d in (OLD_COPY / g).iterdir() if d.is_dir()}
    copy_check = {}
    for f in folders:
        fp = tree_fingerprint(NEW_COPY / f)
        same = sorted(n for n, h in old_fp.items() if h == fp)
        copy_check[f] = {"equals_old_copy_folder": same}
    # for every folder an old copy holds, its content must reappear in the new copy under the folder the map names
    log("copy_check", folders=len(copy_check), new_content=sum(1 for v in copy_check.values() if not v["equals_old_copy_folder"]))

    # 4 C2, before any run is scored
    tour_status, c2 = {}, {}
    for scene in SCENES:
        b_name = f"apr/apr_{scene}_b"
        a_name = f"apr/apr_{scene}_a"
        st = c2_status(attempts[b_name], acc_by) if b_name in attempts else {"status": "no_tour"}
        tour_status[scene] = st
        if st["status"] == "compute":
            res = compute_c2(NEW_COPY / a_name, NEW_COPY / st["folder"])
            c2[scene] = dict(st, **res)
        else:
            c2[scene] = dict(st, f1=None)
    tours = {}
    for name, rows in sorted(attempts.items()):
        if TOUR_RE.match(name):
            for a in rows:
                if is_open(a):
                    continue
                tours[a["folder"]] = dict(tour_counts(NEW_COPY / a["folder"]),
                                          attempt=a["attempt"], launch_ts=a["launch_ts"],
                                          waypoints_reached=acc_by.get(a["folder"], {}).get("waypoints_reached"),
                                          waypoints_listed=acc_by.get(a["folder"], {}).get("waypoints_listed"),
                                          checker_frozen=acc_by.get(a["folder"], {}).get("frozen"),
                                          nvblox_died_lines=acc_by.get(a["folder"], {}).get("nvblox_died_lines"),
                                          timeout_lines=acc_by.get(a["folder"], {}).get("timeout_lines"),
                                          last_stop_whose_graph_changed=acc_by.get(a["folder"], {}).get("last_stop_whose_graph_changed"),
                                          meets_80_percent_rule=acc_by.get(a["folder"], {}).get("meets_80_percent_rule"))
    c2_path = out / f"c2_{stamp}.json"
    c2_path.write_text(json.dumps({"written_at": now_iso(), "written_before": "any rescoring in this pipeline run",
                                   "rule": "PREREGISTRATION_PAPER.md Amendment 2 A2.5 and the Note: F1 (section 1) of APR-b's final graph0 "
                                           "against APR-a's final graph0, for a scene whose APR-b is not frozen and meets the 80% rule",
                                   "damage_note": DAMAGE_NOTE, "scenes": c2, "tours": tours}, indent=1))
    log("c2", file=c2_path.name, sha256=sha256_file(c2_path),
        **{f"status_{s}": c2[s]["status"] for s in SCENES}, **{f"f1_{s}": c2[s].get("f1") for s in SCENES})

    # 5 budget B
    cls = classify(attempts, acceptance)
    budgets = {}
    for scene in SCENES:
        runs = []
        for s in cls["seeds"]:
            if s["scene"] != scene or s["counted"] is None:
                continue
            rec = s["attempts"][s["counted"] - 1]
            stages, _, _ = pc.load_stages(NEW_COPY / rec["folder"], [])
            end_s = stages[-1]["time_s"]
            if rec.get("end_navigation_time_s_checker") is not None and abs(end_s - rec["end_navigation_time_s_checker"]) > 0.006:
                log("budget_end_time_differs", run=rec["folder"], local=end_s, checker=rec["end_navigation_time_s_checker"])
            runs.append({"run": rec["folder"], "end_s": end_s, "exploration_complete": rec["exploration_complete"], "capped": rec["capped"]})
        budgets[scene] = compute_budget(scene, runs, pc.DEFAULT_BUDGET[scene])
        budgets[scene]["end_times_s"] = {r["run"]: r["end_s"] for r in runs}
        budgets[scene]["b_1112_s"] = old_budgets.get(scene)
    (out / f"budgets_{stamp}.json").write_text(json.dumps(budgets, indent=1))
    log("budget", **{f"B_{s}": budgets[s]["primary_s"] for s in SCENES}, **{f"rule_{s}": budgets[s]["primary_rule"] for s in SCENES})

    # the November runs, judged with the B held above
    nov = None
    if e8_list["runs"]:
        camp8 = NEW_COPY / "live_campaign"
        check_nov_b(budgets[NOV_SCENE]["primary_s"])
        names8, never8 = e8_runs_to_assess(camp8, e8_list)
        assessed = [assess_e8(camp8 / r, budgets[NOV_SCENE]["primary_s"], camp8, active=(r in e8_list["active"]))
                    for r in names8]
        nov = {"B_s": NOV_B_S, "runs": assessed, "listing": e8_list, "never_started": never8}
        log("e8", runs=len(assessed), counted=sum(a["counts_in_cells"] for a in assessed),
            reached_b=sum(a["reached_b"] for a in assessed))
    nov_paths = [NEW_COPY / "live_campaign" / a["run"] for a in (nov["runs"] if nov else []) if a["counts_in_cells"]]

    # scene state and mode
    pend_names = {p_["name"] for p_ in pend}
    scene_state = {}
    for scene in SCENES:
        e7_pending = [n for n in pend_names if E7_RE.match(n) and E7_RE.match(n).group(1) == scene]
        tour_pending = [n for n in pend_names if TOUR_RE.match(n) and TOUR_RE.match(n).group(1) == scene]
        scene_state[scene] = {"e7_pending": sorted(e7_pending), "tours_pending": sorted(tour_pending),
                              "complete": not e7_pending and not tour_pending}
    mode = decide_mode(args.mode, scene_state, pend)

    # 6 GED
    wanted = []
    for arm, items in cls["rows"].items():
        for scene, folder in items:
            wanted.append({"folder": folder, "scene": scene, "path": NEW_COPY / folder, "arm": arm})
    for p_ in nov_paths:
        wanted.append({"folder": f"live_campaign/{p_.name}", "scene": NOV_SCENE, "path": p_, "arm": "official_nov"})
    pool = load_ged_pool(OLD_GED_FILES)
    reuse, compute = plan_ged(wanted, pool, stage_rows_local)
    no_stage = [w["folder"] for w in wanted if not stage_rows_local(w["path"])]
    if no_stage:
        log("ged_no_stages", runs=no_stage)
    recheck = sorted(reuse, key=lambda w: len(stage_rows_local(w["path"])))[:max(0, args.ged_recheck)]
    to_run = compute + recheck
    new_rows, recheck_report = {}, []
    if to_run:
        e7_refs = next((r["references"] for r in pool["refs"] if r["file"].endswith("paper_ged_e7_1112.json")), [])
        if not e7_refs:
            raise HostError("no reference list in paper_ged_e7_1112.json")
        shost = subprocess.run(["sha256sum", str(LIVE / "paper_ged.py")], capture_output=True, text=True).stdout.split()[0]
        hsum = ssh(f"sha256sum {WS}/scratch/paper_ged.py").stdout.split()
        if not hsum or hsum[0] != shost:
            raise HostError("the host's scratch/paper_ged.py differs from the repo copy; stop and report")
        specs = [f"/workspace/runs/{w['folder']}={w['scene']}" for w in to_run]
        log("ged_host_start", n_runs=len(specs), runs=[w["folder"] for w in to_run])
        json_path = run_ged_job(ged_host_script(e7_refs, specs, stamp), stamp)
        got = ssh(f"cat {json_path}")
        data = json.loads(got.stdout)
        (out / "ged" / f"paper_ged_new_1113_{stamp}.json").write_text(got.stdout)
        for run in data["runs"]:
            new_rows[Path(run["run_dir"]).parent.name + "/" + Path(run["run_dir"]).name] = run
        log("ged_host_done", n_runs=len(data["runs"]))
        for w in recheck:                                   # does the old value reproduce?
            fresh = new_rows[w["folder"]]
            old = pool["runs"][w["from_entry"]]["rows"]
            worst = 0.0
            for row in fresh["stages"]:
                for k, v in row.items():
                    if k.startswith("ged_"):
                        worst = max(worst, abs(v - old[int(row["stage"])][k]))
            recheck_report.append({"run": w["folder"], "stages": len(fresh["stages"]), "max_abs_diff": worst})
    computed = {w["folder"]: {"scene": w["scene"], "stages": new_rows[w["folder"]]["stages"]} for w in compute}
    ged_file = out / "ged" / "ged_for_scoring.json"
    ged_file.write_text(json.dumps(build_ged_file(pool, reuse, computed), indent=1))
    log("ged_file", reused=len(reuse), computed=len(compute), recheck=json.dumps(recheck_report))

    # 7 score
    def score(out_dir: Path, budget_key: str) -> None:
        argv = build_score_argv(out_dir, cls["rows"], budgets, budget_key, ged_file, nov_paths)
        r = subprocess.run(argv, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(LIVE.parent)})
        if r.returncode != 0:
            raise HostError("paper_compare.py failed: " + r.stderr[-800:])

    archive_previous(out, stamp)
    raw = out / "_paper_compare_raw"
    shutil.rmtree(raw, ignore_errors=True)
    score(raw, "primary_s")
    new_json = json.loads((raw / "paper_compare.json").read_text())
    (out / "paper_compare.json").write_text((raw / "paper_compare.json").read_text())
    md = (raw / "paper_compare.md").read_text()
    shutil.rmtree(raw)
    labels = {s: "interim: awaiting the third attempts" for s in SCENES if mode == "interim" and scene_state[s]["e7_pending"]}
    labels.update({s: "interim: awaiting the APR-b rerun" for s in SCENES
                   if mode == "interim" and s not in labels and scene_state[s]["tours_pending"]})
    banner = ["<!-- written by rescore_paper.py; the figures are paper_compare.py's own output -->", "",
              f"**{mode.capitalize()} rescore, written {now_iso()}.** Budget B per scene: "
              + ", ".join(f"{s} = {budgets[s]['primary_s']:.4f} s ({budgets[s]['primary_rule']}, n = {budgets[s]['n_primary']})" for s in SCENES) + "."]
    for s in SCENES:
        banner.append(f"- {s}: " + (labels[s] if s in labels else "final") + ".")
    (out / "paper_compare.md").write_text("\n".join(banner) + "\n\n" + mark_interim_rows(md, labels))
    alt_done = False
    if any(budgets[s]["second_line_differs"] for s in SCENES):
        score(out / "alt_B_with_capped", "with_capped_s")
        alt_done = True
    comparison = compare_cells(old_json, new_json, SCENES)
    for s in SCENES:
        comparison[s]["b_1112_s"], comparison[s]["b_1113_s"] = old_budgets.get(s), budgets[s]["primary_s"]
        comparison[s]["b_changed"] = not math.isclose(old_budgets.get(s), budgets[s]["primary_s"], rel_tol=0, abs_tol=1e-9)
    (out / "comparison_vs_1112.json").write_text(json.dumps(comparison, indent=1))
    log("score", mode=mode, **{f"cells_diff_{s}": len(comparison[s]["different"]) for s in SCENES},
        **{f"cells_same_{s}": comparison[s]["identical"] for s in SCENES})

    # 8 outputs
    summary = {"written_at": now_iso(), "stamp": stamp, "mode": mode, "acceptance_file": acc_path.name,
               "c2_file": c2_path.name, "scene_state": scene_state, "pending": pend, "budgets": budgets,
               "c2": c2, "tours": tours, "classification": cls, "copy_moves": moves, "copy_check": copy_check,
               "ged": {"reused": [dict(w, path=str(w["path"])) for w in reuse], "computed": [w["folder"] for w in compute],
                       "recheck": recheck_report}, "comparison_vs_1112": {s: {k: v for k, v in comparison[s].items() if k != "different"}
                                                                          | {"n_different": len(comparison[s]["different"])} for s in SCENES},
               "alt_B_scored": alt_done, "deviation_46_table": table46, "unmapped_folders": fm["unmapped"], "skips": fm["skips"],
               "pre_queue": pre_queue, "deviation_sentences": [deviation_sentence(p_) for p_ in pre_queue]}
    if nov:
        summary["nov"] = nov
    (out / "rescore_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    (out / "NOTES.md").write_text(write_notes(summary, comparison, old_budgets, pc))
    log("done", mode=mode, out=str(out))
    print("\n" + table46)
    return 0


def archive_previous(out: Path, stamp: str) -> None:
    """Keep the last run's unstamped outputs before they are overwritten."""
    names = ["paper_compare.json", "paper_compare.md", "NOTES.md", "rescore_summary.json", "comparison_vs_1112.json"]
    have = [out / n for n in names if (out / n).exists()]
    if have:
        dest = out / f"previous_{stamp}"
        dest.mkdir(exist_ok=True)
        for p in have:
            shutil.copy2(p, dest / p.name)
        if (out / "alt_B_with_capped").exists():
            shutil.copytree(out / "alt_B_with_capped", dest / "alt_B_with_capped", dirs_exist_ok=True)
            shutil.rmtree(out / "alt_B_with_capped")


# --------------------------------------------------------------------------
# NOTES.md
# --------------------------------------------------------------------------

def fmt_c2(s: dict) -> str:
    st = s["status"]
    if st == "compute":
        died = "nvblox did not die during it" if s.get("nvblox_died_lines") == 0 else "nvblox died during it"
        return (f"F1 {s['f1']:.4f} (precision {s['precision']:.4f}, recall {s['recall']:.4f}); APR-b holds "
                f"{s['n_objects_apr_b']} objects, APR-a {s['n_objects_apr_a']}; {died}. "
                + ("It is below 0.90, so the slide says the reference moves by more than the paper's margins (2.7-7.9 points), "
                   "and also says APR-a's damage is part of it." if s["below_0_90"] else
                   "It is at or above 0.90. APR-a's damage is still part of it, and the slide says so."))
    return {"awaiting_rerun": "not computed. The only APR-b run is frozen and its rerun has not run. C2 waits for it.",
            "not_computable_frozen_again": "not computable: the rerun is frozen too, and there is no further attempt.",
            "below_80_percent_rule": "not computed: the APR-b run misses the 80% use rule.",
            "in_progress": "not computed: the APR-b rerun is running (or finished and not yet converted). C2 waits for it.",
            "no_folder": "not computed: the folder of the APR-b run is missing.",
            }.get(st, st)


def _group_invalid(bad: list) -> str:
    """Invalid attempts grouped by their reasons, so one reason is said once."""
    groups = {}
    for name, a in bad:
        m = E7_RE.match(name)
        tag = f"{m.group(1)} s{m.group(2)} #{a['attempt']}" if m else name
        groups.setdefault(", ".join(a["why_invalid"]), []).append(tag)
    return "; ".join(f"{', '.join(v)}: {k}" for k, v in groups.items())


def deviation_sentence(pre: dict) -> str:
    """The text the lead adds to the deviations file for an attempt that the queue log does not hold."""
    return f"**11-06: an attempt of e7 {pre['scene']} seed {pre['seed']} that made no stage.** " + pre["sentence"]


def scene_vs_1112(sc: str, cmp_: dict, budgets: dict, rows: dict) -> str:
    """What differs from 11-12 for one scene, said from the comparison and never assumed."""
    d = cmp_[sc]
    n_new = len(d.get("only_in_1113", []))
    new_arms = sorted({c[1] for c in d.get("only_in_1113", [])})
    third = [f for s_, f in rows.get("crashed_frontier_3rd", []) if s_ == sc]
    head = f"{d['compared']} cells compared; {d['identical']} identical, {len(d['different'])} different."
    if d["b_changed"]:
        return (head + f" B moved, from {d.get('b_1112_s', float('nan')):.4f} s to {budgets[sc]['primary_s']:.4f} s, so the cells differ"
                + (f" and {n_new} cells are new ({', '.join(new_arms)})" if n_new else "")
                + f". Every {sc} number in `results_paper_compare_1112/` is superseded by this folder.")
    if not d["different"] and not n_new and not d.get("only_in_1112"):
        return head + " B did not move and the inputs match 11-12's, so these numbers equal 11-12's."
    txt = head + " B did not move."
    if n_new:
        txt += (f" {n_new} new cells appear, in {', '.join(new_arms)}"
                + (f" ({len(third)} third attempt(s) that fail A2.1; they stay out of every paper cell)" if "crashed_frontier_3rd" in new_arms else "") + ".")
    if d.get("only_in_1112"):
        txt += f" {len(d.get('only_in_1112', []))} cells of 11-12 have no counterpart now."
    return txt


def nov_notes(nov: dict) -> list:
    """The section on the November ASP row (Amendment 3). Written only when the host holds an e8 run."""
    runs = nov["runs"]
    counted = [a for a in runs if a["counts_in_cells"]]
    reached = [a for a in counted if a["reached_b"]]
    L = ["", "## November ASP row (Amendment 3)", "",
         f"The row \"ASP + DeepSeek, November\" holds `e8_00853_s42..44_official_105m` (a `_relaunch1` name where the rule gave one). "
         f"Its runs are never pooled with October's `official` arm: the two rows have their own n beside every cell. "
         f"B for 853 is {nov['B_s']:.4f} s, the same B as above. {len(counted)} of 3 runs count in the cells "
         f"({len(runs)} are on the host); {len(reached)} reached B and have a 100% value. A run that did not reach B keeps its "
         "10% and 50% values. A run that fails the GPU check or an E1 exclusion is left out of every cell and listed here. "
         "A `dryrun_e8_` folder is never scored.", ""]
    stale = nov.get("listing", {}).get("stale", [])
    if runs:
        L += ["| Run | State | Navigation time at its last full stage (s) | Reached B | In the cells | Left out because | Note |",
              "|---|---|---|---|---|---|---|"]
        for a in runs:
            state = ("running (stale marker: check by hand)" if a["run"] in stale else "running") if a["open"] else "finished"
            end = "n/a" if a["end_s"] is None else f"{a['end_s']:.1f}"
            L.append(f"| `{a['run']}` | {state} | {end} | {'yes' if a['reached_b'] else 'no'} | "
                     f"{'yes' if a['counts_in_cells'] else 'no'} | {'; '.join(a['reasons']) or '-'} | {'; '.join(a['notes']) or '-'} |")
    ages = nov.get("listing", {}).get("ages_s", {})
    for n in stale:
        L += ["", f"stale marker: check by hand: `.active_{n}` is {ages.get(n, 0) / 3600:.1f} h old on the host's clock "
                  f"(over {STALE_MARKER_S // 3600} h). The run stays unscored until the marker is gone."]
    if nov.get("never_started"):
        L += ["", "A relaunch replaces an original that never started (the Note to Amendment 3): "
              + ", ".join(f"`{n}`" for n in nov["never_started"]) + " holds no stage and is not scored."]
    return L


def write_notes(s: dict, cmp_: dict, old_budgets: dict, pc) -> str:
    """NOTES.md. Every sentence that depends on the state of the runs is generated from that state."""
    b = s["budgets"]
    rows = s["classification"].get("rows", {})
    state = s["scene_state"]
    interim = not all(v["complete"] for v in state.values())
    for sc in SCENES:                      # 11-12 budget for the move test
        cmp_[sc].setdefault("b_1112_s", old_budgets[sc])
    L = ["# Notes on the 13 Nov paper-scale rescore", ""]
    L.append(f"**State: {s['mode']}.** Written {s['written_at']}. Rerun with `bash tools/live_policy/host/rescore_paper.sh`. "
             "The rules are `PREREGISTRATION_PAPER.md`, Amendment 2 and its Note. Tables: `paper_compare.md` and `.json`. "
             "Evidence: `acceptance_*.json`, `folder_map_*`, `c2_*.json`, `budgets_*.json`, `comparison_vs_1112.json`, `rescore_summary.json`.")
    L += ["", "## What changed against 11-12, and why", ""]
    valid = [(x["name"], x["counted"]) for x in s["classification"]["seeds"] if x["counted"]]
    bad = [(x["name"], a) for x in s["classification"]["seeds"] for a in x["attempts"] if a.get("valid") is False]
    L.append(f"1. **Acceptance first.** `check_paper_runs.py` ran on the host before any score (`{s['acceptance_file']}`). "
             f"{len(valid)} e7 runs count as valid: " + ", ".join(sorted(n.split('e7_')[1].replace('_frontier_end', '') for n, _ in valid)) + ". "
             f"{len(bad)} other attempts fail A2.1 and stay out of every paper cell: " + _group_invalid(bad) + ".")
    L.append("2. **Budget B** is now set by script (A2.3). The primary B is the median end time of the valid runs that logged "
             "\"Exploration complete\"; fewer than 2 means the registered fallback. " + "; ".join(
                 f"{sc}: B = {b[sc]['primary_s']:.4f} s ({b[sc]['primary_rule']}, {b[sc]['n_primary']} valid run(s)); 11-12 used {old_budgets[sc]:.4f} s"
                 for sc in SCENES) + ". "
             + ("No valid run stopped at a cap, so the second line (B with capped runs) equals the primary."
                if not any(b[sc]["second_line_differs"] for sc in SCENES) else
                "A capped run changes the second line; it is scored in `alt_B_with_capped/`."))
    L.append(f"3. **C2** was computed and filed (`{s['c2_file']}`) before any run was scored. "
             + " ".join(f"{sc}: {fmt_c2(s['c2'][sc])}" for sc in SCENES) + " " + DAMAGE_NOTE)
    L.append("4. **Tours.** The table below gives, for every tour, whether nvblox died, the \"Timeout! Did not find\" lines, "
             "the last archived stop whose graph changed, and the object nodes at stage 0 and at the end (A2.4).")
    pre = s.get("pre_queue", [])
    L.append("5. **Folders.** The queue renames an older attempt to `*_FAILED_ATTEMPT_HHMM` when the next one launches, and HHMM is that "
             "launch's time. The map is in `folder_map_*.json`. The laptop copy for this run is `runs_1113/` beside the 11-12 `runs/`, "
             "which stays as it was: in the old copy the folder `apr_00853_b` holds the old frozen tour, which on the host now sits in "
             "`apr_00853_b_FAILED_ATTEMPT_1707`." + "".join(" " + p["sentence"] for p in pre))
    g = s["ged"]
    L.append(f"6. **GED.** {len(g['reused'])} runs reuse their 11-12 GED, because their stage list (stage, path length, time) is equal. "
             f"{len(g['computed'])} runs were computed on the host. Recheck of reused values on the host: "
             + (", ".join(f"`{r['run'].split('/')[1]}` max difference {r['max_abs_diff']:.3g} over {r['stages']} stages" for r in g["recheck"]) or "not asked for")
             + ". Reuse goes by content, not by folder name, because the queue gives the plain name to the next attempt.")
    for i, sc in enumerate(SCENES):
        L.append(f"{7 + i}. **{sc} against 11-12.** " + scene_vs_1112(sc, cmp_, b, rows))
    L += ["", "## Budgets", "",
          "| Scene | Primary B (s) | Rule | Valid runs with \"Exploration complete\" | B with capped runs (s) | 11-12 B (s) |",
          "|---|---|---|---|---|---|"]
    for sc in SCENES:
        L.append(f"| {sc} | {b[sc]['primary_s']:.4f} | {b[sc]['primary_rule']} | {b[sc]['n_primary']} | {b[sc]['with_capped_s']:.4f} | {old_budgets[sc]:.4f} |")
    if s.get("nov"):
        L += nov_notes(s["nov"])
    L += ["", "## Tours (A2.4)", "",
          "Object nodes count every object node, doors included, as the frozen test counts them (the F1 count, which leaves out doors, is in `c2_*.json`). "
          "Frozen means the final graph0 holds the same object nodes as stage 0.", "", tour_table(s["tours"])]
    L += ["", "## Status of the two scenes", ""]
    for sc in SCENES:
        v = state[sc]
        if v["complete"]:
            t = f"- **{sc}: final.**"
            if cmp_[sc]["b_changed"]:
                t += (f" B moved from {old_budgets[sc]:.4f} s to {b[sc]['primary_s']:.4f} s, so every {sc} number in "
                      f"`results_paper_compare_1112/` is **superseded** by this folder.")
            else:
                t += " B did not move."
            if b[sc]["primary_rule"] == "fallback":
                t += (f" B stays at the fallback, {b[sc]['primary_s']:.4f} s, because only {b[sc]['n_primary']} valid run(s) exist (A2.3).")
            L.append(t)
        else:
            wait = []
            if v["e7_pending"]:
                seeds = ", ".join(E7_RE.match(n).group(2) for n in v["e7_pending"])
                wait.append(f"the third attempts of seeds {seeds}")
            if v["tours_pending"]:
                wait.append("the APR-b rerun")
            L.append(f"- **{sc}: interim, awaiting {' and '.join(wait)}.** B is " + (
                "the registered fallback, from fewer than 2 valid runs. " if b[sc]["primary_rule"] == "fallback" else "set by the valid runs so far. ")
                + f"Every {sc} number in this folder is provisional. "
                + (f"The {sc} numbers in `results_paper_compare_1112/` are **superseded** as soon as B changes; until then they equal these."
                   if not cmp_[sc]["b_changed"] else f"The {sc} numbers in `results_paper_compare_1112/` are **superseded**: B changed."))
    L += ["", "## Carried over from 11-12 (`results_paper_compare_1112/NOTES.md`)", ""]
    L.append("- Item 1, order of the checks: C1-C5 were computed with the first scoring on 11-12 (deviation 42). Still true as history. This run files C2 first.")
    c2s = s["c2"]
    parts = []
    for sc in SCENES:
        st = c2s[sc]["status"]
        parts.append({"compute": f"superseded for {sc} by its APR-b rerun (F1 {c2s[sc].get('f1') if c2s[sc].get('f1') is None else format(c2s[sc]['f1'], '.4f')})",
                      "awaiting_rerun": f"still open for {sc} until its APR-b rerun runs",
                      "in_progress": f"open for {sc}: its APR-b rerun is running",
                      "not_computable_frozen_again": f"closed for {sc}: the rerun is frozen too, C2 is not computable, and there is no further attempt",
                      }.get(st, f"{sc}: {st}"))
    L.append("- Item 2, C2 not valid: " + "; ".join(parts) + ".")
    L.append("- Item 3, APR-a final graphs end about 60 s early: holds. APR-a is unchanged and stays the reference on both scenes.")
    died = sorted(k.split("/", 1)[1] for k, t in s["tours"].items() if t.get("nvblox_died_lines"))
    L.append("- Item 4, nvblox died partway through some tours: the tour table above gives it per tour"
             + (f" (died in {', '.join(died)})" if died else "") + ". APR-a is still used because the tours move on navmesh paths and Hydra kept growing the graph.")
    L.append("- Item 5, end times leave out the final leg: holds, and B uses the same rule for every run.")
    L.append("- Item 6, the 853 100% cell covers 3 of 5 runs: " + (
        f"holds while B is {b['00853']['primary_s']:.4f} s; read the n in each cell." if not cmp_["00853"]["b_changed"] else
        "B moved for 853, so read the n in each cell again."))
    cc = s.get("copy_check", {}).get("frontier_seeds/e7_00871_s44_frontier_end_FAILED_ATTEMPT_1358", {}).get("equals_old_copy_folder")
    L.append("- Item 7, stages without a graph take the graph of the stage before: holds for the crashed first attempt of seed 44 "
             + ("(its folder is unchanged since 11-12)." if cc else "(check the copy check in `rescore_summary.json`)."))
    L.append("- Item 8, GPU sharing: the Note to Amendment 2 corrects the statement (the first attempt of seed 42 launched under the 12 GB check), "
             "and so does deviation 40. The third attempts were queued under the 12 GB check (deviation 45); this pipeline does not test the GPU at launch.")
    L.append("- Item 9, C1 floor area far off: holds. C1, C3, C4 and C5 depend on APR-a only and are not recomputed (`results_paper_compare_1112/c_checks.json`).")
    L.append("- The frontier clock finding (11-12 NOTES, last section): holds, unchanged.")
    if pre:
        L += ["", "## For the deviations file", ""] + [deviation_sentence(p) for p in pre]
    if interim:
        L += ["", "## When the third attempts land", "",
              "Run the same command. It reads the queue log, maps the folders, copies, recomputes B and C2, and computes GED only for runs "
              "whose stage list has no 11-12 value. It refuses `--mode final` while an attempt is running, not yet converted, or not yet launched. "
              "Then the lead updates deviation 46 from `folder_map_*.md` and marks the 11-12 00871 numbers superseded."]
    return "\n".join(L) + "\n"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--mode", choices=["auto", "interim", "final"], default="auto",
                    help="auto: final only when no attempt is pending; final refuses when one is")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-copy", action="store_true", help="use the laptop copy as it is")
    ap.add_argument("--ged-recheck", type=int, default=0,
                    help="recompute this many reused GED runs on the host and compare (default 0: only when asked)")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run_pipeline(args)
    except HostError as e:
        print(f"STOP: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
