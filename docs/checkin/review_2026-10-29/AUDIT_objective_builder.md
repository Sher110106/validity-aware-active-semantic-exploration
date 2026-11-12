# Builder result

## method
Python: /Users/sher/project/cvp/project/.venv_offline/bin/python, run with -B so nothing is written into work_A. I imported reviewer A's work_A/fastig.py, replay.py and replay2.py read-only, along with the pinned calculate_uncertainty.py that they load.

1. Frame check (frame_check.py). In 10 sampled stages across 4 runs, each observed object node or structure node sits a median 0.16-0.68 m (xy) from the nearest reference object with the same label, and 3.0-5.7 m from one with a random other label. So the reference objects and the observed graphs share one frame (verified: frame_check.json).

2. Replay (audit.py). For each stage I regenerated the candidates and their first-stage scores with fastig.Scorer.first_stage, using A's file order (replay2.gids_for) and RNG offset (replay.stage_meta). The run's own top-10 check is the same as A's: allclose against parsed_runs pose_tops[-1].

3. Unmapped. Primary rule: the code in live_policy.oracle_eligible without the reach test, applied to the union of graph0 and graph1 at stage k. A reference object is mapped if it lies within 0.5 m (xy) of an observed object of ANY label, or of a structure node with the SAME label. The brief describes the rule as "same-label object or structure", which does not match the code. I ran that version too as a variant (suffix _sl).

4. Visibility. I used fastig.visible, the vectorized form of the pinned camera model. Targets are the oracle-set reference objects with identity orientation. Occluders are the structure nodes and door-named nodes of both observed graphs, as in _preprocess_groups. Each object is checked at its centre plus 8 box corners, with a centre-ray box occlusion test.
   - U_cone uses the first-stage camera (0.5-3.0 m) at the candidate's own yaw.
   - U_360 uses the second-stage range (0.1-4.0 m) and takes the union over 12 yaws, 30 deg apart, with the -10 deg pitch. A 36-yaw check changed the per-stage rho by at most 0.003 (yaw_sensitivity.json).

5. Per stage I computed Spearman rho (scipy, average ranks for ties) between U_360 or U_cone and two scores: the ASP total (IG - 0.2*d), which is the score that ranks candidates, and IG alone.
   - The live stop is the last world_frame_path point of stages/(k+1)/executed_path.json, at z = 1.1.
   - The logged first-stage best is pose_tops[-1].top[0]. The logged second-stage pick is the pose_finals 'final' entry nearest the stop.
   - Percentile among the candidates' U_360 is mid-rank: share below plus half the ties.
   - Yardstick: of the unmapped objects in the stop's U_360, the share that show up in stage k+1's graphs (same label within 0.5 m xy), against unmapped objects not in view. I also report an any-label version.

6. Summaries (summarize.py):
   - median and IQR of per-stage rho;
   - mean percentile with a stage bootstrap, resampling stages within each run, 2,000 draws, seed 0;
   - a stage-level one-sided binomial sign test of "stop U_360 > candidate median", with ties dropped;
   - a run-level one-sided exact sign-flip test on run-mean percentiles minus 0.5.

7. Extra matched-state check, not in the brief (counterfactual.py). On every used stage I held the robot state and the 300 candidates fixed and rescored them with four hypothesis sets: actual, observed-only, a fresh live_policy.placebo_graph draw, and a fresh live_policy.oracle_graph draw from oracle_sets.json (the live oracle arm's generator). I also computed a hypothesis-free frontier proxy: each candidate's distance to the path walked through stage k.

I computed no F1 or AUC for any run. I ran no SSH, spent no money, and ran neither Habitat nor the pipeline.

## results
## Short answer

Weakly for the LLM and placebo arms, moderately for the oracle arm. The score does rank views by true unseen objects, but only a little unless the hypotheses are true objects.

- **Decision rule 1 does not fire.** Median per-stage rho(ASP total, U_360) is 0.20 for official, 0.10 placebo, 0.12 filter_only and 0.45 oracle.
- **Decision rule 2 does not fire as written.** Oracle is above 0.3, but official, at 0.20, is not "near 0".
- **Decision rule 3 fires in all four arms.**
- **The placebo arm's stops do almost as well as the LLM arm's.**
- **A hypothesis-free proxy ranks views better than ASP's own score does in the LLM and placebo arms.** The proxy is "far from the walked path".

All numbers are verified from summary.json, cf_summary.json or stages.jsonl unless marked inferred.

## Stages counted

| Step | Stages | Why |
|---|---|---|
| Stages replayed (24 runs in runs.txt) | 396 | Every stage that has a logged top-10, a current position, hypothesis files and a stage k+1 walk. None was skipped before replay (skipped_before_replay.json = []). |
| Dropped: replay top-10 ≠ logged top-10 | 12 | 9 filter_only, 2 official, 1 placebo. Same flags as A's replay2_results.jsonl, with no disagreement. List: summary.json `dropped_mismatch`. |
| **Used for rho and percentile** | **384** | official 119 (7 runs), placebo 110 (7), filter_only 97 (6), oracle 58 (4). U_360 and U_cone varied in every stage, so rho is defined for all 384. |
| Used for the yardstick | 365 | 19 final stages have no stage k+1 observed graph. |

Note: the brief says A's replay matched 383 of 394. A's replay2_results.jsonl has 396 unique stages with 384 matches. My replay gives the same 396/384 (verified).

The counted runs include both e1_00853_s44_official_60m and its _rerun1, and e1_00871_s43_placebo_60m, which contributes 1 stage. All three are in runs.txt.

## Table 1: rho, stop percentile, beats-median tests, yardstick

How to read the columns:
- rho cells show the median [IQR] over stages.
- Percentile cells show the mean (bootstrap 95% CI).
- Sign test: wins-losses-ties, one-sided p, treating stages as independent.
- Run test: runs whose mean percentile is above 0.5, with an exact one-sided sign-flip p. The floor is 1/2^n.
- Yardstick: share of in-view objects found at k+1 vs share of out-of-view objects (same label within 0.5 m).

| Arm / scene | Stages / runs | rho(total, U_360) | rho(total, U_cone) | rho(IG, U_360) | Stop pct | Logged best pct | 2nd-stage pick pct | Sign test (stop) | Run test (stop) | Yardstick |
|---|---|---|---|---|---|---|---|---|---|---|
| official | 119/7 | 0.20 [0.06, 0.44] | 0.30 [0.09, 0.40] | 0.25 [0.11, 0.37] | 0.626 (0.583-0.668) | 0.605 (0.564-0.647) | 0.645 (0.608-0.681) | 82-33-4, p=2.8e-6 | 7/7, p=0.008 | 6.9% vs 0.36% |
| placebo | 110/7 | 0.10 [-0.11, 0.33] | 0.18 [-0.01, 0.33] | 0.12 [-0.03, 0.27] | 0.609 (0.567-0.651) | 0.545 (0.499-0.589) | 0.597 (0.553-0.642) | 71-37-2, p=6.9e-4 | 6/7, p=0.016 | 8.8% vs 0.31% |
| filter_only | 97/6 | 0.12 [-0.06, 0.37] | 0.25 [0.06, 0.37] | 0.19 [0.10, 0.30] | 0.637 (0.582-0.692) | 0.631 (0.583-0.680) | 0.649 (0.597-0.701) | 67-27-3, p=2.2e-5 | 4/6, p=0.062 | 8.5% vs 0.31% |
| oracle_visible | 58/4 | 0.45 [0.24, 0.58] | 0.65 [0.56, 0.69] | 0.45 [0.35, 0.52] | 0.783 (0.737-0.824) | 0.730 (0.682-0.781) | 0.782 (0.734-0.826) | 50-6-2, p=5.1e-10 | 4/4, p=0.062 | 9.0% vs 0.79% |
| official/00853 | 67/4 | 0.13 [-0.03, 0.38] | 0.23 | 0.23 | 0.560 (0.497-0.624) | 0.508 | 0.582 | 39-25-3, p=0.052 | 4/4, p=0.062 | 7.5% vs 0.47% |
| official/00871 | 52/3 | 0.28 [0.15, 0.46] | 0.36 | 0.26 | 0.710 (0.650-0.764) | 0.730 | 0.726 | 43-8-1, p=3e-7 | 3/3, p=0.125 | 6.5% vs 0.24% |
| placebo/00853 | 54/3 | 0.22 [-0.08, 0.39] | 0.22 | 0.12 | 0.679 (0.622-0.729) | 0.597 | 0.677 | 42-12-0, p=3e-5 | 3/3, p=0.125 | 9.9% vs 0.38% |
| placebo/00871 | 56/4 | 0.03 [-0.12, 0.18] | 0.15 | 0.11 | 0.541 (0.476-0.604) | 0.495 | 0.520 | 29-25-2, p=0.34 | 3/4, p=0.125 | 7.6% vs 0.26% |
| filter_only/00853 | 52/3 | 0.26 [0.04, 0.44] | 0.30 | 0.20 | 0.709 (0.638-0.774) | 0.638 | 0.704 | 42-10-0, p=5e-6 | 3/3, p=0.125 | 10.8% vs 0.46% |
| filter_only/00871 | 45/3 | 0.00 [-0.13, 0.22] | 0.12 | 0.17 | 0.553 (0.461-0.643) | 0.624 | 0.586 | 25-17-3, p=0.14 | 1/3, p=0.50 | 6.0% vs 0.20% |
| oracle/00853 | 33/2 | 0.51 [0.23, 0.61] | 0.66 | 0.49 | 0.756 (0.693-0.814) | 0.712 | 0.753 | 27-4-2, p=2e-5 | 2/2, p=0.25 | 10.7% vs 1.15% |
| oracle/00871 | 25/2 | 0.40 [0.26, 0.51] | 0.60 | 0.43 | 0.818 (0.756-0.877) | 0.754 | 0.821 | 23-2-0, p=1e-5 | 2/2, p=0.25 | 7.6% vs 0.43% |

All 384 stages pooled: rho(total, U_360) median 0.18 [-0.01, 0.43]; stop percentile 0.647 (0.623-0.670).

Other checks (verified, summary.json and stages.jsonl):
- **Variant rule.** With the same-label unmapped rule, rho(total, U_360) moves little: 0.20, 0.12, 0.15 and 0.40 across the four arms.
- **Move cost.** rho(-distance, U_360) has a median near 0 in every arm (0.01, -0.03, -0.02, 0.05), so the move-cost term neither drives nor blocks the ranking.
- **Where the stop lands.** The stop is a median 0.23 m from the second-stage pick and 1.97 m from the logged first-stage best.

## Table 2: matched states (extra check, cf_summary.json)

Here the robot state and the 300 candidates are the same in every column; only the hypothesis files change. Cells show median per-stage rho(total, U_360), with rho(total, U_cone) in parentheses.

| Stages of arm | n | actual files | observed only | placebo draw | oracle draw | actual − placebo (paired) | oracle − placebo (paired) | frontier proxy: rho(dist to walked path, U_360) |
|---|---|---|---|---|---|---|---|---|
| official | 119 | 0.20 (0.30) | -0.07 (-0.03) | 0.19 (0.23) | 0.44 (0.71) | +0.07 (+0.05) | +0.31 (+0.48) | 0.50 |
| placebo | 110 | 0.10 (0.18) | -0.01 (0.02) | 0.16 (0.25) | 0.47 (0.70) | -0.03 (-0.03) | +0.26 (+0.45) | 0.21 |
| filter_only | 97 | 0.12 (0.25) | -0.10 (-0.03) | 0.12 (0.18) | 0.39 (0.65) | +0.04 (+0.06) | +0.31 (+0.48) | 0.39 |
| oracle_visible | 58 | 0.45 (0.65) | -0.08 (-0.14) | 0.01 (0.06) | 0.48 (0.65) | +0.28 (+0.51) | +0.30 (+0.52) | 0.40 |
| all | 384 | 0.18 (0.29) | -0.05 (-0.01) | 0.15 (0.19) | 0.44 (0.69) | +0.06 (+0.06) | +0.30 (+0.48) | 0.37 (361 stages with a walked path) |

On official stages, LLM files beat a placebo draw in rho(total, U_360) in 73 of 119 stages (one-sided p = 0.008 at stage level, verified). The edge comes from 00853 (run medians +0.12 to +0.25). On 00871 it is about zero (run medians -0.03 to +0.04).

## Decision rules

- **Rule 1** (rho ≤ 0.1 in every arm, oracle included → "the viewpoint score does not rank views by true unseen objects"): **not met** (verified). Medians are 0.20, 0.10, 0.12 and 0.45 for U_360, and 0.30, 0.18, 0.25 and 0.65 for U_cone. Only placebo comes near 0.1. The claim should not be made. The score ranks weakly with LLM or placebo hypotheses and moderately with true objects.
- **Rule 2** (oracle rho ≥ 0.3 while LLM and placebo stay near 0 → "content quality is a limit too"): **not met as written** (verified). I read "near 0" as |median| < 0.1. Oracle, at 0.45, clears 0.3, but official (0.20) and filter_only (0.12) are not near 0, and placebo (0.10) is at the edge.
  - The matched-state check shows what the rule is meant to detect. On the same states, true-object hypotheses raise rho by about +0.30 (U_360) and +0.48 (U_cone) over placebo, while LLM hypotheses add only about +0.06 (verified, Table 2).
  - Inferred: hypothesis content does steer the score toward true unseen objects, and DeepSeek's content sits much nearer placebo than oracle. So "content quality is a limit" holds in substance, though the pre-set rule does not fire.
- **Rule 3** (live-stop percentile CI wholly above 0.5 → "stops do beat random candidates on true unseen objects"): **met in all four arms** (verified). The lower bounds are 0.583, 0.567, 0.582 and 0.737. Run-level tests agree for official (7/7, p=0.008) and placebo (6/7, p=0.016). Filter_only (4/6, p=0.062) and oracle (4/4, p=0.062, the floor) do not reach significance.
  - Per scene, the CI touches or crosses 0.5 for official/00853 (0.497-0.624), placebo/00871 (0.476-0.604) and filter_only/00871 (0.461-0.643).
  - Inferred: most of this gain does not depend on content, because placebo stops (0.609) do nearly as well as LLM stops (0.626). Only oracle stops stand clearly higher (0.783).

## Yardstick (step 5)

Of the unmapped objects counted in the live stop's U_360, 6.9-9.0% appear in the next stage's map (same label within 0.5 m). For unmapped objects out of view the figure is 0.3-0.8%, about 10-28 times lower; with any label, it is 17-20% against about 1-2% (verified). So U_360 does pick out the objects that get mapped next. But only about 1 in 11 counted objects is mapped, so U_360 overcounts what a stop really yields. Inferred causes:
- walls the robot has not yet mapped do not block the view (the reference has no wall nodes);
- the detector and mapper miss objects (H4).

## Other findings

- **Frontier proxy.** A hypothesis-free rule, "candidates far from the walked path", ranks candidates by U_360 with median rho 0.37 overall. That beats ASP's own score in the official (0.20), placebo (0.10) and filter_only (0.12) arms (verified, cf_summary.json). Inferred: in this setting a frontier-style ranking is as good a guide to true unseen objects as LLM-steered IG, or better.
- **Observed-only IG.** IG from the observed graph alone is zero for about 48% of candidates and does not rank by true unseen objects (median rho -0.05, verified). So any positive rho comes from the hypotheses, including random ones. Inferred: hypotheses placed in unexplored space act as a generic pull outward, and true objects add a real but moderate extra pull.

## decision rules
- Rule 1 (rho <= 0.1 in every arm, oracle included): NOT MET. Median per-stage rho(ASP total, U_360): official 0.20, placebo 0.10, filter_only 0.12, oracle 0.45; U_cone: 0.30, 0.18, 0.25, 0.65 (verified, summary.json decision_rules). Do not claim that the viewpoint score does not rank views by true unseen objects.
- Rule 2 (oracle rho >= 0.3 while LLM and placebo stay near 0, with near 0 read as |median| < 0.1): NOT MET AS WRITTEN. Oracle is 0.45, but official (0.20) and filter_only (0.12) are not near 0, and placebo (0.10) is at the edge (verified). On matched states, oracle content raises rho over placebo by +0.30 (U_360) and +0.48 (U_cone), against +0.06 for LLM content (verified, cf_summary.json). So in substance content quality is a limit (inferred), but the pre-set rule does not fire.
- Rule 3 (live-stop percentile CI wholly above 0.5): MET in all four arms: official 0.626 (0.583-0.668), placebo 0.609 (0.567-0.651), filter_only 0.637 (0.582-0.692), oracle 0.783 (0.737-0.824) (verified). Run-level exact tests: official p=0.008, placebo p=0.016, filter_only p=0.062, oracle p=0.062 (the floor). Per scene the CI is not wholly above 0.5 for official/00853, placebo/00871 or filter_only/00871. The gain is mostly independent of content: placebo stops come close to LLM stops (inferred).

## caveats
- The definition of 'unmapped' in the brief does not match the code it cites. live_policy.oracle_eligible counts a reference object as mapped if it lies within 0.5 m of an observed object of ANY label or of a structure node with the SAME label; the brief says 'same-label object or structure'. I used the code rule as primary and report the same-label version as _sl. The rho results change little (verified).
- U_360 and U_cone count only occlusion by observed structure and door boxes. The reference graphs have no wall nodes, so objects behind walls the robot has not yet mapped count as visible. This inflates U, especially toward unexplored space, and helps explain why only about 7-9% of in-view objects are mapped at the next stage. It may favour any outward-pulling score, including placebo and the frontier proxy (inferred).
- Arms differ in trajectories and states, so comparing rho across arms mixes state with content. The matched-state check (Table 2) removes that, but it uses a single placebo draw and a single oracle draw per stage, so its per-stage numbers are noisy.
- Stage-level sign tests treat stages as independent, which is optimistic because stages within a run are correlated. The run-level exact tests have floors of 1/2^n runs: 0.0078 for 7 runs, 0.0156 for 6 and 0.0625 for 4. Oracle has only 4 runs (2 per scene).
- Run set as given in runs.txt: it includes both e1_00853_s44_official_60m and its _rerun1, and e1_00871_s43_placebo_60m, which has 1 stage. Each counts as a separate run in the bootstrap and the run tests.
- The brief says A matched 383 of 394 stages. A's replay2_results.jsonl and my replay both give 384 of 396; the files win.
- Spearman rho correlates with the ASP total (IG - 0.2*d), the score that actually ranks candidates. Rho with IG alone is also reported and is similar.
- The camera is placed at z = 1.1 for candidates and stops alike, matching AGENT_HEIGHT and the logged path height. Reference objects use identity orientation. U_360 uses 12 yaws; the 36-yaw check moved rho by at most 0.003.
- The decision rules give no threshold for 'near 0' in rule 2. I used |median rho| < 0.1.
- No F1 or AUC was computed for any run. E3 runs entered only as planner states and paths.
- The scratch directory /tmp/cvp_review/audit/audit/tmp (185 MB) holds regenerated placebo and oracle YAMLs and can be deleted. Nothing outside /tmp/cvp_review/audit/audit was written: work_A/__pycache__ mtimes predate this run (verified).