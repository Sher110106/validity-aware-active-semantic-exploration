# Sources for the end-sem deck

Build, from the project root:
0. `.venv_offline/bin/python docs/endsem_2026-11/fill_slots_part3.py` (writes the part 3 values of `slots.json` from the result files)
1. `.venv_offline/bin/python docs/endsem_2026-11/figures/make_stage_picture.py` (backup 12; draws the stage and writes `figures/stage_numbers.json`)
2. `.venv_offline/bin/python docs/endsem_2026-11/build_endsem_pptx.py`

The builder reads the values below from the result files and `slots.json`, and writes `ASP_Endsem.pptx` with `ENDSEM_Script.md` as speaker notes. Render check: `soffice --headless --convert-to pdf ASP_Endsem.pptx`, then `pdftoppm -png`. A PDF of the last build is in `render/ASP_Endsem.pdf`; rebuild it whenever the deck changes. Type size: body 32 px and notes 24 px on a 1920 px canvas, which is 16 pt and 12 pt as projected.

Short names:
- `NUM` = `tools/live_policy/results_2026-10-31/numbers.csv`
- `WRITEUP` = `tools/live_policy/results_2026-10-31/WRITEUP.md`
- `FH` = `tools/live_policy/results_2026-10-31/frontier_seeds/frontier_holm.json`
- `PC` = `tools/live_policy/results_paper_compare_1113/paper_compare.json` (final rescore of 18 Nov; its 853 cells equal the 11-12 file's, plus 27 new cells in the arm `official_nov` (the November ASP row, `N13` item 7); its 871 cells do not: 102 of 243 are the same, because B moved; `comparison_vs_1112.json`, `N13` items 7 and 8)
- `B13` = `tools/live_policy/results_paper_compare_1113/budgets_20261118T031340.json`; `C2F` = `tools/live_policy/results_paper_compare_1113/c2_20261118T031340.json` (both hold the same values as the 17 Nov files and the 18 Nov `T025414` ones). The builder reads the newest file of each name pattern.
- `RS` = `tools/live_policy/results_paper_compare_1113/rescore_summary.json` (key `nov`; the readings of one run are in `nov.alternatives`); `ALT_STOP` = `tools/live_policy/results_paper_compare_1113/alt_nov_e8_00853_s43_official_105m_stopped_after_stage_22/paper_compare.json`; `ALT_OUT` = `tools/live_policy/results_paper_compare_1113/alt_nov_without_e8_00853_s43_official_105m/paper_compare.json` (both folders are named in `RS` `nov.alternatives.rows[].folder`); `DEV` = `tools/live_policy/DEVIATIONS_NOVEMBER.md`
- `CC` = `tools/live_policy/results_paper_compare_1112/c_checks.json`
- `N12` = `tools/live_policy/results_paper_compare_1112/NOTES.md`; `N13` = `tools/live_policy/results_paper_compare_1113/NOTES.md`
- `PLAN` = `docs/ENDSEM_PLAN_2026-11-03.md`; `FINAL` = `docs/ENDSEM_FINAL_PLAN_2026-11-13.md`
- `PREREG` = `tools/live_policy/PREREGISTRATION_PAPER.md`; `SEM` = `tools/live_policy/PREREGISTRATION_SEMANTIC.md`; `M2` = `tools/live_policy/PREREGISTRATION_M2.md`

- `X19` = `tools/live_policy/results_semantic_1113/exploratory_1119/` (`ceiling.json`, `common_rows.json`, `room_test_runs.json`); `AT` = `tools/live_policy/results_m2_1113/exploratory_1119/all_true.json`; `EQ` = `tools/live_policy/results_paper_compare_1113/equal_path/equal_path.json`; `BS` = `tools/live_policy/results_paper_compare_1113/budget_sensitivity/budget_sensitivity.json`. All four are exploratory, made on 2026-11-19 after every result was seen (`DEV` items 66 and 71), and every slide that shows one says so. The builder stops if a file stops saying `registered: false`.
- `PIN` = `slots.json` `pinned`: facts read from files that are not result tables (the proposal's plan, the paper's quotes, the clock lines). Each row below names its file.
- `REVIEW` = `/Users/sher/project/cvp/REVIEW_FABLE_2026-11-19.md` (the independent review that led to this pass; outside the repo).

The main deck has 19 slides (the cover to the closing slide) and the backup has 17; every slide moved out of the main deck in pass 3 is still built, in builder order (`BACKUP_ORDER`). Slide numbers below are the deck's. No table or note on a main slide is below 12 pt as projected; titles are one size.

The two control arms on 853 (`PREREG` Amendment 5) have finished and the final rescore is filed: slide 8 and backup 18 show them (`controls_facts` guards every clause; `slots.json` `controls853` is read from `rescore_summary.json` `nov_controls`). Nothing is running and no Gemini run is left. `slots.json` `gemini_replay` is read from `gemini_1119/results.json` (slides 14 and 15; `gemini_facts` guards every sentence), `neon_replay` from `gemini_neon_1119/results.json` and `neon_minus_{flash,argon}.json` (backup 15; `neon_facts`), and the three models are side by side on slide 16. Gemini 4 Argon (`argon_replay`, `argon_r32`, with the all-36 exploratory files) is on backups 7 and 8 (`argon_facts`, `argon_check_facts`).

## Slide 1: the cover

| Statement | Source |
|---|---|
| "As the author put it to us": the claim that the guesses are often wrong in place but right in meaning, and that this is enough | Said in person to the student; no written record; the paper's nearest text is in section IV-B. The author's demo and the meeting with the student are the only sources. The paper (arXiv 2510.05430v2, section IV-B) calls a "semantically reasonable but physically infeasible bathroom" a failure that "causes the robot to revisit an uninformative region" (`PIN` `paper.bathroom`, `paper.revisit`; text as given for this pass, from the paper). `PLAN` line 325 records the remark's use, not its source; `REVIEW` finding 2 notes that the draft mail to the authors (outside the repo) says the point "names no place". The words are not in quotation marks on a slide |
| "Registered scores and tests are final, the Gemini runs and the two control arms on 853 included." | `DEV` items 66 to 76; `PREREG` Amendment 5; `PREREGISTRATION_GEMINI.md` Notes 1 to 7 |
| Part 1, short form: "With a small model: no detectable difference; a gain up to 0.04 F1 is not ruled out" | `NUM` `E1:hm3d:60m:permutation_hi` (0.04 to two places); no live interval is off 0 (slide 4's rows). Guard: `findings_facts` (sentence 1) |
| Part 2, short form: "On 853 ASP leads frontier by the clock, not clearly by distance. Over random guesses it is higher on average, not separated; over no guesses it reads above." | Slide 7: the three leads are positive (`facts853`); at 50 m and 100 m the equal-path sign is positive under the scripted reference and negative under human labels (`facts_equal853`). Slide 8: the random-guess arm's statement is "in between" (higher on average, not separated, under both references) and the no-guess arm's is "reads above" (`controls_facts`, `RSJ` `statements`). Guard: `findings_facts` (sentence 2) |
| Part 3, short form: "No model was found to beat a trade of regions; a prior from 179 other houses named objects better" | Slides 13 and 16 (L3 verdicts, none Supported; every L3 lower end against D below 0; every L2 upper end against the prior below 0); 179 houses `SEM` §9 (`PIN` `houses`). Guard: `findings_facts` (sentence 3) |

## Slide 2: what became of the proposal

| Number | Source |
|---|---|
| The question: whether validation and calibration of ensemble support can cut false-positive detours without cutting discovery of unseen rooms | `output/pdf/Validity_Aware_Active_Semantic_Exploration_Proposal.pdf`, "Research question" (page 1), as `PIN` `proposal.question`; restated in `docs/archive/IMPLEMENTATION_RESEARCH.md` |
| 5 policies, 4 homes × 3 seeds, 120 m | `docs/archive/IMPLEMENTATION_RESEARCH.md` §4.4 (policy list) and §4.5 ("4 scenes × seeds 42, 43, 44 = 12 runs"; "120 m path budget"); `PIN` `proposal.{policies,scenes,seeds,budget_m}`; `fill_slots_part3.py` asserts the §4.5 text |
| Our validator, live, in 2 homes: −0.003 F1 (−0.047 to +0.037), no detectable difference; the test saw only gains of 0.044 or more | `NUM` `E2:hm3d:60m:statistic` (+0.0034, sign flipped as on slide 4), `:permutation_lo/hi`, `E2:hm3d:60m:mde` (0.0440); `WRITEUP` §3 E2 (the "E2 line") |
| Detours not identifiable; collisions not instrumented | `docs/archive/PHASE13_DIAGNOSTICS_2026-09-17.md` lines 63, 73, 77; `docs/RESULTS.md` "Phase 13 disposition" |
| Calibration retired; its Brier score equals the base rate | `WRITEUP` §9 erratum 3; `docs/RESULTS.md` Errata item 4 |
| September's claim withdrawn: the filter kept 19 of 8,943 guesses; the gain came from deleting the guesses | `WRITEUP` §9 erratum 2; `NUM` `sept:unanimity_kept_of_predicted` ("19 of 8,943"), as `PIN` `proposal.{kept,of}` (read from the CSV by `fill_slots_part3.py`) |
| The question became whether the guesses carry any value | `WRITEUP` §1; `FINAL` §3.2 |

## Slide 3: ASP in one picture

| Number | Source |
|---|---|
| 8 guessed graphs, in two tracks of four | `docs/checkin_2026-11/figures/slices_numbers.json` `members`; the paper's "at least 2 of 8 samples", `PLAN` §B1 (Room test row); the two tracks: `REVIEW` finding 6 (equal graphs cancel, only the two tracks differ) and `tools/decision_replay_reference/calculate_uncertainty.py:269-333` |
| 0.2 per metre; room weight 1.0 | `tools/decision_replay.py:173`; `tools/decision_replay_reference/calculate_uncertainty.py:561,568`; `WRITEUP` §4 "The score" |
| If all 8 graphs agree, the gain is zero; the two tracks start from different observed maps, so it rarely is (in M2's all-true arm, where every member holds every true object, the gain is zero for every candidate in only 2 of 384 stages) | `calculate_uncertainty.py:521-538` (`_calculate_ig_components`) and `:554,558`; `tools/live_policy/live_policy.py:19-22`; `M2` §7 (F0); `M2S` `counts_all_stages.ig_zero_stage_share.F0` |
| No term for truth or unknown space | `WRITEUP` §4 "The score" and §7 V7 |

## Slide 4: the live test

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
| The live model is DeepSeek V4.1 Flash at low reasoning effort | `tools/live_policy/PREREGISTRATION_E1.md` line 9 ("deepseek/deepseek-v4.1-flash-1017 … reasoning effort low"); `WRITEUP` V13 |
| The paper (§IV, footnote on the model): "smaller, less expensive LLMs do not yet provide consistent enough performance to support a fully autonomous robot" | arXiv 2510.05430v2 §IV, footnote, read by the independent review on 2026-11-19 (`REVIEW` arc item 1 and finding 5); `PIN` `paper.small_model`. No file in the repo quotes it |

## Slide 5: why (exploratory)

The reading line says the LLM's guesses add a little ranking over random ones "(exploratory, offline; ranking, not map score)": the +0.07 and the 73 of 119 stages are a ranking of views in a replay (`NUM` `cf:paired_actual_minus_placebo_median:official`), not a map score; the live test (slide 4) found no detectable difference in the map.

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

## Slide 6: live test limits

| Number | Source |
|---|---|
| +0.040 | `NUM` `E1:hm3d:60m:permutation_hi` |
| Gains of 0.024 to 0.028 or more | `NUM` `E1:hm3d:60m:mde` (0.0244, normal approximation); 0.028 (t, 7 degrees of freedom) from `WRITEUP` §3 E1 "Registered reading" |
| 5 of 5 pairs; 10 of 16, 10 of 17, 13 of 15, 8 of 12, 16 of 19 (script: "all five") | `NUM` `pacing_flag:stages_off:*`, `pacing_flag:stages_compared:*`; rule (more than 20% at three or more stages) in `WRITEUP` §3 "Pacing flag" |
| 29.4% v 4.4% | `NUM` `agreement:same_label_1m:official` (0.2944), `agreement:same_label_1m:placebo` (0.0444) |
| +0.043, p 0.015, 0.09 | `NUM` `secondary:E1:f1point60:statistic` (0.0434), `:p` (0.015), `holm_E1_secondaries:f1point60` (0.09) |
| −0.011 at 30 m | `NUM` `secondary:E1:f1point30:statistic` (−0.0106) |
| Filter live: −0.003 (−0.047 to +0.037) | as slide 4 |
| 30%, 2,573 of 8,465 | `NUM` `validator:removed_share:all` (0.304), `validator:removed_new:all`, `validator:raw_new:all` |
| 3.1% v 2.8% | `NUM` `validator:precision_kept_0.5:all` (0.0305), `validator:precision_raw_0.5:all` (0.0278); `WRITEUP` §3 E2 "What the validator did" |
| Reading box: new objects land within 0.5 m of a real one 3.0% of the time, random guesses 0.5%; 97% miss by more than 0.5 m (moved here from the "where the guesses land" slide, now backup 9) | As backup 9: `NUM` `precision_pooled:official:final:0.5m` (0.0304) and `precision_pooled:placebo:final:0.5m` (0.0052); 97% = 1 − 0.0304, derived |

## Slides 7 and 9: the paper's table

Cells from `PC` (reference apr, variant B). Each cell shows `stage_value_x100` mean [min–max] and n (`.n`, or `.n of n_runs`); a time shows only if at least half the runs reach it. The 871 cells are final (`N13`: "00871: final"); the builder stops unless `slots.json` `table871_updated` is true. The paper's cells are one run each. Fig. 4 (left) of arXiv 2510.05430v2: `PC` `meta.paper_fig4_left`, `meta.paper_html_check` (no mismatches).

| Cell (10% / 50% / 100%) | Value | Key |
|---|---|---|
| 853 · Paper ASP | 34.4 / 60.8 / 66.7 | scene 00853, arm official, `paper_f1_x100` |
| 853 · Paper frontier | 18.6 / 46.5 / 58.8 | scene 00853, arm frontier_end, `paper_f1_x100` |
| 853 · Ours ASP, October (60 m) | 16.5 [13.8–19.1] n=2 / 38.7 [37.2–40.1] n=2 / none (0 of 2) | scene 00853, arm official, `stage_value_x100` |
| 853 · Ours ASP, November (105 m) | 17.2 [13.3–21.2] n=3 / 51.1 [45.7–61.5] n=3 / 61.6 [60.3–62.9] n=2 of 3 | scene 00853, arm official_nov (`PC`), `stage_value_x100`; runs `e8_00853_s42..44_official_105m` (`N13` "November ASP row"; `RS` `nov.runs`). Seed 44 ended at 604.0 s, short of B (632.18 s), so it has no 100% value |
| 853 · Ours ASP + filter | 14.8 [12.1–18.4] n=3 / 48.3 [40.9–52.2] n=3 / none (0 of 3) | scene 00853, arm filter_only |
| 853 · Ours random guesses | 13.8 [10.8–16.1] n=3 / 43.9 [39.4–48.2] n=3 / none (0 of 3) | scene 00853, arm placebo |
| 853 · Ours frontier | 12.4 [10.8–14.7] n=5 / 39.5 [33.9–42.0] n=5 / 55.6 [53.5–59.6] n=3 of 5 | scene 00853, arm frontier_end |
| 871 · Paper ASP | 30.5 / 62.4 / 68.0 | scene 00871, arm official, `paper_f1_x100` |
| 871 · Paper frontier | 29.2 / 55.7 / 65.3 | scene 00871, arm frontier_end, `paper_f1_x100` |
| 871 · Ours ASP | 33.9 [30.8–36.4] n=3 / none (0 of 3) / none (0 of 3) | scene 00871, arm official |
| 871 · Ours ASP + filter | 33.0 [29.9–37.6] n=3 / none (0 of 3) / none (0 of 3) | scene 00871, arm filter_only |
| 871 · Ours random guesses | 31.7 [30.2–32.6] n=3 / none (0 of 3) / none (0 of 3) | scene 00871, arm placebo |
| 871 · Ours frontier | 31.9 [27.8–37.4] n=5 / 59.2 [52.2–67.1] n=5 / 66.6 [64.4–68.3] n=3 of 5 | scene 00871, arm frontier_end |

| Number | Source |
|---|---|
| Budget 632 s and 1300 s in the kickers | `PC` `meta.budgets` |
| Slide 7 footnote: "Budget 632 s: the median end of our five frontier runs; the paper gives none" (the budget slide, "Same rules as the paper", is now backup 10) | `B13` `00853.primary_s` (632.175), `primary_rule` "median", `n_primary` 5; `PLAN` §B1 (Budget row); `PREREG` §4 and Amendment 2 A2.3. The builder reads the value from `PC` `meta.budgets` |
| Slide 7 footnote: "The paper's own 853 values moved between versions: at the full budget frontier 48.3 (v1) to 58.8 (v2), ASP 59.0 to 66.7" | `PIN` `paper_versions`, from `docs/checkin/review_2026-10-29/REVIEW_B_paper_field.md` line 130 ("00853 at 100% time, frontier 48.3 → 58.8, ASP 59.0 → 66.7"); the v2 numbers equal `PC` `paper_f1_x100` for 853 at 100% (58.8, 66.7). The builder takes the four numbers from the pinned slot, and the script and README needles check them |
| ASP + filter and random guesses (October) are not rows on slide 7 now; their cells (14.8 / 48.3 / none; 13.8 / 43.9 / none) are one line on backup 10 | The two rows below (scene 00853, arms filter_only, placebo) |
| Paper lead 15.8 and 14.3 points (script) | Derived from the paper cells: 34.4 − 18.6, 60.8 − 46.5 |
| Our lead 4.1 and −0.8 points (script) | Derived from the values as shown: 16.5 − 12.4, 38.7 − 39.5 |
| Slide 7 title: "By the clock ASP reads above frontier; by the metre the sign depends on the reference" | The first half: the November mean is above frontier's at 10%, 50% and 100% of the registered budget (the gaps below are positive; guard in `facts853`). The second half: at equal path, ASP is ahead under the scripted reference (apr) and behind under the human labels (hm3d), at 50 m and at 100 m (guard in `facts_equal853`; rows below). The cover says "ASP reads above frontier by the clock; by the metre, it depends" |
| Slide 7, exploratory block: ASP (November) and our frontier at 50 m and 100 m of path, scripted reference and human labels: 48.2 [43.4–55.6] n=3 and 47.4 [42.3–56.1] n=5; 62.5 [60.7–65.6] n=3 and 58.7 [57.7–59.7] n=2 of 5 (apr); 25.4 [23.7–28.1] n=3 and 27.3 [25.1–30.2] n=5; 32.5 [30.9–33.4] n=3 and 34.1 [33.5–34.8] n=2 of 5 (hm3d) | `EQ` `scenes.00853.tables.{apr,hm3d}.{official_nov,frontier_end}.{50,100}.{mean,min,max,n,n_runs}` (the last stage whose path is at most L metres; no value past a run's last stage). Not registered: `EQ` `registered` is false and `DEV` items 66 and 71 say so; the slide labels the block "Exploratory · equal path" |
| Script slide 7, README finding 3: at 50 m ASP is 0.8 ahead (apr) and 1.9 behind (hm3d); at 100 m 3.8 ahead and 1.6 behind | Derived from the printed means above (48.2 − 47.4; 25.4 − 27.3; 62.5 − 58.7; 32.5 − 34.1). `DEV` item 66 quotes the apr half as 0.7 to 3.8 at its lengths (unrounded 0.77 at 50 m); the deck subtracts printed values throughout |
| Slide 7 note: "The two control arms that share ASP's clock are on slide 8" (the control arms ran after every result above was filed; their reading is on slide 8) | `PREREG` Amendment 5; `DEV` item 68 |
| Body: at the full budget ASP reads 61.6 (n=2) and our frontier 55.6 (n=3); the paper has 66.7 and 58.8 | `PC` apr B, scene 00853, fraction 100: arm official_nov `stage_value_x100.mean` 61.62, `n` 2 (of `n_runs` 3); arm frontier_end 55.57, `n` 3 (of 5); `paper_f1_x100` 66.7 and 58.8 |
| Body: the gaps at 10%, 50% and 100% are 4.8, 11.6 and 6.0 points | Derived from the cells as printed (`PC` apr B, scene 00853, `stage_value_x100.mean`; the unrounded gaps are 4.78, 11.56, 6.05): official_nov 17.2, 51.1, 61.6 minus frontier_end 12.4, 39.5, 55.6 |
| Body: against the paper's 15.8, 14.3 and 7.9 | `paper_f1_x100`: 34.4 − 18.6, 60.8 − 46.5, 66.7 − 58.8 |
| "By less than in the paper" (cover, title area, README) | Shortfall = the paper's gap − ours: 15.8 − 4.8 = 11.0; 14.3 − 11.6 = 2.7; 7.9 − 6.0 = 1.9. The builder stops if a gap is not smaller, or (script and README) if 10% is not the largest shortfall |
| Note: October's two runs led by 4.1 at 10% and trailed by 0.8 at 50% | `PC` apr B, scene 00853, arm official (October; `n_runs` 2) against frontier_end, from the values as printed: 16.5 − 12.4, 38.7 − 39.5 (the "Our lead 4.1 and −0.8" row) |
| Note, slide 10, README, script: November's ASP logs 5.8 s per metre (n=3), our frontier 7.0 (n=5); at a given time ASP has gone farther | `PC` `seconds_per_metre`, scene 00853, arm official_nov: `sec_per_m.mean` 5.774, `sec_per_m.n` 3; arm frontier_end: 6.975, n 5; printed to one decimal as 5.8 and 7.0 (`paper_compare.md` "Seconds per metre": 5.77 and 6.98). The builder stops if ASP's value is not below frontier's. Frontier's clock also counts its waits for a path, ASP's does not: read from the authors' repository at f1ea141b on 2026-11-19 (see slide 10); first found in the host's copy (`N12` "Frontier clock") |
| Note: the two ASP batches differ by 12.4 points at 50% | 51.1 (official_nov) − 38.7 (official), `stage_value_x100.mean` at 50%. The ranges [45.7–61.5] and [37.2–40.1] do not overlap. 12.4 is at least the November lead at 50%, 11.6 (guard) |
| Note: at 100% the gap is 1.5 and −0.2 under the other two references (6.0 under apr) | `PC` cells with `reference` hm3d and frontier_made, `variant` B, scene 00853, fraction 100, `stage_value_x100.mean`: hm3d official_nov 34.4 − frontier_end 32.9 = 1.5; frontier_made 64.3 − 64.5 = −0.2 (unrounded −0.14; the deck subtracts printed values throughout). Both are below 6.0 (guard) |
| Note: by the rule's letter seed 43 loses its 100% value; that cell then reads 62.9, n=1 of 3 | `ALT_STOP`, reference apr, variant B, scene 00853, arm official_nov, fraction 100: `stage_value_x100.mean` 62.90, `n` 1, `n_runs` 3; `RS` `nov.alternatives.rows[kind=stopped]` (`run` e8_00853_s43_official_105m, `stage` 22, `end_s` 514.16, before B = 632.18). The rule: the Note to Amendment 3 (a run stopped by hand counts as ended before B) with A3.2 (such a run keeps the values it has); `DEV` item 64, paragraph added 11-18 03:14 |
| The stopped row keeps seed 43 at 10% and 50% | `ALT_STOP` 10%: 17.2 [13.3–21.2] n=3; 50%: 51.1 [45.7–61.5] n=3, equal to the as-run cells in `PC` (guard: the build stops if they differ) |
| README: with seed 43 left out altogether the row reads 19.1 / 53.6 / 62.9 (n=2, 2, 1), a further sensitivity | `ALT_OUT`, apr B, scene 00853, official_nov: 19.1 [17.1–21.2] n=2; 53.6 [45.7–61.5] n=2; 62.9 [62.9–62.9] n=1 of 2; `RS` `nov.alternatives.rows[kind=without]`; `DEV` item 64. Not quoted on a slide: leaving the run out raises the 10% and 50% means |
| 105 m; the three runs; never pooled with October's | `PREREG` Amendment 3 (A3.1 target path 105 m, A3.3 the row "ASP + DeepSeek, November", A3.4 not pooled); the run names end in `_105m`. 60 m: `WRITEUP` §2 |
| Slide 7 has no open row | `N13` "Status of the two scenes": both final; `RS` `nov.runs` (3 of 3 count in the cells); `slots.json` `asp853_full_budget` holds only the flag "from paper_compare.json (arm official_nov)" |
| "with DeepSeek and a rebuilt reference" (dropped from the slide; the source line on slide 9 keeps DeepSeek and the stand-in) | `FINAL` §5 |
| Slide 9 title: "How close we are to the paper on 871 depends on the budget" | The registered budget (1,300 s) puts ours 1.3 to 3.5 points above the paper's; at 750 s our frontier is 2.9 to 12.1 points below it (rows below; guards `facts871`, `facts_sens871`) |
| Slide 9, table: ours at the registered budget and at 750 s | `BS` `scenes.00871.tables.apr.{official,frontier_end}.{1300.25,750}.{10,50,100}.{mean,min,max,n,n_runs}`. At 1300.25 s the cells equal `PC`'s (the builder stops if they differ). ASP, 750 s: 32.3 [30.5–35.6] n=3 / 56.3 [55.8–56.8] n=2 of 3 / none. Frontier, 750 s: 26.1 [25.3–27.6] / 43.6 [33.9–57.6] / 62.4 [57.7–67.7], n=5 each. Not registered (`BS` `registered` false; `DEV` item 71): the 750 s rows are labelled "Exploratory" |
| Why 750 s: the paper says a run has 25 to 30 steps, which suggests a shorter budget than 1,300 s. Our inference, not the paper's figure | arXiv 2510.05430v2 §IV ("a full experiment has 25-30 steps"), read by the independent review on 2026-11-19 (`REVIEW` finding 4: v1's Fig. 3 gives 4.6 m a step, so about 115 to 140 m, against about 195 m of frontier path at 1,300 s); `PIN` `paper.steps` |
| Slide 9, equal path, 50 m, scripted reference (apr): exact objects 57.8 [53.5–62.1] n=3; ASP 52.6 [47.2–55.7] n=3; ASP + filter 39.7 [32.2–52.6] n=3; random guesses 42.1 [35.9–52.1] n=3; frontier Nov 49.2 [40.8–62.2] n=5; frontier Oct 36.3 [31.4–44.4] n=3; frontier crashed first tries 37.7 [30.7–46.7] n=4; frontier reruns 42.4 [42.4–42.4] n=1 of 4 | `EQ` `scenes.00871.tables.apr.{oracle_visible,official,filter_only,placebo,frontier_end,frontier_60m,crashed_frontier_1st,crashed_frontier_rerun}.50`. Every arm that has a value at 50 m is shown (`frontier_end_ref` has none). Exploratory |
| Our two frontier batches differ by 12.9 at 50 m, more than ASP differs from November's frontier (3.4) or from random guesses (10.5) | Derived from the printed means: 49.2 − 36.3; 52.6 − 49.2; 52.6 − 42.1 (guard in `facts_sens871`). Not true of every pair of arms: exact objects − random guesses is 15.7 and ASP − ASP + filter is 12.9, so the slide names the two pairs it compares |
| Slide 9 body: "At 1,300 s ours are 1.3–3.5 points above the paper's" | The smallest and largest of the four gaps below (ASP 10% 33.9 − 30.5 = 3.4; frontier 10% 31.9 − 29.2 = 2.7; 50% 59.2 − 55.7 = 3.5; 100% 66.6 − 65.3 = 1.3). Keys: `stage_value_x100.mean`, `paper_f1_x100`, scene 00871, arms official and frontier_end (reference apr, variant B). ASP + filter and random guesses have no paper cell |
| Slide 9 body: "At 750 s our frontier is 2.9–12.1 below it" | `BS` frontier_end at 750 s against `paper_f1_x100`: 26.1 − 29.2 = −3.1; 43.6 − 55.7 = −12.1; 62.4 − 65.3 = −2.9 |
| Slide 9 body: "the paper's value lies inside our range in 3 of 4 cells" | Paper value against `stage_value_x100.min`–`.max`: ASP 10% 30.5 v [30.8–36.4] (outside); frontier 10% 29.2 v [27.8–37.4]; 50% 55.7 v [52.2–67.1]; 100% 65.3 v [64.4–68.3] (inside) |
| Slide 9 body: "at 0.8 of the budget 2 of the 4 gaps turn negative" | `PC` cells with `variant` "0.8B" (reference apr, scene 00871), the registered sensitivity check (`paper_compare.md`, "Sensitivity"): ASP 10% 32.9 − 30.5 = +2.4; frontier 10% 29.6 − 29.2 = +0.4; 50% 51.3 − 55.7 = −4.4; 100% 65.0 − 65.3 = −0.3. (At 1.2 B the ASP 10% gap is +6.8 and the frontier 100% cell has n=2 of 5, which the table's rule hides; the slide does not use 1.2 B) |
| Slide 9 body: "At 10% our four arms score 31.7–33.9 and their ranges overlap" | Scene 00871, fraction 10, `stage_value_x100.mean`: official 33.9, filter_only 33.0, placebo 31.7, frontier_end 31.9. The ranges [30.8–36.4], [29.9–37.6], [30.2–32.6], [27.8–37.4] share 30.8–32.6 |
| Slide 9 body: "No ASP run of ours reaches 50% of the budget" | Scene 00871, arms official and filter_only (placebo too), fractions 50 and 100: `stage_value_x100.n` = 0 of 3. ASP stops at 60 m, which took 289–468 s here; 50% of 1,300 s is 650 s (`paper_compare.md` "Not comparable"; `WRITEUP` §2) |
| Slide 9 source line: the paper's cells are one run each; ours carry n; our ASP runs on 871 stop at 60 m | Fig. 4 (left), `PC` `meta.paper_fig4_left`; `FINAL` §5; `WRITEUP` §2 |
| Script slide 9 and README finding 3: "on 853 ours are 3 to 22 points lower" (3.2 to 22.1) | Derived the same way, scene 00853, apr B, arms official and frontier_end: ASP 10% 16.5 − 34.4 = −17.9; ASP 50% 38.7 − 60.8 = −22.1; frontier 12.4 − 18.6 = −6.2; 39.5 − 46.5 = −7.0; 55.6 − 58.8 = −3.2 |
| README finding 3: n in the tables | The cells' `stage_value_x100.n` (and `n_runs` for "3 of 5"), scenes 00853 and 00871, arms official, filter_only, frontier_end |
| Guard | The builder computes every figure above, checks that script slide 9 and README finding 3 hold them (`check_text`), and stops with a message if a figure is missing, a gap changes sign, a null cell is needed, or an ASP run reaches 50% |

## Slide 8: the two control arms on 853 (Amendment 5, final)

Pass 5 cut the slide to the table, the S note, the two statements and one limits line ("Three runs a side, one home, no p-value; the controls ran later, lost no members, and the no-guess arm moves at 7.1 s per metre against 5.8", numbers from `RSJ` `readout3_sec_per_m`). The rows for the chance of 1 in 20, the two-runs, ties-the-best and one-low-run clauses, frontier's 7.0, the dates, the dropped replies, the sleep and the 4.4% against 29.4% are now on backup 18 (same sources).

`RSJ` = `tools/live_policy/results_paper_compare_1113/rescore_summary.json`, key `nov_controls` (final: `interim` false, `listing.final` true, the queue ended; the rescore of 21 Nov). `CTL` = `slots.json` `controls853`, which `fill_slots_part3.py` writes from `RSJ` (every S value, statement, readout and run row), `RSJ` `nov.runs[].evidence.members_dropped_pct` and `live_policy.py` lines 19 to 22. `NOTES` = `results_paper_compare_1113/NOTES.md`, "Control arms (Amendment 5)". Every cell below is read by `controls_facts`, which stops the build on a mismatch.

| Statement | Source |
|---|---|
| What the arms are: both run ASP's own pipeline and clock, three runs each to 115 m (seeds 42, 43, 44). Random guesses: no LLM call, random rooms and objects drawn with the LLM's measured shape statistics. No guesses: no LLM call, every member's completion is a copy of the observed graph | `PREREG` A5.1, A5.2; run names `e9_00853_s42..44_{placebo,observed_only}_115m`; `RSJ` `runs[]` (six finished, `reached_100m` true, 0 out-of-memory and 0 nvblox lines each); `NOTES` run table |
| The S tables, nine runs: S = a run's mean F1 at 50, 60, 80 and 100 m of path. Scripted reference (apr), seeds 42, 43, 44, mean: ASP with the LLM's guesses 53.6, 52.5, 61.7, 55.9; random guesses 58.1, 56.9, 33.6, 49.5; no guesses 37.4, 44.5, 18.6, 33.5. Human labels (hm3d): 29.0, 28.5, 30.4, 29.3; 30.4, 27.7, 17.7, 25.3; 14.4, 20.8, 10.4, 15.2 | `RSJ` `S.<ref>.<arm>.<run>` (full precision; `NOTES` prints one decimal); means derived by the builder. ASP's three S values are the ones the Note to Amendment 5 (case 4) fixes: 53.55, 52.48, 61.73 and 29.05, 28.47, 30.40 (guard). The mean S of each arm equals the mean of the four equal-path means in `EQ` `scenes.00853.tables.<ref>.<arm>.{50,60,80,100}.mean` (guard, 1e-6) |
| Readout 2 marks: registered for the two new arms; first made after the results were seen for ASP with the LLM's guesses (and for frontier) | `RSJ` `readout2_equal_path.labels` (guard: the exact four labels); `NOTES` "Readout 2"; `PREREG` A5.5 item 2; `DEV` item 66 |
| The statements, as they fall: no guesses "reads above" (separated above under both references); random guesses "in between" (above on average, not separated, under both) | `RSJ` `statements`, `per_reference`; the builder re-derives them from the nine S values by A5.6 (separated above = every ASP run above every control run; not above = ASP's mean not higher; else above on average, not separated). A5.6: "the slide gives both S tables and the statements as they fall" (`RSJ` `decision.slide.kind` `both_tables_and_statements`, `slide_sentence` null) |
| Chance alone gives full separation 1 time in 20 with three runs a side | `PREREG` A5.6 ("1 time in 20"); derived: 1 / C(6,3) = 1/20 (guard) |
| "Every run with the LLM's guesses scores above every no-guess run, under both references" | `RSJ` `per_reference.observed_only_nov.{apr,hm3d}` "separated above"; re-derived: lowest ASP S 52.5 (apr), 28.5 (hm3d) against the highest no-guess S 44.5, 20.8 |
| "The code gives unexplored space no value here (live_policy.py, lines 19 to 22), so this arm differs from ASP in more than what the guesses know" (replaces the pass-4 clause that the arm "shows the pipeline needs some guess to explore", which was itself a claim that guesses help; every no-guess run went 116 m or more, so the pipeline did explore) | The arm's own code note, `tools/live_policy/live_policy.py` lines 19 to 22: "A $0 control, but not 'ASP without predictions': with identical members the information gain only sees graph0/graph1 disagreement, so unexplored space scores zero" (`fill_slots_part3.py` asserts the text; `CTL` `code_note`); `PREREG` A5.1 ("It may explore little. That is the arm, not a fault"); end paths `RSJ` `runs[].end_path_m` (116.3, 117.3, 116.5 m). `no_overclaim` blocks "needs some guess to explore" and "guesses add knowledge" as positive claims |
| It moves at 7.1 s per metre, as slowly as frontier (7.0); ASP 5.8, random guesses 5.9 (the no-guess runs end at stages 39 to 43) | `RSJ` `readout3_sec_per_m.{observed_only_nov,frontier_end,official_nov,placebo_nov}.mean` (7.14, 6.98, 5.77, 5.89; ranges 7.00 to 7.38 and 6.40 to 7.84); guard: no-guess above both ASP arms and within 0.3 of frontier. Stages: `RSJ` `runs[].end_stage` (40, 43, 39); the recompute's "41 to 45 stages" does not match the file and is not used |
| "Two random-guess runs score above two LLM runs against the scripted reference" | `RSJ` `S.apr`: random-guess seeds 42 and 43 (58.1, 56.9) are each above two of ASP's runs (53.6, 52.5); guard counts it |
| "Against the human labels the best random-guess run ties the best LLM run (30.4)" (backup 18; was "the best run ... is a random-guess run") | `RSJ` `S.hm3d`: `e9_00853_s42_placebo_115m` 30.4465 against ASP's best 30.3981; both print 30.4 (guard: printed values equal, 30.4) |
| "The gap in the means comes from one low random-guess run" | `RSJ` `S`: the lowest random-guess run is seed 44 under both references (33.6; 17.7). Without it the random-guess mean is 57.5 (apr), above ASP's 55.9, and 29.1 (hm3d), against ASP's 29.3; the gap in the means falls from 6.4 and 4.0 to below a quarter of itself (guard) |
| Limits: three runs per arm in one home, no p-value | `PREREG` A5.6 "What this cannot show" |
| The controls ran from 11-19, after the LLM runs of 11-17 and 11-18, under a different GPU load | `DEV` item 65 ("11-17 and 11-18: how Amendment 3's runs went"); `PREREG` Note to Amendment 5 (the queue had run since 12:43:45 on 11-19); `NOTES` ("another load on the GPU"); A5.6. The recompute's "two to three days apart" is not used: A5.6 and `NOTES` say "two days later", and the files give dates, so the slide gives the dates (guard on both files) |
| They lose no members to dropped replies; the LLM runs lost 7% to 10% | A5.1 (no LLM call); `RSJ` `nov.runs[].evidence.members_dropped_pct` (7.3, 9.6, 7.4; guard); A5.6 |
| The sleep is a median wait | `PREREG` A5.2 (pacing: the per-stage median of `llm_wait_s` over the three ASP runs); A5.6 |
| Random-guess members agree with each other less than the LLM's (4.4% against 29.4%, October) | `NUM` `agreement:same_label_1m:placebo` (0.0444), `:official` (0.2944), as slide 6; A5.6 |
| Neither arm shows that the LLM's guesses beat random ones | A5.6 "What this cannot show"; `no_overclaim` |

## Slide 10: the runs

Pass 5: the clocks paragraph adds "the arms on slide 8 share ASP's clock" (`PREREG` A5.1: the control arms run ASP's own pipeline and clock).

| Number | Source |
|---|---|
| 45.6 [41.7–52.4] (50%) and 39.5 [33.9–42.0]; 15.3 [12.9–16.9] (10%) and 12.4 [10.8–14.7] | `PC` apr B, scene 00853, arm `frontier_60m` (3 runs, October) and `frontier_end` (5 runs, November), `stage_value_x100` mean, min, max |
| The ranges overlap | Read from the two ranges above (41.7–52.4 and 33.9–42.0; 12.9–16.9 and 10.8–14.7) |
| October, November | `WRITEUP` §12 (seeded frontier, 10-30); `PLAN` §B7 (e7 runs, 11-09 to 11-10) |
| October's runs stop at 60 m; November's go to 105 m | `WRITEUP` §2; `PREREG` A3.1 (target path 105 m); run names `_105m`. October's official arm has `stage_value_x100.n` = 0 at 100% (853) and 50% (871) (guard) |
| 2 of 3 November runs reach 100% of the 853 budget | `PC` apr B, scene 00853, arm official_nov, fraction 100: `stage_value_x100.n` 2, `n_runs` 3; seed 44 ended at 604.0 s (`RS` `nov.runs`) |
| 38.7 [37.2–40.1] and 51.1 [45.7–61.5] at 50% on 853, and October's random-guess runs 43.9, between the two | `PC` apr B, scene 00853, fraction 50, arms official, official_nov and placebo (random guesses, October, no LLM; n=3, 39.4–48.2), `stage_value_x100` mean, min, max. The builder stops if 43.9 is not between the two ASP means |
| The batches differ by as much as the gap between ASP and frontier | 51.1 − 38.7 = 12.4 against the November gap at 50%, 11.6 (guard in `facts853`) |
| On 871 no ASP run reaches 50% | `PC` apr B, scene 00871, arms official and filter_only, fraction 50: `stage_value_x100.n` = 0 of 3 (guard) |
| On 871 the only ASP–frontier comparison is at 130 s | 10% of the 871 budget (`PC` `meta.budgets`, 1,300.25 s). Read: ASP has a value at 10% only on 871 |
| Frontier's clock starts at the end of planning, before the path arrives (lines 637-638 of `frontier_baseline.py`) and stops on arrival (664-665); ASP's clock (`exploration_pipeline.py`) starts as the robot begins to move (lines 714-715) | Read on 2026-11-19 from the authors' repository at commit f1ea141b (`git show` on the host's checkout): frontier_baseline.py lines 637-638 and 664-665; exploration_pipeline.py lines 714-715. The independent review found the same (`REVIEW` finding 8, which gave 638 and 715 for the two starts). `PIN` `clock`. First found in the host's copy: `N12` "Frontier clock" |
| "The reference moves": the two tours agree at F1 0.751 on 853 and 0.771 on 871, below the 0.90 line, more than the paper's margins (one line; the full slide is backup 11) | `C2F` `scenes.00853.f1` (0.7511) and `scenes.00871.f1` (0.7714), `below_0_90`; `N13` item 3; as backup 11's row. The builder reads the newest `c2_*.json` |
| 871: the only ASP–frontier comparison at the registered budget is at 130 s | As the row above for 10% of 1300 s; the slide's wording is "at the registered budget" because slide 9's exploratory rows add equal-path and 750 s comparisons |

Not used: the paper's own seconds per metre from its Fig. 4. The repo's files hold the paper's F1 and GED values for Fig. 4 (`PC` `meta.paper_fig4_left`) but not its times or path lengths, so slide 10 gives only our own seconds per metre.

## Part 3 short names

- `S1` = `tools/live_policy/results_semantic_1113`
- `RC` = `S1/claude/results.json`; `RE` = `S1/exploratory/results.json`
- `CSV` = `S1/numbers_part3.csv` (column `key`; its `path` column gives the path inside the file). Every part 3 number below was also matched to a CSV row by value (nearly all numeric slot values; the exceptions are listed at the end). None disagrees with the CSV.
- `RES` = `S1/RESULTS.md`
- `M2S` = `tools/live_policy/results_m2_1113/pass2/summary_factorial.json`
- `slots.json` holds the part 3 values. `fill_slots_part3.py` writes it from the files below, so the builder never types a result.
- Model names in paths: `claude-opus-5-5`, `claude-haiku-5-5` in `RC`; `deepseek`, `gemini`, `placebo` in `RE`.
- Scores are fractions (0 to 1). "Score" is the mean over the 12 run clusters of `models.<m>.analysis.levels.<L>.model_cluster_scores`; a difference is the contrast's own `mean_diff`, over the rows where both sides have a score.

## Slide 11: the author's claim, in three questions

| Number | Source |
|---|---|
| 44 saved inputs | `SEM` §3 |
| Claude Haiku 5.5 and Opus 5.5; blind test, scorer frozen first | `SEM` §2 (last paragraph), §4, §14; `RC` `run_info.freeze_present` (true), `run_info.freeze_sha256` |
| The claim ("as the author put it to us") and the three questions | The claim: said in person to the student; no written record; the paper's nearest text is in section IV-B (quoted on slide 1's row). It is not in quotation marks on a slide. The questions: `SEM` §1; `M2` §1; `FINAL` §3.2. The slide's note quotes the paper's nearest text: `PIN` `paper.bathroom`, `paper.revisit` |
| "Not in the paper; it comes from the author's demo and from what the author told the student when they met" | The brief for this pass; `REVIEW` finding 2 ("no source"); no file records the meeting |
| Is it the model? "Replay Claude on the same 44 saved inputs. Look at Gemini." | `SEM` §3; Gemini's replay on 36 of the 44 inputs is slides 14 and 15; October's 8 saved inputs are exploratory (backup 2) |
| "Control": a baseline that sees the same map | `SEM` §9 ("Each comparator is given only the row's observed graph") |

## Slide 12: controls

| Number | Source |
|---|---|
| 179 other annotated houses | `SEM` §9 (B3); CSV `rule_houses` |
| The five controls: prior (B3), placebo (B1), own-label swap (B5), region trade (D), prior's labels at the model's places (B3L); used at L1, L2 or L3 | `SEM` §9 table |
| "Named": the control the verdict is read against: the prior at L1 and L2, the region trade at L3 | `SEM` §10 "Verdict for a hypothesis"; `RC` `family.hypotheses.<m>|<L>.named` (B3, B3, D) |
| Margin 5, 5, 3 points | `RC` `family.hypotheses.<m>|<L>.delta` (0.05, 0.05, 0.03) × 100; CSV `c_opus_L1_margin`, `c_opus_L3_margin` |
| The comparators' own scores were not checked before the freeze; the power check asked only whether Rejected was within reach | `SEM` §10 "Detectable difference" (the interval half-width shows whether Rejected is within reach; no step asks what a comparator scores); `REVIEW` finding 1. Note: `SEM` §2 lists pilot counts under cruder rules, among them that random room types "exist unexplored" at 0.95; that is the random guesses' L1 level, not the other-house prior's score, which was not looked at |

## Slide 13: the blind test

All differences and margins in points (×100 of the file's value), one decimal; Opus L3's upper end (0.029496 → 2.95) has two because the verdict turns on it (the margin is 3); the slide says so. Scores are hit rates in % (×100). Cell = difference [95% interval] verdict, then the model's own score and the comparator's own score (Opus and Haiku, from `X19` `ceiling.json`; DeepSeek has none).

| Number | Source (file, path) | CSV key |
|---|---|---|
| Opus L1 / L2: −5.8 [−12.2, 0.0]; −35.1 [−41.3, −29.1] | `RC` `models.claude-opus-5-5.analysis.levels.{L1,L2}.comparators.B3.{mean_diff,ci}` | `c_opus_L1_B3_diff`, `c_opus_L1_B3ci_lo/hi`, L2 |
| Opus L3: +0.5 [−1.9, +2.95] | `RC` `...levels.L3.comparators.D.{mean_diff,ci}` | `c_opus_L3_D_diff`, `c_opus_L3_Dci_lo/hi` |
| Haiku L1 / L2: −10.4 [−20.8, 0.0]; −24.9 [−31.5, −18.1] | `RC` `models.claude-haiku-5-5.analysis.levels.{L1,L2}.comparators.B3` | `c_haiku_L1_B3_diff`, `c_haiku_L1_B3ci_*`, L2 |
| Haiku L3: +0.8 [−0.8, +2.4] | `RC` `...levels.L3.comparators.D` | `c_haiku_L3_D_diff`, `c_haiku_L3_Dci_*` |
| DeepSeek (exploratory) L1 / L2 / L3: −1.7 [−5.2, 0.0]; −26.3 [−33.2, −19.4]; −0.6 [−1.9, +0.6] | `RE` `models.deepseek.analysis.levels.<L>.comparators.{B3,B3,D}` | `e_deepseek_L1_B3_diff`, `e_deepseek_L3_D_diff`, `e_deepseek_L3_Dci_*` |
| Scores: Opus 85.4, 58.3, 4.2%; Haiku 89.6, 68.8, 4.4%; DeepSeek 89.2, 66.4, 4.8% | mean of `...levels.<L>.model_cluster_scores` in `RC` / `RE` | `c_opus_L1_score`, `c_haiku_L2_score`, `e_deepseek_L3_score`, … |
| Difference from random guesses at L1 and L2, points: Opus −2.1, −2.3; Haiku −5.2, +8.2; DeepSeek +1.7, +5.8 (Haiku's +8.2 is on backup 13; the slide 13 cells no longer show these) | `RC`/`RE` `...levels.{L1,L2}.comparators.B1.mean_diff` (interval in `.ci`; p in `.p`) | `c_<m>_<L>_B1_diff`, `e_deepseek_<L>_B1_diff` |
| The comparator's own score: prior (B3) at L1: Opus 91.2%, Haiku 100.0%; at L2: 93.4%, 93.7%; region trade (D) at L3: 3.7%, 3.6% | `X19` `ceiling.json` `models.<m>.<L>.comparators.<B3 or D>.comparator_score` (exploratory; every model-minus-comparator mean in it was checked against `RC` and matches). The model's own score beside it is the slot's, from `RC` as above (Opus L3: 4.2% on 44 rows; the D contrast uses 43 rows) |
| Title: "Naming: no detectable gain over the other-house prior, and below it at L2. Placing: none over a region trade" ("base rates" removed everywhere; the prior is built from 179 other houses) | No interval lies wholly above 0 (the L3 lower bounds are −1.9 and −0.8); at L2 both upper ends are below 0 (−29.1, −18.1); the builder stops otherwise (`blind_facts`). Naming = L1 and L2 against the prior; placing = L3 against the region trade |
| L3 scores beside the region trade: Opus 4.3%, Haiku 4.4% against 3.7%, 3.6% | `X19` `ceiling.json` `models.<m>.L3.comparators.D.{model_score,comparator_score}` (43 rows: the trade's own rows); the slide's note says so |
| "The registered line … at L1 no model could have been Supported, and at L2 only a perfect Opus could (backup 14), so the line rests on L3" | Backup 14 and `X19` `ceiling.json` (`perfect_model.can_reach_alpha`: L1 false for both, L2 true for Opus only); guards in `blind_facts` |
| Random score at L3: 1.7% | `RE` `models.placebo.analysis.levels.L3.model_cluster_scores` (mean) | `e_placebo_L3_score` |
| Margins 5, 5, 3 | `RC` `family.hypotheses.<m>|<L>.delta` | `c_opus_L1_margin`, `c_opus_L3_margin` |
| Note: "15 reruns of the trade after the result (deviation 55) kept [Opus L3's upper end] between 2.83 and 2.98" | As backup 13's row: `S1/independent_recompute/margin_summary.json` `summary.claude-opus-5-5|200` and `|5000` (`ci_high_min` 0.028349, `ci_high_max` 0.029792; 10 and 5 runs); `DEV` item 55 | `rc_opus_hi_min`, `rc_opus_hi_max` |
| All six Rejected; DeepSeek's three Rejected (exploratory) | `RC` `family.hypotheses.<m>|<L>.verdict`; `RE` `models.deepseek.exploratory_family.hypotheses` | `c_opus_L1_verdict`, `e_deepseek_L3_verdict` |
| "The claim fails" | `RC` `family.thesis`; rule `SEM` §10 "The thesis" | `thesis` |
| "Rejected: the interval rules out a gain over the named comparator as large as the margin" | `SEM` §10 "Verdict for a hypothesis" (upper end below δ) |
| "At L2 the interval lies wholly below zero" (all three models) | the three L2 upper ends above (−29.1, −18.1, −19.4 points) are below 0 |
| 12 clusters (home, seed, arm) | `SEM` §3; `RC` `mdd_table.L1.n_clusters` |
| One run with the frozen scorer; no other run is recorded | `RC` `run_info` (one run, `rounds_argument` auto, `freeze_present` true); `SEM` §14. The absence of other runs is the lead's statement; no file counts scoring runs |

## Slides 14 and 15: is it the model? (registered replay of Gemini 3.8 Flash)

Pass 3 cut these two slides to a table and one registered sentence each, plus a note. The exploratory lines (the prior and random guesses at L2, the wrong-house check, the claim counts) are backup 17 (`flash_extra_slide`); the rows below say where each one went.

Registered: `PREREGISTRATION_GEMINI.md` with Notes 1 and 2 (hashed before any call on a frame row); how it went: `DEV` item 72. Result: `GR` = `tools/live_policy/results_semantic_1113/gemini_1119/results.json` (write-up: `RESULTS_GEMINI.md`). The slot values come from `fill_slots_part3.py` (`slots.json` `gemini_replay`). The model is `gemini-3.8-flash`, the registered fallback, because `gemini-2.5-pro` was refused (Note 1). Every sentence names it and says it is not the paper's model.

The builder stops (`gemini_facts`) unless: the four hypotheses of 5a are found, with Gemini above and Holm p below 0.05, over 12 clusters; the file's first sentence is the "does not carry over" one; the L3 verdict is Rejected against D with the upper end under the margin; Gemini's L3 score is above both Claude models' and below all three controls; at L2 the prior's interval is below 0 and random guesses' above 0; the wrong-house gate passes at L1 and L2 over 6 pairs; the drop rate is under 25%; 4 members a row, rounds 1, 2, 3 finished.

| Statement | Source (path in `GR`) |
|---|---|
| 36 inputs (rows), 4 members each, 137 of 144 parsed; drop rate 4.9% (under 25%) | `analysis_set.confirmatory.{rows,members,ok,dropped}`; `analysis_set.all_rows_run.drop_rate`; `members_per_row`; `finished_rounds` |
| The author's own loop; Claude ran our port of it, so the contrast is of model and loop together | `PREREGISTRATION_GEMINI.md` §3 and §5a (5a's own words) |
| The paper's Gemini 2.5 Pro is no longer offered to new users (11-19) | Note 1 (HTTP 404, "no longer available to new users") |
| Confirmatory contrast, 12 clusters, one-sided, Holm over 4: Gemini minus Opus L2 +21.0 [+13.5, +28.8], Holm p 0.0010; L3 +2.7 [−0.3, +5.8], 0.0381; Gemini minus Haiku L2 +10.9 [+1.6, +20.5], 0.0344; L3 +3.1 [+0.4, +6.0], 0.0381 | `confirmatory.5a.family.<model>|<L>.{mean_diff,ci,p_holm,found,n_clusters}`; the two scores in the table are `confirmatory.5a.tables.<model>.<L>.{model_mean,other_mean}` (Gemini 78.3% and 7.5%; Opus 57.2% and 4.8%; Haiku 67.4% and 4.4%, on the rows both have). Points = 100 × the file's value |
| The registered sentence for this outcome, word for word | `confirmatory.wording[0]`; `PREREGISTRATION_GEMINI.md` §6 (first bullet) |
| Against Opus at L3 the interval reaches below zero; the lead is found under the one-sided test (Holm p 0.038) | `5a.family.claude-opus-5-5|L3.{ci,p_holm}` (−0.0029 to +0.0576; 0.0381). The independent recompute's note: the sentence is not to be read as more than this |
| October's lead on 8 rows repeated on 36 new ones | `X19` `common_rows.json` (Gemini above Opus and Haiku at L2 on the 8 rows; guarded) and the four hypotheses above |
| L3 registered rule: Rejected; Gemini's own score 7.5% beside its three controls: own labels swapped (B5) 8.5%, region trade (D, named) 8.7%, prior's labels at its places (B3L) 11.0%; Gemini minus each −1.0 [−2.0, −0.1], −1.2 [−3.7, +1.4], −3.5 [−5.4, −1.6]; upper end vs D +1.4, margin 3 | `confirmatory.5b.levels.L3.{verdict,named,delta,ci_upper_named,model_own_score}`; `.comparators.{B5,D,B3L}.{comparator_own_score,mean_diff,ci}`. The D contrast is on D's 35 rows (Gemini's score on them 7.51%) |
| The Rejected sentence, word for word | `confirmatory.wording[5]`; `PREREGISTRATION_GEMINI.md` §6 |
| Slide 14 note: "Gemini ran the author's loop and Claude our port of it, so this compares model and loop together" | `PREREGISTRATION_GEMINI.md` §3 and §5a, as the row above |
| Both hold: Gemini's L3 score (7.5%) is above Claude's (4.8% Opus, 4.4% Haiku) and below the trade's (8.7%); its lead is in the raw rate and does not show that its labels fit their regions | `5a.tables.<claude>.L3.other_mean`; `5b...comparators.D.comparator_own_score`. The reading is the independent recompute's; the rate comparisons are the file's |
| Backup 17, exploratory: at L2 Gemini scores 78.3%; the prior from other houses, making as many claims, scores 90.7%, about 12 points above (−12.4 [−18.5, −6.3]); random guesses 59.6% (+18.6 [+12.8, +24.4]) | `5b.levels.L2.model_own_score`; `.comparators.B3.{comparator_own_score,mean_diff,ci}`, `.comparators.B1.*`. Exploratory under `PREREGISTRATION_GEMINI.md` §5b (L1 and L2 are scored by §10's rule as exploratory; the ceiling is said beside them) |
| Backup 17 and backup 1, exploratory: the wrong-house check passes at L1 (p 0.031) and L2 (p 0.016), 6 pairs | `confirmatory.5c.wrong_house_gate.{L1,L2}.{p,n_pairs,pass}`; reported, no verdict (§5c) |
| Slide 14 note and backup 17: Gemini also made more guesses per member; 5a does not adjust for that | The independent recompute of the result. No number is given: the file holds only totals on different row sets (`confirmatory.5c.validity.kept_vs_guesses.raw.l2_claims`, 1,270 over 137 members) and per-member counts would have to be computed; the deck does not compute them. `PREREGISTRATION_GEMINI.md` §5a compares hit rates with no matching of claim counts |
| Saved inputs from two homes; no robot acted; the comparators at L1 and L2 sit at the ceiling | `PREREGISTRATION_GEMINI.md` §6 (last bullet); `confirmatory.wording[6]` |
| The extension to one more Gemini model (Note 3, Gemini 4 Argon) is on backups 7 and 8; the last run (Neon) is on backup 15 | `PREREGISTRATION_GEMINI.md` Notes 3, 4 and 6; `DEV` items 73, 75, 76 |

## Slide 16: the three Gemini models side by side

Built from `GR`, `AR`, `R32` and `NR` (the four `slots.json` entries, each guarded). Why this slide: the Gemini part would otherwise run to five main slides; the two Argon slides moved to backups 7 and 8 and Neon to backup 15, and this slide gives the three models in one table. The inputs and the registration words use 24 px, the smallest size on a main slide.

| Statement | Source |
|---|---|
| Flash: 36 inputs, 4 members, 137 of 144; L2 minus Opus +21.0 [+13.5, +28.8] above, minus Haiku +10.9 [+1.6, +20.5] above; L3 Rejected (upper end +1.4, margin 3) | `GR` `confirmatory.5a.family`, `5b.levels.L3`; the registration's words ("above" for a found hypothesis, §6) |
| Argon round 1: 12 inputs, 4 members, 48 of 48; minus Opus +17.5 [+5.0, +30.3] above; minus Haiku +13.6 [−1.4, +28.5] not detectably above; L3 Inconclusive (upper end +3.1) | `AR` as above; Note 3 |
| Argon new inputs: 24 inputs, 2 members, 48 of 48; minus Opus +18.7 [+10.8, +26.7]: no verdict registered; minus Haiku +5.4 [−2.8, +13.5]: not detectably above (R2a); L3 Rejected (upper end +2.8) | `R32` as above; Note 4 (only R2a and R2b carry a verdict) |
| Neon: 24 inputs, 2 members, 48 of 48; minus Opus +8.5 [−1.1, +18.0] and minus Haiku +0.6 [−10.0, +12.0]: no verdict registered; L3 Inconclusive (upper end +6.3) | `NR` as above; Note 6 N2 |
| "Three Gemini models were tried in turn (3.8 Flash, 4 Argon, 4 Neon), each chosen after the last result was seen. All three are reported; they are not three independent confirmations, and none is the paper's model." | Note 6 N3, word for word (the builder checks it against the registration) |
| At L3 no Gemini model was found to beat a trade of regions by the margin (Flash Rejected; Argon Inconclusive, then Rejected; Neon Inconclusive). At L2 Flash was above both Claude models; Argon above Opus only; for Neon no verdict was registered | The four files' `5b.levels.L3.verdict` and `5a.family`; Argon's L2 line against Opus is round 1's (the new inputs' Opus line has no verdict, Note 4). Each clause is what a verdict says: Rejected rules out a 3-point gain, Inconclusive does not |

## Slide 17: the paper's room test (exploratory)

Title: "DeepSeek ahead of random guesses in count; not detectable on the rule of §11 (p 0.125)". "Ahead in count" is 10 of 59 against 6 of 69 (16.9% against 8.7%); "not detectable on the rule of §11" is the 8-member-stage p of 0.125 below (above 0.05).

From `X19` `room_test_runs.json` (`DEV` item 71 (c)); its live part is the same as `S1/claude/room_test.json`. Type matched; a room counts if at least 2 of 8 members place a room of that type within 2.5 m of the region centre before the region is first seen (`SEM` §11). Unit: the run; exact permutation of arm labels within a scene (`DEV` item 71).

| Number | Source (path in `room_test_runs.json`) |
|---|---|
| 8-member stages (the rule of registration §11; the slide does not call it a registered result): DeepSeek 10 of 59 rooms, 16.9%; random guesses 6 of 69, 8.7%; p 0.125 | `views.eight_member_stages.pooled.{official,placebo}.{predicted,of,rate}`; `.tests.official_vs_placebo.p_two_sided` (0.125, 200 relabelings) |
| All stages: 13 of 59, 22.0%, p 0.040 | `views.all_stages.pooled.official`; `.tests.official_vs_placebo` (p 0.04, 200 relabelings) |
| The filter arm (DeepSeek's guesses through our validator, 6 runs): 2 of 69, 2.9% on 8-member stages (−5.8 points, p 0.290); 7 of 69, 10.1% on all stages (+1.4 points, p 1.000); not ahead of random guesses | `views.*.pooled.filter_only.{predicted,of,rate}`; `views.*.tests.filter_only_vs_placebo.{observed_diff,p_two_sided}` (400 relabelings) |
| 5 DeepSeek runs and 6 random-guess runs | `views.*.pooled.{official,placebo}.runs` |
| DeepSeek's runs hold 4 to 11 stages with 8 members, out of 17 to 21 | `views.eight_member_stages.runs[arm=official].{n_stages_with_8_members,n_stages}` (min and max). The file's own caution says the arms do not have equal chances under the 8-member rule |
| Opus, replayed: 16.7% of rooms in a fitting unobserved region against 2.7% for random guesses; +13.9 points (+1.4 to +27.1); p 0.016; one contrast, not adjusted | `RC` `models.claude-opus-5-5.extras.l3_rooms.{model_clusters,placebo_clusters,mean_diff,ci,p}`; the table `x_misc` ("L3, rooms only") in `RES` §7. Secondary readout: no verdict rests on it and nothing is corrected for the number of looks |
| The paper reports 9 of 28 rooms (32%) with no chance rate | `S1/claude/room_test.json` `live.by_arm.paper.{predicted,of}`; the paper (Fig. 4 text) gives no chance rate: `REVIEW` finding 7 |

## Slide 18: what this talk cannot show, and how the test was made

Two slides merged in pass 3 (the scope slide and the method slide). Five paragraphs: two houses; a small model in Part 1; static replays, not the paper's model; how the test was made; not done.

| Number | Source |
|---|---|
| Every result holds for 853 and 871 only; truth is a proxy; static replays | `SEM` §16; RESULTS §10 |
| The paper used Gemini 2.5 Pro, which is no longer offered to new users (11-19, Note 1); we ran Claude in our port of the author's loop and all three Gemini models in the author's own, so each Gemini-Claude contrast has two differences (model and loop); Argon and Neon were each added after the last result was seen | `PLAN` §B1 (LLM row); `SEM` §4, §12 (loop: "a direct port of the author's tool loop"; prompt from the run's own config); `PREREGISTRATION_GEMINI.md` Note 1 |
| Part 1's live model is small: DeepSeek V4.1 Flash at low reasoning effort; the paper's sentence on smaller LLMs | As slide 4 (`PREREGISTRATION_E1.md` line 9; arXiv 2510.05430v2 §IV footnote; `PIN` `paper.small_model`) |
| Argon and Neon were each added after the last result was seen | `PREREGISTRATION_GEMINI.md` Notes 3, 5, 6 (what had been seen) |
| "Not done: a live run with a strong model" | `SEM` §16; RESULTS §10 ("What it does not let the talk say"). Part 1's live model was DeepSeek V4.1 Flash; no live run with Claude or Gemini was made |


| Number | Source |
|---|---|
| The scorer was written after DeepSeek's numbers were seen; frozen before Claude | `SEM` §2 (last paragraph), §14 |
| The comparators' own scores were not checked before the freeze | As slide 12 |
| The L3 margin was set knowing the Gemini–DeepSeek gap | `SEM` §2 (last sentence: "The margin δ at L3 (§10) was set knowing the 9-point gap above") |
| M2 is provisional: its yardstick failed part of an October check | `M2` §2, §7; `DEVIATIONS_NOVEMBER.md` item 54 |
| One Haiku member stopped at the token limit and its text did not parse; 175 of 176 did | `RC` `models.claude-haiku-5-5.status` (one member `dropped`: row `e2_00871_s43_filter_st03`, member 3); CSV `status_haiku_ok`, `mem_haiku_parse_fail`, `mem_haiku_n`. The stop: `/Users/sher/project/cvp/replay_outputs/m4/claude-haiku-5-5/effort_medium/e2_00871_s43_filter_st03/member_3/record.json` `stop_reasons` ends `["tool_use", "max_tokens"]` (outside the repo); the unparsed text: `…/member_3/parse.json` (`ok` false) |

## Slide 19: for Claude, in our port, on saved inputs: no better than a prior from other houses

Bold sentence: "In two houses, Claude named rooms and objects no better than a prior from 179 other houses (worse at objects), and put its guesses in fitting regions no more often than a trade of regions (a gain under 3 points is not ruled out)." This replaces the older "no detectable information beyond house base rates" claim everywhere (script, README, RESULTS, the closing slide).

| Number | Source |
|---|---|
| Named rooms (L1) no better than the prior: both Claude intervals end at 0.0 or below (Opus [−12.2, 0.0], Haiku [−20.8, 0.0]) | Slide 13, L1 against B3 (`RC` `...levels.L1.comparators.B3.ci`); guard `findings_facts` (L1 upper ends not above 0). "The prior" = the one built from 179 other houses (B3) |
| Worse at objects (L2): both models far below the prior (−35.1, −24.9 points; upper ends −29.1, −18.1) | Slide 13, L2 against B3; `SEM` §16 (two houses) |
| Placed its guesses in fitting regions no more often than a trade of regions: no L3 interval wholly above 0 (lower ends −1.9, −0.8) | Slide 13, L3 against D; guard `blind_facts` |
| "A gain under 3 points is not ruled out" | Slide 13, L3 (D); backup 14 (upper ends 2.95 and 2.36 points); `SEM` §10 |
| M2 (offline): true objects moved by a model's error showed no detectable gain | Backup 16; `M2` §6, §7 |
| The registered line, second: "The claim fails", for the first half of the claim as the author put it to us (that the guesses are right in meaning) | `RC` `family.thesis`; CSV `thesis`; `SEM` §1, §10 "The thesis"; `FINAL` §5; RESULTS §10. Slide 1's row for the source of the claim |
| It says less than it seems to: at L1 no model could have been Supported, and at L2 only a perfect Opus, so it rests on L3, where Opus's interval ends at 2.95 against a margin of 3 | Backup 14; `X19` `ceiling.json` |
| "Gemini:" box, two sentences. No Gemini model is the paper's model. At L3 none was found to beat a trade of regions by the margin (Flash Rejected; Argon Inconclusive, then Rejected; Neon Inconclusive); at L2 Flash was above both Claude models and Argon above Opus only; for Neon no verdict was registered at L2 | Slide 16 (the files' wording); `GR`, `AR`, `R32`, `NR` `confirmatory.5a.family`, `5b.levels.L3.verdict` |
| Outcome picked by the rules | `slots.json` `outcome` (written from `RC` `family.thesis`) |

## Slide 20: the talk in three sentences, and what it does not say

The three sentences stand in full here (36 px) and in short form on the cover (one under each part). `findings_facts` checks every clause against the result files and stops the build if one fails; the script and README carry the same sentences (needles in `check_text`).

| Sentence | Source and guard |
|---|---|
| 1. "Live, with a small model, ASP's guesses made no detectable difference to the map; a gain up to 0.04 F1 is not ruled out." | `NUM` `E1:hm3d:60m:permutation_lo/hi` (−0.012, +0.040; 0.04 to two places), E2 and the frontier-seed intervals (`FH` `official/ci60`, `placebo/ci60`) all hold 0, E3's p above 0.05. Guard: `findings_facts` |
| 2. "At the paper's scale on 853, ASP leads frontier by the clock but not clearly by distance. Against the same pipeline with random guesses it is higher on average but not separated; against no guesses it reads above, and with none the score barely grows with distance on average." | Clause 1: the leads at 10%, 50% and 100% are positive (`facts853`, slide 7); at equal path the sign is positive under the scripted reference and negative under human labels at 50 m and 100 m (`facts_equal853`; `EQ`, exploratory). Clause 2: `RSJ` `statements.placebo_nov` "in between", `per_reference.placebo_nov.{apr,hm3d}` "above on average, not separated"; the builder re-derives both from the nine S values (A5.6) and checks that ASP's mean S is higher than the random-guess arm's under both references. Clause 3: `RSJ` `statements.observed_only_nov` "reads above" (separated above under both references; re-derived). Clause 4: on average the F1 gain from 50 m to 100 m of path in the no-guess arm is under half of ASP's under both references (apr +4.0 against +14.3; hm3d +2.3 against +7.1; `EQ` `scenes.00853.tables.<ref>.{observed_only_nov,official_nov}.{50,100}.mean`); guard in `findings_facts`. Per run (`paper_compare.json` `runs[].stages[].scores.<ref>.f1` at the last stage within 50 m and 100 m; guard in `controls_facts`): seeds 42 and 44 of the no-guess arm gain under 2 points, but seed 43 gains 11.1 (apr) and 8.4 (hm3d), as much as the LLM runs (ASP +15.6, +17.3, +10.0 and +8.9, +9.5, +2.8), so the sentence says "on average". The recompute's wording "hardly explores" is not used because no file measures exploration. Guard: `findings_facts` |
| 3. "On saved inputs, none of five models (two Claude, three Gemini) was found to put its guesses in fitting regions more often than a trade of regions, and a prior from 179 other houses named objects better than every one of them." | Six L3 verdicts (Opus, Haiku, Flash, Argon round 1, Argon new inputs, Neon): none Supported, Opus and Haiku Rejected; every L3 interval against D has a lower end below 0; every L2 interval against the prior (all five models, Argon's two runs) has an upper end below 0 (`RC`, `GR`, `AR`, `R32`, `NR`). Guard: `findings_facts` |

The list below it follows RESULTS §10 "What it does not let the talk say".

| Number | Source |
|---|---|
| It does not say that the LLM's guesses beat random ones (the control arms do not show it; `no_overclaim` scans the slides, script, README and RESULTS for such wording, and for the positive claim that guesses help this pipeline, but the deck is no longer required to deny the latter) | `RSJ` statements; A5.6 "What this cannot show" |
| It does not say the guesses carry nothing: no gain was found; at L3 a gain under 3 points is not ruled out; the prior's near-perfect score left little room for a gain at L1 and L2 | Slides 13 and 19; backup 14; `REVIEW` finding 1 |
| It does not say the models are no better than random guesses: Haiku is 8.2 points above them at L2 (one contrast, not adjusted, exploratory) | `RC` `models.claude-haiku-5-5.analysis.levels.L2.comparators.B1.{mean_diff,p}` (0.0821; p 0.014); as backup 13. Labelled exploratory: no verdict rests on it (the named comparator at L2 is the prior, `SEM` §10) |
| It does not say that a language model cannot help exploration | RESULTS §10 (the line the write-up is gaining); scope of a static, two-house test |
| (Slides 18 and 16 hold the rest: the paper's model, the loops, live runs with a strong model) | Slides 16 and 18 |

## Backup 1: the wrong-house check

| Number | Source (file, path) | CSV key |
|---|---|---|
| p: Opus 0.125 (L1), 1.000 (L2); Haiku 1.000, 0.953; DeepSeek (exploratory) 1.000, 1.000 | `RC` `family.wrong_house_gate.<m>|<L>.p`; `RE` `models.deepseek.exploratory_family.wrong_house_gate` | `gate_<m>_<L>_p` |
| Pairs: Haiku L1 5, the rest 6; "a pass needs p below 0.05 over 6 pairs"; no Claude model passes (`pass` false for all six) | same, `.n_pairs`, `.pass`; `SEM` §10 "The wrong-house gate" | `gate_haiku_L1_pairs`, `gate_<m>_<L>_pass`, `rule_gate_pairs` |
| October's 8 Gemini rows have no partner (`SEM` §9, B4). Gemini 3.8 Flash in the replay passes: L1 p 0.031, L2 p 0.016, 6 pairs each (reported, no verdict) | `SEM` §9 (B4) | `GR` `confirmatory.5c.wrong_house_gate.{L1,L2}.{p,n_pairs,pass}` |
| Argon round 1: L1 p 0.25, L2 p 0.75; Argon on the new inputs: L1 p 0.625, L2 p 0.8125; Neon: L1 p 0.0625, L2 p 0.0156 (passes at L2 only). 6 pairs each. Reported with no verdict. Argon passes at neither level in either run | `AR`, `R32`, `NR` `confirmatory.5c.wrong_house_gate.{L1,L2}.{p,n_pairs,pass}`. Guard in `wrong_house`: Flash passes at L1 and L2, Neon at L2 only, Argon at neither |
| Definition: the model's guesses for the other home, scored against this home | `SEM` §9 (B4) |

## Backup 2: how far a guess is from an object it could name

A description, and the input to M2's F3 arms (`M2` §4); not a claim about where guesses sit. Medians of the placement-error samples (distance from a guess to the nearest unseen object that answers to its class). Counts and medians are computed from each file's list of distances. "Used / all" = used + left out, with the left-out count from `error_sample_left_out`.

| Number | Source | CSV key |
|---|---|---|
| Median: Gemini 5.8 m, Haiku 7.1, DeepSeek 7.7, Opus 8.1, random 8.9 | `S1/exploratory/error_sample_{gemini,deepseek,placebo}.json`; `S1/claude/error_sample_claude-{haiku,opus}-5-5.json` (np.median) | `err_<m>_median` |
| Used / all: Gemini 314 / 349; Haiku 617 / 894; DeepSeek 1,249 / 1,859; Opus 800 / 1,348; random 1,030 / 1,660 | length of each list; `RC`/`RE` `models.<m>.error_sample_left_out` (35, 277, 610, 548, 630); `error_sample_n` | `err_<m>_n`, `err_<m>_left` |
| "The nearest object of a class is a minimum; guesses with no such object are left out" | `M2` §4 (F3-m: "a guess with no such object in the scene is left out"), §7 ("the distance to the nearest object of a class is a minimum") |
| Gemini: 8 inputs, exploratory; DeepSeek exploratory | `SEM` §3, §4 |
| Medians for DeepSeek, Haiku, Opus equal M2's error medians | `tools/live_policy/results_m2_1113/NOTES.md` "Error samples" | `m2_err_<m>_median` |

## Backup 3: the paper's room test: other counts, Claude replays, prompt hint

The main counts moved to slide 17. This slide keeps the untyped counts, the filter arm, the Claude replays and the prompt hint. From `S1/claude/room_test.json` (its live block equals `S1/exploratory/room_test.json`; checked by `fill_slots_part3.py`). The rows are DeepSeek's October live arms, exploratory: `official` = "DeepSeek, expl.", `filter_only` = "DeepSeek + filter", `placebo` = random guesses.

| Number | Source (file, path) | CSV key |
|---|---|---|
| DeepSeek live, all stages, typed / untyped: 13 and 52 of 59 | `live.by_arm.arms.official.{predicted_all_stages_typed,predicted_all_stages_untyped,of}` | `room_live_official_all_stages_typed_n`, `…_untyped_n`, `room_live_official_of` |
| 8-member stages: 10 and 37 of 59 | `…official.predicted_stages_with_8_members_{typed,untyped}` | `room_live_official_stages_with_8_members_typed_n`, `…_untyped_n` |
| DeepSeek + filter: 7, 37, 2, 11 of 69 | `…arms.filter_only.*` | `room_live_filter_only_*` |
| Random: 6, 40, 6, 40 of 69 | `…arms.placebo.*` | `room_live_placebo_*` |
| Percentages (22%, 88%, 17%, 63%; 10%, 54%, 3%, 16%; 9%, 58%) | Derived: hits over rooms, whole percent |  |
| Paper: 9 of 28 (32%); the rule: at least 2 of 8 members within 2.5 m before the region is seen | `live.by_arm.paper.{predicted,of}`; `SEM` §11 "The paper's room test" | `room_paper_pred`, `room_paper_of`, `rule_room_k`, `rule_room_m` |
| Claude replays, 1 of 4, type matched, of 171 rooms: Opus 11, Haiku 2, DeepSeek 11, random 8 | `replay.claude-opus-5-5.totals`, `replay.claude-haiku-5-5.totals`; `S1/exploratory/room_test.json` `replay.{deepseek,placebo}.totals` | `room_rep_<m>_1of4_typed`, `room_rep_<m>_of` |
| Hint (Haiku, 12 round-1 rows): room claims that hit, 11 of 12 without the sentence, 5 of 9 with it | `S1/nohint_haiku/records_claude-haiku-5-5.json` and `S1/claude/records_claude-haiku-5-5.json`: sum over `records[round 1].model.<member>.counts.{l1_hits,l1_n}`; the no-hint run's other files are in `S1/nohint_haiku/` (`results.json`, `validity.json`, `room_test.json`) | `nohint_nohint_hits`, `nohint_nohint_claims`, `nohint_hint_hits`, `nohint_hint_claims` |
| Hint, object claims: 150 of 230 without, 146 of 219 with (to be added to the write-up) | same two files, `counts.{l2_hits,l2_n}`, summed (no CSV key yet) | |
| Run after the result (deviation 56); exploratory | `DEVIATIONS_NOVEMBER.md` item 56; `SEM` §11 | |

## Backup 4: do the filter and the vote keep right guesses?

From `S1/claude/validity.json` (Opus, Haiku) and `S1/exploratory/validity.json` (DeepSeek, exploratory; placebo = "Random guesses"). Brier scores and the L3 hits kept at a vote of 1.0 are in `slots.json` `validity` but are not on the slide (Brier: Opus 0.257, Haiku 0.136, DeepSeek 0.166, random 0.132; hits at a vote of 1.0: Opus 4 of 122, Haiku 0 of 24, DeepSeek 0 of 40, random 0 of 59).

| Number | Source (path in each model's block) | CSV key |
|---|---|---|
| Removed, %: Opus 8.5, Haiku 20.2, DeepSeek 32.0, random 68.9 | `share_removed.share_removed` ×100 | `val_rem_<m>_share` |
| L3 kept minus removed, points: Opus −12.6, Haiku +0.1, DeepSeek −0.1, random −0.2 | `kept_vs_removed.L3.mean_diff` ×100 | `val_kr_<m>_L3_diff` |
| "Can the interval be read": Opus no, too wide; the others yes, no detectable difference | `kept_vs_removed.L3.verdict` ("interval reaches beyond +-0.05" or "no detectable difference"); rule `SEM` §11 (±5-point band) | |
| Fifth readout cut (needed H5) | `SEM` §15 |

## Backup 5: why does ASP not gain from all true objects?

From `M2S` (`tools/live_policy/results_m2_1113/pass2/summary_factorial.json`).

| Number | Source (path in `M2S`) | CSV key |
|---|---|---|
| All true objects for every member: −0.017 (−0.031 to −0.004) against random guesses | `analysis.main.all.differences.F0-F5.{mean,lo,hi}` (−0.01717, −0.03095, −0.00364) | `m2_F0F5_mean`, `_lo`, `_hi` |
| True objects in differing subsets: +0.218 above random guesses | `analysis.main.all.differences.A.mean` (0.21809) | `m2_A_mean` |
| The score counts disagreement between members; registered before the run | `M2` §7 ("The all-true anchor, F0"); `tools/live_policy/live_policy.py:19-22` |
| The gain is zero for every candidate in only 2 of 384 stages | `counts_all_stages.ig_zero_stage_share.F0.{stages_ig_zero_for_every_candidate,n_stages}` | `m2_f0_ig_zero`, `m2_f0_ig_zero_of` |
| The saved arrays (exploratory): with identical members the score reads mainly where the two observed maps disagree; the gain never passes 2.0 bits over 384 stages, like the no-guess arm's, where other arms reach 4.75 to 5.5; the two correlate at 0.64 over 382 stages | `AT` (as backup 16's row); `M2` §7 (F0 "is a property of the score, shown as such"); `NOTES` of `results_m2_1113` "F0, the all-true anchor". The "we cannot explain" line is gone |

## Backup 6: the four outcomes

| Number | Source |
|---|---|
| The four rules | `SEM` §10 "The thesis" table; the order of the rows `DEVIATIONS_NOVEMBER.md` item 51 |
| Neither Claude model Supported at L3; none at L1 or L2; all six Holm p-values 1.00 | `RC` `family.hypotheses.<m>|<L>.p_holm`; CSV `c_<m>_<L>_holm` |
| None passes the wrong-house check | backup 1 |
| Both models Rejected at L2 and L3 | `RC` `family.hypotheses` |

## Backup 7: Gemini 4 Argon, round 1 (the extension of Note 3)

Registered 2026-11-19 18:51 IST, after the Flash result was seen and before any call on the new model (`PREREGISTRATION_GEMINI.md` Note 3; `DEV` item 73). Result: `AR` = `tools/live_policy/results_semantic_1113/gemini_argon_1119/results.json` (write-up `RESULTS_GEMINI.md`); exploratory contrast `AF` = `.../gemini_argon_1119/argon_minus_flash.json` (computed after both results were seen; `AF.md` says so). Slot: `slots.json` `argon_replay` (`fill_slots_part3.py`). The builder stops (`argon_facts`) unless: 12 rows, 4 members, 48 of 48 parsed, 12 clusters, round 1 finished; exactly one of the four contrasts is found (Opus at L2) and the file's lines use "above" for it and "not detectably above" for the other three; the L3 verdict is Inconclusive against D with an interval that holds zero and reaches the margin; Argon minus Flash holds zero at L2 and L3; the prior's interval at L2 is below 0.

| Statement | Source |
|---|---|
| Gemini 4 Argon, the second of Google's Gemini 4 line (its top model is Gemini 4 Carbon), in the author's loop, on the 12 round-1 inputs, 4 members each, 48 of 48 parsed | Note 5 of `PREREGISTRATION_GEMINI.md` (the price page read fresh on 2026-11-19 at 20:55 IST: Carbon "our most capable reasoning model", Argon "our efficient Gemini 4 frontier reasoning model", same price); `DEV` item 74. Notes 3 and 4 said "top model" from an old cached copy of the page and are corrected. Run and rows: Note 3 (E1); `AR` `analysis_set.confirmatory.{rows,members,ok}`, `members_per_row` |
| The check on 24 more inputs (Note 4) is on backup 8 | `PREREGISTRATION_GEMINI.md` Note 4; `DEV` item 75 |
| Registered after the Flash result was seen | Note 3 ("after the Flash result was seen, before any call on the new model"; E3 asks the slide to say so) |
| Argon minus Opus L2 +17.5 [+5.0, +30.3], Holm p 0.0205, above; Opus L3 −0.4 [−5.7, +4.9], 0.6445; Haiku L2 +13.6 [−1.4, +28.5], 0.1069; Haiku L3 +1.2 [−4.4, +6.7], 0.6445: not detectably above. 12 clusters of one row each | `AR` `confirmatory.5a.family.<model>|<L>.{mean_diff,ci,p_holm,found}`; scores `5a.tables.<model>.<L>.{model_mean,other_mean}`; the words: `confirmatory.wording[1..4]` (the registration's §6) |
| Registered rule at L3: Inconclusive; Argon minus the region trade +0.0 [−2.8, +3.1] against a margin of 3; Argon's own L3 score 6.2% beside 5.7% (own labels swapped), 6.2% (the trade), 6.6% (prior's labels at its places) | `AR` `confirmatory.5b.levels.L3.{verdict,delta,ci_upper_named,model_own_score}`, `.comparators.{B5,D,B3L}.{comparator_own_score,mean_diff,ci}`; `confirmatory.wording[5]` |
| (No longer on the slide; backup 8's all-36 lines replace it.) Exploratory: Argon minus Flash on the same 12 rows, both in the author's loop (the models alone): L2 −2.9 [−9.1, +3.4], L3 −5.4 [−13.1, +2.0] | `AF` `levels.<L>.{diff,interval,p_two_sided,rows}` |
| Exploratory: at L2 Argon scores 79.3%, below the prior (96.5%; −17.2 [−23.9, −10.5]) | `AR` `confirmatory.5b.levels.L2.model_own_score`, `.comparators.B3.{comparator_own_score,mean_diff,ci}` (exploratory under §5b) |
| Not the paper's model; the intervals are wide | `AR` `confirmatory.wording` (each line says the first); 12 clusters of one row each (Note 3 E2a) |
| Reported with no verdict, not on the slide: the wrong-house gate does not pass (L1 p 0.25, L2 p 0.75, 6 pairs) | `AR` `confirmatory.5c.wrong_house_gate` |
| Summary lines (slides 19 and 20; the full table is slide 16): at L3 no Gemini model was found to beat a trade of regions by the margin (Flash Rejected; Argon Inconclusive on round 1, then Rejected on the new inputs; Neon Inconclusive); at L2 Flash was above both Claude models, Argon above Opus only (round 1; the new inputs' Opus line has no verdict, Note 4), for Neon no verdict was registered; none is the paper's model | `GR`, `AR`, `R32` and `NR` `confirmatory.5a.family`, `5b.levels.L3.verdict`. Each clause is what a verdict says: Rejected rules out a 3-point gain, Inconclusive does not |

## Backup 8: Gemini 4 Argon on the 24 inputs it had not seen (Note 4)

Registered 2026-11-19 20:54 IST, after round 1 of Note 3 was seen and before any call on these rows (`PREREGISTRATION_GEMINI.md` Note 4, R1 to R4; `DEV` item 75). `R32` = `tools/live_policy/results_semantic_1113/gemini_argon_r32_1119/results.json` (rounds 3 and 2, 24 rows, 2 members each); `A36` = `.../gemini_argon_all36_exploratory/argon_minus_{haiku,opus,flash}.json` (exploratory, R3: computed after the fact, on all 36 inputs, so they hold the 12 seen before Note 4). Slot: `slots.json` `argon_r32` (`fill_slots_part3.py`). The builder stops (`argon_check_facts`) unless: 24 rows, 48 of 48 parsed, 12 clusters, 2 members, rounds 2 and 3 finished; R2a's one-sided p is not below 0.05 and its interval holds zero (so the registered sentence is the "again not detectably above" one); R2b is Rejected against D with the upper end under the margin; round 1's L3 line was Inconclusive; on all 36 inputs minus Haiku (L2) and minus Flash (L2, L3) hold zero and minus Opus (L2) is above zero.

| Statement | Source |
|---|---|
| Round 1 left Argon against Haiku at L2 at +13.6 with an interval from −1.4 to +28.5; the check tests that one contrast on the 24 other stages of the same 12 runs, 2 members each, 48 of 48 parsed; registered after round 1 was seen | Note 4 ("Why", R1, R2a); `AR` `confirmatory.5a.family.claude-haiku-5-5|L2` (round 1); `R32` `analysis_set.confirmatory.{rows,members,ok}`, `members_per_row` |
| R2a: Argon minus Haiku at L2 +5.4 [−2.8, +13.5], one-sided p 0.0906 before Holm; the registered sentence "On the 24 other stages of the same 12 runs Gemini 4 Argon was again not detectably above Haiku at naming objects" | `R32` `confirmatory.5a.tables.claude-haiku-5-5.L2.{mean_diff,ci,p}` (the one-sided p before Holm). Note 4 says R2a ignores the file's `found` flags and its 5a sentences, which apply Holm over four; the deck does too. The sentence is Note 4's (p not below 0.05) |
| The other three contrasts on the new inputs (Opus L2 +18.7, Opus L3 +1.1, Haiku L3 +0.9), reported with intervals and no verdict | `R32` `confirmatory.5a.tables.<model>.<L>`; Note 4 ("Reported with intervals, no verdict"). Shown in grey; the deck gives them no reading |
| R2b: the registered rule at L3 reads Rejected; Argon minus the region trade +0.4 [−2.1, +2.8], margin 3; own score 4.9% beside 4.7% (own labels swapped), 4.6% (the trade), 7.2% (prior's labels at its places) | `R32` `confirmatory.5b.levels.L3.{verdict,delta,ci_upper_named,model_own_score}`, `.comparators.{B5,D,B3L}.{comparator_own_score,mean_diff,ci}` |
| Two questions were tested (R2a and R2b), each at α = 0.05 | Note 4 R2 ("the slide says that two were tested") |
| Round 1's L3 line was Inconclusive; the new inputs give Rejected | `AR` `5b.levels.L3.verdict` (round 1); `R32` as above |
| Exploratory, all 36 inputs: Argon minus Haiku at L2 +8.1 [−1.3, +17.2]; minus Opus at L2 +18.3 [+11.7, +25.9]; minus Flash −2.7 [−6.7, +1.3] at L2 and −2.1 [−5.1, +1.1] at L3 | `A36` `levels.<L>.{diff,interval,rows}` (all three ran the author's loop; two-sided exact test; `gemini_pair.py`). Marked exploratory on the slide, with "which hold the 12 seen before Note 4" (R3) |
| The fixed sentence of R2b: "Gemini 4 Argon did not beat a trade of region contents by the 3-point margin." | `R32` `confirmatory.wording[5]`; Note 4 R2b. The builder checks the file's line (`argon_check_facts`) |
| All three Gemini models ran the author's loop, but it behaved very differently: about 4 calls a member for Argon, 34 for Flash | `DEV` item 73 ("about four calls a member, where Flash took about 34"); `PIN` `gemini_calls` |
| Argon is the second of Google's Gemini 4 line; not the paper's model | Note 5; `R32` `confirmatory.wording` |
| Gemini 4 Neon, the last run, is on backup 15 | `PREREGISTRATION_GEMINI.md` Notes 6 and 7; `DEV` item 76. Note 6 N3's sentence is on slide 16 |

## Backup 9: where the guesses land

| Number | Source |
|---|---|
| 3.0% v 0.5%, 10.1% v 2.0%, 23.8% v 6.3% | `NUM` `precision_pooled:official:final:{0.5,1,2}m`, `precision_pooled:placebo:final:{0.5,1,2}m` (0.0304, 0.0052; 0.1007, 0.0203; 0.2383, 0.0628); `WRITEUP` §4 "Precision and agreement" |
| About 6 times | `WRITEUP` §3 "Precision" (3.0% against 0.5%, 6 times) |
| 97% miss by more than 0.5 m | Derived: 1 − 0.0304 |
| 853: 1.4% v 0.6%; 871: 4.2% v 0.4% | `NUM` `precision05:official:00853:final` (0.0139), `precision05:placebo:00853:final` (0.0062), `precision05:official:00871:final` (0.0416), `precision05:placebo:00871:final` (0.0040); `WRITEUP` §3 "Precision" |
| Counted runs, per (stage, member) guess | `WRITEUP` §8 "Counting" |

## Backup 10: same rules as the paper

| Number | Source |
|---|---|
| 85 and 66 stops | `CC` `00853.use_rule.reached`, `00871.use_rule.reached` |
| October's other arms on 853 at 10%, 50%, 100%: ASP + filter 14.8, 48.3, none; random guesses 13.8, 43.9, none (a line moved here from slide 7's grey rows) | `PC` apr B, scene 00853, arms filter_only and placebo, `stage_value_x100.mean`; none = 0 of 3 runs reach 100% (rows under "Slides 7 and 9") |
| Stand-in for the author's hand-driven tour: navmesh paths, same mapper | `PLAN` §B1 (Reference row), §B7 (Amendment 1: the tour moves onto navmesh paths); `PREREG` Amendment 1 |
| 5 of 5 runs on 853, 4 of 5 on 871 ran to their natural end | `B13` `00853.n_primary` (5), `00871.n_primary` (4), and the count of `end_times_s` (5 and 5); `N13` item 2 and "Budgets" |
| 1 run on 871 stopped at the 250 m path cap and is left out of the median | `B13` `00871.capped_runs` (`e7_00871_s44_frontier_end`, end 1,740.8 s); the cap: `PREREG` §2a and Amendment 2 A2.1, A2.3; `DEVIATIONS_NOVEMBER.md` item 63. The builder's `PATH_CAP_M` holds the 250 |
| DeepSeek; Gemini 2.5 Pro | `PLAN` §B1 table, LLM row |
| The paper gives no budget value; 10, 50, 100% | `PLAN` §B1 (Budget row); `PREREG` §1 |
| 632 s and 1300 s | `PC` `meta.budgets` (632.175, 1300.252); `B13` `<scene>.primary_s`, `primary_rule` ("median"); rule in `PREREG` §4 and Amendment 2 A2.3 (primary B = median of the valid runs that logged "Exploration complete"); `N13` "Budgets". The 11-12 value for 871, 809.084 s, was the registered fallback (`B13` `00871.b_1112_s`); it is superseded |
| 63, 316, 130, 650 s | Derived: 10% and 50% of the two budgets, whole seconds |
| 871's budget is about twice 853's | Derived: 1300.2523 ÷ 632.1751 = 2.06; the builder stops if the ratio is outside 1.9 to 2.1 (`PC` `meta.budgets`) |
| "Median end of the 5 frontier runs … (612 to 868 s)" on 853 | `B13` `00853.end_times_s` for the runs in `primary_runs`: 611.83 to 867.58 s |
| "Median end of the 4 frontier runs … (1043 to 1610 s)" on 871 | `B13` `00871.end_times_s` for the runs in `primary_runs` (seeds 42, 43, 45, 46): 1,043.03 (seed 45) to 1,610.48 s (seed 43); median 1,300.25 s |

## Backup 11: the reference

| Number | Source |
|---|---|
| 32% and 21% | `CC` `00853.C3.apr_a_recall_vs_hm3d` (0.3222), `00871.C3.apr_a_recall_vs_hm3d` (0.2112) |
| Repeat tour not frozen in either home; F1 0.751 on 853 and 0.771 on 871 (C2) | `C2F` `scenes.00853.f1` (0.7511) and `scenes.00871.f1` (0.7714), `frozen` false in both; `N13` item 3 and "Tours". The builder reads the newest `c2_*.json` and falls back to `N13`'s text while a rescore rewrites the folder |
| Below the 0.90 line; the reference moves by more than the paper's margins (2.7–7.9 points) | `C2F` `scenes.<scene>.below_0_90` and `reading`; `PLAN` §B3 P2 check C2; `PREREG` Amendment 2 A2.5; `N13` item 3 |
| Nvblox died partway through both first tours; each reference lacks about its last 60 s | `N12` disclosures 3 and 4; `N13` "Carried over" |
| Rooms 13 and 14, paper 6 and 9 | `CC` `C1.room_nodes`, `C1.paper_rooms` |
| Navmesh island 77 and 59 m² | `CC` `C1.start_island_area_m2` (77.00, 59.27); `N12` item 9 |
| Waypoint grid 191 and 149 m² | `CC` `C1.kept_area_estimate_m2` (191.25, 148.5); `N12` item 9 ("about 191 and 149") |
| Paper 208 and 235 m² | `CC` `C1.paper_area_m2` (207.63, 235.03) |
| Labelled floor 102 and 105 m² | `C1T` = `tools/live_policy/results_paper_compare_1113/c1_area_table.json` `<scene>.labelled_floor_m2` (102.42, 104.89) |
| Outline of all labelled geometry 213 and 253 m² | `C1T` `<scene>.footprint_hull_m2` (213.21, 252.92) |
| The paper's figure is 2.7 and 4.0 times the walkable floor | Derived: `C1T` `<scene>.paper_m2` ÷ `<scene>.navmesh_start_island_m2` (207.63 ÷ 77.00 = 2.70; 235.03 ÷ 59.27 = 3.97) |
| Within about 7% of the outline | Derived: the larger of \|paper − `footprint_hull_m2`\| ÷ `footprint_hull_m2` over the two homes (2.6% and 7.07%), rounded to a whole per cent; the slide says "about" because 7.07 is just over 7 |
| "We do not know how the paper measured area" | `N12` item 9; `PREREG` §3 (check C1) |

## Backup 12: a hit and a miss, on one real stage

From `figures/stage_numbers.json`, made by `figures/make_stage_picture.py` from the row's observed graph, the robot's path, `tools/live_policy/semantic/truth/00871_*` and one saved Claude member. The 2 m scale bar is drawn in the figure.

| Number | Source |
|---|---|
| Run `e1_00871_s42_official`, stage 8 (script: bathroom and bedroom open; 65 open classes) | `semantic/sample_frame.txt` (round 1, row `e1_00871_s42_official_st08`); `stage_numbers.json` `run`, `stage`, `open_types`, `open_classes`; rules `SEM` §5.5 |
| The guesses: Opus member 0, a "bed" at (6.3, −3.4) that hits and a "toilet" at (−4.3, 8.5) that misses | `/Users/sher/project/cvp/replay_outputs/m4/claude-opus-5-5/effort_medium/e1_00871_s42_official_st08/member_0/parsed_graph.yaml` (outside the repo, as the CSV's `mem_*` rows cite `replay_outputs/m4`); read with `semantic/extract_preds.py` `members_for`; the hit or miss is the scorer's own `semantic/score_levels.py` `l3_hit` (the script asserts it); `stage_numbers.json` `guess_hit`, `guess_miss`. The two guesses were picked by hand from that member's L3 items (it has 2 hits among 9) |
| 0.5 m reach | `SEM` §5.1; `stage_numbers.json` `reach_m` |
| L1, L2, L3 and what a hit needs; L4 secondary | `SEM` §1, §5.5, §8, §11 |
| Base rate: random guesses score 87.5%, 60.6%, 1.7% (L1, L2, L3) | `RE` `models.placebo.analysis.levels.<L>.model_cluster_scores` (mean of 12); CSV `e_placebo_L1_score`, `e_placebo_L2_score`, `e_placebo_L3_score` |

## Backup 13: two facts that cut against the registered line

| Number | Source (file, path) | CSV key |
|---|---|---|
| Opus at L3: the top of the interval 2.95 points; margin 3 | `RC` `family.hypotheses.claude-opus-5-5|L3.ci_upper_named` (0.029496) × 100, `.delta` × 100 | `c_opus_L3_Dci_hi`, `c_opus_L3_margin` |
| 15 reruns of the region trade (D), made after the result: 2.83 to 2.98 points | `S1/independent_recompute/margin_summary.json` `summary.claude-opus-5-5|200` (10 runs, `ci_high_min` 0.028349, `ci_high_max` 0.029792) and `|5000` (5 runs, 0.028866 to 0.029105), `below_0.03`; `DEVIATIONS_NOVEMBER.md` item 55 (D is the randomised control; "deviation 55") | `rc_opus_hi_min`, `rc_opus_hi_max`, `rc_opus_below`, `rc_opus_runs200`, `rc_opus_runs5000` |
| Haiku at L2: 8.2 points above random guesses, p 0.014; one contrast, not adjusted, exploratory (no verdict rests on it; the closing slide says the same) | `RC` `models.claude-haiku-5-5.analysis.levels.L2.comparators.B1.{mean_diff,p}` (0.0821 × 100; interval [+1.1, +14.9]); the p is that contrast's own, not Holm-adjusted | `c_haiku_L2_B1_diff`, `c_haiku_L2_B1_p` |
| "A prior from 179 other houses, making as many claims as the model, scored above both models at naming objects (L2)" | The L2 contrasts against B3 on slide 13, both models, intervals wholly below zero; B3 "making as many claims as the member did": `SEM` §9 (B3 row and "Claims"); 179 houses `SEM` §9 | CSV `rule_houses` |

## Backup 14: what a perfect score could have shown: a ceiling at L1 and L2

Exploratory, made on 2026-11-19 after the result (`DEV` item 71 (a)). Points = 100 × the value in the file. The slide's table is `X19` `ceiling.json`, `models.<m>.<L>.comparators.B3`.

| Number | Source (file, path) | CSV key |
|---|---|---|
| The prior's own score: Opus L1 91.2%, Haiku L1 100.0%, Opus L2 93.4%, Haiku L2 93.7% | `comparator_score` | |
| The most a perfect model could gain: 8.8, 0.0, 6.6, 6.3 points | `max_gain_perfect_model` (100 minus the comparator's score) | |
| The best p after Holm for six tests: 0.750, 1.000 (L1); 0.047, 0.188 (L2) | `perfect_model.p_min_holm6` (the smallest p the exact one-sided sign-flip test could return for a model at 1.0 in every member, `semantic/stats.py`, times 6) | |
| Supported possible: no, no, yes, no | `perfect_model.can_reach_alpha` (guard `blind_facts`: L1 false for both, L2 true for Opus only) | |
| At L3 a perfect model could gain 96 points over the region trade; Opus's interval ends at 2.95 against a margin of 3; Haiku's at 2.36 | `X19` `ceiling.json` `models.<m>.L3.comparators.D.max_gain_perfect_model` (0.9625, 0.9637); `RC` `...L3.comparators.D.ci[1]` | `c_opus_L3_Dci_hi` |

| Number | Source (file, path) | CSV key |
|---|---|---|
| Detectable difference 5.7 (L1), 5.2 (L2) | `S1/exploratory/mdd_table.json` `levels.{L1,L2}.mdd` (0.0571, 0.0524) | `mdd_L1_mdd`, `mdd_L2_mdd` |
| Margin 5.0 | same file, `levels.<L>.delta` (0.05) | `mdd_L1_delta`, `mdd_L2_delta` |
| 80% power | same file, `power` (0.8) | |
| "A true gain equal to the margin would be found less than 80% of the time at L1 and L2" | Read from the two rows above: detectable difference (5.7, 5.2) above the margin (5.0) |
| "Rejected was within reach at each level" | `SEM` §10 "Detectable difference" (the interval half-width shows whether Rejected is within reach); half-widths 0.0375, 0.0357, 0.0071 below the margins 0.05, 0.05, 0.03: same file, `levels.<L>.half_width` | `mdd_<L>_hw` |
| Gains up to 2.95 (Opus) and 2.36 (Haiku) points at L3 not ruled out | upper ends of the L3 intervals against D: `RC` `...levels.L3.comparators.D.ci[1]` (0.029496, 0.023563) × 100 | `c_opus_L3_Dci_hi`, `c_haiku_L3_Dci_hi` |
| (note) No L3 row; its registered figure is 1.1 points and comes from the random guesses' contrast (B5 − D) | `S1/exploratory/mdd_table.json` `levels.L3.{mdd,contrast}` (0.0109, "B5-D"); `SEM` §10 "Detectable difference"; RESULTS §10 | `mdd_L3_mdd` |

## Backup 15: Gemini 4 Neon, the last run (Notes 6 and 7)

Registered 2026-11-19 21:05 IST, after the Flash and Argon results were seen and before any call on this model; Note 7 (2026-11-20 00:39 IST, before any output was scored or read) added one row so that round 3 was whole (`PREREGISTRATION_GEMINI.md` Notes 6 and 7; `DEV` item 76). `NR` = `tools/live_policy/results_semantic_1113/gemini_neon_1119/results.json` (rounds 1 and 3, 24 rows, 2 members each); `NP` = `.../gemini_neon_1119/neon_minus_{flash,argon}.json` (exploratory, on the rows each pair ran). Slot: `slots.json` `neon_replay` (`fill_slots_part3.py`). Note 6 makes the rule at L3 the ONE confirmatory hypothesis; the 5a table is reported with intervals and no verdict, so the deck ignores `NR`'s `found` flags and its 5a sentences. The builder stops (`neon_facts`) unless: 24 rows, 48 of 48 parsed, 12 clusters, 2 members, rounds 1 and 3 finished; the L3 verdict is Inconclusive against D (interval holds zero and reaches the margin); the prior's labels at Neon's own places (B3L) score above Neon; Neon is below Flash and Argon at L2 (intervals below 0); at L2 Neon is below the prior and its lead over random guesses holds zero; the Note 6 N3 sentence is in the registration word for word.

| Statement | Source |
|---|---|
| Gemini 4 Neon, released 18 November; the student's choice for the last run; the author's loop; rounds 1 and 3 (24 inputs), 2 members each, 48 of 48 parsed | Note 6 (Why; N1); `DEV` item 76; `NR` `analysis_set.confirmatory.{rows,members,ok}`, `members_per_row`, `finished_rounds` |
| "Registered after the Flash result and Argon's round-1 result were seen, while Argon's second run was under way and unscored" (Note 6); one input was added before any output was scored, so that round 3 was whole (Note 7) | Note 6 ("What had been seen": the Flash and Argon round-1 results seen, Argon's new-input run under way and unscored); Note 7; `DEV` item 76 |
| All three models ran the author's loop, but it behaved very differently: about 4 calls a member for Argon, 34 for Flash (in the exploratory Neon-minus-Flash and Neon-minus-Argon note) | `DEV` item 73; `PIN` `gemini_calls` |
| The rule at L3 is Inconclusive: Neon minus the region trade +2.9 [−0.4, +6.3], margin 3 | `NR` `confirmatory.5b.levels.L3.{verdict,delta,ci_upper_named}`, `.comparators.D.{mean_diff,ci}`; `confirmatory.wording[5]` |
| Not Supported: the prior's labels at Neon's own places score higher (10.2% against Neon's 8.7%); Neon minus that control −1.5 [−4.1, +1.3] | `NR` `5b.levels.L3.comparators.B3L.{comparator_own_score,mean_diff,ci}`, `model_own_score`. Supported needs Neon above all three controls (Note 6 N2) |
| Own score 8.7% beside 7.6% (own labels swapped), 5.7% (the trade), 10.2% (prior's labels at its places) | `NR` `5b.levels.L3.comparators.{B5,D,B3L}.comparator_own_score` |
| Neon minus Opus +8.5 [−1.1, +18.0] (L2), +3.3 [−1.4, +8.6] (L3); minus Haiku +0.6 [−10.0, +12.0] (L2), +4.0 [−0.4, +8.5] (L3): reported, no verdict | `NR` `confirmatory.5a.tables.<model>.<L>.{mean_diff,ci,model_mean,other_mean}`; Note 6 N2 |
| Exploratory: Neon minus Flash −10.1 [−13.1, −7.3] (L2), +1.5 [−1.5, +5.0] (L3); minus Argon −7.3 [−13.0, −1.8] (L2), +3.7 [−1.3, +8.9] (L3) | `NP` `levels.<L>.{diff,interval,rows}` (all three ran the author's loop; two-sided exact test; `gemini_pair.py`) |
| Exploratory: at L2 Neon scores 74.3%, below the prior (92.5%; −18.3 [−21.2, −15.4]); random guesses 67.3% (+6.9 [−0.5, +14.3]) | `NR` `5b.levels.L2.model_own_score`, `.comparators.{B3,B1}.{comparator_own_score,mean_diff,ci}` (exploratory under Note 6 N2) |
| Not the paper's model | `NR` `confirmatory.wording` (each line says it) |
| Reported with no verdict, not on the slide: the wrong-house gate at L1 p 0.0625 (no pass) and L2 p 0.0156 (pass), 6 pairs | `NR` `confirmatory.5c.wrong_house_gate` |

## Backup 16: M2 varied place, not meaning

From `M2S` `analysis.main.all` (score `ig − 0.2·d`; Spearman per stage; mean over 24 runs; 95% interval from the bootstrap over runs). Arm names on the slide, with the registered names: True objects = F1; Room type only = F-room; Moved: DeepSeek / Haiku / Opus = F3 with that model's error sample (DeepSeek's arm is exploratory); Random guesses = F5; No guesses = F6; All true objects = F0 (`M2` §4). The yardstick is `Ucone`, the unmapped objects a candidate could see inside the camera cone, past walls (`M2` §3). The half-of-the-gain rule: `M2` §6.

| Number | Source (path in `M2S`) | CSV key |
|---|---|---|
| ρ: True objects +0.284; Room type only +0.089; Moved (DeepSeek, Haiku, Opus) +0.046, +0.060, +0.036; Random +0.065; No guesses −0.028; All true objects +0.048; with intervals | `analysis.main.all.arm_mean_rho.<arm>.{mean,lo,hi}` | `m2_<arm>_mean`, `_lo`, `_hi` |
| True objects beat random guesses by 0.218; half is 0.109 | `analysis.main.all.differences.A.mean`; half = A ÷ 2 (derived) | `m2_A_mean` |
| "Not shown sufficient, on a provisional yardstick" (all four arms: three F3, F-room); "no arm does" | `analysis.main.all.reading.verdicts`; `reading.A_separates` true; rule `M2` §6 | |
| (script) 384 stages, 24 runs | `counts_all_stages.n_stages`; `analysis.main.all.n_runs` | `m2_f0_ig_zero_of`, `m2_runs` |
| (script) Each move drawn from the model's error sample | `M2` §4 (F3-m: "a distance drawn with replacement from the sample") |
| (script) Moved arms 0.036 to 0.060: no detectable gain over random guesses; room type only 0.089 | `analysis.main.all.differences.{B_deepseek,B_haiku,B_opus}` (intervals reach +0.009 for Haiku and below for the others); `C` |
| (backup 5) All true objects −0.017 (−0.031 to −0.004) against random guesses | `analysis.main.all.differences.F0-F5.{mean,lo,hi}`; `M2` §7 | `m2_F0F5_mean` |
| Title: M2 varied place, not meaning; moved true objects show no detectable gain | `M2` §3 (the yardstick counts unmapped objects in view whatever their label, `PREREGISTRATION_M2.md:31`) and the cut arms F2 and F4 and the error sweep (`PREREGISTRATION_M2.md:91`), as `REVIEW` finding 6; the three moved arms' differences from random guesses (`differences.B_*`) have lower bounds below 0 (guard in `factorial`) |
| All true objects (exploratory): the gain never passes 2.0 bits, like the no-guess arm's; other arms reach 4.75 to 5.5; the two correlate at 0.64 (382 stages) | `AT` `bits_cap` (2.0), `arms.F0.max_ig` and `arms.F6.max_ig` (2.0 each), `arms.F0.above_cap` and `arms.F6.above_cap` (0), `arms.{F1,F3-*,F5a,F5b,F-room}.max_ig` (4.75 to 5.5), `spearman.{mean,n_used}` (0.635, 382); slot `all_true`. Exploratory (`DEV` item 71 (d)) |
| "With identical members the score reads mainly where the two observed maps disagree" | The interpretation given for this pass and in `REVIEW` finding 6 (mechanism inferred; `tools/decision_replay_reference/calculate_uncertainty.py:269-333` draws the same perturbation noise for every graph, so equal graphs cancel). `AT` holds the cap and the correlation, not this sentence |

## Backup 17: Gemini 3.8 Flash, the exploratory lines

Moved from slides 14 and 15 in pass 3 (`flash_extra_slide`); built from `GR` through `gemini_facts`. Every line is exploratory: the registered result is on slides 14 and 15.

| Statement | Source (path in `GR`) |
|---|---|
| At L2 Gemini scores 78.3%; the prior, making as many claims, 90.7% (−12.4 [−18.5, −6.3]), about 12 points above; random guesses 59.6% (+18.6 [+12.8, +24.4]) | `confirmatory.5b.levels.L2.{model_own_score}`, `.comparators.{B3,B1}.{comparator_own_score,mean_diff,ci}`; exploratory under `PREREGISTRATION_GEMINI.md` §5b (as the row on slides 14 and 15) |
| It passes the wrong-house check at L1 (p 0.031) and L2 (p 0.016), 6 pairs | `confirmatory.5c.wrong_house_gate.{L1,L2}.{p,n_pairs}`; backup 1 |
| Gemini also made more guesses per member; 5a does not adjust for that. Same limits as slide 14. At L1 and L2 the prior sits at the ceiling | As the slide 14 row; `PREREGISTRATION_GEMINI.md` §5a, §6 (last bullet) |

## Backup 18: control arms, equal-time cells and seconds per metre, with no verdict

From `CTL` and `paper_compare.json` (readout 1) and `RSJ` `readout3_sec_per_m`. A5.6: these decide nothing; the reading is on S. Cells: object F1 × 100 (stage value) at 50% and 100% of B = 632.18 s, mean [min–max], n, against the scripted reference (apr) and the human labels (hm3d).

| Statement | Source |
|---|---|
| ASP with the LLM's guesses (`official_nov`), apr 50%: 51.1 [45.7–61.5] n=3; 100%: 61.6 [60.3–62.9] n=2 of 3; hm3d 50%: 26.7 [24.5–30.6] n=3; 100%: 34.4 [33.1–35.7] n=2 of 3 | `paper_compare.json` cells, arm `official_nov`, variant B, `stage_value_x100` (hm3d read through `paper_cells(slots, "B", "hm3d")`) |
| Random guesses (`placebo_nov`): apr 43.2 [27.1–52.3], 58.2 [41.5–66.8]; hm3d 21.0 [13.1–25.3], 30.8 [23.2–35.0], n=3 each. No guesses (`observed_only_nov`): apr 30.9 [18.8–37.4], 35.7 [19.3–49.1]; hm3d 13.8 [10.9–16.2], 16.6 [10.3–24.8], n=3 each | `RSJ` `readout1_cells.<arm>.<ref>.{50,100}.stage` (the builder checks them against `paper_compare.json`); `NOTES` readout 1. Never pooled with October's `placebo` arm |
| Seconds of navigation time per metre: ASP 5.77 [5.36–6.04] n=3; random guesses 5.89 [5.59–6.09] n=3; no guesses 7.14 [7.00–7.38] n=3; our frontier 6.98 [6.40–7.84] n=5 | `RSJ` `readout3_sec_per_m` |
| Readout 2 marks, and "decide nothing" | `RSJ` `readout2_equal_path.labels`; `PREREG` A5.5, A5.6 |
| "From slide 8": chance 1 time in 20; two random-guess runs above two LLM runs; the best random-guess run ties the best LLM run (30.4); the gap in the means from one low random-guess run; the controls ran from 11-19; dropped replies; the sleep; 4.4% against 29.4%; 7.1 s per metre as slowly as frontier (7.0); the no-guess score barely grows with distance on average, seed 43 keeps growing (+11.1 / +8.4) | The rows of slide 8's section above; per-run growth from `paper_compare.json` `runs[].stages[]` (guard) |
| Seed 43 of the LLM arm read other ways (deviation 64) decides nothing: without it the mean S is 57.6 and 29.7, and both statements stand | `RSJ` `other_readings_of_seed_43[].official_nov_mean_S` (both readings 57.64 and 29.72); the builder re-derives the statements without seed 43 and stops if they change |

## File properties

The .pptx `author` and `lastModifiedBy` are set to "ASP replication, end-sem" in the build (`prs.core_properties`), so python-pptx's default name does not appear.

## Values not matched to a CSV key by value

These are not in `numbers_part3.csv`; each has its file and path above.
- Placement "used / all" sums (349, 894, 1,859, 1,348, 1,660) are derived; the left-out counts match `err_<m>_left`.
- Hint, object counts (150 of 230, 146 of 219): `records_*.json` as on backup 3.
- Random-guess validity block (68.9%, −0.2 points): `S1/exploratory/validity.json` `placebo`. The CSV has no placebo validity rows.
- Points figures (8.2, 5.7, 5.2, 5.0, 2.95, 2.36, 2.83, 2.98, and the slide 13 cells) are 100 × a CSV value.

## Not used on a slide, and why

- **The pilot base rates** (88%, 82%, 56%) and room mix: `SEM` §2 lists them as seen before the hash. The deck shows the frozen-rule chance level instead: the random guesses' own scores.
- **Gemini's verdicts** (exploratory, 8 rows): "Inconclusive" at all three levels; not shown. Slides 14 to 16 show the registered runs instead; backup 2 shows its October placement-error median.
- **Difference against the random-guess placebo at L3.** The placebo is a registered comparator at L1 and L2 only (`SEM` §9). At L3 the slide shows the model's score beside the placebo's score.
- **Validity-layer terms** (Brier, vote, τ) stay in `slots.json` and here, not on the main slides.
- **Two clauses of the independent recompute's note, not used as given.** "Took 41 to 45 stages": `nov_controls.runs[].end_stage` reads 40, 43 and 39 for the no-guess runs. "Run two to three days apart": A5.6 and `NOTES` say "two days later"; the slide gives the dates the files give (the ASP runs of 11-17 and 11-18, the controls from 11-19). "The pipeline hardly explores": no file measures exploration; the closing sentence says the map barely grows with distance, read from the F1 at 50 m and 100 m.
