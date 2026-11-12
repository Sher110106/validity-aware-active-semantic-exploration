import glob, json, os
import numpy as np
R0 = "/Users/sher/cvp_live_campaign_copy/runs"
ref = {}
for s in ("00853", "00871"):
    fr = json.load(open(f"{R0}/live_campaign/hm3d_refs_work/{s}_hm3d_reference_summary.json"))["frame"]
    ref[s] = (np.array(fr["world_from_habitat_R"]), np.array(fr["world_from_habitat_t"]))
def fit(H, W):
    # least-squares rigid fit W = R H + t
    hc, wc = H.mean(0), W.mean(0)
    U, S, Vt = np.linalg.svd((H - hc).T @ (W - wc))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return R, wc - R @ hc
runs = sorted(glob.glob(f"{R0}/frontier_seeds/e4_*")) + sorted(glob.glob(f"{R0}/live_campaign/e1_*_60m")) + sorted(glob.glob(f"{R0}/live_campaign/e1_*_rerun1"))
for d in runs:
    n = os.path.basename(d); s = n.split("_")[1]
    H, W = [], []
    for f in glob.glob(f"{d}/stages/*/executed_path.json"):
        e = json.load(open(f)); H += e["habitat_frame_path"]; W += e["world_frame_path"]
    if len(H) < 10: print(n, "too few path points"); continue
    H, W = np.array(H), np.array(W)
    Rr, tr = ref[s]
    resid_ref = np.linalg.norm(W - (H @ Rr.T + tr), axis=1)
    print(f"{n:42s} pts={len(H):5d}  |world - ref_transform(habitat)| median={np.median(resid_ref):.4f} max={resid_ref.max():.4f}")
