# Speaker script: end-sem (24 slides and 4 backup, about 14.5 minutes)

About 1,850 words for the 24 slides. *Italics* in parentheses are stage directions; the builder drops them from the notes. Every number comes from the result files; `SOURCES.md` names the file and the path. Part 3 is filled from `slots.json`, which `fill_slots_part3.py` writes from the result files.

---

## Slide 1: Right in meaning, wrong in place? (about 25 s)

ASP asks a language model to guess the rooms and objects a robot has not seen. Its author says the guesses are often in the wrong place but name the right things, and that this is enough. Is that so?

Part 1 is the live test. Part 2 puts our scores on the paper's scale. Part 3 tests the author's defense with Claude. Parts 1 and 2 are final, except the 871 numbers.

---

## Slide 2: ASP scores views by disagreement, not by truth (about 45 s)

The robot holds a map of what it has seen. The model guesses what lies beyond: eight guessed graphs, each with the same mapped part and its own extra rooms and objects.

For each candidate view, ASP asks what a camera there would see in each graph, and how far the eight differ. A cost of 0.2 per metre is taken off.

The score has no term for truth, none for unexplored space. If all eight graphs agree, the gain is zero. A guess earns score by differing, not by being right.

---

## Slide 3: Live test: no detectable difference (about 50 s)

Part 1. Live runs in two homes, scored against human labels. Each line is a difference in map quality, with its 95% interval.

LLM guesses against random guesses: plus 0.013, from minus 0.012 to plus 0.040. Our filter against the LLM: minus 0.003. The LLM against plain frontier: minus 0.012. Random guesses against frontier: minus 0.025. Exact objects against random guesses: plus 0.034.

All five: no detectable difference. Two cautions. Exact objects stand on one house, under a deviation. And frontier stopped more often on 871 and almost never crossed wall cells.

---

## Slide 4: Why: swapping the guesses barely moves the pick (about 40 s)

Why does the LLM add so little? An offline replay of saved stages; exploratory.

Left, 121 stages. Swap the LLM's guesses for a random set, and the top view moves 2.28 metres. Swap one random set for another, and it moves 2.19. Exact objects move it on 853 stages, by 0.92 metres, not on 871.

Right, 119 stages: how well the score ranks views by unseen objects. The LLM's guesses give 0.20, a random set 0.19. They add plus 0.07 in 73 of 119 stages: a little ranking, but no more movement of the pick than a redraw gives.

---

## Slide 5: Near a real object, but rarely close (about 25 s)

Within half a metre of a real object with the same name: 3.0% of the LLM's new objects, against 0.5% of random ones. Within two metres, 23.8% against 6.3%.

So the LLM lands near a real object about six times as often as chance. Still, 97% of its objects miss by more than half a metre.

---

## Slide 6: Live test limits: what it could not rule out (about 45 s)

First, the interval reaches plus 0.040. The test saw only gains of 0.024 to 0.028 or more.

Second, the placebo differed in pacing, in all five pairs. And members agreed on 29.4% of the LLM's guesses, against 4.4% of random ones.

Third, F1 at 60 metres favours the LLM: plus 0.043, p 0.015, or 0.09 after correction.

Our filter, live: minus 0.003, no detectable difference. It removed 30% of new guesses. That is not proof of no effect.

---

## Slide 7: Same rules as the paper (about 35 s)

Part 2. We score with the author's own F1 and GED code, on the paper's time axis. The author never released the reference, so we built a scripted stand-in for the hand-driven tour. Our model is DeepSeek; the paper's is Gemini 2.5 Pro.

The paper gives no budget value. On 853 we use the median end of five frontier runs, 632 seconds. On 871 only one run finished, so we use the registered fallback, 809 seconds. That will change.

---

## Slide 8: On 853, the paper's ASP lead did not appear (about 50 s)

Object F1 times 100. Each cell shows the mean, the range and the runs that reach that time.

The paper's ASP leads its frontier by 15.8 points at 10% and 14.3 at 50%. Ours: ASP 16.5 and 38.7, from two runs; with our filter 14.8 and 48.3; random 13.8 and 43.9; frontier 12.4 and 39.5. Our ASP lead is 4.1 points at 10% and minus 0.8 at 50%.

The paper's lead did not appear on 853 at 10% and 50%, with DeepSeek and a rebuilt reference. One row is still to come: ASP to the full budget.

---

## Slide 9: On 871, our numbers are to be updated (about 15 s)

Same table, 871. Our cells are marked to be updated: four frontier runs and the repeat tour are being rerun, and the budget moves with them. The paper's cells do not change.

---

## Slide 10: The reference is rebuilt, and it moves (about 45 s)

The reference holds 32% and 21% of the human-labelled objects.

On 853 the repeat tour is not frozen; the two tours agree at F1 0.751, below the 0.90 line. So the reference moves by more than the paper's margins, with the first tour's damage mixed in.

Check C1: 13 and 14 rooms, against the paper's 6 and 9. The navmesh island covers 77 and 59 square metres; the outline of everything labelled 213 and 253. The paper has 208 and 235: 2.7 and 4.0 times the walkable floor, and within about 7% of the outline. We do not know how the paper measured area.

---

## Slide 11: What limits the runs (about 25 s)

Two batches of one frontier explorer differ: on 853 at half the budget, 45.6 in October and 39.5 in November. The ranges overlap. Our ASP runs stop at 60 metres, and ran in October; frontier ran in November. And in the host's copy of the code, frontier's clock counts its waits; ASP's does not. We have not checked that against the released code.

---

## Slide 12: The author's defense, in three questions (about 35 s)

Part 3. The author said the guesses are often wrong in place but right in meaning, and that this is enough. We ask three questions.

Is the meaning right? A model must beat the controls: baselines that see the same map. Would right meaning be enough for ASP? We give ASP true labels, moved by real error. Is it the model? We replayed Claude on the same 44 saved inputs.

It is a blind test: the scorer was frozen first.

---

## Slide 13: A hit and a miss, on one real stage (about 40 s)

One real stage, drawn from files, with two saved guesses from one Opus member. The star is a bed guess that hits; the cross is a toilet guess that misses.

L1 asks which rooms: the type must be still open, here bathroom and bedroom. L2 asks which objects: the class is still open; here, 65 classes. L3 asks roughly where: the guess must reach an unobserved region that fits it, inside the dashed line. L4, exactly where, is secondary.

The base rate is what random guesses score: 87.5%, 60.6% and 1.7%.

---

## Slide 14: What each guess is compared with (about 35 s)

A control sees the same map. The margin is the gain over it that we would still count: 5 points at L1 and L2, 3 at L3. Named means the control the verdict is read against.

Five controls. A prior built from 179 other houses. Random guesses. The model's own labels, swapped among its guesses: the places stay, the labels move. The regions, trading contents. And the prior's labels at the model's places. The named controls are the prior at L1 and L2, and the region trade at L3.

---

## Slide 15: Blind test: the claim fails (about 55 s)

Each cell: the model minus the named comparator, in points, with its interval and verdict; then the score, and the difference from random guesses. A score is a hit rate over 12 clusters (home, seed, arm).

At L1, Opus is 5.8 points below the prior and Haiku 10.4. At L2 both are far below it, Opus 35.1 and Haiku 24.9, the interval wholly below zero. At L3 the intervals reach plus 2.95 points for Opus and 2.4 for Haiku, under the 3-point margin.

All six are Rejected: the interval rules out a gain as large as the margin. It does not say the model is worse, except at L2. The thesis line: the claim fails. The saved Claude scores come from a single run with the frozen scorer; no other run is recorded.

---

## Slide 16: Two facts against the headline (about 45 s)

Two facts cut against the headline. First, Opus at L3 is close: the top of its interval is 2.95 points, the margin 3. After the result, the checker reran the region trade fifteen times, deviation 55. The top ran from 2.83 to 2.98, below 3 every time. A value above it would have made the line inconclusive.

Second, Haiku at L2 is 8.2 points above random guesses, p 0.014: one contrast, not adjusted.

And at L2, in these two houses, a prior from 179 other houses, making as many claims as the model, scored above both models at naming objects.

---

## Slide 17: What the test could see (about 35 s)

At L1 and L2 the detectable difference is 5.7 and 5.2 points, above the 5-point margin. So a true gain equal to the margin would be found less than 80% of the time there. Rejected was still within reach at each level.

At L3, gains up to 2.95 points for Opus and 2.36 for Haiku are not ruled out. There is no L3 row: its registered figure, 1.1 points, comes from the random guesses' contrast and does not bound the Claude contrasts.

---

## Slide 18: The wrong-house check (about 30 s)

The wrong-house check scores the model's guesses for the other home against this home. Guesses that fit this house should beat them.

No model passes. A pass needs p below 0.05 over six pairs. The best is Opus at L1, 0.125. Gemini's eight rows have no partner.

---

## Slide 19: How far a guess is from an object it could name (about 30 s)

This is the input to the next slide, not a claim about where guesses sit. For each source, the median distance from a guess to the nearest unseen object it could name: Gemini 5.8 metres, exploratory, on eight inputs; Haiku 7.1; DeepSeek 7.7, exploratory; Opus 8.1; random guesses 8.9.

The nearest object of a class is a minimum, and guesses with no such object are left out: for Opus, 800 of 1,348 are used.

---

## Slide 20: Right meaning: not shown to be enough (about 55 s)

Would right meaning be enough for ASP's score? Offline, on 384 stages from 24 runs, we correlate ASP's view score with the unmapped objects in view: the yardstick.

True objects give 0.284, random guesses 0.065. True objects beat random guesses by 0.218; half of that is 0.109. Moving the true objects, each move drawn from the model's error sample, gives 0.036 to 0.060: no detectable gain over random guesses.  All true objects for every member gives 0.048, slightly below random guesses: minus 0.017, from minus 0.031 to minus 0.004. We have no tested account of why.

No arm reaches half. Not shown sufficient, on a provisional yardstick.

---

## Slide 21: What this talk cannot show (about 30 s)

Every result holds for homes 853 and 871 only, not other houses. The truth is a proxy: human labels stand in for what the camera saw. The replays are static: Claude saw saved inputs, and no robot acted on its guesses.

The paper used Gemini 2.5 Pro. We used Claude with the author's prompt and loop. A Claude result does not speak for Gemini.

---

## Slide 22: How the test was made (about 35 s)

We wrote the scorer after we saw DeepSeek's numbers, and froze it before Claude. We set the L3 margin knowing the gap between Gemini and DeepSeek. M2 is provisional: its yardstick failed part of an October check. One Haiku member stopped at the token limit and its text did not parse; 175 of 176 did. And part 2 is open: the 871 numbers and the 853 full-budget row are still to come.

---

## Slide 23: The one-line answer to the author (about 40 s)

The claim fails. That is the registered line for the first half of the claim: that the guesses are right in meaning.

In these two houses, both Claude models scored far below the other-house prior at naming objects. Neither beat a trade of region contents by the 3-point margin; a smaller gain is not ruled out.

And M2, offline: right labels moved by each model's error were not shown sufficient. M2 is provisional.

---

## Slide 24: What the answer does not say (about 30 s)

It does not say the guesses reach the map, or where they sit. It does not say the models are no better than random guesses: Haiku is 8.2 points above them at L2, one contrast, not adjusted. It says nothing about live runs, other models or the paper's scale. And it does not show that a language model cannot help exploration. Thank you.

---

## Backup 1: The paper's room test, on DeepSeek's live runs (not timed)

The paper reports 9 of 28 rooms. A room counts if at least two of eight members place a room within 2.5 metres of its centre before the robot sees the region.

On DeepSeek's live October runs, exploratory, with the type matched, on all stages, DeepSeek predicts 13 of 59 rooms, 22%. Random guesses, our chance rate, predict 6 of 69, 9%. On the Claude replays, one of four members, type matched: Opus 11 of 171 rooms, Haiku 2, DeepSeek 11, random 8.

The prompt hint, run after the result, deviation 56: Haiku without the sentence made 12 room claims and 11 hit; with it, 9 claims and 5 hit. Object claims: 150 of 230 without, 146 of 219 with. Small counts; exploratory.

---

## Backup 2: Do the filter and the vote keep right guesses? (not timed)

Our filter removes 8.5% of Opus's guesses, 20.2% of Haiku's, 32.0% of DeepSeek's and 68.9% of random guesses. At L3, kept and removed guesses show no detectable difference for Haiku, DeepSeek and random guesses. For Opus the interval is too wide to read.

---

## Backup 3: Why does ASP not gain from all true objects? (not timed)

The likely question: if every member holds every true object, why does ASP's score not rise? All true objects for every member scored minus 0.017, from minus 0.031 to minus 0.004, against random guesses. True objects in differing subsets scored plus 0.218 above them.

The score counts disagreement between members. We registered that before the run. Why all true objects fall below random guesses we cannot explain: the gain is zero for every candidate in only 2 of 384 stages.

---

## Backup 4: The four outcomes, and the rule that picked one (not timed)

The four pre-written outcomes: holds, mixed, fails, inconclusive. The rows apply in this order. Holds needs a Claude model Supported at L3: neither is. Mixed needs one Supported at L1 or L2 that passes the wrong-house check: none is. Fails needs every Claude model Rejected at L2 and L3: both are. So the line is: the claim fails.
