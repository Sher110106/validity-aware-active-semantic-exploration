#!/usr/bin/env python3
"""Independent recompute of selected bench stages (verifier).

Own code for: wall test (exact grid-cell traversal by line crossings, not
sampling), unmapped rule, walked path, guess-set regeneration (live_policy
imported directly), R2 masking, R3/R5 novelty, R4 support, picks and regret.
Reused (no alternative): fastig candidate regeneration + IG scorer + frustum
visibility engine (reviewer A's replay of the author's scorer)."""
import importlib.util
import json
import os
import re
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, "/tmp/cvp_review/work_A")
import numpy as np  # noqa: E402
import yaml  # noqa: E402

import fastig  # noqa: E402

_spec = importlib.util.spec_from_file_location("lp_v", "/Users/sher/project/cvp/project/tools/live_policy/live_policy.py")
lp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lp)
CAL = lp.load_calibration()
OUT = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(OUT, "tmp")
RUNS = "/tmp/cvp_review/runs"
REF = json.load(open("/tmp/cvp_review/refs/oracle_sets.json"))["scenes"]
P = json.load(open("/tmp/cvp_review/work_A/parsed_runs.json"))
BUILD = {(r["run"], r["stage"]): r for r in map(json.loads, open("/tmp/cvp_bench/bench/build/stages.jsonl"))}


def V(x):
    return np.array(lp._vec(x), float)


def lab(s):
    return str(s).lower().replace("_", " ").strip()


def load(p):
    return yaml.safe_load(open(p))


# ---------- wall map ----------
WM = {}


def wallmap(scene):
    if scene not in WM:
        d = np.load(f"/tmp/cvp_bench/refs/{scene}_walls.npz")
        WM[scene] = (d["occ"].max(0) > 0, np.asarray(d["origin"], float), float(d["res"]))
    return WM[scene]


def seg_blocked(scene, a, b):
    """Exact: does segment a->b (2D) pass through any occupied cell? Cells
    entered are found from every crossing of a grid line; we test the cell at
    the midpoint between consecutive crossing parameters (plus a's own cell)."""
    occ, org, res = wallmap(scene)
    a = (np.asarray(a, float) - org) / res
    b = (np.asarray(b, float) - org) / res
    d = b - a
    ts = [0.0, 1.0]
    for ax in (0, 1):
        if abs(d[ax]) > 1e-12:
            lo, hi = sorted((a[ax], b[ax]))
            for m in range(int(np.ceil(lo)), int(np.floor(hi)) + 1):
                t = (m - a[ax]) / d[ax]
                if 0 < t < 1:
                    ts.append(t)
    ts = np.unique(ts)
    mids = np.concatenate([[0.0], (ts[:-1] + ts[1:]) / 2])
    pts = a[None, :] + mids[:, None] * d[None, :]
    ij = np.floor(pts).astype(int)
    ok = (ij[:, 0] >= 0) & (ij[:, 0] < occ.shape[0]) & (ij[:, 1] >= 0) & (ij[:, 1] < occ.shape[1])
    ij = ij[ok]
    return bool(occ[ij[:, 0], ij[:, 1]].any())


def wall_vis_loop(scene, cxy, oxy):
    """Reference (slow) version: exact traversal per segment."""
    out = np.zeros((len(cxy), len(oxy)), bool)
    for n, c in enumerate(cxy):
        for t, o in enumerate(oxy):
            L = float(np.hypot(*(o - c)))
            if L < 0.1 or L > 4.0:
                continue
            e = c + (o - c) * max(L - 0.15, 0.0) / L
            out[n, t] = not seg_blocked(scene, c, e)
    return out


def wall_vis(scene, cxy, oxy):
    """Vectorised exact traversal: the cells a segment passes through are the
    cell of its start plus the cell at the midpoint between each pair of
    consecutive grid-line crossings."""
    occ, org, res = wallmap(scene)
    cxy = np.asarray(cxy, float); oxy = np.asarray(oxy, float)
    D = oxy[None] - cxy[:, None]
    L = np.hypot(D[..., 0], D[..., 1])
    nn, tt = np.nonzero((L >= 0.1) & (L <= 4.0))
    out = np.zeros(L.shape, bool)
    if not len(nn):
        return out
    a = (cxy[nn] - org) / res
    f = np.maximum(L[nn, tt] - 0.15, 0.0) / L[nn, tt]
    b = (cxy[nn] + D[nn, tt] * f[:, None] - org) / res
    d = b - a
    K = 84
    ts = [np.zeros((len(nn), 1)), np.ones((len(nn), 1))]
    for ax in (0, 1):
        lo = np.minimum(a[:, ax], b[:, ax])
        m = np.ceil(lo)[:, None] + np.arange(K)[None, :]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (m - a[:, ax:ax + 1]) / d[:, ax:ax + 1]
        t[~((t > 0) & (t < 1))] = np.nan
        ts.append(t)
    T = np.sort(np.concatenate(ts, 1), 1)  # nan last
    mid = np.concatenate([np.zeros((len(nn), 1)), (T[:, :-1] + T[:, 1:]) / 2], 1)
    pts = a[:, None, :] + mid[..., None] * d[:, None, :]
    ij = np.floor(np.nan_to_num(pts, nan=-1e9)).astype(np.int64)
    ok = np.isfinite(mid) & (ij[..., 0] >= 0) & (ij[..., 0] < occ.shape[0]) & (ij[..., 1] >= 0) & (ij[..., 1] < occ.shape[1])
    hit = np.zeros(ok.shape, bool)
    hit[ok] = occ[ij[..., 0][ok], ij[..., 1][ok]]
    blocked = hit.any(1)
    out[nn[~blocked], tt[~blocked]] = True
    return out


# ---------- state ----------
def obs_nodes(run, k):
    out = []
    for t in (0, 1):
        p = f"{RUNS}/{run}/stages/{k}/habitat_scene_graph_original_graph{t}.yaml"
        if os.path.exists(p):
            out += [n for n in load(p)["nodes"] if "position" in n]
    return out


def unmapped(refs, nodes):
    objs = [V(n["position"])[:2] for n in nodes if n.get("node_type") == "object"]
    st = [(lab(n["name"]), V(n["position"])[:2]) for n in nodes if n.get("node_type") == "structure"]
    un = []
    for o in refs:
        xy = np.array(o["position"][:2], float)
        m = any(np.hypot(*(xy - p)) <= 0.5 for p in objs) or any(
            L == lab(o["name"]) and np.hypot(*(xy - p)) <= 0.5 for L, p in st)
        un.append(not m)
    return np.array(un)


def cur_pos(run, k):
    if k == 0:
        return np.array(json.load(open(f"{RUNS}/{run}/stages/1/executed_path.json"))["world_frame_path"][0], float)
    return np.array(json.load(open(f"{RUNS}/{run}/stages/{k}/executed_path.json"))["world_frame_path"][-1], float)


def walked(run, k):
    pts = []
    for j in range(1, k + 1):
        p = f"{RUNS}/{run}/stages/{j}/executed_path.json"
        if os.path.exists(p):
            pts += [q[:2] for q in json.load(open(p))["world_frame_path"]]
    if not pts:
        pts = [cur_pos(run, k)[:2]]
    return np.array(pts, float)


def mind(xy, W):
    return np.sqrt(((xy[:, None, :] - W[None, :, :]) ** 2).sum(-1)).min(1)


def guessed(g, ids):
    return [n for n in g["nodes"] if n.get("node_type") == "object" and n["id"] not in ids and "position" in n]


def vis_engine(targets, occl, poses, cfg):
    geom = fastig.GraphGeom({"targets": targets, "occluders": occl})
    R, t, c = fastig.cam_frames(np.asarray(poses, float))
    v, z = fastig.visible(geom, R, t, c, cfg, fastig.frustum_normals(cfg))
    return v | z


def orient(o):
    import ast
    if o is None:
        return np.eye(3)
    return np.array(ast.literal_eval(o) if isinstance(o, str) else o, float)


def view360(targets, occl, xyz, cfg):
    acc = np.zeros((len(xyz), len(targets)), bool)
    for y in np.arange(0, 360, 30.0):
        acc |= vis_engine(targets, occl, np.column_stack([xyz[:, :3], np.full(len(xyz), y)]), cfg)
    return acc


def run_stage(run, k):
    b = BUILD[(run, k)]
    t0 = time.time()
    scene = run.split("_")[1]
    seed = P[run]["cfg"]["SEED"]
    gids = b["gids"]  # order from the build row; checked against top-10 below
    sd = f"{RUNS}/{run}/stages/{k}"
    cur = cur_pos(run, k)
    act = [f"{sd}/habitat_scene_graph_new_graph_{g}.yaml" for g in gids]
    # nprior: count prior first_stage calls: taken from parsed meta like the bench; reuse replay2 meta
    import replay2 as rp2  # noqa
    import replay as rp  # noqa
    meta = rp.stage_meta(run)[k]
    sc0 = fastig.Scorer(act, seed)
    kept, sc, total, order = sc0.first_stage(seed, meta["nprior"], cur)
    tops = P[run]["stages"][str(k)]["pose_tops"][-1]["top"]
    match = all(np.allclose(a, kept[i], atol=1e-6) for a, i in zip(tops, order[:10]))
    res = {"run": run, "stage": k, "n_cand": len(kept), "top10_match": bool(match)}
    refs = REF[str(int(scene))]["objects"]
    nodes = obs_nodes(run, k)
    un = unmapped(refs, nodes)
    rxy = np.array([o["position"][:2] for o in refs], float)
    wv = wall_vis(scene, kept[:, :2], rxy)
    Uw = (wv & un[None]).sum(1)
    tg = [{"id": i, "name": o["name"], "pos": np.array(o["position"], float), "dims": np.array(o["dimension"], float),
           "orient": np.eye(3)} for i, o in enumerate(refs)]
    cone = vis_engine(tg, [], kept, fastig.cu.CameraConfig())
    Uc = (wv & un[None] & cone).sum(1)
    res["Uwall_eq"] = int((Uw == np.array(b["Uwall"])).sum())
    res["Uwall_absdiff_max"] = int(np.abs(Uw - np.array(b["Uwall"])).max())
    res["Ucone_eq"] = int((Uc == np.array(b["Ucone"])).sum())
    res["n_unmapped_eq"] = int(un.sum()) == b["n_unmapped"]
    d = np.linalg.norm(kept[:, :3] - cur[:3], axis=1)
    W = walked(run, k)
    nov = np.minimum(mind(kept[:, :2], W), 4.0)
    tracks = sorted({g // 4 for g in gids})
    obs_p = {t: f"{sd}/habitat_scene_graph_original_graph{t}.yaml" for t in tracks}
    obs_g = {t: load(p) for t, p in obs_p.items()}
    obs_ids = {t: {n["id"] for n in g["nodes"]} for t, g in obs_g.items()}
    ridx = b["run_idx"]
    wd = os.path.join(TMP, f"{run}_{k}")
    os.makedirs(wd, exist_ok=True)
    G = {"actual": [load(f) for f in act], "none": [obs_g[g // 4] for g in gids]}
    F = {"actual": act, "none": [obs_p[g // 4] for g in gids]}
    salt = {"placebo_A": 1, "placebo_B": 2, "oracle": 3}
    for s, sl in salt.items():
        G[s], F[s] = [], []
        for g in gids:
            rng = np.random.default_rng([20261029, ridx, k, g, sl])
            gr = lp.oracle_graph(obs_g[g // 4], rng, CAL, refs)[0] if s == "oracle" else lp.placebo_graph(obs_g[g // 4], rng, CAL)
            p = os.path.join(wd, f"{s}_{g}.yaml")
            yaml.safe_dump(gr, open(p, "w"))
            G[s].append(gr)
            F[s].append(p)
    occl = []
    for n in nodes:
        if "dimension" in n and (n.get("node_type") == "structure" or (n.get("node_type") == "object" and "door" in str(n.get("name", "")).lower())):
            occl.append({"id": n["id"], "name": n.get("name"), "pos": V(n["position"]), "dims": V(n["dimension"]),
                         "orient": orient(n.get("orientation"))})
    cam1, cam2 = fastig.cu.CameraConfig(), fastig.second_cfg()
    picks, regs = {}, {}
    for s in ["actual", "none", "placebo_A", "placebo_B", "oracle"]:
        S, _ = fastig.Scorer(F[s], seed).score(kept, cam1)
        ig = S[:, 0] + S[:, 1]
        # R2: mask guessed objects within 3 m xy of walked path
        mfiles, nmask = [], 0
        for g, gr in zip(gids, G[s]):
            drop = {n["id"] for n in guessed(gr, obs_ids[g // 4]) if mind(V(n["position"])[None, :2], W)[0] <= 3.0}
            nmask += len(drop)
            g2 = dict(gr)
            g2["nodes"] = [n for n in gr["nodes"] if n["id"] not in drop]
            g2["edges"] = [e for e in (gr.get("edges") or []) if e[0] not in drop and e[1] not in drop]
            p = os.path.join(wd, f"m_{s}_{g}.yaml")
            yaml.safe_dump(g2, open(p, "w"))
            mfiles.append(p)
        if nmask:
            Sm, _ = fastig.Scorer(mfiles, seed).score(kept, cam1)
            igm = Sm[:, 0] + Sm[:, 1]
        else:
            igm = ig
        # R4
        items = []
        for g, gr in zip(gids, G[s]):
            for n in guessed(gr, obs_ids[g // 4]):
                items.append((g // 4, g, lab(n["name"]), V(n["position"]), V(n["dimension"]) if "dimension" in n else np.zeros(3),
                              orient(n.get("orientation"))))
        r4 = np.zeros(len(kept))
        if items:
            nmem = {t: sum(1 for g in gids if g // 4 == t) for t in tracks}
            sup = np.array([len({g2 for (t2, g2, L2, p2, _, _) in items if t2 == t and L2 == L and np.hypot(*(p2[:2] - p[:2])) <= 1.0}) / nmem[t]
                            for (t, g, L, p, _, _) in items])
            far = mind(np.array([it[3][:2] for it in items]), W) > 3.0
            sel = np.nonzero(far)[0]
            if len(sel):
                tg4 = [{"id": 900000 + i, "name": items[i][2], "pos": items[i][3], "dims": items[i][4], "orient": items[i][5]} for i in sel]
                v4 = view360(tg4, occl, kept, cam2)
                r4 = v4.astype(float) @ sup[sel]
        sc_ = {"R1": ig - 0.2 * d, "R2": igm - 0.2 * d, "R3": ig - 0.2 * d + 0.5 * nov, "R4": r4 - 0.2 * d, "R5": nov - 0.2 * d}
        picks[s] = {r: int(np.argmax(v)) for r, v in sc_.items()}
        regs[s] = {r: float(Uw.max() - Uw[i]) for r, i in picks[s].items()}
    r6 = np.random.default_rng([20261029, ridx, k, 0, 4]).integers(0, len(kept), 50)
    res["picks_eq"] = {s: {r: picks[s][r] == b["picks"][s][r] for r in picks[s]} for s in picks}
    res["mine_picks"] = picks
    res["build_picks"] = b["picks"]
    res["regret_eq"] = {s: {r: abs(regs[s][r] - b["regret"]["Uwall"][s][r]) < 1e-9 for r in regs[s]} for s in regs}
    res["r6_eq"] = bool((r6 == np.array(b["r6_picks"])).all())
    res["R1_actual_is_logged_best"] = picks["actual"]["R1"] == order[0]
    res["secs"] = round(time.time() - t0, 1)
    import shutil
    shutil.rmtree(wd, ignore_errors=True)
    return res


def job(a):
    return run_stage(*a)


if __name__ == "__main__":
    from multiprocessing import Pool
    todo = [tuple(a.rsplit(":", 1)) for a in sys.argv[1:]]
    todo = [(r, int(k)) for r, k in todo]
    with Pool(7) as pool, open(os.path.join(OUT, "verify_stages.jsonl"), "w") as f:
        for res in pool.imap_unordered(job, todo):
            f.write(json.dumps(res) + "\n")
            f.flush()
            bad = {s: [r for r, ok in v.items() if not ok] for s, v in res["picks_eq"].items()}
            print(res["run"], res["stage"], "match", res["top10_match"], "Uwall_eq", res["Uwall_eq"], "/", res["n_cand"],
                  "maxdiff", res["Uwall_absdiff_max"], "Ucone_eq", res["Ucone_eq"], "unm", res["n_unmapped_eq"],
                  "pick mismatches", {s: v for s, v in bad.items() if v}, "r6", res["r6_eq"], res["secs"], flush=True)
