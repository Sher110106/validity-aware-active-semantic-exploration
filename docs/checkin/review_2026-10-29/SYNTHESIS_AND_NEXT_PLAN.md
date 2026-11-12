# Why the arms explore alike, what ASP missed, and what to do next

2026-10-29, 17:00 IST. This merges two independent reviews by Opus 5.5 at max effort: REVIEW_A_mechanism.md (code and run data) and REVIEW_B_paper_field.md (the ASP paper and the literature). Each reviewer worked alone from CONTEXT_given_to_reviewers.md, wrote its own replay of the author's viewpoint scorer, and labelled claims verified [V], inferred [I] or speculative [S]. Their scripts and outputs are in tools/live_policy/review_2026-10-29/A and B. The main session re-checked the score formula (calculate_uncertainty.py:501-549) and the unused room plan (mid_planning.py:122; find_mid_planner_target has no caller) against the pinned code.

## 1. The answer in one paragraph

ASP picks a viewpoint by how much its eight guessed scene graphs **disagree** about what a camera there would see. Its score is the mutual information between the next view and which ensemble member is right. Nothing in it asks whether a guess is true, and nothing measures unknown space [V].

So the guesses matter only by existing and spreading out:
- With no guesses the score is nearly flat and the robot barely moves [V].
- With any guesses, LLM or random, the score peaks near spots dense with disputed guesses [V].
- Swapping DeepSeek's guesses for a random placebo set moves the chosen spot about as far as swapping one random set for another: 2.1-2.6 m against 2.2-2.3 m over 394 replayed stages [V, A].

On top of that, three sources of noise of the same size act on every stop:
- a second re-scoring step, after which the top-scored candidate becomes the stop in only about a fifth to a third of stages;
- random tie-breaks in 16% of stages;
- mapper timing, which makes two runs with the same seed and arm part at the very first stop [V].

Finally, the detector maps only 5-14% of true objects near a stop at the next stage [V].

This is why the validity layer and the filter could not move F1. The objective has no term that rewards a guess for being right, so it can use correct content only when the guesses themselves sit on true objects.

**Correction after the objective audit (section 8, verified by an independent recompute).** "Effectively random" overstates it:
- With exact true objects as guesses, the score does rank views by the number of true unseen objects they show (median per-stage ρ 0.45).
- DeepSeek's guesses do only slightly better than random ones: ρ 0.20 against 0.10-0.16, and +0.06 over a placebo draw on the same states, almost all of it on 00853.
- At the decision level, the LLM's stop still moves no more than a random redraw.
- A guess-free rule, "far from where the robot has walked", ranks views better than ASP's score does with LLM or random guesses (ρ 0.50 vs 0.20).

So the loop can use content when the content is exact. DeepSeek's content is too inaccurate to steer it (2.6% of its new objects lie within 0.5 m of a true one). Planning noise and the detector, which maps about 1 in 12 unseen objects in view of a stop, then shrink what is left.

## 2. The user's questions

**Why do we explore the same thing whatever the LLM says?** The score rewards disagreement among guesses, not their truth.
- Random guesses of the same shape disagree at least as much as the LLM's. Same-label agreement within 1 m is 29% for the LLM and 4% for the placebo, so the LLM's pull is if anything weaker [V, B].
- Swept-area overlap is the same across arms as across seeds: Jaccard at 60 m is 0.56-0.62 between arms and 0.60-0.65 between seeds [V, A and B].

**Is it random?** Not as a coin flip: the pick is a fixed function of the map, the guesses, a random 300-view sample, reachability and a tie-break. With respect to guess content, though, it acts as one more random draw.
- The LLM's pick fell inside the random-guess spread in 6 of 9 fully replayed states [V, B].
- The top-1 moves no more for LLM-vs-placebo than for placebo-vs-placebo over 394 stages [V, A].
- It is not frontier-like either. The score barely tracks distance from walked ground (ρ 0.04), and 44-62% of guesses in the final view lie in ground already scanned [V, A].

**Then what does ASP contribute?**
- An open, working system: live layered scene graph, LLM completion with a collision tool, a clean mutual-information formula for scoring views over sampled graphs, and nvblox/A* planning [V].
- A prediction result that does not depend on exploration: 9 of 28 unseen rooms placed within 2.5 m [V, paper v2].
- It does **not** show that LLM semantics make exploration better. Our placebo reproduces its "sees farther" behaviour: placebo steps average 4.07 m against the LLM's 3.52 m, where the paper's case is ASP 3.74 m vs frontier 2.76 m [V, B].
- Its margins over frontier, 2.5-7.9 F1 points from one run per scene, sit inside the 5-12 point spread we see between seeds of one arm [V numbers; I comparison, since the references differ].

## 3. What the author missed

| # | Missed | Evidence | Label |
|---|---|---|---|
| 1 | No control separating guess content from the presence of guesses (no random or placebo hypotheses through the same scorer). Baselines are frontier and SSMI only. | ASP v1 §IV-D, v2 §IV-A; our E1 +0.013 AUC, CI −0.000 to +0.025 | V |
| 2 | One run per scene; no seeds, repeats, intervals or tests. Same-scene numbers moved between v1 and v2 by as much as the claimed margins (00853 frontier 48.3→58.8, ASP 59.0→66.7). | Both PDFs | V |
| 3 | The objective rewards disagreement, not truth or discovery. A true guess all members share scores zero; a guess in scanned free space scores fully. The paper calls ignoring well-inferred rooms a feature. | calculate_uncertainty.py:501-549; v2 §IV-B | V (cause), I (effect) |
| 4 | The reachability step changes the objective: it re-scores the top 10 with no move cost and a 4 m camera. | calculate_uncertainty.py:563-612; exploration_pipeline.py:779-833 | V |
| 5 | The room-level graph plan is computed but never used for motion. | mid_planning.py:122; find_mid_planner_target has no caller | V |
| 6 | The two "bootstrapped" tracked graphs add a guess-free disagreement term that points at already-mapped objects. A 10 s file timeout can drop a track. | calculate_uncertainty.py:311; logs | V |
| 7 | A self-built reference (the same mapper, driven by hand) hides the detector's ceiling. Under human HM3D labels, a frontier explorer run to exhaustion reaches recall of only 0.26 (00853) and 0.17 (00871). | v2 §IV-A; f1_score_plot.py:194; frontier_60m_scores.json | V |
| 8 | Unreported sources of chance: completion order, dropped members (7-24% per LLM run), random ties (16%), unreachable targets (about a third), mapper timing. | logs, pose_log.json | V |
| 9 | The method shifted between versions: v1 Eq. 5 lacks the distance term the code always had; the confidence bar fell from a majority to 2 of 8; v1's admission of manual rejection of LLM outputs is gone from v2. | v1 vs v2 text | V |

## 4. The critical gap that remains

**G1: what the guesses say versus the fact that there are guesses.** No published study of LLM- or VLM-guided exploration separates the value of what guesses say from the effect of having guesses at all, or measures how often content changes a decision. The closest work:
- MAPLE (arXiv 2610.28566, Oct 2026) finds the 2D-occupancy version of our null: better prediction does not reliably mean better exploration, and how hypotheses are scored matters more.
- MapEx's no-prediction ablation is "competitive".
- SGImagineNav has a no-prediction ablation and a ground-truth oracle, but no random control and no intervals.
- Two 2026 papers adopt ASP and compare it only with geometric explorers.

**G2: the score and the metric reward different things. This is the cause of G1.** Disagreement gain has no truth term. In the geometric work it comes from (He et al. 2023, MapEx, UPEN), "unknown space seen" and "map gained" nearly coincide. For object-level semantic maps they do not. Before this audit, no one had checked whether the score ranks views by the number of true unseen objects they show.

Our audit (section 8) gives a quantitative answer:
- weakly with LLM or random guesses (ρ 0.10-0.20);
- moderately with exact objects (0.45);
- worse than a guess-free "far from the walked path" rule unless the guesses are exact.

The score passes on whatever truth the guesses carry, and it adds no novelty term of its own.

**G3: the detector's ceiling and the choice of reference.** Recall at exhaustion is 0.17-0.26 against human labels. Most true objects near a stop go unmapped, and a detector-built reference hides this. Even a perfect stop rule faces this cap.

**G4: evaluation practice.** Seed spread inside one arm exceeds the margins the field reports from single runs.

The gap the author missed, and that the viewpoint evidence exposes, is G1 with its cause G2.

## 5. Where the reviews corrected the main session

- **H2 was wrong.** There is no unknown-space term; the guesses are the score. Its content-independence comes from the score rewarding disagreement, not from another term dominating.
- **H5 was partly wrong.** The paper does run a frontier baseline on the same stack (and SSMI). It lacks a placebo, seeds and a human-label reference.
- **The E3 gate verdicts mislead as labels.** Drawn and undrawn true objects sit side by side, so the drawn-vs-undrawn contrast has a low ceiling: standing on a random drawn object gives only 0.015-0.058, and the best possible spot 0.18-0.22 [V, A].
  - The 00853 "broken" gaps (0.027-0.035) are what standing on a random drawn object would give. They do not show a broken loop.
  - The 00871 "detector-limited" verdict misses that planning is also a large limit.
  - The registered verdicts stand as registered. The write-up must add the ceiling table, labelled post hoc.
- **Two arm differences besides content went unlisted in E1:**
  - The candidate anchor is the first LLM call to finish in LLM arms, but always track 0 member 0 in no-LLM arms.
  - 7-24% of LLM member slots were dropped per official run, against none in placebo.
- **Seeds do not pair runs.** Same-seed runs part at stop 0 because the first map differs.
- **ASP v2 (June 2026) exists** and changed the method; the write-up should cite both versions.
- **00871 deserves one line.** All three official runs beat all three placebo runs on 00871, while 00853 points the other way. With two homes the blocked test cannot tell a home-specific effect from noise (p 0.22).

Where the reviewers differ:
- **How often the top-scored candidate becomes the stop:** 18% (A) against 31% (B). The audit reconciled them exactly, and the denominators are not the cause; every stage's target matches a logged top-10 pose.
  - A ranks within the full first-stage top 10 and takes the published target: 71/394 = 18.0%.
  - B ranks within the list after the 1 m history filter, which has already removed the first-stage best in 25.9% of stages, and takes the first tied pose: 112/364 = 30.8%.
  - 18% means "the published target is the first-stage best"; it says nothing about where the robot stopped.
- **Whether ASP is frontier-like:** B inferred a pull to the map's edge from where guesses are placed; A measured almost none (ρ 0.04). A's measurement stands.

## 6. Next plan after tonight (about 20:30 IST)

Both reviewers say the same thing plainly: **stop live runs of this design after tonight.** More runs at affordable n cannot separate content from noise, and the mechanism says a better LLM or filter would not move this score. Do not spend the Gemini credit on live runs.

### Tonight (10-29)
1. Apply the registered 18:00 rule for oracle 00871 seed 44 and let it finish. Launch nothing after it.

### By the package deadline (10-31 20:00 IST), all $0, labelled exploratory beside the registered results

2. **Decision-replay table:**
   - the 97% reproduction of logged top-10 lists;
   - the swap table (no guesses / placebo / oracle pool against the placebo-placebo noise floor);
   - the rank histogram after re-scoring;
   - score variance shares.

   Decision rule: if the stage-bootstrap 95% CI of the LLM-vs-placebo top-1 distance lies wholly below the noise floor, report "decisions are content-sensitive"; otherwise "content enters stops as noise". Source: review_2026-10-29/A. (Both reviews)
3. **Objective audit, the direct test of G2.** For every saved stage, count the not-yet-mapped HM3D reference objects visible (same camera and occluders) from the live stop, from the first-stage best, and from all 300 candidates. Then compute the Spearman ρ between ASP's score and that count, per arm, oracle included. This needs the two HM3D reference YAMLs copied off the host; they are not scores.
   - ρ ≤ 0.1 everywhere: headline "the viewpoint score does not rank views by true unseen objects".
   - Oracle ρ ≥ 0.3 while LLM and placebo stay near 0: content quality is a limit too.

   (Both reviews)
4. **Headroom and E3 ceiling tables:** recall at exhaustion, recall at 60 m per arm, per-stage mapping base rates, the share of guesses in scanned ground, and the drawn-vs-undrawn ceilings beside the gate. (Both reviews)
5. **Write-up:**
   - E1/E2/E3 as registered, with intervals;
   - steps 2-4 as exploratory mechanism;
   - an audit of the ASP paper (v1 and v2);
   - errata for the September static claim (unanimity equals deleting all guesses);
   - the two non-content arm differences;
   - the note that seeds do not pair runs.

### Next 2-3 weeks (only if the user wants to continue)

6. **Offline regret bench on the saved stages** ($0, laptop, 3-5 days). Compare decision rules:
   - ASP's score;
   - ASP's score with guesses in scanned ground masked out;
   - expected discovery (support-weighted guessed objects in view outside scanned ground);
   - novelty only;
   - random.

   Run each on oracle, LLM, placebo and empty hypothesis sets. The utility is reference-visible new objects.

   Go further only if some rule makes oracle beat placebo by at least 30% on regret and LLM beat placebo beyond the noise floor. If none does, write up the audit and stop.
7. **Seeded frontier explorer, 3 seeds x 2 scenes** ($0, 12-24 host h). Today there is one frontier run per scene, so no ASP-vs-frontier statement is possible.
8. **Deterministic stage snapshot** (frame count or Hydra idle flag instead of file-size stability), tested with 3 same-seed placebo replicates (about 12 host h). This decides whether runs can be paired by seed or need at least 5 replicates per cell.
9. **If step 6 finds a rule and step 8 works, a detection-replay simulator** (B's design). Record the scan graph at a 0.75 m pose grid with the real stack (5-10 host h per scene), then run 2-4 scenes x 50 seeds offline. Validate first: replayed live paths must match live per-stage F1 within ±0.01.
10. **Conditional live confirmation.** First the $0 arms (oracle vs placebo under the new rule, 2 scenes x 4 seeds); then, only if that is positive, a DeepSeek arm inside the $25 left. Use the same registered test as E1, with 60 m and 50 m agreeing in sign.

### What a publishable study would need

- 8-10 human-labelled scenes, at least 5 seeds per arm, and a deterministic or replicated mapper.
- Arms: frontier on the same detector; ASP as published; ASP with the better rule; shape-matched and uniform placebo; no guesses; exact-object oracle.
- Metrics: F1 AUC on human labels; F1 relative to the detector's ceiling; decision sensitivity.
- Pre-registered blocked tests with intervals; code and replay data released.
- Detecting 0.01 AUC at the measured spread needs about 60 runs per arm. That is out of reach live, so the simulator route plus a live subset is the only feasible one.
- The honest framing is a placebo-controlled audit of LLM-guided active semantic perception: the objective rewards disagreement, not truth. If step 6 succeeds, add a fixed objective.

## 7. Not yet checked

- Reachability of counterfactual stops: the nvblox grid is not saved.
- The exact E3 eligible sets: oracle_sets.json and the reference are not local. A used the pool of drawn objects; its approach gaps still matched the gates within about 0.01.
- The cause of stage-0 map differences between same-seed runs. Snapshot timing is inferred.
- Literature depth: ASP v1/v2, MapEx and MAPLE were read in full; the rest by sections or abstracts. "No prior semantic placebo" rests on about 20 searches per reviewer [S].

## 8. Objective audit and mechanism tables (plan steps 2-4, done 17:40 IST)

Each result was built by one agent and recomputed by an independent verifier; both verdicts are "holds with corrections". The tables below include the corrections. The objective-audit verifier recomputed 12 stages with the pinned calculate_uncertainty.py loop and matched every per-stage value exactly. Full reports are in AUDIT_objective_verified.md and AUDIT_tables_verified.md; scripts and outputs are in tools/live_policy/review_2026-10-29/audit/. No F1 or AUC of any e3 run was computed.

Coverage: 384 of 396 replayed stages (12 dropped because the replayed top 10 differed from the log).
- U_360: the number of reference objects not yet mapped (oracle-set labels, the live_policy.oracle_eligible rule) that are visible over a full turn at 0.1-4 m, with the observed structure as occluders.

**Does ASP's score rank views by true unseen objects?** The second column is the median per-stage Spearman ρ between the score and U_360; the third is the live stop's percentile among the 300 candidates, with a stage-bootstrap 95% CI.

| Arm | ρ(score, U_360) | Stop percentile | Stop percentile, floor candidates only |
|---|---|---|---|
| official | 0.20 | 0.63 (0.58-0.67) | 0.59 (0.54-0.63) |
| placebo | 0.10 | 0.61 (0.57-0.65) | 0.53 (0.48-0.58) |
| filter_only | 0.12 | 0.64 (0.58-0.69) | 0.61 (0.56-0.67) |
| oracle | 0.45 | 0.78 (0.74-0.82) | 0.74 (0.69-0.79) |

**Matched states.** Same robot state and same 300 candidates; only the hypothesis files change. Each cell is the median ρ(score, U_360).

| Stages of arm | Actual files | Observed only | Placebo draw | Oracle draw | Guess-free "far from walked path" |
|---|---|---|---|---|---|
| official (119) | 0.20 | -0.07 | 0.19 | 0.44 | 0.50 |
| placebo (110) | 0.10 | -0.01 | 0.16 | 0.47 | 0.21 |
| filter_only (97) | 0.12 | -0.10 | 0.12 | 0.39 | 0.39 |
| oracle (58) | 0.45 | -0.08 | 0.01 | 0.48 | 0.40 |

- On official stages, LLM files beat a placebo draw in 73 of 119 stages (p 0.008, stage level). Run medians are +0.07 to +0.25 on 00853 and about 0 on 00871.

**Decision replay (official arm).** The LLM-vs-placebo median top-1 move minus the placebo-vs-placebo floor is +0.09 m, CI −0.25 to +0.38. Verdict: "content enters stops as noise". The LLM does reshape the whole field more than a redraw does (rank ρ 0.60 vs 0.73), but not the stop.

**Yardstick.** Of the unseen objects in view of a stop, 6.9-9.0% appear in the next map, against 0.3-0.8% of those out of view: about 1 in 12.

**E3 ceilings (exact eligible sets).** On the pooled convention, the live approach gap is 19-37% of what a rule that just goes where the drawn objects cluster would give. On the 00853 verdict run, under the unit-mean convention, the share is 0.04 (CI −0.18 to 0.23). So "broken" is not supported, but a near-zero pull on 00853 is not ruled out either.

**Headroom (E1/E2 and frontier only).** Recall at 60 m, mean over runs:

| Scene | Official | Placebo | Filter | Frontier at 60 m | Frontier at exhaustion |
|---|---|---|---|---|---|
| 00853 | 0.175 | 0.151 | 0.184 | 0.194 | 0.261 |
| 00871 | 0.122 | 0.084 | 0.085 | 0.140 | 0.168 |

The frontier explorer at 60 m is above every arm's mean in both scenes.

Caveats:
- The reference has no wall nodes, so unmapped walls do not block U_360. U_360 therefore overcounts, and it may favour any rule that pulls outward, including the "far from walked path" proxy.
- The oracle draws come from the same set U counts, so the oracle rows are partly high by construction. They show the "exact objects" level, not an independent test.
- The 0.5 m unmapped rule lets some mapped objects leak in. With a 1.0 m radius, ρ is 0.17/0.06/0.04/0.42 and no rule outcome changes.
- The placebo's stop advantage is fragile: a run-cluster bootstrap gives 0.49-0.73.

**What this changes in the plan.** Step 6's regret bench should keep the guess-free novelty rule. It already beats ASP's score on this yardstick, and the obvious candidate fix is ASP's score plus a novelty term, or with guesses in scanned ground masked out. Fix the yardstick's wall problem first: add walls from the HM3D mesh or the frontier reference as occluders.

## 9. Update after the final checks (10-29, 22:00 IST)

The final write-up (`tools/live_policy/results_2026-10-31/WRITEUP.md`) went through two rounds of independent checks. Four points change or qualify sections 1-8:
- **The guess-free novelty rule beats ASP's score only under the full-turn count (U_360).** Under the planner's own camera-cone count it does no better than DeepSeek's guesses (0.31 against 0.30 on official stages). Step 6's bench should therefore test it against a yardstick with walls before treating it as the obvious fix.
- **The exact-object shift of the top-scored candidate (+0.68 m) holds on 00853 stages only.** It is +0.54 m (CI −0.23 to +1.20) on counted runs and about 0 on 00871. Oracle sets also differ from placebo sets in member agreement, so truth and agreement are confounded.
- **A registered secondary favours the LLM at the 60 m endpoint.** F1 at 60 m, official minus placebo, is +0.043 (p 0.015, both scenes; Holm over six secondaries 0.09), while the primary AUC is null.
- **The E3 per-scene reading (deviation 26) was chosen after the 00871 gate passed and after the placebo AUCs of both scenes had been seen.** The 00871 contrast carries that caveat.

## 10. Steps 6-10 done (10-30, revised 10:45 IST after an independent review)

The 2-3 week part of §6 ran overnight under three pre-registrations frozen before any result existed. The full report is STEPS_6_TO_10_OUTCOMES.md; DEVIATIONS items 36-39 log the changes. Spend: $0.
- **Step 6, offline bench: no rule passes.**
  - **Yardstick:** the bench counts true unmapped objects visible past HM3D walls. This count includes only 19% of the objects mapped next, and it passes its pre-registered check on one reading only, so the bench numbers are provisional.
  - **Exact objects:** with exact-object guesses, the best rule's regret is 15% below random guesses (21-25% under unregistered wall-map variants). The bar was 30%.
  - **DeepSeek's guesses:** no rule passes the registered test that they beat random ones beyond the noise floor. R3 comes nearest: past the floor at the point estimate, but not with its CI.
  - **Check:** an independent verifier reproduced every pick and decision number.
- **Step 7, seeded frontier explorer: neither LLM nor random guesses beat nearest-frontier exploration on these two homes.**
  - Official − frontier: −0.012, CI −0.053 to +0.029.
  - Placebo − frontier: −0.025, CI −0.050 to +0.002.
  - Holm p: 0.47 and 0.14.
  - An independent recompute matches.
- **Step 8, quiet-wait snapshot: seeds still do not pair runs.**
  - No pair of three same-seed replicates had matching stage-0 maps.
  - The data argue against §7's snapshot-timing cause. The copies came at about the same moment in every run, and each copied file already held the mapper's poses to the end of the scan. The objects one run lacked never appeared in its later maps [I].
  - So the split lies in what the mapper makes of a scan. A wait on the mapper's own progress (frame count or idle flag) is untested, and unlikely to help.
- **Steps 9 and 10: not run,** because step 6 found no rule.

The plan is complete. Two points correct earlier sections:
- **The pinned pipeline moves the robot with `set_state` and no collision check.** Its paths enter wall-map cells at about the rate of random points.
  - The frontier explorer uses the same call, but its paths almost never enter wall cells (0.00-0.17% of points, against 2.4-7.0% for E1 runs).
  - So the step 7 comparison may be tilted, in an unknown direction.
- **The "far from walked path" rule shows no detectable difference from ASP's score** under a wall-aware count (step 6: R1 − R5 with the actual files is −0.16, CI −0.53 to +0.20). It does not beat ASP's score, as §8 suggested.
