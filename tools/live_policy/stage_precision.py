#!/usr/bin/env python3
"""Precision of every live stage's hypotheses against the human HM3D reference.

For each run, stage and completion file: predicted objects placed more than
0.5 m (xy) from every observed object ("new") that land within 0.5 / 1.0 /
2.0 m of a same-label reference object the observed graph has not mapped
(gemini_static_score.score). For filter_only the raw completions (last
attempt under live_policy_raw/) are split into the nodes the validator kept
and the nodes it removed. Members use their own track's observed graph
(graph id // ensemble size).

Usage (pipeline Python, inside a container):
    stage_precision.py <campaign_dir> <out.json> <run> [<run> ...]
"""
import glob
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_static_score as gs  # noqa: E402

REFS = "/workspace/runs/live_campaign/hm3d_refs_work/{}_hm3d_reference.yaml"
ENSEMBLE = 4  # members per track (LLM_ENSEMBLE_COUNT)
FIELDS = ("n_pred", "n_new", "n_relabel") + tuple(f"new_hits_{r}" for r in (0.5, 1.0, 2.0))


def arm_of(run):
    for arm in ("official", "placebo", "filter_only", "oracle_visible", "observed_only", "unanimity"):
        if f"_{arm}_" in run:
            return arm
    return "unknown"


def subset(graph, keep_ids):
    nodes = [n for n in graph.get("nodes") or [] if n["id"] in keep_ids]
    return {"nodes": nodes, "edges": []}


def main():
    campaign, out = sys.argv[1], sys.argv[2]
    rows = []
    for run in sys.argv[3:]:
        scene, arm = run.split("_")[1], arm_of(run)
        ref = [(gs.norm(n.get("name", "")), gs.xy(n)) for n in gs.objects(yaml.safe_load(open(REFS.format(scene))))]
        works = [p for p in glob.glob(os.path.join(campaign, run, "stages", "*")) if os.path.basename(p).isdigit()]
        for work in sorted(works, key=lambda p: int(os.path.basename(p))):
            stage = int(os.path.basename(work))
            observed, novel = {}, {}
            for track in (0, 1):
                p = os.path.join(work, f"habitat_scene_graph_original_graph{track}.yaml")
                if os.path.exists(p):
                    observed[track] = yaml.safe_load(open(p))
                    obs = [(gs.norm(n.get("name", "")), gs.xy(n)) for n in gs.objects(observed[track])]
                    _, seen = gs.greedy(obs, ref, 0.5)
                    novel[track] = [r for j, r in enumerate(ref) if j not in seen]
            attempts = sorted(glob.glob(os.path.join(work, "live_policy_raw", "attempt_*")),
                              key=lambda p: int(p.rsplit("_", 1)[1]))
            for path in sorted(glob.glob(os.path.join(work, "habitat_scene_graph_new_graph_*.yaml"))):
                gid = int(os.path.splitext(path)[0].rsplit("_", 1)[1])
                track = gid // ENSEMBLE
                if track not in observed:
                    continue
                final = yaml.safe_load(open(path)) or {"nodes": []}
                row = {"run": run, "arm": arm, "scene": scene, "stage": stage, "graph_id": gid,
                       "final": gs.score(final, observed[track], novel[track])}
                if arm == "filter_only" and attempts:
                    raw_path = os.path.join(attempts[-1], os.path.basename(path))
                    if os.path.exists(raw_path):
                        raw = yaml.safe_load(open(raw_path)) or {"nodes": []}
                        kept = {n["id"] for n in final.get("nodes") or []}
                        removed = {n["id"] for n in raw.get("nodes") or [] if n["id"] not in kept}
                        obs_ids = {n["id"] for n in observed[track].get("nodes") or []}
                        row["raw"] = gs.score(raw, observed[track], novel[track])
                        row["removed"] = gs.score(subset(raw, removed | obs_ids), observed[track], novel[track])
                rows.append(row)
    totals = {}
    for row in rows:
        for part in ("final", "raw", "removed"):
            if part not in row:
                continue
            key = f"{row['arm']}:{part}"
            t = totals.setdefault(key, {"completions": 0, **{f: 0 for f in FIELDS}})
            t["completions"] += 1
            for f in FIELDS:
                t[f] += row[part][f]
    for t in totals.values():
        for r in (0.5, 1.0, 2.0):
            t[f"new_precision_{r}"] = round(t[f"new_hits_{r}"] / t["n_new"], 4) if t["n_new"] else None
    json.dump({"totals": totals, "rows": rows}, open(out, "w"), indent=1)
    print(json.dumps(totals, indent=1))


if __name__ == "__main__":
    main()
