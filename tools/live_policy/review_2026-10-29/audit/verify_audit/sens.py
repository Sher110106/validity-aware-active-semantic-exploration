"""Sensitivity reruns over all used stages, reusing audit.py functions read-only (fastig visibility):
 (a) unmapped radius 1.0 m instead of 0.5 m (code rule);
 (b) stop percentile among candidates near navigable floor (within 0.5 m xy of any walked path point
     from any run directory of the same scene), a check on the 'stops are on the floor' confound;
 (c) stop percentile against candidates within the same distance band from the current position.
No F1/AUC."""
import sys, os, json, glob
sys.dont_write_bytecode = True
sys.path.insert(0, "/tmp/cvp_review/audit/audit")
import numpy as np
import audit as au
from multiprocessing import Pool
rp, rp2, fastig = au.rp, au.rp2, au.fastig
OUT = "/tmp/cvp_review/audit/verify_audit"
NAV = {}
for sc in ("00853", "00871"):
    pts = []
    for p in glob.glob(f"/tmp/cvp_review/runs/*_{sc}_*/stages/*/executed_path.json"):
        pts += [q[:2] for q in json.load(open(p))["world_frame_path"]]
    NAV[sc] = np.array(pts)

def mapped_r(refs, nodes, r):
    rxy = np.array([o["position"][:2] for o in refs]); rl = [au.lab(o["name"]) for o in refs]
    obj = np.array([au.vec(n["position"])[:2] for n in nodes if n.get("node_type") == "object"]).reshape(-1, 2)
    st = [(au.lab(n["name"]), au.vec(n["position"])[:2]) for n in nodes if n.get("node_type") == "structure"]
    m = np.zeros(len(refs), bool)
    for i, (xy, L) in enumerate(zip(rxy, rl)):
        a = len(obj) and np.min(np.hypot(*(obj - xy).T)) <= r
        b = any(np.hypot(*(xy - p)) <= r for l, p in st if l == L)
        m[i] = bool(a) or b
    return m

def stage(run, k, meta):
    seed = rp.P[run]["cfg"]["SEED"]
    gids = rp2.gids_for(run, k, meta)
    files = [f"{rp.RUNS}/{run}/stages/{k}/habitat_scene_graph_new_graph_{g}.yaml" for g in gids]
    cur = rp.current_pos(run, k)
    kept, sc, total, order = fastig.Scorer(files, seed).first_stage(seed, meta["nprior"], cur)
    scene = run.split("_")[1]
    refs = au.REF[str(int(scene))]["objects"]; nodes = au.observed_nodes(run, k)
    geom, _ = au.ref_geom(refs, nodes)
    v3 = au.vis360(geom, kept, fastig.second_cfg())
    stop = np.array(json.load(open(f"{rp.RUNS}/{run}/stages/{k+1}/executed_path.json"))["world_frame_path"][-1], float)[:3]
    vs = au.vis360(geom, stop[None], fastig.second_cfg())[0]
    row = {"run": run, "arm": rp.arm_of(run), "scene": scene, "stage": k}
    for r in (0.5, 1.0):
        un = ~mapped_r(refs, nodes, r)
        U3 = (v3 & un).sum(1); us = int((vs & un).sum())
        row[f"r{r}"] = {"n_unmapped": int(un.sum()), "rho": au.rho(total, U3), "pct_stop": au.pct(us, U3)}
        if r == 0.5:
            dn = np.min(np.hypot(kept[:, None, 0] - NAV[scene][None, :, 0], kept[:, None, 1] - NAV[scene][None, :, 1]), axis=1)
            nav = dn <= 0.5
            row["nav_frac"] = float(nav.mean())
            row["pct_stop_nav"] = au.pct(us, U3[nav]) if nav.sum() >= 10 else None
            row["rho_nav"] = au.rho(total[nav], U3[nav]) if nav.sum() >= 10 else None
            row["U360_nav_mean"] = float(U3[nav].mean()) if nav.any() else None
            row["U360_offnav_mean"] = float(U3[~nav].mean()) if (~nav).any() else None
            ds = np.hypot(*(stop[:2] - cur[:2])); dc = np.hypot(kept[:, 0] - cur[0], kept[:, 1] - cur[1])
            band = np.abs(dc - ds) <= 1.0
            row["pct_stop_band"] = au.pct(us, U3[band]) if band.sum() >= 10 else None
    return row

def job(a):
    try: return stage(*a)
    except Exception as e:
        import traceback; return {"run": a[0], "stage": a[1], "error": repr(e), "tb": traceback.format_exc()[-1000:]}

if __name__ == "__main__":
    S = [json.loads(l) for l in open("/tmp/cvp_review/audit/audit/stages.jsonl")]
    used = {(r["run"], r["stage"]) for r in S if r.get("top10_match") and "rho_total_U360" in r}
    jobs = []
    for run in sorted({r for r, _ in used}):
        meta = rp.stage_meta(run)
        jobs += [(run, k, meta[k]) for k in sorted(meta) if (run, k) in used]
    with Pool(4) as pool, open(f"{OUT}/sens_stages.jsonl", "w") as f:
        for res in pool.imap_unordered(job, jobs):
            f.write(json.dumps(res) + "\n"); f.flush()
    print("done", len(jobs))
