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


def parse_queue_log(text: str) -> list:
    """The launch, finished and skip lines, in order. ROS noise and other lines are dropped."""
    events = []
    for i, line in enumerate(text.splitlines()):
        m = EVENT_RE.match(line.strip())
        if m:
            events.append({"i": i, "ts": m.group(1), "kind": m.group(2), "name": m.group(3),
                           "rest": m.group(4).lstrip(": ").strip()})
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
            lst.append({"attempt": len(lst) + 1, "launch_ts": e["ts"], "finish_ts": None, "finish_reason": None})
        elif e["kind"] == "finished":
            lst = out.get(e["name"])
            if lst and lst[-1]["finish_reason"] is None:
                lst[-1]["finish_ts"], lst[-1]["finish_reason"] = e["ts"], e["rest"]
    return out


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
                row["status"] = "finished" if a["finish_reason"] is not None else "in_progress"
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
        if rows[-1]["status"] == "in_progress":
            out.append({"name": name, "why": "attempt %d is running or has no finish line yet" % len(rows)})
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

    The counted attempt is the latest finished one, if it is valid (A2.2). Every other finished
    attempt keeps its own crashed row. A running attempt is left out of everything.
    """
    acc_by = {r["run"]: r for r in acceptance["runs"]}
    seeds, rows = [], {}
    for name, atts in sorted(attempt_map.items()):
        m = E7_RE.match(name)
        if not m:
            continue
        scene, seed = m.group(1), int(m.group(2))
        info = {"name": name, "scene": scene, "seed": seed, "attempts": [], "counted": None, "state": None}
        finished = [a for a in atts if a["status"] != "in_progress" and a["folder_exists"]]
        for a in atts:
            rec = {"attempt": a["attempt"], "folder": a["folder"], "status": a["status"],
                   "finish_reason": a["finish_reason"]}
            acc = acc_by.get(a["folder"]) if a["folder"] else None
            if a["status"] == "in_progress":
                rec["valid"] = None
            elif acc is None:
                rec["valid"], rec["why_invalid"] = None, ["no acceptance entry for this folder"]
            else:
                rec.update(attempt_validity(acc, a["finish_reason"]))
                rec["checker_valid"] = acc.get("valid")
                rec["end_navigation_time_s_checker"] = acc.get("end_navigation_time_s")
            info["attempts"].append(rec)
        last = finished[-1] if finished else None
        if last is not None and info["attempts"][last["attempt"] - 1].get("valid"):
            info["counted"] = last["attempt"]
        cap = ATTEMPT_CAP.get(name, 1)
        running = atts[-1]["status"] == "in_progress"
        if info["counted"] is not None:
            info["state"] = "valid"
        elif running or len(atts) < cap:
            info["state"] = "pending"
        else:
            info["state"] = "missing"
        for rec in info["attempts"]:
            if rec["valid"] is None and rec["status"] == "in_progress":
                continue
            if rec["attempt"] == info["counted"]:
                rows.setdefault("frontier_end", []).append((scene, rec["folder"]))
            elif rec["valid"] is not None:
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
    done = [a for a in b_attempts if a["status"] != "in_progress" and a["folder_exists"]]
    if not done:
        return {"status": "in_progress", "folder": None}
    last = done[-1]
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
    return f"""set -u
cd /workspace/scratch
ulimit -v {vlimit_kb}
export SETUPTOOLS_USE_DISTUTILS=stdlib PYTHONPATH=/workspace/scratch/gm MPLBACKEND=Agg OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
nice -n 19 /workspace/environments/semantic_perception/bin/python -B paper_ged.py {args} > paper_ged_new_1113_{stamp}.json 2> paper_ged_new_1113_{stamp}.err
echo rc=$?
"""


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


def check_transfer_list(lines: list) -> list:
    """Read the file list of a dry run. Raise on any file outside the include list, and on any dsg file."""
    files = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(("Transfer starting", "sent ", "total size", "building file list")) or " bytes" in line:
            continue
        if line.endswith("/") or line == ".":
            continue
        base = line.rsplit("/", 1)[-1]
        if "dsg" in line.lower() or not ALLOWED_FILES.match(base):
            raise ValueError(f"the rsync file list holds a file outside the include list: {line!r}")
        files.append(line)
    return files


def rsync_cmd(folders: list, dry: bool) -> list:
    cmd = ["rsync", "-rt", "-v"] + (["-n"] if dry else []) + rsync_rules(folders)
    return cmd + ["-e", "ssh -o BatchMode=yes -o ConnectTimeout=20", f"{HOST}:{WS}/runs/", str(NEW_COPY) + "/"]


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


def table_deviation_46(attempt_map: dict) -> str:
    """The markdown table that completes deviation 46: every e7 871 seed and every tour."""
    def cell(rows, k, cap):
        if k <= len(rows):
            a = rows[k - 1]
            leaf = a["folder"].split("/", 1)[1] if a["folder"] else "(no folder)"
            state = {"in_progress": "running", "no_finish_line": "no finish line"}.get(a["status"], "finished")
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
    if launch_signature(events) != launch_signature(events_a) or existing != existing_a:
        raise HostError("the queue launched or renamed a folder while the acceptance check ran; run again")
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
    (out / f"folder_map_{stamp}.json").write_text(json.dumps(
        {"made_at": now_iso(), "rule": "latest launch keeps the plain name; an older attempt sits in "
         "<name>_FAILED_ATTEMPT_<HHMM of the next launch>", "attempts": attempts, "unmapped_folders": fm["unmapped"],
         "skips": fm["skips"], "pending": pend}, indent=1))
    (out / f"folder_map_{stamp}.md").write_text(table46 + "\n")
    log("folder_map", pending=len(pend), unmapped=len(fm["unmapped"]))
    print("\n" + table46 + "\n")

    # 3 copy
    folders = sorted({a["folder"] for rows in attempts.values() for a in rows if a["status"] != "in_progress"})
    moves = []
    if not args.no_copy:
        NEW_COPY.mkdir(parents=True, exist_ok=True)
        moves = reconcile_local_copy(attempts, stamp)
        dry = subprocess.run(rsync_cmd(folders, True), capture_output=True, text=True, timeout=1800)
        if dry.returncode != 0:
            raise HostError("rsync dry run failed: " + dry.stderr[:500])
        (out / f"rsync_dryrun_{stamp}.txt").write_text(dry.stdout)
        files = check_transfer_list(dry.stdout.splitlines())
        log("rsync_dry_run", files=len(files), list=f"rsync_dryrun_{stamp}.txt")
        real = subprocess.run(rsync_cmd(folders, False), capture_output=True, text=True, timeout=3600)
        if real.returncode != 0:
            raise HostError("rsync failed: " + real.stderr[:500])
        sent = check_transfer_list(real.stdout.splitlines())
        for rows in attempts.values():
            for a in rows:
                if a["folder"] in folders:
                    (NEW_COPY / a["folder"] / ".rescore_attempt.json").write_text(
                        json.dumps({"name": a["name"], "launch_ts": a["launch_ts"], "attempt": a["attempt"]}))
        log("rsync", files_listed=len(files), files_sent=len(sent), moves=len(moves))
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
                tours[a["folder"]] = dict(tour_counts(NEW_COPY / a["folder"]),
                                          attempt=a["attempt"], launch_ts=a["launch_ts"],
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
    pool = load_ged_pool(OLD_GED_FILES)
    reuse, compute = plan_ged(wanted, pool, stage_rows_local)
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
        res = ssh(f"docker exec -i {CONTAINER} bash -s", stdin_text=ged_host_script(e7_refs, specs, stamp), timeout=7200)
        if "rc=0" not in res.stdout:
            raise HostError("GED on the host failed: " + (res.stdout + res.stderr)[-500:])
        got = ssh(f"cat {WS}/scratch/paper_ged_new_1113_{stamp}.json")
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
        argv = [sys.executable, str(LIVE / "paper_compare.py"), "--out-dir", str(out_dir)]
        for arm in ("frontier_end", "crashed_frontier_1st", "crashed_frontier_rerun", "crashed_frontier_3rd"):
            for scene, folder in sorted(cls["rows"].get(arm, [])):
                argv += ["--add-run", f"{arm}={scene}={NEW_COPY / folder}"]
        for arm in sorted(set(cls["rows"]) - {"frontier_end", "crashed_frontier_1st", "crashed_frontier_rerun", "crashed_frontier_3rd"}):
            for scene, folder in sorted(cls["rows"][arm]):
                argv += ["--add-run", f"{arm}={scene}={NEW_COPY / folder}"]
        for scene in SCENES:
            argv += ["--apr", f"{scene}={NEW_COPY / 'apr' / f'apr_{scene}_a'}", "--budget", f"{scene}={budgets[scene][budget_key]!r}"]
        argv += ["--ged-json", str(ged_file)]
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
               "alt_B_scored": alt_done, "deviation_46_table": table46, "unmapped_folders": fm["unmapped"], "skips": fm["skips"]}
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
            "in_progress": "not computed: the APR-b run has not finished."}.get(st, st)


def _group_invalid(bad: list) -> str:
    """Invalid attempts grouped by their reasons, so one reason is said once."""
    groups = {}
    for name, a in bad:
        tag = f"s{E7_RE.match(name).group(2)} #{a['attempt']}" if E7_RE.match(name) else name
        groups.setdefault(", ".join(a["why_invalid"]), []).append(f"{E7_RE.match(name).group(1) if E7_RE.match(name) else ''} {tag}".strip())
    return "; ".join(f"{', '.join(v)}: {k}" for k, v in groups.items())


def write_notes(s: dict, cmp_: dict, old_budgets: dict, pc) -> str:
    mode = s["mode"]
    b = s["budgets"]
    L = []
    L.append("# Notes on the 13 Nov paper-scale rescore")
    L.append("")
    L.append(f"**State: {mode}.** Written {s['written_at']}. Rerun with `bash tools/live_policy/host/rescore_paper.sh`. "
             "The rules are `PREREGISTRATION_PAPER.md`, Amendment 2 and its Note. Tables: `paper_compare.md` and `.json`. "
             "Evidence: `acceptance_*.json`, `folder_map_*`, `c2_*.json`, `budgets_*.json`, `comparison_vs_1112.json`, `rescore_summary.json`.")
    L.append("")
    L.append("## What changed against 11-12, and why")
    L.append("")
    valid = [(x["name"], x["counted"]) for x in s["classification"]["seeds"] if x["counted"]]
    bad = [(x["name"], a) for x in s["classification"]["seeds"] for a in x["attempts"] if a.get("valid") is False]
    L.append(f"1. **Acceptance first.** `check_paper_runs.py` ran on the host before any score (`{s['acceptance_file']}`). "
             f"{len(valid)} e7 runs count as valid: " + ", ".join(sorted(n.split('e7_')[1].replace('_frontier_end', '') for n, _ in valid)) + ". "
             f"{len(bad)} other attempts fail A2.1 and stay out of every paper cell: " + _group_invalid(bad) + ".")
    L.append("2. **Budget B** is now set by script (A2.3). The primary B is the median end time of the valid runs that logged "
             "\"Exploration complete\"; fewer than 2 means the registered fallback. " + "; ".join(
                 f"{sc}: B = {b[sc]['primary_s']:.4f} s ({b[sc]['primary_rule']}, {b[sc]['n_primary']} run(s)); 11-12 used {old_budgets[sc]:.4f} s"
                 for sc in SCENES) + ". "
             + ("No valid run stopped at a cap, so the second line (B with capped runs) equals the primary."
                if not any(b[sc]["second_line_differs"] for sc in SCENES) else
                "A capped run changes the second line; it is scored in `alt_B_with_capped/`."))
    L.append("3. **C2** was computed and filed (`" + s["c2_file"] + "`) before any run was scored. 00853: " + fmt_c2(s["c2"]["00853"])
             + " 00871: " + fmt_c2(s["c2"]["00871"]) + " " + DAMAGE_NOTE)
    t = s["tours"]
    L.append("4. **Tours.** Object nodes at stage 0 and at the end (every object node, as the frozen test counts them; the F1 count, "
             "which leaves out doors, is in `c2_*.json`): " + "; ".join(
                 f"`{k.split('/')[1]}` {v.get('object_nodes_first')} to {v.get('object_nodes_final')}"
                 + (" (frozen)" if v.get("checker_frozen") else "") for k, v in sorted(t.items())) + ".")
    L.append("5. **Folders.** The queue renames an older attempt to `*_FAILED_ATTEMPT_HHMM` when the next one launches, and HHMM is that "
             "launch's time. The map is in `folder_map_*.json`. The laptop copy for this run is `runs_1113/` beside the 11-12 `runs/`, "
             "which stays as it was: in the old copy the folder `apr_00853_b` holds the old frozen tour, which on the host now sits in "
             "`apr_00853_b_FAILED_ATTEMPT_1707`.")
    g = s["ged"]
    L.append(f"6. **GED.** {len(g['reused'])} runs reuse their 11-12 GED, because their stage list (stage, path length, time) is equal. "
             f"{len(g['computed'])} runs were computed on the host. Recheck of reused values on the host: "
             + (", ".join(f"`{r['run'].split('/')[1]}` max difference {r['max_abs_diff']:.3g} over {r['stages']} stages" for r in g["recheck"]) or "none")
             + ". Reuse goes by content, not by folder name, because the queue gives the plain name to the next attempt.")
    d3, d7 = cmp_["00853"], cmp_["00871"]
    L.append(f"7. **00853 against 11-12.** {d3['compared']} cells compared; {d3['identical']} identical, {len(d3['different'])} different"
             + ("." if not d3["different"] else ": see `comparison_vs_1112.json`.") + f" B moved: {d3['b_changed']}."
             + (" Nothing changed for 00853 (same five valid runs, same B, same reference), so its numbers are final and equal 11-12's."
                if not d3["different"] and not d3["b_changed"] else ""))
    L.append(f"8. **00871 against 11-12.** {d7['compared']} cells compared; {d7['identical']} identical, {len(d7['different'])} different. B moved: {d7['b_changed']}. "
             + ("The inputs are the same as on 11-12 (one valid run, the fallback B, the same crashed attempts), so the numbers are the same, "
                "and they are interim." if not d7["different"] and not d7["b_changed"] else "See `comparison_vs_1112.json`."))
    L.append("")
    L.append("## Budgets")
    L.append("")
    L.append("| Scene | Primary B (s) | Rule | Valid runs with \"Exploration complete\" | B with capped runs (s) | 11-12 B (s) |")
    L.append("|---|---|---|---|---|---|")
    for sc in SCENES:
        L.append(f"| {sc} | {b[sc]['primary_s']:.4f} | {b[sc]['primary_rule']} | {b[sc]['n_primary']} | {b[sc]['with_capped_s']:.4f} | {old_budgets[sc]:.4f} |")
    L.append("")
    L.append("## Status of the two scenes")
    L.append("")
    for sc in SCENES:
        v = s["scene_state"][sc]
        if v["complete"]:
            L.append(f"- **{sc}: final.**" + (
                f" B moved from {old_budgets[sc]:.4f} s to {b[sc]['primary_s']:.4f} s, so every {sc} number in "
                f"`results_paper_compare_1112/` is **superseded** by this folder." if cmp_[sc]["b_changed"] else
                f" B did not move; the {sc} cells equal 11-12's."))
        else:
            wait = []
            if v["e7_pending"]:
                seeds = ", ".join(E7_RE.match(n).group(2) for n in v["e7_pending"])
                wait.append(f"the third attempts of seeds {seeds}")
            if v["tours_pending"]:
                wait.append("the APR-b rerun")
            L.append(f"- **{sc}: interim, awaiting {' and '.join(wait)}.** B is " + (
                "the registered fallback, from fewer than 2 valid runs. " if b[sc]["primary_rule"] == "fallback" else "set by the valid runs so far. ")
                + "Every 00871 number in this folder is provisional. "
                + ("The 00871 numbers in `results_paper_compare_1112/` are **superseded** as soon as B changes; until then they equal these."
                   if not cmp_[sc]["b_changed"] else "The 00871 numbers in `results_paper_compare_1112/` are **superseded**: B changed."))
    L.append("")
    L.append("## Carried over from 11-12 (`results_paper_compare_1112/NOTES.md`)")
    L.append("")
    L.append("- Item 1, order of the checks: C1-C5 were computed with the first scoring on 11-12 (deviation 42). Still true as history. This run files C2 first.")
    L.append("- Item 2, C2 not valid: superseded for 00853 by the rerun above. Still open for 00871 until its APR-b rerun runs.")
    L.append("- Item 3, APR-a final graphs end about 60 s early: holds. APR-a is unchanged and stays the reference on both scenes.")
    L.append("- Item 4, nvblox died partway through APR-a on both scenes and through APR-b on 00871: holds. The 00853 APR-b rerun is in the table above.")
    L.append("- Item 5, end times leave out the final leg: holds, and B uses the same rule for every run.")
    L.append("- Item 6, the 853 100% cell covers 3 of 5 runs: holds while B is 632.1751 s; read the n in each cell.")
    L.append("- Item 7, stages without a graph take the graph of the stage before: holds for the crashed first attempt of seed 44.")
    L.append("- Item 8, GPU sharing: corrected by deviation 40. The first attempt of seed 42 launched under the 12 GB check. The third attempts launch under it too.")
    L.append("- Item 9, C1 floor area far off: holds. C1, C3, C4 and C5 depend on APR-a only and are not recomputed (`results_paper_compare_1112/c_checks.json`).")
    L.append("- The frontier clock finding (11-12 NOTES, last section): holds, unchanged.")
    L.append("")
    L.append("## When the third attempts land")
    L.append("")
    L.append("Run the same command. It reads the queue log, maps the folders, copies, recomputes B and C2, and computes GED only for runs "
             "whose stage list has no 11-12 value. It refuses `--mode final` while an attempt is running or not yet launched. "
             "Then the lead updates deviation 46 from `folder_map_*.md` and marks the 11-12 00871 numbers superseded.")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--mode", choices=["auto", "interim", "final"], default="auto",
                    help="auto: final only when no attempt is pending; final refuses when one is")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-copy", action="store_true", help="use the laptop copy as it is")
    ap.add_argument("--ged-recheck", type=int, default=1,
                    help="recompute this many reused GED runs on the host and compare (default 1)")
    args = ap.parse_args(argv)
    try:
        return run_pipeline(args)
    except HostError as e:
        print(f"STOP: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
