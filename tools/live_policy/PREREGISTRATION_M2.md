# Pre-registration: would right meaning be enough for ASP's score? (end-sem plan, milestone M2)

Written 2026-11-13. This file is frozen by its sha256 in `PREREGISTRATION_M2.sha256` before any arm of §4 is scored on a real stage. Rebuilding the October bench and reproducing its old output is not such a scoring.

It follows `docs/ENDSEM_PLAN_2026-11-03.md` §3 M2 as trimmed by `docs/ENDSEM_FINAL_PLAN_2026-11-13.md`. Where they differ from this file, this file wins. §8 lists what the plan asked for and this file does not do.

## 1. Question

The ASP author's defense has a second half: guesses that are right in meaning but wrong in place are enough for ASP. M2 asks what ASP's own viewpoint score makes of guesses that are right by construction, once they are moved by the placement error real models make, or cut down to what a room type tells.

## 2. What had been seen

Nothing here is blind. M2 is a descriptive study with a reading rule set in advance.

- October's mechanism table (`results_2026-10-31/WRITEUP.md`), on the 119 official stages: the median per-stage Spearman of the score against U_360 (and, in brackets, the audit's U_cone) is 0.44 (0.71) with the oracle's guesses, 0.19 (0.23) with the placebo's, 0.20 (0.30) with the LLM's own, −0.07 (−0.03) with none, and 0.50 (0.31) for a rule that uses no guesses. On matched states the oracle gains +0.31 over the placebo and the LLM +0.07. **These are not on M2's yardstick:** they come from `audit/counterfactual.py`, with its own seeds and a U_cone that has no wall test.
- The bench's regret tables per guess set and rule, its regret ratios 0.933, 0.904, 0.853 and 0.850, and its decision go_live = false. They already hold R1 regret for F1, F5 and F6.
- How far the top candidate moves when the guesses change (+0.68 m, +0.10 m, +0.09 m); member agreement within 1 m of 42.2% (oracle), 29.4% (LLM) and 4.4% (placebo); later-found rates up to 17.4%.
- DeepSeek's precision at 0.5, 1 and 2 m (3.0%, 10.1%, 23.8%), a coarse view of the error F3 uses.
- E3's live result: exact objects against the placebo +0.034, against the LLM +0.003.
- U_wall failed the ratio reading of its October yardstick check, so the bench's numbers are provisional (`results_2026-10-31/DEVIATIONS.md`, item 39(e)).
- F3 uses each model's placement error from M1, so M1's exploratory results on DeepSeek, and later the Claude results, are known when F3 runs.

## 3. The bench

The October offline bench (`PREREGISTRATION_BENCH.md`), rebuilt from a copy and checked to reproduce its registered output: 9,600 of 9,600 picks. Its code is not edited; it is imported, and the new arms live in new files.

- **Stages:** the bench's 384 stages (24 runs) whose replayed top-10 matches the log. The 24 runs include runs that E1-E3 excluded from their own tests (a placebo run that ended at 0 m, and archived oracle attempts on 00853); they are valid as robot states.
- **Held fixed per stage:** the robot's state and the 300 first-stage candidates. Only the members' guess files change.
- **Members:** each arm builds one graph for each member id that `rp2.gids_for(run, k)` gives for the stage (2 to 8 ids), from the observed graph of that id's track (id // 4).
- **Score:** `ig − 0.2·d`, the author's first-stage pick rule: `ig` sums the two columns that `fastig.Scorer(files, seed).score(kept, CameraConfig())` returns, and `d` is the 3-D distance from the current pose (as `bench.py` computes R1). `ig` alone is reported beside it.
- **Yardstick:** U_wall_cone, the bench's `Ucone`: the unmapped reference objects a candidate could see past the walls, inside the first-stage camera's cone. The audit's U_cone (no wall test) and U_360 are reported beside it.

## 4. Arms

| Arm | Member graphs |
|---|---|
| F1 | The bench's oracle graphs, as October built them: true unmapped reference objects at their true places, a subset drawn per member as the E3 oracle drew it. |
| F5 | The bench's two placebo sets. |
| F6 | No guesses. |
| F0 | The all-true anchor: every member of a track holds every unmapped reference object of `oracle_sets.json` at its true place, with the rooms of the track's first F1 graph. |
| F3-m | The F1 graphs with every oracle object moved by model m's placement error. |
| F-room | What the room types tell: no true objects, only objects typical of each unseen region's type, placed in that region. |

**Seeds.** F1, F5 and F6 are the bench's own graphs, with its keys `[20261029, run_idx, k, g, s]` (s = 3 for the oracle, 1 and 2 for the placebos). Every new draw uses `np.random.default_rng([20261113, run_idx, k, g, c])`, with c = 11 for F-room and 21, 22, 23 for F3 with DeepSeek, Haiku and Opus.

**F3-m.**
- The error sample of model m: for each new object of model m on the frame rows of `PREREGISTRATION_SEMANTIC.md` (its §7, raw view) whose class is neither "other" nor structure, the distance to the nearest unmapped reference object that answers to its class and lies in an unseen region (its §5). A guess with no such object in the scene is left out. Distances are pooled over all of the model's rows and members.
- Each member's copy of each oracle object takes its own draw: a distance drawn with replacement from the sample, a direction uniform on the circle. The move is horizontal; the object's height, id, label, size and room edge stay. No check rejects a moved object, as none checks an LLM's.
- A member whose oracle graph fell back to placebo objects is not moved, and is counted.
- The error is measured on the semantic truth, while the moved objects are those of `oracle_sets.json`; the report says so.
- F3 runs first for DeepSeek, and for Claude Haiku and Opus once their replays exist. No correction is made for running it for three models.

**F-room.** For each member, on its own track's observed graph:
- The unseen regions are those of `PREREGISTRATION_SEMANTIC.md` §5.4 at that stage, judged on that track; the types are its five scored types (no dining).
- The member's object count N is the count its F1 graph holds, so the two arms spend the same number of guesses.
- The N objects are shared among the unseen typed regions in proportion to n_T, by one multinomial draw. For a type T, n_T is the mean number of detector-vocabulary reference objects per region of type T in the other scene; an object's label is drawn with replacement from the detector labels of those objects; its size comes from the placebo calibration's size table; its place is uniform over the region's floor mask (its `any` mask if it has no floor); its height follows `placebo_graph`. If the other scene has no region of type T, n and the labels come from all its typed regions pooled. A region with two types counts once for each.
- One room node per unseen typed region and type, with ids running from the largest observed id plus 1, in order of region id and then type, the same in every member of a track. Each object has one edge, to its region's first room node. The scorer never reads a room's name; a room type reaches the score only through the labels and links of its objects.
- Where a member has no unseen typed region, its F-room graph equals its F6 graph. Such stages stay in, and are counted.

The number of objects per member is reported for every arm.

## 5. Outcome

- Per stage and arm: the Spearman correlation (the audit's `rho`) between the score and the yardstick over the stage's candidates. F5's per-stage value is the mean of its two sets' correlations.
- A stage where the correlation is undefined for F1, either F5 set, F6, F-room or F3-DeepSeek (a constant score or a constant yardstick) is left out for every arm, and counted. The list of left-out stages is fixed on that first pass and reused when the Claude F3 arms run.
- Per run: the mean over its stages of the per-stage difference between two arms. Summary: the mean over the 24 runs, each run weighing the same.
- Interval: a wild cluster bootstrap over runs. With D_r the run's mean difference and D̄ their mean, each draw is the mean over runs of D̄ + w_r (D_r − D̄), with Rademacher weights w_r; 9,999 draws, seed 20261113; the 2.5th and 97.5th percentiles. The interval speaks of runs within these two houses, not of houses.

Reported beside it: the median per-stage correlation; the same with `ig` alone, with the audit's U_cone and with U_360; R1 regret under U_wall and U_wall_cone; every figure on the official-arm stages alone; and the summary with runs clustered by scene and seed.

## 6. Reading rule

Let A = F1 − F5, B_m = F3-m − F5 and C = F-room − F5.

1. If the interval of A does not lie wholly above 0, the ceiling does not separate from the floor on this yardstick, and M2 is not read further.
2. Otherwise, for X in B_m and C: right meaning is **sufficient** if the interval of X − 0.5 × A lies wholly above 0; **not shown sufficient** if it lies wholly below 0; **inconclusive** otherwise.

The half is a convention taken from the plan. A "not shown sufficient" verdict is worded "not shown sufficient, on a provisional yardstick".

## 7. Bias and limits, registered

- **Toward "not shown sufficient":** F1's objects are the very objects the yardstick counts, so F1 is inflated.
- **Toward "sufficient":** F3 keeps the true labels; the error sample leaves out guesses with no unseen object of their class; and the distance to the nearest object of a class is a minimum, so common classes get short distances.
- The net direction is unknown.
- U_wall failed part of its October check, and the rendered yardstick that would test it (M6) is cut. Every M2 verdict is provisional.
- **The all-true anchor, F0.** Within one track, members that hold the same guesses give `ig` = 0, because `ig` measures disagreement between members; the score is then −0.2·d. On a stage with two tracks the observed graphs differ, so `ig` need not be 0. F0 is run and reported as it comes out, with the share of stages where `ig` is 0 for every candidate. It is a property of the score, shown as such.
- Two houses.

## 8. Not done

- The plan's F2 (true labels at a random point in the true region) and F4 (placebo labels at true places), and with F4 the "labels alone" contrast F1 − F4.
- The 25%, 50% and 100% subset sizes, and the 0 to 4 m error sweep with its figure of ranking power kept against error.
- An error on labels, and an F-room variant that swaps regions.
- The count of true unseen objects at the top pick.
- F3's error applied to rooms: F1's rooms are placebo rooms, so there is no true room to move.
- The decision replay with Claude's members (H5).
