# Results index

This index separates completed evidence from superseded diagnostics. Detailed JSON remains under `tyrone_mirror/runs/`; the dated deviation log explains every correction. The three per-scene matrix static replays are now mirrored with checksums in `tyrone_mirror/runs/matrix120m_scoring/STATIC_REPLAY_SHA256SUMS`.

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

These are 120 m-capped path-normalized AUC values from the corrected static-policy replay, scored with the **canonical evaluator** (`tools/asp_offline/evaluator.py`), not the author-faithful tracked-graph evaluator. The exact keys are `path_normalized_auc_capped.official` and `path_normalized_auc_capped.support_threshold_tau_1.0`. `tau=1.0` means all four members of each graph track support the prediction. Per-scene sources: [00069](../tyrone_mirror/runs/matrix120m_scoring/scene00069_extension_policy_replay.json), [00573](../tyrone_mirror/runs/matrix120m_scoring/scene00573_extension_policy_replay.json), [00853](../tyrone_mirror/runs/matrix120m_scoring/scene00853_extension_policy_replay.json).

| Scene | Official F1 | `tau=1.0` F1 | Relative F1 gain | Official GED | `tau=1.0` GED | Recall official → filtered |
|---|---:|---:|---:|---:|---:|---:|
| 00069 | 0.4789 | 0.5218 | +8.96% | 0.8969 | 0.8254 | 0.4747 → 0.4739 |
| 00573 | 0.3980 | 0.4349 | +9.29% | 0.9576 | 0.8877 | 0.3754 → 0.3743 |
| 00853 | 0.4578 | 0.4957 | +8.28% | 0.8561 | 0.7930 | 0.4461 → 0.4449 |

Interpretation: the filter removes approximately 27% of predicted nodes while retaining approximately 99.7% of full-graph true positives. Near-preserved recall is an observed outcome, not a guarantee of removing predictions. This is a static graph result and a backend characterization, not live-policy generalization.

## Phase 13 disposition

The frozen four-scene calibration corpus contains 2,829 held-out rows, 23 positives, and 16 room rows. Pooled calibration improves overall Brier score but room calibration is too small to support a room-level claim. Static guardrails pass for all three matrix scenes. The tested guardrail policy is `filter_plus_support_threshold_calibrated_tau_1.0`, with absolute F1 loss at most 0.05 and relative normalized-GED increase at most 10%; the headline table above uses raw support alone. The false-positive detour gate is `NOT IDENTIFIABLE`, robot collisions are `NOT INSTRUMENTED`, and combined usefulness is `NOT ESTABLISHED`.

The exact frozen artifact is [phase13_diagnostics_v5.json](../tyrone_mirror/runs/matrix120m_scoring/phase13_v5_20260917/phase13_diagnostics_v5.json), with plots and checksums beside it.

## Gemini v6

The final block reached 19.5 m over seven completed stages and one partial stage. Author-faithful tracked-graph metrics (**`tools/evaluator/`**) at stage 6 were P=0.692, R=0.336, F1=0.452, normalized GED=1.109. Path-normalized AUC through 19.5 m was P=0.757, R=0.184, F1=0.283, normalized GED=1.119.

The best static completion-policy AUC was P=0.769, R=0.184, F1=0.284, normalized GED=0.937. Of 55 available completion files, all were accepted; 35 predicted nodes were removed, consisting of 30 AABB conflicts and 5 impassable crossings. Stage 2 scene 0 member 0 is missing; stage 7 is entirely partial.

The null decision replay matched the official selected pose at all seven completed stages. Filter-only moved one stage. Calibrated support moved five stages, with mean displacement 2.559 m and maximum 5.920 m. The combined risk arm moved 0/7 stages at beta=0, 2/7 at beta=1, and 6/7 at beta=5 or beta=20. These are replay measurements without live ROS reachability.

The ledger settled 898 requests for $18.552664. Reservations summed to $65.749854. No new run should be inferred from the remaining allocation.

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
- [Authoritative deviation log](../tyrone_mirror/DEVIATIONS.md)
- [26 September read-only audit](REMOTE_AUDIT_2026-09-26.md) and [sanitized ledger aggregates](audit/2026-09-26-ledger-summary.json)
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
