#!/usr/bin/env python3
"""Sensitivity: U_360 with 12 yaws (30 deg) vs 36 yaws (10 deg) on 24 stages
(the first used stage >= 3 of each run). Writes yaw_sensitivity.json."""
import json, os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import audit as au
rp, rp2, fastig = au.rp, au.rp2, au.fastig
used = [json.loads(l) for l in open(os.path.join(au.OUT, "stages.jsonl"))]
used = [r for r in used if r.get("top10_match") and "rho_total_U360" in r]
pick = {}
for r in sorted(used, key=lambda r: (r["run"], r["stage"])):
    if r["stage"] >= 3 and r["run"] not in pick:
        pick[r["run"]] = r
out = []
for run, r in pick.items():
    k = r["stage"]; meta = rp.stage_meta(run)[k]; seed = rp.P[run]["cfg"]["SEED"]
    gids = rp2.gids_for(run, k, meta)
    files = [f"{rp.RUNS}/{run}/stages/{k}/habitat_scene_graph_new_graph_{g}.yaml" for g in gids]
    cur = rp.current_pos(run, k)
    kept, sc, total, order = fastig.Scorer(files, seed).first_stage(seed, meta["nprior"], cur)
    refs = au.REF[str(int(r["scene"]))]["objects"]; nodes = au.observed_nodes(run, k)
    un = ~au.mapped_masks(refs, nodes)[0]; geom, _ = au.ref_geom(refs, nodes)
    U12 = (au.vis360(geom, kept, fastig.second_cfg()) & un).sum(1)
    au.YAWS = np.arange(0.0, 360.0, 10.0)
    U36 = (au.vis360(geom, kept, fastig.second_cfg()) & un).sum(1)
    au.YAWS = np.arange(0.0, 360.0, 30.0)
    out.append({"run": run, "stage": k, "rho_U12_U36": au.rho(U12, U36), "mean_U12": float(U12.mean()),
                "mean_U36": float(U36.mean()), "rho_total_U12": au.rho(total, U12), "rho_total_U36": au.rho(total, U36)})
    print(out[-1], flush=True)
json.dump(out, open(os.path.join(au.OUT, "yaw_sensitivity.json"), "w"), indent=1)
print("median rho_U12_U36", np.median([o["rho_U12_U36"] for o in out]),
      "max |d rho_total|", max(abs(o["rho_total_U12"] - o["rho_total_U36"]) for o in out))
