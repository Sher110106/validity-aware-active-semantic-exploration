#!/usr/bin/env python3
"""Own recompute of tables and the decision rule from build/stages.jsonl.
Regrets are recomputed from the stored U arrays and picks (not read from the
stored regret field). Bootstrap: own implementation (resample stages within
run, 2000 draws, default_rng(0)); a second seed shows Monte-Carlo spread."""
import json
import sys

import numpy as np

rows = [json.loads(l) for l in open("/tmp/cvp_bench/bench/build/stages.jsonl")]
rows.sort(key=lambda r: (r["run_idx"], r["stage"]))
SETS = ["actual", "none", "placebo_A", "placebo_B", "oracle"]
RULES = ["R1", "R2", "R3", "R4", "R5", "R6"]


def reg(r, U, rule, s, norm=False):
    U = np.asarray(r[U], float)
    mx = U.max()
    v = mx - (U[r["r6_picks"]].mean() if rule == "R6" else U[r["picks"][s][rule]])
    return v / mx if norm else v


def boot(sub, seed=0, B=2000):
    runs = {}
    for i, r in enumerate(sub):
        runs.setdefault(r["run"], []).append(i)
    rng = np.random.default_rng(seed)
    return np.array([np.concatenate([np.array(v)[rng.integers(0, len(v), len(v))] for v in runs.values()]) for _ in range(B)])


def ci(x):
    return [round(float(v), 3) for v in np.percentile(x, [2.5, 97.5])]


def decision(sub_all, U="Uwall", norm=False, seed=0):
    if norm:
        sub_all = [r for r in sub_all if max(r[U]) > 0]
    off = [r for r in sub_all if r["arm"] == "official"]
    ia, ib = boot(sub_all, seed), boot(off, seed)
    out = {"n_a": len(sub_all), "n_b": len(off)}
    for rule in ["R1", "R2", "R3", "R4"]:
        o = np.array([reg(r, U, rule, "oracle", norm) for r in sub_all])
        a = np.array([reg(r, U, rule, "placebo_A", norm) for r in sub_all])
        rat = o[ia].mean(1) / a[ia].mean(1)
        L = np.array([reg(r, U, rule, "actual", norm) for r in off])
        A = np.array([reg(r, U, rule, "placebo_A", norm) for r in off])
        Bp = np.array([reg(r, U, rule, "placebo_B", norm) for r in off])
        dl = (L - A)[ib].mean(1)
        fl = float(np.percentile((Bp - A)[ib].mean(1), 2.5))
        out[rule] = {"oracle": round(o.mean(), 3), "pA": round(a.mean(), 3), "ratio": round(o.mean() / a.mean(), 4),
                     "ratio_ci": ci(rat), "a_pass": bool(o.mean() / a.mean() <= 0.7 and np.percentile(rat, 97.5) < 1),
                     "LLM": round(L.mean(), 3), "pA_off": round(A.mean(), 3), "pB_off": round(Bp.mean(), 3),
                     "LLM_minus_A": round((L - A).mean(), 3), "ci": ci(dl), "floor": round(fl, 3),
                     "b_pass": bool(L.mean() < A.mean() and np.percentile(dl, 97.5) < fl)}
    out["go_live"] = any(out[r]["a_pass"] and out[r]["b_pass"] for r in ["R1", "R2", "R3", "R4"])
    return out


def table(sub, U="Uwall", norm=False):
    idx = boot(sub)
    t = {}
    for rule in RULES:
        for s in SETS:
            v = np.array([reg(r, U, rule, s, norm) for r in sub])
            t[f"{rule}/{s}"] = (round(v.mean(), 3), ci(v[idx].mean(1)))
    return t


def yard(sub, key, idx):
    a = np.array([[r["yard"][key][f] for f in ("n_in", "in_mapped", "n_out", "out_mapped")] for r in sub], float)
    S = a.sum(0)
    bs = a[idx].sum(1)
    return a, S, bs


if __name__ == "__main__":
    res = {}
    # stored regret == recomputed regret?
    bad = 0
    for r in rows:
        for U in ("Uwall", "Ucone"):
            for s in SETS:
                for rule in RULES:
                    if abs(reg(r, U, rule, s) - r["regret"][U][s][rule]) > 1e-9:
                        bad += 1
    res["stored_regret_mismatches"] = bad
    res["decision_seed0"] = decision(rows)
    res["decision_seed1"] = decision(rows, seed=1)
    res["decision_Ucone"] = decision(rows, "Ucone")
    res["decision_Uwall_norm"] = decision(rows, "Uwall", True)
    res["pooled_Uwall"] = table(rows)
    res["official_Uwall"] = table([r for r in rows if r["arm"] == "official"])
    res["Uwall_max_mean"] = float(np.mean([max(r["Uwall"]) for r in rows]))
    # normalised regret pooled for R4/oracle
    res["norm_R4_oracle"] = float(np.mean([reg(r, "Uwall", "R4", "oracle", True) for r in rows if max(r["Uwall"]) > 0]))
    # yardstick
    ys = [r for r in rows if r.get("yard")]
    idx = boot(ys)
    yd = {"n": len(ys)}
    for key in ("Uwall", "U360"):
        a, S, bs = yard(ys, key, idx)
        si, so = S[1] / S[0], S[3] / S[2]
        yd[key] = {"sums": S.tolist(), "share_in": round(si, 4), "share_out": round(so, 4), "diff": round(si - so, 4),
                   "diff_ci": ci(bs[:, 1] / bs[:, 0] - bs[:, 3] / bs[:, 2]), "ratio": round(si / so, 2),
                   "ratio_ci": ci((bs[:, 1] / bs[:, 0]) / (bs[:, 3] / bs[:, 2]))}
    aw, _, bw = yard(ys, "Uwall", idx)
    a3, _, b3 = yard(ys, "U360", idx)
    g = (bw[:, 1] / bw[:, 0] - bw[:, 3] / bw[:, 2]) - (b3[:, 1] / b3[:, 0] - b3[:, 3] / b3[:, 2])
    yd["gap_diff"] = round(yd["Uwall"]["diff"] - yd["U360"]["diff"], 4)
    yd["gap_ci"] = ci(g)
    # per-stage paired alternative: mean over stages of (share_in - share_out), stages with n_in>0 for both
    res["yard"] = yd
    json.dump(res, open("/tmp/cvp_bench/bench/verify/recompute.json", "w"), indent=1)
    print(json.dumps(res, indent=1)[:12000])
