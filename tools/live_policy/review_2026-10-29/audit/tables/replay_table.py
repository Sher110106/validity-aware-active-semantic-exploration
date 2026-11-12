#!/usr/bin/env python3
"""Decision-replay swap table with stage-bootstrap CIs.
Input: /tmp/cvp_review/work_A/replay2_results.jsonl (read-only). No F1/AUC.
Swap metrics compare a swapped hypothesis set with the stage's ACTUAL set on the same 300
candidates (replay2.py 'fixed'); the noise floor is placebo draw A vs placebo draw B
('fixed_plc_a_vs_b'). For official stages, 'plc' = LLM-vs-placebo.
Bootstrap: resample stages with replacement within each run (run sizes fixed), 2000 draws.
Output: replay_table.json"""
import json
import sys

import numpy as np

SRC = "/tmp/cvp_review/work_A/replay2_results.jsonl"
OUT = "/tmp/cvp_review/audit/tables/replay_table.json"
B = 2000
EXCLUDE_A = {"e1_00871_s43_placebo_60m"}
E1_DROPPED = {"e1_00853_s44_official_60m", "e1_00853_s44_official_60m_rerun1", "e1_00871_s43_placebo_60m"}
ARMS = ["official", "placebo", "filter_only", "oracle_visible"]

rows_all = [json.loads(l) for l in open(SRC)]
rows_all = [r for r in rows_all if "error" not in r and r.get("n_cand", 0) > 0]


def per_stage(r):
    f = r["fixed"]
    fl = r["fixed_plc_a_vs_b"]
    return {
        # distances (m)
        "d_obs": f["obs"]["top1_dist"], "d_plc_a": f["plc_a"]["top1_dist"], "d_plc_b": f["plc_b"]["top1_dist"],
        "d_orc": f["orc"]["top1_dist"], "d_floor": fl["top1_dist"],
        # same top-1
        "s_obs": f["obs"]["top1_same"], "s_plc_a": f["plc_a"]["top1_same"], "s_plc_b": f["plc_b"]["top1_same"],
        "s_orc": f["orc"]["top1_same"], "s_floor": fl["top1_same"],
        "o_obs": f["obs"]["top10_overlap"], "o_plc_a": f["plc_a"]["top10_overlap"], "o_plc_b": f["plc_b"]["top10_overlap"],
        "o_orc": f["orc"]["top10_overlap"], "o_floor": fl["top10_overlap"],
        "r_obs": f["obs"]["rho_total"], "r_plc_a": f["plc_a"]["rho_total"], "r_plc_b": f["plc_b"]["rho_total"],
        "r_orc": f["orc"]["rho_total"], "r_floor": fl["rho_total"],
    }


def nanmed(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    return float(np.median(x)) if len(x) else float("nan")


def nanmean(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    return float(np.mean(x)) if len(x) else float("nan")


def stats(S):
    """S: dict of arrays over stages. Returns the table statistics."""
    o = {}
    for c in ["obs", "plc_a", "plc_b", "orc", "floor"]:
        o[f"same_{c}"] = nanmean(S[f"s_{c}"])
        o[f"move_{c}"] = nanmed(S[f"d_{c}"])
        o[f"ovl_{c}"] = nanmean(S[f"o_{c}"])
        o[f"rho_{c}"] = nanmed(S[f"r_{c}"])
    # placebo swap pooled over both draws (2 values per stage)
    o["same_plc"] = nanmean(np.concatenate([S["s_plc_a"], S["s_plc_b"]]))
    o["move_plc"] = nanmed(np.concatenate([S["d_plc_a"], S["d_plc_b"]]))
    o["ovl_plc"] = nanmean(np.concatenate([S["o_plc_a"], S["o_plc_b"]]))
    o["rho_plc"] = nanmed(np.concatenate([S["r_plc_a"], S["r_plc_b"]]))
    for c in ["obs", "plc", "plc_a", "plc_b", "orc"]:
        o[f"diff_move_{c}_minus_floor"] = o[f"move_{c}"] - o["move_floor"]
    # paired per-stage version: mean of the two placebo-swap moves minus that stage's floor
    o["paired_med_plc_minus_floor"] = nanmed((S["d_plc_a"] + S["d_plc_b"]) / 2 - S["d_floor"])
    return o


def table(rows, seed=20261029):
    runs = sorted({r["run"] for r in rows})
    by_run = {u: [per_stage(r) for r in rows if r["run"] == u] for u in runs}
    keys = list(next(iter(by_run.values()))[0].keys())
    arr = {u: {k: np.array([float(np.nan if s[k] is None else s[k]) for s in by_run[u]]) for k in keys} for u in runs}
    full = {k: np.concatenate([arr[u][k] for u in runs]) for k in keys}
    point = stats(full)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(B):
        idx = {u: rng.integers(0, len(by_run[u]), len(by_run[u])) for u in runs}
        S = {k: np.concatenate([arr[u][k][idx[u]] for u in runs]) for k in keys}
        boots.append(stats(S))
    ci = {k: [float(np.percentile([b[k] for b in boots], 2.5)), float(np.percentile([b[k] for b in boots], 97.5))]
          for k in point}
    return {"n_stages": len(rows), "n_runs": len(runs), "point": point, "ci95": ci}


def main():
    res = {"source": SRC, "B": B, "resampling": "stages within run, run sizes fixed"}
    for setname, excl in [("A_set_394", EXCLUDE_A), ("E1_counted_set", E1_DROPPED)]:
        rows = [r for r in rows_all if r["run"] not in excl]
        res[setname] = {"ALL": table(rows)}
        for a in ARMS:
            res[setname][a] = table([r for r in rows if r["arm"] == a])
        # official arm per scene
        for sc in ["00853", "00871"]:
            res[setname][f"official_{sc}"] = table([r for r in rows if r["arm"] == "official" and f"_{sc}_" in r["run"]])
        # top-10 reproduction counts
        res[setname]["top10_match"] = {a: [sum(r["top10_match"] for r in rows if r["arm"] == a),
                                           sum(1 for r in rows if r["arm"] == a)] for a in ARMS}
        res[setname]["top10_match"]["ALL"] = [sum(r["top10_match"] for r in rows), len(rows)]
    # official stages whose top-10 reproduced exactly (sensitivity)
    rows = [r for r in rows_all if r["run"] not in EXCLUDE_A and r["arm"] == "official" and r["top10_match"]]
    res["official_top10_matched_only"] = table(rows)
    json.dump(res, open(OUT, "w"), indent=1)
    for setname in ["A_set_394", "E1_counted_set"]:
        print("=====", setname, res[setname]["top10_match"])
        for g, t in res[setname].items():
            if g == "top10_match":
                continue
            p, c = t["point"], t["ci95"]
            print(f"{g:16s} n={t['n_stages']:3d} runs={t['n_runs']:2d}")
            for k in ["move_obs", "move_plc", "move_plc_a", "move_plc_b", "move_orc", "move_floor",
                      "diff_move_plc_minus_floor", "diff_move_obs_minus_floor", "diff_move_orc_minus_floor", "paired_med_plc_minus_floor",
                      "same_obs", "same_plc", "same_orc", "same_floor", "ovl_obs", "ovl_plc", "ovl_orc", "ovl_floor",
                      "rho_obs", "rho_plc", "rho_orc", "rho_floor"]:
                print(f"   {k:30s} {p[k]:7.3f}  [{c[k][0]:7.3f}, {c[k][1]:7.3f}]")
    t = res["official_top10_matched_only"]
    print("official top10-matched only n=", t["n_stages"], "diff", t["point"]["diff_move_plc_minus_floor"], t["ci95"]["diff_move_plc_minus_floor"])


if __name__ == "__main__":
    main()
