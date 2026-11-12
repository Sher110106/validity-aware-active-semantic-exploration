# Pre-registration: offline decision bench (plan step 6)

Written 2026-10-29 22:35 IST, before any bench result exists. This is step 6 of docs/checkin/review_2026-10-29/SYNTHESIS_AND_NEXT_PLAN.md §6 (A's B1), with the §9 update: fix the yardstick's walls first.

## States
Every saved stage of the 24 scored runs used in the objective audit whose replayed first-stage top-10 matches the log (384 stages). Each state is the observed map and the robot pose at stage k. Candidates are the same 300 first-stage candidates the audit regenerated with reviewer A's replay of the author's scorer.

## Yardstick (utility)
U_wall(c) is the number of not-yet-mapped reference objects visible from candidate position c over a full 360° turn, within 0.1-4.0 m.
- **Objects:** the objects in oracle_sets.json. "Not yet mapped" uses the live_policy.oracle_eligible rule without its reach test, the same rule as the audit.
- **Visibility:** an object counts if the 2D segment from c to its centre crosses no occupied cell of the HM3D wall map. The map is a horizontal slice of the scene mesh at z = 0.6, 1.1 and 1.6 m in the pipeline frame, on a 0.05 m grid (hm3d_refs_work/<scene>_walls.npz, slice_walls.py). The last 0.15 m before the object is ignored, so an object against a wall still counts.
- **Secondary yardstick:** U_wall_cone, the same count within the first-stage camera cone at the candidate's yaw.

**Yardstick check, before any rule is compared.** Compare U_wall with the audit's U_360 (no walls) on how well each predicts the next map. For the robot's real stop, take the share of counted objects that appear in stage k+1's map (same label within 0.5 m), set against the share for objects outside the count. If U_wall does not separate them at least as well as U_360, report that, and treat bench results as provisional.

## Rules
Every rule picks one of the 300 candidates. All rules except random subtract the author's move cost (0.2 × distance from the robot), as ASP's first stage does. A rule may use only what the robot knows: the observed map, its walked path and the guess files. Occlusion inside a rule uses the observed structure nodes, as ASP's scorer does.
- **R1 ASP:** I_obj + I_room − 0.2·d (the author's first-stage score).
- **R2 ASP-masked:** R1 after removing guessed objects that lie within 3 m (xy) of the path walked before stage k.
- **R3 ASP+novelty:** R1 + 0.5·min(n, 4), where n is the distance in metres from the candidate to the nearest walked-path point.
- **R4 expected discovery:** the sum, over guessed objects in the candidate's full-turn view (0.1-4.0 m, observed occluders) that lie more than 3 m from walked ground, of each object's member support: the share of members in its track with a same-label guess within 1 m. Then −0.2·d.
- **R5 novelty only:** min(n, 4) − 0.2·d.
- **R6 random:** a uniform pick; the mean over 50 draws per stage.

R5 and R6 use no guesses.

## Guess sets
Per stage:
- **actual:** the arm's own files;
- **none:** observed map only;
- **placebo A and placebo B:** two independent draws from live_policy.placebo_graph; their difference is the noise floor;
- **oracle:** a draw from live_policy.oracle_graph, as the live oracle arm draws.

"LLM" means actual on official stages. Official stages are the only ones with unfiltered LLM files; filter_only stages are reported separately.

## Outcome
- **Regret** of a pick: max over candidates of U_wall − U_wall(pick).
- **Normalised regret:** regret / max U_wall, for stages with max U_wall > 0.
- **Summary:** mean regret per rule and guess set, with a stage-bootstrap 95% CI (resample stages within run, 2,000 draws, seed 0).

## Decision rule (the plan's, fixed now)
Go live (plan steps 9-10) only if some rule R1-R4 meets both conditions:
- (a) oracle regret is at most 0.7 × placebo-A regret on the same stages, with the bootstrap CI of the ratio wholly below 1;
- (b) on official stages, LLM regret is below placebo-A regret, with the CI of (LLM − placebo-A) lying wholly below the placebo noise floor. The floor is the 2.5th percentile of the bootstrap of (placebo-B − placebo-A).

If no rule meets both, write up the bench and stop live work. Steps 9 and 10 are then not run, and the plan's own rule makes that its completion.

Also reported, with no decision attached:
- R5 against R1, and whether any guess-based rule beats R5;
- the same tables under U_wall_cone;
- normalised regret.
