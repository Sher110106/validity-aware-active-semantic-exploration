"""Frame check: do walked paths (densified) run through free wall-map cells?"""
import glob, json, sys
import numpy as np
for scene in ("00853", "00871"):
    d = np.load(f"/tmp/cvp_bench/refs/{scene}_walls.npz")
    occ = d["occ"].max(0) > 0; org = d["origin"]; res = float(d["res"])
    occ11 = d["occ"][1] > 0
    pts = []; segs = 0; segs_hit = 0
    for f in glob.glob(f"/tmp/cvp_review/runs/e*_{scene}_*/stages/*/executed_path.json"):
        p = np.array(json.load(open(f))["world_frame_path"], float)[:, :2]
        for a, b in zip(p[:-1], p[1:]):
            n = max(2, int(np.hypot(*(b - a)) / 0.01) + 1)
            s = a + np.linspace(0, 1, n)[:, None] * (b - a)
            pts.append(s); segs += 1
    P = np.concatenate(pts)
    def frac(P, g):
        ij = np.floor((P - org) / res).astype(int)
        ok = (ij[:, 0] >= 0) & (ij[:, 0] < g.shape[0]) & (ij[:, 1] >= 0) & (ij[:, 1] < g.shape[1])
        return float(np.mean(g[ij[ok, 0], ij[ok, 1]])), float(np.mean(ok))
    print(scene, "path pts", len(P), "segments", segs, "occupied frac (union, 1.1m), in-grid:", frac(P, occ), frac(P, occ11)[0])
    # controls: shifted and mirrored maps
    c = P.mean(0)
    for name, Q in [("shift+0.5x", P + [0.5, 0]), ("shift+1y", P + [0, 1.0]), ("mirror x about centre", np.column_stack([2 * c[0] - P[:, 0], P[:, 1]])),
                    ("swap xy", np.column_stack([P[:, 1] - c[1] + c[0], P[:, 0] - c[0] + c[1]]))]:
        print("   control", name, frac(Q, occ))
    # random free-ish baseline: overall occupancy of the bounding box of the path
    lo, hi = P.min(0), P.max(0)
    R = np.random.default_rng(0).uniform(lo, hi, (200000, 2))
    print("   random in path bbox", frac(R, occ))
