#!/usr/bin/env python3
"""Counterfactual replay of ASP's viewpoint score with the vectorized scorer
(fastig.py, verified equal to the pinned loop). See replay.py for the design.

Conditions (same observed graphs, same seed, same RNG call index):
  actual  - files the planner used (checked against pose_log top-10)
  obs     - every member = its track's observed graph
  plc_a, plc_b - two independent placebo draws (live_policy.placebo_graph)
  orc     - oracle_graph draws from the pool of true objects seen in e3 runs
Outputs one JSON line per stage to replay2_results.jsonl. No F1/AUC.
"""
import glob
import json
import os
import re
import sys
from multiprocessing import Pool

sys.path.insert(0, "/tmp/cvp_review/work_A")
import numpy as np  # noqa: E402

np.set_printoptions(legacy="1.25")
import fastig  # noqa: E402
import replay as rp  # noqa: E402

LAMBDA = 0.2
CONDS = ["actual", "obs", "plc_a", "plc_b", "orc"]


def gids_for(run, k, meta):
    sd = f"{rp.RUNS}/{run}/stages/{k}"
    gids_exist = sorted(int(re.search(r"_(\d+)\.yaml$", f).group(1))
                        for f in glob.glob(f"{sd}/habitat_scene_graph_new_graph_*.yaml"))
    order = meta.get("done_order")
    if rp.arm_of(run) in ("official", "filter_only") and order:
        seen = []
        for g in order:
            if g in gids_exist and g not in seen:
                seen.append(g)
        return seen + [g for g in gids_exist if g not in seen]
    return gids_exist


def top_k(total, k=10):
    return sorted(range(len(total)), key=lambda i: total[i], reverse=True)[:k]


def spearman(a, b):
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    if np.std(ra) == 0 or np.std(rb) == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def pred_positions(files, obs_ids_by_track, gids):
    out = []
    for f, g in zip(files, gids):
        for n in rp.load(f)["nodes"]:
            if n.get("node_type") == "object" and n["id"] not in obs_ids_by_track[g // 4] and "position" in n:
                out.append(rp.lp._vec(n["position"]))
    return np.array(out) if out else np.zeros((0, 3))


def walked_xy(run, k):
    pts = []
    for j in range(1, k + 1):
        p = f"{rp.RUNS}/{run}/stages/{j}/executed_path.json"
        if os.path.exists(p):
            pts += [q[:2] for q in json.load(open(p))["world_frame_path"]]
    return np.array(pts) if pts else np.zeros((0, 2))


def job(args):
    run, k, meta = args
    try:
        return stage(run, k, meta)
    except Exception as e:
        import traceback
        return {"run": run, "stage": k, "error": repr(e), "tb": traceback.format_exc()[-800:]}


def stage(run, k, meta):
    sd = f"{rp.RUNS}/{run}/stages/{k}"
    seed = rp.P[run]["cfg"]["SEED"]
    gids = gids_for(run, k, meta)
    wdir = os.path.join(rp.TMP, f"r2_{run}_{k}")
    os.makedirs(wdir, exist_ok=True)
    cur = rp.current_pos(run, k)
    files = {c: rp.build_condition_files(run, k, gids, c, seed, wdir) for c in CONDS}
    scorers = {c: fastig.Scorer(files[c], seed) for c in CONDS}
    kept, sc_act, total_act, order_act = scorers["actual"].first_stage(seed, meta["nprior"], cur)
    tops = rp.P[run]["stages"][str(k)]["pose_tops"][-1]["top"]
    top_rep = [kept[i] for i in order_act[:10]]
    match = len(tops) == len(top_rep) and all(np.allclose(a, b, atol=1e-6) for a, b in zip(tops, top_rep))
    res = {"run": run, "stage": k, "arm": rp.arm_of(run), "n_files": len(gids), "first_gid": gids[0],
           "n_cand": int(len(kept)), "top10_match": bool(match), "nprior": meta["nprior"],
           "cur": cur[:2].tolist()}
    if len(kept) == 0:
        return res
    cam1 = fastig.cu.CameraConfig()
    d = np.linalg.norm(kept[:, :3] - cur[:3], axis=1)
    S = {"actual": sc_act}
    for c in CONDS[1:]:
        S[c], _ = scorers[c].score(kept, cam1)
    ig = {c: S[c][:, 0] + S[c][:, 1] for c in CONDS}
    tot = {c: ig[c] - LAMBDA * d for c in CONDS}
    t10 = {c: top_k(tot[c]) for c in CONDS}
    a1 = kept[t10["actual"][0], :2]
    res["fixed"] = {}
    for c in CONDS:
        b1 = kept[t10[c][0], :2]
        res["fixed"][c] = {
            "top1_same": bool(t10[c][0] == t10["actual"][0]),
            "top1_dist": float(np.hypot(*(b1 - a1))),
            "top10_overlap": len(set(t10[c]) & set(t10["actual"])) / 10.0,
            "rho_total": spearman(tot[c], tot["actual"]),
            "rho_ig": spearman(ig[c], ig["actual"]),
            "ig_mean": float(np.mean(ig[c])), "ig_sd": float(np.std(ig[c])),
            "ig_zero_frac": float(np.mean(np.abs(ig[c]) < 1e-12)),
            "obj_mean": float(np.mean(S[c][:, 0])), "room_mean": float(np.mean(S[c][:, 1])),
        }
    # placebo-vs-placebo noise floor on the fixed set
    pb1 = kept[t10["plc_b"][0], :2]
    pa1 = kept[t10["plc_a"][0], :2]
    res["fixed_plc_a_vs_b"] = {"top1_same": bool(t10["plc_a"][0] == t10["plc_b"][0]),
                               "top1_dist": float(np.hypot(*(pa1 - pb1))),
                               "top10_overlap": len(set(t10["plc_a"]) & set(t10["plc_b"])) / 10.0,
                               "rho_total": spearman(tot["plc_a"], tot["plc_b"])}
    # variance decomposition of the actual total
    hyp = ig["actual"] - ig["obs"]
    base = ig["obs"]
    mv = -LAMBDA * d
    T = tot["actual"]

    def r2(x, y):
        return float(np.corrcoef(x, y)[0, 1] ** 2) if np.std(x) > 0 and np.std(y) > 0 else None

    res["var"] = {"total": float(np.var(T)), "move": float(np.var(mv)), "obs_ig": float(np.var(base)),
                  "hyp": float(np.var(hyp)), "cov_mv_obs": float(np.cov(mv, base, bias=True)[0, 1]),
                  "cov_mv_hyp": float(np.cov(mv, hyp, bias=True)[0, 1]),
                  "cov_obs_hyp": float(np.cov(base, hyp, bias=True)[0, 1]),
                  "r2_T_nonhyp": r2(T, base + mv), "r2_T_move": r2(T, mv), "r2_T_hyp": r2(T, hyp),
                  "hyp_mean": float(np.mean(hyp)), "obs_mean": float(np.mean(base)),
                  "d_mean": float(np.mean(d)), "d_sd": float(np.std(d)),
                  "top1_parts": {"ig": float(ig["actual"][t10["actual"][0]]), "obs": float(base[t10["actual"][0]]),
                                 "hyp": float(hyp[t10["actual"][0]]), "move": float(mv[t10["actual"][0]])},
                  "gap_top1_minus_median": float(T[t10["actual"][0]] - np.median(T)),
                  "gap_top1_minus_top10": float(T[t10["actual"][0]] - T[t10["actual"][9]]) if len(T) >= 10 else None}
    # candidate features: predicted objects in view, distance to observed objects / walked path
    obs_ids = {t: {n["id"] for n in rp.load(f"{sd}/habitat_scene_graph_original_graph{t}.yaml")["nodes"]}
               for t in sorted({g // 4 for g in gids})}
    pred = pred_positions(files["actual"], obs_ids, gids)
    obs_obj = np.array([rp.lp._vec(n["position"]) for t in obs_ids
                        for n in rp.load(f"{sd}/habitat_scene_graph_original_graph{t}.yaml")["nodes"]
                        if n.get("node_type") == "object"])
    walked = walked_xy(run, k)
    feats = {}
    if len(pred):
        dp = np.linalg.norm(kept[:, None, :2] - pred[None, :, :2], axis=2)
        feats["n_pred_within3"] = (dp < 3.0).sum(axis=1)
    if len(obs_obj):
        do = np.linalg.norm(kept[:, None, :2] - obs_obj[None, :, :2], axis=2)
        feats["d_obs_min"] = do.min(axis=1)
    if len(walked):
        dw = np.linalg.norm(kept[:, None, :2] - walked[None, :, :2], axis=2)
        feats["d_walk_min"] = dw.min(axis=1)
    res["feat_corr"] = {f"rho_ig_{n}": spearman(ig["actual"], v) for n, v in feats.items()}
    res["feat_corr"].update({f"rho_hyp_{n}": spearman(hyp, v) for n, v in feats.items()})
    i1 = t10["actual"][0]
    res["top1_feats"] = {n: float(v[i1]) for n, v in feats.items()}
    res["cand_feats_median"] = {n: float(np.median(v)) for n, v in feats.items()}
    res["top10_spread"] = float(np.mean([np.hypot(*(kept[i, :2] - kept[j, :2]))
                                         for a, i in enumerate(t10["actual"]) for j in t10["actual"][a + 1:]]))
    # full first-stage replays (fresh candidates from the same RNG state)
    res["full"] = {}
    full_top1 = {}
    for c in ("obs", "plc_a", "plc_b", "orc"):
        kc, scc, totc, oc = scorers[c].first_stage(seed, meta["nprior"], cur)
        if len(kc) == 0:
            res["full"][c] = None
            continue
        full_top1[c] = kc[oc[0], :2]
        res["full"][c] = {"top1_dist": float(np.hypot(*(kc[oc[0], :2] - a1))), "n_cand": int(len(kc)),
                          "best": float(totc[oc[0]]), "top1_xy": kc[oc[0], :2].tolist()}
    if "plc_a" in full_top1 and "plc_b" in full_top1:
        res["full_plc_a_vs_b"] = float(np.hypot(*(full_top1["plc_a"] - full_top1["plc_b"])))
    # second stage at top-10 original poses, history filtered (no reachability)
    cam2 = fastig.second_cfg()
    hist = rp.history(run, k)
    res["second"] = {}
    for c in CONDS:
        cand = [kept[i] for i in t10[c]]
        filt = [p for p in cand if all(np.linalg.norm(p[:3] - h[:3]) > 1.0 for h in hist)] or cand
        s2, _ = scorers[c].score(np.array(filt), cam2)
        v = s2[:, 0] + s2[:, 1]
        best = float(np.max(v))
        tied = [i for i in range(len(v)) if abs(v[i] - best) <= 1e-6]
        res["second"][c] = {"n": len(filt), "best": best, "n_tied": len(tied),
                            "chosen": [list(map(float, filt[i][:2])) for i in tied],
                            "first_rank_of_chosen": [int(t10[c].index(next(j for j in t10[c] if np.allclose(kept[j], filt[i])))) for i in tied]}
    fin = rp.P[run]["stages"][str(k)]["pose_finals"][-1]
    if fin["new"]:
        newp = np.array(fin["new"])
        res["second_verify"] = {"logged": fin["best_ig"]}
        for c in CONDS:
            s2, _ = scorers[c].score(newp, cam2)
            res["second_verify"][c] = (s2[:, 0] + s2[:, 1]).tolist()
    res["n_pred"] = int(len(pred))
    return res


def main():
    runs = [l.strip() for l in open("/tmp/cvp_review/analysis_pre/runs.txt") if l.strip()]
    if len(sys.argv) > 1:
        runs = [r for r in runs if any(s in r for s in sys.argv[1:])]
    done = set()
    out_path = "/tmp/cvp_review/work_A/replay2_results.jsonl"
    if os.path.exists(out_path):
        for line in open(out_path):
            j = json.loads(line)
            if "error" not in j:
                done.add((j["run"], j["stage"]))
    jobs = []
    for run in runs:
        meta = rp.stage_meta(run)
        for k, m in sorted(meta.items()):
            if (run, k) in done:
                continue
            if k > 0 and not os.path.exists(f"{rp.RUNS}/{run}/stages/{k}/executed_path.json"):
                continue
            if k == 0 and not os.path.exists(f"{rp.RUNS}/{run}/stages/1/executed_path.json"):
                continue
            if not glob.glob(f"{rp.RUNS}/{run}/stages/{k}/habitat_scene_graph_new_graph_*.yaml"):
                continue
            jobs.append((run, k, m))
    print("jobs", len(jobs), flush=True)
    with Pool(7) as pool, open(out_path, "a") as f:
        for res in pool.imap_unordered(job, jobs):
            f.write(json.dumps(res) + "\n")
            f.flush()
            tag = "match" if res.get("top10_match") else ("ERR " + res.get("error", "") if "error" in res else "MISMATCH")
            print(res.get("run"), res.get("stage"), tag, flush=True)


if __name__ == "__main__":
    main()
