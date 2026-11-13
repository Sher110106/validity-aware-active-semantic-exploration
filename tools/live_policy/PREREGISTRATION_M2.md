# Pre-registration: would right meaning be enough for ASP's score? (end-sem plan, milestone M2)

DRAFT, not yet hashed. Written 2026-11-13. It is frozen by its sha256 in `PREREGISTRATION_M2.sha256` before any new arm of §4 is run. Rebuilding the October bench and reproducing its old numbers is not a new arm.

It follows `docs/ENDSEM_PLAN_2026-11-03.md` §3 M2 as trimmed by `docs/ENDSEM_FINAL_PLAN_2026-11-13.md`. Where they differ from this file, this file wins.

## 1. Question

The ASP author's defense has a second half: guesses that are right in meaning but wrong in place are enough for ASP. M2 asks what ASP's own viewpoint score makes of guesses that are right by construction, once they are moved by the placement error real models make, or cut down to room types alone.

## 2. What had been seen

Nothing here is blind. M2 is a descriptive study with a reading rule set in advance.

- October, on official stages (`results_2026-10-31/WRITEUP.md`, the mechanism table): the score built from the oracle's guesses ranks the candidates with a median Spearman of 0.44 against U_360 and 0.71 against U_cone; from the placebo's, 0.19 and 0.23; from the LLM's own, 0.20 and 0.30; from no guesses, −0.07 and −0.03.
- The bench's regret ratios 0.933, 0.904, 0.853 and 0.850, and its decision go_live = false.
- U_wall failed the ratio reading of its October yardstick check, so the bench's numbers are provisional (`results_2026-10-31/DEVIATIONS.md`, item 39(e)).
- The F3 arm uses each model's placement error from M1, so M1's exploratory results on DeepSeek, and later the Claude results, are known when F3 runs.

## 3. The bench

The October offline bench (`PREREGISTRATION_BENCH.md`), rebuilt from a copy and checked to reproduce its registered output: 9,600 of 9,600 picks. Its code is not edited; the new arms live in new files.

- **Stages:** the bench's 384 stages (24 runs) whose replayed top-10 matches the log.
- **Held fixed per stage:** the robot's state and the 300 first-stage candidates. Only the members' guess files change.
- **Score:** the author's first-stage score for each candidate, as the bench's replay computes it.
- **Yardstick:** the bench's U_cone: the unmapped reference objects a candidate could see past the walls, inside the first-stage camera's frustum.

## 4. Arms

Each arm gives every stage a member set of the same shape as the run's own (4 members per track).

| Arm | Member sets |
|---|---|
| F1 | The bench's oracle set, as October built it: true unmapped reference objects at their true places, drawn per member as the E3 oracle drew them. |
| F5 | The bench's two placebo sets (two seeds). F5's value is their mean. |
| F6 | No guesses. |
| F3-m | F1 with every oracle object moved by a distance drawn from model m's error sample, in a direction uniform on the circle. Labels, sizes and rooms stay. No check rejects a moved object, as none checks an LLM's. |
| F-room | No true objects. For each region that is unseen at the stage (as `PREREGISTRATION_SEMANTIC.md` §5.4 defines it) and has a scored type, the member holds one room node of that type at the region's centroid, and n objects placed uniformly in the region's floor mask (its `any` mask if it has no floor). |

**Model m's error sample** comes from M1: for each new object of model m on the frame rows (raw view) that has a canonical class, the distance to the nearest unmapped reference object in an unseen region that answers to its class. An object with no such reference object in the scene is left out. F3 runs first for DeepSeek, and for Claude Opus and Haiku once their replays exist.

**F-room's objects.** For a region of type T, n is the mean number of detector-vocabulary reference objects per region of type T in the other scene, rounded. Their labels are drawn with replacement from those objects' detector labels; their sizes come from the placebo calibration's size table. A region with two types gets a room node for each. The room is named as the mapper names rooms ("an image of a bedroom") and linked as the placebo links its rooms.

**Seeds.** Every draw uses `np.random.default_rng([20261113, run index, stage, track, member, arm code])`.

## 5. Outcome

- Per stage and arm: the Spearman correlation between the score and U_cone over the stage's candidates.
- A stage where that correlation is undefined for any arm (a constant score or a constant yardstick) is left out for every arm, and counted.
- Per run: the mean over its stages. Summary: the mean over the 24 runs.
- Interval: a wild cluster bootstrap over runs (Rademacher weights, 9,999 draws, seed 20261113), 95%.

Reported beside it: the median per-stage correlation; the same against U_360, as October reported it; R1 regret under U_wall and U_cone; and every figure on the official-arm stages alone.

## 6. Reading rule

Let A = F1 − F5, B_m = F3-m − F5 and C = F-room − F5, each a per-run difference averaged over runs.

1. If the interval of A does not lie wholly above 0, the ceiling does not separate from the floor on this yardstick, and M2 is not read further.
2. Otherwise, for X in B_m and C: right meaning is **sufficient** if the interval of X − 0.5 × A lies wholly above 0; **not shown sufficient** if it lies wholly below 0; **inconclusive** otherwise.

A "not shown sufficient" verdict is worded "not shown sufficient, on a yardstick biased toward rejection".

## 7. Bias and limits, registered

- F1's objects are the very objects the yardstick counts, so F1 is inflated and the rule leans toward "not shown sufficient".
- U_wall failed part of its October check, and the rendered yardstick that would test it (M6) is cut. Every M2 verdict is provisional.
- The all-true anchor, in which every member holds the full truth and ASP's score gives unexplored space zero, is an identity of the score. It is shown as such, not as a finding.
- Two houses.

## 8. Not done

The plan's F2 (true labels at a random point in the true region) and F4 (placebo labels at true places); the 25%, 50% and 100% subset sizes; the 0 to 4 m error sweep; the decision replay with Claude's members (H5).
