#!/usr/bin/env python3
"""In-run diagnostics for the live arms and the E3 gate (PREREGISTRATION_E3.md).

Stage alignment (pinned code): hypotheses for stage k are written in
stages/k; the walk driven after stage k's plan is saved to
stages/(k+1)/executed_path.json (exploration_pipeline.py:654, 881-889, 913).
For stage k: reached viewpoint = last point of stages/(k+1)/executed_path.json
(world_frame_path); next map = stage k+1's observed graphs (k+2 as a lag
check); a stage without a k+1 folder holding both is dropped.

Per stage and track, the candidates are the reference objects the oracle may
draw for that track's observed graph (live_policy.oracle_eligible). Each
candidate gets: approach (within 3.5 m xy of the reached viewpoint), mapped
at k+1 and k+2 (same label within 0.5 m xy of an object or structure node of
the next map, either track), and scanned (within 3 m xy of the path walked
before stage k's plan).

- base rate (every arm): share of candidates with approach that are mapped
  at k+1;
- gate (oracle_visible runs): drawn (named by some member of the track) vs
  undrawn candidates, pooled rate difference in approach and in mapping at
  k+1 over the run, one-sided p from 2,000 permutations of the drawn labels
  within stage and track; the same split by scanned;
- scanned share of every arm's new hypotheses, per stage;
- later found (descriptive): unique hypotheses (oracle: reference objects;
  other arms: label + 0.5 m cell) matched within 0.5 m in the final map,
  the last stage left out.

Usage (pipeline Python, inside a container):
    stage_diagnostics.py <campaign_dir> <out.json> <run> [<run> ...]
"""
import glob
import json
import os
import re
import sys

import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_policy  # noqa: E402

ENSEMBLE = 4  # members per track (LLM_ENSEMBLE_COUNT)
APPROACH_M, MAPPED_M, SCANNED_M = 3.5, 0.5, 3.0
N_PERM = 2000


def label(name):
    return live_policy._label(name)


def xy(node):
    return live_policy._vec(node["position"])[:2]


def load(path):
    with open(path) as f:
        return yaml.safe_load(f) or {"nodes": []}


def stage_dirs(campaign, run):
    dirs = [d for d in glob.glob(os.path.join(campaign, run, "stages", "*")) if os.path.basename(d).isdigit()]
    return {int(os.path.basename(d)): d for d in dirs}


def observed(stage_dir):
    out = {}
    for t in (0, 1):
        p = os.path.join(stage_dir, f"habitat_scene_graph_original_graph{t}.yaml")
        if os.path.exists(p):
            out[t] = load(p)
    return out


def map_points(graphs):
    """(label, x, y) of object and structure nodes in a stage's observed graphs."""
    return [(label(n.get("name", "")), *xy(n)) for g in graphs.values() for n in g.get("nodes") or []
            if n.get("node_type") in ("object", "structure") and "position" in n]


def is_mapped(c, points):
    lab, (x, y) = label(c["name"]), c["position"][:2]
    return any(pl == lab and (px - x) ** 2 + (py - y) ** 2 <= MAPPED_M ** 2 for pl, px, py in points)


def path_xy(stage_dir):
    p = os.path.join(stage_dir, "executed_path.json")
    if not os.path.exists(p):
        return None
    pts = json.load(open(p)).get("world_frame_path") or []
    return np.array([[float(q[0]), float(q[1])] for q in pts]) if pts else None


def arm_of(run):
    for arm in ("official", "placebo", "filter_only", "oracle_visible", "observed_only", "unanimity"):
        if f"_{arm}_" in run or (arm == "oracle_visible" and run.startswith("dryrun_oracle_")):
            return arm
    return "unknown"


def gap(rows, outcome):
    d = [r[outcome] for r in rows if r["drawn"]]
    u = [r[outcome] for r in rows if not r["drawn"]]
    return (np.mean(d) - np.mean(u)) if d and u else float("nan"), len(d), len(u)


def permutation_p(rows, outcome, rng):
    obs, _, _ = gap(rows, outcome)
    if np.isnan(obs):
        return float("nan")
    strata = {}
    for i, r in enumerate(rows):
        strata.setdefault((r["stage"], r["track"]), []).append(i)
    vals = np.array([r[outcome] for r in rows], dtype=float)
    drawn = np.array([r["drawn"] for r in rows])
    count = 0
    for _ in range(N_PERM):
        perm = drawn.copy()
        for idx in strata.values():
            perm[idx] = rng.permutation(drawn[idx])
        if vals[perm].mean() - vals[~perm].mean() >= obs - 1e-12:
            count += 1
    return (count + 1) / (N_PERM + 1)


def run_diagnostics(campaign, run, sets, rng):
    scene = str(int(re.search(r"_(\d{5})_s\d+", run).group(1)))
    candidates = sets[scene]["objects"]
    arm = arm_of(run)
    stages = stage_dirs(campaign, run)
    rows, scanned_share = [], []
    walked = np.zeros((0, 2))
    for k in sorted(stages):
        p = path_xy(stages[k])
        if p is not None and k > 0:
            walked = np.vstack([walked, p])  # walked before stage k's plan: stages 1..k
        nxt = stages.get(k + 1)
        obs_k = observed(stages[k])
        reached = path_xy(nxt) if nxt else None
        obs_k1 = observed(nxt) if nxt else {}
        if not obs_k or reached is None or not len(reached) or not obs_k1:
            continue
        rx, ry = reached[-1]
        pts1 = map_points(obs_k1)
        pts2 = map_points(observed(stages[k + 2])) if (k + 2) in stages else None
        new_objs = []
        for t, g in obs_k.items():
            eligible = live_policy.oracle_eligible(g, candidates)
            drawn_keys = set()
            obs_ids = {n["id"] for n in g.get("nodes") or []}
            for f in glob.glob(os.path.join(stages[k], "habitat_scene_graph_new_graph_*.yaml")):
                gid = int(os.path.splitext(f)[0].rsplit("_", 1)[1])
                if gid // ENSEMBLE != t:
                    continue
                for n in load(f).get("nodes") or []:
                    if n.get("node_type") == "object" and n["id"] not in obs_ids and "position" in n:
                        drawn_keys.add((label(n.get("name", "")), tuple(round(v, 3) for v in live_policy._vec(n["position"]))))
                        new_objs.append(xy(n))
            for c in eligible:
                key = (label(c["name"]), tuple(round(v, 3) for v in c["position"]))
                cx, cy = c["position"][:2]
                rows.append({"stage": k, "track": t, "drawn": key in drawn_keys,
                             "approach": (cx - rx) ** 2 + (cy - ry) ** 2 <= APPROACH_M ** 2,
                             "mapped1": is_mapped(c, pts1),
                             "mapped2": is_mapped(c, pts2) if pts2 is not None else None,
                             "scanned": bool(len(walked)) and float(np.min(np.hypot(walked[:, 0] - cx, walked[:, 1] - cy))) <= SCANNED_M,
                             "ref": f"{c['name']}@{c['position'][0]:.3f},{c['position'][1]:.3f}"})
        if new_objs and len(walked):
            w = walked
            scanned_share.append(float(np.mean([np.min(np.hypot(w[:, 0] - x, w[:, 1] - y)) <= SCANNED_M for x, y in new_objs])))
    near = [r for r in rows if r["approach"]]
    out = {"run": run, "arm": arm, "scene": scene, "stages_used": len({r["stage"] for r in rows}),
           "candidate_rows": len(rows),
           "base_rate": {"n_near": len(near), "mapped_k1": float(np.mean([r["mapped1"] for r in near])) if near else None,
                         "mapped_k2": float(np.mean([r["mapped2"] for r in near if r["mapped2"] is not None]))
                         if any(r["mapped2"] is not None for r in near) else None},
           "scanned_share_of_new_hypotheses": float(np.mean(scanned_share)) if scanned_share else None}
    if arm == "oracle_visible":
        gate = {}
        for name, subset in (("all", rows), ("scanned", [r for r in rows if r["scanned"]]),
                             ("unscanned", [r for r in rows if not r["scanned"]])):
            g = {}
            for outcome in ("approach", "mapped1"):
                d, nd, nu = gap(subset, outcome)
                g[outcome] = {"gap": d, "n_drawn": nd, "n_undrawn": nu, "p_one_sided": permutation_p(subset, outcome, rng)}
            lag = [r for r in subset if r["mapped2"] is not None]
            g["mapped2_gap"] = gap([dict(r, mapped2=bool(r["mapped2"])) for r in lag], "mapped2")[0] if lag else None
            gate[name] = g
        out["gate"] = gate
        final_pts = None
        for k in sorted(stages, reverse=True):
            obs = observed(stages[k])
            if obs:
                final_pts = map_points(obs)
                break
        last = max(r["stage"] for r in rows) if rows else None
        drawn_refs = {r["ref"] for r in rows if r["drawn"] and r["stage"] != last}
        found = 0
        for ref in drawn_refs:
            name, pos = ref.split("@")
            x, y = (float(v) for v in pos.split(","))
            found += is_mapped({"name": name, "position": [x, y, 0.0]}, final_pts or [])
        out["later_found"] = {"unique": len(drawn_refs), "share": found / len(drawn_refs) if drawn_refs else None}
    return out


def main():
    campaign, out_path = sys.argv[1], sys.argv[2]
    sets = json.load(open(live_policy.ORACLE_SETS_PATH))["scenes"]
    rng = np.random.default_rng(0)
    rows = []
    for run in sys.argv[3:]:
        r = run_diagnostics(campaign, run, sets, rng)
        rows.append(r)
        print(json.dumps(r), flush=True)
    json.dump(rows, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main()
