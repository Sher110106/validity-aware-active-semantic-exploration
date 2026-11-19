# Speaker script: end-sem (25 slides and 6 backup, about 15 minutes)

About 2,013 words for the 25 slides, no slide above 2.3 words a second; the times in the slide headings add to 900 s. *Italics* in parentheses are stage directions; the builder drops them from the notes. Every number comes from the result files; `SOURCES.md` names the file and the path. Part 3 is filled from `slots.json`, which `fill_slots_part3.py` writes from the result files. Anything not registered is called exploratory on its slide.

---

## Slide 1: Right in meaning, wrong in place? (about 27 s)

ASP asks a language model to guess the rooms and objects a robot has not seen. As the author put it to us, the guesses are often wrong in place but name the right things, and that is enough. We test that.

Registered scores and tests are final. Two control runs and a Gemini replay are registered, running, and not shown.

---

## Slide 2: The proposal's question was measured in part (about 38 s)

The proposal asked: can validating and calibrating the guesses cut false detours without cutting discovery of rooms?

We measured our validator, live, in two homes: minus 0.003, from minus 0.047 to plus 0.037. No detectable difference; the test could see only gains of 0.044 or more.

We did not measure detours or collisions, and calibration was retired.

September's claim is withdrawn: the filter kept 19 of 8,943 guesses, so the gain came from deleting them. The question became: do the guesses carry any value?

---

## Slide 3: ASP scores views by disagreement, not by truth (about 31 s)

The model guesses what lies beyond the mapped part: eight graphs, in two tracks of four. ASP asks what a camera at each candidate view would see in each graph, and how far they differ.

No term asks whether a guess is true. If all eight graphs agree, the gain is zero; the two tracks start from different observed maps, so it rarely is. A guess earns score by differing.

---

## Slide 4: Live test: no detectable difference (about 40 s)

Live runs in two homes, against human labels. Each line is a difference in map quality, with its 95% interval.

LLM guesses against random guesses: plus 0.013, from minus 0.012 to plus 0.040. All five: no detectable difference. Cautions: exact objects stand on one house; frontier stopped more often on 871 and almost never crossed wall cells.

The live model is small: DeepSeek V4.1 Flash at low effort. The paper says such models do not give consistent enough performance. So this null is about ASP with a cheap model.

---

## Slide 5: Why: swapping the guesses barely moves the pick (about 30 s)

An offline replay of saved stages; exploratory.

Swap the LLM's guesses for a random set, and the top view moves 2.28 metres. Swap one random set for another, 2.19. Exact objects move it 0.92 metres on 853 stages, not on 871.

The LLM's guesses rank views a little better: plus 0.07, in 73 of 119 stages. They do not move the pick more than a redraw does.

---

## Slide 6: Near a real object, but rarely close (about 24 s)

Within half a metre of a real object with the same name: 3.0% of the LLM's new objects, against 0.5% of random ones. Within two metres, 23.8% against 6.3%.

So the LLM lands near a real object six times as often as chance. Still, 97% of its objects miss by more than half a metre.

---

## Slide 7: Live test limits: what it could not rule out (about 33 s)

First, the interval reaches plus 0.040; the test saw only gains of 0.024 to 0.028 or more. Second, the placebo differed in pacing in all five pairs, and members agreed on 29.4% of the LLM's guesses against 4.4% of random ones. Third, F1 at 60 metres favours the LLM: plus 0.043, p 0.015, or 0.09 after correction.

Our filter: no detectable difference; it removed 30% of new guesses. That is not proof of no effect.

---

## Slide 8: Same rules as the paper (about 27 s)

Part 2. We score with the author's F1 and GED code, on the paper's time axis, against a scripted stand-in for the hand-driven tour. Our model is DeepSeek; the paper's is Gemini 2.5 Pro.

The paper gives no budget. We use the median end of our frontier runs: 632 seconds on 853, 1300 on 871. So 871's budget is about twice 853's.

---

## Slide 9: By the clock ASP reads above frontier; by the metre the sign depends on the reference (about 43 s)

By the clock, registered: November's three ASP runs sit above our five frontier runs at 10%, 50% and 100%, by 4.8, 11.6 and 6.0 points, against the paper's 15.8, 14.3 and 7.9. At 100% that is two runs against three. October's two runs trailed by 0.8 at 50%; the batches differ by 12.4.

By the metre, exploratory: at 50 metres ASP is 0.8 ahead under the scripted reference and 1.9 behind under the human labels. At 100 metres, 3.8 ahead and 1.6 behind.

One home, two or three runs: not a test of the paper's claim.

---

## Slide 10: How close we are to the paper on 871 depends on the budget (about 41 s)

At our budget, 1300 seconds, ours are 1.3 to 3.5 points above the paper's. But that budget is twice 853's. The paper says a run has 25 to 30 steps, which suggests a shorter budget; that is our inference. At 750 seconds our frontier is 2.9 to 12.1 points below the paper's.

At 50 metres, exploratory: exact objects 57.8, ASP 52.6, November's frontier 49.2, random guesses 42.1, October's frontier 36.3. The two frontier batches differ by 12.9, more than ASP differs from either November's frontier or random guesses. This proves nothing.

---

## Slide 11: The reference is rebuilt, and it moves (about 38 s)

The reference holds 32% and 21% of the human-labelled objects. The repeat tour is not frozen in either home: the two tours agree at F1 0.751 on 853 and 0.771 on 871, below the 0.90 line, so the reference moves by more than the paper's margins.

Check C1: 13 and 14 rooms; the paper has 6 and 9. Its floor area, 208 and 235 square metres, is 2.7 and 4.0 times our walkable floor. We do not know how the paper measured area.

---

## Slide 12: What limits the runs (about 41 s)

October's ASP runs stop at 60 metres, November's go to 105; two of three reach the full budget. At half the budget they score 38.7 and 51.1, a gap as large as ASP's lead over frontier. October's random-guess runs read 43.9, between the two.

The clocks differ. In the authors' code, frontier's clock starts when planning ends, before the path arrives, so it counts the wait; ASP's starts as the robot moves. We checked this on 19 November, in commit f1ea141b. On 853 ASP logs 5.8 seconds a metre against frontier's 7.0.

---

## Slide 13: The author's claim, in three questions (about 36 s)

As the author put it to us, the guesses are often wrong in place but right in meaning, and that is enough. It is not in the paper; it comes from the author's demo and what they told the student.

Is the meaning right? A model must beat the controls. Is it enough for ASP? We give ASP true labels, moved by real error. Is it the model? We replay Claude on 44 saved inputs, and look at Gemini.

---

## Slide 14: A hit and a miss, on one real stage (about 30 s)

One real stage, with two saved guesses from one Opus member: a bed that hits, a toilet that misses.

L1: which rooms; the type must still be open. L2: which objects; the class must be open, here among 65. L3: roughly where; the guess must reach an unobserved region that fits it, inside the dashed line. The base rate is what random guesses score: 87.5%, 60.6% and 1.7%.

---

## Slide 15: What each guess is compared with (about 28 s)

A control sees the same map. The margin is the gain over it we would still count: 5 points at L1 and L2, 3 at L3. Five controls, on the slide. Named: the prior at L1 and L2, the region trade at L3.

We did not check what the comparators score before the freeze; the power check asked only whether Rejected was within reach.

---

## Slide 16: Naming: no detectable gain over base rates, below them at L2. Placing: none over a region trade (about 47 s)

Each cell: the model minus the named comparator, in points, with interval and verdict; then the model's score and the comparator's.

At L1, Opus scores 85.4% and the prior 91.2%; Haiku 89.6% and 100%. At L2, Opus 58.3% against 93.4%; Haiku 68.8% against 93.7%: detectably below. At L3 the intervals end at plus 2.95 points for Opus and 2.4 for Haiku, under the 3-point margin.

The registered line is: the claim fails. It says less than it seems to. All six are Rejected, but at L1 no model could have been Supported, and at L2 only a perfect Opus could, so it rests on L3.

---

## Slide 17: Two facts that cut against the registered line (about 34 s)

Two facts cut against the line. Opus at L3 is close: the top of its interval is 2.95 points, the margin 3. After the result the checker reran the region trade fifteen times, deviation 55: the top ran from 2.83 to 2.98, below 3 every time.

Haiku at L2 is 8.2 points above random guesses, p 0.014: one contrast, not adjusted. And at L2 a prior from 179 other houses scored above both models at naming objects.

---

## Slide 18: What a perfect score could have shown: a ceiling at L1 and L2 (about 45 s)

Exploratory, made after the result. The prior scores 91.2% on Opus's L1 rows and 100% on Haiku's; at L2, 93.4% and 93.7%. A perfect model could gain 8.8 and 0.0 points at L1, 6.6 and 6.3 at L2.

Its best p after Holm: 0.750 and 1.000 at L1; 0.047 and 0.188 at L2. So a perfect score could not have been Supported at L1 for either model, and at L2 only for Opus.

At L3 a perfect model could gain 96 points. So the line rests there: Opus's interval ends at 2.95 against a margin of 3; Haiku's at 2.36.

---

## Slide 19: Is it the model? On 8 rows Gemini 3.8 Flash scored above Claude, and still below the prior (about 37 s)

Exploratory. October's saved guesses from Gemini 3.8 Flash cover eight rows. On those rows at L2, Gemini scores 91.3%, against DeepSeek 73.9%, Haiku 70.5%, Opus 69.6% and random guesses 65.4%; the prior scores 98.8%. At L3, 13.8% against 7.6, 7.8, 5.6 and 2.3.

Limits: eight rows, three clusters, 29 members, chosen in October, and not the paper's Gemini 2.5 Pro. That model is no longer offered to new users. A registered replay of Gemini 3.8 Flash on new rows is running.

---

## Slide 20: Paper's room test: ahead of random guesses; p is 0.125 on the §11 count (about 45 s)

The paper reports 9 of 28 rooms, with no chance rate. Exploratory, DeepSeek's live runs, by the count in registration §11: DeepSeek predicts 10 of 59 rooms, random guesses 6 of 69: 16.9% against 8.7%, p 0.125. On all stages, 13 of 59, 22.0%, p 0.040. Our filter arm, also built from DeepSeek's guesses, is not ahead of random guesses: 2.9% and 10.1%, p 0.290 and 1.000. The 8-member count gives DeepSeek fewer stages, so chances are unequal.

Opus, replayed: 16.7% of its rooms land in a fitting unobserved region, against 2.7% for random guesses; p 0.016, one contrast, not adjusted.

---

## Slide 21: M2 varied place, not meaning: moved true objects show no detectable gain (about 45 s)

M2 varied place, not meaning. Offline, on 384 stages from 24 runs, we correlate ASP's view score with the unmapped objects in view.

True objects give 0.284, random guesses 0.065: a gap of 0.218, and half is 0.109. True objects moved by a model's error give 0.036 to 0.060: no detectable gain over random guesses. No arm reaches half.

All true objects gives 0.048. Exploratory readout: with identical members, the score reads mainly where the two observed maps disagree. That arm's gain never passes 2.0 bits, like the no-guess arm's, and the two correlate at 0.64. Not shown sufficient; yardstick provisional.

---

## Slide 22: What this talk cannot show (about 33 s)

Every result holds for homes 853 and 871 only. Part 1's live model is small, DeepSeek V4.1 Flash at low effort, which the paper doubts; so that null is about ASP with a cheap model.

Truth is a proxy: human labels. The replays are static. The paper used Gemini 2.5 Pro, no longer offered to new users; we used Claude, in our port of the author's loop. A Claude result does not speak for Gemini.

---

## Slide 23: How the test was made (about 22 s)

We wrote the scorer after we saw DeepSeek's numbers, and froze it before Claude. We set the L3 margin knowing the Gemini–DeepSeek gap. We did not check the comparators' own scores before the freeze. M2 is provisional. One Haiku member stopped at the token limit; 175 of 176 parsed.

---

## Slide 24: For Claude, in our port, on saved inputs: no detectable gain over base rates (about 48 s)

For Claude, in two houses: no detectable information beyond house base rates, and content in fitting regions not detectably more often than a trade of regions; gains under 3 points are not ruled out.

The registered line comes second: the claim fails, for the first half of the claim as the author put it to us. It says less than it seems to: at L1 no model could have been Supported, and at L2 only a perfect Opus, so it rests on L3, where Opus's interval ends at 2.95 against a margin of 3.

Gemini 3.8 Flash scored above Claude on eight rows, though below the prior.

---

## Slide 25: What the answer does not say (about 37 s)

It does not say the guesses carry nothing: no gain was found, and at L3 a gain under 3 points is not ruled out. It does not say the models are no better than random guesses: Haiku is 8.2 points above them at L2. It does not say the model is not the cause: Gemini 3.8 Flash scored above Claude on eight rows, though below the prior. And it does not show that a language model cannot help exploration. Thank you.

---

## Backup 1: The wrong-house check (not timed)

The wrong-house check scores the model's guesses for the other home against this home. Guesses that fit this house should beat them.

No model passes. A pass needs p below 0.05 over six pairs. The best is Opus at L1, 0.125. Gemini's eight rows have no partner.

---

## Backup 2: How far a guess is from an object it could name (not timed)

This is the input to M2's moved arms, not a claim about where guesses sit. For each source, the median distance from a guess to the nearest unseen object it could name: Gemini 5.8 metres, exploratory, on eight inputs; Haiku 7.1; DeepSeek 7.7, exploratory; Opus 8.1; random guesses 8.9.

The nearest object of a class is a minimum, and guesses with no such object are left out: for Opus, 800 of 1,348 are used.

---

## Backup 3: The paper's room test: other counts, Claude replays, prompt hint (not timed)

The paper reports 9 of 28 rooms. A room counts if at least two of eight members place a room within 2.5 metres of its centre before the robot sees the region.

On DeepSeek's live October runs, exploratory, with no type match, DeepSeek predicts 52 of 59 rooms on all stages; random guesses 40 of 69. On the Claude replays, one of four members, type matched: Opus 11 of 171 rooms, Haiku 2, DeepSeek 11, random 8.

The prompt hint, run after the result, deviation 56: Haiku without the sentence made 12 room claims and 11 hit; with it, 9 claims and 5 hit. Object claims: 150 of 230 without, 146 of 219 with. Small counts; exploratory.

---

## Backup 4: Do the filter and the vote keep right guesses? (not timed)

Our filter removes 8.5% of Opus's guesses, 20.2% of Haiku's, 32.0% of DeepSeek's and 68.9% of random guesses. At L3, kept and removed guesses show no detectable difference for Haiku, DeepSeek and random guesses. For Opus the interval is too wide to read.

---

## Backup 5: Why does ASP not gain from all true objects? (not timed)

The likely question: if every member holds every true object, why does ASP's score not rise? All true objects for every member scored minus 0.017, from minus 0.031 to minus 0.004, against random guesses. True objects in differing subsets scored plus 0.218 above them.

The score counts disagreement between members. We registered that before the run. The saved arrays, exploratory: with identical members the score reads mainly where the two observed maps disagree. This arm's gain never passes 2.0 bits over 384 stages, like the no-guess arm's, where other arms reach 4.75 to 5.5. The two correlate at 0.64 over 382 stages. The gain is zero for every candidate in only 2 of 384 stages.

---

## Backup 6: The four outcomes, and the rule that picked one (not timed)

The four pre-written outcomes: holds, mixed, fails, inconclusive. The rows apply in this order. Holds needs a Claude model Supported at L3: neither is. Mixed needs one Supported at L1 or L2 that passes the wrong-house check: none is. Fails needs every Claude model Rejected at L2 and L3: both are. So the line is: the claim fails.
