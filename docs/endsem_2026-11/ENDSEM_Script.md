# Speaker script: end-sem (16 slides, about 15 minutes)

About 1,900 words. *Italics* in parentheses are stage directions; the builder drops them from the notes. `[TBD ...]` marks a number that part 3 has not produced yet: fill it in from `slots.json`, then read the sentence as written. `SOURCES.md` gives the file behind each number.

---

## Slide 1: Right in meaning, wrong in place? (about 40 s)

This talk asks one question. ASP asks a language model to guess the rooms and objects the robot has not seen. Its author says the guesses are often in the wrong place but name the right things, and that this is enough. Is that so?

*(Point to the three columns.)*

Part 1 is the live test we finished in October. Part 2 puts our numbers on the paper's scale. Part 3 tests the author's defense head on. Parts 1 and 2 are final, with one exception: the 871 numbers in part 2 are being rerun.

*(Version 1: part 3 slides carry grey "result pending" marks until slots.json is filled.)*

---

## Slide 2: ASP scores views by disagreement, not by truth (about 70 s)

This is how ASP picks where to go. The robot holds a map of what it has seen. The language model guesses what lies beyond. That gives eight guessed graphs. Each has the same mapped part and its own extra rooms and objects.

*(Point to the middle box.)*

For each candidate view, ASP asks what a camera there would see in each graph. Then it measures how far the eight graphs differ about that view. Two terms do this, one for objects and one for rooms. Each is the entropy of what all graphs say together, minus the mean entropy inside each graph. A cost of 0.2 per metre of travel is taken off.

*(Point to the three columns.)*

Look at what the score leaves out. It has no term for whether a guess is true. It has no term for whether the space is unexplored. And if all eight graphs agree, the gain is zero. A guess earns score by differing from the others, not by being right. That matters again in part 3.

---

## Slide 3: Live test: no detectable difference in any contrast (about 80 s)

Part 1. These are live runs in two homes, seeds 42 to 44, scored against the human labels that ship with HM3D. Each line is a difference in map quality, F1 area under the curve to 60 metres, with its 95% interval.

*(Point to the rows, top to bottom.)*

LLM guesses against random guesses of the same shape: plus 0.013, with an interval from minus 0.012 to plus 0.040. Our filter against the LLM alone: minus 0.003. The LLM against plain frontier exploration, with no LLM: minus 0.012. Random guesses against frontier: minus 0.025, and its interval ends at plus 0.002. Exact objects against random guesses: plus 0.034, in one home only.

The registered reading is the same for all five: no detectable difference. For exact objects, three runs against three cannot give a p below 0.10, and we got 0.10. So its interval has no bounds, and that test cannot decide.

---

## Slide 4: Why: swapping the guesses barely moves the pick (about 55 s)

Why does the LLM add so little? We replayed 121 saved stages offline and swapped the guesses. Replace the LLM's guesses with a random set, and the top-scored view moves 2.28 metres, median. Replace one random set with another, and it moves 2.19. The difference is plus 0.09 metres, with an interval from minus 0.25 to plus 0.38.

*(Point to the bars on the right.)*

Now the score against the unseen true objects a view shows. The LLM's guesses give a rank correlation of 0.20. A random set gives 0.19. No guesses give minus 0.07. Exact objects give 0.44, in part by construction, because the count uses the same objects. Exact objects do move the pick more, by 0.68 metres beyond a redraw, but not on 871 stages or on counted runs alone. The score reads random guesses much as it reads the LLM's.

---

## Slide 5: Live test limits: what it could not rule out (about 65 s)

Three things the live test could not rule out.

First, the interval. It reaches plus 0.040. The test had 80% power only for differences of about 0.024 to 0.028. A real gain of 0.040 stays possible.

Second, the placebo differed from the LLM arm in more than content. In pacing: in all five pairs, the placebo's wait differed from its partner's by more than 20% at three or more stages. And in agreement: another member matched 29.4% of the LLM's guesses within a metre, against 4.4% of the placebo's. ASP's score falls when members agree.

Third, one registered secondary favours the LLM. F1 at 60 metres: plus 0.043, p 0.015, which is 0.09 after we correct for six tests. At 30 metres it is minus 0.011, and on 853 the placebo led earlier.

So the test shows no detectable difference at its size. It does not show no effect.

---

## Slide 6: Same rules as the paper (about 60 s)

Part 2. We score with the author's own F1 and GED code, on his time axis. His reference graphs were never released, so we rebuilt them his way: a scripted tour through every reachable point on the start floor, with the same mapper. That is 85 stops on 853 and 66 on 871. We ran the frontier explorer to its natural end: 5 of 5 runs on 853, 1 of 5 on 871. Our LLM is DeepSeek. His is Gemini 2.5 Pro.

*(Point to the timelines.)*

The paper reads its scores at 10, 50 and 100% of a fixed navigation time, and gives no value for that time. We set it from our frontier runs. On 853 it is the median end of five runs, 632 seconds. So 10% is 63 seconds and 50% is 316. On 871 only one run finished, so we use the registered fallback, 809 seconds. That one will change. The 871 reruns are under way, and the budget becomes the median of the valid runs.

---

## Slide 7: The paper's Fig. 4 numbers beside ours (about 70 s)

Object F1 times 100. Start with 853.

The paper's ASP scores 34.4, 60.8 and 66.7 at 10, 50 and 100% of the budget. Its frontier scores 18.6, 46.5 and 58.8. So its ASP lead is 15.8 points at 10% and 14.3 at 50%.

*(Point to our rows.)*

Ours: ASP 16.5 and 38.7, from two runs. Random guesses 13.8 and 43.9. Frontier 12.4, 39.5 and 55.6, where the 55.6 comes from 3 of 5 runs. ASP has no 100% value, because our ASP runs stop at 60 metres. The empty row is for ASP to the full budget on 853. We may run it. If we do, it fills the one gap in the table.

Our ASP lead is 4.1 points at 10% and minus 0.8 at 50%. The paper's lead did not appear on 853 at 10% and 50%, with DeepSeek and a rebuilt reference.

*(Point to the 871 block.)*

Every number of ours in the 871 block is marked to be updated. Those runs are being rerun, and the budget will change. Do not read it yet.

---

## Slide 8: What limits the paper comparison (about 55 s)

Four limits.

One. The reference is rebuilt, not the author's. It holds 32% and 21% of the human-labelled objects. Its F1 against our older frontier-made reference is 0.64 and 0.67. The repeat tour froze, so we do not know how far the reference itself moves. It is being rerun.

Two. Rooms and floor area differ. In check C1 we find 13 and 14 rooms, against the paper's 6 and 9. The start floor's navmesh covers 77 and 59 square metres, against the paper's 208 and 235. We cannot yet explain the gap.

Three. Two batches of the same frontier explorer differ: 45.6 against 39.5 on 853 at half the budget.

Four. Our ASP runs stop at 60 metres. ASP ran in October and frontier in November. In the host's copy of the code, frontier's clock also counts its waits, and ASP's does not.

So we read the table as a check on scale. It does not test the paper's claim.

---

## Slide 9: The author's defense, in three questions (about 60 s)

Part 3. When we met the author, he said the guesses can be wrong in place but right in meaning, and that this is enough. We turn that into three questions.

One: is the meaning right, beyond base rates? The prompt says a scene may contain more than one bedroom and more than one bathroom, so naming one proves little. We compare the saved guesses with controls that see the same map.

Two: would right meaning be enough for ASP's score? Offline, we give ASP true labels with the placement error real models make.

Three: is it the model? We replay Claude Haiku 5.5 and Claude Opus 5.5 on the same 44 saved inputs as DeepSeek. If that does not run, DeepSeek's results stay exploratory.

The validity layer runs in the same pass. We hash the rules before we score any Claude output.

---

## Slide 10: Base rates, and four levels of "right" (about 60 s)

First, base rates. The prompt tells the model that a scene may contain more than one bedroom and more than one bathroom. So when the model names a bedroom, we need to know how often an unseen bedroom exists anyway. [TBD: an unseen bathroom remains in x% of stages, a bedroom in y%, a kitchen in z%. Of the LLM's new rooms, n are bedrooms and m are bathrooms.]

Now four levels of "right". L1: a room type has an unseen region. L2: an object class has an instance in an unseen region. L3: roughly where. The guessed centre lies in, or within half a metre of, an unseen region of that type or holding that class. We score L3 only on regions with nothing mapped or observed yet, so finishing a half-seen room earns no credit. L4: exactly where, within 0.5 to 3 metres. L4 is secondary.

The controls a skeptic accepts: a prior that sees the same map, the same model asked about the wrong house, and the same guesses with positions shuffled.

---

## Slide 11: The paper's room test, with a chance rate (about 50 s)

The paper has its own test. A room counts as predicted if at least two of eight samples place a room of its type within 2.5 metres of its centre, before the robot finds it. The paper reports 9 of 28.

That number has no chance rate beside it. We run the same rule on random guesses of the LLM's shape. [TBD: the LLM predicts x of N rooms; random guesses predict y of N.]

The Claude replays have 4 members, not 8. We report 1 of 4 and 2 of 4 beside the same chance rate. We do not compare them with 9 of 28.

---

## Slide 12: Same inputs, three models (about 55 s)

The same 44 inputs go to DeepSeek, Claude Haiku 5.5 and Claude Opus 5.5. Each row is a model and each column a level. Each cell gives the model's lift over its strongest comparator, with an interval and a verdict: Supported, Rejected or Inconclusive. [TBD: read the table.]

Three rules, all registered. DeepSeek is exploratory, because we saw pilot numbers before we fixed the rules. Claude is the test, in a family of two models and three levels. Under a null the verdict is Inconclusive, not Mixed. And at 44 inputs, L1 cannot decide.

---

## Slide 13: Would right meaning be enough for ASP's score? (about 70 s)

We test this offline on saved stages, with member sets of four. F1 gives ASP the true unseen objects at true positions: the best case. F-room gives true room types at their footprints. F3 gives true labels moved by a model's measured placement error. F5 and F6 are random guesses and no guesses.

First, an anchor. F0 gives every member the full truth. Then the members agree, ASP's score gives unexplored space zero, and the pick falls to the nearest candidate. That is an identity, not a finding. We show it to mark the end of the scale, and for nothing else.

The rule: right meaning is enough if F3 gains at least half of what F1 gains over F5, and the interval by run lies above that line. It is not enough if the top of the interval falls below it. We register one bias. F1 is high by construction, so the verdict leans toward not enough. We write it as "not shown sufficient, on a yardstick biased toward rejection". [TBD: read the chart and the share kept.]

---

## Slide 14: The validity layer across models (about 45 s)

We score the validity layer in the same pass, for every model. October gives a first look, with DeepSeek only. Our validator removed 30% of the new guessed objects, 2,573 of 8,465. 56 of those were hits. The hit rate within half a metre was 3.1% for what it kept and 2.8% for all guesses. It made no detectable difference to the live map.

For the new models we report four readouts: the share removed; whether valid guesses are right more often than removed ones; whether member agreement tracks truth; and the yield of the vote filter. [TBD: read the table.]

Why it matters: the vote keeps what members agree on, and ASP's score gives agreed content zero. If the vote finds the true guesses, ASP's score still has nowhere to use them.

---

## Slide 15: What this talk cannot show (about 40 s)

Five limits.

Two houses. Any inference holds for these two homes.

Proxy truth. HM3D's human labels and a footprint rule for "seen" stand in for what is in the house.

Static replays. Claude sees saved inputs, with four members. No robot acts on its guesses, and we ran no live Claude test.

A weak yardstick. About 1 in 12 unseen true objects in view of a stop reach the next map, and the count ignores unmapped walls.

Room-type claims. We cannot decide them at 44 inputs: that is 12 run clusters and five typable room types. At L1 a null reads Inconclusive.

---

## Slide 16: The one-line answer to the author (about 45 s)

The answer comes in four versions. The registered rules pick one, after the data exist.

Works: a Claude model is Supported at L3 on the unobserved stratum. Then Claude names which rooms and objects lie in which unexplored region better than the named comparators, in two houses, on proxy truth. We have not shown that this reaches the map.

Mixed: Supported at L1 or L2, but not at L3. Right at house level, wrong in place.

Fails: both Claude models Rejected at L2 and L3. Claude's lead over a prior that sees the same map is smaller than the registered margin, and the right semantics in the demo are mostly base rate. This is about ASP's guesses on these inputs, not about LLM-guided exploration in general.

Inconclusive: anything else. We found no detectable difference between Claude's guesses and the comparators. At 44 inputs in two houses, the test detects only differences of the registered size.

If the Claude replays do not run, DeepSeek's results are exploratory and no version applies. Thank you.
