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
Author-faithful object F1 AUC to 60 m (scores: runs/live_campaign/hm3d_refs_work/cells12_scores.json):

| Cell | Official (HM3D) | Placebo (HM3D) | Official (frontier ref) | Placebo (frontier ref) | Official cost |
|---|---|---|---|---|---|
| 00853/42 | 0.1412 | 0.1464 | 0.2623 | 0.3609 | $0.88 |
| 00871/42 | 0.1314 | 0.1141 | 0.4617 | 0.4317 | $0.81 |

Two cells point in opposite directions on the primary reference (mean official minus placebo +0.006); no inference yet. Running: 00853/43 (started 09:24); 00871/43 launches automatically on tyrone when memory allows, then 00853/44 and 00871/44. Each pair takes about 2.5-3 h and only one pair fits in memory at a time, so the six cells need until about evening; E2 (validator arm, 6 runs) after that.

## What went wrong overnight, and the fixes (DEVIATIONS.md on tyrone)
- Six concurrent runs plus leftover ROS stacks exhausted the host's 123 GB of RAM at about 04:00. The kernel OOM killer killed another user's claude-desktop (03:59) and your atlas-api-readonly service (04:10; systemd restarted it at 04:10:50). Under that load the runners misread failed process checks as "pipeline exited" and stopped all six first-wave runs. Fixed: robust process checks, memory guards, one pair at a time; mapper memory grows about 8 GB per hour per run.
- The pipeline's LLM worker processes outlive a stopped pipeline and kept calling the paid API ($0.063 leaked once). Fixed: cleanup kills every process in a container between runs.
- One LLM request hung 12+ minutes (requests' timeout is per socket read). Fixed: a total deadline per request.
- The placebo redrew identical hypotheses after a planning failure and looped. Fixed: retries reseed.
- A 200 response with an error body crashed a runner; fixed.
Lost work: about $1.7 of DeepSeek on aborted or excluded runs; no run's data was corrupted.

## Spend
DeepSeek: $2.78 this month on the key (all tests and runs), $37.22 left of $40. Gemini: $39.60 tonight; if the $200 credit paid only for this project, about $123 is left (unconfirmed; check the AI Studio billing page).

## Code (uncommitted, repo working tree)
tools/live_policy/ (live_policy.py, run_pipeline_with_policy.py, run_live_run.sh, live_runner.py, live_score.py, e1_analysis.py, gemini_static.py, gemini_static_score.py, placebo_calibration.json, PREREGISTRATION_E1.md, PREREGISTRATION_E2.md, this report), tools/legacy/asp_openrouter_shim.py, tools/tests/test_live_policy.py, test_live_runner.py, test_openrouter_shim_metering.py (36 pass locally). Host-only helpers in /workspace/tools/live_policy/ (start_runner.sh, launch_pair.sh, next_pair_when_ready.sh, clean_container.sh, wave_status.py, pacing_update.py).
