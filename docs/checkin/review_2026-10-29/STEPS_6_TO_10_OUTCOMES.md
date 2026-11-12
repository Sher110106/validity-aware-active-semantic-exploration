# Plan steps 6-10: outcomes

2026-10-30. This reports the "next 2-3 weeks" part of SYNTHESIS_AND_NEXT_PLAN.md §6, run overnight on 10-29/30 under three pre-registrations frozen before any result existed:
- tools/live_policy/PREREGISTRATION_BENCH.md (step 6, sha256 2571a7ef…, 22:28 IST);
- PREREGISTRATION_FRONTIER_SEEDS.md (step 7, 22:24 IST);
- PREREGISTRATION_DETERMINISM.md (step 8, 22:31 IST).

Nothing here changes a registered E1-E3 result. Spend: $0.

## 1. Summary

- **Step 6, offline bench: no rule passes, so the plan stops live work.** On 384 saved stages, no decision rule makes exact-object guesses beat random guesses by the required 30%. The best rule manages 15% (ratio 0.850, CI 0.804-0.893, against a bar of 0.70). No rule passes the registered test that DeepSeek's guesses beat random ones by more than two random draws differ. R3 comes nearest, with 1.03 objects less regret than placebo A (CI 0.36-1.76): past the 0.82 floor at the point estimate, but its CI does not clear it. An independent verifier re-derived every pick and every decision number and got the same answer. The wall-aware yardstick passes its pre-registered check on one reading only, so read the bench numbers as provisional; the stop decision holds either way.
- **Step 7, seeded frontier explorer: neither LLM nor random guesses beat nearest-frontier exploration on these two homes.**
  - Official − frontier: −0.012 AUC, CI −0.053 to +0.029, p 0.47.
  - Placebo − frontier: −0.025, CI −0.050 to +0.002, p 0.07, Holm 0.14.
  - Both point estimates favour frontier. The frontier runs needed no LLM and took 22-38 minutes each.
  - An independent recompute matches.
  - Caveat: ASP's paths enter wall-map cells and frontier's almost never do, so the comparison may be tilted, in an unknown direction.
- **Step 8, quiet-wait snapshot: same-seed runs still split at the first stop.** No pair of three replicates had matching stage-0 maps, and two of three pairs stopped 3.6-3.8 m apart. The copy was not early: the wait never saw the map file change, and each copied file already held the mapper's poses to the end of the scan. In one run the mapper simply made fewer objects from the same scan and never recovered them, so a later snapshot would likely not help [I]. As registered, future designs need at least 5 replicates per cell; a replay simulator is the other route (not registered).
- **Steps 9 and 10 were not run.** The plan runs them only if step 6 finds a rule, and it found none. Step 9 also needs step 8 to work: the file-level wait that ran did not make runs pair, and the frame-count or idle-flag snapshot the plan named was not tested.

## 2. Step 6: offline decision bench

### What was tested
- **States:** the 384 saved stages from 24 scored runs whose replayed top-10 list matches the log. These are the same stages as the objective audit. Each stage has the 300 candidate viewpoints that ASP's first stage scored.
- **Yardstick, U_wall:** the number of not-yet-mapped HM3D reference objects visible from a candidate over a full turn, 0.1-4.0 m. It counts an object only if the straight line to it crosses no wall. The walls come from slicing the HM3D mesh at 0.6, 1.1 and 1.6 m (tools/live_policy/review_2026-10-29/bench/walls/). It is meant to fix the audit's U_360, which let objects behind walls count; the check below shows how far it does.
- **Regret** of a pick is the best candidate's U_wall minus the pick's.
- **Rules:**
  - R1, ASP's own score;
  - R2, ASP with guesses on already-walked ground removed;
  - R3, ASP plus a bonus for distance from the walked path;
  - R4, expected discovery (guessed objects in view, weighted by how many ensemble members share them);
  - R5, distance from the walked path alone;
  - R6, random.
  All but R6 subtract ASP's move cost.
- **Guess sets:** the run's actual files; none; two independent random placebo draws (A and B); and an oracle draw of true unmapped objects, made as the live oracle arm made it.

### Yardstick check (done before any rule was compared)
At the robot's real stop, this asks whether the objects a yardstick counts are more likely to appear in the next map than the objects it leaves out (365 stages with a next map).

| Yardstick | Share of counted objects mapped next | Share of other objects mapped next | Difference [95% CI] | Ratio [95% CI] |
|---|---|---|---|---|
| U_wall | 0.104 (156 of 1,496) | 0.0122 | 0.092 [0.076, 0.108] | 8.6 [7.1, 10.2] |
| U_360 (audit) | 0.082 (633 of 7,720) | 0.0039 | 0.078 [0.069, 0.086] | 21.2 [17.2, 26.6] |

- **By the difference, U_wall passes:** it separates at least as well as U_360 (+0.014, CI −0.002 to +0.029).
- **By the ratio, it fails.**
- **U_wall misses most objects that do get mapped next.** It counts only 156 of the 820, against 633 for U_360.
- **Why it misses them:** low furniture in the slice map blocks rays. Ignoring cells inside each object's own outline (beds and tables at 0.6 m) lifts the count of next-mapped objects from 156 to 312 of 820. Using only the 1.1 m slice lifts it to 490. Neither variant was pre-registered.
- **What follows:** the pre-registration did not name the measure. On the ratio, U_wall fails the check, and the pre-registration then makes the bench results provisional. **Read the bench numbers below as provisional.** The stop decision is the same under either reading and under every variant of the wall test.

### Decision rule (pre-registered)
Go live only if some rule R1-R4 meets both conditions:
- **(a)** oracle regret at most 0.7 × placebo-A regret, with the ratio's CI wholly below 1;
- **(b)** on official stages, the CI of (LLM − placebo A) lies wholly below the noise floor (2.5th percentile of the bootstrap of placebo B − placebo A).

| Rule | Oracle regret | Placebo-A regret | (a) ratio [95% CI] | (a) | LLM − placebo A on official stages [95% CI] | Floor | (b) |
|---|---|---|---|---|---|---|---|
| R1 ASP | 9.11 | 9.77 | 0.933 [0.892, 0.972] | fail | −0.03 [−0.76, 0.70] | −0.73 | fail |
| R2 ASP, walked guesses removed | 8.71 | 9.64 | 0.904 [0.862, 0.949] | fail | −0.43 [−1.22, 0.39] | −1.07 | fail |
| R3 ASP + distance bonus | 8.41 | 9.86 | 0.853 [0.815, 0.894] | fail | −1.03 [−1.76, −0.36] | −0.82 | fail |
| R4 expected discovery | 8.09 | 9.52 | 0.850 [0.804, 0.893] | fail | +0.57 [−0.12, 1.27] | −0.29 | fail |

Regret is in objects. Oracle and placebo-A columns pool all 384 stages; the LLM contrast uses the 119 official stages.

**go_live = false.**
- **Condition (a):** every rule is better with exact objects than with random guesses (every ratio CI lies below 1), but none comes close to the 30% gain the plan asked for.
- **Condition (b):** R3 comes nearest. With DeepSeek's guesses it beats placebo A by about one object (−1.03, CI −1.76 to −0.36). But two random draws can differ by 0.82 by chance, and the CI's upper end does not get past that floor.
- **Robustness:** the outcome is the same under the cone-limited yardstick, normalised regret, every wall-test variant, a second bootstrap seed, and an exact cell-by-cell wall test in place of the builder's 5 mm sampling (every number moves by 0.05 or less).

### What else the bench shows (no decision attached)
- **Every rule leaves most of the view unseen.** The best candidate shows 12.7 unmapped objects on average. Across rules and guess sets, the pick shows 2.6-4.6 of them; a random pick shows 2.7.

  | Pooled regret (384 stages) | Actual files | None | Placebo A | Oracle |
  |---|---|---|---|---|
  | R1 ASP | 9.58 | 10.02 | 9.77 | 9.11 |
  | R3 ASP + distance bonus | 9.36 | 9.99 | 9.86 | 8.41 |
  | R4 expected discovery | 9.69 | 9.71 | 9.52 | 8.09 |
  | R5 distance only | 9.74 | 9.74 | 9.74 | 9.74 |
  | R6 random | 9.99 | 9.99 | 9.99 | 9.99 |

- **Under ASP's own score, DeepSeek's guesses show no detectable difference from random ones.** On official stages R1 regret is 9.12 with the LLM files and 9.15 with placebo A (difference −0.03, CI −0.76 to +0.70). That interval is wider than the gain exact objects give R1 on the same stages (8.76 against 9.15), so this test could not separate the LLM from exact objects either.
- **Exact objects help ASP's score only a little.** Oracle regret is 7% below placebo for R1, and 15% below for the best rule (R4, CI 11-20%). Under the unregistered wall-map variants the best gain is 21-25% (R4 ratio 0.785 with object outlines ignored, 0.747 with the 1.1 m slice), still short of 30%.
- **The guess-free distance rule (R5) shows no detectable difference from ASP's score with the guesses it actually had** (R1 − R5, actual files: −0.16, CI −0.53 to +0.20). Only with exact objects does every guess-based rule clearly beat it (R4 oracle −1.65, CI −2.11 to −1.22). With the actual files, R2 (−0.46, CI −0.86 to −0.04) and R3 (−0.38, CI −0.76 to −0.02) beat it narrowly.
- **The filter_only arm's guesses (DeepSeek after our validator) show the same pattern as official.** No rule clears its floor; for example, R3 gives −0.54 [−1.34, 0.24] against a floor of −1.23.

So the scores in the ASP family, fed with the guesses available, choose views only slightly better than random by a wall-aware count. Better guesses alone would not reach the bar: with exact objects the best rule cuts regret by 15% on the registered yardstick and by 21-25% under the unregistered variants, against the 30% asked.

### Caveats
- **The yardstick is weak** (see the check above). It counts 19% of the objects the robot does map next. A better yardstick needs a proper render: the HM3D mesh seen through the robot's camera.
- **The pinned pipeline moves the robot by setting its pose directly,** with no collision check (`_agent_forward` calls `agent.set_state`: exploration_pipeline.py.orig_2f17aa29:587-593, the file the E1-E3 runs used; lines 606-612 in the step 8 patched copy). The path comes from the planner's own map, not Habitat's navmesh. The verifier found walked points inside wall-map cells as often as random points (3.4-3.7% against 3.4-3.6%), while wall-type reference objects line up with the map at zero shift. So the robot probably passes through walls or furniture at times. This is in the author's code, not ours. It does not change the bench decision, but it qualifies item 36(a), which said the walked paths line up with the walls. The frontier explorer uses the same `set_state` motion (frontier_baseline.py:577-580), but its walked paths almost never enter wall-map cells: 0.00-0.17% of path points per run, against 2.4-7.0% per counted E1 run (results_2026-10-31/frontier_seeds/wall_cells.json). It snaps its goals to Habitat's navmesh (frontier_baseline.py:612). So the missing collision check bears on the ASP arms and not on frontier, and step 7 may be tilted, in a direction we do not know.
- **The builder chose readings where the pre-registration was silent,** and listed each one:
  - the walked path is the executed path to stage k;
  - R4 sums over every member's copy of a guess;
  - the "none" set uses each track's observed graph;
  - the bench's placebo draws use their own seeds, so they are fresh draws, not replays of the live files.
- **Run cost:** 2.75 CPU-hours on the laptop for the build, and at least 3.6 more for the verifier (3.64 for its per-stage recompute alone).

### Who did what
- One Opus 5.5 agent built the bench from the frozen text.
- A second, adversarial Opus 5.5 agent checked it. That agent wrote its own wall test and its own masking, novelty, support and pick code, and regenerated every guess set from the recorded seeds. All 9,600 picks matched the builder's.
- Verdict: "holds with corrections". The corrections were two rounding slips in the filter_only list and three caveats, all included above.
- Files: tools/live_policy/review_2026-10-29/bench/:
  - build/ (bench.py, summarize.py, summary.json, stages.jsonl);
  - verify/ (the independent recompute);
  - walls/ (the wall maps and slice_walls.py);
  - agent_reports.json (both agents' full reports).

## 3. Step 7: seeded frontier explorer

### What ran
- **Explorer:** the author's `frontier_baseline.py` with one opt-in change. `ASP_START_JITTER_SEED` moves the start by up to 0.25 m in x and z, snapped to the navmesh. The diff is in tools/live_policy/host/patches/frontier_baseline_jitter.diff.
- **Runs:** six, one at a time, scenes 00853 and 00871 × seeds 42-44. All six reached 60 m (scored final paths 60.4-68.9 m), so no rerun was needed. Each took 22-38 minutes; counted ASP runs that reached 60 m took 2.1-5.7 h (run_table.csv), much of it spent waiting for the LLM or in the placebo's matched pause.
- **Maps:** frontier_baseline.py does not write the evaluator's YAML maps, so every stage was converted with the author's own `f1_score_plot.convert_dsg_to_yaml`, as the earlier frontier reference was.
  - Checked on two ASP stages: this converter and the pipeline's own converter give identical object and room nodes, positions and edges. They differ only in key order and one unused field on room nodes.
- **Scoring:** live_score.py, HM3D reference, then e1_analysis.py as registered.

### Result (registered test)
Object F1 AUC to 60 m on the HM3D human annotation. Each contrast is arm minus frontier. The p-value comes from the scene-blocked exact permutation test, with Holm over the two contrasts.

| Contrast | Difference at 60 m [permutation 95% CI] | p | Holm | Difference at 50 m (p) | Signs agree |
|---|---|---|---|---|---|
| official − frontier (5 v 6 runs) | −0.012 [−0.053, +0.029] | 0.47 | 0.47 | −0.017 (0.35) | yes |
| placebo − frontier (6 v 6 runs) | −0.025 [−0.050, +0.002] | 0.07 | 0.14 | −0.024 (0.07) | yes |

Per run, AUC to 60 m:

| Scene | Official | Placebo | Frontier (seeds 42, 43, 44) |
|---|---|---|---|
| 00853 | 0.1412, 0.1531 | 0.1464, 0.1722, 0.1368 | 0.1785, 0.2156, 0.2028 |
| 00871 | 0.1314, 0.1267, 0.1165 | 0.1141, 0.0826, 0.0860 | 0.0925, 0.0957, 0.1027 |

The official arm has two counted runs on 00853: seed 44 stopped short of 50 m twice and was excluded by the registered rule.

**Reading, as registered: neither LLM nor random guesses beat nearest-frontier exploration on these homes.**
- Neither contrast is significant.
- Both point estimates favour frontier.
- Not ruled out: effects up to about 0.03 in the official arm's favour, and up to about 0.05 in frontier's. For placebo, the interval reaches only +0.002 in the arm's favour.
- Per scene (2-3 runs a cell, not tested): on 00853, official − frontier is −0.052 and placebo − frontier −0.047; on 00871 they are +0.028 and −0.003. Under the registered reading these splits give no credit to LLM content.
- The scene-blocked bootstrap that E1 also reports (runs resampled within scene and arm) gives narrower intervals that exclude 0 for both contrasts (official −0.022 to −0.001; placebo −0.039 to −0.010). It is not the registered test, and with 2-3 runs per cell it understates the spread.
- Minimum detectable effect at 60 m (α 0.05, power 0.8): 0.020 for official and 0.026 for placebo.
- The registered reading forbids any sentence crediting LLM content here: official − frontier is not significant.

### Check and caveats
- **Independent recompute:** an Opus 5.5 verifier wrote its own scorer and exact permutation test before seeing these numbers (tools/live_policy/review_2026-10-29/frontier_verify/REPORT.md).
  - All 31 run AUCs match within 0.00005, and so do the counted and dropped runs, both 60 m p-values and both Holm values.
  - The official 50 m p is 0.34 exactly; e1_analysis.py gives 0.345 because it tests on AUCs rounded to four decimals.
  - CIs here keep shifts with p ≥ 0.05 on a 0.0005 grid.
- **Walls.** Frontier's paths almost never enter wall-map cells, while ASP's do (see the step 6 caveat). The comparison may be tilted, in an unknown direction.
- **More scans per metre for frontier.** Both explorers turn a full circle at every stop, and the 60 m budget counts only forward motion. On 00871 the frontier stops far more often over the same distance: 41-46 stages against 12-28 for the ASP arms. That is how it explores under the registered budget, not a scoring error. A budget in time or in scans could rank the explorers differently.
- **Small effects, checked:**
  - ASP can leave its last map unscored. This happens once (official, 00853, seed 43) and would move the official contrast by 0.0002.
  - On 00853 the navmesh snap moved every seeded start off its drawn point. Seeds 43 and 44 ended about 0.31 m from the reference start in x, past the 0.25 m box (0.38 and 0.33 m in all), and only about 0.10 m from each other. The pre-registration allows the snap; on 00871 every start equals its draw.
  - The maps of both arms line up with the reference to 1-3 cm.

Files: tools/live_policy/results_2026-10-31/frontier_seeds/, made by tools/live_policy/frontier_seeds_analysis.sh. The off-host copy of the six runs (maps, path stats, logs, config) is at /Users/sher/cvp_live_campaign_copy/runs/frontier_seeds/. The full runs, with DSG files, stay on the host at runs/frontier_seeds/.

## 4. Step 8: deterministic stage snapshot

### What ran
- **The change:** `exploration_pipeline.py` gains an opt-in quiet wait. A map snapshot is taken only after the map file's bytes have stayed the same for 15 s, with a 120 s cap. The diff is in tools/live_policy/host/patches/exploration_pipeline_quiescent.diff. With the variable unset, the author's rule is unchanged.
- **Runs:** three $0 placebo replicates, q1-q3, all on scene 00853 with seed 42, a 15 m target, the same pacing and the same placebo seeds. live_policy seeds each draw with [seed, stage, graph id] and adds a salt only for `_rerun<n>` names and retried attempts. The guesses themselves still differ, because the placebo generator places them around each run's observed map: at stage 0, track 0's members hold 6/14/7/10 guesses in q1, 6/14/8/9 in q2 and 6/14/10/10 in q3. So the stage-0 stop, measure (b), carries map noise twice: directly, and through the guesses the map changes.
  - q1 reached 14.2 m by stage 6, then did not move for six stages and hit its 2 h limit.
  - q2 and q3 reached 15 m in about 56 minutes each.
  - The measures use stages 0-2 only, so q1's stall does not affect them.
- **The quiet wait was active but never waited past its first check.** All 50 snapshots (q1 26, q2 12, q3 12) logged "after 15 s extra wait": the file had not changed during the window.
- **Measures, as registered:** (a) stage-0 maps match: in both tracks the same object labels, each object within 0.10 m of a same-label partner. (b) stage-0 stops within 0.25 m. (c) The same at stages 1 and 2. Script: tools/live_policy/determinism_check.py; output: results_2026-10-31/determinism/determinism.json.

### Result
| Pair | Stage-0 maps match (a) | Stage-0 stops apart (b) | Stops apart at stages 1 and 2 |
|---|---|---|---|
| q1-q2 | no: track 0 has 5 against 4 objects; in track 1 one object is 0.17 m from its partner | 0.24 m (passes) | 2.49 m, 0.47 m |
| q1-q3 | no: q3's track 0 has no objects | 3.60 m | 6.03 m, 7.38 m |
| q2-q3 | no: q3's track 0 has no objects | 3.84 m | 4.49 m, 7.31 m |
| Baseline, the three earlier 00853/42 placebo attempts without the change | no pair matches | 1.99, 1.22, 0.77 m | 1.46, 3.45 m where both runs exist |

**Decision, as registered: plan at least 5 replicates per cell; seeds do not pair runs.**
- No replicate pair meets (a). Two of three fail (b). No pair meets either measure at stages 1 or 2.
- **The change did not bring the replicates closer than the baseline.**
  - Stage-0 stops lie 0.24-3.84 m apart (mean 2.56) against 0.77-1.99 m (mean 1.33) for the baseline.
  - The share of stage-0 objects with a same-label partner within 0.10 m is 0.00-1.00 by track, against 0.29-0.89.
  - With three pairs each, this is a description, not a test.

### What this says about the cause
The working cause was that the pipeline copies the map file before the mapper has taken in the whole scan. The step 8 files argue against it:
- **The file never changed during a quiet window** [V].
- **The copies happened at about the same moment in every run.** Track 0's stage-0 file was copied 97-99 s after launch in q1, q2 and q3, about 20 s after each scan ended [V].
- **The contents still differed.** In q3, track 0's stage-0 map holds no objects, and its file is 1.1 MB against 2.4-2.7 MB in q1 and q2 [V]. Track 1 has the same four objects in all three runs.
- **At stage 0 the copy rule has no earlier size to compare with,** so it takes the first file large enough once the scan ends (exploration_pipeline.py:333-360) [V].
- **The copy was not early.** In every run the copied track-0 file holds mapper poses up to 0.1-0.3 s before the scan ended, spread over the whole turn. The pipeline sends the mapper no frames while it waits to copy (`publish_sensor_images` runs only while scanning or moving). These facts come from the review agents' reads of the DSG files and code on the host [V, review].
- **The mapper made less of the same scan.** q3's track 0 kept 58 poses, against 120 in q1 and 104 in q2, and formed no objects. The duvet, nightstand and lamp that q1 and q2 map at stage 0 never appear in q3's track-0 maps at stages 1-5 [V].
- **The likely reading:** the split lies in what the mapper makes of a scan, not in when the file is copied, so a later snapshot would likely not help [I]. Why the mapper keeps fewer poses in some runs (message timing under load, for example) is not established [S].
- **The fix the plan named was not tested.** It waits on the mapper's own progress, by a frame count or an idle flag; this run tested only a file-level wait. Given the point above, it is unlikely to make runs pair, but that is untested.
- **No warning sets q3 apart.** Before its first snapshot each run has 2-3 "No object detected" warnings and nothing else. This check was not registered.

For any future study, mapper noise has to be handled by design. There are two ways:
- at least 5 live replicates per cell;
- a replay simulator that records each scan once and replays it to every arm (the design in plan step 9).


## 5. Steps 9 and 10: not run

The plan (§6, step 9) runs the detection-replay simulator only "if step 6 finds a rule and step 8 works", and step 10 only after that. The pre-registration says: "If no rule meets both, write up the bench and stop live work. Steps 9 and 10 are then not run, and the plan's own rule makes that its completion." Step 6 found no rule, so neither step ran. The roughly $25 left of the DeepSeek budget is unspent.

## 6. Where the plan ends, and what could come next

The plan is complete by its own rules:
- step 6 found no rule worth taking live;
- step 7 found that neither guess arm beats a plain frontier explorer;
- step 8 found that same-seed runs still split at the first stop with the quiet wait, so seeds do not pair runs;
- steps 9 and 10 do not run.

No further live run of this design should follow.

**What the evidence supports.** A placebo-controlled audit of LLM-guided active semantic perception, with three findings that agree:
1. **Live (E1, E2, registered):** DeepSeek's guesses did not detectably beat random guesses of the same shape, and our validator did not detectably help.
2. **Offline (step 6, provisional yardstick):** ASP's viewpoint score turns guesses into views only a little better than random by a wall-aware count. Exact objects improve the best rule by about 15% (21-25% under unregistered wall-map variants), short of the 30% bar.
3. **Against a baseline (step 7, registered):** neither the LLM arm nor the random-guess arm beat a nearest-frontier explorer on these two homes. The explorer also needed no LLM and ran in a fraction of the time. (ASP's paths cross wall cells and frontier's do not, so this comparison may be tilted, in an unknown direction.)

The mechanism review explains why:
- the score rewards disagreement among the guesses, not their truth, and it has no term for unknown space;
- the detector maps about 1 in 12 objects in view.

**If the work continues, the bench and the mechanism review point to the objective and the detector as the larger limits; even exact objects do not reach the bar, so better guesses alone are unlikely to be enough.** In order:
1. **A rendered yardstick.** Render the HM3D semantic mesh through the robot's camera at each candidate pose, offline in habitat-sim. This replaces the slice-map count, which misses 81% of the objects the robot maps next, and it is the first half of the replay simulator in plan step 9.
2. **An objective with terms for unknown space and for truth,** such as support-weighted guessed objects that lie in unexplored space. Test it on the bench against frontier exploration before any live run.
3. **Collision-checked motion** for every arm. Use Habitat's navmesh step instead of `set_state`.
4. **Then the study design in SYNTHESIS_AND_NEXT_PLAN.md §6, "What a publishable study would need":** 8-10 human-labelled scenes, at least 5 seeds per arm, at least 5 replicates per cell or a replay simulator (step 8), and blocked tests registered in advance.

Spend for steps 6-8: $0. Of the $40 DeepSeek cap, about $25 is left: the runners' stop lines total $14.60, and calls made during shutdown add a few cents per paid run. Gemini credit is untouched.

