#!/usr/bin/env python3
"""Frame check: observed objects (pipeline frame) against same-label reference
objects (oracle_sets.json). Reports, per sampled stage, the xy distance from
each observed object to the nearest same-label reference object, and the same
for a shuffled-label null (nearest reference object of a random other label).
Read-only on inputs; writes frame_check.json next to this script."""
import json
import os

import numpy as np
import yaml

RUNS = "/tmp/cvp_review/runs"
OUT = os.path.dirname(os.path.abspath(__file__))
REF = json.load(open("/tmp/cvp_review/refs/oracle_sets.json"))["scenes"]


def vec(v):
    import ast
    return [float(x) for x in (ast.literal_eval(v) if isinstance(v, str) else v)]


def lab(n):
    return str(n).lower().replace("_", " ").strip()


SAMPLES = [("e1_00853_s42_official_60m", [3, 8, 14]), ("e1_00871_s42_placebo_60m", [3, 8, 14]),
           ("e2_00871_s43_filter_only_60m", [5, 10]), ("e3_00853_s43_oracle_visible_60m", [4, 9])]
rows = []
rng = np.random.default_rng(0)
for run, stages in SAMPLES:
    scene = str(int(run.split("_")[1]))
    refs = REF[scene]["objects"]
    rxy = np.array([o["position"][:2] for o in refs])
    rl = np.array([lab(o["name"]) for o in refs])
    for k in stages:
        g = yaml.safe_load(open(f"{RUNS}/{run}/stages/{k}/habitat_scene_graph_original_graph0.yaml"))
        d_same, d_other = [], []
        for n in g["nodes"]:
            if n.get("node_type") not in ("object", "structure") or "position" not in n:
                continue
            L = lab(n["name"])
            if L not in set(rl):
                continue
            xy = np.array(vec(n["position"])[:2])
            dd = np.hypot(*(rxy - xy).T)
            d_same.append(float(dd[rl == L].min()))
            others = sorted(set(rl) - {L})
            o = others[int(rng.integers(len(others)))]
            d_other.append(float(dd[rl == o].min()))
        rows.append({"run": run, "stage": k, "n": len(d_same),
                     "median_same_label_m": float(np.median(d_same)) if d_same else None,
                     "share_same_within_0.5m": float(np.mean(np.array(d_same) <= 0.5)) if d_same else None,
                     "median_random_label_m": float(np.median(d_other)) if d_other else None})
        print(rows[-1])
json.dump(rows, open(f"{OUT}/frame_check.json", "w"), indent=1)
