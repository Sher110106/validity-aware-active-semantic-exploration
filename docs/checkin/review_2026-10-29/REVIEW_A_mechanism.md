# Reviewer A (Opus 5.5, max effort)


## report_path

NOT WRITTEN. The harness blocked /tmp/cvp_review/report_A.md ("subagents should return findings as text"), so the full report is in these fields. Scripts and outputs are in /tmp/cvp_review/work_A/: parse_runs.py, decisions.py, paths.py, pinned_harness.py, fastig.py, verify_fast.py, replay2.py, summarize_replay.py, chosen_view.py, e3_mech.py, e3_ceiling.py, plus their .json outputs. Downloads are in /tmp/cvp_review/papers_A/.

ANSWER. ASP's viewpoint score does depend on the guesses: remove them and the top-scoring candidate changes in 92% of stages [V: replay]. But it uses them only as a field of ensemble disagreement, not as a claim about where unseen objects are. Any guesses with the same spread make the same kind of field. Swapping DeepSeek's guesses for a placebo draw moves the top candidate about as far as swapping one placebo draw for another (median 2.1-2.6 m vs 2.2-2.3 m) [V]. The rest of the loop then adds noise of the same size: the second stage picks the first-stage best in only 18% of live stages, and mapper timing makes same-seed runs of one arm split at the first stop [V]. So stops are random with respect to guess content. They are not frontier-like either: the IG barely tracks distance from walked ground (rho 0.04), and 44-62% of the guesses in the final view sit in ground already scanned [V]. What ASP's prediction adds is a short-range pull toward nearby spots dense with disputed guesses; the 360-degree scan at each stop does most of the mapping [I]. The critical gap: the objective never rewards a guess for being right. It rewards members for disagreeing, so better, filtered or even exact true guesses cannot reliably move F1 [I]. Honest advice: stop live runs of this design after tonight; use the time left for $0 decision-level analysis.

## why_exploration_looks_the_same

HOW THE VIEWPOINT CHOICE WORKS. The pinned copies match the run-manifest md5s for exploration_pipeline.py, llm_completion.py and calculate_uncertainty.py. The worktree patch touches only configs, LLM-response parsing and a launch file [V: author_worktree_diff.patch]. I replayed the author's scorer offline: imported read-only, plus a vectorised copy that matches it to the last bit on six test stages. It reproduces the logged top-10 exactly in 383/394 counted stages, and the logged second-stage IG of the winner in 393/393 [V: work_A/replay2_results.jsonl].

Score, first stage: S(v) = I_obj(v) + 1.0*I_room(v) - 0.2*|p_v - p_robot| (3D) [V: calculate_uncertainty.py:533-548].
- I_x(v) = H(observations pooled over all files and perturbed copies) - mean over files of H(observations within the file) [V: :501-522]. This is the mutual information between 'which member' and 'what a camera at v sees', capped at log2(8)=3 bits per term [I].
- Groups: each hypothesis file (one member of one track, up to 8 files) plus 3 copies with objects moved U(-0.25,0.25) m in x,y. Seeds are SEED+0..2 for every file [V: :249-313, :311].
- Object observation: the multiset of labels of non-door objects with the centre or a box corner in a 90-degree cone (pitch -10 deg, 0.5-3.0 m) and an unblocked centre ray. Only labels and counts matter, not position [V: :377-424, :510, :40].
- Room observation: the room most visible objects link to [V: :480-485].
- Guesses enter both IG terms. The observed part (each file = observed graph + appended guesses, llm_completion.py:388-389) adds no disagreement within a track [I: same noise seeds]. It does add disagreement across tracks: graph0 and graph1 come from 'bootstrapped subsets' of observations [V: paper v2 sec IV] and differ (e.g. 13 vs 17 objects) [V: e1_00853_s42_official_60m/stages/5]. That is a guess-free IG term.
- The move cost uses neither. No first-stage term sees the occupancy grid, unknown space or scanned ground [V].

Sampling: one draw of 3,000 uniform (x,y,yaw) per call [V: :435-443].
- The box is the bounding box of all nodes of all files and perturbed copies, z = 1.1 m [V: :315-333]. Guesses widen it.
- The RNG is seeded once per run [V: :107]: the same uniform numbers at the same call index in every arm, but a different box and filter [I].
- Keep draws within 3.5 m of a non-door object of the FIRST file in the list [V: :430, 446-452]: the first-finished LLM call in LLM arms (llm_completion.py:475), member 0 of track 0 in no-LLM arms (live_policy.py:412-433).
- Keep the first 300 that see at least one object [V: :458-497].
- The seed does not make stages repeatable [I].

Selection:
- Top-10 by stable sort, so ties keep sampling order [V: :551-555]. Drop any within 1 m of an earlier planning position, or keep all 10 if none survive [V: :133-162].
- For each survivor, A* on the nvblox grid through known-free cells only [V: mid_planning.py:477-481], to the target or one of the 10 nearest free cells found by BFS [V: :168-207, 540-587]. Unreachable candidates are skipped [V: exploration_pipeline.py:783-787]. If the end cell is within 0.1 m, keep the pose; otherwise score a pose at the end cell facing the target [V: :791-808].
- Second-stage score = I_obj + I_room with a 0.1-4.0 m camera and NO move cost [V: calculate_uncertainty.py:563-612]. Keep all within 1e-6 of the best; pick one with a second seeded RNG [V: exploration_pipeline.py:234, 811-817, 833]. The published target is the original pose [V: :807].

Fallbacks:
- No candidate reachable: rng.choice([]) raises 'a cannot be empty' and the whole step retries, with a new LLM or placebo draw and new candidates [V: :873-875; 14 errors in logs].
- No candidate sees any object: best_ig is unbound, which raises and retries [I: :556-560].
- File 0 has no objects: the 3.5 m filter is skipped [V: :453-454].
- IG cannot be -inf [I].
- A DSG timeout (10 s) drops a track; the other graph is renamed graph0, leaving 4 files [V: e1_00853_s42_official log line 42].

Graph planner: it plans a room path through completion 0 [V: graph_planning.py:134-184], but the mid planner reads only the last waypoint [V: mid_planning.py:122], and find_mid_planner_target (:408) has no caller. So the room plan has no effect on motion [V]. Every stop ends with a 360-degree scan [V: exploration_pipeline.py:717-734].

WHY THE ARMS LOOK ALIKE (numbers).

(1) Runs split at stop 0, even within one arm and seed [V: paths.py, paths_pairs.json]. Overlap is the Jaccard of ground within 3 m of the walked path.

| Pair type | Split at stage 0 | Median stage-0 gap | Overlap at 30 m | Overlap at 60 m |
|---|---|---|---|---|
| Same arm, same seed (14 pairs) | 93% | 1.9 m | 0.70 (n=3) | n/a |
| Different arm, same seed (32 pairs) | 94% | 1.7 m | 0.61 | 0.62 |
| Same arm, different seed (22 pairs) | 91% | 1.3 m | 0.64 | 0.65 |
| Different arm and seed (66 pairs) | 89% | 1.7 m | 0.60 | 0.60 |

Same-seed replicates differ because the first scan gives different maps: the 00871 s42 placebo run and its ABORTED attempt had 11 vs 5 objects and 9 vs 7 rooms in track 0 [V]. Likely cause: snapshot timing [I].

(2) The final pick is close to a random draw from the top 10 [V: decisions.py, 393 live stages].
- The chosen target is the first-stage best in 18% of stages (official 11%, placebo 18%, filter_only 25%, oracle 21%), a median 2.0 m away from it.
- Official rank histogram within the top 10: [13,16,11,16,8,15,11,7,10,14].
- 16% of stages tie and fall to the seeded pick.
- The top 10 sit a mean 2.7 m apart.

(3) Planner log values match across content types [V: logs].
- First-stage best IG, median bits: official 3.56, placebo 3.55, oracle 3.34, filter_only 3.22.
- Selected IG: 3.84, 4.02, 4.05, 3.55.
- A* failures per attempt: filter_only 0.96, official 0.36, oracle 0.30, placebo 0.19.
- Steps are about 3.3 m long; the robot ends a median 0.24 m from its target; 23% of targets were moved more than 0.5 m by the reachability check.

(4) Counterfactual on the same 300 candidates [V: 394 stages; same-top1 / median top-1 move / top-10 overlap / rank correlation].
- No guesses: 8% / 2.6 m / 0.21 / 0.56.
- Placebo draw: 8% / 2.6 m / 0.24 / 0.63.
- Oracle-pool draw: 8% / 2.7 m / 0.23 / 0.57.
- Placebo vs placebo (noise floor): 9% / 2.3 m / 0.31 / 0.73.
- Official stages only: LLM vs placebo rank correlation 0.59-0.61, so the LLM shapes the field a little differently. Yet the top-1 moves 2.1-2.4 m vs the floor's 2.2 m.
- With fresh candidate sets the top-1 moves 2.5-2.7 m, against 2.5 m between two placebo draws.
- Removing guesses cuts mean IG from 1.82 to 0.45 bits; 48% of candidates fall to exactly 0.

(5) Score composition, medians over stages [V].
- The guess part carries about 70% of score variance (R^2 0.52), track disagreement 23%, move cost 22% (shares overlap through covariance).
- Winners: IG 3.9 bits, track share about 0, move cost -0.44.
- The IG ranks with the number of guessed objects within 3 m (rho 0.34), not with distance from walked ground (rho 0.04).
- Winners lie 1.4 m from the walked path vs 2.1 m for a typical candidate.
- In the final 4 m view, 52/60/62/44% (official/placebo/filter/oracle) of visible guessed objects already lie within 3 m of walked ground [V: chosen_view.py].
- 98-100% of LLM and placebo guessed objects come from a single member.

Reading [I]: H1 holds. H2 is half right: guesses dominate the score, but as a disagreement-density field that any spread-matched guesses reproduce. The placebo was calibrated to the LLM's counts and distances, so E1 tests only fine content, and fine content enters the stop as noise. H3 holds.

## is_viewpoint_choice_random

Random with respect to guess content: yes, effectively [I, from verified replay numbers].
- At the decision level, the stop depends on which guesses exist, not on whether they are right. Replacing LLM content with a placebo draw moves the top candidate a median 2.1-2.6 m; two placebo draws differ by 2.2-2.3 m; same top-1 in 7-8% vs 9% of stages [V].
- Three noise sources of the same size sit on top, about 2 m on a roughly 3 m step [V]:
  - the second-stage re-rank (first-stage best chosen in 18% of stages, flat rank histogram);
  - seeded tie-breaks (16% of stages);
  - mapper timing (same-seed runs of one arm split at stop 0 in 93% of pairs, median 1.9 m).
- At 2 scenes x 3 seeds, per-run AUC varies 0.01-0.03 within an arm [V: CONTEXT sec 2], so no F1 test can see content.

Not random with respect to guesses existing [V]: with no guesses, the top-1 changes in 92% of stages and half the candidates score zero.

Not frontier-like [I]:
- The IG has no grid or unknown-space input [V].
- It barely ranks by novelty (rho 0.04 with distance from walked ground).
- Winners lie closer to walked ground than the average candidate (1.4 vs 2.1 m).
- 44-62% of guesses in the final view are in scanned ground.
- The only frontier-like pull: placebo and LLM rooms sit 1.5-3.5 m beyond mapped rooms, so the guess part leans slightly to new ground (rho 0.21) [V: placebo_calibration.json].

Best description: a short, move-cost-limited hop to a nearby spot dense with disputed guesses, then a 360-degree scan. The frontier explorer's 0.172/0.119 falls inside the arms' spread [V: CONTEXT], which fits the reading that scans along any reasonable walk do most of the mapping [I].

## what_asp_contributes

What ASP's semantic prediction contributes to decisions [I, from verified numbers]:
(a) A pull that keeps the robot moving to nearby new spots with many disputed guesses. Without guesses, 48% of candidates score zero and the guess-free track-disagreement term (graph0 vs graph1) picks winners near already-mapped duplicate objects.
(b) A wider sampling box.
(c) No reliable use of correctness. The IG:
- reads only labels in view [V: :510];
- ignores position error inside the view;
- gives zero value to a guess all members share, even a true one;
- gives full value to a guess in scanned free space. The LLM's collision tool checks only listed nodes [V: llm_completion.py:24-83], and the placebo has no check.
So LLM content can help only by shifting where guesses are dense. The placebo was built to match that spread, and the replay shows the remaining content moves stops no more than random redraws [V].

E3: why exact objects pull only slightly, and why drawn objects are not mapped more. I rebuilt the drawn-vs-undrawn contrast using the pool of true objects drawn in any e3 run; oracle_sets.json is not local. It reproduces the gates' approach gaps: 0.026-0.044 vs 0.027-0.050 [V: e3_mech.py].
- Drawn objects are 26-41% of the eligible set, with a median of 9-21 undrawn eligible neighbours within 3.5 m. Any stop near a drawn object also 'approaches' many undrawn ones [V].
- Approach-gap ceilings per stage and track [V: e3_ceiling.py]:
  - standing on a random drawn object: 0.015-0.058;
  - standing where the most drawn objects lie within 3.5 m (a rule that follows only the guesses): 0.10-0.15;
  - best possible spot (uses undrawn labels too): 0.18-0.22;
  - live ASP: 0.005-0.030 per unit, 0.026-0.044 pooled.
- So the planner captures roughly a tenth to a third of what a guess-following rule could show [I]. Causes: the IG rewards disagreement, and 11-22% of drawn objects were drawn by 2+ members, which damps their pull [V]; the move cost caps reach; the second stage re-ranks the top 10 almost at random; mapper noise moves the stop [V/I].

Mapping: every stop scans 360 degrees, so drawn and undrawn neighbours are scanned alike. P(mapped at k+1 | approached) is only 5.4-13.6% [V: gates]. The expected mapping gap is about 0.03 x (0.05-0.14), roughly 0.002-0.006, too small for ~900 drawn rows in 12-17 clustered stages to detect [I]. The observed -0.011 to +0.004 fit. The 00853 'broken' verdicts do not show a broken loop: the live gap is comparable to standing on a random drawn object. The 00871 'detector-limited' verdict misses that planning is also a large limit [I].

## author_missed

- **item**: No content control. Nothing separates informed guesses from same-shape random guesses or from no guesses, so the paper credits 'LLM semantics' for gains its own objective cannot attribute to content. | **evidence**: ASP v2 sec IV: the baselines are frontier and SSMI; the only ablation is a qualitative node-type study on one scene (also in v1). Replay: placebo vs LLM moves the top-1 as much as placebo vs placebo (2.1-2.6 vs 2.2-2.3 m). | **label**: verified
- **item**: No repeated runs or seeds. Here, same-seed runs of one arm split at the first stop because the first map differs, so single runs per scene cannot carry a method claim. | **evidence**: No seeds or trials in the v1/v2 text; Fig. 3 averages four scenes (inferred: single runs). paths_pairs.json: 93% of same-arm same-seed pairs split at stage 0 (median 1.9 m). Stage-0 graphs differ, e.g. 11 vs 5 objects in 00871 s42 placebo vs its ABORTED attempt. | **label**: inferred
- **item**: The objective rewards ensemble disagreement, not expected discovery. A guess every member shares scores zero even if true; a guess in already-observed free space scores in full; there is no unknown-space or coverage term. | **evidence**: calculate_uncertainty.py:501-522, :510 (labels only), :377-424 (no grid input). LLM collision tool checks listed nodes only (llm_completion.py:24-83). Final views: 44-62% of visible guessed objects lie within 3 m of walked ground (chosen_view.json). | **label**: verified
- **item**: The reachability re-rank silently changes the objective. It drops the move cost and widens the camera to 4 m, so the final pick is close to a random member of the top 10. | **evidence**: calculate_uncertainty.py:563-612 (no move cost, range 4.0, near 0.1); exploration_pipeline.py:779-833. Paper sec III-C describes re-ranking but not this. Live: first-stage best chosen in 18% of stages; official rank histogram [13,16,11,16,8,15,11,7,10,14]. | **label**: verified
- **item**: The two 'bootstrapped' tracks add a guess-free IG term that points at disputed observed objects. One track can vanish on a 10 s file timeout, with the other renamed graph0. | **evidence**: Paper v2 sec IV ('two scene graphs on bootstrapped subsets'); calculate_uncertainty.py:311 (shared noise seeds); obs-only replay IG mean 0.45 bits, nonzero for about half the candidates; e1_00853_s42_official log line 42 and stages/0 (4 files from graph1). | **label**: verified
- **item**: Mapper-made ground truth. The reference comes from manually driving the same mapper, so it measures what this detector can see and favours runs whose maps resemble it. | **evidence**: ASP v2 sec IV-A; CONTEXT sec 1-2: the frontier-made reference inflates AUC 1.9-4.5x. | **label**: verified
- **item**: The perception ceiling is never measured. Most true objects near a stop are not mapped at the next stage, which caps map gain no matter how good the stop is. | **evidence**: gates/*.json base rate: P(mapped at k+1 | within 3.5 m) = 5.4-13.6%. | **label**: verified
- **item**: The room-level graph plan is computed but never used for motion. | **evidence**: mid_planning.py:122 reads only high_level_path[-1]; find_mid_planner_target (:408) has no caller; graph_planning.py:134-184. | **label**: verified

## critical_gaps

- **gap**: No link between being right and being chosen. ASP scores a view by how much the sampled completions disagree about the labels in view, so correct, wrong and random guesses with the same spread make the same kind of field. Prediction quality, which the paper credits and the validity layer tried to improve, has no path to F1 through this planner. | **why_it_matters**: This explains E1 and E2 (content and filtering cannot move stops beyond noise) and the weak E3 pull (live gap 0.005-0.03 per unit vs 0.10-0.15 for a rule that just goes where most drawn objects are). Better LLMs or better filters will not help until the decision rule values correct, not-yet-seen content. | **evidence**: Replay on 394 stages: swapping content moves the top-1 2.1-2.6 m vs 2.2-2.3 m between two placebo draws; rho(IG, novelty) 0.04; 44-62% of guesses in final views lie in scanned ground. E3 ceilings: e3_ceiling.json. | **label**: inferred | **prior_work**: MapEx (arXiv 2409.15590) scores views by predicted-map variance inside the visible unknown area, and its 'Observed Map' ablation (no predictions) is 'competitive'. MAPLE (arXiv 2610.28566, Oct 2026) finds 'more accurate map prediction does not necessarily produce better exploration' and evaluates one-step decision regret. UPEN (2202.11907) and L2M (2106.15648) tie ensemble disagreement to unseen map area. LGR (2503.20241), VLFM and ESC let language models rank geometric frontiers, so geometry supplies novelty. 3D Scene Graph Prediction (2607.10879) reports that LLMs struggle with precise geometry.
- **gap**: No decision-level test and no replicates. The F1-AUC endpoint sits at the end of a noisy chain (guesses, stop, scan, detector, map). Seeds do not pair runs, because the mapper output differs from the first scan. | **why_it_matters**: At 2 scenes x 3 seeds, content effects smaller than replicate noise (about 2 m per stop, 0.01-0.03 AUC per run) are invisible. Results need a fixed-state decision test first, and paired or replicated live runs second. | **evidence**: paths_pairs.json: 93% of same-arm same-seed pairs split at stage 0; arms overlap no more within an arm than between arms (Jaccard 0.61-0.65 at 30 m). The replay reproduces 97% of logged top-10s, so offline decision tests are feasible. | **label**: verified | **prior_work**: MAPLE's controlled comparison on shared states with decision regret; Ramakrishnan et al., An Exploration of Embodied Visual Exploration (2001.02192), on benchmarking exploration paradigms; ASP follow-ups (2605.18197, 2605.18184) adopt ASP's IG and compare only to geometric baselines, with no content control in what I read.
- **gap**: Perception caps map gain. Most true objects near a stop are not added to the map at the next stage. | **why_it_matters**: Even a perfect stop rule faces this cap. The E3 mapping gap is about the approach gap times 0.05-0.14, which is undetectable at this n. | **evidence**: gates/*.json base rates 5.4-13.6%; mapping gaps -0.011 to +0.004. | **label**: verified | **prior_work**: Gervet et al., Navigating to Objects in the Real World (2212.00922), on how much modular semantic pipelines depend on perception; Clio/Hydra mapping limits as used by ASP (paper sec III-B).

## key_papers

- **title**: Active Semantic Perception (Tang, Chaudhari) | **id_or_url**: arXiv:2510.05430 (v2 11 Jun 2026; v1 6 Oct 2025) | **year**: 2025/2026 | **relevance**: The method under test. Facts used: baselines are frontier and SSMI; two graphs from bootstrapped observation subsets; 300 candidates; mapper-made reference; Gemini 2.5 Pro at $1.28 per step; no content control or seeds. | **read_in_full**: True
- **title**: MapEx: Indoor Structure Exploration with Probabilistic Information Gain from Global Map Predictions | **id_or_url**: arXiv:2409.15590 | **year**: 2024/2025 | **relevance**: IG = predicted-map variance x visible unknown area; its 'Observed Map' (no prediction) ablation is competitive. Direct prior evidence that how predictions enter the IG matters more than having them. | **read_in_full**: False
- **title**: MAPLE: Mondrian-Anchored Prior for Learning-free Indoor Exploration | **id_or_url**: arXiv:2610.28566 | **year**: 2026 | **relevance**: Newest work: more accurate prediction does not imply better exploration; per-hypothesis visibility; one-step decision regret on shared states, the model for the proposed offline bench. | **read_in_full**: False
- **title**: Uncertainty-driven Planner for Exploration and Navigation (UPEN) | **id_or_url**: arXiv:2202.11907 | **year**: 2022 | **relevance**: Ensemble disagreement over predicted occupancy, tied to unseen area, as the exploration signal. | **read_in_full**: False
- **title**: Learning to Map for Active Semantic Goal Navigation (L2M) | **id_or_url**: arXiv:2106.15648 | **year**: 2021/2022 | **relevance**: Semantic map prediction beyond the field of view, with ensemble uncertainty for goal choice. | **read_in_full**: False
- **title**: Occupancy Anticipation for Efficient Exploration and Navigation | **id_or_url**: arXiv:2008.09285 | **year**: 2020 | **relevance**: Predicting unseen occupancy to speed exploration; early predicted-map baseline. | **read_in_full**: False
- **title**: An Exploration of Embodied Visual Exploration | **id_or_url**: arXiv:2001.02192 | **year**: 2020/2021 | **relevance**: Benchmark of exploration paradigms with frontier baselines and evaluation design. | **read_in_full**: False
- **title**: Navigating to Objects in the Real World | **id_or_url**: arXiv:2212.00922 | **year**: 2022/2023 | **relevance**: Large empirical study; modular semantic pipelines and their perception limits. | **read_in_full**: False
- **title**: LGR: LLM-Guided Ranking of Frontiers for Object Goal Navigation | **id_or_url**: arXiv:2503.20241 | **year**: 2025 | **relevance**: LLM ranks geometric frontiers, the common alternative to scoring free-floating LLM guesses. | **read_in_full**: False
- **title**: 3D Scene Graph Prediction: Generating Hierarchical Models from Partially Observed Environments | **id_or_url**: arXiv:2607.10879 | **year**: 2026 | **relevance**: Diffusion-based scene-graph completion compared with LLM floor-plan generation; notes LLM geometry limits. | **read_in_full**: False
- **title**: Imaginative World Modeling with Scene Graphs for Embodied Agent Navigation (SGImagineNav) | **id_or_url**: arXiv:2508.06990 | **year**: 2025/2026 | **relevance**: VLM-predicted scene-graph completion used for navigation; part of the LLM-imagination line ASP belongs to. | **read_in_full**: False
- **title**: RGB-only Active 3D Scene Graph Generation for Indoor Mobile Robots | **id_or_url**: arXiv:2605.18197 | **year**: 2026 | **relevance**: Follow-up that adopts ASP's IG; claims more than 2x objects vs a geometric baseline, with no content control in what I read. | **read_in_full**: False
- **title**: Fixed External Cameras as Common Prior Maps for Active 3D Scene Graph Generation | **id_or_url**: arXiv:2605.18184 | **year**: 2026 | **relevance**: Second ASP-based follow-up (graph-based semantic exploration). | **read_in_full**: False
- **title**: VLFM: Vision-Language Frontier Maps for Zero-Shot Semantic Navigation | **id_or_url**: https://openreview.net/pdf?id=gdw1zUTABk | **year**: 2024 | **relevance**: Language-model value used to score geometric frontiers (search snippet only). | **read_in_full**: False
- **title**: ESC: Exploration with Soft Commonsense Constraints for Zero-shot Object Navigation | **id_or_url**: https://proceedings.mlr.press/v202/zhou23r/zhou23r.pdf | **year**: 2023 | **relevance**: LLM commonsense used over frontiers (search snippet only). | **read_in_full**: False

## next_plan

- **step**: A0 (tonight, after about 20:30 IST) | **what**: Let tonight's last run finish. Queue no new live runs of this design. | **why**: The replay shows content moves stops no more than random redraws, and replicate noise is about 2 m per stop. More runs at affordable n cannot separate content from noise. | **cost**: $0; 0 extra host-h | **time**: none | **decision_rule**: None. This is the stop decision: stop live experiments of the current loop.
- **step**: A1 (by 10-31 20:00) | **what**: Add the decision-level replay to the package: 97% top-10 reproduction; the swap table (no guesses / placebo / oracle-pool vs the placebo-placebo floor); flat rank histogram; score variance shares. Source: /tmp/cvp_review/work_A. | **why**: Explains the E1/E2 nulls by mechanism, not just by p-values. | **cost**: $0; laptop about 1 h | **time**: 2 h | **decision_rule**: If the official-arm LLM-vs-placebo top-1 distance has a stage-bootstrap 95% CI entirely below the placebo-placebo floor, report 'decision is content-sensitive'. Otherwise report 'content enters stops as noise'.
- **step**: A2 (by 10-31 20:00) | **what**: View-value test against the HM3D reference. For all 394 saved stages, count unmapped reference objects visible (same 3-4 m camera, observed structure as occluders) from: the live stop, the first-stage best, each counterfactual top-1, and all 300 candidates. Needs oracle_sets.json or the reference yaml copied by the main session. This is not F1/AUC. | **why**: Asks directly whether ASP looks at more new true objects than a random candidate does. | **cost**: $0; laptop 2-3 h CPU | **time**: 4 h | **decision_rule**: If the live stop is at or below the candidate median (stage-blocked permutation p >= 0.05), headline 'viewpoint choice does not target unseen objects'. If it is above, say some content survives and perception is the main cap.
- **step**: A3 (by 10-31 20:00) | **what**: Add the E3 ceiling table (random drawn object / max drawn count / best spot / live) beside the gate, labelled post hoc. | **why**: The 00853 'broken' and 00871 'detector-limited' verdicts misread a low-ceiling contrast: live gaps match a robot standing on one drawn object. | **cost**: $0 | **time**: 1 h | **decision_rule**: Report the live gap as a share of the max-drawn-count ceiling (about 0.1-0.3). Do not call the loop broken unless that share is near 0 with a CI.
- **step**: A4-A5 (by 10-31 20:00) | **what**: Add a note that same-seed replicates split at stage 0 (map differences listed). Write E1/E2 as nulls with intervals, plus the mechanism, plus what is not ruled out. | **why**: Seeds do not pair runs; readers need to know that. | **cost**: $0 | **time**: rest of the window | **decision_rule**: None.
- **step**: B1 (next 2-3 weeks) | **what**: MAPLE-style regret bench on the 394 stages, with reference-visible new objects as the utility. Rules: ASP IG; ASP IG with guesses in scanned or known-free ground masked out; expected discovery (member-support-weighted guessed objects in view outside scanned ground); novelty only; random. Hypothesis sets: oracle, LLM, placebo, none. | **why**: Finds a rule that turns correct content into better stops before spending host time. | **cost**: $0; laptop | **time**: 3-5 days | **decision_rule**: Go live only if, under some rule, oracle beats placebo on regret by at least 30% and LLM beats placebo outside the placebo-placebo noise. Otherwise write up the audit and stop.
- **step**: B2 (next 2-3 weeks) | **what**: Make the stage map deterministic: snapshot on a frame count or Hydra idle flag instead of file-size stability. Test with 3 same-seed placebo replicates. | **why**: Paired designs need same-seed runs to match. | **cost**: $0; about 12 host-h | **time**: 2 days | **decision_rule**: If stage-0 graphs match and stops agree within 0.25 m, pair runs by seed. If not, plan at least 5 replicates per cell.
- **step**: B3 (next 2-3 weeks) | **what**: Live test of the B1 winner with $0 arms: oracle vs placebo, 2 scenes x 4 seeds = 16 runs. Add an observed_only arm only if B1 shows the no-guess rule differs from placebo. | **why**: First live test whose oracle arm can actually pull the robot. | **cost**: $0; about 64 host-h (about 1 day at 3 concurrent) | **time**: 3-4 days | **decision_rule**: If oracle - placebo AUC > 0 (scene-blocked permutation p < 0.05, 50 m and 60 m agree), add a 16-run DeepSeek arm (about $16 of $25 at $0.75-1.29 per run). Otherwise stop live work.
- **step**: C (what a publishable study would need) | **what**: At least 8-10 human-annotated scenes x 3-5 seeds, on a deterministic or replicated mapper. Arms: frontier on the same detector, ASP as published, ASP with the B1 rule, matched placebo, no guesses, oracle. HM3D annotation reference; pre-registered 50/60 m tests; replay and regret as mechanism. | **why**: Current variance (0.01-0.03 AUC within an arm; MDE about 0.024 at 5 pairs) needs many more scenes. | **cost**: $0 arms: about 600 host-h (5 arms x 30 runs x 4 h, 8-9 days at 3 concurrent). A DeepSeek arm of about $30 exceeds the $25 left. The paper's Gemini 2.5 Pro is about $35 per run (paper sec IV), far out of budget. | **time**: 4-6 weeks | **decision_rule**: Within budget, publish a placebo-controlled audit of the objective (with $0 arms and existing LLM runs). Claim LLM-content effects only if funded.

## disagreements_with_context

- H2 is half wrong. The score is not dominated by guess-independent terms: the guess-dependent part carries about 70% of score variance across candidates (R^2 0.52), and removing guesses changes the top-1 in 92% of stages. What holds is that the guess term is not content-specific: it is a disagreement-density field that any spread-matched guesses reproduce. It is also not a pull toward unexplored space: rho with novelty 0.04, and 44-62% of guesses in the final view lie in scanned ground.
- H4 as worded ('capped by perception, not planning') is incomplete. The planner captures only about a tenth to a third of the approach gap that a rule following only the drawn objects could show (live 0.005-0.03 per unit vs 0.10-0.15). Perception (5-14% mapped when approached) is a second cap, not the only one.
- H5 is partly wrong. The ASP paper does run a frontier baseline, plus SSMI (v1 and v2 sec IV). What it lacks is a placebo or no-guess control, repeated runs, and a non-mapper reference.
- The E3 verdict labels mislead. The 00853 'broken' gaps (0.027-0.035) are about what a robot standing on a random drawn object would show (0.015-0.058). The drawn-vs-undrawn contrast has a low ceiling (best spot 0.18-0.22) because drawn and undrawn objects sit side by side.
- CONTEXT sec 1 step 3 omits two facts. The planner draws 3,000 candidates and keeps 300 near the first-listed file's objects. The final choice uses a different score (no move cost, 4 m camera) after reachability, and it picks the first-stage best in only 18% of stages.
- '4 members x 2 tracks = 8 files' does not always hold. A 10 s DSG timeout can drop a track, and the other graph is then renamed graph0 (e1_00853_s42_official stage 0 had 4 files from graph1).
- Seeds 42-44 do not make runs repeatable or paired. Same-seed runs of one arm split at stage 0 in 93% of pairs, because the first map differs.
- The user's summary needs one fix. The validation layer removing (almost) all guesses was the static unanimity filter (99.8%). The live E2 filter removed about a quarter. Both fail for the same reason: guesses reach F1 only through stops, and stops ignore correctness.

## open_questions

- Could not check: the counterfactual stops' reachability. The nvblox grid is not saved, so swaps were scored on the first stage and on an unconstrained second stage; only the live winners' second-stage IG was verified (393/393).
- Could not check: the exact E3 eligible sets (oracle_sets.json and the HM3D reference are not local). I used the pool of objects drawn in any e3 run, which omits never-drawn objects; approach gaps still matched the gates within about 0.01.
- Could not check: the cause of stage-0 map differences between same-seed runs. Snapshot timing is my inference; it needs host-side frame logs.
- 11 of 394 stages did not reproduce the logged top-10 (9 filter_only, 2 official), probably file order or in-place rewrites after retries. They are kept in the swap statistics.
- The e3 logs are truncated, so log values cover fewer e3 stages; pose logs cover all.
- Literature depth: ASP v2 was read in full; MapEx and MAPLE by section; the rest at abstract level; VLFM, ESC and SG-Nav from search snippets only. TinyFish was used via its CLI; the MCP tools were not exposed in this session.
- Does the live stop see more unmapped reference objects than a random candidate? (Plan step A2.)
- Is the 00871 pattern (official above placebo in 3/3 seeds) real, and by what mechanism? The path and decision data show no arm signature.
- Would the paper's LLM (Gemini 2.5 Pro) change the disagreement field enough to matter? The objective would still ignore correctness.
- Can Hydra/Clio be made deterministic enough to pair runs by seed?