import glob, json
import numpy as np
from scipy.ndimage import distance_transform_edt
for scene in ("00853", "00871"):
    d = np.load(f"/tmp/cvp_bench/refs/{scene}_walls.npz")
    org = d["origin"]; res = float(d["res"])
    for name, g in [("union", d["occ"].max(0) > 0), ("1.1", d["occ"][1] > 0), ("1.6", d["occ"][2] > 0)]:
        dt = distance_transform_edt(~g) * res
        P = []
        for f in glob.glob(f"/tmp/cvp_review/runs/e*_{scene}_*/stages/*/executed_path.json"):
            p = np.array(json.load(open(f))["world_frame_path"], float)[:, :2]
            for a, b in zip(p[:-1], p[1:]):
                P.append(a + np.linspace(0, 1, 10)[:, None] * (b - a))
        P = np.concatenate(P)
        ij = np.floor((P - org) / res).astype(int)
        dd = dt[ij[:, 0], ij[:, 1]]
        lo, hi = P.min(0), P.max(0)
        R = np.random.default_rng(0).uniform(lo, hi, (200000, 2))
        rij = np.floor((R - org) / res).astype(int)
        rd = dt[rij[:, 0], rij[:, 1]]
        q = lambda x: [round(float(np.mean(x <= t)), 3) for t in (0.0, 0.1, 0.2, 0.3)]
        print(scene, name, "path: share with wall dist <=0,0.1,0.2,0.3 m", q(dd), " random:", q(rd), "median", round(float(np.median(dd)),2), round(float(np.median(rd)),2))
