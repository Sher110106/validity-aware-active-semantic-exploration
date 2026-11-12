# Pre-registration addendum: live campaign E3 (oracle_visible vs placebo), 2026-10-28

Frozen before the first counted oracle run; sha256 in /workspace/runs/live_campaign/PREREGISTRATION_E3.sha256. Everything not stated here follows PREREGISTRATION_E1.md and the campaign DEVIATIONS.md (items 17-21 record the oracle code, the gates, the scheduler and the analysis fix).

Pinned (sha256):
- oracle_sets.json a7b35313bb9c0f9e7bb72771290b0b9f6b9788d48c49b0374d990ca6339b0b34
- hm3d_refs_work/label_mapping.json 6035b772d0bf04e354e96e88e66f22991d0d412292af0a6516a2f43462128a54
- live_policy.py 6e4710cfd212c88b7d5e5337041139a59bb867b35ab1eadf5f24f08af7a4a4cc
- live_runner.py 6f6c14b7bdc05ac1314e4acc355ae9b5a13494a527c4253d87ab2e253b315a8f
- campaign_sched.py ab47ab4805a06e6bdfb630c53ca9024a253a8b5c6fd3f46e9754c4049e58275d
- stage_diagnostics.py 83e21d56ea483466d29a47a715798bac22bc22d57bc00565548978bb077cd695
- e1_analysis.py a6e756a074422883af610b1aebdf4d7cc20cfe6c98e550f4ea419943286d6558

## Disclosure
E3 is registered after the AUCs of four of its six placebo comparator runs were known (00853/42, 00871/42, 00853/43, 00853/44). E3 reuses E1's placebo runs, so E1 and E3 share errors, and the oracle runs do not run at the same time as their comparators. The campaign is a pilot (DEVIATIONS 1, 5, 16).

## Question
Do true object hypotheses, drawn at random per ensemble member at the placebo's count and passed through the author's information gain and detector, raise the live robot's object F1 AUC to 60 m over random hypotheses of the same shape? This is an exact-object control, not a bound on what any guesser could do: the planner rewards disagreement between members (calculate_uncertainty.py:501-522), so a guesser whose members disagree differently, or that predicts rooms, could do better or worse.

## Arm: oracle_visible (as coded: live_policy.oracle_eligible, oracle_graph)
- Candidate set per scene: every object node of the primary HM3D reference (`<scene>_hm3d_reference.yaml`: annotation labels that map into the pipeline vocabulary; doors were already excluded when the reference was built), pipeline frame; 180 objects on 00853, 232 on 00871. No run's map chooses it; it is the answer key the arms are scored on.
- Eligible per stage and track: candidates more than 0.5 m (xy) from every observed object node, and from every observed structure node with the same label (Hydra maps most windows and curtains as structure), and within 5.0 m (xy) of an observed room centre (any observed node if no room is mapped yet).
- Per member (seed key [SEED, stage, graph_id], with the placebo's attempt and rerun salts): rooms from the placebo's process on the same stream (placebo_graph with the object count forced to zero); then a count drawn from the placebo's count distribution (Poisson(10) clipped 6-16; its own draw, not the placebo member's number), taken without replacement from the eligible set; exact reference label, position and dimension; is_predicted true; linked to the nearest room, observed or hypothesised, so the room term of information gain carries placebo room names. If nothing is eligible the member gets a fresh placebo draw and is flagged fallback. Logged per member: n_candidates_in_reach, n_drawn, fallback.
- Rooms equal the placebo partner's only while the two runs' observed graphs are the same (in practice near stage 0); for 00871/43 the partner is a salted rerun, so they differ from the start.
- Pacing: the exact no_llm_delay_schedule of the cell's placebo run, read from that run's run_manifest.txt (scheduler field pacing_from). An oracle rerun is named <run>_rerun1, keeps that schedule, draws a salted stream, and is analysed under the rerun name. Pacing matches per decision, not per metre; stages per run, metres per stage and sleep seconds per metre are reported as covariates.
- max_hours 7.5; max_cost_usd 0.

## Cells
Scenes 00853 and 00871, seeds 42 and 43 (four runs), 60 m. Seed 44 (two runs) only if, at the 2026-10-29 18:00 IST check, the scheduler's queue is projected to finish by 2026-10-31 02:00 IST; the decision is logged in DEVIATIONS before any seed-44 oracle job is queued, and it looks only at host time. Comparators: the E1 placebo runs of the same cells, reused.

## Gates passed before any counted run
- P1 (code check, true by construction): on 47 saved observed graphs from six finished runs, four members per track with the live seed key, oracle new-object precision 1.0 at 0.5 m (1,868 of 1,868), no relabels, no fallback, median 103 candidates in reach, median 10 drawn (hm3d_refs_work/oracle_positive_control_v2.json).
- P2 (dry run dryrun_oracle_00871_s42_10m, 10 m, 60 s pacing): target reached at 14.55 m in 2 stages, 0 planning errors, 24 member draws with 83-99 candidates in reach and no fallback. The plan's box clause failed as written: the stage-0 sampling box was offset from the placebo run's by 2.20 m and 2.45 m in y, with similar widths (10.33 x 10.55 vs 10.76 x 10.80 m), so a box test could not show what it was meant to. Replacement rule, fixed before the result was computed: xy distance of each hypothesis to the nearest observed room centre, oracle vs placebo, on the saved graphs; pass if the oracle's 90th percentile is within 1 m of the placebo's, else reach 3.5 m and P1 and P2 repeated. Result: median 2.01 vs 1.80 m, 90th percentile 4.11 vs 3.32 m (difference 0.79 m): pass; reach stays 5.0 m.
- z: no filter. 00853 objects span 0.00-2.52 m and 00871 -0.02-3.02 m; the largest gap between consecutive object heights is 0.18 m (00853) and 0.16 m (00871); the objects above 2 m are ceiling fans, curtains, lamps, and on 00871 also picture frames and windows. One floor each. The plan's trigger (span above 3 m) fires on 00871 and is not applied, because the filter would remove same-floor objects the arms are scored on.
- Frame: established by the scorer (observed graphs match the same reference the oracle copies positions from; wrong transforms score 0.00-0.03 F1) and by P1. No in-run test here claims to catch a frame error.
- Base rate, from non-oracle runs before any counted oracle run (stage_diagnostics.py; hm3d_refs_work/base_rates_pre_E3.json): among eligible candidates within 3.5 m (xy) of the reached viewpoint at stage k, the share mapped at stage k+1: 00853 official 12.3% and 9.9%, placebo 10.1%, 11.1% and 9.5%; 00871 official 5.2% and 5.5%, placebo 6.8%.

## In-run gate: drawn vs undrawn
Stage alignment from the pinned code: hypotheses for stage k are written in stages/k, and the walk driven after stage k's plan is saved to stages/(k+1)/executed_path.json (exploration_pipeline.py:654, 881-889, 913). For stage k: reached viewpoint = last point of stages/(k+1)/executed_path.json (world_frame_path); next map = stage k+1's observed graphs (k+2 as a lag check); stages without that k+1 data are dropped.

Per stage and track, the eligible set follows the rule above, and the union of the track's member draws is a random subset of it. Drawn and undrawn eligible candidates are compared on (i) approach: within 3.5 m (xy) of the reached viewpoint; (ii) mapping: same label within 0.5 m (xy) of an object or structure node in stage k+1's observed graphs. Statistic: pooled rate difference (drawn minus undrawn) over the run; p from 2,000 permutations of the drawn labels within each stage and track; one-sided (drawn greater), fixed now. This is a gate on whether the arm works as intended, not a finding. Also reported: the same split for candidates within 3 m of the path walked before stage k ("scanned") and beyond it, the k+2 mapping gap, and every arm's share of new hypotheses in scanned space.

Verdict per scene from the first finished oracle run on that scene (later runs reported):
- broken: approach p >= 0.05. Oracle runs archived as FAILED_ATTEMPT, one fix, rerun; a second broken verdict ends E3 and the gate results are the result.
- detector-limited: approach p < 0.05 and mapping p >= 0.05.
- working: approach p < 0.05 and mapping p < 0.05.
Gaps are reported beside the p values with the scene's base rate. No absolute gap threshold is used: drawn and undrawn candidates sit side by side, so a robot that steers to drawn objects also passes undrawn ones, and the size of the gap reflects that mixing rather than whether the arm works (the 2-stage dry run gave an approach gap of +0.002, p 0.53, on 360 candidate rows; a full run gives about 3,000).

Descriptive only: the share of unique drawn reference objects later found in the final map (last stage left out), and for every arm the share of unique hypotheses (label and 0.5 m cell) later found.

## Metric, references, test
Primary: author-faithful object F1 AUC to 60 m against the HM3D reference. The frontier-made reference is descriptive for E3, because the oracle holds the HM3D answer key. Primary contrast: oracle_visible minus placebo, scene-blocked exact permutation, two-sided, alpha 0.05, its own family (E1 and E2 stay a Holm pair as registered; Holm over all three is reported as a sensitivity line). Secondary: oracle_visible minus official. Sensitivity: the same test on AUC to 50 m; an effect is claimed only if the 60 m and 50 m results agree in sign. Intervals: bootstrap CI and the permutation-inverted 95% interval from e1_analysis.py; "effects up to b are not ruled out" uses the wider. Null form: "No detectable difference: d = ... (95% CI a to b). The design had 80% power only for differences of about x (normal approximation). Effects up to b are not ruled out." Covariates: stages per run, metres per stage, sleep seconds per metre, F1 at 60 m beside the AUC, fallback share.

## Exclusions
As E1 (below 50 m, one rerun). A run with fallback on more than 20% of member draws is labelled diluted and left out of the primary. Analysis with e1_analysis.py --seeds 42,43 (or 42,43,44 if seed 44 runs), exclusions from EXCLUDED_*.json markers, one counted run per cell.

## Reading rules (fixed now)
Read the AUC only after the gate verdict. Working and p < 0.05: "exact objects drawn at random per member raised F1 AUC over the placebo by d [CI]". Working and no detectable difference: the null form. Detector-limited: report the AUC with the gate table and claim only that exact objects delivered this way did not raise map gain through this detector. Any sentence that the loop converts exact but not LLM hypotheses needs the oracle minus official contrast at p < 0.05 with its CI; otherwise write "the oracle beat the placebo by d [CI]; the LLM did not detectably; oracle minus official = d [CI]". A null rules out this kind of content through this information gain, not guessers whose member agreement tracks confidence or that predict rooms. With observed_only not run, the design cannot say whether hypotheses of any kind change map gain.
