#!/usr/bin/env python3
"""Share of each run's walked path that lies in occupied cells of the HM3D wall
map (1.1 m slice), for the six seeded frontier runs and the counted E1 runs.

The world-frame path in stages/*/executed_path.json is sampled every 2 cm and
looked up in review_2026-10-29/bench/walls/<scene>_walls.npz (slice_walls.py).
Usage: wall_cells.py [copy_dir] > wall_cells.json
"""
import csv
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LP = os.path.dirname(os.path.dirname(HERE))
COPY = sys.argv[1] if len(sys.argv) > 1 else "/Users/sher/cvp_live_campaign_copy"
STEP_M = 0.02


def wall_map(scene):
    z = np.load(os.path.join(LP, "review_2026-10-29/bench/walls", f"{scene}_walls.npz"))
    k = [round(float(h), 1) for h in z["heights"]].index(1.1)
    return z["occ"][k], z["origin"][:2], float(z["res"])


def share(run_dir, scene):
    occ, origin, res = wall_map(scene)
    pts = []
    for f in sorted(glob.glob(os.path.join(run_dir, "stages", "*", "executed_path.json"))):
        p = np.array(json.load(open(f))["world_frame_path"], float)[:, :2]
        for a, b in zip(p[:-1], p[1:]):
            n = max(1, int(np.ceil(np.linalg.norm(b - a) / STEP_M)))
            pts.append(a + (b - a) * np.linspace(0, 1, n, endpoint=False)[:, None])
    P = np.vstack(pts)
    ij = np.floor((P - origin) / res).astype(int)
    inside = (ij[:, 0] >= 0) & (ij[:, 1] >= 0) & (ij[:, 0] < occ.shape[0]) & (ij[:, 1] < occ.shape[1])
    return {"share_in_wall_cells": float(occ[ij[inside, 0], ij[inside, 1]].mean()), "n_points": int(len(P))}


def main():
    out = {"frontier": {}, "e1": {}}
    for r in sorted(glob.glob(os.path.join(COPY, "runs/frontier_seeds/e4_*_frontier_60m"))):
        out["frontier"][os.path.basename(r)] = share(r, os.path.basename(r).split("_")[1])
    table = os.path.join(LP, "results_2026-10-31/run_table.csv")
    for row in csv.DictReader(open(table)):
        if row["status"] == "counted" and row["arm"] in ("official", "placebo"):
            out["e1"][row["run"]] = share(os.path.join(COPY, "runs/live_campaign", row["run"]), row["scene"])
    for g in ("frontier", "e1"):
        v = [x["share_in_wall_cells"] for x in out[g].values()]
        out[f"{g}_range"] = [min(v), max(v)]
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
