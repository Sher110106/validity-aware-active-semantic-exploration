#!/usr/bin/env python3
"""Summaries of stages.jsonl for the offline decision bench (PREREGISTRATION_BENCH.md).

- yardstick check (U_wall vs U_360 at the real stop, share mapped at k+1);
- regret tables: rules R1-R6 x guess sets, by arm and pooled, U_wall and
  U_wall_cone, raw and normalised, with a stage bootstrap (resample stages
  within run, 2,000 draws, seed 0; one resample matrix per stage subset, so all
  quantities on a subset are paired);
- the decision rule exactly as written;
- R5 against R1 and against every guess-based rule (no decision attached).
Writes summary.json. Sensitivity variants of the wall test are reported under
"sensitivity" and feed no decision."""
import json
import os
from collections import OrderedDict

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
B = 2000
ARMS = ["official", "placebo", "filter_only", "oracle_visible"]
SETS = ["actual", "none", "placebo_A", "placebo_B", "oracle"]
RULES = ["R1", "R2", "R3", "R4", "R5", "R6"]
ALL = [json.loads(l) for l in open(os.path.join(OUT, "stages.jsonl"))]
USED = [r for r in ALL if "error" not in r and "drop" not in r]
USED.sort(key=lambda r: (r["run_idx"], r["stage"]))


def boot_idx(rows, seed=0):
    """(B, n) indices: resample stages within run (runs in run-list order)."""
    runs = []
    by = OrderedDict()
    for i, r in enumerate(rows):
        by.setdefault(r["run"], []).append(i)
    rng = np.random.default_rng(seed)
    idx = np.empty((B, len(rows)), dtype=np.int64)
    for b in range(B):
        parts = [np.asarray(v)[rng.integers(0, len(v), len(v))] for v in by.values()]
        idx[b] = np.concatenate(parts)
    runs = list(by)
    return idx, runs


def ci(x):
    lo, hi = np.percentile(x, [2.5, 97.5])
    return [float(lo), float(hi)]


def regret_vec(rows, U_key, rule, s, norm=False, var=None):
    out = []
    for r in rows:
        U = np.asarray(r["Uwall_var"][var] if var else r[U_key], float)
        mx = U.max()
        if rule == "R6":
            v = mx - U[r["r6_picks"]].mean()
        else:
            v = mx - U[r["picks"][s][rule]]
        out.append(v / mx if norm else v)
    return np.array(out)


def subset_for(rows, U_key, norm, var=None):
    if not norm:
        return rows
    return [r for r in rows if max(r["Uwall_var"][var] if var else r[U_key]) > 0]


def table(rows, U_key, norm=False, var=None):
    rows = subset_for(rows, U_key, norm, var)
    if not rows:
        return {"n_stages": 0}, {}, None
    idx, runs = boot_idx(rows)
    t = {"n_stages": len(rows), "n_runs": len(runs), "cells": {}}
    vecs = {}
    for rule in RULES:
        t["cells"][rule] = {}
        for s in SETS:
            v = regret_vec(rows, U_key, rule, s, norm, var)
            vecs[(rule, s)] = v
            t["cells"][rule][s] = {"mean": float(v.mean()), "ci95": ci(v[idx].mean(1))}
    return t, vecs, idx


def decision(rows, U_key, norm=False, var=None):
    """Condition (a) on all used stages pooled; condition (b) on official stages."""
    res = {}
    rows_n = subset_for(rows, U_key, norm, var)
    _, va, ia = table(rows_n, U_key, norm, var) if rows_n else (None, None, None)
    off = [r for r in rows_n if r["arm"] == "official"]
    _, vb, ib = table(off, U_key, norm, var)
    for rule in ["R1", "R2", "R3", "R4"]:
        o, pa = va[(rule, "oracle")], va[(rule, "placebo_A")]
        num, den = o[ia].mean(1), pa[ia].mean(1)
        with np.errstate(divide="ignore", invalid="ignore"):
            rb = num / den
        ratio = float(o.mean() / pa.mean()) if pa.mean() > 0 else None
        rb_f = rb[np.isfinite(rb)]
        ci_r = ci(rb_f) if len(rb_f) else None
        a_ok = bool(ratio is not None and ratio <= 0.7 and ci_r is not None and ci_r[1] < 1 and len(rb_f) == B)
        llm, pa_o, pb_o = vb[(rule, "actual")], vb[(rule, "placebo_A")], vb[(rule, "placebo_B")]
        dlp = llm - pa_o
        dba = pb_o - pa_o
        boot_d = dlp[ib].mean(1)
        boot_f = dba[ib].mean(1)
        floor = float(np.percentile(boot_f, 2.5))
        ci_d = ci(boot_d)
        b_ok = bool(llm.mean() < pa_o.mean() and ci_d[1] < floor)
        res[rule] = {
            "a": {"n_stages": len(rows_n), "oracle_mean": float(o.mean()), "placebo_A_mean": float(pa.mean()),
                  "ratio": ratio, "ratio_ci95": ci_r, "n_boot_finite": int(len(rb_f)),
                  "ratio_le_0.7": bool(ratio is not None and ratio <= 0.7),
                  "ci_wholly_below_1": bool(ci_r is not None and ci_r[1] < 1), "pass": a_ok},
            "b": {"n_stages": len(off), "LLM_mean": float(llm.mean()), "placebo_A_mean": float(pa_o.mean()),
                  "placebo_B_mean": float(pb_o.mean()), "LLM_minus_A": float(dlp.mean()), "LLM_minus_A_ci95": ci_d,
                  "B_minus_A": float(dba.mean()), "B_minus_A_ci95": ci(boot_f), "noise_floor_p2.5": floor,
                  "LLM_below_A": bool(llm.mean() < pa_o.mean()), "ci_wholly_below_floor": bool(ci_d[1] < floor),
                  "pass": b_ok},
            "both": bool(a_ok and b_ok)}
    res["go_live"] = any(res[r]["both"] for r in ["R1", "R2", "R3", "R4"])
    return res


def r5_compare(rows, U_key, norm=False):
    rows = subset_for(rows, U_key, norm)
    _, v, idx = table(rows, U_key, norm)
    out = {"n_stages": len(rows)}
    for s in SETS:
        out[s] = {}
        for rule in ["R1", "R2", "R3", "R4"]:
            d = v[(rule, s)] - v[("R5", s)]
            bd = d[idx].mean(1)
            c = ci(bd)
            out[s][rule] = {"rule_minus_R5": float(d.mean()), "ci95": c, "beats_R5": bool(c[1] < 0)}
    out["any_guess_rule_beats_R5"] = sorted(f"{rule}/{s}" for s in SETS for rule in ["R1", "R2", "R3", "R4"]
                                            if out[s][rule]["beats_R5"])
    return out


def yard(rows, keys):
    ys = [r for r in rows if r.get("yard")]
    if not ys:
        return {"n_stages": 0}
    idx, runs = boot_idx(ys)
    out = {"n_stages": len(ys), "n_runs": len(runs)}
    arr = {}
    for k in keys:
        a = np.array([[r["yard"][k][f] for f in ("n_in", "in_mapped", "n_out", "out_mapped")] for r in ys], float)
        arr[k] = a
        S = a.sum(0)
        si, so = S[1] / S[0] if S[0] else None, S[3] / S[2] if S[2] else None
        bs = a[idx].sum(1)  # (B,4)
        with np.errstate(divide="ignore", invalid="ignore"):
            bsep = bs[:, 1] / bs[:, 0] - bs[:, 3] / bs[:, 2]
            brat = (bs[:, 1] / bs[:, 0]) / (bs[:, 3] / bs[:, 2])
        out[k] = {"n_in": int(S[0]), "in_mapped": int(S[1]), "n_out": int(S[2]), "out_mapped": int(S[3]),
                  "share_in": si, "share_out": so,
                  "separation_in_minus_out": (si - so) if si is not None and so is not None else None,
                  "separation_ci95": ci(bsep[np.isfinite(bsep)]) if np.isfinite(bsep).any() else None,
                  "ratio_in_over_out": (si / so) if si is not None and so else None,
                  "ratio_ci95": ci(brat[np.isfinite(brat)]) if np.isfinite(brat).any() else None,
                  "stages_with_in_gt0": int((a[:, 0] > 0).sum())}
    ref = arr["U360"]
    for k in keys:
        if k == "U360":
            continue
        a = arr[k]
        bs, br = a[idx].sum(1), ref[idx].sum(1)
        with np.errstate(divide="ignore", invalid="ignore"):
            d = (bs[:, 1] / bs[:, 0] - bs[:, 3] / bs[:, 2]) - (br[:, 1] / br[:, 0] - br[:, 3] / br[:, 2])
        d = d[np.isfinite(d)]
        sep_k, sep_r = out[k]["separation_in_minus_out"], out["U360"]["separation_in_minus_out"]
        out[k]["minus_U360_separation"] = (sep_k - sep_r) if sep_k is not None and sep_r is not None else None
        out[k]["minus_U360_ci95"] = ci(d) if len(d) else None
        out[k]["n_boot_finite"] = int(len(d))
        out[k]["separates_at_least_as_well"] = bool(sep_k is not None and sep_r is not None and sep_k >= sep_r)
    return out


def main():
    drops = {"bench_errors": [(r["run"], r["stage"], r.get("error")) for r in ALL if "error" in r],
             "bench_top10_mismatch": [(r["run"], r["stage"], r.get("drop")) for r in ALL if "drop" in r]}
    audit = [json.loads(l) for l in open("/tmp/cvp_review/audit/audit/stages.jsonl")]
    drops["audit_replay_mismatch_before_384"] = [(r["run"], r["stage"]) for r in audit
                                                 if not (r.get("top10_match") and "rho_total_U360" in r)]
    S = {"prereg_sha256": "2571a7ef15f7a3bef974ef37f8fddcb964bfa2954d91f08d9a581d24af842f22",
         "n_rows": len(ALL), "n_used": len(USED), "drops": drops,
         "n_by_arm": {a: sum(1 for r in USED if r["arm"] == a) for a in ARMS},
         "n_runs_by_arm": {a: len({r["run"] for r in USED if r["arm"] == a}) for a in ARMS},
         "seeds": {"bootstrap": "numpy default_rng(0), 2000 draws, one resample matrix per stage subset, runs in "
                                "runs.txt order, stages sorted by stage number within run",
                   "placebo_A": "default_rng([20261029, run_idx, stage, gid, 1])",
                   "placebo_B": "default_rng([20261029, run_idx, stage, gid, 2])",
                   "oracle": "default_rng([20261029, run_idx, stage, gid, 3])",
                   "R6": "default_rng([20261029, run_idx, stage, 0, 4]).integers(0, n_cand, 50)",
                   "run_idx": "0-based line number in /tmp/cvp_review/analysis_pre/runs.txt"}}
    # sanity: R1/actual pick equals the logged ASP first-stage best
    S["R1_actual_equals_logged_first_stage_best"] = int(sum(r["asp_R1_actual_matches_logged"] for r in USED))
    # yardstick check
    ykeys = ["Uwall", "U360"]
    S["yardstick_check"] = yard(USED, ykeys)
    S["yardstick_check"]["by_arm"] = {a: yard([r for r in USED if r["arm"] == a], ykeys) for a in ARMS}
    yc = S["yardstick_check"]["Uwall"]
    S["yardstick_check"]["verdict"] = ("U_wall separates at least as well as U_360" if yc["separates_at_least_as_well"]
                                       else "U_wall does NOT separate as well as U_360: bench results provisional")
    S["provisional"] = not yc["separates_at_least_as_well"]
    # regret tables
    S["tables"] = {}
    for U_key in ("Uwall", "Ucone"):
        for norm in (False, True):
            name = f"{U_key}{'_norm' if norm else ''}"
            S["tables"][name] = {"pooled": table(USED, U_key, norm)[0]}
            for a in ARMS:
                rows = [r for r in USED if r["arm"] == a]
                S["tables"][name][a] = table(rows, U_key, norm)[0]
    # decision rule, as written: U_wall, raw regret
    S["decision"] = decision(USED, "Uwall")
    S["decision_reported_only"] = {"Ucone": decision(USED, "Ucone"), "Uwall_norm": decision(USED, "Uwall", True),
                                   "Ucone_norm": decision(USED, "Ucone", True)}
    # filter_only, reported separately: actual (filtered LLM) vs placebo A, same machinery as (b)
    fo = [r for r in USED if r["arm"] == "filter_only"]
    if not fo:
        fo = USED[:1]  # partial-data test only
    _, vf, ifo = table(fo, "Uwall")
    S["filter_only_actual_vs_placebo"] = {}
    for rule in ["R1", "R2", "R3", "R4"]:
        d = vf[(rule, "actual")] - vf[(rule, "placebo_A")]
        f = vf[(rule, "placebo_B")] - vf[(rule, "placebo_A")]
        S["filter_only_actual_vs_placebo"][rule] = {
            "n_stages": len(fo), "actual_minus_A": float(d.mean()), "ci95": ci(d[ifo].mean(1)),
            "floor_p2.5": float(np.percentile(f[ifo].mean(1), 2.5))}
    S["R5_comparisons"] = {"Uwall": r5_compare(USED, "Uwall"), "Ucone": r5_compare(USED, "Ucone"),
                           "Uwall_norm": r5_compare(USED, "Uwall", True)}
    # sensitivity (not pre-registered)
    vkeys = ["Uwall_" + v for v in USED[0]["Uwall_var"]]
    sens = {"note": "not pre-registered; no decision uses these",
            "yardstick_check": yard(USED, ["Uwall", "U360"] + vkeys), "decision": {}}
    for v in USED[0]["Uwall_var"]:
        sens["decision"][v] = decision(USED, None, False, v)
        sens["decision"][v] = {k: ({"a_ratio": x["a"]["ratio"], "a_ci": x["a"]["ratio_ci95"], "a_pass": x["a"]["pass"],
                                    "b_LLM_minus_A": x["b"]["LLM_minus_A"], "b_ci": x["b"]["LLM_minus_A_ci95"],
                                    "b_floor": x["b"]["noise_floor_p2.5"], "b_pass": x["b"]["pass"]}
                                   if isinstance(x, dict) else x) for k, x in sens["decision"][v].items()}
    S["sensitivity"] = sens
    # stage-level descriptors
    S["descriptors"] = {
        "Uwall_max_mean": float(np.mean([r["Uwall_max"] for r in USED])),
        "Uwall_max_zero_stages": int(sum(r["Uwall_max"] == 0 for r in USED)),
        "Ucone_max_zero_stages": int(sum(r["Ucone_max"] == 0 for r in USED)),
        "Uwall_mean_over_cands": float(np.mean([np.mean(r["Uwall"]) for r in USED])),
        "U360_mean_over_cands": float(np.mean([np.mean(r["U360"]) for r in USED])),
        "rho_Uwall_U360_median": float(np.median([r["rho_Uwall_U360"] for r in USED if r["rho_Uwall_U360"] is not None])),
        "rho_total_Uwall_median": float(np.median([r["rho_total_Uwall"] for r in USED if r["rho_total_Uwall"] is not None])),
        "stop_in_wall_cell": int(sum(bool(r.get("stop_in_wall_cell")) for r in USED)),
        "cand_in_wall_cell_frac_mean": float(np.mean([r["cand_in_wall_cell_frac"] for r in USED])),
        "cand_outside_grid_frac_mean": float(np.mean([r["cand_outside_grid_frac"] for r in USED])),
        "oracle_fallback_members": int(sum(m["fallback"] for r in USED for m in r["oracle_info"])),
        "oracle_members": int(sum(len(r["oracle_info"]) for r in USED)),
        "cpu_seconds_stage_sum": float(sum(r.get("secs", 0) for r in USED)),
    }
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
    return S


if __name__ == "__main__":
    S = main()
    print(json.dumps({k: S[k] for k in ("n_used", "n_by_arm", "provisional")}, indent=1))
