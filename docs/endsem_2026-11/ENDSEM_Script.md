# Speaker script: end-sem (23 slides and 3 backup, about 14.5 minutes)

About 1,850 words for the 23 slides. *Italics* in parentheses are stage directions; the builder drops them from the notes. Every number comes from the result files; `SOURCES.md` names the file and the path. Part 3 is filled from `slots.json`, which `fill_slots_part3.py` writes from the result files.

---

## Slide 1: Right in meaning, wrong in place? (about 25 s)

ASP asks a language model to guess the rooms and objects a robot has not seen. Its author says the guesses are often in the wrong place but name the right things, and that this is enough. Is that so?

Part 1 is the live test. Part 2 puts our scores on the paper's scale. Part 3 tests the author's defense with Claude. Parts 1 and 2 are final, except the 871 numbers.

---

## Slide 2: ASP scores views by disagreement, not by truth (about 45 s)

The robot holds a map of what it has seen. The model guesses what lies beyond: eight guessed graphs, each with the same mapped part and its own extra rooms and objects.

For each candidate view, ASP asks what a camera there would see in each graph, and how far the eight graphs differ. A cost of 0.2 per metre is taken off.

The score has no term for truth, and none for unexplored space. If all eight graphs agree, the gain is zero. A guess earns score by differing from the others, not by being right.

---

## Slide 3: Live test: no detectable difference (about 50 s)

Part 1. Live runs in two homes, scored against human labels. Each line is a difference in map quality, with its 95% interval.

LLM guesses against random guesses: plus 0.013, from minus 0.012 to plus 0.040. Our filter against the LLM: minus 0.003. The LLM against plain frontier: minus 0.012. Random guesses against frontier: minus 0.025. Exact objects against random guesses: plus 0.034.

All five read the same way: no detectable difference. Two cautions. Exact objects stand on one house, under a deviation. And frontier stopped more often on 871 and almost never crossed wall cells, so that comparison may tilt.

---

## Slide 4: Why: swapping the guesses barely moves the pick (about 45 s)

Why does the LLM add so little? We replayed saved stages offline. This is exploratory.

Left, 121 stages. Swap the LLM's guesses for a random set, and the top view moves 2.28 metres. Swap one random set for another, and it moves 2.19. Exact objects move it on 853 stages, by 0.92 metres, not on 871.

On the right, 119 stages: how well the score ranks views by unseen objects. The LLM's guesses give 0.20, a random set 0.19. They add plus 0.07 in 73 of 119 stages: a little ranking, but no more movement of the pick than a redraw gives.

---

## Slide 5: Near a real object, but rarely close (about 25 s)

Within half a metre of a real object with the same name: 3.0% of the LLM's new objects, against 0.5% of random ones. Within two metres, 23.8% against 6.3%.

So the LLM lands near a real object about six times as often as chance. Still, 97% of its objects miss by more than half a metre. That is the "wrong in place" half of the claim.

---

## Slide 6: Live test limits: what it could not rule out (about 45 s)

First, the interval reaches plus 0.040. The test saw only gains of 0.024 to 0.028 or more.

Second, the placebo differed in pacing, in all five pairs. And members agreed on 29.4% of the LLM's guesses, against 4.4% of random ones.

Third, F1 at 60 metres favours the LLM: plus 0.043, p 0.015, or 0.09 after correction.

Our filter, live: minus 0.003, no detectable difference. It removed 30% of new guesses. That is not proof of no effect.

---

## Slide 7: Same rules as the paper (about 35 s)

Part 2. We score with the author's own F1 and GED code, on the paper's time axis. The author never released the reference, so we built a scripted stand-in for the hand-driven tour. Frontier runs to its natural end. Our model is DeepSeek; the paper's is Gemini 2.5 Pro.

The paper gives no budget value. On 853 we use the median end of five frontier runs, 632 seconds. On 871 only one run finished, so we use the registered fallback, 809 seconds. That will change.

---

## Slide 8: On 853, the paper's ASP lead did not appear (about 50 s)

Object F1 times 100. Each cell shows the mean, the range and the runs that reach that time.

The paper's ASP leads its frontier by 15.8 points at 10% and 14.3 at 50%. Ours: ASP 16.5 and 38.7, from two runs; with our filter 14.8 and 48.3; random guesses 13.8 and 43.9; frontier 12.4 and 39.5. Our ASP lead is 4.1 points at 10% and minus 0.8 at 50%.

The paper's lead did not appear on 853 at 10% and 50%, with DeepSeek and a rebuilt reference. ASP has no 100% value, because our runs stop at 60 metres. One row is still to come: ASP to the full budget.

---

## Slide 9: On 871, our numbers are to be updated (about 15 s)

Same table, 871. Our cells are marked to be updated: four frontier runs and the repeat tour are being rerun, and the budget moves with them. The paper's cells do not change.

---

## Slide 10: The reference is rebuilt, and it moves (about 40 s)

The reference holds 32% and 21% of the human-labelled objects.

On 853 the repeat tour is not frozen, and the two tours agree at F1 0.751, below the 0.90 line. So the reference moves by more than the paper's margins; the first tour's damage is mixed in. On 871 the repeat tour is pending.

Check C1: 13 and 14 rooms, against the paper's 6 and 9. The navmesh island covers 77 and 59 square metres, the waypoint grid 191 and 149, the paper 208 and 235. The grid reaches under furniture, which explains part of the gap.

---

## Slide 11: What limits the runs (about 25 s)

Two batches of one frontier explorer differ: on 853 at half the budget, 45.6 in October and 39.5 in November. The ranges overlap. Our ASP runs stop at 60 metres, and ran in October; frontier ran in November. And in the host's copy of the code, frontier's clock counts its waits; ASP's does not. We have not checked that against the released code.

---

## Slide 12: The author's defense, in three questions (about 35 s)

Part 3. The author said the guesses are often wrong in place but right in meaning, and that this is enough. We ask three questions.

Is the meaning right? A model must beat the controls: baselines that see the same map. Would right meaning be enough for ASP? We give ASP true labels, moved by real error. Is it the model? We replayed Claude on the same 44 saved inputs.

It is a blind test: we froze the scorer before we scored any Claude output.

---

## Slide 13: A hit, on one real stage (about 40 s)

One real stage, drawn from files. We show no model's guesses.

L1 asks which rooms: a hit needs the room type to be still open. Here that is bathroom and bedroom. L2 asks which objects: the class is still open; here, 65 classes. L3 asks roughly where: the guess must reach an unobserved region of its type or class, inside the dashed line. L4, exactly where, is secondary.

The base rate is what random guesses score: 87.5% at L1, 60.6% at L2, 1.7% at L3. So chance alone gets many hits at L1 and L2.

---

## Slide 14: What each guess is compared with (about 30 s)

A control sees the same map. The margin is the gain over it that we would still count: 5 points at L1 and L2, 3 at L3.

Five controls. A prior built from 179 other houses. Random guesses. The model's own labels, swapped among its guesses: the places stay, the labels move. The regions, trading contents. And the prior's labels at the model's places.

The named comparators are the prior at L1 and L2, and the region trade at L3.

---

## Slide 15: Blind test: the claim fails (about 55 s)

Each cell: the model minus the named comparator, its interval and the verdict; then the score and the difference from random guesses. A score is the mean over 12 clusters; a cluster is one home, seed and arm.

At L1, Opus is 0.058 below the prior and Haiku 0.104. At L2 both are far below it, Opus 0.351 and Haiku 0.249, with the interval wholly below zero. At L3 both are within 0.01 of the region trade.

All six are Rejected. That means the interval rules out a gain over the named comparator as large as the margin. It does not say the model is worse; only at L2 does the interval lie wholly below zero. The thesis line is: the claim fails. The saved Claude scores come from a single run with the frozen scorer; no other run is recorded.

---

## Slide 16: Two facts against the headline (about 45 s)

Two facts cut against the headline. First, Opus at L3 is close: the top of its interval is 0.0295, and the margin is 0.03. After the result, the independent checker reran the region trade fifteen times, deviation 55. The top ran from 0.0283 to 0.0298, below 0.03 every time. A value above it would have made the line inconclusive.

Second, Haiku at L2 is 8.2 points above random guesses, p 0.014. That is one contrast, and not adjusted.

In plain words: a list of the objects most houses have beats both models at naming unseen objects. At naming rooms the gap is smaller, and its interval touches zero.

---

## Slide 17: What the test could see (about 35 s)

What could the test see? At L1 and L2 the detectable difference is 5.7 and 5.2 points. Both exceed the 5-point margin. So a true gain equal to the margin would be found less than 80% of the time there. Rejected was still within reach at each level.

At L3, gains up to 2.95 points for Opus and 2.36 for Haiku are not ruled out.

---

## Slide 18: The wrong-house check (about 30 s)

The wrong-house check scores the model's guesses for the other home against this home. Guesses that fit this house should beat them.

No model passes. A pass needs p below 0.05 over six pairs. The best is Opus at L1, 0.125. Gemini's eight rows have no partner.

---

## Slide 19: Wrong in place: every source misses by metres (about 30 s)

How wrong in place? For each source, the median distance from a guess to the nearest unseen object it could name. Gemini 5.8 metres, exploratory, on eight inputs. Haiku 7.1. DeepSeek 7.7. Opus 8.1. Random guesses 8.9.

Each median rests on the guesses that have such an object in the house: for Opus, 800 of 1,348. Every source misses by metres.

---

## Slide 20: Would right meaning be enough? Not shown (about 50 s)

Would right meaning be enough for ASP's score? We tested it offline, on 384 stages from 24 runs. For each arm we correlate ASP's view score with the unmapped objects in view; that count is the yardstick.

True objects give 0.284, random guesses 0.065. So true objects beat random guesses by 0.218, and half of that is 0.109. Moving the true objects by each model's median error, 7 to 8 metres, gives 0.036 to 0.060: no gain over random guesses. Room type only gives 0.089. All true objects gives 0.048: when every member agrees, the gain is zero.

No other arm reaches half. Not shown sufficient, on a provisional yardstick.

---

## Slide 21: What this talk cannot show (about 30 s)

Every result holds for homes 853 and 871 only. It says nothing about other houses. The truth is a proxy: human labels and a footprint rule stand in for what the camera saw. The replays are static: Claude saw saved inputs, and no robot acted on its guesses.

The paper used Gemini 2.5 Pro. We used Claude with the author's prompt and loop. A Claude result does not speak for Gemini.

---

## Slide 22: The one-line answer to the author (about 40 s)

The claim fails. That is the registered line for the first half of the claim: that the guesses are right in meaning.

Both Claude models scored far below the other-house prior at naming objects. Neither beat a trade of region contents by the 3-point margin; a smaller gain is not ruled out.

And M2, offline, on a provisional yardstick: right labels moved by each model's error were not shown sufficient. M2 is provisional.

---

## Slide 23: What the answer does not show (about 30 s)

It does not show that an LLM cannot help exploration. We wrote the scorer after we saw DeepSeek's numbers. We set the L3 margin knowing the gap between Gemini and DeepSeek. M2 is provisional. One Haiku member's final text did not parse; 175 of 176 did. And part 2 is open: the 871 numbers and the 853 full-budget row are still to come. Thank you.

---

## Backup 1: The paper's room test, on DeepSeek's live runs (not timed)

The paper's rule: a room counts if at least two of eight members place a room within 2.5 metres of its centre before the robot sees the region. The paper reports 9 of 28.

On DeepSeek's live October runs, with the type matched, on all stages, DeepSeek predicts 13 of 59 rooms, 22%. Random guesses, our chance rate, predict 6 of 69, 9%. On the Claude replays, with one of four members and the type matched, Opus predicts 11 of 171 rooms, Haiku 2, DeepSeek 11, random guesses 8.

The prompt hint, run after the result, deviation 56: Haiku without the sentence made 12 room claims and 11 hit; with it, 9 claims and 5 hit. Object claims: 150 of 230 without, 146 of 219 with. The counts are small, and this is exploratory.

---

## Backup 2: Do the filter and the vote keep right guesses? (not timed)

Our filter removes 8.5% of Opus's guesses, 20.2% of Haiku's, 32.0% of DeepSeek's. The difference in L3 hit rate between kept and removed guesses is too wide to read for Opus. For Haiku and DeepSeek it shows no detectable difference. So where the interval can be read, kept guesses are not right more often.

---

## Backup 3: The four outcomes, and the rule that picked one (not timed)

The four pre-written outcomes: holds, mixed, fails, inconclusive. The rows apply in this order. Holds needs a Claude model Supported at L3: neither is. Mixed needs one Supported at L1 or L2 that passes the wrong-house check: none is. Fails needs every Claude model Rejected at L2 and L3: both are. So the line is: the claim fails.
