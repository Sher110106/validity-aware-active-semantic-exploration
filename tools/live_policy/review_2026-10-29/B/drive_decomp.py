"""Decision-level variance decomposition at fixed observed states ($0, offline).

For an official run's stage k (observed graphs fixed), replay ASP's first-stage
ranking plus the reachable-assumed re-score under:
  LLM      - the run's own LLM member files (sorted order),
  placebo  - K fresh placebo draws on the same observed graphs and member ids
             (tools/live_policy/live_policy.py placebo_graph, our calibration),
  none     - every member = its track's observed graph (no predictions),
each with the same viewpoint draw U0, and LLM also with K fresh viewpoint draws.
Outputs chosen xy per condition and summary distances.
"""
import sys, os, json, glob, re, itertools, tempfile
sys.path.insert(0, "/tmp/cvp_review/work_B")
sys.path.insert(0, "/Users/sher/project/cvp/project/tools/live_policy")
import numpy as np
import yaml
import replay as R
import live_policy as lp

K = int(os.environ.get("K", "20"))
CALIB = lp.load_calibration()
TMP = "/tmp/cvp_review/work_B/scratch/decomp"
os.makedirs(TMP, exist_ok=True)


def members_of(sd):
    return sorted(int(re.search(r"_(\d+)\.yaml$", f).group(1)) for f in glob.glob(sd + "/habitat_scene_graph_new_graph_*.yaml"))


def observed_path(sd, gid):
    return f"{sd}/habitat_scene_graph_original_graph{gid // 4}.yaml"


def write(graph, name):
    p = os.path.join(TMP, name)
    with open(p, "w") as f:
        yaml.safe_dump(graph, f)
    return p


def current_and_history(run, k):
    hist = []
    for j in range(1, k + 2):
        ep = f"{run}/stages/{j}/executed_path.json"
        if os.path.exists(ep):
            P = json.load(open(ep))["world_frame_path"]
            if P:
                if j == 1:
                    hist.append(np.array(P[0]))
                if j <= k:
                    hist.append(np.array(P[-1]))
    cur = hist[-1] if k > 0 else hist[0]
    return cur, hist[: k + 1]


def chosen(S, U, cur, hist):
    out = S.decide(U, cur, hist)
    c = out["choice"]
    top_ig = [t[2] + t[3] for t in out["kept"]]
    mx = max(top_ig) if top_ig else 0.0
    near_max = float(np.mean([v >= mx - 0.25 for v in top_ig])) if top_ig else 0.0
    return dict(xy=np.array(c[:2]), top=[np.array(t[1][:2]) for t in out["top"]], best_first=out["best_first"],
                final_ig=out["final_ig"], ties=out["ties"], n_kept=len(out["kept"]), share_near_max=near_max,
                max_raw_ig=mx)


def pdist(xs):
    return [float(np.linalg.norm(a - b)) for a, b in itertools.combinations(xs, 2)]


def run_state(run, k, seed):
    sd = f"{run}/stages/{k}"
    gids = members_of(sd)
    cur, hist = current_and_history(run, k)
    U0 = np.random.default_rng(seed).random((3000, 4))
    llm_files = [f"{sd}/habitat_scene_graph_new_graph_{g}.yaml" for g in gids]
    S = R.Scorer(llm_files, seed)
    res = {"run": os.path.basename(run), "stage": k, "members": gids}
    res["llm"] = chosen(S, U0, cur, hist)
    res["llm_U"] = [chosen(S, np.random.default_rng([seed, 999, c]).random((3000, 4)), cur, hist) for c in range(K)]
    none_files = [observed_path(sd, g) for g in gids]
    Sn = R.Scorer(none_files, seed)
    res["none"] = chosen(Sn, U0, cur, hist)
    res["plac"] = []
    for j in range(K):
        files = []
        for g in gids:
            obs = yaml.safe_load(open(observed_path(sd, g)))
            rng = np.random.default_rng([seed, k, g, 7000 + j])
            files.append(write(lp.placebo_graph(obs, rng, CALIB), f"{res['run']}_{k}_{g}_{j}.yaml"))
        Sp = R.Scorer(files, seed)
        res["plac"].append(chosen(Sp, U0, cur, hist))
    return res, cur


def summarize(res, cur):
    L = res["llm"]["xy"]; N = res["none"]["xy"]
    LU = [x["xy"] for x in res["llm_U"]]; P = [x["xy"] for x in res["plac"]]
    d_sampling = pdist([L] + LU)                     # same hypotheses, different viewpoint draws
    d_placebo = pdist(P)                             # same draw, different random hypotheses
    d_llm_vs_plac = [float(np.linalg.norm(L - p)) for p in P]
    # where does the LLM choice sit among placebo choices? (mean distance to the others)
    plac_self = [np.mean([np.linalg.norm(p - q) for q in P if q is not p]) for p in P]
    llm_mean = float(np.mean(d_llm_vs_plac))
    pct = float(np.mean([s <= llm_mean for s in plac_self]))
    ang = lambda xy: np.degrees(np.arctan2(xy[1] - cur[1], xy[0] - cur[0]))
    return dict(
        run=res["run"], stage=res["stage"], members=len(res["members"]),
        llm_xy=np.round(L, 2).tolist(), none_xy=np.round(N, 2).tolist(),
        d_llm_none=round(float(np.linalg.norm(L - N)), 2),
        med_pair_sampling=round(float(np.median(d_sampling)), 2),
        med_pair_placebo=round(float(np.median(d_placebo)), 2),
        med_llm_to_placebo=round(float(np.median(d_llm_vs_plac)), 2),
        llm_mean_dist_percentile_among_placebo=round(pct, 2),
        share_placebo_within_1m_of_llm=round(float(np.mean([d < 1.0 for d in d_llm_vs_plac])), 2),
        share_sampling_within_1m_of_llm=round(float(np.mean([np.linalg.norm(L - x) < 1.0 for x in LU])), 2),
        llm_maxIG=round(res["llm"]["max_raw_ig"], 2), none_maxIG=round(res["none"]["max_raw_ig"], 2),
        plac_maxIG_med=round(float(np.median([x["max_raw_ig"] for x in res["plac"]])), 2),
        llm_share_near_max=round(res["llm"]["share_near_max"], 2),
        plac_share_near_max_med=round(float(np.median([x["share_near_max"] for x in res["plac"]])), 2),
        llm_dist_from_robot=round(float(np.linalg.norm(L - cur[:2])), 2),
        plac_dist_from_robot_med=round(float(np.median([np.linalg.norm(p - cur[:2]) for p in P])), 2),
        none_dist_from_robot=round(float(np.linalg.norm(N - cur[:2])), 2),
    )


if __name__ == "__main__":
    targets = sys.argv[1:]
    allres = []
    for t in targets:
        run, k = t.rsplit(":", 1)
        run = "/tmp/cvp_review/runs/" + run
        seed = int(yaml.safe_load(open(run + "/config/pipeline_config.yaml"))["SEED"])
        res, cur = run_state(run, int(k), seed)
        s = summarize(res, cur)
        allres.append({"summary": s, "raw": {
            "llm": res["llm"]["xy"].tolist(), "none": res["none"]["xy"].tolist(),
            "llm_U": [x["xy"].tolist() for x in res["llm_U"]], "plac": [x["xy"].tolist() for x in res["plac"]],
            "cur": cur.tolist()}})
        print(json.dumps(s), flush=True)
    out = os.environ.get("OUT")
    if out:
        json.dump(allres, open(out, "w"))
