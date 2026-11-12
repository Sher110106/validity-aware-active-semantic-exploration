#!/usr/bin/env python3
"""Offline counterfactual replay of ASP's first-stage viewpoint score.

For each saved stage of a run:
 1. Rebuild the exact candidate set with the pinned UncertaintyCalculator
    (same seed, same RNG call index, same file order) and check the top-10
    against the run's own pose_log.json.
 2. Score the SAME candidate poses with other hypothesis sets built on the
    same observed graphs:
      actual   - the files the planner used;
      obs      - every member = its track's observed graph (no hypotheses);
      plc_a/b  - placebo_graph() draws (live_policy.py, our project code);
      orc      - oracle_graph() draws from a pool of true objects (union of
                 objects the oracle arm drew in any e3 run of the scene).
 3. Re-run the full first stage (fresh candidates from the same RNG state)
    under obs and plc_a, to include the candidate-set dependence.
 4. Second-stage IG (near 0.1 m, range 4 m, no move cost) at the top-10
    original poses for each condition, and at the logged winner's new_pose.

Read-only on run data; scratch files go to /tmp/cvp_review/work_A/tmp.
No F1/AUC is computed.
"""
import copy
import glob
import importlib.util
import json
import os
import re
import sys
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, "/tmp/cvp_review/work_A")
import numpy as np  # noqa: E402

np.set_printoptions(legacy="1.25")
import yaml  # noqa: E402

import pinned_harness as ph  # noqa: E402

cu = ph.cu
_spec = importlib.util.spec_from_file_location(
    "live_policy_local", "/Users/sher/project/cvp/project/tools/live_policy/live_policy.py")
lp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lp)

RUNS = "/tmp/cvp_review/runs"
TMP = "/tmp/cvp_review/work_A/tmp"
P = json.load(open("/tmp/cvp_review/work_A/parsed_runs.json"))
CALIB = lp.load_calibration()
LAMBDA = 0.2


def oracle_pool(scene):
    pool = {}
    for f in glob.glob(f"{RUNS}/e3_{scene}_*/stages/*/habitat_scene_graph_new_graph_*.yaml"):
        d = yaml.safe_load(open(f))
        for n in d["nodes"]:
            if n.get("node_type") == "object" and n.get("is_predicted"):
                key = (n["name"], n["position"])
                pool[key] = {"name": n["name"], "position": lp._vec(n["position"]),
                             "dimension": lp._vec(n["dimension"])}
    return list(pool.values())


POOLS = {}


def arm_of(run):
    for a in ("official", "placebo", "filter_only", "oracle_visible"):
        if f"_{a}_" in run:
            return a
    return "?"


def stage_meta(run):
    """Per stage: nprior (RNG calls before the last attempt) and file order."""
    r = P[run]
    ks = sorted(int(x) for x in r["stages"])
    meta = {}
    calls = 0
    att_by_stage = {}
    for a in r["attempts"]:
        att_by_stage.setdefault(a["stage"], []).append(a)
    for k in ks:
        s = r["stages"][str(k)]
        n_tops = len(s.get("pose_tops") or [])
        if n_tops:
            meta[k] = {"nprior": calls + n_tops - 1}
            atts = att_by_stage.get(k) or []
            meta[k]["log_attempts"] = len(atts)
            if atts and atts[-1].get("done_order"):
                meta[k]["done_order"] = atts[-1]["done_order"]
            if atts:
                meta[k]["log_best"] = atts[-1].get("first_stage_best")
        calls += n_tops
    return meta


def current_pos(run, k):
    if k == 0:
        p = f"{RUNS}/{run}/stages/1/executed_path.json"
        return np.array(json.load(open(p))["world_frame_path"][0], dtype=float)
    p = f"{RUNS}/{run}/stages/{k}/executed_path.json"
    return np.array(json.load(open(p))["world_frame_path"][-1], dtype=float)


def history(run, k):
    return [current_pos(run, j) for j in range(0, k + 1)]


def write_yaml(obj, path):
    with open(path, "w") as f:
        yaml.safe_dump(obj, f)


def load(path):
    with open(path) as f:
        return yaml.safe_load(f)


def score_fixed(calc, files, poses, cam_cfg):
    groups = calc._build_scene_graph_groups(files)
    mapping = calc._get_object_to_parent_mapping(files)
    opt = calc._preprocess_groups(groups)
    out = []
    for pose in poses:
        camera = cu.Camera(config=cam_cfg, position=np.asarray(pose[:3], dtype=float), yaw_degrees=float(pose[3]))
        gobs = []
        for i, og in enumerate(opt):
            names, rooms = [], []
            for sg in og:
                ids, _, _, nc = calc._visible_testing(sg, camera)
                fr = set()
                if ids:
                    pn = [mapping[i][o] for o in ids if o in mapping[i]]
                    if pn:
                        fr = {Counter(pn).most_common(1)[0][0]}
                names.append(nc)
                rooms.append(fr)
            gobs.append({"sample": pose, "names_list": names, "rooms_list": rooms})
        o = calc._calculate_ig_components(gobs, lambda x: x["names_list"])
        r = calc._calculate_ig_components(gobs, lambda x: x["rooms_list"])
        out.append((o["H_y"] - o["H_y_epsilon"], r["H_y"] - r["H_y_epsilon"]))
    return np.array(out, dtype=float)


def second_cfg():
    c = copy.deepcopy(cu.CameraConfig())
    c.near_clip = 0.1
    c.max_range = 4.0
    return c


def build_condition_files(run, k, gids, cond, seed, wdir):
    sd = f"{RUNS}/{run}/stages/{k}"
    files = []
    for g in gids:
        t = g // 4
        obs_path = f"{sd}/habitat_scene_graph_original_graph{t}.yaml"
        if cond == "actual":
            files.append(f"{sd}/habitat_scene_graph_new_graph_{g}.yaml")
            continue
        dst = os.path.join(wdir, f"{cond}_{g}.yaml")
        observed = load(obs_path)
        if cond == "obs":
            write_yaml(observed, dst)
        elif cond.startswith("plc"):
            salt = {"plc_a": 1001, "plc_b": 1002}[cond]
            rng = np.random.default_rng([int(seed), k, g, salt])
            write_yaml(lp.placebo_graph(observed, rng, CALIB), dst)
        elif cond == "orc":
            scene = re.search(r"_(\d{5})_s", run).group(1)
            rng = np.random.default_rng([int(seed), k, g, 2001])
            if scene not in POOLS:
                POOLS[scene] = oracle_pool(scene)
            graph, _info = lp.oracle_graph(observed, rng, CALIB, POOLS[scene])
            write_yaml(graph, dst)
        files.append(dst)
    return files


def top_k(total, k=10):
    order = sorted(range(len(total)), key=lambda i: total[i], reverse=True)
    return order[:k]


def spearman(a, b):
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    if np.std(ra) == 0 or np.std(rb) == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def replay_stage(args):
    run, k, meta = args
    try:
        return _replay_stage(run, k, meta)
    except Exception as e:  # report, do not hide
        return {"run": run, "stage": k, "error": repr(e)}


def _replay_stage(run, k, meta):
    sd = f"{RUNS}/{run}/stages/{k}"
    seed = P[run]["cfg"]["SEED"]
    gids_exist = sorted(int(re.search(r"_(\d+)\.yaml$", f).group(1))
                        for f in glob.glob(f"{sd}/habitat_scene_graph_new_graph_*.yaml"))
    order = meta.get("done_order")
    if arm_of(run) in ("official", "filter_only") and order:
        # keep the last occurrence pattern: the done order of this attempt
        seen = []
        for g in order:
            if g in gids_exist and g not in seen:
                seen.append(g)
        gids = seen + [g for g in gids_exist if g not in seen]
    else:
        gids = gids_exist
    wdir = os.path.join(TMP, f"{run}_{k}")
    os.makedirs(wdir, exist_ok=True)
    cur = current_pos(run, k)
    calc = ph.make_calc(seed, meta["nprior"], wdir)
    files = build_condition_files(run, k, gids, "actual", seed, wdir)
    lo, hi, scored, order_idx = ph.first_stage(calc, files, cur)
    poses = [s[2] for s in scored]
    top_replay = [poses[i] for i in order_idx[:10]]
    logged = json.load(open(f"{sd}/pose_log.json")) if False else None
    tops = P[run]["stages"][str(k)]["pose_tops"][-1]["top"]
    match = len(tops) == len(top_replay) and all(
        np.allclose(np.array(a), np.array(b), atol=1e-6) for a, b in zip(tops, top_replay))
    # the logged first-stage best, if any
    res = {"run": run, "stage": k, "arm": arm_of(run), "n_files": len(gids), "first_gid": gids[0],
           "n_cand": len(poses), "top10_match": bool(match), "nprior": meta["nprior"],
           "log_best": meta.get("log_best"), "replay_best": float(scored[order_idx[0]][0]) if scored else None}
    if not poses:
        return res
    poses_arr = np.array(poses)
    d = np.linalg.norm(poses_arr[:, :3] - cur[:3], axis=1)
    cam1 = cu.CameraConfig()
    conds = ["actual", "obs", "plc_a", "plc_b", "orc"]
    S = {}
    for c in conds:
        fl = files if c == "actual" else build_condition_files(run, k, gids, c, seed, wdir)
        calc_c = ph.make_calc(seed, 0, wdir)
        S[c] = score_fixed(calc_c, fl, poses, cam1)
    tot = {c: S[c][:, 0] + S[c][:, 1] - LAMBDA * d for c in conds}
    ig = {c: S[c][:, 0] + S[c][:, 1] for c in conds}
    res["replay_vs_scored_maxabs"] = float(np.max(np.abs(ig["actual"] - np.array([s[1] for s in scored]))))
    t10 = {c: top_k(tot[c]) for c in conds}
    res["fixed"] = {}
    for c in conds:
        res["fixed"][c] = {
            "top1": int(t10[c][0]), "top1_xy": poses_arr[t10[c][0], :2].tolist(),
            "top1_same_as_actual": bool(t10[c][0] == t10["actual"][0]),
            "top1_dist_to_actual": float(np.hypot(*(poses_arr[t10[c][0], :2] - poses_arr[t10["actual"][0], :2]))),
            "top10_overlap": len(set(t10[c]) & set(t10["actual"])) / 10.0,
            "spearman_total_vs_actual": spearman(tot[c], tot["actual"]),
            "spearman_ig_vs_actual": spearman(ig[c], ig["actual"]),
            "ig_mean": float(np.mean(ig[c])), "ig_sd": float(np.std(ig[c])),
            "ig_zero_frac": float(np.mean(np.abs(ig[c]) < 1e-12)),
            "obj_mean": float(np.mean(S[c][:, 0])), "room_mean": float(np.mean(S[c][:, 1])),
        }
    # variance decomposition of the actual total over candidates
    hyp = ig["actual"] - ig["obs"]
    base = ig["obs"]
    mv = -LAMBDA * d
    T = tot["actual"]
    res["var"] = {"total": float(np.var(T)), "move": float(np.var(mv)), "obs_ig": float(np.var(base)),
                  "hyp_part": float(np.var(hyp)),
                  "cov_move_obs": float(np.cov(mv, base, bias=True)[0, 1]),
                  "cov_move_hyp": float(np.cov(mv, hyp, bias=True)[0, 1]),
                  "cov_obs_hyp": float(np.cov(base, hyp, bias=True)[0, 1]),
                  "r2_total_on_nonhyp": float(np.corrcoef(T, base + mv)[0, 1] ** 2) if np.std(base + mv) > 0 else None,
                  "r2_total_on_move": float(np.corrcoef(T, mv)[0, 1] ** 2) if np.std(mv) > 0 else None,
                  "hyp_mean": float(np.mean(hyp)), "obs_ig_mean": float(np.mean(base)),
                  "move_mean": float(np.mean(mv)), "d_mean": float(np.mean(d)), "d_sd": float(np.std(d))}
    # top-10 spatial spread (actual)
    t = poses_arr[t10["actual"], :2]
    res["top10_spread_m"] = float(np.mean([np.hypot(*(a - b)) for i, a in enumerate(t) for b in t[i + 1:]]))
    # full first-stage replay under alternative hypotheses (fresh candidates, same RNG state)
    res["full"] = {}
    for c in ("obs", "plc_a", "orc"):
        fl = build_condition_files(run, k, gids, c, seed, wdir)
        calc_c = ph.make_calc(seed, meta["nprior"], wdir)
        lo_c, hi_c, sc_c, oi_c = ph.first_stage(calc_c, fl, cur)
        if not sc_c:
            res["full"][c] = None
            continue
        p1 = np.array(sc_c[oi_c[0]][2])
        res["full"][c] = {"top1_xy": p1[:2].tolist(),
                          "top1_dist_to_actual": float(np.hypot(*(p1[:2] - poses_arr[t10['actual'][0], :2]))),
                          "n_cand": len(sc_c), "best": float(sc_c[oi_c[0]][0]),
                          "top10_xy": [list(map(float, sc_c[i][2][:2])) for i in oi_c[:10]],
                          "bounds_area": float((hi_c[0] - lo_c[0]) * (hi_c[1] - lo_c[1]))}
    res["bounds_area_actual"] = float((hi[0] - lo[0]) * (hi[1] - lo[1]))
    # second stage at top-10 original poses (no reachability) per condition, history-filtered as pinned
    cam2 = second_cfg()
    hist = history(run, k)
    res["second"] = {}
    for c in conds:
        idx = t10[c]
        cand = [poses[i] for i in idx]
        filt = [p for p in cand if all(np.linalg.norm(np.asarray(p[:3]) - h[:3]) > 1.0 for h in hist)] or cand
        fl = files if c == "actual" else build_condition_files(run, k, gids, c, seed, wdir)
        calc_c = ph.make_calc(seed, 0, wdir)
        s2 = score_fixed(calc_c, fl, filt, cam2)
        v = s2[:, 0] + s2[:, 1]
        best = float(np.max(v))
        tied = [i for i in range(len(v)) if abs(v[i] - best) <= 1e-6]
        res["second"][c] = {"n": len(filt), "best": best, "n_tied": len(tied),
                            "chosen_xy": [list(map(float, filt[i][:2])) for i in tied]}
    # verify second stage at the logged winner's new pose(s)
    fin = P[run]["stages"][str(k)]["pose_finals"][-1]
    if fin["new"]:
        calc_c = ph.make_calc(seed, 0, wdir)
        s2 = score_fixed(calc_c, files, [np.array(p) for p in fin["new"]], cam2)
        res["second_verify"] = {"logged_best": fin["best_ig"], "replayed": (s2[:, 0] + s2[:, 1]).tolist()}
        # the same new poses under other hypothesis sets
        res["second_newpose_alt"] = {}
        for c in ("obs", "plc_a", "orc"):
            fl = build_condition_files(run, k, gids, c, seed, wdir)
            s2c = score_fixed(ph.make_calc(seed, 0, wdir), fl, [np.array(p) for p in fin["new"]], cam2)
            res["second_newpose_alt"][c] = (s2c[:, 0] + s2c[:, 1]).tolist()
    # hypothesis bookkeeping
    npred = []
    for g in gids:
        dd = load(f"{sd}/habitat_scene_graph_new_graph_{g}.yaml")
        obs_ids = {n["id"] for n in load(f"{sd}/habitat_scene_graph_original_graph{g // 4}.yaml")["nodes"]}
        npred.append(sum(1 for n in dd["nodes"] if n["id"] not in obs_ids and n.get("node_type") == "object"))
    res["n_pred_per_file"] = npred
    return res


def main():
    runs = [l.strip() for l in open("/tmp/cvp_review/analysis_pre/runs.txt") if l.strip()]
    if len(sys.argv) > 1:
        runs = [r for r in runs if any(s in r for s in sys.argv[1:])]
    jobs = []
    for run in runs:
        meta = stage_meta(run)
        for k, m in sorted(meta.items()):
            # need executed path for current position
            if k > 0 and not os.path.exists(f"{RUNS}/{run}/stages/{k}/executed_path.json"):
                continue
            if k == 0 and not os.path.exists(f"{RUNS}/{run}/stages/1/executed_path.json"):
                continue
            if not glob.glob(f"{RUNS}/{run}/stages/{k}/habitat_scene_graph_new_graph_*.yaml"):
                continue
            jobs.append((run, k, m))
    out_path = "/tmp/cvp_review/work_A/replay_results.jsonl"
    with Pool(7) as pool, open(out_path, "a") as f:
        for res in pool.imap_unordered(replay_stage, jobs):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(res.get("run"), res.get("stage"), "match" if res.get("top10_match") else ("ERR " + res.get("error", "") if "error" in res else "MISMATCH"), flush=True)


if __name__ == "__main__":
    main()
