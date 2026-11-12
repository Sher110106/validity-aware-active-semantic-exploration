#!/usr/bin/env python3
"""Matched-state check (secondary): on every used stage, hold the robot state
and the 300 replayed candidates fixed and swap the hypothesis files:
  actual - the files the planner used;
  obs    - each member = its track's observed graph (no hypotheses);
  plc    - live_policy.placebo_graph draw per member;
  orc    - live_policy.oracle_graph draw per member from oracle_sets.json
           (the live oracle arm's own generator and object universe).
Score each with A's vectorized scorer (first-stage camera), total = IG - 0.2 d,
and take Spearman rho with U_360 and U_cone. Also a hypothesis-free frontier
proxy: candidate distance to the walked path (stages 1..k).
Scratch hypothesis files go to ./tmp. Writes cf_stages.jsonl. No F1/AUC."""
import json
import os
import sys
from multiprocessing import Pool

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import audit as au  # noqa: E402

rp, rp2, fastig = au.rp, au.rp2, au.fastig
OUT = au.OUT
TMP = os.path.join(OUT, "tmp")
CALIB = rp.lp.load_calibration()


def cond_files(run, k, gids, cond, seed):
    sd = f"{rp.RUNS}/{run}/stages/{k}"
    if cond == "actual":
        return [f"{sd}/habitat_scene_graph_new_graph_{g}.yaml" for g in gids]
    wdir = os.path.join(TMP, f"{run}_{k}")
    os.makedirs(wdir, exist_ok=True)
    scene = int(run.split("_")[1])
    out = []
    for g in gids:
        observed = rp.load(f"{sd}/habitat_scene_graph_original_graph{g // 4}.yaml")
        dst = os.path.join(wdir, f"{cond}_{g}.yaml")
        rng = np.random.default_rng([int(seed), k, g, {"plc": 3001, "orc": 3002, "obs": 0}[cond]])
        if cond == "obs":
            graph = observed
        elif cond == "plc":
            graph = rp.lp.placebo_graph(observed, rng, CALIB)
        else:
            graph, _ = rp.lp.oracle_graph(observed, rng, CALIB, au.REF[str(scene)]["objects"])
        rp.write_yaml(graph, dst)
        out.append(dst)
    return out


def stage(run, k, meta):
    seed = rp.P[run]["cfg"]["SEED"]
    gids = rp2.gids_for(run, k, meta)
    cur = rp.current_pos(run, k)
    sc_act = fastig.Scorer(cond_files(run, k, gids, "actual", seed), seed)
    kept, sc, total, order = sc_act.first_stage(seed, meta["nprior"], cur)
    scene = run.split("_")[1]
    refs = au.REF[str(int(scene))]["objects"]
    nodes = au.observed_nodes(run, k)
    m_prim, _ = au.mapped_masks(refs, nodes)
    un = ~m_prim
    geom, _ = au.ref_geom(refs, nodes)
    cam1 = fastig.cu.CameraConfig()
    U3 = (au.vis360(geom, kept, fastig.second_cfg()) & un).sum(1)
    Uc = (au.vis(geom, kept, cam1) & un).sum(1)
    d = np.linalg.norm(kept[:, :3] - cur[:3], axis=1)
    row = {"run": run, "arm": rp.arm_of(run), "scene": scene, "stage": k}
    for c in ("actual", "obs", "plc", "orc"):
        if c == "actual":
            ig = sc[:, 0] + sc[:, 1]
        else:
            s, _ = fastig.Scorer(cond_files(run, k, gids, c, seed), seed).score(kept, cam1)
            ig = s[:, 0] + s[:, 1]
        tot = ig - au.LAMBDA * d
        row[c] = {"rho_total_U360": au.rho(tot, U3), "rho_total_Ucone": au.rho(tot, Uc),
                  "rho_ig_U360": au.rho(ig, U3), "ig_zero_frac": float(np.mean(np.abs(ig) < 1e-12))}
    walked = rp2.walked_xy(run, k)
    if len(walked):
        dw = np.min(np.linalg.norm(kept[:, None, :2] - walked[None, :, :2], axis=2), axis=1)
        row["frontier_proxy"] = {"rho_dwalk_U360": au.rho(dw, U3), "rho_dwalk_Ucone": au.rho(dw, Uc)}
    return row


def job(a):
    try:
        return stage(*a)
    except Exception as e:
        import traceback
        return {"run": a[0], "stage": a[1], "error": repr(e), "tb": traceback.format_exc()[-1500:]}


def main():
    used = [json.loads(l) for l in open(os.path.join(OUT, "stages.jsonl"))]
    used = {(r["run"], r["stage"]) for r in used if r.get("top10_match") and "rho_total_U360" in r}
    jobs = []
    for run in sorted({r for r, _ in used}):
        meta = rp.stage_meta(run)
        jobs += [(run, k, meta[k]) for k in sorted(meta) if (run, k) in used]
    print("jobs", len(jobs), flush=True)
    with Pool(7) as pool, open(os.path.join(OUT, "cf_stages.jsonl"), "w") as f:
        for res in pool.imap_unordered(job, jobs):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(res["run"], res["stage"], res.get("error", ""), flush=True)


if __name__ == "__main__":
    main()
