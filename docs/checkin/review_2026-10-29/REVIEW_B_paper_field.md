# Review B: the paper, the field and the contribution

Reviewer B, 2026-10-29 IST. Labels: **[V]** verified (I checked the file, log or paper cited), **[I]** inferred from verified facts, **[S]** speculative. My scripts and their outputs are in `/tmp/cvp_review/work_B/`; papers are in `/tmp/cvp_review/papers_B/`. I computed no F1 or AUC for any e3_* run. The harness blocked me from writing this file to `/tmp/cvp_review/report_B.md`; the parent can save it there.

## Answer

The user is right that the validity layer could not raise F1, but the reason is sharper than "F1 depends on exploration". In ASP the guesses never enter the map; they only choose where the robot stops. The viewpoint score rewards places where the eight guessed graphs *disagree* about what the camera would see. It never asks whether a guess is true, and it falls where members agree [V, code below]. Random guesses of the same shape disagree at least as much as the LLM's, near the same edge of the map, so they send the robot to the same kind of places. Our placebo even takes longer steps than the LLM (4.07 m vs 3.52 m per step), which is the "sees farther" behaviour the paper credits to semantics [V]. When I replay the planner's choice offline, a fresh 300-viewpoint sample moves the pick by a median 1.2-4.7 m, and a fresh random guess set moves it 1.7-5.3 m. The LLM's pick sits inside the random spread in 6 of 9 states and at or beyond its edge in 3 [V]. Content moves some single decisions, but area covered and F1 do not differ beyond seed noise. Then the detector caps what any route can add: even after the frontier explorer ran out of frontiers it had mapped only 26% (00853) and 17% (00871) of human-labelled objects [V]. So the choice is not a coin flip, but the part that depends on content is small next to sampling noise and the detector's limits. The ASP paper never ran the control that would show this (random guesses through the same scorer), reports one run per scene with no seeds, and scores against a map built by its own detector [V]. The gap in the field is the same: no one has separated what semantic guesses *say* from the fact that guesses *exist*, or checked that the score ranks views by true new objects. The closest work (MAPLE, October 2026) finds the 2D-occupancy version of our null. The honest plan: stop live LLM runs now; let tonight's registered $0 oracle run finish; spend 10-30 and 10-31 on $0 offline audits and the write-up; do further live work only after a fast replay simulator and a truth-sensitive score exist.

## 1. How the viewpoint choice actually works

All line numbers refer to `/tmp/cvp_review/pipeline_pinned_copy/scripts/`. All of this is [V] unless marked.

**Inputs.** At each stage the LLM (or our arm) writes up to 8 hypothesis graphs: 4 samples for each of two tracked graphs (`llm_completion.py:458-479`). Each is the observed graph plus guessed objects and rooms (`llm_completion.py:388`). The planner copies each graph 3 more times with object centres jittered by up to ±0.25 m in x and y, using the same seeds (SEED+k) for every member (`calculate_uncertainty.py:249-313`; `pipeline_config.yaml:133-136`).

**What a view "sees".** For a pose x (position, yaw), the observation Y(G, x) is the multiset of object names inside a 640×480 frustum (fx = 320, so about 90° wide; 0.5-3 m range; 10° down tilt) whose centre ray is not cut by a wall, window, curtain or door box (`calculate_uncertainty.py:14-98, 377-424`). The room observation is the most common parent room of the visible objects (`:480-488`).

**The score.** With m hypothesis graphs (m ≤ 8) and N = 4 versions each:

  I_obj(x) = H(Y) − (1/m) Σ_g H(Y | g), with entropies over the m·N observations (`:501-522`); I_room the same over room observations.

  Stage 1: S(x) = I_obj(x) + 1.0·I_room(x) − 0.2·‖x − x_robot‖ (`:531-549`; weights at `pipeline_config.yaml:140-141`).

This is the mutual information between the next observation and *which member is right*, a committee-disagreement score. It is 0 where all members show the same names and at most log2(m) (3 bits for 8 members) per term where all differ.

**Candidates.** 3,000 uniform draws in the box spanned by every node of every hypothesis graph (`:315-333, 437-443`), kept if within 3.5 m of an object in the *first* hypothesis file (`:430, 446-452`) and if any graph shows any object (`:477-478, 496-497`), up to 300. The random generator is seeded once per run and carries over between stages (`:107`; one calculator per run, `exploration_pipeline.py:185`).

**Final pick.** Keep the top 10 by S, drop those within 1 m of past stops (`calculate_uncertainty.py:135-142`). For each, ask the occupancy planner where it can actually get; re-score I_obj + I_room at that endpoint with a 0.1-4 m camera and *no* move cost (`exploration_pipeline.py:779-818`; `calculate_uncertainty.py:563-612`). Take the best; break ties at random (`exploration_pipeline.py:833`). The robot is sent to the original target (`:793, 807`) and does a full 360° turn when it stops (`:717-734`).

**Which terms depend on guessed content.** I_obj and I_room do, entirely. There is **no** term for unknown space, coverage or truth. The parts that do not depend on content are: differences between the two tracked graphs (up to about 2 bits with no guesses at all), the jitter, the move cost, the 300-view sample, reachability, the tie-break and the full turn. This corrects H2 in CONTEXT.md: the guesses *are* the score.

**Four consequences.**
1. Truth never enters. A wrong guess placed where other members put nothing scores the same as a right one [V].
2. Agreement lowers the pull. If all members put the same bed in the same place, the score there falls towards 0 [V]. With an observed-map metric, good, agreed guesses push the robot away from what they predict [I].
3. The chosen yaw hardly matters, because the robot turns 360° at every stop [V code; I effect]. The paper says as much about early stages (v2 §IV-B).
4. "First hypothesis file" means the first LLM call to finish in the LLM arms (`as_completed`, `llm_completion.py:475`), but always track 0 member 0 in our no-LLM arms (`tools/live_policy/live_policy.py:385-442`). This is a small difference between arms that is not about content [V].

**Replay check [V].** I rebuilt the scorer offline (`work_B/replay.py`). It calls the pinned functions for jitter, grouping, room mapping and entropy, and uses a vectorised visibility test that gave 0 mismatches against the pinned one on 30 poses × 32 graphs. It reproduces the logged top 10 at stage 0 of `e1_00853_s42_placebo_60m` exactly, and the logged best score (3.9750). It also reproduces the real stage-0 target of `e1_00871_s42_official_60m` ([-1.46, 7.59]). It cannot replay reachability, because that needs the live occupancy grid.

**What happened live [V]** (`work_B/reach.py`, 364 decisions, 21 counted runs, from `stages/k/pose_log.json` and `stages/k+1/executed_path.json`):
- The stage-1 top candidate was the final pick in only 31% of decisions.
- 33% of picks were unreachable at plan time (filter_only 16%, official 34%, oracle 36%, placebo 46%).
- 57 picks (16%) were ties broken at random.
- The robot stopped within 1 m of its target in 83% of stages. The median move from start to stop was 2.8-3.2 m.

## 2. Why exploration looks the same across arms

**The paths split at once, but the area covered does not differ more than chance [V]** (`work_B/paths.py`):
- Same scene and seed, different arms: stage-0 targets are 0.25-5.1 m apart (median about 2 m). Even stage-0 inputs differ: `e1_00853_s42_official_60m` had one tracked graph and 4 members at stage 0, its placebo two graphs and 8 members.
- Swept-area overlap (cells within 2 m of the path) as Jaccard index at 60 m: 0.60 for the same arm with different seeds (18 pairs), 0.56 for different arms with the same seed (28 pairs), 0.55 for different arms and seeds (54 pairs). At 20 m: 0.57 / 0.55 / 0.55.
- Changing the guess source changes the route no more than changing the seed does.

**Random guesses reproduce the "semantic" behaviour [V]** (`work_B/steps.py`):
- Mean path per step to 60 m: official 3.52 m, filter_only 3.74, placebo 4.07, oracle 4.77.
- The paper's case for "sees farther": ASP 3.74 m vs frontier 2.76 m (v2, Fig. 3 caption); 4.6 vs 2 m in v1.
- A placebo that knows nothing about the scene steps farther than the LLM. The long steps come from the score and the sampler [I].

**Members disagree everywhere they guess [V]** (`work_B/agree.py`). Share of guessed objects that another member of the same track also guessed, with the same label:

| Arm | within 0.5 m | within 1 m | within 2 m | any label within 1 m | objects |
|---|---|---|---|---|---|
| official (LLM) | 17.7% | 29.4% | 45.6% | 71.6% | 7,854 |
| placebo | 1.2% | 4.4% | 15.4% | 41.4% | 8,829 |
| filter_only | 11.5% | 20.6% | 33.2% | 60.1% | 6,147 |
| oracle_visible | 39.3% | 45.5% | 53.1% | 70.8% | 4,796 |

The LLM agrees with itself more than the placebo does, so by consequence 2 its pull is if anything weaker. The oracle agrees most, because members draw from one pool of true objects; true objects shared by several members pull *less* [I].

**Decision replay at fixed maps [V]** (`work_B/drive_decomp.py`; K = 12; the pick assumes every top-10 pose is reachable). For each state I replayed the choice four ways: with the LLM's own guesses; with 12 fresh viewpoint samples and the same guesses (sampling spread); with 12 fresh placebo guess sets on the same observed graphs and member ids, all scored on one shared viewpoint sample (guess spread); and with no guesses.

| State | Members | Sampling spread (m) | Guess spread (m) | LLM to placebo picks (m) | LLM percentile among placebo | Pick distance from robot: none / LLM / placebo (m) | Max IG: LLM / none / placebo |
|---|---|---|---|---|---|---|---|
| 00853 s42 st0 | 4 | 1.62 | 1.84 | 1.87 | 0.58 | 0.13 / 2.43 / 2.68 | 3.50 / 0.00 / 3.89 |
| 00853 s43 st0 | 7 | 2.57 | 1.66 | 2.79 | 0.92 | 0.32 / 4.39 / 2.23 | 4.26 / 1.97 / 4.65 |
| 00871 s42 st0 | 7 | 1.16 | 2.80 | 2.22 | 0.00 | 1.03 / 1.45 / 2.50 | 4.65 / 1.97 / 4.55 |
| 00871 s43 st0 | 8 | 1.60 | 2.74 | 3.55 | 1.00 | 0.23 / 2.55 / 2.91 | 4.15 / 2.00 / 4.51 |
| 00871 s44 st0 | 8 | 2.68 | 2.57 | 3.89 | 0.83 | 1.00 / 2.54 / 3.08 | 4.91 / 2.00 / 4.71 |
| 00853 s42 st4 | 7 | 2.99 | 5.32 | 5.76 | 0.75 | 1.00 / 5.84 / 4.25 | 4.28 / 1.97 / 4.72 |
| 00853 s43 st4 | 6 | 2.99 | 4.61 | 2.88 | 0.00 | 1.73 / 1.04 / 3.05 | 3.25 / 2.00 / 4.19 |
| 00871 s42 st4 | 7 | 4.72 | 4.18 | 3.36 | 0.00 | 1.75 / 3.28 / 3.57 | 4.08 / 1.97 / 4.45 |
| 00871 s43 st4 | 6 | 1.64 | 2.09 | 10.00 | 1.00 | 1.26 / 4.70 / 6.89 | 4.17 / 1.84 / 4.31 |

Read across the rows:
- With no guesses the score is near flat (0-2 bits, all of it from the two tracked graphs differing), so the move cost wins and the robot picks a point 0.1-1.75 m away. *Some* guesses are what make it travel [V].
- Any guess set, random or LLM, gives a peak of about 3.3-4.9 bits [V].
- The pick moves 1.2-4.7 m with the viewpoint sample alone, and 1.7-5.3 m with the random guess draw [V].
- The LLM's pick is inside the placebo spread in 6 of 9 states and at or beyond its edge in 3 (92nd, 100th, 100th percentile). In one state it is 10 m from every placebo pick [V].
- Content does move some decisions, about as often as the random parts do [I].

**The detector then limits what any route can add [V]:**
- Frontier explorer, human-label reference: recall 0.261 at 95.7 m on 00853 (F1 0.364) and 0.168 by 97.8 m on 00871, when it ran out of frontiers (`analysis_pre/frontier_60m_scores.json`).
- Our runs at 60 m reach recall 0.13-0.23 on 00853 and 0.05-0.14 on 00871 (`analysis_pre/scores_e1_e2.json`). The room left for better routing at 60 m is at most about 0.03-0.13 recall.
- In the E3 verdict run (00871 s42), drawn oracle objects were approached slightly more often than undrawn true neighbours (+0.036, p 0.04) but mapped no more often (+0.003, p 0.54; base rate 5.4%).
- 53% of the oracle's new guesses lay in space the robot had already scanned (`gates/E3_gate_00871_s42.json`): the detector had missed those objects while nearby.

**Final F1 at 60 m, human labels [V]:**
- 00853: official 0.268, 0.278; placebo 0.205, 0.259, 0.229; filter_only 0.255, 0.238, 0.326; frontier 0.272.
- 00871: official 0.180, 0.198, 0.180; placebo 0.165, 0.109, 0.108; filter_only 0.211, 0.094, 0.108; frontier 0.207.
- Within one arm and scene, seeds span 5-12 points.
- On 00871 all three official runs beat all three placebo runs on AUC and final F1, while 00853 points the other way. With two homes this could be a home-specific content effect or noise; the blocked test cannot tell (p 0.22) [V numbers; I reading].

**Why, in one chain [I]:**
1. The score is a disagreement map.
2. LLM and random guesses both put disagreement near mapped rooms. The placebo places objects 0.5-2.5 m from a room centre and rooms 1.5-3.5 m out (`live_policy.py:203-277`); the LLM prompt says "project a few meters outward" (`pipeline_config.yaml:92`). Both pull the robot to the map's edge, in a direction set largely by chance.
3. The full turn at each stop means stop positions matter, not view directions.
4. The detector maps few true objects even close up.
5. Noise is large: 7-24% of LLM member slots dropped per official run (12.6% pooled; none in placebo); 16% of picks were random ties; a third of targets were unreachable; mapper timing varies.

Content changes single decisions, but the changes do not add up to a different map.

## 3. Is it random, and what then does ASP contribute

**Is it random?** Not as a coin flip. The pick is a fixed function of the observed map, the guess set, the view sample, reachability and a tie-break. But two of those inputs are random draws (the guess set and the 300-view sample), and together they set most of where the robot goes. The truth of the guesses never enters. At the level of map gain, LLM content behaves like one more random draw [I, from §2]. What is not random is the overall shape: candidates near known objects, guesses near known rooms, a move cost and a full turn. That shape makes ASP act like an explorer that walks to the map's edge in a semi-random direction [I].

**What ASP contributes, read fairly:**
1. An open, working system. It builds a layered scene graph live (objects, rooms, walls and doors, "nothing" nodes), has an LLM complete it with a collision tool, scores views over the completions, and plans with nvblox and A* [V]. It made every test in this project possible. I found no other public end-to-end system of this kind [I].
2. A clean formula for scoring views over sampled scene graphs (v2 Eqs. 1-5) [V]. It can host other objectives; the problem is what it rewards [I].
3. A prediction result that does not depend on exploration: 9 of 28 unseen rooms placed within 2.5 m before the robot found them (v2 §IV-A). v2 counts a guess as "confident" at 2 of 8 members, where v1 needed more than half [V].
4. What it does not show: that LLM semantics make exploration better. Our placebo reproduces its behaviour (long steps, targets past the frontier). Its margins over frontier exploration (2.5-7.9 F1 points at 100% time, v2 Fig. 4, one run each) are inside the 5-12 point seed spread we measured within one arm [V numbers; I conclusion; the references differ, so this is a scale check].

**What this project contributes [I]:**
1. The first placebo-controlled, pre-registered live test of LLM scene-graph guesses in an information-gain explorer that I could find, scored on human labels.
2. An exact-object control with a drawn-vs-undrawn gate.
3. A mechanism account with a replay tool that reproduces logged choices.
4. An honest result for the validity layer: the static gain equals deleting all guesses, and live E2 is null.
5. A reusable recipe.

## 4. What the author missed

1. **No control for content.** Only frontier and SSMI baselines; the ablation is qualitative, on node types (v1 §IV-D; v2 §IV-A) [V].
2. **One run per scene, no statistics.** No seeds, repeats, intervals or tests, and no numeric Lmax in either version [V]. Same-scene numbers moved between versions: 00853 at 100% time, frontier 48.3 → 58.8, ASP 59.0 → 66.7. That is as large as the claimed margins [V].
3. **The score rewards disagreement, not truth.** The paper calls this a feature ("infers the structural layout inside known rooms easily and therefore ignores such rooms", v2 §IV-B). Under an observed-map metric it is why good content cannot show up in F1 [V text and code; I consequence].
4. **"Sees farther" is not semantic.** Placebo 4.07 m vs LLM 3.52 m per step [V; I].
5. **A self-built reference.** The ground truth comes from "manually navigat[ing] ... ensuring ... all objects are detected" with the same pipeline (`f1_score_plot.py:194`). That hides a detector ceiling of recall 0.17-0.26 under human labels [V].
6. **Unreported sources of chance:** completion order, dropped members, random ties (16%), unreachable targets (33%), mapper timing [V].
7. **A shifting method.** v1's Eq. 5 has no distance term, though the code has λd = 0.2; v2 adds it. The confidence threshold fell from more than half to 2 of 8. v1 used manual rejection of LLM outputs (about 0.08 per metre); v2 drops the sentence [V].
8. **Real robot.** Baselines were "manually assisted ... about 2-3 times in each trial"; the trial count is not stated [V].
9. **Our first stage** matched the code and, like the paper, compared only with frontier exploration on one seed. Its static unanimity "gain" equalled deleting all guesses [V].

## 5. The critical gaps that remain, with prior work

**G1. Content versus presence for semantic guesses (the central gap).**
- *The gap.* No published study of LLM- or VLM-guided exploration separates what the guesses say from having guesses at all, or measures how often content changes a decision.
- *Our evidence* [V]: E1 official − placebo +0.013 AUC (bootstrap CI −0.000 to +0.025; permutation CI −0.012 to +0.040; MDE 0.024); placebo steps longer than the LLM; replay.
- *Closest work.*
  - MAPLE (arXiv 2610.28566, Oct 2026): conditioning a random Mondrian prior on observed geometry lifts ROC-AUC from about 0.47 to 0.63-0.64 but "does not consistently" cut travel [V, read in full]. That is our null in 2D occupancy.
  - MapEx (ICRA 2025): its no-prediction "Observed Map" ablation is "competitive" [V].
  - SGImagineNav (RA-L 2026): a no-prediction ablation (+5.25 success points on 400 HM3D episodes) and a ground-truth oracle (72.25%), but no random control and no intervals [V].
  - LGR (2025): random-frontier policy, not random guesses [V].
  - LFG (2023): frontier and LLM variants only [V].
  - Two 2026 papers adopt ASP and compare it only with geometric explorers (2605.18197, 2605.18184) [V].

**G2. The score and the metric reward different things (the cause of G1).**
- *The gap.* No one has checked whether disagreement gain over LLM scene graphs ranks views by true new objects.
- *Our evidence* [V]: agreement 18-29% for the LLM and 39-46% for the oracle; the score is flat without guesses; exact objects lift approach by only 3.6 points.
- *Closest work.*
  - MAPLE: how hypotheses are scored matters more than the predictor; hypothesis-wise visibility cuts travel by about 50% at 5 m.
  - MapEx and UPEN score coverage and variance over predicted occupancy.
  - He et al. (ACC 2024), ASP's source for the formula, works on geometry.
- *Why they fall short.* All are geometric, where "unknown space seen" and "map gained" nearly coincide. For object-level maps they do not.

**G3. The detector's ceiling and the choice of reference.**
- *The gap.* Exploration papers rarely report the most any route could map with their detector against human labels.
- *Our evidence* [V]: recall ceiling 0.17-0.26; per-stage mapping of nearby true objects 5-13%; 53% of oracle guesses in scanned space; the frontier-made reference inflates frontier-like runs 2.9-4.5×.
- *Closest work.* OpenLex3D (NeurIPS 2025) on label choice; SGImagineNav's error analysis (annotation noise, false positives); Hydra and Clio evaluations. None ties the ceiling to how much planning can add.

**G4. Evaluation practice.**
- *The gap.* ASP uses one run per scene; MapEx 40 conditions with no tests; SGImagineNav 400 episodes with no intervals; MAPLE reports intervals.
- *Our evidence.* Within-arm seed spread (5-12 points) exceeds ASP's margins (2.5-7.9) [V].
- *Prior guidance.* Agarwal et al. 2021; Ramakrishnan et al. 2021.

The critical gap the author missed and our viewpoint evidence catches is **G1 with its cause G2**: the score cannot tell true guesses from false ones, so semantic content has no path to the reported metric except through where disagreement happens to land. G3 then caps what is left.

## 6. Next plan after tonight

Budgets: DeepSeek about $25 left of $40; Gemini about $123, unconfirmed; host at most 3 runs at once, 2-7 h each.

**Plain answer: stop live LLM experiments now.** The designs cannot resolve effects below 0.024-0.044 AUC, and the mechanism says a better LLM will not move this score. Do not spend Gemini credit.

**By 10-31 20:00 IST:**

| Step | What | Why | Cost | Time | Decision rule |
|---|---|---|---|---|---|
| A1 | Apply the 18:00 rule. If allowed, let oracle 00871 s44 finish; launch nothing after it | Completes registered E3 | $0; ≤ 7 host h, queued | ends about 20:30 | Ends below 50 m: record as missing, no rerun |
| A2 | Decision-replay audit on every counted stage (official, filter_only, oracle), K = 20 placebo draws and K = 20 view samples | Full table of how often content moves decisions | $0; 4-8 CPU h | 10-30 | Outside the 90% placebo envelope in ≤ 15% of stages: "not beyond chance". ≥ 40%: "content moves decisions; null is downstream". Else "mixed" (now 3 of 9) |
| A3 | Objective audit: with HM3D YAMLs copied off the host, compute Spearman ρ between ASP's score and the count of visible unmapped true objects over the 300 candidates, per arm including oracle | Direct test of G2 | $0; 2-3 h | 10-30 | ρ ≤ 0.1 everywhere: score-metric mismatch is the main mechanism. Oracle ≥ 0.3 while LLM/placebo near 0: content quality is the limit (note only) |
| A4 | Headroom table: recall ceilings, recall at 60 m per arm, base mapping rates, scanned share | States G3 | $0; 1 h | 10-30 | Descriptive |
| A5 | Write-up: registered results as registered; A2-A4 labelled exploratory; paper audit; errata | Deliverable | $0 | 10-31 | Every number traced to file:key; no "ASP beats frontier" or "better LLM would help" claim |

**Next 2-3 weeks:**

| Step | What | Why | Cost | Time | Decision rule |
|---|---|---|---|---|---|
| B1 | Frontier explorer, 3 seeds × 2 scenes, with a registered ±0.25 m start jitter | Only one frontier run per scene exists | $0; 12-24 host h | 1-2 days | Frontier inside official's CI: "neither LLM nor random guesses beat nearest-frontier here" |
| B2 | Detection-replay simulator: record the 360° scan graph at each node of a 0.75 m pose grid with the real stack, then plan offline | Live n for power is out of reach | $0 API; 5-10 host h per scene; 3-5 days of code | weeks 1-2 | Replay 3 live paths; per-stage F1 within ±0.01, else stop |
| B3 | Simulator: 2-4 scenes × 50 seeds; frontier, placebo, oracle (split and shared), saved LLM completions; ASP score vs an "expected unseen objects in view" score | Tests G1 and G2 with power | $0 | weeks 2-3 | Oracle > placebo under the new score but not ASP's: the score is what matters, go to B4. Neither: the detector limits the gain, stop |
| B4 | Conditional: 6 live DeepSeek runs with the new score vs 6 placebo runs | Live confirmation | about $6-10; about 36 host h | 3-4 days | Registered E1-style test; 60 m and 50 m must agree in sign |

**A publishable study [I]:**
- At least 8-10 human-labelled scenes and at least 5 seeds per arm.
- At SD 0.02 AUC, detecting 0.01 needs about 60 runs per arm, roughly 1,000+ live host hours, so the simulator route plus a live subset is the only feasible one.
- Arms: frontier; coverage gain without guesses; shape-matched and uniform placebo; LLM (cheap and strong); exact-object oracle (split vs shared); ASP's score vs a truth-sensitive score.
- Metrics: human-label F1 AUC, F1 relative to the detector's ceiling, and decision sensitivity.
- Concurrent arms with randomised containers; pre-registered blocked tests with intervals; release code and replay data.
- API spend under about $60.

## 7. What I could not check

- **Reachability.** The replay assumes every top-10 pose is reachable; live, a third were not.
- **Replay size.** Only 9 states replayed, at K = 12. The 10th (00871 s44 stage 4) was still running; see `work_B/decomp_s4.log`.
- **Objective audit (A3).** Not done: the HM3D reference YAMLs are only on the host.
- **E3 AUCs.** Sealed; not computed.
- **The paper's figures.** I could not read the curves in Fig. 3 or Fig. 8, or a numeric Lmax.
- **Papers.**
  - Read in full: ASP v1 and v2, MapEx, MAPLE.
  - Main sections only: SGImagineNav, LGR, LFG (experiments), 2605.18184, 2605.18197.
  - Abstracts only: Agarwal et al., Ramakrishnan et al., OpenLex3D, SEA, Probabilistic Scene Graphs, UPEN, Hydra, Clio, He et al.
- **"No prior semantic placebo"** rests on about 20 searches; a missed paper is possible [S].
