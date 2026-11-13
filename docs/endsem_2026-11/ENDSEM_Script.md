# Speaker script: end-sem (20 slides and one backup, about 14 minutes)

About 1,750 words for the 20 slides. *Italics* in parentheses are stage directions; the builder drops them from the notes. `[TBD ...]` marks a number that part 3 has not produced yet: fill it in from `slots.json`, then read the sentence as written. `SOURCES.md` gives the file behind each number. Version 2: part 3 slides carry grey "result pending" marks until `slots.json` is filled.

---

## Slide 1: Right in meaning, wrong in place? (about 30 s)

ASP asks a language model to guess the rooms and objects the robot has not seen. Its author says the guesses are often in the wrong place but name the right things, and that this is enough. Is that so?

Part 1 is the live test. Part 2 puts our numbers on the paper's scale. Part 3 tests his defense. Parts 1 and 2 are final, except the 871 numbers, which are being rerun.

---

## Slide 2: ASP scores views by disagreement, not by truth (about 50 s)

The robot holds a map of what it has seen. The model guesses what lies beyond: eight guessed graphs, each with the same mapped part and its own extra rooms and objects.

*(Point to the middle panel.)*

For each candidate view, ASP asks what a camera there would see in each graph, and how far the eight graphs differ. A cost of 0.2 per metre is taken off.

*(Point to the three columns.)*

The score has no term for truth, and none for unexplored space. If all eight graphs agree, the gain is zero. A guess earns score by differing from the others, not by being right.

---

## Slide 3: Live test: no detectable difference (about 55 s)

Part 1. Live runs in two homes, seeds 42 to 44, scored against human labels. Each line is a difference in map quality, with its 95% interval.

*(Point to the rows, top to bottom.)*

LLM guesses against random guesses: plus 0.013, from minus 0.012 to plus 0.040. Our filter against the LLM: minus 0.003. The LLM against plain frontier: minus 0.012. Random guesses against frontier: minus 0.025. Exact objects against random guesses: plus 0.034.

All five read the same way: no detectable difference. Two cautions. Exact objects stand on one house, under a deviation, with three runs against three. And frontier stopped more often on 871 and almost never crossed wall cells, so that comparison may tilt.

---

## Slide 4: Why: swapping the guesses barely moves the pick (about 50 s)

Why does the LLM add so little? We replayed saved stages offline. This is exploratory.

On the left, 121 stages. Swap the LLM's guesses for a random set, and the top view moves 2.28 metres. Swap one random set for another, and it moves 2.19. The difference is plus 0.09, from minus 0.25 to plus 0.38. Exact objects move the pick on 853 stages, by 0.92 metres, but not on 871 stages.

On the right, 119 stages: how well the score ranks views by unseen objects. The LLM's guesses give 0.20, a random set 0.19. They add plus 0.07 in 73 of 119 stages. That is a little ranking, but no more movement of the pick than a redraw gives.

---

## Slide 5: Near a real object, but rarely close (about 30 s)

Within half a metre of a real object with the same name: 3.0% of the LLM's new objects, against 0.5% of random ones. Within a metre, 10.1% against 2.0%. Within two metres, 23.8% against 6.3%.

So the LLM lands near a real object about six times as often as chance. Still, 97% of its objects miss by more than half a metre. This is the "wrong in place" half of the claim.

---

## Slide 6: Live test limits: what it could not rule out (about 50 s)

Three limits. First, the interval reaches plus 0.040. The test saw only gains of 0.024 to 0.028 or more.

Second, the placebo differed in pacing, in all five pairs. And members agreed on 29.4% of the LLM's guesses, against 4.4% of the random ones. ASP's score falls when members agree, so content is not the only change.

Third, F1 at 60 metres favours the LLM: plus 0.043, p 0.015, or 0.09 after correction.

*(Point to the strip.)*

Our filter, live: minus 0.003, no detectable difference. It removed 30% of new guesses. 3.1% of what it kept were hits, against 2.8% of all. No detectable difference is not proof of no effect.

---

## Slide 7: Same rules as the paper (about 40 s)

Part 2. We score with the author's own F1 and GED code, on his time axis. His reference was never released, so we built a scripted stand-in for his hand-driven tour: navmesh paths, the same mapper. Frontier runs to its natural end: 5 of 5 runs on 853, 1 of 5 on 871. Our model is DeepSeek. His is Gemini 2.5 Pro.

*(Point to the timelines.)*

The paper gives no budget value. On 853 we use the median end of five frontier runs, 632 seconds. So 10% is 63 seconds and 50% is 316. On 871 only one run finished, so we use the registered fallback, 809 seconds. That will change.

---

## Slide 8: On 853, the paper's ASP lead did not appear (about 55 s)

Object F1 times 100. Each cell shows the mean, the range and the runs that reach that time.

The paper's ASP scores 34.4, 60.8 and 66.7 at 10, 50 and 100% of the budget. Its frontier scores 18.6, 46.5 and 58.8. So its lead is 15.8 points at 10% and 14.3 at 50%.

*(Point to our rows.)*

Ours: ASP 16.5 and 38.7, from two runs. ASP with our filter, 14.8 and 48.3. Random guesses 13.8 and 43.9. Frontier 12.4, 39.5 and 55.6. Our ASP lead is 4.1 points at 10% and minus 0.8 at 50%. His lead did not appear on 853 at 10% and 50%, with DeepSeek and a rebuilt reference.

ASP has no 100% value, because our runs stop at 60 metres. One row is pending: ASP to the full budget. We may run it.

---

## Slide 9: On 871, our numbers are to be updated (about 15 s)

Same table, 871. Our cells are marked to be updated. Four frontier runs and the repeat tour are being rerun, and the budget moves with them. The paper's cells do not change.

---

## Slide 10: The reference is rebuilt, and it moves (about 45 s)

The reference holds 32% and 21% of the human-labelled objects.

Its repeat tour on 853 is not frozen. The two tours agree at F1 0.751, below the 0.90 line of the pre-registration. So the reference moves by more than the paper's margins. The first tour's damage is mixed in: nvblox died partway, and each reference lacks about its last 60 seconds. On 871 the repeat tour is pending.

*(Point to the table.)*

Check C1. We find 13 and 14 rooms, against the paper's 6 and 9. The navmesh island covers 77 and 59 square metres, the waypoint grid 191 and 149, the paper 208 and 235. The gap is partly explained: the grid reaches under furniture. On 853 it comes near the paper's figure. On 871 it does not.

---

## Slide 11: What limits the runs (about 30 s)

Two batches of one frontier explorer differ. On 853 at half the budget: 45.6 in October, 39.5 in November. At 10%: 15.3 and 12.4. The ranges overlap.

Our ASP runs stop at 60 metres, and ran in October; frontier ran in November. And in the host's copy of the code, frontier's clock counts its waits for a path; ASP's does not. We have not checked that against the released code.

---

## Slide 12: The author's defense, in three questions (about 40 s)

Part 3. The author said the guesses can be wrong in place but right in meaning, and that this is enough. We ask three questions.

One: is the meaning right, beyond base rates? The prompt says a scene may hold more than one bedroom and bathroom, so naming one proves little.

Two: would right meaning be enough? Offline, we give ASP true labels moved by real placement error.

Three: is it the model? We replay Claude Haiku 5.5 and Opus 5.5 on the same 44 saved inputs. We hash the rules before we score any Claude output.

---

## Slide 13: What a hit would need, on one real stage (about 40 s)

One real stage, drawn from files: run e1 00871 seed 42, stage 8. The map shows the 47 object nodes and 12 room nodes the robot had built. The colours are the house's regions: 7 seen, 1 partly seen, 8 unobserved. We show no model's guesses and compute no score.

For L1 and L2 a hit has no place: the type or class must be open. Here: bathroom, bedroom, and 65 classes. For L3 the guess must reach an unobserved region of its type or class, inside the dashed line.

---

## Slide 14: Three levels of "right" (about 40 s)

L1, which rooms: the type is still open. L2, which objects: the class is still open. L3, roughly where: the guess reaches an unobserved region that is of its type, or holds its class. L4, exactly where, is secondary.

Base rates matter. [TBD: an unseen bathroom remains in x% of stages, a bedroom y%, a kitchen z%.] When they are high, naming such a room proves little.

---

## Slide 15: What each guess is compared with (about 35 s)

Five comparisons. A prior from 179 other annotated houses, given the same map. The random-guess placebo. The model's own labels, swapped among its own guesses: the places stay, the labels move. The unobserved regions, trading contents. And the prior's labels at the model's places.

Apart, the wrong-house check: the same model's guesses for the other home, over six pairs. It gates L1 and L2, outside the test family.

---

## Slide 16: The paper's room test, with a chance rate (about 35 s)

A room counts as predicted if at least two of eight members place a room within 2.5 metres of its centre before the robot sees the region. The paper reports 9 of 28, with no chance rate beside it.

We score the same rule, with and without the type, and add random guesses as the chance rate. [TBD: the LLM predicts x of N rooms; random guesses y of N.] The replays have 4 members, so we report 1 of 4 and 2 of 4 beside chance, not against 9 of 28.

---

## Slide 17: Same inputs, three models (about 40 s)

The same 44 inputs go to Claude Opus 5.5, Claude Haiku 5.5 and DeepSeek. Each cell gives the lift over the named comparator: the prior at L1 and L2, the region trade at L3. The margins are 5, 5 and 3 points. The last column gives the detectable difference. [TBD: read the table.]

Each p is the largest over the cell's comparators. The family is two Claude models and three levels, with Holm. DeepSeek is exploratory. [TBD: the wrong-house check, and whether the freeze says L1 can decide.]

---

## Slide 18: Would right meaning be enough? (about 55 s)

We test this offline on 384 saved stages from 24 runs. F1 gives ASP the true objects: the best case. F5 is random guesses, the floor. F6 is no guesses. F3 moves the true objects by each model's own placement error. F-room keeps only what room types tell.

F0 is the all-true anchor. It is a property of the score: when every member holds the same guesses, the gain is zero. We show it as it comes out.

The rule has two steps. Does F1 separate from F5? If not, we stop. Then an arm is sufficient if it keeps at least half of that gap, with its interval wholly above. Every verdict is provisional. [TBD: read the chart.]

---

## Slide 19: What this talk cannot show (about 35 s)

Two houses. Proxy truth: human labels and a footprint rule stand in for what the camera saw. Static replays: no robot acts on Claude's guesses, and we ran no live Claude test. A weak yardstick: about 1 in 12 unseen objects in view reach the next map.

We wrote the scorer after we saw DeepSeek's numbers, and freeze it before any Claude output is scored. Every M2 verdict is provisional. The 8 Gemini rows have no wrong-house partner. And the plan expects the test cannot decide room types at 44 inputs; the freeze will say.

---

## Slide 20: The one-line answer to the author (about 50 s)

Four versions. The registered rules pick one, after the data exist.

Works: a Claude model is Supported at L3. Claude places content in the right unobserved region better than the named comparators. We have not shown that this reaches the map.

Mixed: none Supported at L3, and one Supported at L1 or L2 that also passes the wrong-house check. Right at house level, wrong in place.

Fails: every Claude model Rejected at L2 and L3. At L3 the margin is over the region trade, not the prior. Claude's lead over a prior that sees the same map is under the margin.

Inconclusive: none of these rules is met. The claim is neither supported nor rejected, and we state what the test could detect. If the replays do not run, no row applies. Thank you.

---

## Slide 21: Backup: the validity layer across models (not timed)

Four readouts, per model, in the same pass: the share the validator removes; whether valid guesses are right more often than removed ones; whether member agreement tracks truth; the yield of the vote filter. A fifth, on decisions, needed the cut bench replay. October gave the one live line on slide 6. [TBD: read the table.]
