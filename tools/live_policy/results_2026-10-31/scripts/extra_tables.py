#!/usr/bin/env python3
"""Derived numbers the write-up quotes that no other output holds.

- E1 pacing flag (PREREGISTRATION_E1: a pair is flagged if the placebo's delay
  differs from its official partner's LLM wait by more than 20% at three or
  more stages), from each stage's live_policy.jsonl in the off-host copy.
- F1 at 30 m and 60 m per counted run (HM3D reference, author-faithful,
  linear interpolation on the stage curve, hold-last past the final stage),
  with the spread between seeds within each arm and scene.
- Path overlap from reviewer A's paths_pairs.json: stage-0 split share and
  gap, and swept-area Jaccard at 60 m (2 m radius), all runs and counted only.
- Range of per-run base mapping rates (stage_diagnostics.json).
- Spend from run_table.csv.

Usage: extra_tables.py <package_dir> <copy_campaign_dir> <paths_pairs.json>
Writes <package_dir>/analysis/extra_tables.json.
"""
import csv
import glob
import json
import os
import re
import statistics
import sys

PAIRS = {("00853", 42): ("e1_00853_s42_official_60m", "e1_00853_s42_placebo_60m"),
         ("00853", 43): ("e1_00853_s43_official_60m", "e1_00853_s43_placebo_60m"),
         ("00871", 42): ("e1_00871_s42_official_60m", "e1_00871_s42_placebo_60m"),
         ("00871", 43): ("e1_00871_s43_official_60m", "e1_00871_s43_placebo_60m_rerun1"),
         ("00871", 44): ("e1_00871_s44_official_60m", "e1_00871_s44_placebo_60m")}


def stage_records(campaign, run):
    out = {}
    for f in glob.glob(os.path.join(campaign, run, "stages", "*", "live_policy.jsonl")):
        k = os.path.basename(os.path.dirname(f))
        if k.isdigit():
            out[int(k)] = [json.loads(line) for line in open(f) if line.strip()]
    return out


def value_at(stages, key, x):
    pts = sorted((s["path_m"], s[key]) for s in stages if key in s and s.get("path_m") is not None)
    if not pts:
        return None
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[0][1]


def main():
    pkg, campaign, pairs_path = sys.argv[1:4]
    out = {}

    flags = {}
    for (scene, seed), (o, p) in PAIRS.items():
        ro, rp = stage_records(campaign, o), stage_records(campaign, p)
        rows = []
        for k in sorted(set(ro) & set(rp)):
            w, d = ro[k][-1].get("llm_wait_s"), rp[k][-1].get("delay_s")
            if w and d is not None:
                rows.append({"stage": k, "llm_wait_s": round(w, 1), "placebo_delay_s": d, "off_by_more_than_20pct": abs(d - w) / w > 0.2})
        n_off = sum(r["off_by_more_than_20pct"] for r in rows)
        flags[f"{scene}_s{seed}"] = {"official": o, "placebo": p, "stages_compared": len(rows), "stages_off": n_off,
                                    "flagged": n_off >= 3, "rows": rows}
    out["pacing_flag"] = flags

    rt = {r["run"]: r for r in csv.DictReader(open(os.path.join(pkg, "run_table.csv")))}
    counted = {n for n, r in rt.items() if r["status"] == "counted"}
    scores = {os.path.basename(r["run_dir"]): r for r in json.load(open(os.path.join(pkg, "analysis", "all_scores.json")))}
    f1 = {}
    for name in sorted(counted):
        st = scores[name].get("hm3d_stages", [])
        f1[name] = {"arm": rt[name]["arm"], "scene": rt[name]["scene"],
                    "f1_30m": round(value_at(st, "af_f1", 30.0), 4), "f1_60m": round(value_at(st, "af_f1", 60.0), 4)}
    out["f1_points"] = f1
    groups = {}
    for name, v in f1.items():
        groups.setdefault(f"{v['arm']}:{v['scene']}", []).append(v)
    out["f1_by_arm_scene"] = {g: {"n": len(v), "f1_30m_mean": round(statistics.mean(x["f1_30m"] for x in v), 4),
                                  "f1_60m_mean": round(statistics.mean(x["f1_60m"] for x in v), 4),
                                  "f1_60m_spread_points": round(100 * (max(x["f1_60m"] for x in v) - min(x["f1_60m"] for x in v)), 1)}
                              for g, v in sorted(groups.items())}

    pairs = json.load(open(pairs_path))
    rows = pairs  # one record per run pair within a scene, with its kind
    summ = {}
    for subset, keep in (("all", lambda r: True), ("counted", lambda r: r["a"] in counted and r["b"] in counted)):
        for k in ("same_arm_same_seed", "same_arm_diff_seed", "diff_arm_same_seed", "diff_arm_diff_seed"):
            sel = [r for r in rows if r["kind"] == k and keep(r)]
            j = [r["J60_r2"] for r in sel if r.get("J60_r2") is not None]
            d0 = [r["d_stage"]["0"] for r in sel if "0" in (r.get("d_stage") or {})]
            summ[f"{subset}:{k}"] = {"pairs": len(sel),
                                     "split_at_stage0_share": round(sum(r.get("first_div") == 0 for r in sel) / len(sel), 3) if sel else None,
                                     "stage0_gap_median_m": round(statistics.median(d0), 2) if d0 else None,
                                     "J60_r2_median": round(statistics.median(j), 3) if j else None, "J60_n": len(j)}
    out["paths"] = summ

    diag = json.load(open(os.path.join(pkg, "analysis", "stage_diagnostics.json")))
    rates = [d["base_rate"]["mapped_k1"] for d in diag if d.get("base_rate", {}).get("mapped_k1") is not None]
    out["base_rate_k1"] = {"min": round(min(rates), 4), "max": round(max(rates), 4), "runs": len(rates)}

    # Registered null form: the MDE as a share of the mean AUC of the runs in the contrast.
    nf = {}
    for name in ("E1_hm3d_60m", "E2_hm3d_60m", "E3_hm3d_60m", "E3_vs_official_hm3d_60m"):
        t = json.load(open(os.path.join(pkg, "analysis", f"{name}.json")))
        vals = [x for v in t["per_scene"].values() for k, xs in v.items() if k != "diff_of_means" for x in xs]
        nf[name] = {"mde": round(t["mde_alpha05_power80"], 4), "mean_auc": round(statistics.mean(vals), 4),
                    "mde_share_of_mean_auc": round(t["mde_alpha05_power80"] / statistics.mean(vals), 3)}
    # MDE as a range: e1_analysis uses (1.96 + 0.84) * se; the t-based value uses
    # t(0.975, df) + t(0.80, df) with df = residual degrees of freedom (7 for E1 and E2).
    T = {4: 2.7764 + 0.9410, 5: 2.5706 + 0.9195, 6: 2.4469 + 0.9057, 7: 2.3646 + 0.8960, 8: 2.3060 + 0.8889}
    for name, df in (("E1_hm3d_60m", 7), ("E2_hm3d_60m", 7)):
        nf[name]["df"] = df
        nf[name]["mde_t"] = round(nf[name]["mde"] * T[df] / 2.80, 4)
    out["null_form"] = nf

    # Spend from every runner stop line: the last attempt of each name is the scored
    # run; earlier attempts under the same name were archived; dryrun_/e0_ are tests.
    stops = []
    for f in glob.glob(os.path.join(campaign, "runner_*.log")):
        for line in open(f):
            m = re.match(r"^(\S+) \[\S+\] (\S+): (\w+) at [\d.]+ m, \$([\d.]+)", line)
            if m:
                stops.append((m.group(1), m.group(2), float(m.group(4))))
    stops.sort()
    last = {}
    for t, name, c in stops:
        last[name] = (t, c)
    spend = {"scored_last_attempts": 0.0, "archived_attempts": 0.0, "tests_and_dry_runs": 0.0}
    for t, name, c in stops:
        if not re.match(r"^e[123]_", name):
            spend["tests_and_dry_runs"] += c
        elif last[name][0] == t:
            spend["scored_last_attempts"] += c
        else:
            spend["archived_attempts"] += c
    out["spend_from_stop_lines"] = {k: round(v, 2) for k, v in spend.items()}
    out["spend_from_stop_lines"]["total"] = round(sum(spend.values()), 2)

    # Validator: removed share and 0.5 m precision before and after, counted filter_only runs.
    sp = json.load(open(os.path.join(pkg, "analysis", "stage_precision.json")))
    fr = [r for r in sp["rows"] if r["run"] in counted and r["arm"] == "filter_only"]
    val = {}
    for scene in ("00853", "00871", "all"):
        rs = [r for r in fr if scene == "all" or r["scene"] == scene]
        raw_n, raw_h = sum(r["raw"]["n_new"] for r in rs), sum(r["raw"]["new_hits_0.5"] for r in rs)
        fin_n, fin_h = sum(r["final"]["n_new"] for r in rs), sum(r["final"]["new_hits_0.5"] for r in rs)
        rem_n, rem_h = sum(r["removed"]["n_new"] for r in rs), sum(r["removed"]["new_hits_0.5"] for r in rs)
        val[scene] = {"raw_new": raw_n, "removed_new": rem_n, "removed_share": round(rem_n / raw_n, 3),
                      "removed_hits_0.5": rem_h, "precision_raw_0.5": round(raw_h / raw_n, 4), "precision_kept_0.5": round(fin_h / fin_n, 4)}
    by_run = {}
    for r in fr:
        t = by_run.setdefault(r["run"], [0, 0])
        t[0] += r["removed"]["n_new"]
        t[1] += r["raw"]["n_new"]
    per_run = [a / b for a, b in by_run.values() if b]
    val["removed_share_per_run_range"] = [round(min(per_run), 3), round(max(per_run), 3)]
    out["validator"] = val

    cost = lambda sel: round(sum(float(r["cost_usd"] or 0) for r in sel), 2)
    out["spend_usd"] = {"counted_runs": cost(r for r in rt.values() if r["status"] == "counted"),
                        "all_scored_runs": cost(rt.values())}
    json.dump(out, open(os.path.join(pkg, "analysis", "extra_tables.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k in ("f1_by_arm_scene", "paths", "base_rate_k1", "spend_usd")}, indent=1))
    print({k: (v["stages_off"], v["stages_compared"], v["flagged"]) for k, v in flags.items()})


if __name__ == "__main__":
    main()
