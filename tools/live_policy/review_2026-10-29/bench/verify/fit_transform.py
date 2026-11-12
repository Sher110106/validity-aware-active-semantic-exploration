"""Fit habitat_frame_path -> world_frame_path (rigid) per scene, check consistency."""
import glob, json
import numpy as np
for scene in ("00853", "00871"):
    H, W = [], []
    for f in glob.glob(f"/tmp/cvp_review/runs/e*_{scene}_*/stages/*/executed_path.json"):
        d = json.load(open(f))
        H += d["habitat_frame_path"]; W += d["world_frame_path"]
    H, W = np.array(H), np.array(W)
    A = np.column_stack([H, np.ones(len(H))])
    X, *_ = np.linalg.lstsq(A, W, rcond=None)
    r = W - A @ X
    print(scene, len(H), "affine fit max resid", float(np.abs(r).max()))
    print(np.round(X, 5))
