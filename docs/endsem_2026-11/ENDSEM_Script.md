# Speaker script: end-sem (27 slides and 6 backup, about 15 minutes)

About 2,034 words for the 27 slides, no slide above 2.3 words a second; the times in the slide headings add to 900 s. *Italics* in parentheses are stage directions; the builder drops them from the notes. Every number comes from the result files; `SOURCES.md` names the file and the path. Part 3 is filled from `slots.json`, which `fill_slots_part3.py` writes from the result files. Anything not registered is called exploratory on its slide.

---

## Slide 1: Right in meaning, wrong in place? (about 28 s)

ASP asks a language model to guess the rooms and objects a robot has not seen. As the author put it to us, the guesses are often wrong in place but name the right things, and that is enough. We test that in three parts.

Registered scores and tests are final, both Gemini replays included. Two control runs are registered, running, and not shown.

---

## Slide 2: The proposal's question was measured in part (about 33 s)

The proposal asked: can validating and calibrating the guesses cut false detours without cutting discovery of rooms?

We measured our validator, live, in two homes: minus 0.003, from minus 0.047 to plus 0.037. No detectable difference; the test could see only gains of 0.044 or more.

We did not measure detours or collisions, and calibration was retired.

September's claim is withdrawn: the filter kept 19 of 8,943 guesses, so the gain came from deleting them.

---

## Slide 3: ASP scores views by disagreement, not by truth (about 26 s)

The model guesses what lies beyond the mapped part: eight graphs, in two tracks of four. ASP scores each candidate view by how far the graphs differ about it.

No term asks whether a guess is true. If all eight graphs agree, the gain is zero; the two tracks start from different observed maps, so it rarely is.

---

## Slide 4: Live test: no detectable difference (about 32 s)

Two homes, human labels.

LLM guesses against random guesses: plus 0.013, from minus 0.012 to plus 0.040. All five: no detectable difference. Cautions: exact objects stand on one house; frontier stopped more often on 871 and almost never crossed wall cells.

The live model is small: DeepSeek V4.1 Flash at low effort. The paper says such models do not give consistent enough performance. So this null is about ASP with a cheap model.

---

## Slide 5: Why: swapping the guesses barely moves the pick (about 24 s)

Exploratory replay of saved stages.

Swap the LLM's guesses for a random set, and the top view moves 2.28 metres. Swap one random set for another, 2.19.

The LLM's guesses rank views a little better: plus 0.07, in 73 of 119 stages. They do not move the pick more than a redraw does.

---

## Slide 6: Near a real object, but rarely close (about 18 s)

Within half a metre of a real object with the same name: 3.0% of the LLM's new objects, against 0.5% of random ones; within two metres, 23.8% against 6.3%.

Still, 97% of its objects miss by more than half a metre.

---

## Slide 7: Live test limits: what it could not rule out (about 31 s)

First, the interval reaches plus 0.040; the test saw only gains of 0.024 to 0.028 or more. Second, the placebo differed in pacing in all five pairs, and members agreed on 29.4% of the LLM's guesses against 4.4% of random ones. Third, F1 at 60 metres favours the LLM: plus 0.043, p 0.015, or 0.09 after correction.

Our filter: no detectable difference. That is not proof of no effect.

---

## Slide 8: Same rules as the paper (about 23 s)

Part 2. We score with the author's F1 and GED code, on the paper's time axis, against a scripted stand-in for the hand-driven tour.

The paper gives no budget. We use the median end of our frontier runs: 632 seconds on 853, 1300 on 871. So 871's budget is about twice 853's.

---

## Slide 9: By the clock ASP reads above frontier; by the metre the sign depends on the reference (about 37 s)

By the clock, registered: November's three ASP runs sit above our five frontier runs at 10%, 50% and 100%, by 4.8, 11.6 and 6.0 points, against the paper's 15.8, 14.3 and 7.9. October's two runs trailed by 0.8 at 50%; the batches differ by 12.4.

By the metre, exploratory: at 50 metres ASP is 0.8 ahead under the scripted reference and 1.9 behind under the human labels. At 100 metres, 3.8 ahead and 1.6 behind.

One home: not a test of the paper's claim.

---

## Slide 10: How close we are to the paper on 871 depends on the budget (about 39 s)

At our budget, 1300 seconds, ours are 1.3 to 3.5 points above the paper's. But that budget is twice 853's. The paper says a run has 25 to 30 steps, which suggests a shorter budget; that is our inference. At 750 seconds our frontier is 2.9 to 12.1 points below the paper's.

At 50 metres, exploratory: exact objects 57.8, ASP 52.6, November's frontier 49.2, random guesses 42.1, October's frontier 36.3. The two frontier batches differ by 12.9, more than ASP differs from either November's frontier or random guesses.

---

## Slide 11: The reference is rebuilt, and it moves (about 27 s)

The repeat tour is not frozen in either home: the two tours agree at F1 0.751 on 853 and 0.771 on 871, below the 0.90 line, so the reference moves by more than the paper's margins.

Its floor area, 208 and 235 square metres, is 2.7 and 4.0 times our walkable floor. We do not know how the paper measured area.

---

## Slide 12: What limits the runs (about 33 s)

October's ASP runs stop at 60 metres, November's go to 105; two of three reach the full budget. At half the budget they score 38.7 and 51.1, a gap as large as ASP's lead over frontier.

The clocks differ. In the authors' code, frontier's clock starts when planning ends, before the path arrives, so it counts the wait; ASP's starts as the robot moves. On 853 ASP logs 5.8 seconds a metre against frontier's 7.0.

---

## Slide 13: The author's claim, in three questions (about 35 s)

As the author put it to us, the guesses are often wrong in place but right in meaning, and that is enough. It is not in the paper; it comes from the author's demo and what they told the student.

Is the meaning right? Is it enough for ASP? We give ASP true labels, moved by real error. Is it the model? We replay Claude on 44 saved inputs, and two Gemini models on 36 and 12 of them.

---

## Slide 14: A hit and a miss, on one real stage (about 19 s)

One real stage, with two saved guesses from one Opus member: a bed that hits, a toilet that misses.

L1: which rooms. L2: which objects. L3: roughly where: the guess must reach an unobserved region that fits it, inside the dashed line.

---

## Slide 15: What each guess is compared with (about 26 s)

A control sees the same map. The margin is the gain over it we would still count: 5 points at L1 and L2, 3 at L3. Named: the prior at L1 and L2, the region trade at L3.

We did not check what the comparators score before the freeze; the power check asked only whether Rejected was within reach.

---

## Slide 16: Naming: no detectable gain over base rates, below them at L2. Placing: none over a region trade (about 42 s)

Each cell: model minus comparator, in points, then the two scores.

At L1, Opus scores 85.4% and the prior 91.2%; Haiku 89.6% and 100%. At L2, Opus 58.3% against 93.4%; Haiku 68.8% against 93.7%: detectably below. At L3 the intervals end at plus 2.95 points for Opus and 2.4 for Haiku, under the 3-point margin.

The registered line is: the claim fails. It says less than it seems to. All six are Rejected, but at L1 no model could have been Supported, and at L2 only a perfect Opus could, so it rests on L3.

---

## Slide 17: Two facts that cut against the registered line (about 24 s)

Opus at L3 is close: the top of its interval is 2.95 points, the margin 3. After the result the checker reran the region trade fifteen times, deviation 55: the top ran from 2.83 to 2.98, below 3 every time.

Haiku at L2 is 8.2 points above random guesses, p 0.014: one contrast, not adjusted.

---

## Slide 18: What a perfect score could have shown: a ceiling at L1 and L2 (about 32 s)

Exploratory. The prior scores 91.2% on Opus's L1 rows and 100% on Haiku's; at L2, 93.4% and 93.7%.

Its best p after Holm: 0.750 and 1.000 at L1; 0.047 and 0.188 at L2. So a perfect score could not have been Supported at L1 for either model, and at L2 only for Opus.

So the line rests on L3: Opus's interval ends at 2.95 against a margin of 3; Haiku's at 2.36.

---

## Slide 19: Is it the model? In the author's loop Gemini 3.8 Flash scored above Claude (about 48 s)

Gemini 3.8 Flash, in the author's own loop, on the 36 inputs Claude saw: four members each, 137 of 144 parsed. The paper's Gemini 2.5 Pro is no longer offered to new users.

Gemini minus Opus at L2: plus 21.0 points, from plus 13.5 to plus 28.8, Holm p 0.0010. At L3: plus 2.7, from minus 0.3 to plus 5.8, p 0.0381, found under the registered one-sided test. Minus Haiku: plus 10.9 at L2, plus 3.1 at L3. All four found, 12 clusters. So the Claude result does not carry over. Gemini ran the author's loop and Claude our port, so model and loop come together. Not the paper's model.

---

## Slide 20: At L3 Gemini 3.8 Flash is above Claude, but not above a trade of regions (about 58 s)

The registered rule at L3 reads Rejected. Gemini scores 7.5%, below all three controls: 8.5%, 8.7% for the trade, 11.0%. Its interval against the trade ends at plus 1.4, under the margin of 3. Both hold: Gemini reaches fitting regions more often than Claude, 7.5% against 4.8% and 4.4%, yet no more often than a trade gives for its own guesses. Its lead is in the raw rate; it does not show its labels fit their regions; against Opus the interval includes zero.

Exploratory: at L2 Gemini scores 78.3%, below the prior's 90.7%, about 12 points, though the prior makes as many claims, and above random guesses' 59.6%. It passes the wrong-house check at L1 and L2. Gemini also made more guesses per member; 5a does not adjust for that.

---

## Slide 21: Gemini 4 Argon is above Opus at L2, and not detectably above Claude elsewhere (about 53 s)

Gemini 4 Argon, the top model on Google's price page on 19 November, in the author's loop, on the 12 round-1 inputs: four members each, 48 of 48 parsed. Registered after the Flash result was seen. Not the paper's model.

Argon minus Opus at L2: plus 17.5 points, from plus 5.0 to plus 30.3, Holm p 0.0205: above. The other three are not detectably above. The rule at L3 reads Inconclusive: Argon minus the trade 0.0, from minus 2.8 to plus 3.1, against a margin of 3. Argon scores 6.2%, beside 5.7, 6.2 and 6.6.

Exploratory: Argon minus Flash is minus 2.9 at L2 and minus 5.4 at L3, both holding zero. 12 clusters of one row each: wide intervals.

---

## Slide 22: Paper's room test: ahead of random guesses; p is 0.125 on the §11 count (about 42 s)

The paper reports 9 of 28 rooms, with no chance rate. Exploratory, DeepSeek's live runs, by the count in registration §11: it predicts 10 of 59 rooms, random guesses 6 of 69: 16.9% against 8.7%, p 0.125. On all stages, 13 of 59, 22.0%, p 0.040. Our filter arm, also built from DeepSeek's guesses, is not ahead: 2.9% and 10.1%, p 0.290 and 1.000. The 8-member count gives DeepSeek fewer stages, so chances are unequal.

Opus, replayed: 16.7% of its rooms land in a fitting unobserved region, against 2.7% for random guesses; p 0.016, unadjusted.

---

## Slide 23: M2 varied place, not meaning: moved true objects show no detectable gain (about 35 s)

M2 varied place, not meaning.

True objects give 0.284, random guesses 0.065: a gap of 0.218, and half is 0.109. Moved by a model's error they give 0.036 to 0.060: no detectable gain over random guesses. No arm reaches half.

All true objects gives 0.048. Exploratory readout: with identical members, the score reads mainly where the two observed maps disagree. That arm's gain never passes 2.0 bits, like the no-guess arm's, and the two correlate at 0.64. Not shown sufficient.

---

## Slide 24: What this talk cannot show (about 29 s)

Every result holds for homes 853 and 871 only. Part 1's model is small.

Truth is a proxy. The replays are static. The paper used Gemini 2.5 Pro, no longer offered to new users; we ran Claude in our port of the author's loop and Gemini 3.8 Flash in the author's own. Neither is the paper's model. Argon was added after the Flash result was seen.

---

## Slide 25: How the test was made (about 22 s)

We wrote the scorer after we saw DeepSeek's numbers, and froze it before Claude. We set the L3 margin knowing the Gemini–DeepSeek gap. We did not check the comparators' own scores before the freeze. M2 is provisional. One Haiku member stopped at the token limit; 175 of 176 parsed.

---

## Slide 26: For Claude, in our port, on saved inputs: no detectable gain over base rates (about 49 s)

For Claude, in two houses: no detectable information beyond house base rates, and content in fitting regions not detectably more often than a trade of regions; gains under 3 points are not ruled out.

The registered line comes second: the claim fails, for the first half of the claim as the author put it to us. It says less than it seems to: at L1 no model could have been Supported, and at L2 only a perfect Opus, so it rests on L3.

Two Gemini models scored above Opus at L2. Neither was found to beat a trade of regions at L3: Flash Rejected, Argon Inconclusive. Neither is the paper's model.

---

## Slide 27: What the answer does not say (about 35 s)

It does not say the guesses carry nothing: no gain was found, and at L3 a gain under 3 points is not ruled out. It does not say the models are no better than random guesses: Haiku is 8.2 points above them at L2. It does not carry over to Gemini 3.8 Flash or, at L2, to Gemini 4 Argon; neither is the paper's model. And it does not show that a language model cannot help exploration. Thank you.

---

## Backup 1: The wrong-house check (not timed)

The wrong-house check scores the model's guesses for the other home against this home. Guesses that fit this house should beat them.

No Claude model passes. A pass needs p below 0.05 over six pairs. The best is Opus at L1, 0.125. Gemini 3.8 Flash, in the replay, passes at L1, 0.031, and at L2, 0.016. October's eight rows had no partner.

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
