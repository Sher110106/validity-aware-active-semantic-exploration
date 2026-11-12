#!/usr/bin/env python3
"""Descriptive: share of each run's hypotheses later found where they said.

Unit: a unique hypothesis, counted once per run: the oracle's reference
objects (label and exact position), and for other arms each new predicted
object's (label, 0.5 m xy cell). New = more than 0.5 m (xy) from every object
observed at that stage. Found = a same-label object or structure node within
0.5 m (xy) in the final map (the last stage that saved observed graphs). The
last stage's hypotheses are left out: they could not be found later.

Usage: later_found.py <campaign_dir> <out.json> <run> [<run> ...]
"""
import glob
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_policy  # noqa: E402


def load(path):
    with open(path) as f:
        return yaml.safe_load(f) or {"nodes": []}


def main():
    campaign, out_path = sys.argv[1], sys.argv[2]
    rows = []
    for run in sys.argv[3:]:
        stages = sorted((int(os.path.basename(d)), d) for d in glob.glob(os.path.join(campaign, run, "stages", "*"))
                        if os.path.basename(d).isdigit())
        mapped = [(k, d) for k, d in stages if os.path.exists(os.path.join(d, "habitat_scene_graph_original_graph0.yaml"))]
        if len(mapped) < 2:
            continue
        final = []
        for t in (0, 1):
            p = os.path.join(mapped[-1][1], f"habitat_scene_graph_original_graph{t}.yaml")
            if os.path.exists(p):
                final += [(live_policy._label(n.get("name", "")), live_policy._vec(n["position"])[:2])
                          for n in load(p).get("nodes") or [] if n.get("node_type") in ("object", "structure") and "position" in n]
        oracle = "_oracle_visible_" in run or run.startswith("dryrun_oracle_")
        hyps = {}
        for k, d in mapped[:-1]:
            for t in (0, 1):
                op = os.path.join(d, f"habitat_scene_graph_original_graph{t}.yaml")
                if not os.path.exists(op):
                    continue
                obs = load(op)
                obs_ids = {n["id"] for n in obs.get("nodes") or []}
                obs_xy = [live_policy._vec(n["position"])[:2] for n in obs.get("nodes") or []
                          if n.get("node_type") == "object" and "position" in n]
                for f in glob.glob(os.path.join(d, "habitat_scene_graph_new_graph_*.yaml")):
                    if int(os.path.splitext(f)[0].rsplit("_", 1)[1]) // 4 != t:
                        continue
                    for n in load(f).get("nodes") or []:
                        if n.get("node_type") != "object" or n["id"] in obs_ids or "position" not in n:
                            continue
                        x, y = live_policy._vec(n["position"])[:2]
                        if any((x - a) ** 2 + (y - b) ** 2 <= 0.25 for a, b in obs_xy):
                            continue
                        lab = live_policy._label(n.get("name", ""))
                        key = (lab, round(x, 3), round(y, 3)) if oracle else (lab, int(x // 0.5), int(y // 0.5))
                        hyps.setdefault(key, (lab, x, y))
        found = sum(any(fl == lab and (fx - x) ** 2 + (fy - y) ** 2 <= 0.25 for fl, (fx, fy) in final)
                    for lab, x, y in hyps.values())
        rows.append({"run": run, "unique_hypotheses": len(hyps), "found": found,
                     "share": round(found / len(hyps), 4) if hyps else None})
        print(json.dumps(rows[-1]), flush=True)
    json.dump(rows, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main()
