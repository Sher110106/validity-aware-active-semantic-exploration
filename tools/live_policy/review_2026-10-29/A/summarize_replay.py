#!/usr/bin/env python3
"""Summarize replay2_results.jsonl per arm. No F1/AUC."""
import json
import sys

import numpy as np

EXCLUDE = {"e1_00871_s43_placebo_60m"}  # stopped at 0 m, dropped by E1
rows = [json.loads(l) for l in open("/tmp/cvp_review/work_A/replay2_results.jsonl")]
rows = [r for r in rows if "error" not in r and r["run"] not in EXCLUDE and r.get("n_cand", 0) > 0]
arms = ["official", "placebo", "filter_only", "oracle_visible"]


def med(x):
    x = [v for v in x if v is not None and not (isinstance(v, float) and np.isnan(v))]
    return float(np.median(x)) if x else float("nan")


def mean(x):
    x = [v for v in x if v is not None and not (isinstance(v, float) and np.isnan(v))]
    return float(np.mean(x)) if x else float("nan")


out = {}
print("stages per arm:", {a: sum(1 for r in rows if r["arm"] == a) for a in arms}, "total", len(rows))
print("top-10 reproduced exactly:", sum(r["top10_match"] for r in rows), "/", len(rows))
sv = [r for r in rows if "second_verify" in r]
ok = sum(1 for r in sv if any(abs(v - r["second_verify"]["logged"]) < 1e-6 for v in r["second_verify"]["actual"]))
print("second-stage IG at logged winner reproduced:", ok, "/", len(sv))
print()
for a in arms + ["ALL"]:
    R = [r for r in rows if (a == "ALL" or r["arm"] == a)]
    o = {"n": len(R)}
    for c in ["obs", "plc_a", "plc_b", "orc"]:
        o[c] = {"top1_same": mean([r["fixed"][c]["top1_same"] for r in R]),
                "top1_dist_med": med([r["fixed"][c]["top1_dist"] for r in R]),
                "top10_overlap": mean([r["fixed"][c]["top10_overlap"] for r in R]),
                "rho_total_med": med([r["fixed"][c]["rho_total"] for r in R]),
                "rho_ig_med": med([r["fixed"][c]["rho_ig"] for r in R]),
                "ig_mean": mean([r["fixed"][c]["ig_mean"] for r in R]),
                "ig_zero": mean([r["fixed"][c]["ig_zero_frac"] for r in R]),
                "full_top1_dist_med": med([(r["full"].get(c) or {}).get("top1_dist") for r in R]),
                "second_best_mean": mean([r["second"][c]["best"] for r in R]),
                }
    o["actual"] = {"ig_mean": mean([r["fixed"]["actual"]["ig_mean"] for r in R]),
                   "ig_zero": mean([r["fixed"]["actual"]["ig_zero_frac"] for r in R]),
                   "obj_mean": mean([r["fixed"]["actual"]["obj_mean"] for r in R]),
                   "room_mean": mean([r["fixed"]["actual"]["room_mean"] for r in R])}
    o["plc_a_vs_b"] = {"top1_same": mean([r["fixed_plc_a_vs_b"]["top1_same"] for r in R]),
                       "top1_dist_med": med([r["fixed_plc_a_vs_b"]["top1_dist"] for r in R]),
                       "top10_overlap": mean([r["fixed_plc_a_vs_b"]["top10_overlap"] for r in R]),
                       "rho_total_med": med([r["fixed_plc_a_vs_b"]["rho_total"] for r in R]),
                       "full_top1_dist_med": med([r.get("full_plc_a_vs_b") for r in R])}
    V = [r["var"] for r in R]
    o["var"] = {"share_move": med([v["move"] / v["total"] for v in V if v["total"] > 0]),
                "share_obs": med([v["obs_ig"] / v["total"] for v in V if v["total"] > 0]),
                "share_hyp": med([v["hyp"] / v["total"] for v in V if v["total"] > 0]),
                "r2_T_nonhyp": med([v["r2_T_nonhyp"] for v in V]),
                "r2_T_move": med([v["r2_T_move"] for v in V]),
                "r2_T_hyp": med([v["r2_T_hyp"] for v in V]),
                "top1_obs_share": med([v["top1_parts"]["obs"] / v["top1_parts"]["ig"] for v in V if v["top1_parts"]["ig"] > 0]),
                "top1_move": med([v["top1_parts"]["move"] for v in V]),
                "top1_ig": med([v["top1_parts"]["ig"] for v in V]),
                "d_mean": med([v["d_mean"] for v in V]),
                "gap_top1_top10": med([v["gap_top1_minus_top10"] for v in V])}
    o["feat"] = {k: med([r["feat_corr"].get(k) for r in R]) for k in
                 ["rho_ig_n_pred_within3", "rho_ig_d_walk_min", "rho_ig_d_obs_min", "rho_hyp_n_pred_within3",
                  "rho_hyp_d_walk_min"]}
    o["top1_d_walk_med"] = med([r["top1_feats"].get("d_walk_min") for r in R])
    o["cand_d_walk_med"] = med([r["cand_feats_median"].get("d_walk_min") for r in R])
    o["top10_spread_med"] = med([r["top10_spread"] for r in R])
    # second stage reshuffle without reachability
    ranks = [x for r in R for x in r["second"]["actual"]["first_rank_of_chosen"][:1]]
    o["second_rank_hist"] = np.bincount(ranks, minlength=10).tolist() if ranks else []
    o["second_tied_gt1"] = mean([r["second"]["actual"]["n_tied"] > 1 for r in R])
    out[a] = o

json.dump(out, open("/tmp/cvp_review/work_A/replay2_summary.json", "w"), indent=1)
for a, o in out.items():
    print("=" * 20, a, "n =", o["n"])
    print(" actual IG mean %.2f  zero-IG share %.2f  obj %.2f room %.2f" % (o["actual"]["ig_mean"], o["actual"]["ig_zero"], o["actual"]["obj_mean"], o["actual"]["room_mean"]))
    for c in ["obs", "plc_a", "plc_b", "orc"]:
        x = o[c]
        print(f" {c:6s} same-top1 {x['top1_same']:.2f}  top1-dist med {x['top1_dist_med']:.2f} m  top10-overlap {x['top10_overlap']:.2f}  rho_total {x['rho_total_med']:.2f}  rho_ig {x['rho_ig_med']:.2f}  IG mean {x['ig_mean']:.2f} zero {x['ig_zero']:.2f}  full-replay top1 dist med {x['full_top1_dist_med']:.2f}")
    x = o["plc_a_vs_b"]
    print(f" plcA-vs-plcB same-top1 {x['top1_same']:.2f}  dist med {x['top1_dist_med']:.2f}  overlap {x['top10_overlap']:.2f}  rho {x['rho_total_med']:.2f}  full dist med {x['full_top1_dist_med']:.2f}")
    v = o["var"]
    print(f" var shares (median over stages): move {v['share_move']:.2f} obs {v['share_obs']:.2f} hyp {v['share_hyp']:.2f}; R2 T~nonhyp {v['r2_T_nonhyp']:.2f} T~move {v['r2_T_move']:.2f} T~hyp {v['r2_T_hyp']:.2f}")
    print(f" top1: IG {v['top1_ig']:.2f}, obs share {v['top1_obs_share']:.2f}, move {v['top1_move']:.2f}; mean cand dist {v['d_mean']:.2f} m; top1-top10 gap {v['gap_top1_top10']:.2f}")
    print(" feature rhos:", {k: round(val, 2) for k, val in o["feat"].items()})
    print(f" top1 d_walk med {o['top1_d_walk_med']:.2f} vs candidates {o['cand_d_walk_med']:.2f}; top10 spread {o['top10_spread_med']:.2f} m")
    print(" second-stage (no reachability) rank of chosen in top10:", o["second_rank_hist"], "ties>1:", round(o["second_tied_gt1"], 2))
