#!/usr/bin/env python3
"""Recompute U_wall and U_wall_cone for all 384 stages with the exact
grid-line-crossing wall test (verify_stages.wall_vis), keep the builder's
picks, and recompute regrets and the decision rule. Shows whether the
builder's 5 mm sampling changes any number that matters."""
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, "/tmp/cvp_bench/bench/verify")
import numpy as np  # noqa: E402

import verify_stages as VS  # noqa: E402

OUT = "/tmp/cvp_bench/bench/verify"


def one(a):
    run, k = a
    import replay as rp
    b = VS.BUILD[(run, k)]
    scene = run.split("_")[1]
    seed = VS.P[run]["cfg"]["SEED"]
    sd = f"{VS.RUNS}/{run}/stages/{k}"
    act = [f"{sd}/habitat_scene_graph_new_graph_{g}.yaml" for g in b["gids"]]
    meta = rp.stage_meta(run)[k]
    kept, sc, total, order = VS.fastig.Scorer(act, seed).first_stage(seed, meta["nprior"], VS.cur_pos(run, k))
    refs = VS.REF[str(int(scene))]["objects"]
    un = VS.unmapped(refs, VS.obs_nodes(run, k))
    rxy = np.array([o["position"][:2] for o in refs], float)
    wv = VS.wall_vis(scene, kept[:, :2], rxy) & un[None]
    tg = [{"id": i, "name": o["name"], "pos": np.array(o["position"], float), "dims": np.array(o["dimension"], float),
           "orient": np.eye(3)} for i, o in enumerate(refs)]
    cone = VS.vis_engine(tg, [], kept, VS.fastig.cu.CameraConfig())
    return {"run": run, "stage": k, "Uwall": wv.sum(1).tolist(), "Ucone": (wv & cone).sum(1).tolist(),
            "z_unique": sorted(set(np.round(kept[:, 2], 4).tolist()))[:5]}


if __name__ == "__main__":
    from multiprocessing import Pool
    todo = list(VS.BUILD)
    with Pool(7) as pool, open(os.path.join(OUT, "exact_U.jsonl"), "w") as f:
        for r in pool.imap_unordered(one, todo):
            f.write(json.dumps(r) + "\n")
            f.flush()
