# Results

This is the one map of results for every experiment. It separates completed evidence from superseded diagnostics, and lists the errata. Detail JSON stays under `tyrone_mirror/runs/` (September) and `tools/live_policy/` (October and November). The dated deviation logs explain each correction. The three per-scene matrix static replays are mirrored with checksums in `tyrone_mirror/runs/matrix120m_scoring/STATIC_REPLAY_SHA256SUMS`.

Read the [Errata](#errata) before quoting any September number.

| Period | What | Where |
|---|---|---|
| September | Replication, DeepSeek 120 m matrix, Phase 13, Gemini campaign | sections below, from "Run families" |
| October | Live placebo-controlled campaign (E1-E3, steps 6-8) | [October live campaign](#october-live-campaign) |
| November | Scores on the paper's scale | [November paper-scale scores](#november-paper-scale-scores) |
| November | Is the guesses' meaning right? (Part 3) | [Part 3](#part-3-is-the-meaning-right-november-13-and-19-nov) |

## Run families (September)

| Family | Runs or artifacts | Status | Primary result |
|---|---|---|---|
| Initial ASP gates | `scene00069_seed42_v4`, clean v3, and early probes | Completed | Baseline pipeline, evaluator, and artifact replay gates passed. |
| 00069 low-effort probe | `scene00069_seed42_25m_20260914_v3` | Completed | Tracked-graph AUC P=0.671, R=0.241, F1=0.352, normalized GED=1.075. |
| 00069 high-effort probe | `scene00069_seed42_high_effort_v5_matched` and `_full` | Completed | Matched AUC P=0.655, R=0.198, F1=0.302, normalized GED=1.189; full AUC F1=0.329. |
| Calibration collection | `scene00069_seed42_25m_20260914_v3`, `scene00573_seed42_calib_high32k`, `scene00853_seed42_calib_high32k`, `scene00871_seed42_calib_high32k` | Completed | Four-scene LOSO calibration and support-policy replay. |
| Final DeepSeek matrix | `scene00069_seed42_matrix120m`, `scene00573_seed42_matrix120m`, `scene00853_seed42_matrix120m` | Completed | All three reached 120 m. The static guardrails passed, but the gain is not a filter effect (see [Errata](#errata)). |
| Phase 13 | `matrix120m_scoring/phase13_v5_20260917` | Frozen | Calibration, validator, static guardrails, decision replay, and trajectory-availability diagnostics. |
| Gemini campaign | 3 scenes x seeds 42, 43, 44, with preserved v1/v2/v6 attempts | Stopped | No Gemini block reached 120 m. Whether all 9 blocks ran is unverified (see [Errata](#errata)). |
| Gemini v6 offline analysis | `prospective_gemini/.../offline_analysis_20260922/block_00069_42_v6` | Completed | Author-faithful evaluator, static policy replay, decision replay, validator taxonomy, and ledger economics. |

## 00069 short probes

The earlier 00069 short-run work set the baseline and exposed the main failure modes.
- Low-effort v3, 25 m: tracked-graph AUC P=0.671, R=0.241, F1=0.352, normalized GED=1.075.
- High-effort v5, matched budget: P=0.655, R=0.198, F1=0.302, normalized GED=1.189. It did worse.
- **Caveat.** v3 against v5 is not a clean estimate of reasoning effort. Parser survival and token settings differed between the two runs. Read it as a configuration result.

## Final DeepSeek matrix

These are 120 m-capped path-normalized AUC values from the corrected static-policy replay, scored with the **canonical evaluator** (`tools/asp_offline/evaluator.py`), not the author-faithful tracked-graph evaluator. The exact keys are `path_normalized_auc_capped.official` and `path_normalized_auc_capped.support_threshold_tau_1.0`. `tau=1.0` means all four members of each graph track support the prediction. Per-scene sources: [00069](../tyrone_mirror/runs/matrix120m_scoring/scene00069_extension_policy_replay.json), [00573](../tyrone_mirror/runs/matrix120m_scoring/scene00573_extension_policy_replay.json), [00853](../tyrone_mirror/runs/matrix120m_scoring/scene00853_extension_policy_replay.json).

| Scene | Official F1 | `tau=1.0` F1 | Relative F1 gain | Official GED | `tau=1.0` GED | Recall official -> filtered |
|---|---:|---:|---:|---:|---:|---:|
| 00069 | 0.4789 | 0.5218 | +8.96% | 0.8969 | 0.8254 | 0.4747 -> 0.4739 |
| 00573 | 0.3980 | 0.4349 | +9.29% | 0.9576 | 0.8877 | 0.3754 -> 0.3743 |
| 00853 | 0.4578 | 0.4957 | +8.28% | 0.8561 | 0.7930 | 0.4461 -> 0.4449 |

Reading, as corrected (WRITEUP §9 erratum 2; see [Errata](#errata)):
- `tau=1.0` keeps 19 of 8,943 predicted nodes. Its F1 (0.5218 / 0.4349 / 0.4957) scores within 0.0002 of the observed map alone (0.5219 / 0.4351 / 0.4957).
- The gain therefore shows that the guesses hurt the map. It does not show that the filter adds value.
- Recall stays near 99.7% of full-graph true positives because the unchanged observed map dominates that count. It is a full-graph measure, not predicted-only retention.
- This is a static graph result and a backend characterization, not live-policy generalization.

Guardrails passed on all three scenes. The registered limits were absolute F1 loss at most 0.05 and relative normalized-GED increase at most 10%; observed normalized GED fell. The frozen Phase 13 report records 752 expected completion slots, 686 available, 667 accepted, 19 rejected and 66 missing (from the 27 September closeout report; the frozen Phase 13 JSON below is the source and was not rechecked here).

## Calibration and risk term (September reading)

- Calibration does not improve the static result at the useful endpoint, and it is harmful at some intermediate thresholds.
- The risk term is nearly inactive or counterproductive: it either moves few viewpoints or picks counterproductive ones.
- Corrected decision replay shows a descriptive filtering effect on novel reference-object visibility. It does not replay ROS reachability or a live counterfactual trajectory.
- The October audit retired both (WRITEUP §9 erratum 3; [Errata](#errata)).

## Phase 13 disposition

The frozen four-scene calibration corpus contains 2,829 held-out rows, 23 positives, and 16 room rows. Pooled calibration improves overall Brier score but room calibration is too small to support a room-level claim. Static guardrails pass for all three matrix scenes. The tested guardrail policy is `filter_plus_support_threshold_calibrated_tau_1.0`, with absolute F1 loss at most 0.05 and relative normalized-GED increase at most 10%; the headline table above uses raw support alone. The false-positive detour gate is `NOT IDENTIFIABLE`, robot collisions are `NOT INSTRUMENTED`, and combined usefulness is `NOT ESTABLISHED`.

The exact frozen artifact is [phase13_diagnostics_v5.json](../tyrone_mirror/runs/matrix120m_scoring/phase13_v5_20260917/phase13_diagnostics_v5.json), with plots and checksums beside it.

## Gemini v6

The final block reached 19.5 m over seven completed stages and one partial stage. Author-faithful tracked-graph metrics (**`tools/evaluator/`**) at stage 6 were P=0.692, R=0.336, F1=0.452, normalized GED=1.109. Path-normalized AUC through 19.5 m was P=0.757, R=0.184, F1=0.283, normalized GED=1.119.

The best static completion-policy AUC was P=0.769, R=0.184, F1=0.284, normalized GED=0.937. Of 55 available completion files, all were accepted; 35 predicted nodes were removed, consisting of 30 AABB conflicts and 5 impassable crossings. Stage 2 scene 0 member 0 is missing; stage 7 is entirely partial.

The null decision replay matched the official selected pose at all seven completed stages. Filter-only moved one stage. Calibrated support moved five stages, with mean displacement 2.559 m and maximum 5.920 m. The combined risk arm moved 0/7 stages at beta=0, 2/7 at beta=1, and 6/7 at beta=5 or beta=20. These are replay measurements without live ROS reachability.

The ledger settled 898 requests for $18.552664. Reservations summed to $65.749854. No new run should be inferred from the remaining allocation.

## October live campaign

Pilot-status live runs of the author's pipeline on HM3D scenes 00853 and 00871 (human-annotated), seeds 42-44, 60 m path budget. Dates: 28-30 Oct 2026. Every result carries **pilot status**: one E1 cell is missing and the code changed after the E1 freeze.

Read these, in order:
- [WRITEUP.md](../tools/live_policy/results_2026-10-31/WRITEUP.md): the write-up (frozen, hash-pinned). §1 gives the answer, §9 the errata, §12 steps 6-8.
- [run_table.md](../tools/live_policy/results_2026-10-31/run_table.md): every run, status, path, hours, cost.
- [tests.md](../tools/live_policy/results_2026-10-31/tests.md): every registered test with d, p, intervals and MDE.
- [numbers.csv](../tools/live_policy/results_2026-10-31/numbers.csv): every number in the write-up with its source file and key.
- [DEVIATIONS.md](../tools/live_policy/results_2026-10-31/DEVIATIONS.md): numbered departures from the pre-registrations.

Arms: `official` (DeepSeek V4.1 Flash completions), `placebo` (random guesses of the LLM's measured shape), `filter_only` (official plus our validator), `oracle_visible` (true unmapped HM3D objects). Metric: author-faithful object F1 of the robot's observed map against the HM3D annotation, as area under the curve to 60 m (WRITEUP §2).

| Experiment | Contrast | d (F1 AUC, HM3D, 60 m) | p | Reading | Source |
|---|---|---:|---:|---|---|
| E1 | official - placebo | +0.013 (permutation 95% CI -0.012 to +0.040) | 0.22 (Holm 0.44) | No detectable difference. 80% power only for about 0.024-0.028. | WRITEUP §1, §3; tests.md |
| E2 | official - filter_only | +0.003 (CI -0.037 to +0.047) | 0.86 | No detectable difference. 80% power only for about 0.044-0.051. | WRITEUP §1, §3; tests.md |
| E3 | oracle_visible - placebo, 00871 only | +0.034 | 0.10 | Smallest p a 3 v 3 test can return; no detectable difference. Registered only under deviation 26. | WRITEUP §3; tests.md |
| E3 | oracle_visible - official, 00871 only | +0.003 | 0.70 | No detectable difference; wider interval unbounded. | WRITEUP §3; tests.md |

- **Secondary result, E1.** F1 at the 60 m endpoint: official - placebo +0.043, p 0.015, positive on both scenes. Holm across the six E1 secondaries gives 0.09. At 30 m: -0.011 (p 0.58). The pacing flag marks all five counted pairs, so the arms differ in timing as well as content (WRITEUP §3).
- **Precision.** New DeepSeek guesses fall within 0.5 m of a same-label unseen object 3.0% of the time, against 0.5% for the placebo (WRITEUP §3).
- **E2 validator.** It removed 2,573 of 8,465 new guessed objects (30%); 56 of them were hits (WRITEUP §3).
- **Cells.** E1 official has 5 of 6 cells (00853/44 missing). E3 has 3 counted runs, all on 00871 (WRITEUP §2).
- **Static table on the new model [exploratory].** In all 11 runs, adding guesses lowers F1 AUC by 0.0015-0.0078. Unanimity keeps under 1% of them and scores within 0.0001 of the observed map alone (WRITEUP §5).
- **Offline audit [exploratory].** The viewpoint score has no term for whether a guess is true. DeepSeek's content moves the top-scored candidate no more than a random redraw (+0.09 m, CI -0.25 to +0.38). About 1 in 12 unseen objects counted in view of a stop reach the next map (WRITEUP §4).

### Steps 6-8 (30 Oct, $0)

Run under three pre-registrations frozen before any result (`PREREGISTRATION_BENCH.md`, `_FRONTIER_SEEDS.md`, `_DETERMINISM.md`). Full report: `docs/checkin/review_2026-10-29/STEPS_6_TO_10_OUTCOMES.md`. Source: WRITEUP §12.

| Step | Result |
|---|---|
| 6, offline bench | No rule passes, so live work stops. With exact-object guesses the best rule's regret is 15% below random guesses, against a bar of 30%. No rule shows DeepSeek's guesses beating random ones by more than two random draws differ. |
| 7, seeded frontier explorer | Neither LLM nor random guesses beat nearest-frontier exploration. Official - frontier -0.012 (CI -0.053 to +0.029, p 0.47). Placebo - frontier -0.025 (CI -0.050 to +0.002, p 0.07, Holm 0.14). |
| 8, repeat runs | Same-seed runs still split at the first stop, even with a quiet-wait snapshot. Plan at least 5 replicates per cell. |
| 9, 10 | Not run, by the plan's rule. |

## November paper-scale scores

Scores on the scale of the paper's Fig. 4 (arXiv 2510.05430v2): F1 x 100 at 10%, 50% and 100% of a time budget B, scored with the author's matching rules, plus GED from the author's gmatch4py code.

Read these:
- [paper_compare.md](../tools/live_policy/results_paper_compare_1113/paper_compare.md): the current scores (final rescore, 18 Nov; budgets 632.1751 s on 853 and 1300.2523 s on 871).
- [NOTES.md](../tools/live_policy/results_paper_compare_1113/NOTES.md): the command, budgets, checks and disclosures. The 12 Nov files in `results_paper_compare_1112/` and the 6 Nov files in `results_paper_compare/` are superseded; the `ged/` folder of the latter still feeds the rescore.
- Exploratory readouts of 19 Nov, on no registered table: [equal_path.md](../tools/live_policy/results_paper_compare_1113/equal_path/equal_path.md) (F1 at equal path length) and [budget_sensitivity.md](../tools/live_policy/results_paper_compare_1113/budget_sensitivity/budget_sensitivity.md) (other budgets); `tools/live_policy/DEVIATIONS_NOVEMBER.md`, items 66 and 71.
- Current status and open items: the README, "Where things stand". Plan: [ENDSEM_PLAN_2026-11-03.md](ENDSEM_PLAN_2026-11-03.md).

Headline: APR reference (the coverage-tour map). Cells are F1 x 100 at 10% / 50% / 100% of B (cells are means; "none" means no run reached the stage). Source: paper_compare.md, "Reference: apr".

Scene 00853, B = 632.1751 s:

| Row | Our arm | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|
| Frontier | `frontier_end` (5 runs to the end of exploration) | 12.4 (n=5) | 18.6 | 39.5 (n=5) | 46.5 | 55.6 (n=3 of 5) | 58.8 |
| ASP, October | `official` (2 runs, stop at 60 m) | 16.5 (n=2) | 34.4 | 38.7 (n=2) | 60.8 | none | 66.7 |
| ASP, November | `official_nov` (3 runs, to 105 m) | 17.2 (n=3) | 34.4 | 51.1 (n=3) | 60.8 | 61.6 (n=2 of 3) | 66.7 |
| ASP + filter | `filter_only` (3 runs, stop at 60 m) | 14.8 (n=3) | 34.4 | 48.3 (n=3) | 60.8 | none | 66.7 |

Scene 00871, B = 1300.2523 s (final; the 12 Nov scores for 871 were read at B = 809.084 s and are superseded):

| Row | Our arm | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|
| Frontier | `frontier_end` (5 runs; B is the median of the 4 that logged "Exploration complete") | 31.9 (n=5) | 29.2 | 59.2 (n=5) | 55.7 | 66.6 (n=3 of 5) | 65.3 |
| ASP | `official` (3 runs, stop at 60 m) | 33.9 (n=3) | 30.5 | none | 62.4 | none | 68.0 |
| ASP + filter | `filter_only` (3 runs, stop at 60 m) | 33.0 (n=3) | 30.5 | none | 62.4 | none | 68.0 |
| Random guesses | `placebo` (3 runs, stop at 60 m) | 31.7 (n=3) | none | none | none | none | none |

Reading:
- On 853, by the clock, November's ASP row sits above our frontier at 10%, 50% and 100%, by less than the paper's gaps (README, finding 3). By the metre the sign depends on the reference (`equal_path.md`, exploratory). The 11-12 reading that the paper's lead "does not appear" was for October's shorter runs and is superseded. The paper's own 853 values moved between versions: at the full budget frontier 48.3 (v1) to 58.8 (v2), ASP 59.0 to 66.7 (`docs/checkin/review_2026-10-29/REVIEW_B_paper_field.md`). Our ASP rows are still below the paper's ASP row.
- On 871 our cells are 1.3 to 3.5 points above the paper's where both have a cell, at a budget about twice 853's. At 750 s (`budget_sensitivity.md`, exploratory) our frontier reads 26.1 / 43.6 / 62.4, below the paper's 29.2 / 55.7 / 65.3. No ASP run of ours reaches 50% of 1300 s.
- These are not like-for-like. The paper scores against a hand-driven full-scene map. We use a coverage-tour map. ASP runs stop at 60 m of path (105 m for November's 853 runs), so late cells are none. Scenes 00069 and 00573 have no run here. paper_compare.md, "Not comparable", lists every difference.
- Treat the cells as descriptive. n is 1-5 per cell and NOTES.md lists the disclosures (for example, the repeat tour is not frozen, and the APR floor area differs from the paper's).
- The F1 readout is the stage value at the last stage at or before t; the running maximum (the author's plot rule) is reported beside it in the JSON.

## Part 3: is the meaning right? (November, 13 and 19 Nov)

Source and limits: [results_semantic_1113/RESULTS.md](../tools/live_policy/results_semantic_1113/RESULTS.md). A pre-registered, blind replay of Claude Opus 5.5 and Haiku 5.5 on 44 saved planner inputs from scenes 853 and 871, scored once by a scorer frozen beforehand, with a prior built from 179 other houses and four other comparators.

- **Registered line: "the claim fails".** All six hypotheses read Rejected, for the first half of the claim as the author put it to us (that the guesses are right in meaning), in these two houses. Opus against the other-house prior: -35.1 points at L2 (-41.3 to -29.1); against a trade of region contents at L3: +0.5 (-1.9 to +2.95), margin 3. Haiku: -24.9 at L2 (-31.5 to -18.1); +0.8 at L3 (-0.8 to +2.4).
- **What the data show.** Claude named rooms and objects no better than a prior from 179 other houses (worse at objects), and put its guesses in fitting regions no more often than a trade of regions (a gain under 3 points is not ruled out).
- **The ceiling (exploratory, 19 Nov; `results_semantic_1113/exploratory_1119/ceiling.md`).** The prior scores 91.2% (Opus's L1 rows), 100.0% (Haiku's), 93.4% and 93.7% (L2). A perfect score could not have been Supported at L1 for either model, and at L2 only for Opus (best p after Holm 0.047); the line rests on L3, where Opus's interval ends at 2.95 against the margin of 3. The comparators' own scores were not checked before the test was frozen.
- **Is it the model? Registered Gemini replay** (`results_semantic_1113/gemini_1119/RESULTS_GEMINI.md`, `results.json`; `PREREGISTRATION_GEMINI.md` with Notes 1 and 2; `DEVIATIONS_NOVEMBER.md` item 72). Gemini 3.8 Flash (the registered fallback; the paper's Gemini 2.5 Pro is no longer offered to new users), in the author's own loop, on the 36 inputs Claude saw: 4 members each, 137 of 144 parsed. Gemini minus Opus: +21.0 points at L2 (+13.5 to +28.8, Holm p 0.0010), +2.7 at L3 (-0.3 to +5.8, p 0.0381). Gemini minus Haiku: +10.9 at L2 (+1.6 to +20.5, p 0.0344), +3.1 at L3 (+0.4 to +6.0, p 0.0381). All four found: "The Claude result does not carry over to Gemini 3.8 Flash: on the same inputs Gemini 3.8 Flash names more of what is there and puts more of it in fitting regions. Gemini 3.8 Flash is not the paper's model." At L3 the registered rule reads Rejected: "Gemini 3.8 Flash did not beat a trade of region contents by the 3-point margin." Its L3 score, 7.5%, is below all three controls (8.5%, 8.7%, 11.0%). Limits: the loops differ (the author's against our port), so the contrast is of model and loop together; against Opus at L3 the interval includes zero; Gemini made more guesses per member and 5a does not adjust for that; two homes; no robot acted; the comparators at L1 and L2 sit at the ceiling. Exploratory beside it: at L2 the prior is about 12 points above Gemini; the wrong-house check passes at L1 and L2.
- **Extension of Note 3: Gemini 4 Argon** (registered after the Flash result was seen; `results_semantic_1113/gemini_argon_1119/`; `DEVIATIONS_NOVEMBER.md` item 73). Gemini 4 Argon is the second of Google's Gemini 4 line (its top model is Gemini 4 Carbon; Note 5, `DEVIATIONS_NOVEMBER.md` item 74). In the author's loop, on the 12 round-1 inputs, 4 members each, 48 of 48 parsed; 12 clusters of one row each, so the intervals are wide. Argon minus Opus: +17.5 points at L2 (+5.0 to +30.3, Holm p 0.0205), above; -0.4 at L3 (-5.7 to +4.9), not detectably above. Argon minus Haiku: +13.6 at L2 (-1.4 to +28.5) and +1.2 at L3 (-4.4 to +6.7), not detectably above. Registered rule at L3: Inconclusive (minus the region trade +0.0, -2.8 to +3.1, margin 3); own L3 score 6.2% beside 5.7%, 6.2%, 6.6%. Exploratory: Argon minus Flash on the same 12 rows -2.9 at L2 (-9.1 to +3.4) and -5.4 at L3 (-13.1 to +2.0); at L2 Argon is below the prior (96.5%). Not the paper's model. On the 24 other stages of the same 12 runs (Note 4, registered after round 1 was seen; `gemini_argon_r32_1119/`; item 75; 2 members each, 48 of 48 parsed; two questions tested): Argon minus Haiku at L2 +5.4 points (-2.8 to +13.5), one-sided p 0.0906, so "again not detectably above Haiku"; the registered rule at L3 reads Rejected (minus the region trade +0.4, -2.1 to +2.8, margin 3; own score 4.9% beside 4.7%, 4.6%, 7.2%), where round 1 was Inconclusive. Exploratory on all 36 inputs (the loop behaved very differently between Argon and Flash, about four calls a member against about 34, item 73; they hold the 12 seen first): minus Haiku at L2 +8.1 (-1.3 to +17.2), minus Opus +18.3 (+11.7 to +25.9), minus Flash -2.7 at L2 and -2.1 at L3, both holding zero. Neither Gemini model so far was found to beat a trade of regions at L3 (Flash Rejected; Argon Inconclusive on round 1, Rejected on the new inputs).
- **Gemini 4 Neon, the last run** (Notes 6 and 7, registered after the Flash result and Argon's round-1 result were seen, while Argon's second run was under way and unscored; `gemini_neon_1119/`; item 76). Rounds 1 and 3, 24 inputs, 2 members each, 48 of 48 parsed. The one confirmatory line, the rule at L3: Inconclusive (minus the region trade +2.9 points, -0.4 to +6.3, margin 3; not Supported because the prior's labels at its places score higher, minus that control -1.5, -4.1 to +1.3); own score 8.7% beside 7.6%, 5.7%, 10.2%. Reported with no verdict: minus Opus +8.5 at L2 (-1.1 to +18.0) and +3.3 at L3; minus Haiku +0.6 at L2 (-10.0 to +12.0) and +4.0 at L3. Exploratory: minus Flash -10.1 at L2 (-13.1 to -7.3), minus Argon -7.3 at L2 (-13.0 to -1.8); at L2 below the prior (92.5%). Not the paper's model. Three Gemini models were tried in turn (3.8 Flash, 4 Argon, 4 Neon), each chosen after the last result was seen. All three are reported; they are not three independent confirmations, and none is the paper's model. At L3 no Gemini model was found to beat a trade of regions by the margin; at L2 Flash was above both Claude models and Argon above Opus only, and no verdict was registered for Neon at L2.
- **Room test (exploratory).** `exploratory_1119/room_test_runs.md`: see README, finding 4 (including the filter arm, which is not ahead of random guesses on either count).
- **M2 (offline, provisional yardstick).** True objects moved by each model's error show no detectable gain over random guesses; M2 varied place, not meaning (`results_semantic_1113/RESULTS.md` section 8; `results_m2_1113/exploratory_1119/all_true.md`).
- **Control arms on 853 (Amendment 5, final).** Same pipeline and clock, three runs each to 115 m. S (mean F1 at 50, 60, 80, 100 m of path), scripted reference / human labels, mean of three runs: ASP with the LLM's guesses 55.9 / 29.3; random guesses 49.5 / 25.3; no guesses 33.5 / 15.2. Registered statements: no guesses, "reads above"; random guesses, "in between" (higher on average, not separated, under both references). Chance alone gives full separation 1 time in 20 with three runs a side. The code gives unexplored space no value here (`live_policy.py`, lines 19 to 22), so the no-guess arm differs from ASP in more than what the guesses know; with no guesses the score barely grows with distance on average. Three runs a side in one home, no p-value; the controls ran later under another GPU load. Neither arm shows that the LLM's guesses beat random ones. Detail: README finding 3. Nothing is running; no Gemini run is left.

## Errata

Read these before quoting an earlier number. Items 1, 2, 4, 5 and 8 are WRITEUP §9 errata 1-5; items 3, 6 and 7 correct September claims.

1. **DeepSeek's 0.5 m precision "at chance" (OVERNIGHT_REPORT_2026-10-28, result 4) is wrong for live stages.** Live: 3.0% against the placebo's 0.5%. On the 8 matched static inputs the figures are 2.1% and 1.4% (`docs/checkin/FABLE_REVIEW_2026-10-28.md`). The check-in 1 deck still shows 1.7% vs 1.5%, the slide 3 frontier claim ("21% behind to 10% ahead", which step 7 reverses) and the slide 4 plan the reviews dropped.
2. **The September static headline "removes about 27 percent of predicted nodes" is wrong.** `tau=1.0` keeps 19 of 8,943 (99.8% removed). It scores within 0.0002 of the observed map alone (WRITEUP §9 erratum 2). This replicates on the 1017 model (WRITEUP §5).
3. **"Ensemble unanimity improves precision and GED" is not a filter effect.** The F1 gain shows that the guesses hurt the map. The 27 September closeout report (removed from the tree; it stays in git history) read it as a property of the backend's ensemble disagreement; erratum 2 does not support that.
4. **Calibration and the risk term are retired.** The offline Brier score equals the base rate. The combined risk term at beta <= 1 moved 2, 0 and 3 stages on the three matrix scenes (WRITEUP §9 erratum 3). The paper's "bit-identical at beta <= 1" is false.
5. **Two different filters were conflated.** The agreement vote (unanimity) and the validator (structural and geometric checks; the `filter_only` arm) are different filters. The 61 -> 45 and 313 -> 138 counts come from the validator, not from unanimity (WRITEUP §9 erratum 4; `docs/archive/PHASE13_DIAGNOSTICS_2026-09-17.md`).
6. **Gemini breadth is unverified.** The September closeout said the Gemini campaign "ran the full 3-scene x 3-seed breadth design". The archive report `docs/archive/SCIENTIFIC_CAMPAIGN_REPORT_2026-09-22.md` also lists all 9 blocks, each at "stage 0 (partial)" or later. A later hand-off note said 3 of 9 blocks never ran. The repo holds no per-block listing that settles this, so it is not verifiable from the repo. No block reached 120 m.
7. **The 61-category F1 list was not "unpublished" (#93).** DEVIATIONS #51 and several archive documents say the paper's list of 61 categories is not published anywhere. Entry #93 of `tyrone_mirror/DEVIATIONS.md` (9 Oct 2026) corrects this: the list has been in the author repo's `task_def/` folder since its first commit.
8. **Campaign notes corrected in the October DEVIATIONS item 34:** the item 26 p is 0.0655; the item 28 cost is the scheduler's figure, which includes shutdown calls; the item 31 run times were five runs of 2.07-2.75 h.

## Cost

Costs are kept by provider. Do not add across providers.

**Gemini** (recorded in the ledgers, [sanitized aggregates](audit/2026-09-26-ledger-summary.json), [26 September audit](audit/2026-09-26-remote-audit.md)):
- Settled cost across five ledgers: **$37.353274 over 2,282 settled requests.**
  - capability probe $0.003775
  - native-count verification $0.016292
  - engineering pilot $0.549772
  - scientific campaign $36.783435, including v6
- Three earlier probe and verification requests stay `DISPATCHED` with $0.009147 reserved and unknown settled cost. They are not counted as zero.
- Allocations sum to $183.50 against the $190 code ceiling. The $6.50 gap is arithmetic, not permission to spend.
- The scientific ledger sums to $159.976812 in reservations against its $160 allocation, leaving $0.023188 of headroom. This is why the shared allocation stopped while settled spend was lower.
- **Outside the ledger:** the 28 Oct Gemini static test (`tools/live_policy/gemini_static.py`) used $39.60 of Gemini credit (OVERNIGHT_REPORT_2026-10-28, result 4 and cost line). The ledger summary excludes it.
- **Gemini total, both: about $76.95** ($37.353274 + $39.60 = $76.953274). This is Gemini only.

**DeepSeek, October live campaign:** $14.60 in all, against a $40 cap (WRITEUP §2). That is $11.45 on counted paid runs, $13.06 on all scored runs, plus $1.33 for archived paid attempts and $0.20 for tests and dry runs. Calls made while a run shuts down add a few cents per run.

**September DeepSeek and OpenRouter spend:** not in the ledgers above and not totalled here. The ledger summary excludes it. Total: not verifiable from the repo.

## Artifact map

- [00069 matrix static replay](../tyrone_mirror/runs/matrix120m_scoring/scene00069_extension_policy_replay.json)
- [00573 matrix static replay](../tyrone_mirror/runs/matrix120m_scoring/scene00573_extension_policy_replay.json)
- [00853 matrix static replay](../tyrone_mirror/runs/matrix120m_scoring/scene00853_extension_policy_replay.json)
- [Static replay checksums](../tyrone_mirror/runs/matrix120m_scoring/STATIC_REPLAY_SHA256SUMS)
- [Author-faithful 00069 v6 evaluator](../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/author_faithful_evaluator.json)
- [00069 v6 extension replay](../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/extension_policy_replay.json)
- [00069 v6 decision replay](../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/decision_replay_00069_v6.json)
- [00069 v6 derived metrics](../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/derived_metrics.json)
- [Fixed-parser scoring summary](../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_scoring_20260922/block_00069_42_v6/summary.json)
- [Frozen Phase 13 diagnostics](../tyrone_mirror/runs/matrix120m_scoring/phase13_v5_20260917/phase13_diagnostics_v5.json)
- [Authoritative deviation log (September)](../tyrone_mirror/DEVIATIONS.md)
- [October live campaign package](../tools/live_policy/results_2026-10-31/WRITEUP.md)
- [November paper-scale scores](../tools/live_policy/results_paper_compare_1112/paper_compare.md)
- [26 September read-only audit](audit/2026-09-26-remote-audit.md) and [sanitized ledger aggregates](audit/2026-09-26-ledger-summary.json)
- [Architecture and metric reference](ARCHITECTURE.md)

## Input availability

The [27 September file-level manifest](audit/2026-09-27-input-manifest.json) and [SHA-256 list](audit/2026-09-27-input-SHA256SUMS) inventory 1,702 existing files. They record 92 local byte-matching copies, 1,607 host-only files, and three differing source files. Hashes of all 13 inputs listed in the frozen Phase 13 provenance match. Missing completion slots remain explicitly recorded.

| Input family | Local availability | Host requirement |
|---|---|---|
| 00069 calibration stage graphs | Selected cached stages mirrored | Full logs and other run files remain on host |
| 00573, 00853, 00871 calibration stage graphs | Results/configuration only | Raw stage graphs required for fitting |
| Four frontier references | Required `graph0` checkpoints mirrored | Other source artifacts remain on host |
| Three 120 m matrix runs | Static/decision results mirrored | Raw graphs, navigation/path files, logs, and request metadata required |
| Phase 13 v5 | Report, reliability plots, checksums mirrored | Raw inputs above required for regeneration |
| Gemini v6 | Derived scoring and analysis JSON mirrored | Original stage graphs remain on host; not an input to DeepSeek Phase 13 |
| Retired-supervisor snapshot | File digests recorded | Snapshot contents remain on host |
| Live ledgers and response archives | Sanitized accounting notes only | Original private records remain on host; live databases excluded from file hashing |

This is a selected-evidence mirror, not a complete raw-data export. Static replay resolves calibration folds by exact `/workspace/...` reference paths, so a local path yields `UNCALIBRATED_PROVISIONAL`. Decision replay needs all four calibration corpora even when `--run` points elsewhere. The manifest also discloses host/repository source drift. See [REPRODUCE.md](REPRODUCE.md) for what each tier needs.

The October and November data are not in this mirror in full. The October package holds scores and manifests; the mapper dumps stay on the host (WRITEUP §10).
