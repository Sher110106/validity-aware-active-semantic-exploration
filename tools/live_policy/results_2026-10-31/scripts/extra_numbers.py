#!/usr/bin/env python3
"""Append the write-up's exploratory numbers to numbers.csv.

build_results.py records the registered results and mechanism tables. The
write-up also quotes the decision replay, the objective audit, the E3 ceilings,
the headroom table and the static three-way table. This reads each of those
values from its JSON file, so numbers.csv names the file and key behind every
number in the write-up.

Usage: extra_numbers.py <numbers.csv> <static_three_way.json>
Paths to the review outputs are relative to this file's directory.
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = "review_2026-10-29/audit"
ARMS = ("official", "placebo", "filter_only", "oracle_visible")


def get(rel, path):
    value = json.load(open(os.path.join(HERE, rel)))
    for part in path.split("/"):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def main():
    out_csv, static_path = sys.argv[1], sys.argv[2]
    rows = []

    def add(key, rel, path, nd=4):
        v = get(rel, path)
        rows.append({"key": key, "value": round(v, nd) if isinstance(v, float) else v, "source": f"{rel}:{path}"})

    s, c, sens = f"{AUDIT}/audit/summary.json", f"{AUDIT}/audit/cf_summary.json", f"{AUDIT}/verify_audit/sens_summary.json"
    add("audit:stages_used", s, "n_used")
    add("audit:stages_replayed", s, "n_replayed")
    for a in ARMS:
        add(f"audit:rho_score_U360_median:{a}", s, f"by_arm/{a}/rho/rho_total_U360/median")
        add(f"audit:stop_pct_mean:{a}", s, f"by_arm/{a}/pct/pct_stop/mean")
        add(f"audit:stop_pct_ci_lo:{a}", s, f"by_arm/{a}/pct/pct_stop/ci95/0")
        add(f"audit:stop_pct_ci_hi:{a}", s, f"by_arm/{a}/pct/pct_stop/ci95/1")
        add(f"audit:stop_pct_floor_candidates:{a}", sens, f"{a}/pct_stop_nav/0")
        add(f"audit:yardstick_in_view_mapped:{a}", s, f"by_arm/{a}/yardstick/share_in_sl")
        add(f"audit:yardstick_out_of_view_mapped:{a}", s, f"by_arm/{a}/yardstick/share_out_sl")
        add(f"audit:rho_r1.0_median:{a}", sens, f"{a}/rho_r1.0_median")
        for h in ("actual", "obs", "plc", "orc"):
            add(f"cf:rho_score_U360_median:{a}:{h}", c, f"by_arm/{a}/{h}:rho_total_U360/median")
        add(f"cf:paired_actual_minus_placebo_median:{a}", c, f"by_arm/{a}/paired_actual_minus_plc:rho_total_U360/median")
        add(f"cf:paired_oracle_minus_placebo_median:{a}", c, f"by_arm/{a}/paired_orc_minus_plc:rho_total_U360/median")
        add(f"cf:far_from_walked_path_rho_median:{a}", c, f"by_arm/{a}/frontier:rho_dwalk_U360/median")
    add("audit:yardstick_in_view_mapped:all", s, "all/yardstick/share_in_sl")

    r = f"{AUDIT}/tables/replay_table.json"
    for k in ("move_plc", "move_floor", "diff_move_plc_minus_floor", "rho_plc", "rho_floor"):
        add(f"replay:official:{k}", r, f"A_set_394/official/point/{k}")
    add("replay:official:diff_move_plc_minus_floor:ci_lo", r, "A_set_394/official/ci95/diff_move_plc_minus_floor/0")
    add("replay:official:diff_move_plc_minus_floor:ci_hi", r, "A_set_394/official/ci95/diff_move_plc_minus_floor/1")
    add("replay:official:n_stages", r, "A_set_394/official/n_stages")

    rk = f"{AUDIT}/tables/rank_reconcile.json"
    add("rank:published_target_is_first_stage_best", rk, "A_set_A_filter/rank_unfilt_pathlog/all/share_all")

    e3 = f"{AUDIT}/tables/e3_ceiling_exact.json"
    ceilings = json.load(open(os.path.join(HERE, e3)))
    for run, v in ceilings.items():
        if not isinstance(v, dict) or "live_share_of_max_drawn_pooled" not in v:
            continue
        add(f"e3_ceiling:live_share_pooled:{run}", e3, f"{run}/live_share_of_max_drawn_pooled")
        add(f"e3_ceiling:live_share_unit_mean:{run}", e3, f"{run}/live_share_of_max_drawn_unit_mean")
        add(f"e3_ceiling:live_share_unit_mean_ci_lo:{run}", e3, f"{run}/live_share_ci95_unit_mean/0")
        add(f"e3_ceiling:live_share_unit_mean_ci_hi:{run}", e3, f"{run}/live_share_ci95_unit_mean/1")

    hd = f"{AUDIT}/tables/headroom_table.json"
    for scene in ("00853", "00871"):
        add(f"headroom:frontier_recall_final:{scene}", hd, f"frontier/{scene}/af_recall_final")
        add(f"headroom:frontier_recall_at_60m:{scene}", hd, f"frontier/{scene}/af_recall_at_60m")

    add("replay:official:diff_move_oracle_minus_floor", r, "A_set_394/official/point/diff_move_orc_minus_floor")
    add("replay:official:diff_move_oracle_minus_floor:ci_lo", r, "A_set_394/official/ci95/diff_move_orc_minus_floor/0")
    add("replay:official:diff_move_oracle_minus_floor:ci_hi", r, "A_set_394/official/ci95/diff_move_orc_minus_floor/1")
    add("replay:official_counted_only:diff_move_plc_minus_floor", r, "E1_counted_set/official/point/diff_move_plc_minus_floor")
    add("replay:official_counted_only:ci_lo", r, "E1_counted_set/official/ci95/diff_move_plc_minus_floor/0")
    add("replay:official_counted_only:ci_hi", r, "E1_counted_set/official/ci95/diff_move_plc_minus_floor/1")
    bs = f"{AUDIT}/verify_audit/boot_sens.json"
    for a in ARMS:
        add(f"audit:stop_pct_floor_ci_lo:{a}", sens, f"{a}/pct_stop_nav/1/0")
        add(f"audit:stop_pct_floor_ci_hi:{a}", sens, f"{a}/pct_stop_nav/1/1")
        add(f"audit:stop_pct_run_cluster_ci_lo:{a}", bs, f"{a}/cluster_ci/0")
        add(f"audit:stop_pct_run_cluster_ci_hi:{a}", bs, f"{a}/cluster_ci/1")
    for scene in ("00853", "00871"):
        add(f"headroom:frontier_hm3d_auc_f1_60m:{scene}", hd, f"frontier/{scene}/hm3d_auc_af_f1_to_60m")
    hdj = json.load(open(os.path.join(HERE, hd)))
    for k in sorted(hdj.get("arm_scene", {})):
        if "af_recall_at_60m_mean" in hdj["arm_scene"][k]:
            add(f"headroom:recall_at_60m_mean:{k}", hd, f"arm_scene/{k}/af_recall_at_60m_mean")

    pkg = "results_2026-10-31/analysis"
    ex = f"{pkg}/extra_tables.json"
    exj = json.load(open(os.path.join(HERE, ex)))
    for cell in exj["pacing_flag"]:
        add(f"pacing_flag:stages_off:{cell}", ex, f"pacing_flag/{cell}/stages_off")
        add(f"pacing_flag:stages_compared:{cell}", ex, f"pacing_flag/{cell}/stages_compared")
    for run in exj["f1_points"]:
        for k in ("f1_30m", "f1_60m"):
            add(f"f1_points:{k}:{run}", ex, f"f1_points/{run}/{k}")
    for g in exj["f1_by_arm_scene"]:
        for k in ("f1_30m_mean", "f1_60m_mean", "f1_60m_spread_points"):
            add(f"f1_points:{k}:{g}", ex, f"f1_by_arm_scene/{g}/{k}")
    for g in exj["paths"]:
        for k in ("pairs", "split_at_stage0_share", "stage0_gap_median_m", "J60_r2_median"):
            if exj["paths"][g][k] is not None:
                add(f"paths:{k}:{g}", ex, f"paths/{g}/{k}")
    for name in exj["null_form"]:
        add(f"null_form:mde_share_of_mean_auc:{name}", ex, f"null_form/{name}/mde_share_of_mean_auc", 3)
        add(f"null_form:mean_auc:{name}", ex, f"null_form/{name}/mean_auc")
    for scene in ("00853", "00871", "all"):
        for k in ("raw_new", "removed_new", "removed_share", "removed_hits_0.5", "precision_raw_0.5", "precision_kept_0.5"):
            add(f"validator:{k}:{scene}", ex, f"validator/{scene}/{k}")
    add("validator:removed_share_per_run_min", ex, "validator/removed_share_per_run_range/0")
    add("validator:removed_share_per_run_max", ex, "validator/removed_share_per_run_range/1")
    add("base_rate_k1:min", ex, "base_rate_k1/min")
    add("base_rate_k1:max", ex, "base_rate_k1/max")
    add("spend:counted_runs", ex, "spend_usd/counted_runs", 2)
    add("spend:all_scored_runs", ex, "spend_usd/all_scored_runs", 2)
    ag = f"{pkg}/agreement.json"
    for a in ARMS:
        add(f"agreement:same_label_1m:{a}", ag, f"{a}/same_label_1m")
    for b in (60, 50):
        lr = f"{pkg}/E2_hm3d_{b}m_latency_rule.json"
        add(f"E2_latency_rule:{b}m:statistic", lr, "statistic")
        add(f"E2_latency_rule:{b}m:p", lr, "blocked_permutation_p")
        add(f"E2_latency_rule:{b}m:n_relabelings", lr, "n_relabelings")
    add("E2_latency_rule:60m:boot_lo", f"{pkg}/E2_hm3d_60m_latency_rule.json", "bootstrap_95ci/0")
    add("E2_latency_rule:60m:boot_hi", f"{pkg}/E2_hm3d_60m_latency_rule.json", "bootstrap_95ci/1")
    for fam in ("E1", "E2", "E3"):
        for b in (60, 50):
            add(f"signflip_p:{fam}:hm3d:{b}m", f"{pkg}/{fam}_hm3d_{b}m.json", "seed_paired_signflip_p")
        for m in ("object_f1", "af_recall", "object_recall", "normalized_ged"):
            sec = f"{pkg}/secondary/{fam}_hm3d_{m}_60m.json"
            add(f"secondary:{fam}:{m}:statistic", sec, "statistic")
            add(f"secondary:{fam}:{m}:p", sec, "blocked_permutation_p")

    fr_rel = f"{pkg}/frontier_60m_scores.json"
    for i, fr in enumerate(json.load(open(os.path.join(HERE, fr_rel)))):
        rows.append({"key": f"inflation:frontier_run:{fr['scene']}", "value": round(fr["auc_af_f1_to_60m"] / fr["hm3d_auc_af_f1_to_60m"], 2),
                     "source": f"{fr_rel}:{i}/auc_af_f1_to_60m / {i}/hm3d_auc_af_f1_to_60m"})
    ratios = [r["auc_af_f1_to_60m"] / r["hm3d_auc_af_f1_to_60m"] for r in json.load(open(os.path.join(HERE, pkg, "all_scores.json")))
              if r.get("hm3d_auc_af_f1_to_60m")]
    rows.append({"key": "inflation:live_runs_range", "value": f"{min(ratios):.2f}-{max(ratios):.2f}",
                 "source": f"{pkg}/all_scores.json: auc_af_f1_to_60m / hm3d_auc_af_f1_to_60m over all scored runs"})

    for a in ARMS:
        add(f"audit:n_stages:{a}", s, f"by_arm/{a}/n_stages")
    st0 = json.load(open(static_path))["runs"]
    drops = [t["observed_only"]["object_f1"] - t["official"]["object_f1"] for t in st0.values()]
    gaps = [abs(t["tau_1.0"]["object_f1"] - t["observed_only"]["object_f1"]) for t in st0.values()]
    rows.append({"key": "static:guesses_lower_f1_by_min", "value": round(min(drops), 4), "source": "static_three_way.json: min over runs of observed_only - official object_f1"})
    rows.append({"key": "static:guesses_lower_f1_by_max", "value": round(max(drops), 4), "source": "static_three_way.json: max over runs of observed_only - official object_f1"})
    rows.append({"key": "static:unanimity_vs_observed_max_gap", "value": round(max(gaps), 4), "source": "static_three_way.json: max over runs of |tau_1.0 - observed_only| object_f1"})

    for name in ("E1_hm3d_60m", "E2_hm3d_60m"):
        add(f"null_form:mde_t:{name}", ex, f"null_form/{name}/mde_t")
        rows.append({"key": f"null_form:mde_t_share_of_mean_auc:{name}",
                     "value": round(exj["null_form"][name]["mde_t"] / exj["null_form"][name]["mean_auc"], 3),
                     "source": f"{ex}: null_form/{name}/mde_t / null_form/{name}/mean_auc"})
    for k in ("scored_last_attempts", "archived_attempts", "tests_and_dry_runs", "total"):
        add(f"spend_stop_lines:{k}", ex, f"spend_from_stop_lines/{k}", 2)
    for fam in ("E1", "E2", "E3", "E3_vs_official"):
        for m in ("f1point30", "f1point60"):
            sec = f"{pkg}/secondary/{fam}_hm3d_{m}.json"
            add(f"secondary:{fam}:{m}:statistic", sec, "statistic")
            add(f"secondary:{fam}:{m}:p", sec, "blocked_permutation_p")
            for scene in json.load(open(os.path.join(HERE, sec)))["per_scene"]:
                add(f"secondary:{fam}:{m}:per_scene_d:{scene}", sec, f"per_scene/{scene}/diff_of_means")
    add("rank:ties_share", rk, "A_set_A_filter/share_ties_gt1")
    add("replay:top10_reproduced", r, "A_set_394/top10_match/ALL/0")
    add("replay:top10_stages", r, "A_set_394/top10_match/ALL/1")
    add("replay:official:diff_move_obs_minus_floor", r, "A_set_394/official/point/diff_move_obs_minus_floor")
    add("replay:official:diff_move_obs_minus_floor:ci_lo", r, "A_set_394/official/ci95/diff_move_obs_minus_floor/0")
    add("replay:official:diff_move_obs_minus_floor:ci_hi", r, "A_set_394/official/ci95/diff_move_obs_minus_floor/1")
    for setname, label in (("E1_counted_set/official", "counted"), ("A_set_394/official_00853", "00853"), ("A_set_394/official_00871", "00871")):
        add(f"replay:oracle_minus_floor:{label}", r, f"{setname}/point/diff_move_orc_minus_floor")
        add(f"replay:oracle_minus_floor:{label}:ci_lo", r, f"{setname}/ci95/diff_move_orc_minus_floor/0")
        add(f"replay:oracle_minus_floor:{label}:ci_hi", r, f"{setname}/ci95/diff_move_orc_minus_floor/1")
    for a in ARMS:
        for h in ("actual", "obs", "plc", "orc"):
            add(f"cf:rho_score_Ucone_median:{a}:{h}", c, f"by_arm/{a}/{h}:rho_total_Ucone/median")
        add(f"cf:far_from_walked_path_rho_Ucone_median:{a}", c, f"by_arm/{a}/frontier:rho_dwalk_Ucone/median")
    runs_rec = [v["af_recall_at_60m"] for k, v in hdj["runs"].items() if v.get("counted") and v.get("af_recall_at_60m") is not None]
    for scene in ("00853", "00871"):
        vals = [v["af_recall_at_60m"] for k, v in hdj["runs"].items() if v.get("counted") and v.get("scene") == scene and v.get("af_recall_at_60m") is not None]
        rows.append({"key": f"headroom:recall_at_60m_single_runs:{scene}", "value": f"{min(vals):.3f}-{max(vals):.3f}",
                     "source": f"{hd}:runs/*/af_recall_at_60m (counted E1/E2 runs)"})
    for b in (60, 50):
        lr = f"{pkg}/E2_hm3d_{b}m_latency_rule.json"
        for scene in ("00853", "00871"):
            add(f"E2_latency_rule:{b}m:per_scene_d:{scene}", lr, f"per_scene/{scene}/diff_of_means")
        add(f"E2_latency_rule:{b}m:mde", lr, "mde_alpha05_power80")
        add(f"E2_latency_rule:{b}m:signflip_p", lr, "seed_paired_signflip_p")
        add(f"E2_latency_rule:{b}m:min_attainable_p", lr, "min_attainable_p")
    add("E2_latency_rule:50m:boot_lo", f"{pkg}/E2_hm3d_50m_latency_rule.json", "bootstrap_95ci/0")
    add("E2_latency_rule:50m:boot_hi", f"{pkg}/E2_hm3d_50m_latency_rule.json", "bootstrap_95ci/1")
    rt = {x["run"]: x for x in csv.DictReader(open(os.path.join(HERE, "results_2026-10-31", "run_table.csv")))}
    for o, f_ in (("e1_00853_s42_official_60m", "e2_00853_s42_filter_only_60m"), ("e1_00871_s44_official_60m", "e2_00871_s44_filter_only_60m")):
        a, b = float(rt[o]["llm_wait_mean_s"]), float(rt[f_]["llm_wait_mean_s"])
        rows.append({"key": f"latency_gap_filter_vs_official:{o[3:12]}", "value": round((b - a) / a, 3),
                     "source": "run_table.csv llm_wait_mean_s (filter - official) / official"})
    ps = {k: get(f"{pkg}/{k}_hm3d_60m.json", "blocked_permutation_p") for k in ("E1", "E2", "E3")}
    order = sorted(ps, key=ps.get)
    run_max = 0.0
    for i, k in enumerate(order):
        run_max = max(run_max, min(1.0, (len(order) - i) * ps[k]))
        rows.append({"key": f"holm_three_families:{k}", "value": round(run_max, 3), "source": "Holm over E1, E2, E3 HM3D 60 m blocked_permutation_p"})

    sec_ps = {m: get(f"{pkg}/secondary/E1_hm3d_{m}{suffix}.json", "blocked_permutation_p")
              for m, suffix in (("object_f1", "_60m"), ("af_recall", "_60m"), ("object_recall", "_60m"),
                                ("normalized_ged", "_60m"), ("f1point30", ""), ("f1point60", ""))}
    order = sorted(sec_ps, key=sec_ps.get)
    run_max = 0.0
    for i, m in enumerate(order):
        run_max = max(run_max, min(1.0, (len(order) - i) * sec_ps[m]))
        rows.append({"key": f"holm_E1_secondaries:{m}", "value": round(run_max, 3),
                     "source": "Holm over the six E1 secondary blocked_permutation_p values (analysis/secondary/E1_*)"})

    # Numbers quoted from documents rather than JSON files.
    for key, value, src in (
        ("paper:asp_margin_over_frontier_f1_points", "2.5-7.9", "docs/checkin/review_2026-10-29/REVIEW_B_paper_field.md section 3 (ASP v2 Fig. 4, one run per scene)"),
        ("paper:asp_steps_m_vs_frontier", "3.74 vs 2.76", "docs/checkin/review_2026-10-29/REVIEW_B_paper_field.md section 2 (ASP v2 Fig. 3 caption)"),
        ("sept:unanimity_kept_of_predicted", "19 of 8,943", "docs/checkin/review_2026-10-29/CONTEXT_given_to_reviewers.md section 1"),
        ("sept:unanimity_vs_observed_only_f1", "0.5218/0.4349/0.4957 vs 0.5219/0.4351/0.4957", "docs/checkin/review_2026-10-29/CONTEXT_given_to_reviewers.md section 1"),
        ("sept:risk_term_beta1_stages_moved", "2, 0 and 3 stages", "FINAL_PLAN_2026-10-29.md package list (errata: beta <= 1 moved 2/0/3 stages)"),
        ("static8:precision_0.5m_deepseek_vs_placebo", "2.1% vs 1.4%", "docs/checkin/FABLE_REVIEW_2026-10-28.md (recount on 8 matched inputs)"),
        ("audit:stop_to_first_stage_best_median_m", 1.97, "docs/checkin/review_2026-10-29/AUDIT_objective_verified.md (Other checks: where the stop lands)"),
        ("audit:far_from_walked_path_stages", 361, "docs/checkin/review_2026-10-29/AUDIT_objective_verified.md (frontier proxy covers 361 stages)"),
        ("audit:official_llm_beats_placebo_stages", "73 of 119 (p 0.008)", "docs/checkin/review_2026-10-29/AUDIT_objective_verified.md (Table 2 text)"),
        ("prereg:scene_base_rates_pre_E3", "00853 9.5-12.3%, 00871 5.2-6.8%", "PREREGISTRATION_E3.md (in-run gate; base_rates_pre_E3.json)"),
        ("sept:validator_counts", "61->45 and 313->138", "docs/archive/PHASE13_DIAGNOSTICS_2026-09-17.md line 49 (validator columns of the aggregate row)"),
        ("sept:unanimity_removed_share", "99.8%", "derived from 19 of 8,943 kept (CONTEXT_given_to_reviewers.md section 1)"),
        ("audit:llm_vs_placebo_run_medians", "00853 +0.07 to +0.25; 00871 about 0", "docs/checkin/review_2026-10-29/AUDIT_objective_verified.md (Table 2 text, corrected)"),
        ("reproduce:files", "31 of 31 reproduce, 27 exactly", "tools/live_policy/reproduce.sh output, 2026-10-29 (DEVIATIONS item 35)"),
        ("runtable_bug:e1_00871_s42_official", "showed 0.92 h, $0.16; counted run 2.68 h, $0.81", "DEVIATIONS item 32 (d)"),
        ("spend_cap_usd", 40, "PREREGISTRATION_E1.md Spend (the OpenRouter key's $40 limit)"),
        ("placebo_prior_delay_s", "260/400/500", "PREREGISTRATION_E1.md Arms (Pacing: schedule 260 s, 400 s, then 500 s)"),
        ("e1_00853_s44_official_rerun1_stalled_at_m", 44.25, "DEVIATIONS.md item 27"),
        ("e1_00853_s44_official_first_attempt_m", 46.8, "DEVIATIONS.md item 17"),
        ("archived_attempts", 13, "/Users/sher/cvp_live_campaign_copy/runs/live_campaign: directories ending FAILED_ATTEMPT* or ABORTED_*"),
        ("copy_manifest_files", 9657, "COPY_MANIFEST.sha256 line count"),
        ("host_manifest_files", 13453, "HOST_MANIFEST.sha256 line count"),
    ):
        rows.append({"key": key, "value": value, "source": src})

    st = json.load(open(static_path))
    for run, t in st["runs"].items():
        for k in ("official", "tau_1.0", "observed_only"):
            rows.append({"key": f"static:{k}:{run}", "value": t[k]["object_f1"], "source": f"static_three_way.json:runs/{run}/{k}/object_f1"})
        for k in ("total", "kept_by_unanimity"):
            rows.append({"key": f"static:predicted_nodes_{k}:{run}", "value": t["predicted_nodes"][k],
                         "source": f"static_three_way.json:runs/{run}/predicted_nodes/{k}"})

    with open(out_csv, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["key", "value", "source"])
        for row in rows:
            w.writerow(row)
    print(f"appended {len(rows)} rows to {out_csv}")


if __name__ == "__main__":
    main()
