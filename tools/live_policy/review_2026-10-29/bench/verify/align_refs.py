import json
import numpy as np
from scipy.ndimage import distance_transform_edt
REF = json.load(open("/tmp/cvp_review/refs/oracle_sets.json"))["scenes"]
for scene in ("00853", "00871"):
    d = np.load(f"/tmp/cvp_bench/refs/{scene}_walls.npz")
    org = d["origin"]; res = float(d["res"])
    g = d["occ"][1] > 0
    dt = distance_transform_edt(~g) * res
    refs = REF[str(int(scene))]["objects"]
    names = [o["name"].lower() for o in refs]
    wallish = np.array([any(w in n for w in ("window", "door", "picture", "curtain", "mirror", "frame", "shelf", "cabinet", "tv")) for n in names])
    xy = np.array([o["position"][:2] for o in refs])
    def md(P):
        ij = np.floor((P - org) / res).astype(int)
        ij = np.clip(ij, 0, np.array(g.shape) - 1)
        return dt[ij[:, 0], ij[:, 1]]
    print(scene, "n wallish", wallish.sum(), "of", len(refs))
    for name, sh in [("true", (0, 0)), ("+0.3x", (0.3, 0)), ("-0.3x", (-0.3, 0)), ("+0.3y", (0, 0.3)), ("-0.3y", (0, -0.3)), ("+1x", (1, 0)), ("+1y", (0, 1))]:
        dd = md(xy + sh)
        print("  ", name, "wallish median dist", round(float(np.median(dd[wallish])), 3), "share<=0.15", round(float(np.mean(dd[wallish] <= 0.15)), 2),
              "| all median", round(float(np.median(dd)), 3))
    # path test with same shifts
    import glob
    P = []
    for f in glob.glob(f"/tmp/cvp_review/runs/e*_{scene}_*/stages/*/executed_path.json"):
        p = np.array(json.load(open(f))["world_frame_path"], float)[:, :2]
        for a, b in zip(p[:-1], p[1:]):
            P.append(a + np.linspace(0, 1, 10)[:, None] * (b - a))
    P = np.concatenate(P)
    for name, sh in [("true", (0, 0)), ("+0.3x", (0.3, 0)), ("-0.3x", (-0.3, 0)), ("+0.3y", (0, 0.3)), ("-0.3y", (0, -0.3))]:
        dd = md(P + sh)
        print("   path", name, "share in wall cell (1.1)", round(float(np.mean(dd == 0)), 4), "share <=0.1", round(float(np.mean(dd <= 0.1)), 3))
