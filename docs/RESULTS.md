# Results

This is the one map of results for every experiment. It separates completed evidence from superseded diagnostics, and lists the errata. Detail JSON stays under `tyrone_mirror/runs/` (September) and `tools/live_policy/` (October and November). The dated deviation logs explain each correction. The three per-scene matrix static replays are mirrored with checksums in `tyrone_mirror/runs/matrix120m_scoring/STATIC_REPLAY_SHA256SUMS`.

Read the [Errata](#errata) before quoting any September number.

| Period | What | Where |
|---|---|---|
| September | Replication, DeepSeek 120 m matrix, Phase 13, Gemini campaign | sections below, from "Run families" |
| October | Live placebo-controlled campaign (E1-E3, steps 6-8) | [October live campaign](#october-live-campaign) |
| November | Scores on the paper's scale | [November paper-scale scores](#november-paper-scale-scores) |

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
- [paper_compare.md](../tools/live_policy/results_paper_compare_1112/paper_compare.md): the current scores (12 Nov).
- [NOTES.md](../tools/live_policy/results_paper_compare_1112/NOTES.md): the command, budgets, independent check, and nine disclosures.
- `tools/live_policy/results_paper_compare/` holds the superseded 6 Nov scores. Its `ged/` folder still feeds the 12 Nov run.
- Current status and open items: [STATUS_2026-11-12.md](STATUS_2026-11-12.md). Plan: [ENDSEM_PLAN_2026-11-03.md](ENDSEM_PLAN_2026-11-03.md).

Headline: scene 00853, APR reference (the coverage-tour map). Cells are F1 x 100 at 10% / 50% / 100% of B (cells are means; budget B = 632.1751 s). The 100% cell is null for runs that ended before B. Source: paper_compare.md, "Reference: apr".

| Row | Our arm | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|
| Frontier | `frontier_end` (5 runs to the end of exploration) | 12.4 | 18.6 | 39.5 | 46.5 | 55.6 (3 of 5 runs) | 58.8 |
| ASP | `official` (2 runs, stop at 60 m) | 16.5 | 34.4 | 38.7 | 60.8 | null | 66.7 |
| ASP | `filter_only` (3 runs, stop at 60 m) | 14.8 | 34.4 | 48.3 | 60.8 | null | 66.7 |

Reading:
- Our frontier row sits below the paper's frontier row at 10% and 50% and is close at 100% (55.6 against 58.8).
- Our ASP rows sit far below the paper's ASP row (16.5 / 38.7 against 34.4 / 60.8). Our `official` ASP row (38.7 at 50%) is level with our own frontier row (39.5). `filter_only` leads it by 8.8 at 50%, but E2 found no detectable difference between the two ASP arms, and n is 2-3. The paper's 14.3-point lead for ASP at 50% does not appear for `official`.
- These are not like-for-like. The paper scores against a hand-driven full-scene map. We use a coverage-tour map. ASP runs stop at 60 m of path, so the 100% cell is null. Scenes 00069 and 00573 have no run here. Paper_compare.md, "Not comparable", lists every difference.
- Scene 00871 has one finished frontier run. Its APR cells are 26.4 / 43.2 / 62.8 against the paper's 29.2 / 55.7 / 65.3.
- Treat the cells as descriptive. n is 1-5 per cell and NOTES.md lists nine disclosures (for example, the check C2 is not valid and the APR floor area differs from the paper's).
- The F1 readout is the stage value at the last stage at or before t; the running maximum (the author's plot rule) is reported beside it in the JSON.

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
