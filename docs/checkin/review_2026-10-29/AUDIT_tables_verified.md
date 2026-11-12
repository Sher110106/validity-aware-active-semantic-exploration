# Verifier result

verdict: holds_with_corrections

## checks
- [ok] Table 1 point values (same top-1, median move, overlap, rho, move minus floor) for every arm, the ALL row and the official per-scene rows | Wrote my own code (/tmp/cvp_review/audit/verify_tables/v_replay.py) that reads replay2_results.jsonl on the same set: 394 stages in 23 runs, without e1_00871_s43_placebo_60m and without n_cand==0 rows. Compared the results with replay_table.json A_set_394.*.point | Every point value matches to 3 decimals, e.g. official move_plc 2.284, floor 2.192, diff +0.092, rho_plc 0.601, rho_floor 0.732 [verified]
- [ok] Stage-bootstrap 95% CIs (stages resampled within run, 2,000 draws) | Ran my own bootstrap with a different seed (v_replay.json → ci_within_run). Read the bootstrap code in replay_table.py: run sizes are fixed, resampling is with replacement, and it reports 2.5/97.5 percentiles of each median and of each difference of medians | Official diff CI is [-0.27, +0.39] in mine and [-0.25, +0.38] in theirs. The other CIs agree to within Monte Carlo error [verified]
- [ok] Replay inputs: the top1_dist, floor and overlap fields in replay2_results.jsonl are correct | v_stage_rescore.py re-scored 8 random stages (one per arm and scene) from the saved condition files with the fastig scorer. The calculator workdir pointed to my audit dir and bytecode writing was off. For each stage I recomputed top-1 under actual/obs/plc_a/plc_b/orc on the 300 fixed candidates | All 8 stages match: obs, plc_a, plc_b and orc moves, the plc_a-vs-plc_b floor and the plc_a top-10 overlap (v_stage_rescore.json) [verified]. This uses A's fastig scorer, not the pinned loop. 383/394 top-10 lists reproduce the logs
- [ok] Decision rule (task wording): CI of the official LLM-vs-placebo move minus the floor is [-0.25, +0.38], so 'content enters stops as noise' | Recomputed the CI and checked the per-scene, E1-counted and top-10-matched rows in replay_table.json | The CI contains 0, so the verdict follows. The sensitivity rows (E1-counted -0.04 [-0.32,+0.31], matched-only +0.01 [-0.26,+0.39], per scene) also contain 0 [verified]
- [ok] Under the plan's literal wording ('wholly below the floor') the verdict is the same, and that wording looks reversed | Read SYNTHESIS line 104 and REVIEW_A line 169. Compared the LLM-vs-placebo CI [2.04, 2.59] with the floor 2.19 | The verdict is the same under both wordings [verified]. Calling the direction reversed is a fair inference: a move below the floor would mean the LLM picks central spots, not that content matters [inferred]
- [NOT OK] 'rank rho 0.60 [0.57,0.62] vs 0.73 [0.71,0.76], and top-10 overlap 0.24 vs 0.29, with CIs that do not overlap' | replay_table.json A_set_394.official.ci95.ovl_plc / ovl_floor / rho_floor | The rho CIs do not overlap. The overlap CIs do: [0.21, 0.27] vs [0.26, 0.32]. Also, the rho_floor upper bound is 0.755, which rounds to 0.75, not 0.76 [verified]
- [NOT OK] Minor CI rounding in Table 1a | Compared the table text with the full-precision values in replay_table.json | Five CI ends are 0.01 off from double rounding of the 3-decimal log: official no-guesses upper bound 2.70 (written 2.71); official floor overlap upper bound 0.32 (0.33); official floor rho upper bound 0.75 (0.76); placebo-arm no-guesses diff lower bound -0.03 (-0.04); ALL oracle-pool lower bound 2.41 (2.42) [verified]
- [ok] 18% (A) vs 31% (B) reconciled exactly: 71/394 vs 112/364; the cause is the list ranked within and the target pose, not the denominator | v_rank.py re-runs B's reach.py logic (best_filtered_poses, final_pose[0], last allclose match, needs a next executed path) and A's logic (path_log target in best_sample_poses) on the raw pose_log and path_log files | B set: 364 stages, all 364 matched, 112 rank-1 = 30.8%. A logic on A set: 71/394 = 18.0%. Every stage matches under both rules, so the denominators are equal. Shares of 25.9% (top-1 removed by history) and 16.0% (ties) confirmed in rank_reconcile.json [verified]
- [NOT OK] 1b rank histogram is 'on A's run set of 394 stages', the same set as Table 1 | Compared stage sets in decisions.json and replay2_results.jsonl run by run | These are two different sets of 394 stages. decisions.json covers 24 runs and includes 1 stage of the excluded e1_00871_s43_placebo_60m (so placebo has 110). It lacks e2_00871_s43_filter_only stage 15, which has no path_log (so filter_only has 105). The replay set has placebo 109 and filter_only 106. Dropping the 0 m run's stage gives 71/393 = 18.1%, so nothing material changes [verified]
- [NOT OK] '18% = the final stop is the first-stage best' | Read decisions.py and rank_reconcile.py: A's rank uses the published target (last point of path_log), not where the robot stopped | The 18% is the share of stages whose published target is the first-stage best. B found many targets unreachable, so the robot often stops elsewhere. The wording needs to change [verified from code]
- [ok] E3: the recomputed pooled live gap and drawn/undrawn counts equal every gate file; ceilings and shares in both conventions | v_e3.py reimplements oracle_eligible from the live_policy constants (REACH 5.0 m, NEW 0.5 m, structure same-label rule, room anchors) and the gate's stage rule (k+1 path and k+1 observed graph), with key matching at 3-decimal rounding and _label normalisation. It computes live, exact random-drawn, max-drawn (mean over ties) and best spot, pooled and unit mean. I also read stage_diagnostics.py to confirm the gate's alignment: stage k pairs with stages/(k+1)/executed_path.json | All five runs match e3_ceiling_exact.json to full precision, e.g. 00871 s42 pooled live 0.035848, n 890/2515, max-drawn 0.1088, share 0.329. 00853 retry unit-mean share 0.041 [verified]
- [ok] Exact sets give 0-2 fewer units than A's pool, probably because of the stage k+1 observed-graph rule [inferred] | v_e3.py with the k+1 observed-graph requirement removed | Without that rule the unit counts are 26/34/32/24/30, which are A's counts exactly. The cause is confirmed [verified]
- [NOT OK] Max-drawn and best-spot ceilings change by at most 0.003 | Compared e3_ceiling_exact.json unit_mean with work_A/e3_ceiling.json | The largest change is 0.0034 (00853 first attempt, best spot 0.2234 vs 0.220). 'At most about 0.004' is correct. The conclusion does not change [verified]
- [NOT OK] 'On 00853, the live gaps (0.027-0.035) are at or below what standing on a random drawn object gives (0.032-0.049 pooled)' | e3_ceiling_exact.json mixed.live vs mixed.random_drawn | This is true for the retry (0.027 vs 0.049) and s43 (0.031 vs 0.039). It is false for the first attempt, where live is above random-drawn: 0.035 vs 0.032 pooled, 0.031 vs 0.026 unit mean [verified]
- [NOT OK] A3 rule: pooled shares 0.19-0.37, 'no run's CI sits near 0', so 'broken' is not supported | e3_ceiling_exact.json live_share_* and live_share_ci95_*. Also read the plan's '0.1-0.3', which matches A's unit-mean shares | The verdict 'broken not supported' holds in both conventions. But two pooled CIs reach 0 (retry [0.01, 0.38], s43 [-0.04, 0.41]). Under the unit-mean convention, which the plan's 0.1-0.3 refers to, the 00853 verdict run's share is 0.04 [-0.18, 0.23]: a point estimate near 0 with a CI too wide to call it either way. The headline leaves this out [verified numbers; inferred reading]
- [ok] Table 3 frontier recall at exhaustion and recall/F1 at 60 m, arm-by-scene recall/F1 at 60 m (E1/E2 only) | v_headroom.py uses np.interp on hm3d_stages af_recall/af_f1 vs path_m (holding end values) for 8 runs, including both short runs, and for the frontier file. It asserts that scores_e1_e2.json has no e3 rows | All values match headroom_table.json, e.g. frontier 00853 final 0.261 / F1 0.364 at 95.7 m, at 60 m 0.194/0.286; e2_00871_s43 0.054 held at 54.9 m. No e3 F1 or AUC was read or computed [verified]. The files have no point 'recall at 60 m' key, only hm3d_auc_af_recall_to_60m (an AUC), so interpolating the stage curve is a fair reading
- [ok] Mapping base rates and stage_diagnostics scanned shares per arm and scene | v_headroom.py recomputes pooled mapped_k1 weighted by n_near, the run range, and the mean of scanned_share_of_new_hypotheses on counted E1/E2 runs | All six rows match (e.g. official 853 11.0% [9.9, 12.3], filter_only 871 5.6% [4.3, 6.6]) [verified]. The scanned-share column is a mean over runs of each run's per-stage mean, not a mean over stages
- [NOT OK] Base rates 'equal gates/base_rates_pre_E3.json for the 11 E1 runs that file holds' | Listed the runs in base_rates_pre_E3.json and read the matches_pre_E3_file flags in headroom_table.json | The file holds 9 rows: 8 E1 runs and dryrun_oracle_00871_s42_10m. All 8 E1 runs match. 'Eleven' is wrong [verified]
- [NOT OK] Chosen-view scanned shares and A's '52/60/62/44%' = 0.517/0.597/0.617/0.438 (cited to headroom_table_log.txt) | Recomputed from work_A/chosen_view.json (mean vis_scanned_share over stages k>0, A's 24-run set). Searched headroom_table_log.txt and headroom_table.json | The values are right: 0.5169/0.5972/0.6172/0.4384, and 0.438 is the oracle arm. They are not in headroom_table_log.txt, which prints all-stage means 0.485/0.558/0.582. The source citation is wrong. E1/E2 view shares 0.50/0.60/0.62 and all-guess shares 0.65/0.67/0.72 match [verified]
- [NOT OK] Caveat: the within-run stage bootstrap ignores between-run variance, so the CIs are likely too narrow | Ran a run-level cluster bootstrap in v_replay.py (ci_cluster_runs) | For the key official diff, the cluster CI is [-0.22, +0.36], no wider than the within-run CI. The caveat is unsupported for this cell, though a 7-run cluster bootstrap is itself weak [verified numbers; inferred reading]
- [ok] Rules respected: no money, no SSH, no Habitat, no e3 F1/AUC, writes only in audit/tables | Read all four scripts. Checked timestamps on tools/live_policy/__pycache__ and work_A/__pycache__ (last writes at 16:00 and 16:13, before the tables run at 16:53-16:58) | No violations found. e3_ceiling_exact.py turns off bytecode writing before importing live_policy [verified]

## corrections
- Table 1 note: only the rank-rho CIs are disjoint (official 0.60 [0.57, 0.62] vs floor 0.73 [0.71, 0.75]). The top-10 overlap CIs overlap: 0.24 [0.21, 0.27] vs 0.29 [0.26, 0.32].
- Table 1a rounding: official no-guesses CI is [1.88, 2.70]; official floor overlap CI upper bound is 0.32; floor rho CI is [0.71, 0.75]; placebo-arm no-guesses minus floor is +0.78 [-0.03, +1.38]; ALL oracle-pool CI is [2.41, 2.97].
- 1b uses decisions.json's 394 stages, which is not the replay set. It covers 24 runs: it includes 1 stage of the excluded 0 m run e1_00871_s43_placebo_60m (placebo 110) and lacks e2_00871_s43_filter_only stage 15 (filter_only 105). Without the 0 m run's stage the share is 71/393 = 18.1%.
- 1c: 18% is the share of stages whose published target (path_log) is the first-stage best. It is not where the robot stopped.
- Table 2: the unit-count gap with A (0-2 units) is verified, not inferred. Removing the stage k+1 observed-graph rule restores A's counts of 26/34/32/24/30.
- Table 2: ceilings change by at most about 0.004, not 0.003 (00853 first attempt best spot: 0.2234 vs 0.220).
- Table 2: 'On 00853 live is at or below random-drawn' holds for the retry and s43 only. The first attempt is above (0.035 vs 0.032 pooled; 0.031 vs 0.026 unit mean).
- A3 outcome: two pooled CIs reach 0 (retry lower bound 0.01, s43 lower bound -0.04). Under the unit-mean convention, which the plan's 0.1-0.3 refers to, the 00853 verdict run's share is 0.04 [-0.18, 0.23]. 'Broken' is still not supported, because the CI is too wide, but the headline 'no run has a CI near 0' should go.
- Table 3: base_rates_pre_E3.json holds 8 E1 runs plus one dry run, not 11 E1 runs. All 8 match.
- Table 3: A's 0.517/0.597/0.617/0.438 (0.438 is the oracle arm) are right but are not in headroom_table_log.txt. Cite /tmp/cvp_review/audit/verify_tables/v_headroom.py and chosen_view.json instead (recomputed by the verifier).
- Table 3 column label: the stage_diagnostics scanned share is a mean over runs of each run's per-stage mean.
- Caveats: a run-level cluster bootstrap gives the official diff CI [-0.22, +0.36], no wider than the within-run CI, so 'CIs likely too narrow' is unsupported for this cell. Add one caveat: the 300 fixed candidates are drawn near the first-listed actual file's objects, so each swap is scored on a candidate set picked using the actual content [inferred from fastig.first_stage].

## corrected results
## Answer in brief
- **Decision-rule verdict: "content enters stops as noise".** In the official arm, the LLM-vs-placebo median top-1 move minus the noise floor is +0.09 m, 95% CI [-0.25, +0.38]. The CI includes 0. [V: replay_table.json → A_set_394.official.point/ci95.diff_move_plc_minus_floor; the verifier reproduced it with its own bootstrap as [-0.27, +0.39]]
- **18% vs 31% reconciled exactly, but not by denominator.** Every stage's target matches a logged top-10 pose, so both denominators are equal. The gap comes from which list each reviewer ranked in (full top-10 vs history-filtered) and which pose each took as the target (see 1c). [V]
- **Exact eligible sets change nothing that matters.** Ceilings move by at most about 0.004. Pooled, the live gap is 19-37% of the max-drawn ceiling. Under A's unit-mean convention the 00853 verdict run's share is 0.04 [-0.18, 0.23], and two pooled CIs reach 0. The data cannot call the loop broken, and they cannot rule out a near-zero pull on 00853. [V numbers, I reading]

All files are in `/tmp/cvp_review/audit/tables/`; the verifier's checks are in `/tmp/cvp_review/audit/verify_tables/`. V = verified, I = inferred.

---
## 1. Decision-replay table
Source: `work_A/replay2_results.jsonl`, 394 stages in 23 runs (summarize_replay.py's set, without e1_00871_s43_placebo_60m). Output: `replay_table.json` → `A_set_394.<arm>.point|ci95.<stat>`.
- same = mean `fixed.<c>.top1_same`;
- move = median `fixed.<c>.top1_dist`;
- overlap = mean `top10_overlap`;
- rho = median `rho_total`;
- floor = `fixed_plc_a_vs_b`;
- the placebo swap pools draws a and b.

Top-10 lists reproduce in 383/394 stages: official 119/121, placebo 109/109, filter_only 97/106, oracle 58/58 [V]. The verifier re-scored 8 random stages (2 per arm, both scenes) and every Table 1 field matched [V: verify_tables/v_stage_rescore.json].

### 1a. Swaps against the noise floor (median move in m, stage-bootstrap 95% CI)
| Arm (stages, runs) | Swap | Same top-1 | Median top-1 move [CI] | Move - floor [CI] | Top-10 overlap | Rank rho |
|---|---|---|---|---|---|---|
| **official (121, 7)** | no guesses | 8.3% | 2.29 [1.88, 2.70] | +0.10 [-0.39, +0.51] | 0.19 | 0.51 |
| | **placebo (LLM vs placebo)** | 7.9% | **2.28 [2.04, 2.59]** | **+0.09 [-0.25, +0.38]** | 0.24 [0.21, 0.27] | 0.60 [0.57, 0.62] |
| | oracle-pool draw | 2.5% | 2.87 [2.28, 3.21] | +0.68 [+0.01, +1.06] | 0.19 | 0.52 |
| | **floor (plc vs plc)** | 10.7% | **2.19 [1.90, 2.51]** | - | 0.29 [0.26, 0.32] | 0.73 [0.71, 0.75] |
| placebo (109, 6) | no guesses | 8.3% | 2.85 [2.25, 3.38] | +0.78 [-0.03, +1.38] | 0.21 | 0.61 |
| | placebo | 11.0% | 2.31 [2.01, 2.68] | +0.24 [-0.22, +0.62] | 0.31 | 0.70 |
| | oracle-pool | 7.3% | 3.45 [2.51, 3.96] | +1.39 [+0.35, +1.86] | 0.18 | 0.47 |
| | floor | 10.1% | 2.07 [1.74, 2.47] | - | 0.32 | 0.74 |
| filter_only (106, 6) | no guesses | 3.8% | 2.54 [2.23, 2.78] | -0.34 [-0.84, +0.54] | 0.25 | 0.61 |
| | placebo | 5.2% | 2.90 [2.59, 3.35] | +0.03 [-0.33, +0.90] | 0.21 | 0.61 |
| | oracle-pool | 7.5% | 2.50 [2.05, 3.11] | -0.38 [-1.00, +0.58] | 0.22 | 0.57 |
| | floor | 4.7% | 2.88 [2.06, 3.22] | - | 0.28 | 0.70 |
| oracle_visible (58, 4) | no guesses | 13.8% | 3.29 [2.46, 3.78] | +0.92 [+0.06, +1.93] | 0.15 | 0.49 |
| | placebo | 6.9% | 3.21 [2.70, 3.75] | +0.85 [+0.21, +1.84] | 0.20 | 0.52 |
| | oracle-pool | 22.4% | 1.86 [1.33, 2.63] | -0.51 [-1.31, +0.74] | 0.47 | 0.86 |
| | floor | 13.8% | 2.36 [1.55, 2.75] | - | 0.35 | 0.79 |
| ALL (394, 23) | no guesses | 7.9% | 2.62 [2.34, 2.80] | +0.31 [-0.01, +0.60] | 0.21 | 0.57 |
| | placebo | 7.9% | 2.58 [2.40, 2.74] | +0.27 [+0.07, +0.53] | 0.24 | 0.63 |
| | oracle-pool | 8.1% | 2.69 [2.41, 2.97] | +0.38 [+0.04, +0.76] | 0.23 | 0.57 |
| | floor | 9.4% | 2.31 [2.07, 2.48] | - | 0.31 | 0.73 |

All rows [V]. CIs for the unbracketed cells are in replay_table.json `ci95`.

### Official-arm LLM-vs-placebo contrast in detail [V: replay_table.json]
- Draw a alone: 2.42 [2.09, 2.88]. Draw b alone: 2.09 [1.81, 2.47]. This is A's "2.1-2.4 m".
- By scene:
  - 00853 (67 stages): 2.13 [1.84, 2.62] vs floor 2.02 [1.77, 2.33]; difference +0.10 [-0.22, +0.60].
  - 00871 (54 stages): 2.36 [2.07, 2.77] vs floor 2.49 [1.98, 2.85]; difference -0.13 [-0.45, +0.27].
- Sensitivity checks:
  - E1-counted runs only (92 stages): -0.04 [-0.32, +0.31].
  - Stages whose top-10 reproduced (119): +0.01 [-0.26, +0.39].
  - Median of paired per-stage differences: -0.06 [-0.32, +0.44].
  - Run-level cluster bootstrap (verifier, v_replay.json): +0.09 [-0.22, +0.36].

### Decision rule
The CI of the LLM-vs-placebo move minus the floor is [-0.25, +0.38]. It does not lie wholly above 0, so: **"content enters stops as noise"** [V]. The same verdict holds per scene and in every sensitivity check.

The plan's wording ("CI wholly **below** the floor → content-sensitive") gives the same verdict, because the CI [2.04, 2.59] contains the floor (2.19) [V]. That wording looks reversed: a move below the floor would mean the LLM picks central spots, not that content matters [I].

### Beside the rule [V numbers, I reading]
- **The score field shifts but the stop does not.** LLM content changes the rank order of the whole field more than a placebo redraw does: rho 0.60 [0.57, 0.62] vs 0.73 [0.71, 0.75], with disjoint CIs. Top-10 overlap is lower too (0.24 vs 0.29), but those CIs overlap ([0.21, 0.27] vs [0.26, 0.32]). Content does not move the top-1 more. Part of the rho gap may come from structure, such as dropped members and file order, rather than content [I].
- **The ALL-arms placebo difference (+0.27 [+0.07, +0.53]) is not an LLM effect.** It comes mainly from the oracle arm (+0.85 [+0.21, +1.84]) [I].
- **Candidate-set caveat.** The 300 fixed candidates are drawn near the first-listed actual file's objects, so each swap is scored on a set picked using the actual content [I, from fastig.first_stage].

### 1b. Rank of the chosen target within the first-stage top-10
Source: `work_A/decisions.json` `rank`. This is a different set of 394 stages from Table 1. It covers 24 runs:
- it includes 1 stage of the excluded 0 m run e1_00871_s43_placebo_60m, so placebo has 110;
- it lacks e2_00871_s43_filter_only stage 15, which has no path_log, so filter_only has 105.

Without the 0 m run's stage, the share is 71/393 = 18.1% [V].

| Arm | All stages | Target matches a logged top-10 pose | Rank histogram 0..9 | Top-1 share |
|---|---|---|---|---|
| official | 121 | 121 | [13,16,11,16,8,15,11,7,10,14] | 10.7% |
| placebo | 110 | 110 | [20,19,11,10,7,6,8,11,10,8] | 18.2% |
| filter_only | 105 | 105 | [26,13,15,11,9,9,5,4,10,3] | 24.8% |
| oracle_visible | 58 | 58 | [12,5,4,10,5,3,5,6,2,6] | 20.7% |
| ALL | 394 | 394 | [71,53,41,47,29,33,29,28,32,31] | **18.0% (71/394) under both denominators** |

### 1c. Exact reconciliation of 18% (A) and 31% (B) [V: rank_reconcile.json; verifier re-ran B's reach.py logic, v_rank.json]
| Ranked within | Target pose from | A's set (394) | B's set (364; 21 runs) |
|---|---|---|---|
| unfiltered `best_sample_poses` | path_log published target (**A**) | **71/394 = 18.0%** | 66/364 = 18.1% |
| unfiltered | `final_pose[0]` | 84/394 = 21.3% | 77/364 = 21.2% |
| history-filtered `best_filtered_poses` | path_log | 104/394 = 26.4% | 94/364 = 25.8% |
| history-filtered | `final_pose[0]` (**B**) | 125/394 = 31.7% | **112/364 = 30.8%** |

What drives the difference:
1. **List ranked within.** B ranks in the history-filtered list, and in 25.9% of stages that filter has already removed the first-stage best.
2. **Target pose.** B takes `final_pose[0]`. In the 16.0% of stages with ties, that is not always the pose that was published.
3. **Run set.** This has almost no effect.

The synthesis's "both right for their denominators" is wrong about the cause [V]. A more accurate reading:
- 18% = "the published target is the first-stage best". This is the target, not where the robot stopped.
- 31% = "the first-listed tied pose is the best survivor of the history filter".

A uniform pick over the filtered list would give 14.6% [V].

---
## 2. E3 ceiling table (post hoc, exact eligible sets)
Sources:
- `gates/E3_gate_*.json`;
- `e3_ceiling_exact.json`;
- A's pool values from `work_A/e3_ceiling.json`.

The verifier reimplemented the eligible-set rule and the ceilings, and every value matched [V: verify_tables/v_e3.json]. The recomputed pooled live gap and the drawn/undrawn counts equal every gate file.

### Pooled convention (the gate's)
| Oracle run | Stages | Live gap (gate) | p (one-sided) | Random drawn (expectation) | Max-drawn | Best spot | **Live / max-drawn [95% CI]** | Base rate k+1 |
|---|---|---|---|---|---|---|---|---|
| 00871 s42 (verdict) | 12 | 0.036 | 0.039 | 0.028 | 0.109 | 0.181 | **0.33 [0.09, 0.58]** | 5.4% |
| 00871 s43 | 11 | 0.050 | 0.067 | 0.037 | 0.134 | 0.206 | **0.37 [0.11, 0.59]** | 8.4% |
| 00853 s42 first attempt | 14 | 0.035 | 0.065 | 0.032 | 0.151 | 0.216 | **0.23 [0.11, 0.36]** | 12.9% |
| 00853 s42 retry (verdict) | 16 | 0.027 | 0.37 | 0.049 | 0.143 | 0.219 | **0.19 [0.01, 0.38]** | 13.2% |
| 00853 s43 | 16 | 0.031 | 0.22 | 0.039 | 0.159 | 0.224 | **0.20 [-0.04, 0.41]** | 13.6% |

### Unit-mean convention (A's), exact sets vs A's pool approximation
| Run | Units exact / A | Live | Random drawn (expectation; single draw) | Max-drawn | Best spot | Live/max-drawn [CI] | A pool: random / max / best / live |
|---|---|---|---|---|---|---|---|
| 00871 s42 | 24 / 26 | 0.029 | 0.021; 0.008 | 0.099 | 0.180 | 0.29 [-0.07, 0.59] | 0.045 / 0.100 / 0.179 / 0.026 |
| 00871 s43 | 22 / 24 | 0.035 | 0.021; 0.009 | 0.127 | 0.200 | 0.27 [0.04, 0.49] | 0.019 / 0.125 / 0.198 / 0.030 |
| 00853 s42 first | 28 / 30 | 0.031 | 0.026; 0.023 | 0.155 | 0.223 | 0.20 [0.06, 0.33] | 0.058 / 0.154 / 0.220 / 0.024 |
| 00853 s42 retry | 32 / 34 | 0.005 | 0.031; 0.030 | 0.120 | 0.214 | **0.04 [-0.18, 0.23]** | 0.015 / 0.119 / 0.213 / 0.005 |
| 00853 s43 | 32 / 32 | 0.014 | 0.025; 0.027 | 0.145 | 0.219 | 0.10 [-0.13, 0.34] | 0.034 / 0.145 / 0.219 / 0.014 |

### What changes with the exact sets
- **[V] Ceilings:** max-drawn and best-spot change by at most about 0.004 per run.
- **[V] Live gaps:** live unit-mean gaps change by at most 0.007.
- **[V] Random-drawn ceiling:** A's single-draw range (0.015-0.058) should be replaced by the exact expectation: 0.021-0.031 (unit mean) or 0.028-0.049 (pooled).
- **[V] Unit counts:** the exact sets have 0-2 fewer units because the gate needs a stage k+1 observed graph. Without that rule the counts are A's 26/34/32/24/30.
- **[V] Live gap vs random drawn:**
  - On the 00853 retry (0.027 vs 0.049) and s43 (0.031 vs 0.039), the live gap is below what standing on a random drawn object gives.
  - On the 00853 first attempt it is slightly above (0.035 vs 0.032).
  - On 00871 it is above (0.036 vs 0.028; 0.050 vs 0.037).
- **[V numbers / I reading] A3 rule:**
  - Pooled shares are 0.19-0.37, but the retry and s43 CIs reach 0 (0.01, -0.04).
  - Under the unit-mean convention, which the plan's "0.1-0.3" refers to, the 00853 verdict run is 0.04 [-0.18, 0.23].
  - No run shows a share that is near 0 with a CI narrow enough to say so. So "broken" is not supported, but a near-zero pull on 00853 cannot be ruled out.

---
## 3. Headroom table (E1/E2 runs and frontier only; no e3 data)
Value at 60 m = HM3D author-faithful curve (`hm3d_stages[].af_recall` / `af_f1` vs `path_m`), linearly interpolated and held at the last value for short runs [V: headroom_table.json; verifier spot-checked 8 runs and both frontier scenes]. The files hold only AUC keys (`hm3d_auc_af_recall_to_60m`), no point value at 60 m.

| Scene | Frontier recall at exhaustion (final stage) | Frontier recall / F1 at 60 m | Official recall / F1 at 60 m | Placebo recall / F1 at 60 m | Filter_only recall / F1 at 60 m |
|---|---|---|---|---|---|
| 00853 | **0.261** (95.7 m, stage 33); F1 0.364 | 0.194 / 0.286 | 0.175 / 0.272 (n=2: 0.172, 0.178†) | 0.151 / 0.238 (0.138, 0.166, 0.149) | 0.184 / 0.274 (0.164, 0.159, 0.228) |
| 00871 | **0.168** (120.2 m, stage 54); F1 0.242 | 0.140 / 0.209 | 0.122 / 0.190 (0.115, 0.127, 0.124) | 0.084 / 0.138 (0.108, 0.079, 0.065) | 0.085 / 0.138 (0.136, 0.054†, 0.064) |

- † These runs stopped short and are held at their last value: e1_00853_s43_official at 54.3 m and e2_00871_s43_filter_only at 54.9 m.
- [I] Arm recall at 60 m is 50-73% of the frontier's final recall. The frontier at 60 m is above every arm mean in both scenes.

| Arm, scene | Mapping base rate P(mapped at k+1 \| within 3.5 m), pooled [run range] | Scanned share of new guesses (stage_diagnostics; mean over runs of per-run stage means) | Guesses in chosen 4 m view in scanned ground (chosen_view, mean over stages k>0) | All guesses at the stage in scanned ground (k>0) |
|---|---|---|---|---|
| official 00853 | 11.0% [9.9, 12.3] | 0.64 | 0.53 | 0.64 |
| official 00871 | 5.7% [5.2, 6.3] | 0.65 | 0.48 | 0.66 |
| placebo 00853 | 10.2% [9.5, 11.1] | 0.67 | 0.53 | 0.66 |
| placebo 00871 | 6.8% [6.5, 7.2] | 0.65 | 0.67 | 0.68 |
| filter_only 00853 | 11.8% [10.9, 12.6] | 0.69 | 0.60 | 0.70 |
| filter_only 00871 | 5.6% [4.3, 6.6] | 0.73 | 0.63 | 0.73 |
| **Both scenes** | - | - | official 0.50, placebo 0.60, filter 0.62 | 0.65 / 0.67 / 0.72 |

- [V] Base rates: `stage_diagnostics.json[run].base_rate.mapped_k1`, pooled by `n_near`. They equal `gates/base_rates_pre_E3.json` for the **8** E1 runs that file holds; it also holds one dry run.
- [V] A's "52/60/62/44%" is the mean over stages k>0 on A's 24-run set: 0.517 / 0.597 / 0.617 / 0.438, where 0.438 is the oracle arm. The verifier recomputed these from `work_A/chosen_view.json`. They are not in headroom_table_log.txt, which prints all-stage means of 0.485/0.558/0.582.
- For context only (Table 2): the e3 base rates are 5.4-13.6% (gate files).