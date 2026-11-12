#!/usr/bin/env python3
"""Summaries of stages.jsonl: per arm and per arm x scene.
- per-stage Spearman rho: median and IQR;
- live-stop (and logged best / second-stage pick) U_360 percentile: mean with a
  stage bootstrap 95% CI (resample stages within each run, 2,000 draws);
- one-sided sign test that the stop beats the candidate median (stage level,
  ties dropped) and a run-level one-sided exact sign-flip test on run means;
- yardstick: share of in-view vs out-of-view unmapped objects present at k+1.
Writes summary.json. No F1/AUC."""
import itertools
import json
import os
from collections import defaultdict

import numpy as np
from scipy.stats import binomtest

OUT = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(f"{OUT}/stages.jsonl")]
USED = [r for r in R if r.get("top10_match") and "rho_total_U360" in r]
ARMS = ["official", "placebo", "filter_only", "oracle_visible"]
RHOS = ["rho_total_U360", "rho_total_Ucone", "rho_ig_U360", "rho_ig_Ucone", "rho_negdist_U360",
        "rho_total_U360_sl", "rho_total_Ucone_sl"]
PCTS = ["pct_stop", "pct_best", "pct_final", "pct_sl_stop", "pct_cone_best"]
B = 2000


def q(x):
    x = np.array([v for v in x if v is not None], float)
    if not len(x):
        return None
    return {"n": int(len(x)), "median": float(np.median(x)), "q25": float(np.percentile(x, 25)),
            "q75": float(np.percentile(x, 75)), "mean": float(np.mean(x))}


def boot_mean(rows, key, seed=0):
    by = defaultdict(list)
    for r in rows:
        if r.get(key) is not None:
            by[r["run"]].append(r[key])
    if not by:
        return None
    rng = np.random.default_rng(seed)
    pooled = np.concatenate([np.array(v, float) for v in by.values()])
    means = []
    for _ in range(B):
        s = [np.array(v, float)[rng.integers(0, len(v), len(v))] for v in by.values()]
        means.append(np.concatenate(s).mean())
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"n_stages": int(len(pooled)), "n_runs": len(by), "mean": float(pooled.mean()),
            "ci95": [float(lo), float(hi)]}


def sign_tests(rows, key):
    flag = "gt_median_" + key.split("_", 1)[1]
    w = sum(1 for r in rows if r.get(flag) is True)
    l = sum(1 for r in rows if r.get(flag) is False)
    t = sum(1 for r in rows if flag in r and r.get(flag) is None)
    p = binomtest(w, w + l, 0.5, alternative="greater").pvalue if w + l else None
    by = defaultdict(list)
    for r in rows:
        if r.get(key) is not None:
            by[r["run"]].append(r[key])
    d = np.array([np.mean(v) - 0.5 for v in by.values()])
    obs = d.sum()
    flips = [np.dot(s, np.abs(d)) for s in itertools.product([-1, 1], repeat=len(d))]
    p_run = float(np.mean([f >= obs - 1e-12 for f in flips])) if len(d) else None
    return {"stage_wins": w, "stage_losses": l, "stage_ties": t, "p_sign_one_sided": p,
            "run_means": {k: float(np.mean(v)) for k, v in by.items()},
            "runs_above_half": int((d > 0).sum()), "n_runs": int(len(d)),
            "p_run_signflip_one_sided": p_run, "p_floor_run": 1.0 / 2 ** len(d) if len(d) else None}


def yard(rows):
    ys = [r["yard"] for r in rows if r.get("yard")]
    s = {k: int(sum(y[k] for y in ys)) for k in ("n_in", "in_mapped_sl", "in_mapped_any", "n_out", "out_mapped_sl",
                                                  "out_mapped_any")}
    s["n_stages"] = len(ys)
    s["share_in_sl"] = s["in_mapped_sl"] / s["n_in"] if s["n_in"] else None
    s["share_out_sl"] = s["out_mapped_sl"] / s["n_out"] if s["n_out"] else None
    s["share_in_any"] = s["in_mapped_any"] / s["n_in"] if s["n_in"] else None
    s["share_out_any"] = s["out_mapped_any"] / s["n_out"] if s["n_out"] else None
    # per-stage paired difference (stages with both sets non-empty)
    diffs = [y["in_mapped_sl"] / y["n_in"] - y["out_mapped_sl"] / y["n_out"] for y in ys if y["n_in"] and y["n_out"]]
    s["stage_diff_sl"] = q(diffs)
    return s


def block(rows):
    out = {"n_stages": len(rows), "n_runs": len({r["run"] for r in rows}),
           "runs": sorted({r["run"] for r in rows})}
    out["rho"] = {k: q([r.get(k) for r in rows]) for k in RHOS}
    out["pct"] = {k: boot_mean(rows, k) for k in PCTS}
    out["beats_median"] = {k: sign_tests(rows, k) for k in ("pct_stop", "pct_best", "pct_final")}
    out["U360_stop_mean"] = float(np.mean([r["U360_stop"] for r in rows]))
    out["U360_cand_mean"] = float(np.mean([r["U360_mean"] for r in rows]))
    out["stop_to_final_m_median"] = q([r.get("stop_to_final_m") for r in rows])
    out["yardstick"] = yard(rows)
    return out


summary = {"n_replayed": len(R), "n_used": len(USED),
           "dropped_mismatch": sorted([r["run"], r["stage"]] for r in R if not r.get("top10_match")),
           "by_arm": {}, "by_arm_scene": {}, "all": block(USED)}
for a in ARMS:
    rows = [r for r in USED if r["arm"] == a]
    summary["by_arm"][a] = block(rows)
    for s in ("00853", "00871"):
        rs = [r for r in rows if r["scene"] == s]
        if rs:
            summary["by_arm_scene"][f"{a}/{s}"] = block(rs)

# decision rules (primary: median per-stage rho of the ASP total with U_360)
med = {a: summary["by_arm"][a]["rho"]["rho_total_U360"]["median"] for a in ARMS}
medc = {a: summary["by_arm"][a]["rho"]["rho_total_Ucone"]["median"] for a in ARMS}
ci = {a: summary["by_arm"][a]["pct"]["pct_stop"]["ci95"] for a in ARMS}
summary["decision_rules"] = {
    "rule1_all_rho_le_0.1": {"U360": all(v <= 0.1 for v in med.values()),
                             "Ucone": all(v <= 0.1 for v in medc.values()), "medians_U360": med,
                             "medians_Ucone": medc},
    "rule2_oracle_ge_0.3_others_near_0": {
        "U360": med["oracle_visible"] >= 0.3 and all(abs(med[a]) < 0.1 for a in ("official", "placebo", "filter_only")),
        "Ucone": medc["oracle_visible"] >= 0.3 and all(abs(medc[a]) < 0.1 for a in ("official", "placebo",
                                                                                      "filter_only"))},
    "rule3_stop_pct_ci_above_0.5": {a: ci[a][0] > 0.5 for a in ARMS},
}
json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)
print(json.dumps(summary["decision_rules"], indent=1))
for a in ARMS:
    b = summary["by_arm"][a]
    print(a, b["n_stages"], {k: (round(v["median"], 3), round(v["q25"], 3), round(v["q75"], 3)) for k, v in b["rho"].items()})
    print("   pct", {k: (round(v["mean"], 3), [round(x, 3) for x in v["ci95"]]) for k, v in b["pct"].items()})
    print("   sign", {k: (v["stage_wins"], v["stage_losses"], v["stage_ties"], v["p_sign_one_sided"],
                      v["runs_above_half"], v["n_runs"], v["p_run_signflip_one_sided"]) for k, v in b["beats_median"].items()})
    y = b["yardstick"]
    print("   yard", {k: y[k] for k in y if k != "stage_diff_sl"}, y["stage_diff_sl"])
for k, b in summary["by_arm_scene"].items():
    print(k, b["n_stages"], b["n_runs"], {x: round(b["rho"][x]["median"], 3) for x in ("rho_total_U360", "rho_total_Ucone", "rho_ig_U360")},
          "pct_stop", round(b["pct"]["pct_stop"]["mean"], 3), [round(x, 3) for x in b["pct"]["pct_stop"]["ci95"]],
          "sign", b["beats_median"]["pct_stop"]["stage_wins"], b["beats_median"]["pct_stop"]["stage_losses"],
          round(b["beats_median"]["pct_stop"]["p_sign_one_sided"], 4),
          "yard", round(b["yardstick"]["share_in_sl"], 3), round(b["yardstick"]["share_out_sl"], 3))
