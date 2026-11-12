# Builder result

## method
Table 1 reads work_A/replay2_results.jsonl and uses the same stage set as summarize_replay.py: 394 stages in 23 runs, with e1_00871_s43_placebo_60m left out. Each swap is compared with the stage's actual hypothesis set on the same 300 candidates (key 'fixed'). The noise floor is placebo draw A vs placebo draw B (key 'fixed_plc_a_vs_b'). For the placebo swap, the two draws are pooled, giving 2 values per stage. For the CIs I resampled stages with replacement within each run (run sizes fixed, 2,000 draws, seed 20261029) and took the 2.5th and 97.5th percentiles of each median and of each difference of medians. The rank histogram comes from work_A/decisions.json. The 18% vs 31% reconciliation re-reads pose_log.json and path_log.json and applies both reviewers' definitions to both run sets. Table 2 recomputes the eligible sets with live_policy.oracle_eligible(observed graph, refs/oracle_sets.json objects), the same call and stage rule the gate uses. As a check, the pooled live gap and the drawn/undrawn row counts reproduce every gate file exactly. Each ceiling is computed per (stage, track) unit in two ways: as a mean over units (A's convention) and pooled over rows (the gate's convention). The live share of the max-drawn ceiling has a 95% CI from a stage bootstrap (2,000 draws). Table 3 reads E1/E2 rows only: frontier_60m_scores.json, scores_e1_e2.json (hm3d_stages, author-faithful af_recall/af_f1, linearly interpolated at 60 m and held at the last value for short runs, as in evaluator.area_under_curve), stage_diagnostics.json and base_rates_pre_E3.json for base rates, and work_A/chosen_view.json for the scanned share. No F1 or AUC was computed for any e3 run, nothing was spent, and nothing ran on a host. All files are in /tmp/cvp_review/audit/tables/.

## results
## Answer in brief
- **Decision-rule verdict: "content enters stops as noise".** In the official arm, the LLM-vs-placebo median top-1 move minus the noise floor is +0.09 m, 95% CI [−0.25, +0.38]. The CI includes 0. [verified: replay_table.json → A_set_394.official.point/ci95.diff_move_plc_minus_floor]
- **18% vs 31% reconciled exactly, but not by denominator.** Every one of the 394 stages has a target that matches a logged top-10 pose, so both denominators are equal. The gap comes from which list each reviewer ranked in (the full top-10 vs the history-filtered list) and which pose each took as the target (see 1c).
- **Exact eligible sets change nothing that matters.** The max-drawn and best-spot ceilings move by at most 0.003. The live gap is 19–37% of the max-drawn ceiling (pooled), and no run has a CI near 0.

All files are in `/tmp/cvp_review/audit/tables/`. V = verified (computed or read; file and key given). I = inferred.

---
## 1. Decision-replay table

Source: `work_A/replay2_results.jsonl`, 394 stages in 23 runs (summarize_replay.py's set). Output: `replay_table.json` → `A_set_394.<arm>.point|ci95.<stat>`.
- `same_*` = mean of `fixed.<c>.top1_same`.
- `move_*` = median of `fixed.<c>.top1_dist`.
- `ovl_*` = mean of `fixed.<c>.top10_overlap`.
- `rho_*` = median of `fixed.<c>.rho_total`.
- floor = `fixed_plc_a_vs_b`.
- The placebo swap pools draws a and b.

The top-10 lists reproduce in 383/394 stages (97.2%): official 119/121, placebo 109/109, filter_only 97/106, oracle 58/58 [V: `top10_match`].

### 1a. Swaps against the noise floor, by arm (median move in m with stage-bootstrap 95% CI)

| Arm (stages, runs) | Swap | Same top-1 | Median top-1 move [CI] | Move − floor [CI] | Top-10 overlap | Rank ρ |
|---|---|---|---|---|---|---|
| **official (121, 7)** | no guesses | 8.3% | 2.29 [1.88, 2.71] | +0.10 [−0.39, +0.51] | 0.19 | 0.51 |
| | **placebo (LLM vs placebo)** | 7.9% | **2.28 [2.04, 2.59]** | **+0.09 [−0.25, +0.38]** | 0.24 [0.21, 0.27] | 0.60 [0.57, 0.62] |
| | oracle-pool draw | 2.5% | 2.87 [2.28, 3.21] | +0.68 [+0.01, +1.06] | 0.19 | 0.52 |
| | **floor (plc vs plc)** | 10.7% | **2.19 [1.90, 2.51]** | — | 0.29 [0.26, 0.33] | 0.73 [0.71, 0.76] |
| placebo (109, 6) | no guesses | 8.3% | 2.85 [2.25, 3.38] | +0.79 [−0.04, +1.38] | 0.21 | 0.61 |
| | placebo | 11.0% | 2.31 [2.01, 2.68] | +0.24 [−0.22, +0.62] | 0.31 | 0.70 |
| | oracle-pool | 7.3% | 3.45 [2.51, 3.96] | +1.39 [+0.35, +1.86] | 0.18 | 0.47 |
| | floor | 10.1% | 2.07 [1.74, 2.47] | — | 0.32 | 0.74 |
| filter_only (106, 6) | no guesses | 3.8% | 2.54 [2.23, 2.78] | −0.34 [−0.84, +0.54] | 0.25 | 0.61 |
| | placebo | 5.2% | 2.90 [2.59, 3.35] | +0.03 [−0.33, +0.90] | 0.21 | 0.61 |
| | oracle-pool | 7.5% | 2.50 [2.05, 3.11] | −0.38 [−1.00, +0.58] | 0.22 | 0.57 |
| | floor | 4.7% | 2.88 [2.06, 3.22] | — | 0.29 | 0.70 |
| oracle_visible (58, 4) | no guesses | 13.8% | 3.29 [2.46, 3.78] | +0.92 [+0.06, +1.93] | 0.15 | 0.49 |
| | placebo | 6.9% | 3.21 [2.70, 3.75] | +0.85 [+0.21, +1.84] | 0.20 | 0.52 |
| | oracle-pool | 22.4% | 1.86 [1.33, 2.63] | −0.51 [−1.31, +0.74] | 0.47 | 0.86 |
| | floor | 13.8% | 2.36 [1.55, 2.75] | — | 0.35 | 0.79 |
| ALL (394, 23) | no guesses | 7.9% | 2.62 [2.34, 2.80] | +0.31 [−0.01, +0.60] | 0.21 | 0.57 |
| | placebo | 7.9% | 2.58 [2.40, 2.74] | +0.27 [+0.07, +0.53] | 0.24 | 0.63 |
| | oracle-pool | 8.1% | 2.69 [2.42, 2.97] | +0.38 [+0.04, +0.76] | 0.23 | 0.57 |
| | floor | 9.4% | 2.31 [2.07, 2.48] | — | 0.31 | 0.73 |

All rows are [V]. The table's own key, `rho_*`, is printed without CIs except in the official rows (same file, `ci95`).

### Official-arm LLM-vs-placebo contrast in detail [V: replay_table.json]
- Placebo draw a alone: 2.42 [2.09, 2.88]. Draw b alone: 2.09 [1.81, 2.47]. This is A's "2.1–2.4 m".
- By scene:
  - 00853 (67 stages): 2.13 [1.84, 2.62] vs floor 2.02 [1.77, 2.33]; difference +0.10 [−0.22, +0.60].
  - 00871 (54 stages): 2.36 [2.07, 2.77] vs floor 2.49 [1.98, 2.85]; difference −0.13 [−0.45, +0.27].
- Sensitivity checks:
  - Only the E1-counted runs (92 stages; both s44 official partial runs dropped): difference −0.04 [−0.32, +0.31] (`E1_counted_set.official`).
  - Only stages whose top-10 reproduced (119): +0.01 [−0.26, +0.39] (`official_top10_matched_only`).
  - Median of paired per-stage differences: −0.06 [−0.32, +0.44] (`paired_med_plc_minus_floor`).

### Decision rule (task wording)
The CI of the LLM-vs-placebo move minus the floor is [−0.25, +0.38]. It does not lie wholly above 0, so: **"content enters stops as noise"** [V]. The same verdict holds per scene and in every sensitivity check.

The plan text (SYNTHESIS §6 step 2, REVIEW_A A1) words the rule as "CI … wholly **below** the noise floor → content-sensitive". That direction looks reversed: content should make the LLM-vs-placebo move larger than the floor, not smaller [I]. Under the plan's literal wording the verdict is the same, since the LLM-vs-placebo median CI [2.04, 2.59] contains the floor (2.19) [V].

### Two points worth reporting beside the rule [V numbers, I reading]
- **The score field shifts but the stop does not.** In the official arm, LLM content changes the whole score field more than a placebo redraw does: rank ρ 0.60 [0.57, 0.62] vs 0.73 [0.71, 0.76], and top-10 overlap 0.24 vs 0.29, with CIs that do not overlap. It does not move the top-1 more. Part of the ρ gap may come from structure rather than content: dropped LLM members and file order differ between the live files and fresh placebo draws [I].
- **The ALL-arms placebo difference (+0.27 [+0.07, +0.53]) is not an LLM effect.** It comes from the oracle arm (+0.85 [+0.21, +1.84]) and, more weakly, the placebo arm. So the scorer does tell exact-object draws apart from placebo draws, but not LLM content apart from placebo [I].

### 1b. Rank of the chosen target within the first-stage top-10
Source: `work_A/decisions.json`, `rank` (0 = first-stage best), on A's run set of 394 stages. Reproduced in `rank_reconcile.json` → `decisions_json`.

| Arm | All stages | Stages whose target matches a logged top-10 pose | Rank histogram 0..9 | Top-1 share |
|---|---|---|---|---|
| official | 121 | 121 | [13,16,11,16,8,15,11,7,10,14] | 10.7% |
| placebo | 110 | 110 | [20,19,11,10,7,6,8,11,10,8] | 18.2% |
| filter_only | 105 | 105 | [26,13,15,11,9,9,5,4,10,3] | 24.8% |
| oracle_visible | 58 | 58 | [12,5,4,10,5,3,5,6,2,6] | 20.7% |
| ALL | 394 | 394 | [71,53,41,47,29,33,29,28,32,31] | **18.0% (71/394) under both denominators** |

[V] Both denominators are identical: every stage's target matches a logged top-10 pose exactly (`n_rank_matched` 394/394).

### 1c. Exact reconciliation of 18% (A) and 31% (B)
Source: `rank_reconcile.json`. B's run set has 21 runs and 364 stages: it leaves out both e1_00853_s44_official runs and e1_00871_s43_placebo_60m.

| Ranked within | Target pose taken from | A's set (394) | B's set (364) |
|---|---|---|---|
| unfiltered `best_sample_poses` | published target (path_log last point) = **A's definition** | **71/394 = 18.0%** | 66/364 = 18.1% |
| unfiltered | `final_pose[0]` | 84/394 = 21.3% | 77/364 = 21.2% |
| history-filtered `best_filtered_poses` | path_log | 104/394 = 26.4% | 94/364 = 25.8% |
| history-filtered | `final_pose[0]` = **B's definition** (work_B/reach.py) | 125/394 = 31.7% | **112/364 = 30.8%** |

[V] What drives the difference:
1. **List ranked within.** B ranks within the history-filtered list. In 25.9% of stages that filter has already removed the first-stage best (`share_top1_removed_by_history`).
2. **Target pose.** B takes `final_pose[0]`, which in the 16% of stages with ties is not always the pose the seeded RNG published.
3. **Run set.** This has almost no effect.

So the synthesis line "18% (all stages) vs 31% (stages matching the logged top 10) … both right for their denominators" is wrong about the cause [V]. A more accurate reading:
- 18% = "the final stop is the first-stage best".
- 31% = "the first-listed tied pose is the best survivor of the history filter".

A uniform pick over the filtered list would give 14.6% (mean of 1/n_filtered; mean list length 7.9) [V: `chance`].

---
## 2. E3 ceiling table (post hoc, exact eligible sets)
Sources:
- `gates/E3_gate_*.json`: `gate.all.approach.gap`, `.p_one_sided`, `base_rate.mapped_k1`;
- `e3_ceiling_exact.json` → `<run>.mixed.<strategy>.pooled|unit_mean` and `live_share_of_max_drawn_*`, `live_share_ci95_*`;
- A's pool values from `work_A/e3_ceiling.json`.

**Check [V]:** with `refs/oracle_sets.json`, my recomputed pooled live gap and the drawn/undrawn row counts equal every gate file exactly (`recomputed_live_gap_all_rows`, `recomputed_n_drawn`/`_undrawn`). For example, 00871 s42: 0.035848, 890/2515. Every stage-track unit had both drawn and undrawn objects.

### Pooled convention (comparable to the gate gap)

| Oracle run | Stages | Live approach gap (gate) | p (one-sided) | Random drawn object (exact expectation) | Max-drawn spot | Best spot | **Live / max-drawn [95% CI]** | Mapping base rate k+1 |
|---|---|---|---|---|---|---|---|---|
| 00871 s42 (verdict) | 12 | 0.036 | 0.039 | 0.028 | 0.109 | 0.181 | **0.33 [0.09, 0.58]** | 5.4% |
| 00871 s43 | 11 | 0.050 | 0.067 | 0.037 | 0.134 | 0.206 | **0.37 [0.11, 0.59]** | 8.4% |
| 00853 s42 first attempt | 14 | 0.035 | 0.065 | 0.032 | 0.151 | 0.216 | **0.23 [0.11, 0.36]** | 12.9% |
| 00853 s42 retry (verdict) | 16 | 0.027 | 0.37 | 0.049 | 0.143 | 0.219 | **0.19 [0.01, 0.38]** | 13.2% |
| 00853 s43 | 16 | 0.031 | 0.22 | 0.039 | 0.159 | 0.224 | **0.20 [−0.04, 0.41]** | 13.6% |

### Unit-mean convention (A's), exact sets vs A's pool approximation

| Run | Units exact / A | Live | Random drawn (expectation; single draw) | Max-drawn | Best spot | Live/max-drawn [CI] | A pool: random / max / best / live |
|---|---|---|---|---|---|---|---|
| 00871 s42 | 24 / 26 | 0.029 | 0.021; 0.008 | 0.099 | 0.180 | 0.29 [−0.07, 0.59] | 0.045 / 0.100 / 0.179 / 0.026 |
| 00871 s43 | 22 / 24 | 0.035 | 0.021; 0.009 | 0.127 | 0.200 | 0.27 [0.04, 0.49] | 0.019 / 0.125 / 0.198 / 0.030 |
| 00853 s42 first | 28 / 30 | 0.031 | 0.026; 0.023 | 0.155 | 0.223 | 0.20 [0.06, 0.33] | 0.058 / 0.154 / 0.220 / 0.024 |
| 00853 s42 retry | 32 / 34 | 0.005 | 0.031; 0.030 | 0.120 | 0.214 | 0.04 [−0.18, 0.23] | 0.015 / 0.119 / 0.213 / 0.005 |
| 00853 s43 | 32 / 32 | 0.014 | 0.025; 0.027 | 0.145 | 0.219 | 0.10 [−0.13, 0.34] | 0.034 / 0.145 / 0.219 / 0.014 |

### What changes with the exact sets
- **[V] Ceilings:** the max-drawn and best-spot ceilings change by at most 0.003 per run.
- **[V] Live gaps:** live unit-mean gaps change by at most 0.007.
- **[V] Random-drawn ceiling:**
  - A's random-drawn range (0.015–0.058) came from one random object per unit, so it was noisy.
  - The exact expectation is 0.021–0.031 (unit mean) or 0.028–0.049 (pooled).
  - A's "0.015–0.058" should be replaced by these figures.
- **[I] Unit counts:** the exact sets give 0–2 fewer units per run, most likely because the gate also needs a stage k+1 observed graph.
- **[V/I] Conclusions that stand:**
  - On 00853, the live gaps (0.027–0.035) are at or below what standing on a random drawn object gives (0.032–0.049 pooled).
  - On 00871, the live gaps (0.036, 0.050) are above that level (0.028, 0.037).
  - On A3's rule ("call the loop broken only if the share is near 0 with a CI"), the pooled shares are 0.19–0.37 and no run's CI sits near 0. The 00853 retry and s43 lower bounds (0.01, −0.04) mean a near-zero pull on 00853 cannot be ruled out.

---
## 3. Headroom table (E1/E2 runs and frontier only; no e3 data)
Value at 60 m = HM3D author-faithful curve (`hm3d_stages[].af_recall` / `af_f1` vs `path_m`), linearly interpolated, from `headroom_table.json`. Only E1/E2-counted runs are included.

| Scene | Frontier recall at exhaustion (final stage) | Frontier recall / F1 at 60 m | Official recall / F1 at 60 m | Placebo recall / F1 at 60 m | Filter_only recall / F1 at 60 m |
|---|---|---|---|---|---|
| 00853 | **0.261** (95.7 m, stage 33); F1 0.364 | 0.194 / 0.286 | 0.175 / 0.272 (n=2: 0.172, 0.178†) | 0.151 / 0.238 (0.138, 0.166, 0.149) | 0.184 / 0.274 (0.164, 0.159, 0.228) |
| 00871 | **0.168** (120.2 m, stage 54); F1 0.242 | 0.140 / 0.209 | 0.122 / 0.190 (0.115, 0.127, 0.124) | 0.084 / 0.138 (0.108, 0.079, 0.065) | 0.085 / 0.138 (0.136, 0.054†, 0.064) |

- Sources [V]:
  - frontier: `frontier_60m_scores.json[scene].hm3d_stages` (last stage; interpolated at 60 m);
  - arms: `scores_e1_e2.json[run].hm3d_stages`;
  - per-run values: `headroom_table.json` → `runs`, `arm_scene`.
- † Two runs stopped short, so their value is the held last value: e1_00853_s43_official ended at 54.3 m and e2_00871_s43_filter_only at 54.9 m.
- [I] Arm recall at 60 m is 50–73% of the frontier's final recall. The frontier's final recall is itself only 0.17–0.26 of HM3D objects.

| Arm, scene | Mapping base rate P(mapped at k+1 \| within 3.5 m), pooled [run range] | Scanned share of new guesses (stage_diagnostics, mean of per-stage shares) | Guesses in the chosen 4 m view lying in scanned ground (chosen_view, mean over stages k>0) | All guesses at the stage in scanned ground (chosen_view, k>0) |
|---|---|---|---|---|
| official 00853 | 11.0% [9.9, 12.3] | 0.64 | 0.53 | 0.64 |
| official 00871 | 5.7% [5.2, 6.3] | 0.65 | 0.48 | 0.66 |
| placebo 00853 | 10.2% [9.5, 11.1] | 0.67 | 0.53 | 0.66 |
| placebo 00871 | 6.8% [6.5, 7.2] | 0.65 | 0.67 | 0.68 |
| filter_only 00853 | 11.8% [10.9, 12.6] | 0.69 | 0.60 | 0.70 |
| filter_only 00871 | 5.6% [4.3, 6.6] | 0.73 | 0.63 | 0.73 |
| **Both scenes (view share)** | — | — | official 0.50, placebo 0.60, filter 0.62 | 0.65 / 0.67 / 0.72 |

- Sources [V]:
  - base rates: `stage_diagnostics.json[run].base_rate.mapped_k1`, pooled by `n_near`; they equal `gates/base_rates_pre_E3.json` for the 11 E1 runs that file holds;
  - scanned share: `scanned_share_of_new_hypotheses`;
  - view shares: `chosen_view.json` `vis_scanned_share` / `all_scanned_share`.
- [V] A's "52/60/62/44%" is the mean over stages k>0 on A's full run set: 0.517 / 0.597 / 0.617 / 0.438 (`headroom_table_log.txt`; check in this session). On E1/E2-counted runs the official figure is 0.50.
- For context in Table 2 (not headroom): the e3 base rates are 5.4–13.6% (gate files).

## decision rules
- Step 2 rule (task wording): official-arm LLM-vs-placebo median top-1 move minus the placebo-placebo floor = +0.09 m, stage-bootstrap 95% CI [-0.25, +0.38]. It does not lie wholly above 0, so the verdict is 'content enters stops as noise' [verified: replay_table.json A_set_394.official.diff_move_plc_minus_floor]. The same verdict holds per scene (00853 +0.10 [-0.22,+0.60]; 00871 -0.13 [-0.45,+0.27]), on E1-counted runs only (-0.04 [-0.32,+0.31]) and on top-10-matched stages only (+0.01 [-0.26,+0.39]).
- Under the plan's literal wording ('CI wholly below the noise floor -> content-sensitive') the verdict is also 'noise': the LLM-vs-placebo median CI [2.04, 2.59] contains the floor (2.19). That wording looks reversed in direction [inferred].
- A3 rule (E3): do not call the loop broken unless the live/max-drawn share is near 0 with a CI. Pooled shares are 0.19-0.37, and no run's CI sits near 0. The 00853 retry [0.01, 0.38] and s43 [-0.04, 0.41] lower bounds cannot exclude a near-zero pull, so 'broken' is not supported; the data only fail to rule out a weak pull on 00853 [verified numbers, inferred reading].
- 18% vs 31%: reconciled exactly (71/394 vs 112/364). The cause is the list ranked within (unfiltered vs history-filtered) and the target pose (published path_log target vs final_pose[0]), not the denominator, since all 394 stages match a logged top-10 pose [verified: rank_reconcile.json].

## caveats
- The stage bootstrap resamples stages within fixed runs, so it ignores between-run variance; the CIs are likely too narrow for claims about runs or arms [inferred].
- The noise floor uses one pair of placebo draws per stage (plc_a, plc_b), and the LLM-vs-placebo move pools both draws; with draw a alone the median is 2.42 m, with draw b alone 2.09 m [verified].
- The replay set (A's 394 stages) includes the two partial e1_00853_s44_official runs, which E1 drops; the sensitivity rows exclude them and the verdict holds [verified].
- 11 of 394 stages did not reproduce the logged top-10 (9 filter_only, 2 official); they are kept in the main rows [verified].
- Counterfactual swaps are scored on the first-stage score on fixed candidates. Reachability and the second-stage re-rank are not replayed for swaps, because the nvblox grid is not saved [verified from replay2.py].
- E3 ceilings use a 0.5 m grid over the eligible objects' bounding box plus 1 m, with no reachability or wall check, so they are upper bounds. 'Random drawn object' is now the exact expectation over drawn objects; A's single-draw figure is shown beside it [verified].
- To call oracle_eligible, e3_ceiling_exact.py imports live_policy.py read-only from the project working tree (an uncommitted, modified file) with bytecode writing disabled. It reproduces the gate row counts exactly, so it matches the host code for this function [verified].
- 'Recall at exhaustion' is the frontier run's final stage. The 00871 run ended at 120.15 m, which may be a 120 m cap rather than true exhaustion; frontier_config.yaml does not settle this [inferred]. There is one frontier run per scene, with no seeds.
- Values at 60 m use linear interpolation of the stage curve; two counted runs ended short (54.3 m, 54.9 m) and are held at their last value [verified].
- The headroom table reads no e3 score rows (scores_e1_e2.json holds none; an assert checks this). The e3 base rates appear only in Table 2, taken from the gate files. No F1 or AUC was computed for any e3 run.