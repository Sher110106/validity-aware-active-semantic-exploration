# Speaker script: end-sem (19 slides and 17 backup, about 15 minutes)

About 1,755 words for the 19 slides, 117 words a minute; the times in the slide headings add to 900 s. *Italics* in parentheses are stage directions; the builder drops them from the notes. Every number comes from the result files; `SOURCES.md` names the file and the path. Part 3 is filled from `slots.json`, which `fill_slots_part3.py` writes from the result files. Anything not registered is called exploratory on its slide. Slides that moved to the backup keep their text here, in the order the builder puts them.

---

## Slide 1: Right in meaning, wrong in place? (about 57 s)

ASP asks a language model to guess the rooms and objects a robot has not seen. As the author put it to us, the guesses are often wrong in place but name the right things, and that is enough. We test that in three parts.

Part 1, live, with a small model: no detectable difference; a gain up to 0.04 F1 is not ruled out. Part 2, on 853: ASP leads frontier by the clock, not clearly by distance. Part 3, on saved inputs: no model was found to beat a trade of regions; a prior from 179 other houses named objects better. Two control runs are registered, running, and not shown.

---

## Slide 2: The proposal's question was measured in part (about 38 s)

The proposal asked: can validating and calibrating the guesses cut false detours without cutting discovery of rooms?

We measured our validator, live, in two homes: minus 0.003, from minus 0.047 to plus 0.037. No detectable difference; the test could see only gains of 0.044 or more.

We did not measure detours or collisions, and calibration was retired.

September's claim is withdrawn: the filter kept 19 of 8,943 guesses, so the gain came from deleting them.

---

## Slide 3: ASP scores views by disagreement, not by truth (about 30 s)

The model guesses what lies beyond the mapped part: eight graphs, in two tracks of four. ASP scores each candidate view by how far the graphs differ about it.

No term asks whether a guess is true. If all eight graphs agree, the gain is zero; the two tracks start from different observed maps, so it rarely is.

---

## Slide 4: Live test: no detectable difference (about 45 s)

Live runs in two homes, scored against human labels. LLM guesses against random guesses: plus 0.013, from minus 0.012 to plus 0.040. The other four contrasts on the slide read the same way: no detectable difference. Cautions: exact objects stand on one house; frontier stopped more often on 871 and almost never crossed wall cells.

The live model is small: DeepSeek V4.1 Flash at low effort. The paper says such models do not give consistent enough performance. So this null is about ASP with a cheap model.

---

## Slide 5: Why: swapping the guesses barely moves the pick (about 28 s)

An exploratory replay of saved stages. Swap the LLM's guesses for a random set, and the top view moves 2.28 metres; swap one random set for another, 2.19. The LLM's guesses rank views a little better, plus 0.07 in 73 of 119 stages, but do not move the pick more than a redraw does.

---

## Slide 6: Live test limits: what it could not rule out (about 49 s)

First, the interval reaches plus 0.040; the test saw only gains of 0.024 to 0.028 or more. Second, the placebo differed in pacing in all five pairs, and members agreed on 29.4% of the LLM's guesses against 4.4% of random ones. Third, F1 at 60 metres favours the LLM: plus 0.043, p 0.015, or 0.09 after correction.

Our filter: no detectable difference. That is not proof of no effect. The LLM's new objects land within half a metre of a real one 3.0% of the time, random guesses 0.5%; 97% miss by more than that.

---

## Slide 7: By the clock ASP reads above frontier; by the metre the sign depends on the reference (about 69 s)

Part 2. We score with the author's F1 and GED code, on the paper's time axis, against a scripted stand-in for the hand-driven tour. The paper gives no budget; we use the median end of our frontier runs, 632 seconds on 853.

By the clock, registered: November's three ASP runs sit above our five frontier runs at 10%, 50% and 100%, by 4.8, 11.6 and 6.0 points. October's two runs trailed by 0.8 at 50%; the batches differ by 12.4. By the metre, exploratory: at 50 metres ASP is 0.8 ahead under the scripted reference and 1.9 behind under the human labels. At 100 metres, 3.8 ahead and 1.6 behind.

The paper's own 853 values moved between versions: frontier 48.3 to 58.8, ASP 59.0 to 66.7. One home: not a test of the paper's claim.

---

## Slide 8: How close we are to the paper on 871 depends on the budget (about 33 s)

At our budget, 1300 seconds, ours are 1.3 to 3.5 points above the paper's. But that budget is twice 853's. The paper's 25 to 30 steps a run suggest a shorter budget; our inference. At 750 seconds our frontier is 2.9 to 12.1 points below the paper's.

At 50 metres, exploratory, the two frontier batches differ by 12.9, more than ASP differs from either.

---

## Slide 9: What limits the runs (about 44 s)

October's ASP runs stop at 60 metres, November's go to 105; two of three reach the full budget. The clocks differ. In the authors' code, frontier's clock starts when planning ends, before the path arrives, so it counts the wait; ASP's starts as the robot moves. On 853 ASP logs 5.8 seconds a metre against frontier's 7.0. The reference moves too: the two tours agree at F1 0.751 on 853 and 0.771 on 871, below the 0.90 line, so by more than the paper's margins.

---

## Slide 10: The author's claim, in three questions (about 43 s)

As the author put it to us, the guesses are often wrong in place but right in meaning, and that is enough. It is not in the paper; it comes from the author's demo and what they told the student.

Is the meaning right? Is it enough for ASP? We give ASP true labels, moved by real error. Is it the model? We replay Claude on 44 saved inputs, and three Gemini models on up to 36 of them. The scorer was frozen first.

---

## Slide 11: What each guess is compared with (about 32 s)

A control sees the same map. The margin is the gain over it we would still count: 5 points at L1 and L2, 3 at L3. Named: the prior from 179 other houses at L1 and L2, the region trade at L3.

We did not check what the comparators score before the freeze; the power check asked only whether Rejected was within reach.

---

## Slide 12: Naming: no detectable gain over the other-house prior, and below it at L2. Placing: none over a region trade (about 51 s)

Each cell is the model minus the named comparator, in points. At L1, Opus scores 85.4% and the prior 91.2%; Haiku 89.6% and 100%. At L2, Opus 58.3% against 93.4%; Haiku 68.8% against 93.7%: detectably below. At L3 the intervals end at plus 2.95 points for Opus and 2.4 for Haiku, under the 3-point margin; fifteen reruns after the result kept Opus's top between 2.83 and 2.98.

The registered line is: the claim fails. All six are Rejected, but at L1 no model could have been Supported, and at L2 only a perfect Opus could, so it rests on L3.

---

## Slide 13: Is it the model? In the author's loop Gemini 3.8 Flash scored above Claude (about 58 s)

Registered replay: Gemini 3.8 Flash, in the author's own loop, on the 36 inputs Claude saw: 137 of 144 members parsed. The paper's Gemini 2.5 Pro is no longer offered to new users.

Gemini minus Opus at L2: plus 21.0 points, from plus 13.5 to plus 28.8; at L3 plus 2.7, from minus 0.3 to plus 5.8, found under the registered one-sided test. Minus Haiku: plus 10.9 and plus 3.1. All four found. So the Claude result does not carry over. But Gemini ran the author's loop and Claude our port: model and loop come together. And Gemini made more guesses per member; 5a does not adjust for that. Not the paper's model.

---

## Slide 14: At L3 Gemini 3.8 Flash is above Claude, but not above a trade of regions (about 32 s)

The registered rule at L3 reads Rejected. Gemini scores 7.5%, below all three controls: 8.5%, 8.7% for the trade, 11.0%; its interval against the trade ends at plus 1.4, under the margin of 3. Gemini beats Claude's 4.8% and 4.4% in raw rate, but not the trade's 8.7% for its own guesses. Its lead does not show its labels fit their regions.

---

## Slide 15: Three Gemini models: at L3 none was found to beat a trade of regions (about 55 s)

Three Gemini models were tried in turn (3.8 Flash, 4 Argon, 4 Neon), each chosen after the last result was seen. All three are reported; they are not three independent confirmations, and none is the paper's model.

At L2 Flash was above both Claude models; Argon above Opus only; for Neon no verdict was registered. At L3 no Gemini model was found to beat a trade of regions by the margin: Flash Rejected; Argon Inconclusive, then Rejected; Neon Inconclusive. Neon, the student's choice for the last run, was registered after the Flash result and Argon's round-1 result were seen, while Argon's second run was under way and unscored.

---

## Slide 16: DeepSeek ahead of random guesses in count; not detectable on the rule of §11 (p 0.125) (about 44 s)

DeepSeek's live runs, exploratory, by the count in registration §11: it predicts 10 of 59 rooms, random guesses 6 of 69: 16.9% against 8.7%, p 0.125, not detectable. On all stages, 13 of 59, 22.0%, p 0.040. Our filter arm, built from the same guesses, is not ahead: 2.9% and 10.1%, p 0.290 and 1.000. Opus, replayed: 16.7% of rooms in a fitting region, against 2.7% for random guesses; p 0.016, unadjusted. The paper reports a count with no chance rate; random guesses give one.

---

## Slide 17: What this talk cannot show, and how the test was made (about 55 s)

Every result holds for two homes only, and Part 1's model is small. Truth is a proxy and the replays are static: no robot acted on Claude's or Gemini's guesses. The paper used Gemini 2.5 Pro, no longer offered to new users. We ran Claude in our port of the author's loop and all three Gemini models in the author's own, so each Gemini-Claude contrast has two differences. We wrote the scorer after seeing DeepSeek's numbers, set the L3 margin knowing the Gemini-DeepSeek gap, and did not check the comparators' own scores before the freeze. M2 is provisional. Not done: a live run with a strong model.

---

## Slide 18: For Claude, in our port, on saved inputs: no better than a prior from other houses (about 62 s)

For Claude, in two houses: it named rooms and objects no better than a prior from 179 other houses, worse at objects, and put its guesses in fitting regions no more often than a trade of regions; a gain under 3 points is not ruled out. The registered line is: the claim fails, as the author put it to us. It says less than it seems to: at L1 no model could have been Supported, and at L2 only a perfect Opus, so it rests on L3. M2, offline: true objects moved by a model's error showed no detectable gain. No Gemini model is the paper's model. At L3 none was found to beat a trade of regions by the margin.

---

## Slide 19: What the talk found, and what it does not say (about 75 s)

Part 1: live, with a small model, ASP's guesses made no detectable difference to the map; a gain up to 0.04 F1 is not ruled out. Part 2: at the paper's scale on 853, ASP leads frontier by the clock but not clearly by distance. The control arms that would show whether the guesses cause that lead are registered and running. Part 3: on saved inputs, none of five models (two Claude, three Gemini) was found to put its guesses in fitting regions more often than a trade of regions, and a prior from 179 other houses named objects better than every one of them.

It does not say that the guesses carry nothing; that the models are no better than random guesses, since Haiku is 8.2 points above them at L2, one contrast, not adjusted, exploratory; or that a language model cannot help exploration. Thank you.

---

## Backup 1: The wrong-house check (not timed)

The wrong-house check scores the model's guesses for the other home against this home. Guesses that fit this house should beat them.

No Claude model passes. A pass needs p below 0.05 over six pairs. The best is Opus at L1, 0.125. Gemini 3.8 Flash passes at L1, 0.031, and at L2, 0.016; Gemini 4 Neon at L2 only, 0.016; Gemini 4 Argon at neither, in either run. October's eight rows had no partner.

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

---

## Backup 7: Gemini 4 Argon, round 1: above Opus at L2, not detectably above Claude elsewhere (not timed)

Gemini 4 Argon, the second of Google's Gemini 4 line, in the author's loop, on the 12 round-1 inputs: four members each, 48 of 48 parsed. Registered after the Flash result was seen. Not the paper's model.

Argon minus Opus at L2: plus 17.5 points, from plus 5.0 to plus 30.3: above. The other three are not detectably above. The rule at L3 reads Inconclusive: minus the trade 0.0, from minus 2.8 to plus 3.1, margin 3. Argon scores 6.2%, beside 5.7, 6.2 and 6.6. Twelve clusters of one row: wide intervals.

---

## Backup 8: On 24 new inputs Argon is again not detectably above Haiku at L2 (not timed)

Round 1 left Argon against Haiku at L2 at plus 13.6, interval from just below zero. Registered after that, a check on the 24 other stages of the same 12 runs: two members each, 48 of 48 parsed. Two questions were tested. Argon minus Haiku at L2: plus 5.4, from minus 2.8 to plus 13.5, one-sided p 0.0906: again not detectably above. The L3 rule reads Rejected, plus 0.4 from the trade, minus 2.1 to plus 2.8; round 1's was Inconclusive.

Exploratory, all 36 inputs, holding the 12 seen first: minus Haiku at L2 plus 8.1, minus Opus plus 18.3, minus Flash minus 2.7 and minus 2.1, holding zero. Not the paper's model. The registered fixed sentence for the rule on the new inputs: Gemini 4 Argon did not beat a trade of region contents by the 3-point margin. All three models ran the author's loop, but it behaved very differently: about four calls a member for Argon, 34 for Flash.

---

## Backup 9: Near a real object, but rarely close (not timed)

Within half a metre of a real object with the same name: 3.0% of the LLM's new objects, against 0.5% of random ones; within two metres, 23.8% against 6.3%.

Still, 97% of its objects miss by more than half a metre.

---

## Backup 10: Same rules as the paper (not timed)

Part 2. We score with the author's F1 and GED code, on the paper's time axis, against a scripted stand-in for the hand-driven tour.

The paper gives no budget. We use the median end of our frontier runs: 632 seconds on 853, 1300 on 871. So 871's budget is about twice 853's.

---

## Backup 11: The reference is rebuilt, and it moves (not timed)

The repeat tour is not frozen in either home: the two tours agree at F1 0.751 on 853 and 0.771 on 871, below the 0.90 line, so the reference moves by more than the paper's margins.

Its floor area, 208 and 235 square metres, is 2.7 and 4.0 times our walkable floor. We do not know how the paper measured area.

---

## Backup 12: A hit and a miss, on one real stage (not timed)

One real stage, with two saved guesses from one Opus member: a bed that hits, a toilet that misses.

L1: which rooms. L2: which objects. L3: roughly where: the guess must reach an unobserved region that fits it, inside the dashed line.

---

## Backup 13: Two facts that cut against the registered line (not timed)

Opus at L3 is close: the top of its interval is 2.95 points, the margin 3. After the result the checker reran the region trade fifteen times, deviation 55: the top ran from 2.83 to 2.98, below 3 every time.

Haiku at L2 is 8.2 points above random guesses, p 0.014: one contrast, not adjusted, exploratory.

---

## Backup 14: What a perfect score could have shown: a ceiling at L1 and L2 (not timed)

Exploratory. The prior scores 91.2% on Opus's L1 rows and 100% on Haiku's; at L2, 93.4% and 93.7%.

Its best p after Holm: 0.750 and 1.000 at L1; 0.047 and 0.188 at L2. So a perfect score could not have been Supported at L1 for either model, and at L2 only for Opus.

So the line rests on L3: Opus's interval ends at 2.95 against a margin of 3; Haiku's at 2.36.

---

## Backup 15: Gemini 4 Neon, the last run: Inconclusive at L3 (not timed)

Gemini 4 Neon, released on 18 November, the student's choice for the last run, in the author's loop, on rounds 1 and 3: 24 inputs, two members each, 48 of 48 parsed. Registered after the Flash result and Argon's round-1 result were seen, while Argon's second run was under way and unscored; one input was added so that round 3 was whole. Not the paper's model.

The one registered line, the rule at L3, is Inconclusive: Neon minus the trade plus 2.9 points, from minus 0.4 to plus 6.3, margin 3. It is not Supported: the prior's labels at Neon's own places score higher, minus 1.5, from minus 4.1 to plus 1.3. Neon scores 8.7%, beside 7.6, 5.7 and 10.2. Against Claude: reported, no verdict. Exploratory: at L2 Neon is below Flash, minus 10.1, and Argon, minus 7.3. The three models ran the author's loop, but it behaved very differently: about four calls a member for Argon, 34 for Flash.

---

## Backup 16: M2 varied place, not meaning: moved true objects show no detectable gain (not timed)

M2 varied place, not meaning.

True objects give 0.284, random guesses 0.065: a gap of 0.218, and half is 0.109. Moved by a model's error they give 0.036 to 0.060: no detectable gain over random guesses. No arm reaches half.

All true objects gives 0.048. Exploratory readout: with identical members, the score reads mainly where the two observed maps disagree. Its gain never passes 2.0 bits, like the no-guess arm's; they correlate at 0.64. Not shown sufficient.

---

## Backup 17: Gemini 3.8 Flash: the exploratory lines (not timed)

Exploratory: at L2 Gemini scores 78.3%, about 12 points below the prior, which makes as many claims, and above random guesses. It passes the wrong-house check at L1 and L2. Gemini also made more guesses per member; 5a does not adjust for that.
