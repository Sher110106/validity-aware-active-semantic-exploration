# Do LLM scene-graph guesses help a live robot map? A placebo-controlled pilot with an exact-object control arm

The campaign ran from 2026-10-28 to 10-29 (IST); this package was built at 22:02 IST on 10-29. Section 12 and the files listed in `POST_CAMPAIGN_MANIFEST.sha256` were added on 10-30. Every number below appears in `numbers.csv` with its file and key. For a number quoted from a document, `numbers.csv` gives the document and section instead. `DEVIATIONS.md` numbers each departure from the pre-registrations (items 1-35; items 36-39 cover section 12).

Labels:
- **[R, pilot]**: registered analysis. Every result carries pilot status because the E1 confirmatory conditions failed: one cell is missing and the code changed after the freeze (PREREGISTRATION_E1, "Claim status").
- **[X]**: exploratory.
- **[I]**: an inference from the cited evidence.

## 1. Answer

**Content (E1) [R, pilot].** DeepSeek V4.1 Flash's scene-graph guesses did not detectably beat random guesses of the same shape.
- d = +0.013 F1 AUC to 60 m (95% CI −0.012 to +0.040).
- The design had 80% power only for differences of about 0.024-0.028.
- One registered secondary points the other way. On F1 at the 60 m endpoint, DeepSeek's runs end ahead: +0.043, p 0.015, positive on both scenes. At 30 m the difference is −0.011 (p 0.58). This is one of six E1 secondary tests, and Holm across them gives 0.09. Read together: the LLM arm ended ahead at 60 m on these two homes, but its map quality over the whole path was not detectably better.

**The validator (E2) [R, pilot].** Our validator did not detectably change the official pipeline's result.
- d = +0.003 (95% CI −0.037 to +0.047; 80% power only for about 0.044-0.051).
- The registered latency rule removes two cells. Without them the test cannot reach alpha (smallest p 0.11), and d stays +0.005.

**Exact objects (E3).** The registered text ends E3 after a second broken gate verdict, and the gate broke twice on 00853. Reading the verdict per scene is deviation 26, fixed before any oracle AUC was read. It was fixed after the 00871 gate had passed and after an interim E1 pass had shown the placebo AUCs (§3, Scope). Under that reading, E3 rests on 00871 alone [R, pilot, under deviation 26; exploratory under the literal rule].
- All three oracle runs beat all three placebo runs: +0.034. That gives p = 0.10, the smallest value a 3 v 3 test can return, so by the registered test it is no detectable difference.
- Oracle minus official is +0.003 (p 0.70). A 3 v 3 test cannot reach p < 0.05, and the registered wider interval is unbounded, so effects of any size are not ruled out. We cannot tell exact objects from DeepSeek's guesses on that home.

**What the offline audit suggests [X].** ASP picks viewpoints by how much its guessed graphs disagree about what a camera would see. No term in the score asks whether a guess is true.
- **Decisions.** Swapping DeepSeek's guesses for a random set moves the top-scored candidate no more than swapping one random set for another. Exact objects moved it more on 00853 stages, but not on 00871 or on counted runs alone.
- **Ranking.** With exact objects the score ranks views by the number of true unseen objects they show (partly by construction; see §4). With DeepSeek's guesses it barely does.
- **A guess-free rule.** Simply preferring ground far from where the robot has walked ranks views better under the full-turn count. Under the camera-cone count it does no better than DeepSeek's guesses, and both counts ignore walls.
- **Yield.** Of the unseen objects counted in view of a stop, about 1 in 12 reach the next map. Part of that gap comes from the yardstick, which ignores unmapped walls, and part from the detector.

**The static gain [X].** On the new model, the September static "unanimity gain" again scores within 0.0001 of the map with all guesses deleted.

## 2. What ran

The author's ASP pipeline (pinned commit f1ea141b) on HM3D scenes 00853 and 00871, which have human annotation, seeds 42-44, with a 60 m path budget.

The arms:

| Arm | What steers viewpoint choice | Cost |
|---|---|---|
| official | DeepSeek V4.1 Flash 1017 (DeepInfra fp8) completions, used as the author's pipeline uses them | about $1 per run |
| placebo | random guesses of the LLM's measured shape (counts, labels, room links, distances). Each stage sleeps by a delay schedule: the registered prior (260/400/500 s) for 00853/42, and per-stage medians over finished official runs for the rest (registered update rule), not each partner's wait | $0 |
| filter_only | official plus our validator, which removed 30% of new guesses (22-37% per run) | about $1.1 per run |
| oracle_visible | true unmapped HM3D objects, drawn at random per member at the placebo's counts, with placebo rooms | $0 |

**Metric:** author-faithful object F1 of the robot's observed map against the HM3D human annotation, as area under the curve (AUC) to 60 m.
- The frontier-made reference is secondary for E1/E2 and descriptive for E3.

**Tests:**
- scene-blocked exact permutation, two-sided, alpha 0.05;
- Holm over E1 and E2; E3 is its own family;
- a claim needs the 60 m and 50 m results to agree in sign.

**Cells:**

| Cell | Planned | Counted | Missing, excluded or archived |
|---|---|---|---|
| E1 official | 6 | 5 | 00853/44 missing: the first attempt hit the 4.5 h wall-clock limit at 46.8 m, and the rerun stalled at 44.25 m (items 17, 27) |
| E1 placebo | 6 | 6 | 00871/43 first attempt stopped at 0 m (item 16); its rerun counts |
| E2 filter_only | 6 | 6 | none; 00871/43 counts at 54.9 m (item 28) |
| E3 oracle | 4-6 | 3 (00871 s42, s43, s44) | 00853/42: first attempt archived (gate broken, item 26); retry excluded (broken again, item 29). 00853/43: excluded (E3 ended on 00853). 00853/44: missing, not queued (item 31) |

**Archived attempts.** Thirteen attempt directories were archived and never scored:
- five false exits when the host ran out of memory in wave 1, voided by the restart (item 5);
- five runs stopped by hand to protect host memory (items 7, 8, 12), each using its cell's one rerun;
- two earlier attempts at the 00853/42 placebo (a retry loop, item 1, and a false exit);
- the 00853 oracle first attempt (item 26).

**Spend:**
- DeepSeek, from the runners' stop lines: $11.45 on counted paid runs and $13.06 on all scored runs. Archived paid attempts add $1.33 and tests and dry runs $0.20, for $14.60 in all, against a $40 cap. Calls made while a run shuts down add a few cents per run (item 34).
- Gemini: $0.

## 3. Registered results [R, pilot]

### E1: official minus placebo

| Ref, budget | d | 00853 (2 v 3) | 00871 (3 v 3) | p (200 relabelings) | Holm p | Bootstrap 95% CI | Permutation 95% CI | MDE | Sign-flip p (pairs) |
|---|---|---|---|---|---|---|---|---|---|
| HM3D, 60 m | +0.013 | −0.005 | +0.031 | 0.22 | 0.44 | −0.000 to +0.025 | −0.012 to +0.040 | 0.024 | 0.38 (5) |
| HM3D, 50 m | +0.007 | −0.012 | +0.026 | 0.53 | 1.00 | −0.005 to +0.019 | −0.018 to +0.035 | 0.023 | 0.56 (5) |
| frontier ref, 60 m | +0.008 | −0.073 | +0.089 | 0.84 | 1.00 | −0.027 to +0.039 | −0.074 to ≥ +0.108 | 0.064 | 0.69 (5) |

"≥" marks a bound that sits on the edge of the search grid, so the true bound is at least that far out.

**Precision.** DeepSeek's new guesses landed within 0.5 m of a same-label unseen object 6 times as often as the placebo's: 3.0% against 0.5% pooled; 1.39% against 0.62% on 00853 (2.2×), and 4.16% against 0.40% on 00871 (10×).

Registered reading: **no detectable difference.**
- d = +0.013 (95% CI −0.012 to +0.040).
- The design had 80% power only for differences of about 0.024 (normal approximation) to 0.028 (t, 7 degrees of freedom), which is 19-22% of the arms' mean AUC.
- Effects up to +0.040 are not ruled out.

On 00871 all three official runs beat all three placebo runs; on 00853 the official runs sit inside the placebo range. With two homes the blocked test cannot tell a home-specific effect from noise.

**Registered covariates and secondaries:**
- **Pacing flag.** A pair is flagged if the placebo's delay differs from its official partner's LLM wait by more than 20% at three or more stages. All five counted pairs are flagged (10 of 16, 10 of 17, 13 of 15, 8 of 12 and 16 of 19 stages). Placebo delays follow the registered prior for 00853/42 and medians over finished official runs for the rest, not each partner's wait. The arms therefore differ in timing as well as content.
- **F1 at 30 m and 60 m** (registered secondary; point values from each run's curve, hold-last for runs that stopped early):
  - At 60 m: official − placebo +0.043, p 0.015, sign-flip p 0.06; positive on both scenes (+0.034, +0.052).
  - At 30 m: −0.011, p 0.58 (00853 −0.052, 00871 +0.031).
  - Holm across the six E1 secondary tests (canonical F1, the two recall forms and nGED as AUC, plus F1 at 30 m and 60 m) gives 0.09 for the 60 m test.
  - The official arm ends ahead at 60 m; the placebo leads earlier on 00853, and the primary AUC weighs the whole path.
- **Seed-paired sign-flip test:** p 0.38 at 60 m and 0.56 at 50 m, over 5 pairs. Seeds do not pair runs (§4), so this test is weak.
- **Canonical metrics** (60 m, HM3D): F1 AUC +0.013 (p 0.22), recall AUC +0.008 (p 0.23), nGED AUC −0.001 (p 0.81).
- **Not done:** the extended label tier (item 34).

### E2: official minus filter_only

| Ref, budget | d | 00853 (2 v 3) | 00871 (3 v 3) | p | Holm p | Bootstrap 95% CI | Permutation 95% CI | MDE | Sign-flip p (pairs) |
|---|---|---|---|---|---|---|---|---|---|
| HM3D, 60 m | +0.003 | −0.016 | +0.022 | 0.86 | 0.86 | −0.019 to +0.025 | −0.037 to +0.047 | 0.044 | 0.31 (5) |
| HM3D, 50 m | −0.001 | −0.019 | +0.017 | 0.96 | 1.00 | −0.022 to +0.020 | −0.039 to +0.039 | 0.041 | 0.50 (5) |
| HM3D, 60 m, latency rule (cells 00853/42 and 00871/44 removed) | +0.005 | −0.011 | +0.021 | 1.00 (18) | — | −0.027 to +0.038 | unbounded at this n | n/a (smallest p 0.11) | 0.50 (3) |
| HM3D, 50 m, same cells removed | +0.003 | −0.012 | +0.017 | 1.00 (18) | — | −0.028 to +0.033 | unbounded at this n | n/a (smallest p 0.11) | 0.50 (3) |

Registered reading: **no detectable difference.**
- d = +0.003 (95% CI −0.037 to +0.047).
- The design had 80% power only for differences of about 0.044 to 0.051 (normal approximation to t), which is 33-38% of the arms' mean AUC.
- Effects from −0.037 to +0.047 are not ruled out.
- The 60 m and 50 m signs disagree.

**What the validator did.** It removed 2,573 of 8,465 new guessed objects (30%), and 56 of them were hits. Pooled 0.5 m precision rose from 2.8% to 3.1% (2.3% to 2.5% on 00853, 3.3% to 3.7% on 00871).

**Latency rule** (item 21d). It fires for 00853/42 (filter arm's mean LLM wait 53% above the official arm's) and 00871/44 (22% below). Without those cells the test cannot reach alpha (18 relabelings, smallest p 0.11), and d stays +0.005.

**F1 at the 60 m endpoint:** +0.026 (p 0.28). At 30 m: −0.012 (p 0.59).

**Canonical metrics:** F1 AUC +0.003 (p 0.85), recall AUC +0.001 (p 0.93), nGED AUC −0.000 (p 0.97).

### E3: oracle_visible minus placebo, 00871 only [R, pilot, under deviation 26]

**Scope.** PREREGISTRATION_E3 says "a second broken verdict ends E3 and the gate results are the result."
- Item 26, written before any E3 AUC was read, read the verdicts per scene and replaced the "one fix" with a retry of unchanged code, because no fault was found.
- Under the literal rule, the gate table below is the registered E3 result, and the 00871 contrast is exploratory.
- Under item 26, the contrast is registered for 00871.
- Item 26 was written at 04:58 on 10-29. By then the 00871 gate had passed (item 25, 03:38), and an interim E1 pass (23:55 on 10-28) had shown the placebo AUCs: low on 00871 (0.114, 0.086) and higher on 00853 (0.137-0.172). Only the oracle AUCs were unseen. Keeping the scene whose gate passed was therefore a choice made with some knowledge of the comparators, and a reader should weigh the 00871 contrast with that in mind (item 35).
- The E3 AUC files were written by the 15:40 analysis pass and stayed unopened until after the 18:01 seed-44 decision (items 31, 34).

**Gate:** drawn vs undrawn eligible true objects in the same stage and track; one-sided permutation, from registered single-run calls (`gates/`, `figures/e3_gate.png`). The base-rate column gives each run's own rate. The registered pre-E3 scene rates were 9.5-12.3% (00853) and 5.2-6.8% (00871).

| Oracle run | Role | Usable stages | Drawn / undrawn rows | Approach gap | p | Mapping gap (k+1) | p | Run's base mapping rate |
|---|---|---|---|---|---|---|---|---|
| 00853 s42, first attempt | verdict run: broken; archived | 14 | 945 / 1,386 | +0.035 | 0.065 | +0.004 | 0.29 | 12.9% |
| 00853 s42, retry | verdict run: broken again | 16 | 1,071 / 1,596 | +0.027 | 0.37 | −0.007 | 0.73 | 13.2% |
| 00853 s43 | later run, reported | 16 | 1,040 / 1,465 | +0.031 | 0.22 | −0.011 | 0.85 | 13.6% |
| 00871 s42 | verdict run: detector-limited | 12 | 890 / 2,515 | +0.036 | 0.039 | +0.003 | 0.54 | 5.4% |
| 00871 s43 | later run, reported | 11 | 740 / 1,799 | +0.050 | 0.067 | −0.000 | 0.49 | 8.4% |
| 00871 s44 | later run, reported | 16 | 1,091 / 2,944 | +0.005 | 0.44 | +0.010 | 0.23 | 8.2% |

The 00871 verdict rests on s42 alone. Taken one by one, s43 (p 0.067) and s44 (p 0.44, gap +0.005) would each read broken.

**Contrast.** Three oracle runs against three placebo runs: 20 relabelings, smallest two-sided p 0.10. So the permutation-inverted interval cannot exclude any shift.

| Contrast, ref, budget | d | p | Bootstrap 95% CI | Permutation 95% CI | Runs: AUC (F1 at 60 m) |
|---|---|---|---|---|---|
| oracle − placebo, HM3D, 60 m | +0.034 | 0.10 | +0.015 to +0.046 | unbounded at this n | oracle 0.130 (0.171), 0.128 (0.209), 0.127 (0.191); placebo 0.114 (0.174), 0.083 (0.133), 0.086 (0.107) |
| oracle − placebo, HM3D, 50 m | +0.031 | 0.10 | +0.015 to +0.043 | unbounded | same sign as 60 m |
| oracle − official, HM3D, 60 m | +0.003 | 0.70 | −0.003 to +0.011 | unbounded | official 0.131, 0.127, 0.117 |
| oracle − official, HM3D, 50 m | +0.004 | 0.40 | −0.004 to +0.013 | unbounded | |
| oracle − placebo, frontier ref, 60 m (descriptive) | +0.138 | 0.10 | +0.071 to +0.196 | unbounded | |

No MDE is given. At 3 v 3 the exact test cannot reach p < 0.05, so it has no power at alpha 0.05 for any effect size; the normal approximation in the analysis files (0.028) does not apply.

**Reading.** The registered reading for a detector-limited scene allows one claim: exact objects delivered this way did not raise map gain detectably through this detector (p = 0.10). Beside it:
- p = 0.10 is as low as this design can go: every oracle run scored above every placebo run. With three runs per arm the bootstrap interval is too narrow to lean on, and the registered wider interval is unbounded. The test cannot decide this either way.
- Oracle minus official: **no detectable difference**, d = +0.003 (p 0.70). The registered wider interval is unbounded, so effects of any size are not ruled out; the bootstrap interval (−0.003 to +0.011) is too narrow at 3 v 3 to lean on. All three official runs also beat all three placebo runs on 00871 (E1, +0.031 on that scene); the three filter_only runs did not.
- Whether the 00871 placebo runs were poor, or the guided arms helped, three runs cannot tell [I].
- The registered rule forbids saying that the loop uses exact guesses but not the LLM's, and the data give no support for it.
- Holm over E1, E2 and E3 (registered sensitivity line): adjusted p 0.44, 0.86 and 0.30.

**Canonical metrics and F1 points** (oracle − placebo, 60 m): F1 AUC +0.033 (p 0.10), recall AUC +0.024 (p 0.10), nGED AUC +0.011 (p 0.30); F1 at 60 m +0.053 (p 0.20), at 30 m +0.047 (p 0.10). Oracle − official F1 at 60 m: +0.000 (p 1.0).

**Post hoc ceilings, not registered** (`review_2026-10-29/audit/tables/e3_ceiling_exact.json`; 00871 s44 is not in this audit). Drawn and undrawn true objects sit side by side, so the drawn-vs-undrawn contrast has a low ceiling. Compared with a rule that simply goes where drawn objects cluster, the live approach gap reaches:
- **pooled:** 19-37% across the five audited runs (the archived 00853 first attempt included);
- **unit mean, by run:**
  - 00871 s42 (verdict run): 0.29 (CI −0.07 to 0.59);
  - 00871 s43: 0.27 (0.04 to 0.49);
  - 00853 first attempt: 0.20 (0.06 to 0.33);
  - 00853 retry: 0.04 (−0.18 to 0.23);
  - 00853 s43: 0.10 (−0.13 to 0.34).

This measure does not separate the "broken" runs from the "detector-limited" ones: the 00853 first attempt shows some pull, while the 00871 verdict run's interval crosses zero.

## 4. What the offline audit suggests [X]

**Sources.** Two independent reviews (Opus 5.5, max effort), each with its own replay of the author's scorer, and an audit built by one agent and recomputed by an independent verifier (`review_2026-10-29/` in docs and tools).

**Coverage.** None of these analyses includes the last oracle run (00871 s44). Each includes some excluded runs:
- the ρ and stop-percentile audit: 24 runs, including both 00853/44 official attempts, the 0 m placebo and the two excluded 00853 oracle runs;
- the top-candidate replay: 23 runs, the same set without the 0 m placebo;
- the E3 ceiling audit: five oracle runs, including the archived 00853 first attempt.

Counted-run figures are given where they differ.

**The score** (`calculate_uncertainty.py:501-549`): S = I_obj + I_room − 0.2·distance.
- Each I term is the entropy of what all guessed graphs together say a camera would see, minus the mean entropy within each graph. That is the mutual information between the next view and which member is right.
- No term measures unknown space or whether a guess is true.
- After a reachability check, the top 10 candidates are re-scored without the distance term. The published target is the first-stage best in 18% of stages, and 16% of picks are random tie-breaks.
- The room-level graph plan is computed but never used for motion (`mid_planning.py:122`).

**The top-scored candidate** (first stage, same 300 candidates; A's vectorised scorer, which reproduces 97% of logged top-10 lists).
- **Official arm (121 stages).** Replacing the LLM's guesses with a random set moves the top-scored candidate 2.28 m (median). Two random sets differ by 2.19 m, so the difference is +0.09 m (95% CI −0.25 to +0.38).
- **Counted runs only:** −0.04 m (CI −0.32 to +0.31).
- **No guesses:** removing all guesses moves it +0.10 m beyond the floor (CI −0.39 to +0.51), no more than a redraw.
- **Exact objects:**
  - all 121 stages: an oracle draw moves it +0.68 m beyond the floor (CI +0.01 to +1.06);
  - counted runs only: +0.54 m (CI −0.23 to +1.20);
  - 00853 stages: +0.92 m (CI +0.34 to +1.47);
  - 00871 stages: −0.00 m (CI −0.63 to +0.69).

So DeepSeek's content moves this candidate no more than a random redraw does. Exact objects moved it more on 00853 stages, but not on 00871 or on counted runs alone. Oracle sets also differ from placebo sets in member agreement (below), so these runs cannot say whether truth or agreement drives the shift. These are first-stage candidates, not stops: the robot stops a median 1.97 m from the first-stage best. The 300 candidates are drawn near the actual guess file's objects, so each swap is scored on a set picked using the actual content.

**Does the score rank views by true unseen objects?** Two counts serve as the yardstick:
- U_360: the number of not-yet-mapped true objects visible over a full turn at a candidate;
- U_cone: the same count within the planner's own camera cone.

The table gives the median per-stage Spearman ρ between U_360 (U_cone in brackets) and the score built from each guess set. The robot state and the 300 candidates stay the same; only the guess files change.

| Stages of arm | Actual guesses | No guesses | Placebo set | Oracle set | Guess-free "far from walked path" |
|---|---|---|---|---|---|
| official (119) | 0.20 (0.30) | −0.07 (−0.03) | 0.19 (0.23) | 0.44 (0.71) | 0.50 (0.31) |
| placebo (110) | 0.10 (0.18) | −0.01 (0.02) | 0.16 (0.24) | 0.47 (0.70) | 0.21 (0.14) |
| filter_only (97) | 0.12 (0.25) | −0.10 (−0.03) | 0.12 (0.18) | 0.39 (0.65) | 0.39 (0.24) |
| oracle (58) | 0.45 (0.65) | −0.08 (−0.14) | 0.01 (0.06) | 0.48 (0.65) | 0.40 (0.34) |

Notes on the table:
- **The "far from walked path" column** covers 361 stages (stage 0 has no walked path).
- **Exact objects** raise ρ by about +0.31 over a placebo set on official stages. The oracle sets are drawn from the very objects U_360 counts, so that column is partly high by construction: it marks the exact-object level, not an independent test.
- **DeepSeek's guesses** add +0.07 on official stages (paired median; 73 of 119 stages, p 0.008 at stage level). Run medians are +0.07 to +0.25 on 00853 and about 0 on 00871.
- **With a 1.0 m unmapped radius,** ρ is 0.17, 0.06, 0.04 and 0.42.
- **The guess-free rule** beats ASP's score only under U_360. Under U_cone it does no better than DeepSeek's guesses (0.31 against 0.30 on official stages), and worse than placebo or exact sets on their own stages.
- **The reference has no walls,** so both counts include objects behind unmapped walls. That may favour any outward-pulling rule.

**Where the stops land.** The robot's real stop, as a percentile of U_360 among the 300 candidates, with a within-run stage bootstrap 95% CI:

| Arm | All candidates | Candidates within 0.5 m of any walked path ("floor") | Run-cluster CI |
|---|---|---|---|
| official | 0.63 (0.58-0.67) | 0.59 (0.54-0.63) | 0.54-0.71 |
| placebo | 0.61 (0.57-0.65) | 0.53 (0.48-0.58) | 0.49-0.73 |
| filter_only | 0.64 (0.58-0.69) | 0.61 (0.56-0.67) | 0.53-0.73 |
| oracle | 0.78 (0.74-0.82) | 0.74 (0.69-0.79) | 0.72-0.86 |

"Floor" is a stand-in for walkable ground, not a navmesh. The placebo stops are not shown to beat a random floor candidate.

**Yield and the detector:**
- Of the unseen true objects counted in view of a stop, 6.9-9.0% (by arm) appear in the next map, against 0.3-0.8% of those out of view. Pooled, that is 8.2%, about 1 in 12. Part of the gap is the yardstick (no walls) and part is the detector.
- Per-stage mapping rates of nearby true objects are 4.3-13.6% across runs.
- A frontier explorer run until it ran out of frontiers reached recall of 0.261 (00853) and 0.168 (00871), one run per scene.
- Arm means reach 0.15-0.18 (00853) and 0.08-0.12 (00871) recall at 60 m; single runs reach 0.14-0.23 and 0.05-0.14.

**Precision and agreement:**
- **Precision** (counted runs, (stage, member) instances): new guesses within 0.5 / 1 / 2 m of a same-label unmapped true object are 3.0% / 10.1% / 23.8% for official and 0.5% / 2.0% / 6.3% for placebo. Per scene, see §3.
- **Later found:** 0.48% (00853) and 0.89% (00871) of DeepSeek's unique guesses were found later in the final map, against 0.11% and 0.20% for the placebo and 17.4% for the oracle (`mechanism.md`).
- **Agreement:** members agree with each other on a same-label object within 1 m for 29.4% of LLM guesses, 4.4% of placebo guesses and 42.2% of oracle guesses. Agreement lowers the score, so the arms differ in disagreement structure as well as in content.

**Noise and paths** (`review_2026-10-29/A/paths_pairs.json`, runs to 17:40):
- Same-seed runs of one arm, archived attempts included, split at the first stop in 14 of 15 pairs (median gap 1.7 m), because the first map differs. Seeds do not pair runs.
- Among counted runs, swept-area overlap at 60 m (Jaccard, 2 m radius) is about 0.52 between arms and 0.62 between seeds of one arm. The arms do go to somewhat different places; no arm turns that into a detectable map gain.
- F1 at 60 m varies between seeds of one arm by 1-2 points for official, 4-7 for placebo, 8-12 for filter_only and 4 for oracle (`extra_tables.json`).

## 5. The static table on the new model [X]

Object F1 AUC to 60 m against the HM3D annotation (canonical evaluator), for three maps: the observed map plus the guesses, plus unanimity-filtered guesses, and the observed map alone. For filter_only runs, "guesses" means those the validator kept. File: `static_three_way.json`.

| Run | Guesses | Unanimity | Observed only | Guessed nodes kept by unanimity |
|---|---|---|---|---|
| official 00853 s42 | 0.1345 | 0.1406 | 0.1406 | 8 of 1,474 |
| official 00853 s43 | 0.1446 | 0.1523 | 0.1524 | 12 of 2,038 |
| official 00871 s42 | 0.1265 | 0.1295 | 0.1296 | 8 of 1,571 |
| official 00871 s43 | 0.1206 | 0.1246 | 0.1246 | 5 of 1,762 |
| official 00871 s44 | 0.1122 | 0.1149 | 0.1148 | 10 of 1,826 |
| filter 00853 s42 | 0.1547 | 0.1589 | 0.1589 | 2 of 1,006 |
| filter 00853 s43 | 0.1224 | 0.1255 | 0.1255 | 1 of 1,155 |
| filter 00853 s44 | 0.1925 | 0.1990 | 0.1990 | 1 of 1,311 |
| filter 00871 s42 | 0.1324 | 0.1345 | 0.1345 | 0 of 1,372 |
| filter 00871 s43 | 0.0771 | 0.0787 | 0.0787 | 4 of 814 |
| filter 00871 s44 | 0.0894 | 0.0909 | 0.0909 | 3 of 943 |

- In all 11 runs, adding the guesses lowers the map's F1 AUC, by 0.0015-0.0078.
- Unanimity keeps under 1% of them and scores within 0.0001 of the observed map alone.

The September finding replicates on the 1017 model, at 60 m, against human labels.

## 6. What the author missed, and the open gap

Detail is in `SYNTHESIS_AND_NEXT_PLAN.md`.
- The ASP paper (arXiv 2510.05430, v1 and v2) compares only with frontier exploration and SSMI.
- It reports one run per scene: no seeds, intervals or tests.
- It scores against a map built by its own detector.
- It has no control that separates what the guesses say from the fact that there are guesses.
- The method changed between v1 and v2.

Its margins over frontier are 2.5-7.9 F1 points. Our seed spreads at 60 m are 1-2 points for the official arm and 4-12 for placebo and filter_only. This is a scale check only, because the references differ: the paper's single runs cannot separate its margins from seed noise of the size we see in two of our arms.

We found no published study of LLM-guided exploration that separates content from presence, or that checks whether the viewpoint score ranks views by true unseen objects. That rests on about 20 searches per reviewer. The closest work is MAPLE (arXiv 2610.28566, Oct 2026), which finds the 2D-occupancy version of this null.

## 7. Evidence and inference

**Evidence:**
- **V1.** E1 HM3D 60 m: d +0.013, p 0.22, permutation CI −0.012 to +0.040, MDE 0.024-0.028; 50 m +0.007, p 0.53. Sign-flip p 0.38. F1 at the 60 m endpoint +0.043 (p 0.015; Holm over six secondaries 0.09); at 30 m −0.011. `analysis/E1_hm3d_*.json`, `analysis/secondary/E1_hm3d_f1point*.json`.
- **V2.** E2 HM3D 60 m: d +0.003, p 0.86, permutation CI −0.037 to +0.047, MDE 0.044; 50 m −0.001. Under the latency rule: +0.005, p 1.0. `analysis/E2_hm3d_*.json`.
- **V3.** E3, 00871: oracle − placebo +0.034, p 0.10 (the 3 v 3 floor); 50 m +0.031, p 0.10. Oracle − official +0.003, p 0.70, with the wider interval unbounded. `analysis/E3_*.json`.
- **V4.** Gate gaps and p per oracle run; only 00871 s42 passes the approach test. `gates/E3_gate_*.json`.
- **V5.** Precision at 0.5 m: official 3.0%, placebo 0.5% (00853 1.39% vs 0.62%; 00871 4.16% vs 0.40%). `numbers.csv` precision rows, from `analysis/stage_precision.json`, counted runs.
- **V6.** Static: adding guesses lowers F1 AUC in 11 of 11 runs; unanimity is within 0.0001 of observed-only. `static_three_way.json`.
- **V7.** The score has no truth or unknown-space term. `calculate_uncertainty.py:501-549`.
- **V8.**
  - The published target is the first-stage best in 18% of stages; 16% of picks are ties.
  - The room plan is unused.
  - The robot stops a median 1.97 m from the first-stage best.

  `audit/tables/rank_reconcile.json`; `mid_planning.py:122`; `audit/audit/summary.json`.
- **V9.** Top-scored candidate, beyond the redraw floor:
  - LLM vs placebo +0.09 m (CI −0.25 to +0.38), or −0.04 m on counted runs;
  - no guesses +0.10 m (CI −0.39 to +0.51);
  - oracle draw +0.68 m (CI +0.01 to +1.06), but +0.54 m (CI −0.23 to +1.20) on counted runs and −0.00 m on 00871.

  `audit/tables/replay_table.json`.
- **V10.** ρ(score, U_360): 0.20 / 0.10 / 0.12 / 0.45. Matched states on official stages: oracle +0.31 and LLM +0.07 over placebo. Guess-free rule 0.50 under U_360 but 0.31 under U_cone (DeepSeek 0.30). `audit/audit/summary.json`, `cf_summary.json`.
- **V11.** About 1 in 12 counted in-view unseen objects reach the next map. Per-stage mapping rates 4.3-13.6%. Frontier recall at exhaustion 0.261 / 0.168. `audit/audit/summary.json`; `analysis/extra_tables.json`; `audit/tables/headroom_table.json`.
- **V12.** Same-seed runs split at stop 0 in 14 of 15 pairs. Overlap is 0.52 between arms and 0.62 between seeds (counted). `analysis/extra_tables.json` (paths).
- **V13.** Arm differences beyond content:
  - every E1 pair is pacing-flagged;
  - the candidate anchor is the first LLM call to finish in LLM arms, member 0 in no-LLM arms;
  - 7-24% of LLM members are dropped per official run, against none in placebo;
  - same-label agreement within 1 m is 29.4% (LLM) against 4.4% (placebo).

  `analysis/extra_tables.json`, `REVIEW_B_paper_field.md`, `run_table.csv`, `analysis/agreement.json`.
- **V14.** E3 ceiling shares: pooled 19-37%; 00853 first attempt 0.20 (0.06 to 0.33) and retry 0.04 (−0.18 to 0.23), unit mean. `audit/tables/e3_ceiling_exact.json`.
- **V15.** ASP paper facts as stated in §6. `REVIEW_B_paper_field.md` §3-4.
- **V16.** F1 at 60 m spreads between seeds of one arm: official 1-2 points, placebo 4-7, filter_only 8-12, oracle 4. `analysis/extra_tables.json` (f1_by_arm_scene).

**Inference:**
- **I1.** On these two homes, with this planner and detector, DeepSeek's content did not detectably change map quality over the path to 60 m. Effects up to about 0.04 AUC are not ruled out, and the LLM arm did end ahead on F1 at 60 m, which is a secondary result (V1, V2).
- **I2.** The validator did not detectably help (V2), and unanimity reduces to the observed map (V6). A plausible reason [X]:
  - guesses reach F1 only through where the robot goes (the metric scores the observed map, §2);
  - the score has no truth term (V7);
  - DeepSeek's content moves the top-scored candidate no more than a random redraw (V9).
- **I3.** Offline, exact-object sets shift the score's ranking toward true unseen objects (partly by construction), and on 00853 they shift the top candidate (V9, V10). They also differ from placebo sets in member agreement (V13), so these runs cannot say whether truth or agreement does it. DeepSeek's guesses, 3% precise at 0.5 m, barely shift either (V5, V10). This is a statement about the score, not about map gain; at map level, exact objects were not detectably better than DeepSeek's guesses (V3).
- **I4.** The detector and our yardstick together leave little for any stop rule to show (V11). How much is the detector's share is not known, because the yardstick ignores walls.
- **I5.** At the decision level, re-ranking, ties and mapper timing are about as large as content effects (V8, V9, V12).
- **I6.** The gate labels say more about a low-ceiling contrast than about the loop (V4, V14).
- **I7.** ASP's published gains over frontier cannot be credited to semantics without a content control. Single runs cannot separate margins of 2.5-7.9 points from the seed noise we see in placebo and filter_only (V16, V15, V1).
- **I8.** The 00871 pattern (official and oracle above placebo in 3 of 3 seeds) could be a home-specific content effect, a non-content arm difference (V13), or noise. filter_only, also LLM-guided, did not beat placebo on 00871 (V1, V3, V13).

## 8. Limits

**Design and measurement:**
- **Pilot status:**
  - The code frozen with E1/E2 on 10-28 no longer matches live_policy.py, live_runner.py, run_live_run.sh, live_score.py, e1_analysis.py or the OpenRouter shim; each change is a numbered deviation.
  - The code frozen with E3 still matches, except the scheduler's concurrency limit (item 23).
  - One E1 cell is missing.
- **E3:**
  - E3 was registered after four of its six placebo comparator AUCs were known.
  - The per-scene reading (deviation 26) was chosen after the 00871 gate passed and after the placebo AUCs of both scenes had been seen.
  - It reuses E1's placebo runs, so E1 and E3 share errors.
  - It rests on one scene under deviation 26, with a smallest attainable p of 0.10.
- **Pacing:** all five E1 pairs are pacing-flagged, so placebo and official runs differ in timing.
- **Timing:** E2, E3 and the E1 reruns (counted: the 00871/43 placebo) did not run beside their comparators, and wave-2 containers were not rotated (item 21e).
- **Member disagreement:** placebo members disagree more than LLM members, so content and disagreement structure are confounded (V13).
- **Counting:** precision counts (stage, member) instances; runs are the independent unit.
- **MDE:** it is a normal approximation; the t-based value is about 16% larger at 7 degrees of freedom. At 3 v 3 and in the latency-rule test the exact test cannot reach alpha, so no MDE applies.
- **Permutation intervals:** they are searched on a ±0.1 grid; bounds on the grid edge are marked "≥". At 3 v 3 they are unbounded.
- **The frontier-made reference** is the frontier run's own final map. It raises that run's AUC 2.9× (00853) and 4.5× (00871), and the live runs' 1.9-4.2×. It is secondary or descriptive only, and no ASP-vs-frontier comparison was tested.
- **Scope:** two scenes, one mapper (Hydra/Clio), one detector, one live LLM.
- **Wall-clock censoring:** e1_00853_s43_official stopped at 54.3 m on the time limit and e2_00871_s43_filter_only at 54.9 m on the call-loop rule. Both are held at their last value to 60 m.
- **Gemini:** the static Gemini comparison rests on 8 matched inputs and was never run live.
- **Hypotheses of any kind:** with no live observed-only arm, the design cannot say whether hypotheses of any kind change map gain. Offline, removing all guesses moves the top-scored candidate no more than a random redraw (V9), but it flattens the score; that is a decision-level fact, not a map-gain test.
- **Multiplicity:** the secondary tests are not corrected, apart from the Holm line given for F1 at 60 m.
- **Not done:** the extended label tier and D4 (item 34).

**The offline audit:**
- It includes excluded runs and leaves out 00871 s44.
- Its yardstick ignores unmapped walls.
- Its oracle rows are partly high by construction.
- It scores first-stage candidates, not stops.

**Bookkeeping:**
- `analysis/E3_*.json` list 00853 placebo and official runs under counted_runs, but they enter no E3 statistic, because 00853 has no counted oracle run.
- Spend totals use the runners' stop lines and miss shutdown calls of a few cents per run.

## 9. Errata

1. "DeepSeek's 0.5 m precision is at chance" (OVERNIGHT_REPORT_2026-10-28, result 4) is wrong for the live stages: 3.0% against the placebo's 0.5% (V5). On the 8 matched static inputs the figures are 2.1% and 1.4% (docs/checkin/FABLE_REVIEW_2026-10-28.md).
2. The September static headline said unanimity "removes about 27 percent of predicted nodes". It keeps 19 of 8,943 (99.8% removed), and it scores within 0.0002 of the observed map alone: 0.5218/0.4349/0.4957 against 0.5219/0.4351/0.4957 (CONTEXT_given_to_reviewers.md §1). The gain shows that the guesses hurt the map, not that the filter adds value. This replicates on the 1017 model (V6).
3. Calibration and the risk term are retired: the offline Brier score equals the base rate, and the combined risk term at beta ≤ 1 moved 2, 0 and 3 stages on the three matrix scenes (FINAL_PLAN_2026-10-29.md package list). The paper's "bit-identical at beta ≤ 1" is false.
4. The agreement vote (unanimity, an ensemble-support threshold) and the validator (structural and geometric checks; the filter_only arm) are different filters. The 61→45 and 313→138 counts come from the validator, not from unanimity (docs/archive/PHASE13_DIAGNOSTICS_2026-09-17.md).
5. Campaign notes corrected in DEVIATIONS item 34:
   - the item 26 p is 0.0655;
   - the item 28 cost is the scheduler's figure, which includes shutdown calls;
   - the item 31 run times were five runs of 2.07-2.75 h.

   Also:
   - The reviewers' 18% vs 31% comes from which list and which target pose each counted (V8).
   - The run table briefly showed e1_00871_s42_official's stopped first attempt (0.92 h, $0.16) in place of the counted run (2.68 h, $0.81).

## 10. Provenance and reproduction

**Off-host copy:** `/Users/sher/cvp_live_campaign_copy`, laid out like the host's `/workspace`.
- It holds every file the analysis reads, plus `tools/live_policy/oracle_sets.json`.
- Its manifest is `COPY_MANIFEST.sha256` (9,657 files); check it with `cd /Users/sher/cvp_live_campaign_copy && shasum -a 256 -c MANIFEST.sha256`.
- The mapper dumps (`graph*_dsg.json`) and image slices stay on the host under `runs/live_campaign/`, covered by `HOST_MANIFEST.sha256` (13,453 files; item 32).

**`reproduce.sh`:** re-scores every run from the copy and reruns E1-E3 (both references, both budgets), the E2 latency rule and the canonical secondary metrics. Against the final outputs, 31 of 31 files reproduce, 27 exactly. The other four differ only in the last binary digit of mde_alpha05_power80, because the laptop's newer Python sums statistics.mean differently; the script compares floats at 1e-12 relative.

The script does not cover:
- the F1-point secondaries, `extra_tables.json` and `agreement.json`, which come from `scripts/` in this package;
- `numbers.csv`, written by `build_results.py` and `tools/live_policy/extra_numbers.py`.

**Hashes:**
- The three pre-registrations (19382f74, 2ef52402, 360d5d03), `oracle_sets.json` (a7b35313), the HM3D reference graphs, the label mapping and the frame transform all verify against their sha256 files. Code-file mismatches are listed under Limits.
- Pinned analysis code:
  - `live_score.py` a29d9b01 (an environment override only; item 32);
  - `e1_analysis.py` a6e756a0;
  - `stage_diagnostics.py` 83e21d56.

**Numbers:** `numbers.csv` holds every number in this write-up with its file and key, or, for numbers quoted from documents, the document and section.

## 11. Next steps

The full plan is in `SYNTHESIS_AND_NEXT_PLAN.md` §6 and §8. In short:
- Stop live runs of this design.
- Next, run an offline test bench on the saved stages ($0). It compares ASP's score, ASP's score with a novelty term or with guesses in scanned ground masked out, and a guess-free novelty rule, on oracle, LLM, placebo and empty guess sets. Fix the yardstick's wall problem first.
- Go live again only if some rule makes exact objects beat random ones by a wide margin and the LLM beat random beyond noise.

## 12. After the package: plan steps 6-8 (10-30) [R under new pre-registrations; X where marked]

These ran overnight on 10-29/30 under three pre-registrations frozen before any result existed: `PREREGISTRATION_BENCH.md`, `_FRONTIER_SEEDS.md` and `_DETERMINISM.md`. None changes a result above. The full report is `docs/checkin/review_2026-10-29/STEPS_6_TO_10_OUTCOMES.md`; DEVIATIONS items 36-39 log the changes. Spend: $0.
- **Offline bench (step 6) [R, new pre-registration; the descriptive results are X]: no rule passes, so live work stops.**
  - **Yardstick:** regret is counted in true unmapped objects visible past HM3D walls, over 384 saved stages. This count includes only 19% of the objects the robot maps next. It passes its pre-registered check on one reading only; on the other, the pre-registration makes these results provisional.
  - **Exact objects:** with exact-object guesses, the best rule's regret is 15% below random guesses, against a bar of 30%. For R4 the oracle/placebo regret ratio is 0.850, CI 0.804-0.893; for ASP's own score it is 0.933. Under the unregistered wall-map variants the best gain is 25%.
  - **DeepSeek's guesses:** no rule passes the test that they beat random ones by more than two random draws differ. R3 comes nearest: LLM − placebo A −1.03, CI −1.76 to −0.36, against a floor of −0.82.
  - **Under ASP's own score,** LLM and random guesses show no detectable difference: regret 9.12 vs 9.15 on official stages, difference −0.03, CI −0.76 to +0.70.
  - **Steps 9 (replay simulator) and 10 (live confirmation)** are not run, by the plan's rule.
- **Seeded frontier explorer (step 7) [R, new pre-registration]: neither LLM nor random guesses beat nearest-frontier exploration on these homes.**
  - Official − frontier: −0.012, CI −0.053 to +0.029, p 0.47.
  - Placebo − frontier: −0.025, CI −0.050 to +0.002, p 0.07, Holm 0.14.
  - At 50 m both have the same sign.
  - [X] **Per scene** (small cells, not tested): on 00853, official − frontier is −0.052 and placebo − frontier −0.047; on 00871 they are +0.028 and −0.003. Under the registered reading these splits give no credit to LLM content.
  - [X] **Walls:** frontier's paths almost never enter wall-map cells (0.00-0.17% of path points), while the E1 runs' paths do (2.4-7.0%). Both explorers move without a collision check, so the comparison may be tilted, in an unknown direction.
  - [X] **Stops:** on 00871, frontier stops and scans far more often over the same 60 m, with 41-46 stages against 12-28 for the ASP arms.
- **Repeat runs (step 8) [R, new pre-registration]: same-seed runs still split at the first stop.**
  - Three placebo replicates ran on 00853/42 with a quiet-wait snapshot: the map is copied only after its file has stayed unchanged for 15 s.
  - No pair had matching stage-0 maps. Stage-0 stops lay 0.24, 3.60 and 3.84 m apart, against 0.77-1.99 m for the three earlier attempts without the wait.
  - As registered: seeds do not pair runs, so plan at least 5 replicates per cell.
  - [X] **The copy was not early.** Each copied file already covered the whole scan. In one run the mapper made fewer objects from the same scan and never recovered them, so a later snapshot would likely not help [I]. A replay simulator is the other route (not registered).
