"""Independent scorer: author-faithful object F1 AUC vs HM3D reference.

Own implementation (no project imports). Usage: python -B score.py
Writes /tmp/cvp_verify_step7/scores.json
"""
import ast
import glob
import json
import math
import os
import re

import numpy as np
import yaml

ROOT = "/Users/sher/cvp_live_campaign_copy/runs"
REFDIR = os.path.join(ROOT, "live_campaign", "hm3d_refs_work")
OUT = "/tmp/cvp_verify_step7/scores.json"
THRESH = 0.5


def load_objects(path):
    with open(path) as f:
        d = yaml.safe_load(f) or {}
    objs = []
    for n in d.get("nodes", []) or []:
        name = n.get("name")
        if name is not None and str(name).lower() == "door":
            continue
        if n.get("node_type") != "object":
            continue
        pos = n["position"]
        if isinstance(pos, str):
            pos = ast.literal_eval(pos)
        objs.append((name, np.asarray(pos, dtype=float)))
    return objs


def f1(ref, pred):
    if not ref or not pred:
        return 0.0, 0.0, 0.0
    free = list(range(len(ref)))
    tp = 0
    for pname, ppos in pred:
        best, bd = None, math.inf
        for gi in free:
            gname, gpos = ref[gi]
            if gname != pname:
                continue
            d = float(np.linalg.norm(ppos - gpos))
            if d < bd:
                bd, best = d, gi
        if best is not None and bd < THRESH:
            tp += 1
            free.remove(best)
    p = tp / len(pred)
    r = tp / len(ref)
    return p, r, (2 * p * r / (p + r) if p + r > 0 else 0.0)


def curve(run_dir, ref):
    pts = []
    for sd in glob.glob(os.path.join(run_dir, "stages", "*")):
        k = os.path.basename(sd)
        if not k.isdigit():
            continue
        ns = os.path.join(sd, "navigation_stats.json")
        if not os.path.isfile(ns):
            continue
        tracks = [os.path.join(sd, f"habitat_scene_graph_original_graph{i}.yaml") for i in (0, 1)]
        tracks = [t for t in tracks if os.path.isfile(t)]
        if not tracks:
            continue
        x = float(json.load(open(ns))["total_path_length_meters"])
        f1s = [f1(ref, load_objects(t))[2] for t in tracks]
        pts.append({"stage": int(k), "x": x, "f1": sum(f1s) / len(f1s), "n_tracks": len(tracks),
                    "f1_tracks": f1s})
    pts.sort(key=lambda p: (p["x"], p["stage"]))
    return pts


def auc(points, budget):
    """points: list of (x, y) sorted by x (stable by stage). Trapezoid on [0, budget] / budget;
    hold first value back to 0, linear interpolation at budget crossing, hold last past end.
    Duplicate x keep the last y (matches author dedupe)."""
    pts = [(x, y) for x, y in points]
    if len(pts) < 2:
        return 0.0

    def at(x):
        if x <= pts[0][0]:
            return pts[0][1]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x <= x1:
                if x1 == x0:
                    return y1
                return y0 + (x - x0) / (x1 - x0) * (y1 - y0)
        return pts[-1][1]

    c = [(x, y) for x, y in pts if 0.0 <= x <= budget]
    if not c or c[0][0] > 0:
        c.insert(0, (0.0, at(0.0)))
    if c[-1][0] < budget:
        c.append((budget, at(budget)))
    else:
        c[-1] = (budget, at(budget))
    dd = {}
    for x, y in c:
        dd[x] = y
    c = sorted(dd.items())
    a = sum((x1 - x0) * (y0 + y1) / 2 for (x0, y0), (x1, y1) in zip(c, c[1:]))
    return a / budget


def scene_of(name):
    m = re.match(r"e\d_(\d{5})_s(\d+)_([a-z_]+?)_60m(?:_rerun(\d+))?$", name)
    return m


def main():
    refs = {s: [o for o in load_objects(os.path.join(REFDIR, f"{s}_hm3d_reference.yaml"))]
            for s in ("00853", "00871")}
    out = {"refs_n_objects": {s: len(v) for s, v in refs.items()}, "runs": {}}
    dirs = sorted(glob.glob(os.path.join(ROOT, "frontier_seeds", "e4_*"))) + \
        sorted(glob.glob(os.path.join(ROOT, "live_campaign", "e1_*")))
    for d in dirs:
        name = os.path.basename(d)
        m = scene_of(name)
        if not m:
            out["runs"][name] = {"skipped": "name does not match counted pattern"}
            continue
        scene, seed, arm, rerun = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        pts = curve(d, refs[scene])
        xy = [(p["x"], p["f1"]) for p in pts]
        out["runs"][name] = {
            "scene": scene, "seed": seed, "arm": arm, "rerun": rerun,
            "final_path_m": max([p["x"] for p in pts], default=0.0),
            "n_scored_stages": len(pts),
            "auc60": auc(xy, 60.0), "auc50": auc(xy, 50.0),
            # variant: anchor a (0,0) point (to show whether the origin rule matters)
            "auc60_with_origin0": auc(sorted([(0.0, 0.0)] + [p for p in xy if p[0] > 0]), 60.0),
            "points": pts,
        }
    json.dump(out, open(OUT, "w"), indent=1, default=float)
    for n, r in out["runs"].items():
        if "auc60" in r:
            print(f"{n:45s} final={r['final_path_m']:6.2f} n={r['n_scored_stages']:3d} "
                  f"auc60={r['auc60']:.6f} auc50={r['auc50']:.6f} o0={r['auc60_with_origin0']:.6f}")
        else:
            print(n, r)
    print(out["refs_n_objects"])


if __name__ == "__main__":
    main()
