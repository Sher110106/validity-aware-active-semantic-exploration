# Sources for the end-sem deck

Build, from the project root:
1. `.venv_offline/bin/python docs/endsem_2026-11/figures/make_stage_picture.py` (slide 13; draws the stage and writes `figures/stage_numbers.json`)
2. `.venv_offline/bin/python docs/endsem_2026-11/build_endsem_pptx.py`

The builder reads the values below from the result files and `slots.json`, and writes `ASP_Endsem.pptx` with `ENDSEM_Script.md` as speaker notes. Render check: `soffice --headless --convert-to pdf ASP_Endsem.pptx`, then `pdftoppm -png`. Type size: body 32 px and notes 24 px on a 1920 px canvas, which is 16 pt and 12 pt as projected.

Short names:
- `NUM` = `tools/live_policy/results_2026-10-31/numbers.csv`
- `WRITEUP` = `tools/live_policy/results_2026-10-31/WRITEUP.md`
- `FH` = `tools/live_policy/results_2026-10-31/frontier_seeds/frontier_holm.json`
- `PC` = `tools/live_policy/results_paper_compare_1113/paper_compare.json` (its 853 and 871 cells equal the 11-12 file's; `comparison_vs_1112.json`)
- `CC` = `tools/live_policy/results_paper_compare_1112/c_checks.json`
- `N12` = `tools/live_policy/results_paper_compare_1112/NOTES.md`; `N13` = `tools/live_policy/results_paper_compare_1113/NOTES.md`
- `PLAN` = `docs/ENDSEM_PLAN_2026-11-03.md`; `FINAL` = `docs/ENDSEM_FINAL_PLAN_2026-11-13.md`
- `PREREG` = `tools/live_policy/PREREGISTRATION_PAPER.md`; `SEM` = `tools/live_policy/PREREGISTRATION_SEMANTIC.md`; `M2` = `tools/live_policy/PREREGISTRATION_M2.md`

A number marked **TBD** has no source yet. Part 3 has not run. Its values live in `slots.json` and show as TBD until filled.

Slides 1 and 20 carry no result number. Slide 1 repeats the names and the arXiv id of `docs/checkin_2026-11/build_checkin2_pptx.py`.

## Slide 2: ASP in one picture

| Number | Source |
|---|---|
| 8 guessed graphs | `docs/checkin_2026-11/figures/slices_numbers.json` `members`; the paper's "at least 2 of 8 samples", `PLAN` §B1 (Room test row) |
| 0.2 per metre; room weight 1.0 | `tools/decision_replay.py:173`; `tools/decision_replay_reference/calculate_uncertainty.py:561,568`; `WRITEUP` §4 "The score" |
| Gain is zero if all 8 agree | `calculate_uncertainty.py:521-538` (`_calculate_ig_components`) and `:554,558`; `tools/live_policy/live_policy.py:19-22`; `M2` §7 (F0) |
| No term for truth or unknown space | `WRITEUP` §4 "The score" and §7 V7 |

## Slide 3: the live test

Axis ticks (0, ±0.05) are scale labels. Interval type: registered permutation interval.

| Number | Source |
|---|---|
| +0.013 (−0.012 to +0.040) | `NUM` `E1:hm3d:60m:statistic`, `:permutation_lo`, `:permutation_hi` |
| −0.003 (−0.047 to +0.037), filter vs LLM | `NUM` `E2:hm3d:60m:statistic`, `:permutation_lo/hi`, signs flipped: E2 is registered as official minus filter_only (+0.003, −0.037 to +0.047) |
| −0.012 (−0.053 to +0.029) | `FH` `official/d60`, `official/ci60`; `NUM` `frontier_seeds:official:*` (4 places) |
| −0.025 (−0.050 to +0.002) | `FH` `placebo/d60`, `placebo/ci60`; `NUM` `frontier_seeds:placebo:*` (its `ci60_lo` is −0.0505 at 4 places; `WRITEUP` §12 prints −0.050) |
| +0.034, p 0.10, no bounds, home 871, 3 runs against 3 | `NUM` `E3:hm3d:60m:statistic`, `:p`; `WRITEUP` §3 E3 ("20 relabelings, smallest two-sided p 0.10"; "unbounded at this n") |
| Exact objects stand on one house under deviation 26 | `WRITEUP` §1 (E3 paragraph) and §3 E3 "Scope"; `tools/live_policy/results_2026-10-31/DEVIATIONS.md` item 26 |
| Frontier stopped more often on 871; its paths almost never crossed wall cells | `WRITEUP` §12 step 7 ([X] Walls; [X] Stops: 41-46 stages against 12-28; 0.00-0.17% against 2.4-7.0% of path points) |
| 2 homes, seeds 42-44, 60 m, 95% | `WRITEUP` §2 |
| "No detectable difference" | `WRITEUP` §3 "Registered reading" for E1, E2, E3; `FINAL` §5 |

## Slide 4: why (exploratory)

Offline replay of saved stages (`review_2026-10-29/audit/tables/replay_table.json`, set `A_set_394`, arm official, first-stage candidates) and the counterfactual ρ audit (`review_2026-10-29/audit/audit/cf_summary.json`).

| Number | Source |
|---|---|
| 121 stages (the move panel) | `NUM` `replay:official:n_stages` |
| 119 stages (the ρ panel) | `NUM` `audit:n_stages:official`; `cf_summary.json` `by_arm.official.n`; `WRITEUP` §4 table row "official (119)" |
| 2.28 m and 2.19 m | `NUM` `replay:official:move_plc` (2.2838), `replay:official:move_floor` (2.1916) |
| +0.09 m (−0.25 to +0.38) | `NUM` `replay:official:diff_move_plc_minus_floor` (0.0922), `:ci_lo`, `:ci_hi` |
| +0.68 m (+0.01 to +1.06) | `NUM` `replay:official:diff_move_oracle_minus_floor` (0.6774), `:ci_lo`, `:ci_hi` |
| 853 stages +0.92 m (+0.34 to +1.47); 871 stages −0.00 m (−0.63 to +0.69) | `NUM` `replay:oracle_minus_floor:00853` (0.9152, 0.3412, 1.4669) and `:00871` (−0.0035, −0.6275, 0.6872); `WRITEUP` §4 "The top-scored candidate" |
| ρ 0.20, 0.19, −0.07, 0.44 | `NUM` `cf:rho_score_U360_median:official:actual` (0.1981), `:plc` (0.1884), `:obs` (−0.0713), `:orc` (0.442) |
| +0.07 over a random set, 73 of 119 stages | `NUM` `cf:paired_actual_minus_placebo_median:official` (0.0679); "73 of 119 stages, p 0.008" from `WRITEUP` §4 notes under the ρ table |
| Exact objects high in part by construction | `WRITEUP` §4 notes under the ρ table |

## Slide 5: where the guesses land

| Number | Source |
|---|---|
| 3.0% v 0.5%, 10.1% v 2.0%, 23.8% v 6.3% | `NUM` `precision_pooled:official:final:{0.5,1,2}m`, `precision_pooled:placebo:final:{0.5,1,2}m` (0.0304, 0.0052; 0.1007, 0.0203; 0.2383, 0.0628); `WRITEUP` §4 "Precision and agreement" |
| About 6 times | `WRITEUP` §3 "Precision" (3.0% against 0.5%, 6 times) |
| 97% miss by more than 0.5 m | Derived: 1 − 0.0304 |
| 853: 1.4% v 0.6%; 871: 4.2% v 0.4% | `NUM` `precision05:official:00853:final` (0.0139), `precision05:placebo:00853:final` (0.0062), `precision05:official:00871:final` (0.0416), `precision05:placebo:00871:final` (0.0040); `WRITEUP` §3 "Precision" |
| Counted runs, per (stage, member) guess | `WRITEUP` §8 "Counting" |

## Slide 6: live test limits

| Number | Source |
|---|---|
| +0.040 | `NUM` `E1:hm3d:60m:permutation_hi` |
| Gains of 0.024 to 0.028 or more | `NUM` `E1:hm3d:60m:mde` (0.0244, normal approximation); 0.028 (t, 7 degrees of freedom) from `WRITEUP` §3 E1 "Registered reading" |
| 5 of 5 pairs; 10 of 16, 10 of 17, 13 of 15, 8 of 12, 16 of 19 (script: "all five") | `NUM` `pacing_flag:stages_off:*`, `pacing_flag:stages_compared:*`; rule (more than 20% at three or more stages) in `WRITEUP` §3 "Pacing flag" |
| 29.4% v 4.4% | `NUM` `agreement:same_label_1m:official` (0.2944), `agreement:same_label_1m:placebo` (0.0444) |
| +0.043, p 0.015, 0.09 | `NUM` `secondary:E1:f1point60:statistic` (0.0434), `:p` (0.015), `holm_E1_secondaries:f1point60` (0.09) |
| −0.011 at 30 m | `NUM` `secondary:E1:f1point30:statistic` (−0.0106) |
| Filter live: −0.003 (−0.047 to +0.037) | as slide 3 |
| 30%, 2,573 of 8,465 | `NUM` `validator:removed_share:all` (0.304), `validator:removed_new:all`, `validator:raw_new:all` |
| 3.1% v 2.8% | `NUM` `validator:precision_kept_0.5:all` (0.0305), `validator:precision_raw_0.5:all` (0.0278); `WRITEUP` §3 E2 "What the validator did" |

## Slide 7: same rules as the paper

| Number | Source |
|---|---|
| 85 and 66 stops | `CC` `00853.use_rule.reached`, `00871.use_rule.reached` |
| Stand-in for his hand-driven tour: navmesh paths, same mapper | `PLAN` §B1 (Reference row), §B7 (Amendment 1: the tour moves onto navmesh paths); `PREREG` Amendment 1 |
| 5 of 5 on 853, 1 of 5 on 871 | `N13` item 2 and "Budgets" (5 and 1 valid runs); `N12` "Command" |
| DeepSeek; Gemini 2.5 Pro | `PLAN` §B1 table, LLM row |
| The paper gives no budget value; 10, 50, 100% | `PLAN` §B1 (Budget row); `PREREG` §1 |
| 632 s and 809 s | `PC` `meta.budgets` (632.175, 809.084), `meta.budget_sources`; rule in `PREREG` §4 and Amendment 2 A2.3; `N13` "Budgets" |
| 63, 316, 81, 405 s | Derived: 10% and 50% of the two budgets, whole seconds |
| 612 to 868 s | `N12` "Budgets": the five end times 611.83 to 867.58 s |
| Fallback, reruns replace it with a median | `PREREG` §4 and Amendment 2 A2.3 |

## Slides 8 and 9: the paper's table

Cells from `PC` (reference apr, variant B). Each cell shows `stage_value_x100` mean [min–max] and n (`.n`, or `.n of n_runs`); a time shows only if at least half the runs reach it. Every 871 cell of ours is marked "to be updated" until `slots.json` `table871_updated` is true. The paper's own 871 numbers do not change, so they carry no mark. Fig. 4 (left) of arXiv 2510.05430v2: `PC` `meta.paper_fig4_left`, `meta.paper_html_check` (no mismatches).

| Cell (10% / 50% / 100%) | Value | Key |
|---|---|---|
| 853 · Paper ASP | 34.4 / 60.8 / 66.7 | scene 00853, arm official, `paper_f1_x100` |
| 853 · Paper frontier | 18.6 / 46.5 / 58.8 | scene 00853, arm frontier_end, `paper_f1_x100` |
| 853 · Ours ASP | 16.5 [13.8–19.1] n=2 / 38.7 [37.2–40.1] n=2 / none (0 of 2) | scene 00853, arm official, `stage_value_x100` |
| 853 · Ours ASP + filter | 14.8 [12.1–18.4] n=3 / 48.3 [40.9–52.2] n=3 / none (0 of 3) | scene 00853, arm filter_only |
| 853 · Ours random guesses | 13.8 [10.8–16.1] n=3 / 43.9 [39.4–48.2] n=3 / none (0 of 3) | scene 00853, arm placebo |
| 853 · Ours frontier | 12.4 [10.8–14.7] n=5 / 39.5 [33.9–42.0] n=5 / 55.6 [53.5–59.6] n=3 of 5 | scene 00853, arm frontier_end |
| 871 · Paper ASP | 30.5 / 62.4 / 68.0 | scene 00871, arm official, `paper_f1_x100` |
| 871 · Paper frontier | 29.2 / 55.7 / 65.3 | scene 00871, arm frontier_end, `paper_f1_x100` |
| 871 · Ours ASP | 32.3 [30.5–35.6] n=3 / none (0 of 3) / none | scene 00871, arm official |
| 871 · Ours ASP + filter | 30.2 [28.6–32.3] n=3 / none (1 of 3) / none | scene 00871, arm filter_only |
| 871 · Ours random guesses | 27.2 [26.0–28.6] n=3 / none (1 of 3) / none | scene 00871, arm placebo |
| 871 · Ours frontier | 26.4 [26.4–26.4] n=1 / 43.2 [43.2–43.2] n=1 / 62.8 [62.8–62.8] n=1 | scene 00871, arm frontier_end |

| Number | Source |
|---|---|
| Budget 632 s and 809 s in the kickers | `PC` `meta.budgets` |
| Paper lead 15.8 and 14.3 points (script) | Derived from the paper cells: 34.4 − 18.6, 60.8 − 46.5 |
| Our lead 4.1 and −0.8 points (script) | Derived from the values as shown: 16.5 − 12.4, 38.7 − 39.5 |
| ASP stops at 60 m | `WRITEUP` §2 |
| "One row pending": ASP to the full budget on 853: **TBD** | `slots.json` `asp853_full_budget`; optional run, `FINAL` §6 |
| The wording "did not appear on 853 at 10% and 50%, with DeepSeek and a rebuilt reference" | `FINAL` §5 |
| 871: four frontier runs and the repeat tour being rerun | `N13` "Status of the two scenes"; `PREREG` Amendment 2 |

## Slide 10: the reference

| Number | Source |
|---|---|
| 32% and 21% | `CC` `00853.C3.apr_a_recall_vs_hm3d` (0.3222), `00871.C3.apr_a_recall_vs_hm3d` (0.2112) |
| Repeat tour on 853 not frozen; F1 0.751 (C2) | `N13` item 3 (`c2_20261113T191301.json`: `scenes.00853.f1` 0.7511, `frozen` false). The builder reads the newest `c2_*.json` and falls back to `N13`'s text while a rescore rewrites the folder |
| Below the 0.90 line; the reference moves by more than the paper's margins (2.7–7.9 points) | `PLAN` §B3 P2 check C2; `PREREG` Amendment 2 A2.5; `N13` item 3 |
| Nvblox died partway through both first tours; each reference lacks about its last 60 s | `N12` disclosures 3 and 4; `N13` "Carried over" |
| 871 repeat tour pending | `N13` item 3 and "Status of the two scenes" |
| Rooms 13 and 14, paper 6 and 9 | `CC` `C1.room_nodes`, `C1.paper_rooms` |
| Navmesh island 77 and 59 m² | `CC` `C1.start_island_area_m2` (77.00, 59.27); `N12` item 9 |
| Waypoint grid 191 and 149 m² | `CC` `C1.kept_area_estimate_m2` (191.25, 148.5); `N12` item 9 ("about 191 and 149") |
| Paper 208 and 235 m² | `CC` `C1.paper_area_m2` (207.63, 235.03) |
| "Partly explained": the grid reaches under furniture | `N12` item 9; `docs/STATUS_2026-11-12.md` §2 (navmesh leaves out floor under furniture) |

## Slide 11: the runs

| Number | Source |
|---|---|
| 45.6 [41.7–52.4] (50%) and 39.5 [33.9–42.0]; 15.3 [12.9–16.9] (10%) and 12.4 [10.8–14.7] | `PC` apr B, scene 00853, arm `frontier_60m` (3 runs, October) and `frontier_end` (5 runs, November), `stage_value_x100` mean, min, max |
| The ranges overlap | Read from the two ranges above (41.7–52.4 and 33.9–42.0; 12.9–16.9 and 10.8–14.7) |
| October, November | `WRITEUP` §12 (seeded frontier, 10-30); `PLAN` §B7 (e7 runs, 11-09 to 11-10) |
| ASP stops at 60 m; ran in October | `WRITEUP` §2; `PC` |
| Frontier's clock counts its waits | `N12` "Frontier clock" (host copy; not checked against the released code) |

## Slide 12: the defense

| Number | Source |
|---|---|
| 44 saved inputs | `SEM` §3 |
| Claude Haiku 5.5 and Opus 5.5 | `SEM` §4 |
| "Scene may contain more than one bedroom and more than one bathroom" | `SEM` §2 (the author's prompt), host `pipeline_config.yaml:101` |
| The claim, three questions, the validity layer, hash before scoring | `SEM` §1, §11, §14; `M2` §1; `FINAL` §3.2 |
| DeepSeek exploratory if the replays do not run | `SEM` §16 |

## Slide 13: one real stage

All from `figures/stage_numbers.json`, made by `figures/make_stage_picture.py` from the row's observed graph, the robot's path and `tools/live_policy/semantic/truth/00871_*`. No model output, no score.

| Number | Source |
|---|---|
| Run `e1_00871_s42_official_60m`, stage 8 | `semantic/sample_frame.txt` (round 1); `stage_numbers.json` `run`, `stage` |
| 47 object nodes, 12 room nodes | `stage_numbers.json` `observed_object_nodes`, `observed_room_nodes` |
| 16 regions: 7 seen, 1 partly seen, 8 unobserved | `stage_numbers.json` `regions`, `seen`, `partly_seen`, `unobserved`; rules `SEM` §5.4 |
| Open types bathroom and bedroom; 65 open classes | `stage_numbers.json` `open_types`, `open_classes`; rules `SEM` §5.5 |
| 0.5 m reach | `SEM` §5.1; `stage_numbers.json` `reach_m` |

## Slide 14: three levels

| Number | Source |
|---|---|
| L1, L2, L3 and what a hit needs; L4 secondary | `SEM` §1, §5.5, §8, §11 (L4) |
| 0.5, 1, 2, 3 m (L4) | `SEM` §11 |
| Base rates, bathroom, bedroom, kitchen: **TBD** | `slots.json` `base_rates`. The 88%, 82% and 56% in `SEM` §2 come from earlier, cruder rules, so they are not shown |

## Slide 15: controls

| Number | Source |
|---|---|
| 179 other annotated houses | `SEM` §9 (the other-house prior B3) |
| Placebo (B1), own-label swap (B5), region trade (D), prior's labels at the model's places (B3L) | `SEM` §9 table |
| Used at L1, L2 or L3 | `SEM` §9 table, last column |
| Wrong-house check: 6 pairs, a gate for L1 and L2, outside the family | `SEM` §9 (B4) and §10 "The wrong-house gate" |

## Slide 16: the paper's room test

| Number | Source |
|---|---|
| At least 2 of 8 members, 2.5 m, before the region is seen; with and without type | `SEM` §11 "The paper's room test" |
| The paper's 9 of 28 | `PLAN` §B1; `docs/checkin/review_2026-10-29/REVIEW_B_paper_field.md:117` (arXiv v2 §IV-A) |
| 8 members live, 4 in replays; 1 of 4 and 2 of 4 | `SEM` §11; `PLAN` §A item 21 |
| Hits and rooms, chance counts: **TBD** | `slots.json` `room_test` |

## Slide 17: three models

| Number | Source |
|---|---|
| 44 inputs; Opus, Haiku, DeepSeek | `SEM` §3, §4 |
| Named comparators (prior at L1 and L2, region trade at L3); margins 5, 5 and 3 points | `SEM` §10 "Verdict for a hypothesis" |
| Each p is the largest over comparators; 2 Claude models × 3 levels; Holm | `SEM` §10 |
| About 20 points (L1 detectable difference, plan) | `SEM` §10 "Detectable difference" |
| Lift, interval, verdict, detectable difference, wrong-house p, L1 decision: **TBD** | `slots.json` `models` |

## Slide 18: M2

| Number | Source |
|---|---|
| 384 stages, 24 runs | `M2` §3 (the bench's 384 stages, 24 runs) |
| F1, F5, F6, F3, F-room, F0 | `M2` §4 |
| Step 1 and step 2 of the reading rule; half the gap | `M2` §6 |
| F0: the gain is zero for identical members | `M2` §7 (F0); `tools/live_policy/live_policy.py:19-22` |
| Yardstick: wall-aware cone count; wild cluster bootstrap; every verdict provisional | `M2` §3 (Yardstick), §5, §7 |
| ρ per arm, F0 share: **TBD** | `slots.json` `factorial` |

## Slide 19: limits

| Number | Source |
|---|---|
| Two houses | `SEM` §16 |
| About 1 in 12 (8.2%) | `NUM` `audit:yardstick_in_view_mapped:all` (0.082); `WRITEUP` §4 "Yield and the detector" |
| Count ignores unmapped walls | `WRITEUP` §4 and §8 |
| 4 members; no live Claude test | `SEM` §3, §15 |
| Scorer written after DeepSeek's numbers were seen, frozen before Claude | `SEM` §2 (last paragraph), §14 |
| Every M2 verdict is provisional | `M2` §7 |
| The 8 Gemini rows have no wrong-house partner | `SEM` §9 (B4) |
| Plan expects L1 cannot decide at 44 inputs | `SEM` §10 "Detectable difference"; the freeze decides: `slots.json` `models.l1_cannot_decide` |

## Slide 20: the answers

| Number | Source |
|---|---|
| The four rules, in plain speech | `SEM` §10 "The thesis" table, word for word: holds (a Claude model Supported at L3), mixed, fails (every Claude model Rejected at L2 and L3; the L3 margin is over D, the region trade), inconclusive (anything else) |
| What each outcome lets the talk claim | `FINAL` §5 table; `SEM` §16 |
| Picked outcome | `slots.json` `outcome` |

## Backup slide: the validity layer

| Number | Source |
|---|---|
| Four readouts; tau 1 | `SEM` §11 "The validity layer" (readouts 1 to 4; votes 0.5, 0.75, 1.0). Readout 5 needed H5, cut: `SEM` §15 |
| Per-model values: **TBD** | `slots.json` `validity` |

## Not used on a slide, and why

- **Base rates 88%, 82%, 56%.** They sit in `SEM` §2 as seen before the hash, from earlier rules. The slide has a TBD slot for the frozen rule.
- **Room mix of the LLM's new rooms.** `PLAN` §A item 3 (69% and 21% of 724) and its Appendix R (512 and 167 of 755) disagree, and `SEM` §2 lists a recount of 1,353 room nodes. No result file holds a settled figure. Off the slides.
- **Pilot room-test counts** (34/46, 17/38, 18/40): seen before the hash. Off the slides.
- **"Frontier in 22-38 min against 2.1-5.7 h"** (`PLAN` §11 slide 3): no result file found. Off the slides.
