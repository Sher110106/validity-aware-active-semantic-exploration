# Verifier result

verdict: holds_with_corrections

## checks
- [ok] Stage alignment: stage k's plan pairs with the last point of stages/(k+1)/executed_path.json, and the current position is the end of stages/k (start of stages/1 for k=0). | Read audit.py and work_A/replay.py current_pos. In verify_stages.py I recomputed the gap between the first point of stages/(k+1) path and the stage-k current position on 13 stages, and read pose_log final_pose against the next path end for e1_00871_s42_official stage 3. | The gap is 0.0 m in all 13 stages. The stage-3 final pose (-2.53, 7.92) matches the stage-4 path end (-2.45, 7.80). Path z is 1.1, the same as candidate z (AGENT_HEIGHT 1.1). Verified: verify_audit/verify_stages.jsonl, key path_start_to_cur_m and stop_z.
- [ok] The camera model and occlusion match calculate_uncertainty.py: 90 deg cone, -10 deg pitch, 0.5-3.0 m (first stage) or 0.1-4.0 m (second stage), centre plus 8 corners in the frustum, centre-ray OBB occlusion by structure and door nodes. | I read the pinned Camera, points_are_in_view, _preprocess_groups, _visible_testing and _ray_intersects_obb against fastig.visible and audit.ref_geom. I then wrote my own pipeline (verify_stages.py) that calls the pinned cu.Camera and calc._visible_testing directly, not fastig. | The definitions match. On 12 used stages (all 8 arm x scene cells plus 4 random) my pinned-loop recomputation equals the audit's stages.jsonl exactly: n_unmapped, n_unmapped_sl, rho_total_U360, rho_total_Ucone, rho_total_U360_sl, U360_mean, U360_stop, pct_stop, U360_best, pct_best and yardstick counts. Verified: verify_audit/compare.json, all_equal true for 13 of 13 rows.
- [ok] Candidate regeneration and the top-10 filter: 396 stages replayed, 12 dropped for mismatch (9 filter_only, 2 official, 1 placebo), 384 used, with no disagreement against A. | I counted stages.jsonl and replay2_results.jsonl. In my own run the candidates came from the pinned first_stage loop (pinned_harness.first_stage), and I checked the top-10 against the last best_sample_poses line of pose_log.json, which I read myself. I also searched every stage directory of the 24 runs for a logged top-10 that was not replayed. | 396/384/12 confirmed, with 0 disagreements against A. All 12 sampled used stages match in my pinned replay, and the one dropped stage I tried (e1_00871_s42_official_60m stage 10) also fails to match in mine. No stage with a logged top-10 was left out. The brief's '383 of 394' is wrong; the files give 384 of 396. Verified.
- [ok] Unmapped rule: the primary rule is the code rule in live_policy.oracle_eligible (any-label object or same-label structure within 0.5 m xy, in either graph), and the brief's same-label wording is a variant. | I read live_policy.py lines 280-312 and wrote my own implementation of both rules in verify_stages.py. | The code rule matches oracle_eligible without the reach test. The brief's wording does differ from the code it cites. Both rules reproduce exactly on 12 stages. Verified.
- [ok] Frame check: reference objects and observed graphs share one frame. | I read frame_check.json and ran my own frame_offset.py (5 runs, mean xyz offset of same-label pairs within 1.5 m). | Medians are 0.16-0.68 m same-label against 3.0-5.7 m random-label, as stated. My check finds no systematic shift: mean offsets are at most 0.09 m per axis and the median |offset| is at most 0.19 m. But only 46-76% of observed objects lie within 0.5 m of a same-label reference object (4-17% more lie at 0.5-1.0 m), so the 0.5 m rule leaks some mapped objects into 'unmapped'. Verified: frame_check.json; verify_audit/frame_offset.json.
- [ok] Every number in Table 1 (rho median/IQR, stop, best and second-stage percentiles with CIs, sign tests, run tests, yardstick) for 4 arms and 8 arm x scene cells, plus the pooled row. | resummarize.py recomputes everything from stages.jsonl with my own code: medians, a bootstrap with a different seed, the sign test from U360_stop against U360_median, an exact sign-flip test, and pooled yardstick shares. I also read summary.json for the exact CI values. | All cells match to rounding. Bootstrap CIs differ only by seed noise (at most 0.006). Verified: verify_audit/resummary.json, audit/summary.json.
- [NOT OK] Table 2 (matched states) and its text: LLM files beat a placebo draw in 73 of 119 official stages, p=0.008; on 00853 the run medians are +0.12 to +0.25; on 00871 they are -0.03 to +0.04. | resummarize.py on cf_stages.jsonl. | Every Table 2 cell matches, and so do 73/119 and p=0.0084. But the 00853 run medians of actual minus placebo are 0.136, 0.119, 0.072 (e1_00853_s44_official_60m) and 0.254, so the range is +0.07 to +0.25, not +0.12 to +0.25. The 00871 values are 0.036, -0.014 and -0.025, which matches. Verified: resummarize.py output, CF official runmed.
- [ok] Yardstick: 6.9-9.0% of in-view objects are mapped against 0.3-0.8% of out-of-view objects, 10-28 times lower; with any label, 17-20% against 1-2%; 'about 1 in 11'. | resummarize.py yard() pools the counts. | The shares match (same-label in-view 0.069-0.090, out-of-view 0.0031-0.0079; any-label 0.166-0.200 against 0.0095-0.0223; ratios 11-28). Pooled in-view is 8.2%, which is about 1 in 12, not 1 in 11. That is minor. Verified.
- [ok] Decision rule 1 not met; rule 2 not met as written; rule 3 met in all four arms. | I checked the medians and CIs in summary.json decision_rules against the plan wording in SYNTHESIS_AND_NEXT_PLAN.md section 6. Then I ran sensitivity checks of my own: (a) unmapped radius 1.0 m, (b) the stop percentile among candidates within 0.5 m of any walked path in the scene (a stand-in for navigable floor), (c) a run-cluster bootstrap, and (d) 20 bootstrap seeds. | As specified, all three outcomes follow from the numbers. Rule 1: medians 0.198, 0.103, 0.123, 0.450, so not all at or below 0.1. Rule 2: official is 0.198, not near 0. Rule 3: lower bounds 0.583, 0.567, 0.582, 0.737. The outcomes are robust to radius 1.0 m (rho 0.17, 0.06, 0.04, 0.42; rules 1 and 2 still do not fire). Rule 3 for placebo is fragile, though. A run-cluster bootstrap gives 0.494-0.731, and among navigable-floor candidates the placebo stop percentile is 0.529 (0.482-0.576). Verified: verify_audit/sens_summary.json, boot_sens.json.
- [NOT OK] Placebo stops (0.609) do nearly as well as LLM stops (0.626), so the stop gain is mostly content-independent (inferred). | Navigable-floor restriction in sens.py. | The claim is weaker than stated. Against navigable-floor candidates the values are official 0.585 (0.541-0.627), placebo 0.529 (0.482-0.576), filter_only 0.611 and oracle 0.741. Off-floor candidates see fewer unmapped objects (placebo-arm means 10.0 against 16.1), so part of the stops' edge comes from being on the floor. The arms also differ in state. Verified numbers, inferred reading.
- [ok] Frontier proxy (distance to walked path) ranks better than ASP in the official, placebo and filter_only arms. | cf_stages.jsonl recomputed. | Per-arm frontier against ASP: 0.50 vs 0.20, 0.21 vs 0.10, 0.39 vs 0.12; in the oracle arm 0.40 vs 0.45. The frontier figures cover 361 stages and the ASP figures 384 (k=0 has no walked path). The claim holds as stated. Verified.
- [ok] Other stated numbers: variant _sl rho, move-cost rho, stop distances, observed-only IG zero share, yaw sensitivity, nothing written outside the audit directory. | resummarize.py, yaw_sensitivity.json, and find -newer on work_A. | _sl rho: 0.20, 0.12, 0.15, 0.40. rho(-d): 0.01, -0.03, -0.02, 0.05. The stop lies 0.235 m from the second-stage pick and 1.974 m from the first-stage best. Observed-only IG is zero for 0.484 of candidates. The largest change in rho from 36 yaws is 0.003, over 23 stages, not 24. No file in work_A is newer than audit.py. Verified.
- [ok] The scripts make no F1/AUC computation and no forbidden actions. | I read all six scripts. | No F1 or AUC appears anywhere. The scripts make no SSH calls and no network calls. Verified.

## corrections
- Table 2 text: the 00853 run medians of the official-minus-placebo rho are +0.07 to +0.25 (0.072, 0.119, 0.136, 0.254), not +0.12 to +0.25. The low run is e1_00853_s44_official_60m (verified, cf_stages.jsonl).
- Yardstick text: pooled, 8.2% of in-view counted objects get mapped, about 1 in 12. Per arm it runs from 1 in 14 to 1 in 11 (verified).
- Rule 3, add a robustness note. The within-run stage bootstrap that the brief asks for holds the runs fixed. A run-cluster bootstrap puts the placebo CI at 0.494-0.731, which crosses 0.5. Among candidates on navigable floor (within 0.5 m of any walked path in the scene) the placebo stop percentile is 0.529 (0.482-0.576). Official (0.585, 0.541-0.627), filter_only (0.611, 0.555-0.666) and oracle (0.741, 0.691-0.788) stay above 0.5 (verified, verify_audit/boot_sens.json, sens_summary.json). The rule fires as specified, but the placebo verdict is fragile.
- The inferred claim that the stop gain is 'mostly independent of content' is weaker than stated. Off-floor random candidates see fewer unmapped objects, so part of every arm's edge comes from stops being on the floor. Against floor candidates the official-minus-placebo gap grows from 0.017 to 0.056 (verified numbers; the reading is inferred, and the arms also differ in state).
- Add a radius sensitivity. With a 1.0 m unmapped radius, median rho(total, U_360) is 0.17, 0.06, 0.04 and 0.42 (official, placebo, filter_only, oracle). No rule outcome changes, but placebo and filter_only fall below 0.1 (verified, sens_summary.json). The frame check shows only 46-76% of observed objects within 0.5 m of a same-label reference, with no systematic offset (verified, frame_offset.json).
- Add a caveat. Oracle hypotheses are drawn from the same reference set that U counts, so the oracle arm's rho (and the oracle draw in Table 2) is partly high by construction. It gives the 'exact objects' level, not an independent test (inferred).
- Minor: yaw_sensitivity.json covers 23 stages, not 24. The frontier proxy covers 361 stages and ASP 384, and the frontier is below ASP in the oracle arm (0.40 vs 0.45).

## corrected results
## Short answer

The score does rank views by true unseen objects, but only weakly with LLM or placebo hypotheses and moderately with true objects (oracle).

- **Decision rule 1 does not fire.** Median per-stage rho(ASP total, U_360) is 0.20 for official, 0.10 placebo, 0.12 filter_only and 0.45 oracle.
- **Decision rule 2 does not fire as written.** Oracle is above 0.3, but official, at 0.20, is not near 0.
- **Decision rule 3 fires in all four arms under the stage bootstrap the brief specifies.** For placebo the result is fragile; see the robustness notes.
- **A hypothesis-free proxy, "far from the walked path", ranks views better than ASP's own score in the LLM and placebo arms.**

All numbers are verified from summary.json, cf_summary.json or stages.jsonl in /tmp/cvp_review/audit/audit/ unless marked inferred. A verifier recomputed 12 used stages, spread over all 8 arm x scene cells, with the pinned calculate_uncertainty.py loop (not fastig) and matched every per-stage value exactly (/tmp/cvp_review/audit/verify_audit/compare.json).

## Stages counted

| Step | Stages | Why |
|---|---|---|
| Stages replayed (24 runs in runs.txt) | 396 | Every stage with a logged top-10, a current position, hypothesis files and a stage k+1 walk. None was skipped before replay, and no stage with a logged top-10 was missed. |
| Dropped: replay top-10 ≠ logged top-10 | 12 | 9 filter_only, 2 official, 1 placebo. These are the same stages A's replay2_results.jsonl flags. |
| **Used for rho and percentile** | **384** | official 119 (7 runs), placebo 110 (7), filter_only 97 (6), oracle 58 (4). rho is defined in all 384. |
| Used for the yardstick | 365 | 19 final stages have no stage k+1 observed graph. |

The brief's "383 of 394" is wrong; the files give 384 of 396. The run set includes both e1_00853_s44_official_60m and its _rerun1, and e1_00871_s43_placebo_60m (1 stage), as runs.txt lists them.

## Table 1: rho, stop percentile, beats-median tests, yardstick

How to read the columns:
- rho cells show the median [IQR] over stages.
- Percentile cells show the mean (stage bootstrap 95% CI, resampling within each run, 2,000 draws).
- Sign test: wins-losses-ties against the candidate median, with a one-sided p.
- Run test: runs above 0.5, with an exact one-sided sign-flip p.
- Yardstick: share of in-view objects mapped at k+1 against out-of-view objects (same label within 0.5 m).

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

All 384 stages pooled: rho(total, U_360) has median 0.18 [-0.01, 0.43], and the stop percentile is 0.647 (0.623-0.670).

Other checks (verified):
- **Same-label unmapped rule.** rho(total, U_360) is 0.20, 0.12, 0.15 and 0.40 across the four arms.
- **Move cost.** The median of rho(-distance, U_360) is 0.01, -0.03, -0.02 and 0.05.
- **Where the stop lands.** The stop is a median 0.23 m from the second-stage pick and 1.97 m from the logged first-stage best.

### Robustness (added by the verifier; /tmp/cvp_review/audit/verify_audit/)

| Arm | rho(total, U_360), unmapped radius 1.0 m | Stop pct, radius 1.0 m | Stop pct among navigable-floor candidates | Stop pct, run-cluster bootstrap CI |
|---|---|---|---|---|
| official | 0.17 | 0.611 (0.572-0.651) | 0.585 (0.541-0.627) | 0.536-0.705 |
| placebo | 0.06 | 0.611 (0.570-0.651) | 0.529 (0.482-0.576) | 0.494-0.731 |
| filter_only | 0.04 | 0.609 (0.554-0.663) | 0.611 (0.555-0.666) | 0.534-0.725 |
| oracle_visible | 0.42 | 0.770 (0.717-0.815) | 0.741 (0.691-0.788) | 0.717-0.857 |

"Navigable floor" means candidates within 0.5 m (xy) of any walked path point from any run of the scene. That is a stand-in for the floor, not a navmesh. About 53-67% of candidates qualify. Off-floor candidates see fewer unmapped objects; in the placebo arm the means are 10.0 against 16.1.

## Table 2: matched states (extra check, cf_summary.json)

The robot state and the 300 candidates are the same in every column; only the hypothesis files change. Cells show the median per-stage rho(total, U_360), with rho(total, U_cone) in parentheses.

| Stages of arm | n | actual files | observed only | placebo draw | oracle draw | actual − placebo (paired) | oracle − placebo (paired) | frontier proxy: rho(dist to walked path, U_360) |
|---|---|---|---|---|---|---|---|---|
| official | 119 | 0.20 (0.30) | -0.07 (-0.03) | 0.19 (0.23) | 0.44 (0.71) | +0.07 (+0.05) | +0.31 (+0.48) | 0.50 |
| placebo | 110 | 0.10 (0.18) | -0.01 (0.02) | 0.16 (0.25) | 0.47 (0.70) | -0.03 (-0.03) | +0.26 (+0.45) | 0.21 |
| filter_only | 97 | 0.12 (0.25) | -0.10 (-0.03) | 0.12 (0.18) | 0.39 (0.65) | +0.04 (+0.06) | +0.31 (+0.48) | 0.39 |
| oracle_visible | 58 | 0.45 (0.65) | -0.08 (-0.14) | 0.01 (0.06) | 0.48 (0.65) | +0.28 (+0.51) | +0.30 (+0.52) | 0.40 |
| all | 384 | 0.18 (0.29) | -0.05 (-0.01) | 0.15 (0.19) | 0.44 (0.69) | +0.06 (+0.06) | +0.30 (+0.48) | 0.37 (361 stages with a walked path) |

On official stages, LLM files beat a placebo draw in 73 of 119 stages (one-sided p = 0.008, stage level). The edge comes from 00853, where the run medians are **+0.07 to +0.25** (corrected; the low run is e1_00853_s44_official_60m at +0.07). On 00871 it is about zero, with run medians of -0.03 to +0.04.

The oracle draws are taken from the same reference set that U counts, so the oracle column is partly high by construction (inferred).

## Decision rules

- **Rule 1** (rho ≤ 0.1 in every arm, oracle included): **not met** (verified). The U_360 medians are 0.20, 0.10, 0.12 and 0.45; the U_cone medians are 0.30, 0.18, 0.25 and 0.65. With a 1.0 m unmapped radius the U_360 medians are 0.17, 0.06, 0.04 and 0.42, so the rule still fails.
- **Rule 2** (oracle rho ≥ 0.3 while LLM and placebo stay near 0, with "near 0" read as |median| < 0.1): **not met as written** (verified). Official is 0.20, and with the 1.0 m radius it is still 0.17.
  - On matched states, true-object hypotheses raise rho over placebo by about +0.30 (U_360) and +0.48 (U_cone), while LLM hypotheses add about +0.06.
  - Inferred: content quality is a limit in substance, though the pre-set rule does not fire.
- **Rule 3** (live-stop percentile CI wholly above 0.5): **met in all four arms under the specified within-run stage bootstrap** (verified). The lower bounds are 0.583, 0.567, 0.582 and 0.737.
  - The placebo verdict is fragile. A run-cluster bootstrap gives 0.494-0.731, and against navigable-floor candidates the placebo stop percentile is 0.529 (0.482-0.576). Official, filter_only and oracle stay above 0.5 under both checks (verified).
  - Per scene, the CI touches or crosses 0.5 for official/00853 (lower bound 0.495-0.500 across 20 bootstrap seeds), placebo/00871 and filter_only/00871.
  - Inferred: part of every arm's edge over random candidates comes from stops lying on the floor. Against floor candidates, LLM stops (0.585) lead placebo stops (0.529) by more than the raw gap (0.626 against 0.609) suggests. The arms also differ in state, so this is not a clean content test.

## Yardstick (step 5)

Of the unmapped objects counted in the live stop's U_360, 6.9-9.0% appear in the next stage's map (same label within 0.5 m). For unmapped objects out of view the figure is 0.3-0.8%, about 11-28 times lower. With any label it is 17-20% against 1-2% (verified).

So U_360 does pick out the objects that get mapped next. But pooled, only about 1 in 12 counted objects is mapped, so U_360 overcounts what a stop yields. Inferred causes:
- walls the robot has not yet mapped do not block the view (the reference has no wall nodes; one sampled stop counts 60 unmapped objects in view);
- the detector and mapper miss objects (H4).

## Other findings

- **Frontier proxy.** "Far from the walked path" ranks candidates by U_360 better than ASP's score in the official (0.50 vs 0.20), placebo (0.21 vs 0.10) and filter_only (0.39 vs 0.12) arms, but not in the oracle arm (0.40 vs 0.45) (verified). U ignores unmapped walls, which may favour any outward-pulling rule (inferred).
- **Observed-only IG.** IG from the observed graph alone is zero for about 48% of candidates, and its median rho is -0.05 (verified).

## Builder's method and caveats (first draft)

Appended 2026-11-12 from the first-draft builder file, which is removed from the tree. The corrected results are in the sections above. Scratch paths are generalised.

### Method
Python: .venv_offline/bin/python, run with -B so nothing is written into work_A. I imported reviewer A's work_A/fastig.py, replay.py and replay2.py read-only, along with the pinned calculate_uncertainty.py that they load.

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

### Caveats
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
- The reviewer scratch directory (185 MB) holds regenerated placebo and oracle YAMLs and can be deleted. Nothing outside the reviewer scratch directory was written: work_A/__pycache__ mtimes predate this run (verified).
