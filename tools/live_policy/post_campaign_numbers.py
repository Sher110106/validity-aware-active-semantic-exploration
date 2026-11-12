#!/usr/bin/env python3
"""Append numbers.csv rows for the post-campaign plan steps 6-8 (WRITEUP §12).

Run after build_results.py and extra_numbers.py, from tools/live_policy:
    python3 post_campaign_numbers.py results_2026-10-31
Sources are paths relative to the package folder, as in extra_numbers.py.
"""
import csv
import json
import os
import sys

BENCH = "../review_2026-10-29/bench/build/summary.json"
FRONTIER = "frontier_seeds/frontier_holm.json"
FRONTIER_SCORES = "frontier_seeds/frontier_seeds_scores.raw.json"
DETERMINISM = "determinism/determinism.json"


def get(pkg, rel, path):
    v = json.load(open(os.path.join(pkg, rel)))
    for p in path.split("/"):
        v = v[int(p)] if isinstance(v, list) else v[p]
    return v


def main():
    pkg = sys.argv[1]
    rows = []

    def add(key, rel, path, nd=4):
        v = get(pkg, rel, path)
        rows.append({"key": key, "value": round(v, nd) if isinstance(v, float) else v, "source": f"{rel}:{path}"})

    # Step 6: the decision table, the yardstick check and the regret scale.
    add("bench:go_live", BENCH, "decision/go_live")
    for r in ("R1", "R2", "R3", "R4"):
        add(f"bench:{r}:a_ratio", BENCH, f"decision/{r}/a/ratio", 3)
        add(f"bench:{r}:a_ratio_ci_lo", BENCH, f"decision/{r}/a/ratio_ci95/0", 3)
        add(f"bench:{r}:a_ratio_ci_hi", BENCH, f"decision/{r}/a/ratio_ci95/1", 3)
        add(f"bench:{r}:a_oracle_regret", BENCH, f"decision/{r}/a/oracle_mean", 2)
        add(f"bench:{r}:a_placebo_A_regret", BENCH, f"decision/{r}/a/placebo_A_mean", 2)
        add(f"bench:{r}:b_llm_minus_A", BENCH, f"decision/{r}/b/LLM_minus_A", 2)
        add(f"bench:{r}:b_ci_lo", BENCH, f"decision/{r}/b/LLM_minus_A_ci95/0", 2)
        add(f"bench:{r}:b_ci_hi", BENCH, f"decision/{r}/b/LLM_minus_A_ci95/1", 2)
        add(f"bench:{r}:b_floor", BENCH, f"decision/{r}/b/noise_floor_p2.5", 2)
    for y in ("Uwall", "U360"):
        add(f"bench:yardstick:{y}:share_in", BENCH, f"yardstick_check/{y}/share_in", 3)
        add(f"bench:yardstick:{y}:in_mapped", BENCH, f"yardstick_check/{y}/in_mapped")
        add(f"bench:yardstick:{y}:separation", BENCH, f"yardstick_check/{y}/separation_in_minus_out", 3)
        add(f"bench:yardstick:{y}:ratio", BENCH, f"yardstick_check/{y}/ratio_in_over_out", 1)
    add("bench:Uwall_max_mean", BENCH, "descriptors/Uwall_max_mean", 1)
    for gs in ("actual", "placebo_A"):
        add(f"bench:R1:official:{gs}_regret", BENCH, f"tables/Uwall/official/cells/R1/{gs}/mean", 2)
    best = min(get(pkg, BENCH, f"decision/{r}/a/ratio") for r in ("R1", "R2", "R3", "R4"))
    rows.append({"key": "bench:best_oracle_gain_over_placebo", "value": round(1 - best, 3),
                 "source": f"{BENCH}: 1 - min over R1-R4 of decision/<rule>/a/ratio"})
    add("bench:n_stages", BENCH, "n_used")

    # Step 7: the two registered contrasts and the per-run frontier AUCs.
    for c in ("official", "placebo"):
        for k in ("d60", "p60", "p60_holm", "d50", "p50"):
            add(f"frontier_seeds:{c}:{k}", FRONTIER, f"{c}/{k}")
        add(f"frontier_seeds:{c}:ci60_lo", FRONTIER, f"{c}/ci60/0")
        add(f"frontier_seeds:{c}:ci60_hi", FRONTIER, f"{c}/ci60/1")
    for i, r in enumerate(json.load(open(os.path.join(pkg, FRONTIER_SCORES)))):
        name = os.path.basename(r["run_dir"])
        add(f"auc_hm3d_60m:{name}", FRONTIER_SCORES, f"{i}/hm3d_auc_af_f1_to_60m")
        add(f"path_m:{name}", FRONTIER_SCORES, f"{i}/final_path_m", 1)
        rows.append({"key": f"n_stages:{name}", "value": len(r["stages"]), "source": f"{FRONTIER_SCORES}:{i}/stages (count)"})
    # Stage counts of the counted 00871 ASP runs, for the scans-per-metre caveat.
    for i, r in enumerate(json.load(open(os.path.join(pkg, "analysis/all_scores.json")))):
        name = os.path.basename(r["run_dir"])
        if name.startswith("e1_00871") and r.get("final_path_m", 0) >= 50:
            rows.append({"key": f"n_stages:{name}", "value": len(r["stages"]), "source": f"analysis/all_scores.json:{i}/stages (count)"})

    # Step 8: replicate agreement (written by determinism_check.py).
    if os.path.exists(os.path.join(pkg, DETERMINISM)):
        add("determinism:replicates_all_pairs_stage0_pass", DETERMINISM, "replicates/all_pairs_stage0_pass")
        add("determinism:baseline_all_pairs_stage0_pass", DETERMINISM, "baseline/all_pairs_stage0_pass")
        add("determinism:decision", DETERMINISM, "decision")
        for g in ("replicates", "baseline"):
            for i, d in enumerate(get(pkg, DETERMINISM, f"{g}/stage0_stop_distance_m")):
                if d is not None:
                    add(f"determinism:{g}:pair{i}:stage0_stop_distance_m", DETERMINISM, f"{g}/stage0_stop_distance_m/{i}", 2)

    # Added after the independent review (DEVIATIONS item 39).
    add("bench:yardstick:Uwall:out_mapped", BENCH, "yardstick_check/Uwall/out_mapped")
    y = get(pkg, BENCH, "yardstick_check/Uwall")
    rows.append({"key": "bench:yardstick:Uwall:recall_of_next_mapped", "value": round(y["in_mapped"] / (y["in_mapped"] + y["out_mapped"]), 2),
                 "source": f"{BENCH}: yardstick_check/Uwall in_mapped / (in_mapped + out_mapped)"})
    variants = get(pkg, BENCH, "sensitivity/decision")
    best_v = min(variants[v][r]["a_ratio"] for v in variants for r in ("R1", "R2", "R3", "R4"))
    rows.append({"key": "bench:best_oracle_gain_unregistered_variants", "value": round(1 - best_v, 3),
                 "source": f"{BENCH}: 1 - min over sensitivity/decision/<variant>/<rule>/a_ratio"})
    for v in ("own_footprint", "slice_1p1"):
        add(f"bench:sensitivity:{v}:R4_a_ratio", BENCH, f"sensitivity/decision/{v}/R4/a_ratio", 3)
    for c in ("official", "placebo"):
        add(f"frontier_seeds:{c}:mde60", FRONTIER, f"{c}/mde60", 3)
        for sc in ("00853", "00871"):
            add(f"frontier_seeds:{c}:per_scene60:{sc}", FRONTIER, f"{c}/per_scene60/{sc}/diff_of_means", 3)
    WALLS = "frontier_seeds/wall_cells.json"
    for g in ("frontier", "e1"):
        add(f"wall_cells:{g}:min_share", WALLS, f"{g}_range/0", 4)
        add(f"wall_cells:{g}:max_share", WALLS, f"{g}_range/1", 4)
    rows.append({"key": "spend:steps_6_8_usd", "value": 0,
                 "source": "e5_* config/run_manifest.txt max_cost_usd=0.0; frontier_baseline.py and the bench make no LLM calls"})

    # Settings quoted from the pre-registrations (document rows, as in extra_numbers.py).
    rows.append({"key": "bench:bar_oracle_gain_over_placebo", "value": 0.3,
                 "source": "PREREGISTRATION_BENCH.md: Decision rule (a), oracle regret at most 0.7 x placebo-A regret"})
    rows.append({"key": "determinism:quiet_wait_s", "value": 15,
                 "source": "PREREGISTRATION_DETERMINISM.md: Runs, ASP_DSG_QUIESCENT_S=15"})
    rows.append({"key": "determinism:min_replicates_if_fail", "value": 5,
                 "source": "PREREGISTRATION_DETERMINISM.md: Decision, otherwise plan at least 5 replicates per cell"})

    out_csv = os.path.join(pkg, "numbers.csv")
    existing = list(csv.DictReader(open(out_csv)))
    keys = {r["key"] for r in rows}
    kept = [r for r in existing if r["key"] not in keys]  # rerunning replaces, never duplicates
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["key", "value", "source"])
        w.writeheader()
        w.writerows(kept + rows)
    print(f"{len(rows)} post-campaign rows; numbers.csv now has {len(kept) + len(rows)} rows")


if __name__ == "__main__":
    main()
