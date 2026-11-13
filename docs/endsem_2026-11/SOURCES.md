# Sources for the end-sem deck

Build: `.venv_offline/bin/python docs/endsem_2026-11/build_endsem_pptx.py` (from the project root). It reads the values below from the result files and `slots.json`, and writes `ASP_Endsem.pptx` with `ENDSEM_Script.md` as speaker notes. Render check: `soffice --headless --convert-to pdf ASP_Endsem.pptx`, then `pdftoppm -png`.

Short names:
- `NUM` = `tools/live_policy/results_2026-10-31/numbers.csv`
- `WRITEUP` = `tools/live_policy/results_2026-10-31/WRITEUP.md`
- `FH` = `tools/live_policy/results_2026-10-31/frontier_seeds/frontier_holm.json`
- `PC` = `tools/live_policy/results_paper_compare_1112/paper_compare.json`
- `CC` = `tools/live_policy/results_paper_compare_1112/c_checks.json`
- `NOTES` = `tools/live_policy/results_paper_compare_1112/NOTES.md`
- `PLAN` = `docs/ENDSEM_PLAN_2026-11-03.md`; `FINAL` = `docs/ENDSEM_FINAL_PLAN_2026-11-13.md`; `STATUS` = `docs/STATUS_2026-11-12.md`
- `PREREG` = `tools/live_policy/PREREGISTRATION_PAPER.md`

A number marked **TBD** has no source yet. Part 3 has not run. Its values live in `slots.json` and show as TBD until filled.

Slides 1 and 16 carry no result. Slide 1 repeats the names and the arXiv id of `docs/checkin_2026-11/build_checkin2_pptx.py`.

## Slide 2: ASP in one picture

| Number | Source |
|---|---|
| 8 guessed graphs | `docs/checkin_2026-11/figures/slices_numbers.json` `members` (8 members in a live stage); the paper's "at least 2 of 8 samples", `PLAN` §B1 (Room test row) |
| 0.2 per metre of travel; room gain weight 1.0 | `tools/decision_replay.py:173` (`MOVE_COST_LAMBDA=0.2`, `UNCERTAINTY_ROOM_WEIGHT=1.0`); `tools/decision_replay_reference/calculate_uncertainty.py:561,568`; `WRITEUP` §4 "The score" |
| Gain is zero if all 8 graphs agree | `calculate_uncertainty.py:521-538` (`_calculate_ig_components`) and `:554,558` (gain = H_y minus the mean within-graph entropy); `tools/live_policy/live_policy.py:19-22` |
| No term for truth or unknown space | `WRITEUP` §4 "The score" and §7 V7 |

## Slide 3: the live test

Axis ticks (0, ±0.05) are scale labels. Interval type: registered permutation interval.

| Number | Source |
|---|---|
| +0.013 (−0.012 to +0.040) | `NUM` `E1:hm3d:60m:statistic`, `:permutation_lo`, `:permutation_hi` |
| −0.003 (−0.047 to +0.037), filter vs LLM | `NUM` `E2:hm3d:60m:statistic`, `:permutation_lo/hi`, all three with the sign flipped: E2 is registered as official minus filter_only (+0.003, −0.037 to +0.047) |
| −0.012 (−0.053 to +0.029) | `FH` `official/d60` and `official/ci60` (−0.05296, +0.02854); `NUM` `frontier_seeds:official:d60`, `:ci60_lo/hi` hold the same values to 4 places |
| −0.025 (−0.050 to +0.002) | `FH` `placebo/d60` and `placebo/ci60`; `NUM` `frontier_seeds:placebo:*` (its `ci60_lo` is −0.0505 at 4 places; `WRITEUP` §12 prints −0.050) |
| +0.034, p 0.10, interval unbounded, home 871 only, 3 runs against 3 | `NUM` `E3:hm3d:60m:statistic`, `:p`; `WRITEUP` §3 E3 ("20 relabelings, smallest two-sided p 0.10"; "unbounded at this n") |
| 2 homes, seeds 42-44, 60 m, 95% | `WRITEUP` §2 |
| The LLM arm has 2 runs on 853 | `tools/live_policy/results_2026-10-31/run_table.md` (`e1_00853_s44_official` excluded); `WRITEUP` §2 cells table |
| "No detectable difference" | `WRITEUP` §3 "Registered reading" for E1, E2 and E3; `FINAL` §5 |

## Slide 4: why

Offline replay of saved stages, first-stage candidates (`review_2026-10-29/audit/tables/replay_table.json`, set `A_set_394`, arm official).

| Number | Source |
|---|---|
| 2.28 m and 2.19 m | `NUM` `replay:official:move_plc` (2.2838), `replay:official:move_floor` (2.1916) |
| +0.09 m (−0.25 to +0.38) | `NUM` `replay:official:diff_move_plc_minus_floor` (0.0922), `:ci_lo` (−0.247), `:ci_hi` (0.3799) |
| +0.68 m (+0.01 to +1.06) | `NUM` `replay:official:diff_move_oracle_minus_floor` (0.6774), `:ci_lo` (0.0122), `:ci_hi` (1.0559) |
| Not on 871 stages or counted runs alone (script) | `WRITEUP` §4 "The top-scored candidate"; `NUM` `replay:oracle_minus_floor:counted` (+0.54, −0.23 to +1.20) |
| 121 stages | `NUM` `replay:official:n_stages` |
| ρ 0.20, 0.19, −0.07, 0.44 | `NUM` `cf:rho_score_U360_median:official:actual` (0.1981), `:plc` (0.1884), `:obs` (−0.0713), `:orc` (0.442); `review_2026-10-29/audit/audit/cf_summary.json` |
| Exact objects high in part by construction | `WRITEUP` §4 notes under the ρ table |

## Slide 5: live test limits

| Number | Source |
|---|---|
| +0.040 and −0.012 | `NUM` `E1:hm3d:60m:permutation_hi`, `:permutation_lo` |
| 80% power for about 0.024 to 0.028 | `NUM` `E1:hm3d:60m:mde` (0.0244, normal approximation); 0.028 (t, 7 degrees of freedom) from `WRITEUP` §3 E1 "Registered reading" |
| 5 of 5 pairs; 10 of 16, 10 of 17, 13 of 15, 8 of 12, 16 of 19 stages | `NUM` `pacing_flag:stages_off:*` and `pacing_flag:stages_compared:*` (00853_s42, 00853_s43, 00871_s42, 00871_s43, 00871_s44); rule (more than 20% at three or more stages) in `WRITEUP` §3 "Pacing flag" |
| 29.4% v 4.4% within 1 m | `NUM` `agreement:same_label_1m:official` (0.2944), `agreement:same_label_1m:placebo` (0.0444) |
| +0.043, p 0.015, 0.09 | `NUM` `secondary:E1:f1point60:statistic` (0.0434), `:p` (0.015), `holm_E1_secondaries:f1point60` (0.09); six secondary tests: `WRITEUP` §3 |
| −0.011 at 30 m, p 0.58 | `NUM` `secondary:E1:f1point30:statistic` (−0.0106), `:p` (0.575) |
| 853 placebo led earlier, −0.052 at 30 m | `NUM` `secondary:E1:f1point30:per_scene_d:00853` (−0.0517); `WRITEUP` §3 "F1 at 30 m and 60 m" |

## Slide 6: same rules as the paper

| Number | Source |
|---|---|
| 85 and 66 stops | `CC` `00853.use_rule.reached`, `00871.use_rule.reached` |
| 5 of 5 on 853, 1 of 5 on 871 | `NOTES` "Command" and "Budgets"; `STATUS` §1 |
| DeepSeek; Gemini 2.5 Pro | `PLAN` §B1 table, LLM row |
| 10%, 50%, 100%; the paper gives no budget value | `PLAN` §B1 (Budget row); `PREREG` §1 |
| 632 s and 809 s | `PC` `meta.budgets` (632.175, 809.084), `meta.budget_sources`; rule in `PREREG` §4 and Amendment 2 A2.3 |
| 63, 316, 81, 405 s | Derived: 10% and 50% of the two budgets above, rounded to whole seconds |
| 612 to 868 s | `NOTES` "Budgets": the five end times 611.83 to 867.58 s |
| Registered fallback; reruns replace it with the median of valid runs | `PREREG` §4 and Amendment 2 A2.3 |

## Slide 7: the paper's table

Cells from `PC`. Our value shows only if at least half the runs reach that time (the rule of the check-in 2 deck). Every 871 value of ours is marked "to be updated" until `slots.json` `table871_updated` is true. The paper's own 871 numbers do not change, so they carry no mark.

| Slide 7 cell | Value | Key in `PC` (cells[] with reference apr, variant B) |
|---|---|---|
| 853 · Paper ASP | 34.4 / 60.8 / 66.7 | scene 00853, arm official, `paper_f1_x100` at fraction 10 / 50 / 100 |
| 853 · Paper frontier | 18.6 / 46.5 / 58.8 | scene 00853, arm frontier_end, `paper_f1_x100` at fraction 10 / 50 / 100 |
| 853 · Ours ASP | 16.5 (n 2/2) / 38.7 (n 2/2) / none (n 0/2) | scene 00853, arm official, `stage_value_x100.mean`, `.n`, `n_runs` at fraction 10 / 50 / 100 |
| 853 · Ours random guesses | 13.8 (n 3/3) / 43.9 (n 3/3) / none (n 0/3) | scene 00853, arm placebo, same keys |
| 853 · Ours frontier | 12.4 (n 5/5) / 39.5 (n 5/5) / 55.6 (n 3/5) | scene 00853, arm frontier_end, same keys |
| 871 · Paper ASP | 30.5 / 62.4 / 68.0 | scene 00871, arm official, `paper_f1_x100` |
| 871 · Paper frontier | 29.2 / 55.7 / 65.3 | scene 00871, arm frontier_end, `paper_f1_x100` |
| 871 · Ours ASP | 32.3 (n 3/3) / none (n 0/3) / none (n 0/3) | scene 00871, arm official, `stage_value_x100` |
| 871 · Ours random guesses | 27.2 (n 3/3) / none (n 1/3) / none (n 0/3) | scene 00871, arm placebo, `stage_value_x100` |
| 871 · Ours frontier | 26.4 (n 1/1) / 43.2 (n 1/1) / 62.8 (n 1/1) | scene 00871, arm frontier_end, `stage_value_x100` |

| Number | Source |
|---|---|
| Run counts in row labels: 2, 3, 5 runs on 853; 3, 3, 1 on 871 | `PC` `n_runs` of the cells above |
| Budget 632 s and 809 s in the table headers | `PC` `meta.budgets` |
| Paper ASP lead 15.8 and 14.3 points | Derived from the paper cells: 34.4 − 18.6 and 60.8 − 46.5 |
| Our ASP lead 4.1 and −0.8 points | Derived from the values as shown: 16.5 − 12.4 and 38.7 − 39.5 (unrounded: +4.05 and −0.87) |
| 2 ASP runs | `PC` 853 official `n_runs` |
| Row "ASP to the full budget on 853": TBD | `slots.json` `asp853_full_budget`; optional run, `FINAL` §6 |
| Fig. 4 (left) of arXiv 2510.05430v2 | `PC` `meta.paper_fig4_left`; `meta.paper_html_check` (no mismatches) |
| "ASP runs stop at 60 m" | `WRITEUP` §2; `NOTES` |

## Slide 8: limits of the comparison

| Number | Source |
|---|---|
| 32% and 21% | `CC` `00853.C3.apr_a_recall_vs_hm3d` (0.3222), `00871.C3.apr_a_recall_vs_hm3d` (0.2112) |
| 0.64 and 0.67 | `CC` `C5.apr_a_vs_frontier_made_f1_prec_rec[0]` (0.6387, 0.6701) |
| Repeat tour froze; being rerun | `CC` `C2.apr_b_final_identical_to_stage0`; `NOTES` item 2; `PREREG` Amendment 2 A2.4 and A2.5 |
| Rooms 13 and 14 against 6 and 9 | `CC` `C1.room_nodes`, `C1.paper_rooms` |
| Navmesh 77 and 59 m² against 208 and 235 | `CC` `C1.start_island_area_m2` (77.00, 59.27), `C1.paper_area_m2` (207.63, 235.03) |
| 45.6 v 39.5 (50%) and 15.3 v 12.4 (10%), 3 and 5 runs | `PC` apr B, scene 00853, arms `frontier_60m` (n_runs 3) and `frontier_end` (n_runs 5), `stage_value_x100.mean` |
| October batch, November batch | `WRITEUP` §12 (seeded frontier, 10-30); `PLAN` §B7 (e7 runs, 11-09 to 11-10) |
| ASP runs stop at 60 m; ran in October | `WRITEUP` §2; `PC` |
| Frontier's clock also counts its waits | `NOTES` "Frontier clock" (from the host's copy of the code; not checked against the released code) |

## Slide 9: the author's defense

| Number | Source |
|---|---|
| 44 saved inputs | `PLAN` §M0b item 4 (36 DeepSeek stages + 8 Gemini inputs) |
| Claude Haiku 5.5 and Claude Opus 5.5 | `FINAL` §3.2 M4 and §7 |
| "may contain more than one bedroom and more than one bathroom" | host `exploration/config/pipeline_config.yaml:101`, as quoted in `PLAN` §A item 3 and `docs/checkin_2026-11/SOURCES.md` (slide 4) |
| The author's claim, three questions, validity layer | `STATUS` §4; `FINAL` §3.2; `PLAN` §0 |
| DeepSeek exploratory if the replays do not run | `FINAL` §5 (last table row) |

## Slide 10: base rates and levels

| Number | Source |
|---|---|
| Quote from the prompt | as slide 9 |
| L1 to L4, 0.5 / 1 / 2 / 3 m, unobserved stratum, five typable types | `PLAN` §M0b items 1 and 2; §A item 4 |
| Base-rate shares and room mix: **TBD** | `slots.json` `base_rates`; to be re-derived under the frozen truth rule (see "Not used" below) |

## Slide 11: the paper's room test

| Number | Source |
|---|---|
| At least 2 of 8 samples, 2.5 m, same type | `PLAN` §B1 (Room test row) and §B3 P4 "The room rate" |
| 9 of 28 | `PLAN` §B1; `docs/checkin/review_2026-10-29/REVIEW_B_paper_field.md:117` (arXiv v2 §IV-A) |
| 8 members live, 4 in replays; 1 of 4 and 2 of 4 | `PLAN` §A item 21 |
| Hits and rooms for each arm, chance rate: **TBD** | `slots.json` `room_test` |

## Slide 12: three models

| Number | Source |
|---|---|
| 44 inputs; 2 Claude models × 3 levels; Holm p below 0.05 | `PLAN` §M0b item 4 and §4; `FINAL` §3.2 (family) |
| Lift, interval, verdict for 3 models × 3 levels: **TBD** | `slots.json` `models` |

## Slide 13: oracle factorial

| Number | Source |
|---|---|
| F0 identity, pick falls to the nearest candidate | `PLAN` §A item 6; `tools/live_policy/live_policy.py:19-22` (identical members: unexplored space scores zero) |
| F1, F-room, F3, F5 (two seeds), F6; member sets of 4 | `PLAN` §M2 table |
| Rule: (F3 − F5) at least 0.5 × (F1 − F5), interval by run; registered bias | `PLAN` §M2 "Rule"; `FINAL` §3.2 M2 |
| ρ per arm, share kept: **TBD** | `slots.json` `factorial` |

## Slide 14: the validity layer

| Number | Source |
|---|---|
| 30%, 2,573 of 8,465 | `NUM` `validator:removed_share:all` (0.304), `validator:removed_new:all`, `validator:raw_new:all`; `WRITEUP` §3 E2 "What the validator did" |
| 56 removed guesses were hits | `NUM` `validator:removed_hits_0.5:all` |
| 3.1% v 2.8% | `NUM` `validator:precision_kept_0.5:all` (0.0305), `validator:precision_raw_0.5:all` (0.0278); `WRITEUP` §3 E2 |
| No detectable difference to the live map | `WRITEUP` §3 E2 "Registered reading" |
| τ = 1, four readouts | `PLAN` §B4 (tau set 0.5, 0.75, 1.0; readouts 1 to 4). Readout 5 (decisions) needed H5, which `FINAL` §6 cuts |
| Per-model readouts: **TBD** | `slots.json` `validity` |

## Slide 15: limits

| Number | Source |
|---|---|
| 8.2%, about 1 in 12 | `NUM` `audit:yardstick_in_view_mapped:all` (0.082); `WRITEUP` §4 "Yield and the detector" |
| Count ignores unmapped walls | `WRITEUP` §4 and §8 |
| 12 run clusters; 44 inputs; five typable types | `PLAN` §M0b items 1 and 4; §4 |
| 4 members; no live Claude test | `PLAN` §A item 21; `FINAL` §6 (E6 cut) |
| Null at L1 reads Inconclusive | `FINAL` §5 |

## Slide 16: the answers

The four lines come from `PLAN` §1 (works, mixed, fails), `PLAN` §A item 2 (the fourth outcome and the Mixed rule) and `FINAL` §5 (what each outcome lets the talk claim). Edits: the live Claude run (E6) and the Sonnet clauses are gone; the Fails line has no M2 clause; no number appears. The rules: `PLAN` §4 "Verdicts" and "The author's semantic claim holds". The picked outcome goes in `slots.json` `outcome`.

## Not used on a slide, and why

- **Base rates 88%, 82%, 56%** (unseen bathroom, bedroom, kitchen): `PLAN` §11 slide 6 and §1 only. No result file holds them, and the plan says to re-derive them under the frozen rule. Left as TBD.
- **Room mix of the LLM's new rooms:** `PLAN` §A item 3 says 69% bedrooms and 21% bathrooms of 724 rooms; its Appendix R says 512 bedrooms and 167 bathrooms of 755 rooms. The two disagree and neither has a result file. Left as TBD.
- **Pilot room-test counts** (34/46, 17/38, 18/40, `PLAN` §M0b item 6): seen before the hash, so they stay off the slides.
- **"Frontier in 22-38 min against 2.1-5.7 h"** (`PLAN` §11 slide 3): no result file found. Not used.
