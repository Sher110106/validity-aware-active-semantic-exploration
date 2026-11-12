#!/usr/bin/env python3
"""Objective audit: does ASP's first-stage viewpoint score rank candidate views
by how many true, not-yet-mapped reference objects they would show?

Per counted stage:
 1. Regenerate the 300 candidates and their first-stage scores with reviewer A's
    vectorized replay (work_A/fastig.py, imported read-only) and check the
    top-10 against the logged pose_log top-10 (same test as work_A/replay2.py).
 2. For each candidate: U_cone (scorer's first-stage camera at the candidate's
    own yaw: 90 deg, -10 deg pitch, 0.5-3.0 m) and U_360 (union over 12 yaws,
    30 deg apart, second-stage range 0.1-4.0 m) = number of unmapped oracle-set
    reference objects visible, centre-ray occlusion by the observed graphs'
    structure and door boxes (as calculate_uncertainty.py does).
 3. Spearman rho of ASP score (total = IG - 0.2 d, and IG alone) with U_360, U_cone.
 4. U_360 and percentile for the live stop (last point of stages/(k+1)
    executed_path world_frame_path), the logged first-stage best, and the
    logged second-stage pick.
 5. Yardstick: of unmapped objects in the live stop's U_360, the share present
    (same label within 0.5 m xy, object or structure) in stage k+1's observed
    graphs, against unmapped objects not in view.

Unmapped (primary, = live_policy.oracle_eligible without the reach test):
more than 0.5 m (xy) from every observed object node of any label and from
every same-label structure node, in both observed graphs. Variant 'sl':
more than 0.5 m from every same-label object or structure node.
No F1/AUC is computed. Outputs: stages.jsonl in this directory.
"""
import glob
import json
import os
import sys
import warnings
from multiprocessing import Pool

sys.dont_write_bytecode = True
sys.path.insert(0, "/tmp/cvp_review/work_A")
import numpy as np  # noqa: E402

np.set_printoptions(legacy="1.25")
from scipy.stats import spearmanr  # noqa: E402

import fastig  # noqa: E402
import replay as rp  # noqa: E402
import replay2 as rp2  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
REF = json.load(open("/tmp/cvp_review/refs/oracle_sets.json"))["scenes"]
LAMBDA = 0.2
YAWS = np.arange(0.0, 360.0, 30.0)
A_MATCH = {}
for line in open("/tmp/cvp_review/work_A/replay2_results.jsonl"):
    j = json.loads(line)
    if "error" not in j:
        A_MATCH[(j["run"], j["stage"])] = j["top10_match"]


def lab(n):
    return str(n).lower().replace("_", " ").strip()


def vec(v):
    return np.array(rp.lp._vec(v), dtype=float)


def observed_nodes(run, k):
    out = []
    for t in (0, 1):
        p = f"{rp.RUNS}/{run}/stages/{k}/habitat_scene_graph_original_graph{t}.yaml"
        if os.path.exists(p):
            out += [n for n in rp.load(p)["nodes"] if "position" in n]
    return out


def mapped_masks(refs, nodes):
    """(primary_mapped, samelabel_mapped) bool arrays over refs."""
    rxy = np.array([o["position"][:2] for o in refs])
    rl = [lab(o["name"]) for o in refs]
    obj = [(lab(n["name"]), vec(n["position"])[:2]) for n in nodes if n.get("node_type") == "object"]
    st = [(lab(n["name"]), vec(n["position"])[:2]) for n in nodes if n.get("node_type") == "structure"]
    prim = np.zeros(len(refs), bool)
    sl = np.zeros(len(refs), bool)
    r2 = 0.5 ** 2
    for i, (xy, L) in enumerate(zip(rxy, rl)):
        near_any_obj = any(((xy - p) ** 2).sum() <= r2 for _, p in obj)
        near_sl_obj = any(((xy - p) ** 2).sum() <= r2 for l2, p in obj if l2 == L)
        near_sl_st = any(((xy - p) ** 2).sum() <= r2 for l2, p in st if l2 == L)
        prim[i] = near_any_obj or near_sl_st
        sl[i] = near_sl_obj or near_sl_st
    return prim, sl


def ref_geom(refs, nodes):
    targets = [{"id": 100000 + i, "name": o["name"], "pos": np.array(o["position"], float),
                "dims": np.array(o["dimension"], float), "orient": np.eye(3)} for i, o in enumerate(refs)]
    occ = []
    for n in nodes:
        if n.get("node_type") not in ("object", "structure") or "dimension" not in n:
            continue
        if n.get("node_type") == "structure" or "door" in str(n.get("name", "")).lower():
            o = n.get("orientation")
            occ.append({"id": n["id"], "name": n.get("name"), "pos": vec(n["position"]), "dims": vec(n["dimension"]),
                        "orient": eval_orient(o)})
    return fastig.GraphGeom({"targets": targets, "occluders": occ}), len(occ)


def eval_orient(o):
    import ast
    if o is None:
        return np.eye(3)
    return np.array(ast.literal_eval(o) if isinstance(o, str) else o, float)


def vis(geom, poses, cfg):
    poses = np.asarray(poses, float)
    R, t, cpos = fastig.cam_frames(poses)
    v, z = fastig.visible(geom, R, t, cpos, cfg, fastig.frustum_normals(cfg))
    return v | z


def vis360(geom, xyz, cfg):
    xyz = np.asarray(xyz, float)
    acc = np.zeros((len(xyz), geom.T), bool)
    for y in YAWS:
        poses = np.column_stack([xyz[:, :3], np.full(len(xyz), y)])
        acc |= vis(geom, poses, cfg)
    return acc


def rho(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = spearmanr(a, b).statistic
    return None if not np.isfinite(r) else float(r)


def pct(u, U):
    U = np.asarray(U)
    return float((np.sum(U < u) + 0.5 * np.sum(U == u)) / len(U))


def stage(run, k, meta):
    sd = f"{rp.RUNS}/{run}/stages/{k}"
    scene = run.split("_")[1]
    seed = rp.P[run]["cfg"]["SEED"]
    gids = rp2.gids_for(run, k, meta)
    files = rp.build_condition_files(run, k, gids, "actual", seed, None)
    cur = rp.current_pos(run, k)
    scorer = fastig.Scorer(files, seed)
    kept, sc, total, order = scorer.first_stage(seed, meta["nprior"], cur)
    tops = rp.P[run]["stages"][str(k)]["pose_tops"][-1]["top"]
    top_rep = [kept[i] for i in order[:10]]
    match = len(tops) == len(top_rep) and all(np.allclose(a, b, atol=1e-6) for a, b in zip(tops, top_rep))
    row = {"run": run, "arm": rp.arm_of(run), "scene": scene, "seed": seed, "stage": k, "n_cand": int(len(kept)),
           "top10_match": bool(match), "A_top10_match": A_MATCH.get((run, k))}
    nxt = f"{rp.RUNS}/{run}/stages/{k + 1}/executed_path.json"
    if not match or len(kept) == 0:
        return row
    if not os.path.exists(nxt):
        row["drop"] = "no stages/(k+1)/executed_path.json"
        return row
    refs = REF[str(int(scene))]["objects"]
    nodes = observed_nodes(run, k)
    m_prim, m_sl = mapped_masks(refs, nodes)
    un, un_sl = ~m_prim, ~m_sl
    geom, n_occ = ref_geom(refs, nodes)
    cam1 = fastig.cu.CameraConfig()
    cam2 = fastig.second_cfg()
    vc = vis(geom, kept, cam1)
    v3 = vis360(geom, kept, cam2)
    Uc, U3 = (vc & un).sum(1), (v3 & un).sum(1)
    Uc_sl, U3_sl = (vc & un_sl).sum(1), (v3 & un_sl).sum(1)
    ig = sc[:, 0] + sc[:, 1]
    d = np.linalg.norm(kept[:, :3] - cur[:3], axis=1)
    row.update({"n_ref": len(refs), "n_unmapped": int(un.sum()), "n_unmapped_sl": int(un_sl.sum()), "n_occluders": n_occ,
                "U360_mean": float(U3.mean()), "U360_median": float(np.median(U3)), "U360_max": int(U3.max()),
                "U360_zero_frac": float(np.mean(U3 == 0)), "Ucone_mean": float(Uc.mean()),
                "Ucone_zero_frac": float(np.mean(Uc == 0)),
                "rho_total_U360": rho(total, U3), "rho_total_Ucone": rho(total, Uc),
                "rho_ig_U360": rho(ig, U3), "rho_ig_Ucone": rho(ig, Uc),
                "rho_negdist_U360": rho(-d, U3),
                "rho_total_U360_sl": rho(total, U3_sl), "rho_total_Ucone_sl": rho(total, Uc_sl)})
    # live stop, logged first-stage best, logged second-stage pick
    stop = np.array(json.load(open(nxt))["world_frame_path"][-1], float)[:3]
    best = np.array(tops[0], float)
    fin = rp.P[run]["stages"][str(k)]["pose_finals"][-1]
    pts = {"stop": stop, "best": best[:3]}
    if fin.get("final"):
        fpts = np.array(fin["final"], float)
        j = int(np.argmin(np.hypot(fpts[:, 0] - stop[0], fpts[:, 1] - stop[1])))
        pts["final"] = fpts[j, :3]
    names = list(pts)
    vp = vis360(geom, np.array([pts[n] for n in names]), cam2)
    for i, n in enumerate(names):
        u = int((vp[i] & un).sum())
        row[f"U360_{n}"] = u
        row[f"pct_{n}"] = pct(u, U3)
        row[f"gt_median_{n}"] = None if u == np.median(U3) else bool(u > np.median(U3))
        row[f"xy_{n}"] = pts[n][:2].tolist()
    row["U360_sl_stop"] = int((vp[0] & un_sl).sum())
    row["pct_sl_stop"] = pct(row["U360_sl_stop"], U3_sl)
    row["Ucone_best"] = int(Uc[order[0]])
    row["pct_cone_best"] = pct(row["Ucone_best"], Uc)
    row["stop_to_best_m"] = float(np.hypot(*(stop[:2] - best[:2])))
    if "final" in pts:
        row["stop_to_final_m"] = float(np.hypot(*(stop[:2] - pts["final"][:2])))
    row["stop_to_cur_m"] = float(np.hypot(*(stop[:2] - cur[:2])))
    # yardstick: mapped at stage k+1 ?
    nodes_next = observed_nodes(run, k + 1)
    if nodes_next:
        m2_prim, m2_sl = mapped_masks(refs, nodes_next)
        inv = vp[0] & un
        outv = (~vp[0]) & un
        row["yard"] = {"n_in": int(inv.sum()), "in_mapped_sl": int((inv & m2_sl).sum()),
                       "in_mapped_any": int((inv & m2_prim).sum()),
                       "n_out": int(outv.sum()), "out_mapped_sl": int((outv & m2_sl).sum()),
                       "out_mapped_any": int((outv & m2_prim).sum())}
    else:
        row["yard"] = None
    return row


def job(a):
    try:
        return stage(*a)
    except Exception as e:
        import traceback
        return {"run": a[0], "stage": a[1], "error": repr(e), "tb": traceback.format_exc()[-1500:]}


def main():
    runs = [l.strip() for l in open("/tmp/cvp_review/analysis_pre/runs.txt") if l.strip()]
    if len(sys.argv) > 1:
        runs = [r for r in runs if any(s in r for s in sys.argv[1:])]
    jobs, skipped = [], []
    for run in runs:
        meta = rp.stage_meta(run)
        for k, m in sorted(meta.items()):
            if k > 0 and not os.path.exists(f"{rp.RUNS}/{run}/stages/{k}/executed_path.json"):
                skipped.append((run, k, "no current position (stages/k/executed_path.json)"))
                continue
            if k == 0 and not os.path.exists(f"{rp.RUNS}/{run}/stages/1/executed_path.json"):
                skipped.append((run, k, "no stages/1/executed_path.json"))
                continue
            if not glob.glob(f"{rp.RUNS}/{run}/stages/{k}/habitat_scene_graph_new_graph_*.yaml"):
                skipped.append((run, k, "no hypothesis files"))
                continue
            jobs.append((run, k, m))
    print("jobs", len(jobs), "skipped", len(skipped), flush=True)
    out = os.path.join(OUT, "stages.jsonl" if len(sys.argv) == 1 else "stages_test.jsonl")
    with Pool(7) as pool, open(out, "w") as f:
        for res in pool.imap_unordered(job, jobs):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(res["run"], res["stage"], res.get("error") or res.get("top10_match"), res.get("rho_total_U360"),
                  flush=True)
    json.dump(skipped, open(os.path.join(OUT, "skipped_before_replay.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
