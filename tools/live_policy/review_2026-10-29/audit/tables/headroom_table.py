#!/usr/bin/env python3
"""Headroom table from existing outputs. E1/E2 runs and the frontier explorer only; no e3 rows
are read from any score file (scores_e1_e2.json holds none) and no F1/AUC is computed for e3.
Value at 60 m = linear interpolation of the per-stage HM3D author-faithful curve
(hm3d_stages[*].af_recall / af_f1 vs path_m), held at the last value if the run stopped short,
the same 'at' rule as asp_offline.evaluator.area_under_curve. Output: headroom_table.json"""
import json
import re

import numpy as np

AP = "/tmp/cvp_review/analysis_pre"
OUT = "/tmp/cvp_review/audit/tables/headroom_table.json"
DROPPED = {"e1_00853_s44_official_60m", "e1_00853_s44_official_60m_rerun1", "e1_00871_s43_placebo_60m"}
ARMS = ["official", "placebo", "filter_only"]


def arm_of(r):
    m = re.search(r"(official|placebo|filter_only|oracle_visible)", r)
    return m.group(1) if m else "frontier"


def at(stages, metric, x):
    pts = sorted((float(s["path_m"]), float(s[metric])) for s in stages if metric in s)
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y1 if x1 == x0 else y0 + (x - x0) / (x1 - x0) * (y1 - y0)
    return pts[-1][1]


res = {"frontier": {}, "runs": {}, "arm_scene": {}, "base_rate": {}, "scanned": {}}
# 1. frontier explorer
for f in json.load(open(f"{AP}/frontier_60m_scores.json")):
    st = f["hm3d_stages"]
    last = max(st, key=lambda s: s["path_m"])
    res["frontier"][f["scene"]] = {
        "final_path_m": last["path_m"], "final_stage": last["stage"],
        "af_recall_final": last["af_recall"], "af_f1_final": last["af_f1"], "af_precision_final": last["af_precision"],
        "object_recall_final": last["object_recall"],
        "af_recall_at_60m": at(st, "af_recall", 60.0), "af_f1_at_60m": at(st, "af_f1", 60.0),
        "max_af_recall_any_stage": max(s["af_recall"] for s in st),
        "hm3d_auc_af_f1_to_60m": f["hm3d_auc_af_f1_to_60m"]}
# 2. E1/E2 runs at 60 m
for r in json.load(open(f"{AP}/scores_e1_e2.json")):
    run = r["run_dir"].rstrip("/").split("/")[-1]
    assert not run.startswith("e3_")
    st = r["hm3d_stages"]
    last = max(st, key=lambda s: s["path_m"]) if st else None
    res["runs"][run] = {"arm": arm_of(run), "scene": r["scene"], "counted": run not in DROPPED,
                        "final_path_m": r["final_path_m"],
                        "af_recall_at_60m": at(st, "af_recall", 60.0) if st and r["final_path_m"] > 0 else None,
                        "af_f1_at_60m": at(st, "af_f1", 60.0) if st and r["final_path_m"] > 0 else None,
                        "af_recall_final": last["af_recall"] if last else None,
                        "hm3d_auc_af_recall_to_60m": r.get("hm3d_auc_af_recall_to_60m"),
                        "hm3d_auc_af_f1_to_60m": r.get("hm3d_auc_af_f1_to_60m")}
for a in ARMS:
    for sc in ["00853", "00871"]:
        R = [v for v in res["runs"].values() if v["counted"] and v["arm"] == a and v["scene"] == sc]
        res["arm_scene"][f"{a}_{sc}"] = {
            "n": len(R),
            "af_recall_at_60m": [round(v["af_recall_at_60m"], 4) for v in R],
            "af_recall_at_60m_mean": float(np.mean([v["af_recall_at_60m"] for v in R])),
            "af_f1_at_60m": [round(v["af_f1_at_60m"], 4) for v in R],
            "af_f1_at_60m_mean": float(np.mean([v["af_f1_at_60m"] for v in R])),
            "short_runs": [(round(v["final_path_m"], 1)) for v in R if v["final_path_m"] < 60]}
# 3. mapping base rate (E1/E2 only), from stage_diagnostics.json; cross-check base_rates_pre_E3.json
sd = [x for x in json.load(open(f"{AP}/stage_diagnostics.json")) if not x["run"].startswith("e3_")]
pre = {x["run"]: x for x in json.load(open("/tmp/cvp_review/gates/base_rates_pre_E3.json"))}
for x in sd:
    res["base_rate"][x["run"]] = {"arm": x["arm"], "scene": x["scene"], "counted": x["run"] not in DROPPED,
                                  "n_near": x["base_rate"]["n_near"], "mapped_k1": x["base_rate"]["mapped_k1"],
                                  "mapped_k2": x["base_rate"]["mapped_k2"],
                                  "scanned_share_of_new_hypotheses": x["scanned_share_of_new_hypotheses"],
                                  "matches_pre_E3_file": (x["run"] in pre and abs(pre[x["run"]]["base_rate"]["mapped_k1"] - x["base_rate"]["mapped_k1"]) < 1e-12) if x["run"] in pre else None}
agg = {}
for a in ARMS:
    for sc in ["853", "871"]:
        R = [v for v in res["base_rate"].values() if v["counted"] and v["arm"] == a and v["scene"] == sc]
        nn = sum(v["n_near"] for v in R)
        agg[f"{a}_{sc}"] = {"runs": len(R), "n_near": nn,
                            "pooled_mapped_k1": sum(v["mapped_k1"] * v["n_near"] for v in R) / nn,
                            "run_range": [min(v["mapped_k1"] for v in R), max(v["mapped_k1"] for v in R)],
                            "scanned_share_new_hyp_mean": float(np.mean([v["scanned_share_of_new_hypotheses"] for v in R]))}
res["base_rate_arm_scene"] = agg
# 4. share of guesses in scanned ground, chosen_view.json (final 4 m view and all guesses at the stage)
cv = [x for x in json.load(open("/tmp/cvp_review/work_A/chosen_view.json")) if not x["run"].startswith("e3_")]
for a in ARMS:
    for sc in ["00853", "00871", "both"]:
        R = [x for x in cv if x["arm"] == a and x["run"] not in DROPPED and (sc == "both" or f"_{sc}_" in x["run"])]
        vis = [x["vis_scanned_share"] for x in R if x["vis_scanned_share"] is not None]
        allp = [x["all_scanned_share"] for x in R if x["all_scanned_share"] is not None]
        vis1 = [x["vis_scanned_share"] for x in R if x["vis_scanned_share"] is not None and x["stage"] > 0]
        allp1 = [x["all_scanned_share"] for x in R if x["all_scanned_share"] is not None and x["stage"] > 0]
        res["scanned"][f"{a}_{sc}"] = {"stages": len(R), "vis_mean": float(np.mean(vis)), "vis_median": float(np.median(vis)),
                                       "all_mean": float(np.mean(allp)), "vis_mean_stage_gt0": float(np.mean(vis1)),
                                       "all_mean_stage_gt0": float(np.mean(allp1))}
# A's 52/60/62/44 reproduction check (A used all runs in runs.txt incl. dropped)
for a in ARMS:
    R = [x["vis_scanned_share"] for x in cv if x["arm"] == a and x["vis_scanned_share"] is not None]
    res["scanned"][f"{a}_A_runset_vis_mean"] = float(np.mean(R))
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps(res["frontier"], indent=1))
for k, v in res["arm_scene"].items():
    print(k, v)
for k, v in res["runs"].items():
    print(k, {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()})
for k, v in agg.items():
    print(k, v)
print([ (k, v["matches_pre_E3_file"]) for k, v in res["base_rate"].items()])
for k, v in res["scanned"].items():
    print(k, v)
