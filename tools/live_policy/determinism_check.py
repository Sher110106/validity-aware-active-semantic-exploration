#!/usr/bin/env python3
"""Plan step 8 measures (PREREGISTRATION_DETERMINISM.md) for same-seed runs.

For every pair of runs in a group, at stages 0, 1 and 2:
- (a) maps match: in both tracks (habitat_scene_graph_original_graph{0,1}.yaml)
  the object label multisets are equal, and every object lies within 0.10 m
  (xy) of a same-label object in the other run, in both directions;
- (b) stops agree: the stop chosen at stage k (last point of
  stages/<k+1>/executed_path.json, world frame) lies within 0.25 m (xy).
Objects are nodes with node_type "object". A stage missing in either run is
reported as None.

Usage: determinism_check.py --replicates DIR... --baseline DIR... > out.json
"""
import argparse
import ast
import itertools
import json
import math
import os
import re
from collections import Counter

import yaml

STAGES = (0, 1, 2)
OBJ_TOL = 0.10
STOP_TOL = 0.25


def objects(run, k, g):
    p = os.path.join(run, "stages", str(k), f"habitat_scene_graph_original_graph{g}.yaml")
    if not os.path.exists(p):
        return None
    nodes = yaml.safe_load(open(p))["nodes"]
    return [(n["name"], ast.literal_eval(n["position"])[:2]) for n in nodes if n.get("node_type") == "object"]


def stop(run, k):
    p = os.path.join(run, "stages", str(k + 1), "executed_path.json")
    if not os.path.exists(p):
        return None
    path = json.load(open(p))["world_frame_path"]
    return path[-1][:2] if path else None


def nearest_same_label(a, b):
    """For each object in a, distance to the nearest same-label object in b."""
    out = []
    for name, xy in a:
        ds = [math.dist(xy, q) for n, q in b if n == name]
        out.append(min(ds) if ds else math.inf)
    return out


def compare_maps(r1, r2, k):
    tracks = []
    for g in (0, 1):
        a, b = objects(r1, k, g), objects(r2, k, g)
        if a is None or b is None:
            return None
        ca, cb = Counter(n for n, _ in a), Counter(n for n, _ in b)
        d = nearest_same_label(a, b) + nearest_same_label(b, a)
        tracks.append({
            "track": g, "n_objects": [len(a), len(b)],
            "labels_equal": ca == cb,
            "label_sym_diff": sum(((ca - cb) + (cb - ca)).values()),
            "share_within_tol": sum(x <= OBJ_TOL for x in d) / len(d) if d else 1.0,
            "max_nearest_m": (max(d) if math.isfinite(max(d)) else None) if d else 0.0,  # None: a label with no partner
            "all_within_tol": all(x <= OBJ_TOL for x in d),
        })
    return {"tracks": tracks, "pass": all(t["labels_equal"] and t["all_within_tol"] for t in tracks)}


def compare_stops(r1, r2, k):
    s1, s2 = stop(r1, k), stop(r2, k)
    if s1 is None or s2 is None:
        return None
    d = math.dist(s1, s2)
    return {"distance_m": d, "pass": d <= STOP_TOL}


def quiet_waits(run):
    """Extra seconds the quiet-snapshot rule waited, per snapshot. rospy writes the
    line to the node's rosout.log, which is copied into <run>/logs/ after the run."""
    p = os.path.join(run, "logs", "rosout.log")
    if not os.path.exists(p):
        return None
    return [float(m.group(1)) for m in re.finditer(r"Quiescent snapshot.*?after ([0-9.]+) s extra wait", open(p, errors="replace").read())]


def group(runs):
    pairs = []
    for r1, r2 in itertools.combinations(runs, 2):
        row = {"pair": [os.path.basename(r1.rstrip("/")), os.path.basename(r2.rstrip("/"))], "stages": {}}
        for k in STAGES:
            row["stages"][k] = {"a_maps": compare_maps(r1, r2, k), "b_stops": compare_stops(r1, r2, k)}
        s0 = row["stages"][0]
        row["stage0_pass"] = bool(s0["a_maps"] and s0["a_maps"]["pass"] and s0["b_stops"] and s0["b_stops"]["pass"])
        pairs.append(row)
    return {
        "runs": [os.path.basename(r.rstrip("/")) for r in runs],
        "quiet_waits_s": {os.path.basename(r.rstrip("/")): quiet_waits(r) for r in runs},
        "pairs": pairs,
        "all_pairs_stage0_pass": all(p["stage0_pass"] for p in pairs),
        "stage0_stop_distance_m": [p["stages"][0]["b_stops"]["distance_m"] if p["stages"][0]["b_stops"] else None for p in pairs],
        "stage0_share_within_tol": [
            [t["share_within_tol"] for t in p["stages"][0]["a_maps"]["tracks"]] if p["stages"][0]["a_maps"] else None
            for p in pairs],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicates", nargs="+", required=True)
    ap.add_argument("--baseline", nargs="+", required=True)
    args = ap.parse_args()
    rep, base = group(args.replicates), group(args.baseline)
    out = {
        "prereg": "PREREGISTRATION_DETERMINISM.md",
        "tolerances": {"object_xy_m": OBJ_TOL, "stop_xy_m": STOP_TOL},
        "replicates": rep,
        "baseline": base,
        "decision": "pair runs by seed" if rep["all_pairs_stage0_pass"]
                    else "plan at least 5 replicates per cell",
    }
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
