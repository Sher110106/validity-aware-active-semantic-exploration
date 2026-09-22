# Results index

This index separates completed evidence from superseded diagnostics. Detailed JSON remains under `tyrone_mirror/runs/`; the dated deviation log explains every correction.

## Run families

| Family | Runs or artifacts | Status | Primary result |
|---|---|---|---|
| Initial ASP gates | `scene00069_seed42_v4`, clean v3, and early probes | Completed | Baseline pipeline, evaluator, and artifact replay gates passed. |
| 00069 low-effort probe | `scene00069_seed42_25m_20260914_v3` | Completed | Tracked-graph AUC P=0.671, R=0.241, F1=0.352, normalized GED=1.075. |
| 00069 high-effort probe | `scene00069_seed42_high_effort_v5_matched` and `_full` | Completed | Matched AUC P=0.655, R=0.198, F1=0.302, normalized GED=1.189; full AUC F1=0.329. |
| Calibration collection | `scene00069_seed42_25m_20260914_v3`, `scene00573_seed42_calib_high32k`, `scene00853_seed42_calib_high32k`, `scene00871_seed42_calib_high32k` | Completed | Four-scene LOSO calibration and support-policy replay. |
| Final DeepSeek matrix | `scene00069_seed42_matrix120m`, `scene00573_seed42_matrix120m`, `scene00853_seed42_matrix120m` | Completed | All three reached 120 m; unanimity static guardrails passed. |
| Phase 13 | `matrix120m_scoring/phase13_v5_20260917` | Frozen | Calibration, validator, static guardrails, decision replay, and trajectory-availability diagnostics. |
| Gemini campaign | 3 scenes × seeds 42, 43, 44, with preserved v1/v2/v6 attempts | Stopped | Breadth completed; no Gemini block reached 120 m. |
| Gemini v6 offline analysis | `prospective_gemini/.../offline_analysis_20260922/block_00069_42_v6` | Completed | Author-faithful evaluator, static policy replay, decision replay, validator taxonomy, and ledger economics. |

## Final DeepSeek matrix

These are 120 m-capped AUC values from the corrected static-policy replay. `tau=1.0` means all four members of each graph track support the prediction.

| Scene | Official F1 | `tau=1.0` F1 | Relative F1 gain | Official GED | `tau=1.0` GED | Recall official → filtered |
|---|---:|---:|---:|---:|---:|---:|
| 00069 | 0.4789 | 0.5218 | +8.96% | 0.8969 | 0.8254 | 0.4747 → 0.4739 |
| 00573 | 0.3980 | 0.4349 | +9.29% | 0.9576 | 0.8877 | 0.3754 → 0.3743 |
| 00853 | 0.4578 | 0.4957 | +8.28% | 0.8561 | 0.7930 | 0.4461 → 0.4449 |

Interpretation: the filter removes approximately 27% of predicted nodes while retaining approximately 99.7% of full-graph true positives. The unchanged recall is expected because the filter removes predictions rather than adding them. This is a static graph result and a backend characterization, not live-policy generalization.

## Phase 13 disposition

The frozen four-scene calibration corpus contains 2,829 held-out rows, 23 positives, and 16 room rows. Pooled calibration improves overall Brier score but room calibration is too small to support a room-level claim. Static guardrails pass for all three matrix scenes. The false-positive detour gate is `NOT IDENTIFIABLE`, robot collisions are `NOT INSTRUMENTED`, and combined usefulness is `NOT ESTABLISHED`.

The exact frozen artifact is [phase13_diagnostics_v5.json](../tyrone_mirror/runs/matrix120m_scoring/phase13_v5_20260917/phase13_diagnostics_v5.json), with plots and checksums beside it.

## Gemini v6

The final block reached 19.5 m over seven completed stages and one partial stage. Author-faithful tracked-graph metrics at stage 6 were P=0.692, R=0.336, F1=0.452, normalized GED=1.109. Path-normalized AUC through 19.5 m was P=0.757, R=0.184, F1=0.283, normalized GED=1.119.

The best static completion-policy AUC was P=0.769, R=0.184, F1=0.284, normalized GED=0.937. Of 55 available completion files, all were accepted; 35 predicted nodes were removed, consisting of 30 AABB conflicts and 5 impassable crossings. Stage 2 scene 0 member 0 is missing; stage 7 is entirely partial.

The null decision replay matched the official selected pose at all seven completed stages. Filter-only moved one stage. Calibrated support moved five stages, with mean displacement 2.559 m and maximum 5.920 m. The combined risk arm moved 0/7 stages at beta=0, 2/7 at beta=1, and 6/7 at beta=5 or beta=20. These are replay measurements without live ROS reachability.

The ledger settled 898 requests for $18.552664. Reservations summed to $65.749854. No new run should be inferred from the remaining allocation.

## Artifact map

- [Author-faithful 00069 v6 evaluator](../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/author_faithful_evaluator.json)
- [00069 v6 extension replay](../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/extension_policy_replay.json)
- [00069 v6 decision replay](../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/decision_replay_00069_v6.json)
- [00069 v6 derived metrics](../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_analysis_20260922/block_00069_42_v6/derived_metrics.json)
- [Fixed-parser scoring summary](../tyrone_mirror/runs/prospective_gemini/scientific_campaign_20260922/offline_scoring_20260922/block_00069_42_v6/summary.json)
- [Frozen Phase 13 diagnostics](../tyrone_mirror/runs/matrix120m_scoring/phase13_v5_20260917/phase13_diagnostics_v5.json)
- [Authoritative deviation log](../tyrone_mirror/DEVIATIONS.md)
