# Phase 13 diagnostics closeout — v5 — 2026-09-17

## Scope and correction history

Primary review found a real v4 aggregation defect: cross-scene diversity was weighted by all stage tracks although tracks with fewer than two available completions do not define a pairwise diversity value. v4 and DEVIATIONS #79 are preserved unchanged. v5 uses only defined diversity tracks, adds explicit defined-track counts, and is authoritative. The effect is small: aggregate diversity changes from `0.6360473977461963 → 0.7555852798134879` to `0.6360903078259732 → 0.7556307279246379`. Calibration, static guardrails, trajectory diagnostics, and plots are otherwise unchanged.

The completion boundary remains exact: 94 completed stage directories × 2 scene tracks × 4 expected ensemble members = **752 expected completion slots**. Partial/empty post-shutdown stage directories are excluded.

## Calibration: complete per-scene LOSO table

The calibrator is pooled across room and object hypotheses and fit leave-one-scene-out. Each held-out fold is evaluated only on held-out predictions. The train-rate baseline uses only matching-subset prevalence from the other three scenes. ECE uses ten equal-width bins, `[lower, upper)` except the final bin includes 1.0, weighted by bin population.

| held-out scene | subset | n | positives | raw Brier | calibrated Brier | train-rate Brier | raw ECE | calibrated ECE |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 00069 | overall | 395 | 4 | 0.0924051 | 0.0104083 | 0.0100294 | 0.270886 | 0.004994 |
| 00069 | object | 393 | 3 | 0.0903308 | 0.0091733 | 0.0075825 | 0.269720 | 0.004737 |
| 00069 | room | 2 | 1 | 0.5000000 | 0.2530864 | 0.2500000 | 0.500000 | 0.055556 |
| 00573 | overall | 680 | 11 | 0.0895221 | 0.0134609 | 0.0160270 | 0.268382 | 0.009028 |
| 00573 | object | 673 | 6 | 0.0898960 | 0.0090964 | 0.0088580 | 0.270431 | 0.005110 |
| 00573 | room | 7 | 5 | 0.0535714 | 0.4330778 | 0.3492063 | 0.142857 | 0.549020 |
| 00853 | overall | 705 | 2 | 0.0866135 | 0.0032290 | 0.0028785 | 0.274113 | 0.005099 |
| 00853 | object | 703 | 2 | 0.0850818 | 0.0028823 | 0.0028479 | 0.272760 | 0.004383 |
| 00853 | room | 2 | 0 | 0.6250000 | 0.1250877 | 0.3265306 | 0.750000 | 0.256623 |
| 00871 | overall | 1,049 | 6 | 0.0828765 | 0.0052553 | 0.0057017 | 0.266683 | 0.001865 |
| 00871 | object | 1,044 | 4 | 0.0818966 | 0.0040465 | 0.0038224 | 0.267241 | 0.003116 |
| 00871 | room | 5 | 2 | 0.2875000 | 0.2576657 | 0.2611570 | 0.350000 | 0.295619 |

Pooled aggregate:

| subset | n | positives | rate | raw Brier | calibrated Brier | train-rate Brier | raw ECE | calibrated ECE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| overall | 2,829 | 23 | 0.813% | 0.0867356 | 0.0074422 | 0.0080843 | 0.269530 | 0.001575 |
| object | 2,813 | 15 | 0.533% | 0.0857847 | 0.0056800 | 0.0053089 | 0.269730 | 0.001564 |
| room | 16 | 8 | 50.000% | 0.2539062 | 0.3172638 | 0.3064557 | 0.265625 | 0.369944 |

Overall calibration is uneven: pooled calibrated Brier improves over raw and baseline, but object calibration is worse than its baseline by 0.0003710 and room calibration is worse by 0.0108082. The low pooled ECE is dominated by extreme imbalance and 2,813 object rows; it is not evidence of room calibration. Room n is only 16. Per-scene overall Brier is better than baseline on 00573 and 00871, worse on 00069 and 00853.

Reliability plots are `reliability_overall.svg`, `reliability_object.svg`, and `reliability_room.svg`. v5 plots are byte-identical to v4.

## Validator diagnostics

The validator is evaluated on predicted hypotheses only. The unchanged observed map is excluded before both evaluator calls. Matching is recomputed after filtering, so a surviving duplicate can rematch a reference node after a closer invalid duplicate is removed. Diversity is mean pairwise Jaccard **distance** over case-folded `(kind, label)` sets, averaged within each track and then weighted across scenes only by tracks with at least two available completions.

| scene | expected | available | accepted | rejected | missing | excluded | survival | object TP before→after | room TP before→after | object TP retention | room TP retention | object FP removal | room FP removal | defined tracks before/after | diversity before→after |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---|---|
| 00069 | 224 | 201 | 197 | 4 | 23 | 993 | 66.14% | 11→9 | 109→60 | 81.82% | 55.05% | 31.20% | 58.47% | 56/56 | 0.6175574039→0.7377880412 |
| 00573 | 272 | 255 | 246 | 9 | 17 | 1,461 | 63.55% | 27→20 | 118→38 | 74.07% | 32.20% | 33.38% | 58.02% | 67/67 | 0.6280232128→0.7470864830 |
| 00853 | 256 | 230 | 224 | 6 | 26 | 1,135 | 66.82% | 23→16 | 86→40 | 69.57% | 46.51% | 29.77% | 62.67% | 64/64 | 0.6607518388→0.7801878352 |
| **aggregate** | 752 | 686 | 667 | 19 | 66 | 3,589 | 65.36% | 61→45 | 313→138 | 73.77% | 44.09% | 31.57% | 59.70% | 187/187 | 0.6360903078→0.7556307279 |

The old “~99.7% true positives” phrase describes full-graph evaluator TP retention (after TP / before TP), dominated by unchanged observed-map nodes; it is not the recall score itself and is not predicted-only retention.

## Static guardrails

Policy: `filter_plus_support_threshold_calibrated_tau_1.0`; 120 m-capped AUC. Limits: object-F1 absolute loss ≤0.05 and normalized-GED relative increase ≤10%.

| scene | official F1 | policy F1 | F1 loss | official GED | policy GED | GED change | gate |
|---|---:|---:|---:|---:|---:|---:|---|
| 00069 | 0.478938 | 0.521794 | -0.042856 | 0.896941 | 0.825383 | -7.978% | pass |
| 00573 | 0.397964 | 0.434966 | -0.037003 | 0.957558 | 0.887629 | -7.303% | pass |
| 00853 | 0.457820 | 0.495655 | -0.037835 | 0.856089 | 0.792967 | -7.373% | pass |

Static and invalid-hypothesis gates pass. The false-positive detour gate remains **NOT IDENTIFIABLE**: replay selected stage-local poses but did not navigate them and records no live reachability or cumulative counterfactual paths. Combined usefulness is therefore **NOT ESTABLISHED**.

## Trajectory availability

| scene | completed stages | final path | A* failures | API counter / records | cost |
|---|---:|---:|---:|---:|---|
| 00069 | 28 | 125.325 m | 13 | 1922 / 1922 | unavailable |
| 00573 | 34 | 121.875 m | 10 | 2445 / 2444 | unavailable |
| 00853 | 32 | 126.075 m | 15 | 2053 / 2053 | unavailable |

Robot collision count is **NOT INSTRUMENTED**, not zero. The controller uses `agent.set_state` and unconditionally increments path length; no contact, blocked-step, or collision-sensor artifacts exist. LLM `check_collision` concerns object-box overlap. A* failures are planner failures. Costs/token usage are unavailable and summed request seconds are concurrency-inflated.

## Disposition

Phase 13 is evaluated and closed for the frozen corpus. Detours remain NOT IDENTIFIABLE, collisions remain NOT INSTRUMENTED, and combined usefulness remains NOT ESTABLISHED. Verification: local focused suite is 11 passed / 2 PyYAML-dependent skipped; tyrone focused suite is 13 passed; complete tyrone offline suite is 54 passed; author-faithful evaluator suite is 11 passed; compileall, XML/SVG validation, source-hash, mirror-hash, and `git diff --check` checks pass. No live run was launched.

## v5 artifact hashes

| artifact | SHA-256 |
|---|---|
| `phase13_diagnostics_v5.json` | `8f99132b8955c48f6f5e05f4de865ceb3dacfc697b2087800a84ab491d318036` |
| `reliability_overall.svg` | `d8fb3c6ae2bbdf625066661829d7827412ec41c7d2e476343c1f1ae1d5cb7375` |
| `reliability_object.svg` | `2421f461df44b06d38c68172755ad056f3ec46cf75f9412df6718e6c57a72724` |
| `reliability_room.svg` | `ceb340fde1fcff6a3ed790761cc8b796e67815a6b6830192e71c478b66435550` |

The authoritative directory is `runs/matrix120m_scoring/phase13_v5_20260917/` on tyrone and is mirrored locally at `tyrone_mirror/runs/matrix120m_scoring/phase13_v5_20260917/`. v4 remains preserved.
