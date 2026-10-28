# Pre-registration: live campaign E1 (official vs placebo), 2026-10-28

Frozen before wave 1 launches. Its sha256, and the sha256 of every file it names, are recorded in /workspace/runs/live_campaign/PREREGISTRATION_E1.sha256 on tyrone. Decided by the main session after the Fable plan, the Opus judge, the GPT Astra review and the Fable response to it (all under /tmp/cvp_ctrl/ and /tmp/cvp_ctrl/dialogue/).

## Question
Does the scene-conditioned content of the LLM's scene-graph predictions help the live ASP robot map objects per metre of path, compared with hypotheses that have the same shape statistics but no conditioning on the scene?

## Arms
- official: the author's pipeline, unchanged. ASP_LIVE_POLICY=official is a no-op on the completion files (unit-tested). Model deepseek/deepseek-v4.1-flash-1017 on OpenRouter, pinned to DeepInfra fp8 with no fallbacks, reasoning effort low, max_tokens 16000, author prompt and tool loop unchanged.
- placebo (v2): no LLM call. Each of the 8 ensemble members gets the observed graph plus its own random hypotheses, seeded by (SEED, stage, graph id), calibrated from 20 raw 1017 completions of tonight's dry run (tools/live_policy/placebo_calibration.json): objects Poisson(10) clipped to 6-16; rooms 1 or 2 (P(2) = 0.6); object labels and sizes drawn from the empirical 1017 frequencies (LLM spelling kept); room names from the empirical 1017 room names; each new room 1.5-3.5 m from a random observed room centre (rejected within 1.0 m of any observed node), unflagged like the LLM's rooms, linked to the nearest observed room and to the second nearest with p = 0.32; each object flagged is_predicted like the LLM's, attached with p = 0.54 to a new room at 0.3-1.5 m from its centre, otherwise to a random observed room at 0.5-2.5 m, rejected within 0.3 m of an observed object centre, z = floor + height / 2, linked to its room. No navmesh or structure check (the LLM has neither).
- Pacing: the placebo arm sleeps per planning step so its step lasts as long as the LLM step would: schedule 260 s, 400 s, then 500 s for every later stage (dry-run LLM phases: 263, 406, 575 s). Update rule for wave 2, fixed now: per-stage median of llm_wait_s over the wave-1 official runs for the stages they reached, the prior for later stages. The actual delay is logged per stage.

## Cells, waves and containers
Scenes 00853 and 00871 (HM3D val, official semantic annotation); seeds 42, 43, 44; 60 m path budget (the runner stops at the first checkpoint whose recorded path is at least 60 m). Each official run and the placebo run of the same (scene, seed) run at the same time on two identical containers. Wave 1: 00853/42, 00871/42, 00853/43. Wave 2: 00871/43, 00853/44, 00871/44, with container-to-arm assignments rotated. 00069 is not in tonight's design.

## Metric and references
Primary: author-faithful tracked-graph object F1 (tools/evaluator matching: exact label, centre distance < 0.5 m, greedy), mean of graph0 and graph1 at each checkpoint, path-normalised trapezoid AUC over 0-60 m (asp_offline.evaluator.area_under_curve, budget 60, hold-last past the final checkpoint), against the HM3D-annotation reference (runs/live_campaign/hm3d_refs_work/<scene>_hm3d_reference.yaml, primary label tier). Secondary: the same against the frontier-made reference (live_score.REFS); canonical F1, recall and nGED AUC; F1 at 30 and 60 m; the extended label tier as a sensitivity check. A claim needs the same sign under both references.

## Test
Statistic: mean over scenes of (mean official AUC - mean placebo AUC). Primary: scene-blocked permutation of arm labels within each scene, exact (C(6,3)^2 = 400 relabelings), two-sided, alpha 0.05; this is the only confirmatory contrast tonight (Holm with E2 if E2 is run later). Secondary: seed-paired sign-flip test over the 6 cells. Reported: per-scene differences, scene-blocked bootstrap 95% CI, and the minimum detectable effect (alpha 0.05, power 0.8) as a range. A non-significant result is "no detectable difference, MDE = x", never "equal".

## Exclusions and covariates
Excluded (and rerun once if time allows): a run that stops below 50 m; an official run with any call not served by DeepInfra with the 1017 model; an official run with more than 50% of ensemble members dropped over the run (the dry run dropped about 17%; drops are part of the official arm's behaviour with this model, so the rate is reported per run as a covariate rather than used to exclude at 20%). A pair is flagged if the placebo's delay differs from its official partner's LLM wait by more than 20% at three or more stages.

## Claim status
Tonight is confirmatory only if: this file is hashed before wave 1; placebo and pacing code do not change after wave 1 except through the update rule above; all 12 runs reach 50 m without exclusion; and the between-wave gate passes (planning errors <= 5 per run, stage overheads not more than 15% above the dry run). Otherwise every result is labelled pilot.

## Spend
Per official run cap $1.50 (shim, reserved atomically per call); campaign cap $10 over all live-campaign run directories plus the unspent caps of active runs (runner, under a lock); the OpenRouter key's $40 limit is the backstop. The runner stops a run on: cost cap, call cap, more than 400 calls in one stage, more than 5 planning errors, a provider violation, more than 50% dropped members after 5 steps, a 40-minute stall, policy failure, or 4.5 h wall clock.

## Code
tools/live_policy/{live_policy.py, run_pipeline_with_policy.py, run_live_run.sh, live_runner.py, live_score.py, e1_analysis.py, placebo_calibration.json}, tools/legacy/asp_openrouter_shim.py (deployed to both host copies); sha256 recorded alongside this file.
