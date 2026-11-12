# Overnight report, 2026-10-28 (written 07:35 IST; runs continue)

## How the plan was made
1. Four Fable readers went through every result, trace and the run infrastructure; three Fable planners wrote plans (rigor, presentation, information per dollar); an Opus judge attacked them; a Fable synthesizer merged them. Files: /tmp/cvp_ctrl/final_plan.md, judge_verdict.json.
2. GPT-6 Astra (Codex) reviewed plan and code: no-go until six fixes (/tmp/cvp_ctrl/dialogue/astra_review_1.md).
3. The Fable side answered Astra point by point (/tmp/cvp_ctrl/dialogue/fable_response_1.json). Where they disagreed I took Fable's placebo spec (no navmesh knowledge the LLM lacks) and pacing schedule, and Astra's code fixes and HM3D reference.
4. Final design (E1): the author's pipeline on DeepSeek V4.1 Flash 1017 (DeepInfra fp8, hard pin) against a placebo that replaces the LLM's hypotheses with random ones of the same measured shape; scenes 00853 and 00871 (human HM3D annotation); seeds 42-44; 60 m; scored against the HM3D annotation. Pre-registered and hashed before the first run (PREREGISTRATION_E1.md, plus an E2 addendum for the validator arm). Because code changed after the freeze (DEVIATIONS 1-13), E1 is labelled a pilot.

## Results ready now
1. ASP vs frontier depends on the reference (existing runs, zero cost, one run per arm, ILLUSTRATIVE). Against the human HM3D annotation, the old-model ASP run on 00853 maps objects faster than the frontier explorer: F1 AUC +0.026 at 25 m to +0.016 at 95.7 m (+27% to +7%); 00871 to 28 m: +0.022 (+32%). Against the frontier-made reference the sign flips (frontier ahead by about 21%), because that reference scores the frontier run against itself (its F1 AUC is 2.7-3.3x higher under its own reference). Files: /tmp/cvp_zero/hm3d_rescore/.
2. The static negative holds on the human reference (00853, 120 m): raw predictions F1 AUC 0.2479, unanimity 0.2580, observed graph only 0.2580.
3. The stage-0 "noise" was contamination, not noise: in six September runs the mapper kept running between launches, so stage 0 already held earlier runs' maps (Spearman with carried-over content 0.99-1.0). Clean launches vary by about +/-0.03 F1. This retires the effort comparison for good. Files: /tmp/cvp_zero/noise_checks/.
4. A bigger model predicts better (Gemini 3.8 Flash vs DeepSeek 1017 on identical stage inputs through the author's tool loop; 29 vs 40 completions; 8 stages; $39.60 of Gemini credit). Precision of predicted objects placed away from mapped objects, against the HM3D annotation: within 0.5 m 7.1% vs 1.7% (random placebo 1.5%); within 1.0 m 17.1% vs 7.4% (placebo 4.1%). Gemini ahead at 7 of 8 stages (sign test p = 0.07). DeepSeek's 0.5 m precision is at chance. Gemini also relabels detected objects, often to the annotated label. Exploratory: the metric was fixed after the first 7 Gemini completions. Files: hm3d_refs_work/gemini_static*_scores.json on tyrone.
5. The decision-replay yardstick has no frame bug but counts one 90-degree view with over-strict occlusion and predicts the robot's actual gain weakly (Spearman 0.27); keep it off slides as an absolute number.
6. Engineering on 1017 / DeepInfra fp8, live: about $0.88-0.95 per 60 m official run, $0.03-0.05 per stage, cache 88-91%, LLM wait 4-16 min per stage, 6-21% of ensemble members dropped (parse failures).
7. New assets: HM3D-annotation reference graphs for 00853 and 00871 in the pipeline frame (frame transform exact against the robot's logged paths); figure pack /tmp/cvp_zero/figures/.

## Live E1 so far (pilot)
Author-faithful object F1 AUC to 60 m (scores: runs/live_campaign/hm3d_refs_work/cells12_scores.json, cell3_scores.json):

| Cell | Official (HM3D) | Placebo (HM3D) | Official (frontier ref) | Placebo (frontier ref) | Official path | Official cost |
|---|---|---|---|---|---|---|
| 00853/42 | 0.1412 | 0.1464 | 0.2623 | 0.3609 | 61.1 m | $0.88 |
| 00871/42 | 0.1314 | 0.1141 | 0.4617 | 0.4317 | 64.6 m | $0.81 |
| 00853/43 | 0.1531 | 0.1722 | 0.2896 | 0.3697 | 54.3 m | $1.15 |

The placebo leads in two of three cells on the primary reference (mean official minus placebo -0.002); no inference yet. The 00853/43 official run hit the 4.5 h limit at 54.3 m (kept: above the 50 m line), so its 60 m score holds its last value from 54.3 m; at 50 m, which both arms reached, the cell reads 0.1304 vs 0.1549.

Status at 14:00 (DEVIATIONS 15-16):
- 00871/43: official running (20 m at 13:47). Its placebo stopped at 0.0 m: after its first move the robot stood where the author's planner reached none of 53 candidates over six differently seeded hypothesis sets. Excluded and queued for one rerun with a fresh placebo stream (a plain rerun would replay the same draws).
- E2 (our filter_only change vs the author's official pipeline) moved to the front: 00853/42 and 00871/42 started at 13:58; first E2 numbers about 17:00-18:00.
- Then E1 pairs 00853/44 and 00871/44, the placebo rerun, and E2 seeds 43 and 44 (campaign_jobs_3.txt).

Status at 17:20:
- 00871/43 official reached 61.0 m at 16:32 ($1.02): HM3D AUC to 60 m 0.1267 (frontier ref 0.467). Its placebo rerun is still queued.
- First E2 result: e2_00871_s42_filter_only_60m reached 60.8 m at 17:19 ($1.09). HM3D AUC to 60 m 0.136 against the official run's 0.1314 on the same scene and seed (+0.005; at 50 m 0.124 vs 0.122). The two official seeds on 00871 differ by the same 0.005, so this one pair shows no gain beyond seed noise. Scores: hm3d_refs_work/e2_00871_s42_scores.json.
- Frontier explorer scored to 60 m on both scenes (hm3d_refs_work/frontier_60m_scores.json): HM3D AUC 0.1716 on 00853, 0.1192 on 00871. On 00853 the live DeepSeek official runs (0.141, 0.153) fall below it; on 00871 they beat it (0.131, 0.127).
- Pair 00853/44 started at 17:19; e2_00853_s42 at 47.6 m. Chart: results_snapshot_2026-10-28.html.

## What went wrong overnight, and the fixes (DEVIATIONS.md on tyrone)
- Six concurrent runs plus leftover ROS stacks exhausted the host's 123 GB of RAM at about 04:00. The kernel OOM killer killed another user's claude-desktop (03:59) and your atlas-api-readonly service (04:10; systemd restarted it at 04:10:50). Under that load the runners misread failed process checks as "pipeline exited" and stopped all six first-wave runs. Fixed: robust process checks, memory guards, one pair at a time; mapper memory grows about 8 GB per hour per run.
- The pipeline's LLM worker processes outlive a stopped pipeline and kept calling the paid API ($0.063 leaked once). Fixed: cleanup kills every process in a container between runs.
- One LLM request hung 12+ minutes (requests' timeout is per socket read). Fixed: a total deadline per request.
- The placebo redrew identical hypotheses after a planning failure and looped. Fixed: retries reseed.
- A 200 response with an error body crashed a runner; fixed.
Lost work: about $1.7 of DeepSeek on aborted or excluded runs; no run's data was corrupted.

## Spend
DeepSeek: $2.78 this month on the key at 07:35 (all tests and runs); the live campaign's metered total was $4.97 at 14:00, well inside the $40 cap. Gemini: $39.60 tonight; if the $200 credit paid only for this project, about $123 is left (unconfirmed; check the AI Studio billing page).

## Code (uncommitted, repo working tree)
tools/live_policy/ (live_policy.py, run_pipeline_with_policy.py, run_live_run.sh, live_runner.py, live_score.py, e1_analysis.py, gemini_static.py, gemini_static_score.py, placebo_calibration.json, PREREGISTRATION_E1.md, PREREGISTRATION_E2.md, this report), tools/legacy/asp_openrouter_shim.py, tools/tests/test_live_policy.py, test_live_runner.py, test_openrouter_shim_metering.py (36 pass locally). Host-only helpers in /workspace/tools/live_policy/ (start_runner.sh, launch_pair.sh, next_pair_when_ready.sh, clean_container.sh, wave_status.py, pacing_update.py).
