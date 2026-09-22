# Gemini scientific block: zero-cost analysis

This report covers the preserved `block_00069_42_v6` run. No provider calls were made for this analysis. All replays used the deployed offline fix at commit `5c178e2`; stage 7 is partial and is excluded from trajectory metrics.

## Main results

The author-faithful tracked graph reached 19.5 m with precision **0.692**, recall **0.336**, F1 **0.452**, and normalized GED **1.109** at stage 6. Path-normalized AUC over 0–19.5 m was precision **0.757**, recall **0.184**, F1 **0.283**, normalized GED **1.119**.

The completion-policy replay (a static prediction-quality analysis, not a counterfactual live trajectory) produced the following 0–19.5 m capped AUC:

| Policy | Object precision | Object recall | Object F1 | Normalized GED |
|---|---:|---:|---:|---:|
| Official/raw | 0.686 | 0.184 | 0.277 | 0.953 |
| Validator only | 0.500 | 0.185 | 0.264 | 0.984 |
| Filter + support, τ=0.50 | 0.745 | 0.184 | 0.282 | 0.941 |
| Filter + support, τ=0.75 | 0.761 | 0.184 | 0.283 | 0.938 |
| Filter + support, τ=1.00 | 0.769 | 0.184 | 0.284 | 0.937 |

The support replay is genuinely LOSO-calibrated, trained on scenes 00573, 00853, and 00871 while holding out 00069. In this run the calibrated and raw-support rows coincide because the observed support levels are quantized by the intended four-member denominator; that is a result, not evidence that calibration is unnecessary in general.

## Validation and completeness

- 55 available completion files were validated; all 55 were accepted and none rejected.
- 35 predicted nodes were removed: 30 `aabb_conflict` and 5 `impassable_crossing` issues.
- Stage 2 scene 0 is missing member 0. Stages 0–1 and 3–6 have both complete four-member tracks (13 complete scene-track records total).
- Stage 7 has no completion files and no navigation checkpoint, so it is recorded as partial only.

## Decision replay

The null-control replay exactly reproduced the official selected pose at all seven completed stages (zero displacement). Relative to that control, mean selected-pose displacement was 0.185 m for filter-only (one non-zero stage) and 2.559 m for calibrated support (five non-zero stages; maximum 5.920 m). The combined risk arm changed the selection on 0/7 stages at β=0, 2/7 at β=1, and 6/7 at β=5 or β=20. These are replayed decision differences; they are not measured navigation outcomes. Robot collisions and false-positive detours remain unidentifiable from these artifacts.

## Real economics and instrumentation

For `run-block_00069_42_v6`, the ledger contains 898 settled requests, all with `STOP` finish reason and no ledger errors or retries. Real settled spend was **$18.552664**. The sum of reservations was **$65.749854**, illustrating why the shared allocation exhausted on reservation accounting even though settled spend was much lower. Per-stage settled spend was:

| Stage | Path (m) | Requests | Settled |
|---:|---:|---:|---:|
| 0 | 0.000 | 134 | $2.087117 |
| 1 | 2.475 | 144 | $2.540419 |
| 2 | 3.825 | 109 | $2.105128 |
| 3 | 6.075 | 118 | $2.178027 |
| 4 | 11.175 | 123 | $2.628527 |
| 5 | 15.825 | 126 | $3.487372 |
| 6 | 19.500 | 117 | $2.616456 |
| 7 (partial) | — | 27 | $0.909618 |

The raw archive and ledger agree on 20,401,514 input tokens, 747,185 thought tokens, 119,712 candidate tokens, and 21,268,411 total tokens. The native-count instrumentation recorded 1,162 count attempts with zero fallbacks: real count mean 17,388 (range 9,346–24,099), while the safety-bound value averaged 19,561, an average margin of 2,173 tokens (12.5%).

## Matched historical comparisons

At a common 16.425 m path budget, v6’s tracked-graph AUC was precision 0.770, recall 0.160, F1 0.256, normalized GED 1.120. The earlier scene-00069 v3 run (DeepSeek backend) was precision 0.668, recall 0.210, F1 0.318, normalized GED 1.065 at the same cap. The completed 00069 matrix run (also DeepSeek) was precision 0.769, recall 0.130, F1 0.216, normalized GED 1.106. These comparisons are descriptive only: backend, run configuration, and checkpoint spacing differ, so they do not isolate a model effect.

The full Phase 13 cross-scene calibration report was not rerun for this one partial block: that diagnostic is registered against the frozen four-scene/94-stage corpus and cannot honestly treat a single 00069 partial trajectory as a new held-out scene. Its applicable single-run pieces (validation, decision replay, trajectory metrics, and accounting) are included above.

## Artifacts

- [Zero-cost fixed-parser scoring summary](../../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_scoring_20260922/block_00069_42_v6/summary.json)
- [Derived metrics](../../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/derived_metrics.json)
- [Author-faithful evaluator](../../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/author_faithful_evaluator.json)
- [Extension-policy replay](../../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/extension_policy_replay.json)
- [Decision replay](../../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/decision_replay_00069_v6.json)
- [Matched matrix evaluator](../../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/comparison_matrix00069_author_faithful_through_16_425m.json)
