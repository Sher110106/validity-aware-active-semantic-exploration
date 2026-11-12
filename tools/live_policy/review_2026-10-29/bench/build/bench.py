#!/usr/bin/env python3
"""Offline decision bench (PREREGISTRATION_BENCH.md, sha256 2571a7ef...).

Per stage (the 384 audit stages whose replayed first-stage top-10 matches the log):
  - regenerate the 300 first-stage candidates with reviewer A's vectorised
    replay of the author's scorer (work_A/fastig.py, imported read-only) and
    re-check the top-10 against the logged pose_log top-10;
  - yardstick U_wall: unmapped reference objects (oracle_sets.json, audit's
    primary 'not yet mapped' rule) whose xy distance from the candidate is in
    [0.1, 4.0] m and whose 2D segment from the candidate to the object centre
    crosses no occupied cell of the HM3D wall map (union of the 0.6/1.1/1.6 m
    slices), ignoring the last 0.15 m before the object;
  - U_wall_cone: U_wall restricted to the first-stage camera frustum at the
    candidate's yaw (author's first-stage camera, frustum/range test only);
  - rules R1-R6 under guess sets actual / none / placebo A / placebo B / oracle;
  - regret = max_c U(c) - U(pick); R6 = mean over 50 uniform draws;
  - yardstick check at the robot's real stop (U_wall vs the audit's U_360).
Writes stages.jsonl in this folder. Scratch hypothesis YAMLs go to ./tmp and
are deleted after each stage (they are reproducible from the recorded seeds).
"""
import json
import os
import shutil
import sys
import time
from multiprocessing import Pool

sys.dont_write_bytecode = True
sys.path.insert(0, "/tmp/cvp_review/audit/audit")
import numpy as np  # noqa: E402

import audit as au  # noqa: E402  (read-only import; also imports work_A replay/fastig)

rp, rp2, fastig = au.rp, au.rp2, au.fastig
OUT = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(OUT, "tmp")
CALIB = rp.lp.load_calibration()
LAMBDA = 0.2
BENCH_SEED = 20261029
SALT = {"placebo_A": 1, "placebo_B": 2, "oracle": 3, "R6": 4}
SETS = ["actual", "none", "placebo_A", "placebo_B", "oracle"]
RULES = ["R1", "R2", "R3", "R4", "R5", "R6"]
N_R6 = 50
MASK_M = 3.0
SUPPORT_M = 1.0
NOVELTY_CAP = 4.0
NOVELTY_W = 0.5
UMIN, UMAX, TAIL = 0.1, 4.0, 0.15
STEP = 0.005  # segment sampling step (m), res/10

RUNS = [l.strip() for l in open("/tmp/cvp_review/analysis_pre/runs.txt") if l.strip()]
RUN_IDX = {r: i for i, r in enumerate(RUNS)}
WALLS = {}


def walls(scene, layer="union"):
    key = (scene, layer)
    if key not in WALLS:
        d = np.load(f"/tmp/cvp_bench/refs/{scene}_walls.npz")
        occ = d["occ"].astype(bool)
        grid = occ.any(0) if layer == "union" else occ[list(np.round(d["heights"], 2)).index(layer)]
        WALLS[key] = (grid, np.asarray(d["origin"], float), float(d["res"]))
    return WALLS[key]


def wall_visible(scene, cxy, oxy, head=0.0, half=None, layer="union"):
    """(N,T) bool: xy distance in [UMIN, UMAX] and the segment c->o, minus its
    last TAIL metres, crosses no occupied wall cell. Primary (pre-registered):
    head=0, half=None, layer='union' (any of the 0.6/1.1/1.6 m slices).
    Sensitivity only: head>0 also ignores the first `head` metres; half (T,2)
    ignores samples inside the object's own axis-aligned xy footprint; layer
    picks one slice height."""
    occ, org, res = walls(scene, layer)
    cxy = np.asarray(cxy, float)
    oxy = np.asarray(oxy, float)
    diff = oxy[None, :, :] - cxy[:, None, :]
    L = np.linalg.norm(diff, axis=-1)
    inr = (L >= UMIN) & (L <= UMAX)
    out = np.zeros(L.shape, bool)
    nn, tt = np.nonzero(inr)
    if not len(nn):
        return out
    Lc = np.maximum(L[nn, tt] - TAIL, 0.0)
    nmax = int(np.ceil(UMAX / STEP)) + 1
    s = np.arange(nmax) * STEP  # (S,)
    u = diff[nn, tt] / np.maximum(L[nn, tt], 1e-12)[:, None]
    blocked = np.zeros(len(nn), bool)
    CH = 4000
    for a in range(0, len(nn), CH):
        b = slice(a, a + CH)
        # samples at 0, STEP, 2*STEP, ... clamped to the end of the checked part
        tpar = np.minimum(s[None, :], Lc[b, None])
        pts = cxy[nn[b]][:, None, :] + u[b][:, None, :] * tpar[:, :, None]
        ij = np.floor((pts - org) / res).astype(np.int64)
        ok = (ij[..., 0] >= 0) & (ij[..., 0] < occ.shape[0]) & (ij[..., 1] >= 0) & (ij[..., 1] < occ.shape[1])
        ii = np.clip(ij[..., 0], 0, occ.shape[0] - 1)
        jj = np.clip(ij[..., 1], 0, occ.shape[1] - 1)
        hit = occ[ii, jj] & ok
        if head > 0:
            hit &= tpar >= head
        if half is not None:
            rel = np.abs(pts - oxy[tt[b]][:, None, :])
            hit &= ~np.all(rel <= half[tt[b]][:, None, :], axis=-1)
        blocked[b] = hit.any(axis=1)
    out[nn[~blocked], tt[~blocked]] = True
    return out


# sensitivity variants of the wall test (not pre-registered; no decision uses them)
VARIANTS = {"head015": dict(head=0.15), "own_footprint": dict(half=True), "head015_footprint": dict(head=0.15, half=True),
            "slice_1p1": dict(layer=1.1)}


def wall_variants(scene, cxy, oxy, halfxy):
    out = {}
    for name, kw in VARIANTS.items():
        kw = dict(kw)
        if kw.get("half"):
            kw["half"] = halfxy
        out[name] = wall_visible(scene, cxy, oxy, **kw)
    return out


def cone_mask(kept, refs):
    """(N,T): reference object inside the author's first-stage camera frustum at
    the candidate's yaw (frustum and range test on centre+corners, no occluders)."""
    tg = [{"id": i, "name": o["name"], "pos": np.array(o["position"], float), "dims": np.array(o["dimension"], float),
           "orient": np.eye(3)} for i, o in enumerate(refs)]
    geom = fastig.GraphGeom({"targets": tg, "occluders": []})
    return au.vis(geom, kept, fastig.cu.CameraConfig())


def walked(run, k, cur):
    w = rp2.walked_xy(run, k)
    if len(w) == 0:
        w = np.asarray(cur[:2], float)[None, :]
    return np.asarray(w, float)


def min_dist(pxy, wxy):
    if len(pxy) == 0:
        return np.zeros(0)
    return np.sqrt(((pxy[:, None, :] - wxy[None, :, :]) ** 2).sum(-1)).min(1)


def write_yaml(g, path):
    rp.write_yaml(g, path)
    return path


def guessed(graph, obs_ids):
    return [n for n in graph["nodes"] if n.get("node_type") == "object" and n["id"] not in obs_ids and "position" in n]


def mask_graph(graph, obs_ids, wxy):
    """Drop guessed objects within MASK_M (xy) of the walked path, and their edges."""
    drop = set()
    for n in guessed(graph, obs_ids):
        xy = np.array(rp.lp._vec(n["position"])[:2])[None, :]
        if min_dist(xy, wxy)[0] <= MASK_M:
            drop.add(n["id"])
    g2 = {"nodes": [n for n in graph["nodes"] if n["id"] not in drop],
          "edges": [e for e in (graph.get("edges") or []) if e[0] not in drop and e[1] not in drop]}
    for key in graph:
        if key not in g2:
            g2[key] = graph[key]
    return g2, len(drop)


def r4_score(graphs, gids, obs_ids, obs_nodes, kept, wxy):
    """Expected discovery: sum over guessed objects in the full-turn view (12 yaws,
    0.1-4.0 m, observed occluders) lying > MASK_M m from walked ground, of member
    support = share of the track's members with a same-label guess within 1 m (xy)."""
    items = []  # (track, gid, label, pos, dims, orient)
    for g, gr in zip(gids, graphs):
        t = g // 4
        for n in guessed(gr, obs_ids[t]):
            items.append((t, g, au.lab(n["name"]), np.array(rp.lp._vec(n["position"]), float),
                          np.array(rp.lp._vec(n["dimension"]), float) if "dimension" in n else np.zeros(3),
                          au.eval_orient(n.get("orientation"))))
    n_items = len(items)
    if not items:
        return np.zeros(len(kept)), {"n_guess": 0, "n_far": 0}
    members = {}
    for g in gids:
        members.setdefault(g // 4, []).append(g)
    sup = np.zeros(n_items)
    for i, (t, g, L, p, _, _) in enumerate(items):
        hit = set()
        for (t2, g2, L2, p2, _, _) in items:
            if t2 == t and L2 == L and np.hypot(*(p2[:2] - p[:2])) <= SUPPORT_M:
                hit.add(g2)
        sup[i] = len(hit) / len(members[t])
    far = min_dist(np.array([it[3][:2] for it in items]), wxy) > MASK_M
    sel = [i for i in range(n_items) if far[i]]
    if not sel:
        return np.zeros(len(kept)), {"n_guess": n_items, "n_far": 0}
    tg = [{"id": 200000 + i, "name": items[i][2], "pos": items[i][3], "dims": items[i][4], "orient": items[i][5]}
          for i in sel]
    occ = []
    for n in obs_nodes:
        if n.get("node_type") not in ("object", "structure") or "dimension" not in n:
            continue
        if n.get("node_type") == "structure" or "door" in str(n.get("name", "")).lower():
            occ.append({"id": n["id"], "name": n.get("name"), "pos": au.vec(n["position"]),
                        "dims": au.vec(n["dimension"]), "orient": au.eval_orient(n.get("orientation"))})
    geom = fastig.GraphGeom({"targets": tg, "occluders": occ})
    v = au.vis360(geom, kept, fastig.second_cfg())
    return v.astype(float) @ sup[sel], {"n_guess": n_items, "n_far": len(sel),
                                         "support_mean_far": float(sup[sel].mean())}


def stage(run, k, meta):
    t0 = time.time()
    scene = run.split("_")[1]
    seed = rp.P[run]["cfg"]["SEED"]
    ridx = RUN_IDX[run]
    gids = rp2.gids_for(run, k, meta)
    sd = f"{rp.RUNS}/{run}/stages/{k}"
    cur = rp.current_pos(run, k)
    act_files = [f"{sd}/habitat_scene_graph_new_graph_{g}.yaml" for g in gids]
    scorer = fastig.Scorer(act_files, seed)
    kept, sc, total, order = scorer.first_stage(seed, meta["nprior"], cur)
    tops = rp.P[run]["stages"][str(k)]["pose_tops"][-1]["top"]
    top_rep = [kept[i] for i in order[:10]]
    match = len(tops) == len(top_rep) and all(np.allclose(a, b, atol=1e-6) for a, b in zip(tops, top_rep))
    row = {"run": run, "arm": rp.arm_of(run), "scene": scene, "seed": seed, "stage": k, "run_idx": ridx,
           "n_cand": int(len(kept)), "top10_match": bool(match), "gids": gids}
    if not match or len(kept) == 0:
        row["drop"] = "top10 mismatch" if len(kept) else "no candidates"
        return row
    refs = au.REF[str(int(scene))]["objects"]
    nodes = au.observed_nodes(run, k)
    m_prim, _ = au.mapped_masks(refs, nodes)
    un = ~m_prim
    rxy = np.array([o["position"][:2] for o in refs], float)
    # yardsticks over candidates
    wv = wall_visible(scene, kept[:, :2], rxy)
    Uw_set = wv & un[None, :]
    cone = cone_mask(kept, refs)
    Uw = Uw_set.sum(1)
    Uc = (Uw_set & cone).sum(1)
    halfxy = np.array([np.asarray(o["dimension"][:2], float) / 2 for o in refs])
    wvar = wall_variants(scene, kept[:, :2], rxy, halfxy)
    occ_, org_, res_ = walls(scene)
    ij_ = np.floor((kept[:, :2] - org_) / res_).astype(int)
    inb = (ij_[:, 0] >= 0) & (ij_[:, 0] < occ_.shape[0]) & (ij_[:, 1] >= 0) & (ij_[:, 1] < occ_.shape[1])
    row["cand_in_wall_cell_frac"] = float(np.mean(inb & occ_[np.clip(ij_[:, 0], 0, occ_.shape[0] - 1),
                                                           np.clip(ij_[:, 1], 0, occ_.shape[1] - 1)]))
    row["cand_outside_grid_frac"] = float(np.mean(~inb))
    row["Uwall_var"] = {n: (v & un[None, :]).sum(1).tolist() for n, v in wvar.items()}
    geom_obs, _ = au.ref_geom(refs, nodes)
    v360 = au.vis360(geom_obs, kept, fastig.second_cfg())
    U3 = (v360 & un).sum(1)
    d = np.linalg.norm(kept[:, :3] - cur[:3], axis=1)
    wxy = walked(run, k, cur)
    nov = np.minimum(min_dist(kept[:, :2], wxy), NOVELTY_CAP)
    row.update({"n_ref": len(refs), "n_unmapped": int(un.sum()), "n_walk_pts": int(len(wxy)),
                "Uwall": Uw.tolist(), "Ucone": Uc.tolist(), "U360": U3.tolist(),
                "rho_Uwall_U360": au.rho(Uw, U3), "rho_total_Uwall": au.rho(total, Uw)})
    # guess sets
    obs_paths = {t: f"{sd}/habitat_scene_graph_original_graph{t}.yaml" for t in sorted({g // 4 for g in gids})}
    obs_graph = {t: rp.load(p) for t, p in obs_paths.items()}
    obs_ids = {t: {n["id"] for n in g["nodes"]} for t, g in obs_graph.items()}
    wdir = os.path.join(TMP, f"{run}_{k}")
    os.makedirs(wdir, exist_ok=True)
    graphs, files, seeds, orc_info = {}, {}, {}, []
    graphs["actual"] = [rp.load(f) for f in act_files]
    files["actual"] = act_files
    graphs["none"] = [obs_graph[g // 4] for g in gids]
    files["none"] = [obs_paths[g // 4] for g in gids]
    for s in ("placebo_A", "placebo_B", "oracle"):
        graphs[s], files[s], seeds[s] = [], [], {}
        for g in gids:
            key = [BENCH_SEED, ridx, k, g, SALT[s]]
            seeds[s][str(g)] = key
            rng = np.random.default_rng(key)
            if s == "oracle":
                gr, info = rp.lp.oracle_graph(obs_graph[g // 4], rng, CALIB, refs)
                orc_info.append({"gid": g, **info})
            else:
                gr = rp.lp.placebo_graph(obs_graph[g // 4], rng, CALIB)
            graphs[s].append(gr)
            files[s].append(write_yaml(gr, os.path.join(wdir, f"{s}_{g}.yaml")))
    seeds["R6"] = [BENCH_SEED, ridx, k, 0, SALT["R6"]]
    row["seeds"] = seeds
    row["oracle_info"] = orc_info
    cam1 = fastig.cu.CameraConfig()
    scores, info = {}, {}
    for s in SETS:
        if s == "actual":
            ig = sc[:, 0] + sc[:, 1]
        else:
            S, _ = fastig.Scorer(files[s], seed).score(kept, cam1)
            ig = S[:, 0] + S[:, 1]
        n_guess = sum(len(guessed(gr, obs_ids[g // 4])) for g, gr in zip(gids, graphs[s]))
        if n_guess:
            mg, nm = [], 0
            for g, gr in zip(gids, graphs[s]):
                g2, c = mask_graph(gr, obs_ids[g // 4], wxy)
                nm += c
                mg.append(write_yaml(g2, os.path.join(wdir, f"masked_{s}_{g}.yaml")))
            if nm:
                S, _ = fastig.Scorer(mg, seed).score(kept, cam1)
                ig_m = S[:, 0] + S[:, 1]
            else:
                ig_m = ig
        else:
            nm, ig_m = 0, ig
        r4, r4i = r4_score(graphs[s], gids, obs_ids, nodes, kept, wxy)
        scores[s] = {"R1": ig - LAMBDA * d, "R2": ig_m - LAMBDA * d, "R3": ig - LAMBDA * d + NOVELTY_W * nov,
                     "R4": r4 - LAMBDA * d, "R5": nov - LAMBDA * d}
        info[s] = {"n_guess": int(n_guess), "n_masked": int(nm), "R4": r4i,
                   "ig_zero_frac": float(np.mean(np.abs(ig) < 1e-12)), "r4_zero_frac": float(np.mean(r4 == 0))}
    row["set_info"] = info
    r6 = np.random.default_rng(seeds["R6"]).integers(0, len(kept), N_R6)
    picks, reg = {}, {"Uwall": {}, "Ucone": {}}
    for s in SETS:
        picks[s] = {r: int(np.argmax(scores[s][r])) for r in ("R1", "R2", "R3", "R4", "R5")}
    for name, U in (("Uwall", Uw), ("Ucone", Uc)):
        mx = int(U.max())
        for s in SETS:
            reg[name][s] = {r: float(mx - U[picks[s][r]]) for r in picks[s]}
            reg[name][s]["R6"] = float(mx - U[r6].mean())
        row[f"{name}_max"] = mx
    row["picks"] = picks
    row["r6_picks"] = r6.tolist()
    row["regret"] = reg
    row["asp_logged_top1_idx"] = int(order[0])
    row["asp_R1_actual_matches_logged"] = bool(picks["actual"]["R1"] == order[0])
    # yardstick check at the real stop
    nxt = f"{rp.RUNS}/{run}/stages/{k + 1}/executed_path.json"
    stop = np.array(json.load(open(nxt))["world_frame_path"][-1], float)[:3]
    nodes_next = au.observed_nodes(run, k + 1)
    if nodes_next:
        _, m2_sl = au.mapped_masks(refs, nodes_next)
        in_w = wall_visible(scene, stop[None, :2], rxy)[0] & un
        in_3 = au.vis360(geom_obs, stop[None, :], fastig.second_cfg())[0] & un
        y = {}
        sv = {n: v[0] & un for n, v in wall_variants(scene, stop[None, :2], rxy, halfxy).items()}
        sv_l = [("Uwall_" + n, v) for n, v in sv.items()]
        for nm_, inv in [("Uwall", in_w), ("U360", in_3)] + sv_l:
            outv = (~inv) & un
            y[nm_] = {"n_in": int(inv.sum()), "in_mapped": int((inv & m2_sl).sum()),
                      "n_out": int(outv.sum()), "out_mapped": int((outv & m2_sl).sum())}
        row["yard"] = y
        occ, org, res = walls(scene)
        i, j = np.floor((stop[:2] - org) / res).astype(int)
        row["stop_in_wall_cell"] = bool(0 <= i < occ.shape[0] and 0 <= j < occ.shape[1] and occ[i, j])
    else:
        row["yard"] = None
    row["secs"] = round(time.time() - t0, 1)
    shutil.rmtree(wdir, ignore_errors=True)
    return row


def job(a):
    try:
        return stage(*a)
    except Exception as e:
        import traceback
        return {"run": a[0], "stage": a[1], "error": repr(e), "tb": traceback.format_exc()[-2000:]}


def main():
    used = [json.loads(l) for l in open("/tmp/cvp_review/audit/audit/stages.jsonl")]
    used = {(r["run"], r["stage"]) for r in used if r.get("top10_match") and "rho_total_U360" in r}
    only = sys.argv[1:]
    jobs = []
    for run in RUNS:
        meta = rp.stage_meta(run)
        jobs += [(run, k, meta[k]) for k in sorted(meta) if (run, k) in used]
    if only:
        jobs = [j for j in jobs if any(f"{j[0]}:{j[1]}" == o or (":" not in o and o in j[0]) for o in only)]
    print("jobs", len(jobs), flush=True)
    out = os.path.join(OUT, "stages.jsonl" if not only else "stages_test.jsonl")
    t0 = time.time()
    with Pool(int(os.environ.get("NPROC", 7))) as pool, open(out, "w") as f:
        for i, res in enumerate(pool.imap_unordered(job, jobs)):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(i + 1, res["run"], res["stage"], res.get("error") or res.get("drop") or res.get("secs"),
                  round(time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
