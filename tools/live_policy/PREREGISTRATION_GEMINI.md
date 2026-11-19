# Pre-registration: the paper's own model on the frame rows

Filed 2026-11-19 11:57 IST, before any generation call of this replay. `PREREGISTRATION_SEMANTIC.md` stays as it is and keeps its hash; this file adds one model to that test, under the same frozen scorer. Section numbers with § point into that file.

## 1. Why

The semantic test answered for Claude. The paper's system used Gemini 2.5 Pro, and the author's config at f1ea141b still names it (`LLM_MODEL_NAME: "gemini-2.5-pro"`). In September the project recorded that model as withdrawn for our key, and has not tried it since. On 11-19 the public price page listed it, and a free call (`models.get`, no generation) showed that our key can see it. So the test can be put to the paper's own model, on the inputs Claude was given. An independent review of the whole project (11-19) asked for a Gemini replay, and the student approved it the same day, with whatever credit is left on the Gemini key.

## 2. What had been seen before the hash

- Every result in `results_semantic_1113/`: Claude Opus and Haiku on all 44 rows (confirmatory), and DeepSeek, the placebo and October's Gemini 3.8 Flash members (exploratory).
- On the 8 rows of round 4, where October's Gemini 3.8 Flash guesses exist (29 members of 32): at L2 Gemini 91.3%, Opus 69.6%, Haiku 70.5%, DeepSeek 73.9%, random guesses 65.4%; at L3 13.8%, 5.6%, 7.8%, 7.6%, 2.3%. On those rows the prior B3 scores 98.8% at L2. Gemini is above Opus in 7 of the 8 rows at L2.
- The comparators' own scores on the frame: B3 reaches 100% at L1 in nearly every row, and about 93% at L2 (100% in 37 to 39 of the 44 rows).
- No output of Gemini 2.5 Pro on any input of ours, ever. No output of any Gemini model on any row of rounds 1 to 3. No generation call of this replay.

## 3. Model, loop and inputs

- **Model:** `gemini-2.5-pro`. If the smoke test (§4) cannot get one member through on it because the model is refused or not served, the replay uses `gemini-3.8-flash`, the model of October's static test, and says so on the slide. No other change of model is made.
- **Loop:** the author's own `llm_completion.py` at f1ea141b, in the container, as October ran it: `LLMCompletion(model_name=…, user_prompt=…, seed=…)`, `generate_completion_response`, then `parse_response`. His settings stand (temperature 0.2, dynamic thinking, his tool and his feasibility check). The host's copy (md5 dc70801e…, the file E1 and October's Gemini test ran) differs from f1ea141b only in crash guards: a tool call with missing arguments gets an error reply instead of raising, and a reply with no fenced code block makes `parse_response` return false instead of raising. The request it sends is the author's. Member k of a row uses seed = the run's seed + k, as his pipeline does.
- **Inputs:** the folders exported for the Claude replays under §12 (`frame_inputs/<row_id>/`): his prompt, the observed graph of track 0 byte for byte, and the 6 slices. The tool checks each file's sha256 against the export's list before any call. Gemini sees the files Claude saw.
- **Members:** 4 per row. If 48 times the smoke test's mean cost per member is more than what is left of the cap after it, rows get 2 members (members 0 and 1) instead. A member is dropped, and counted, if the loop raises or its final text does not parse. No member is run again. A drop rate above 25% is flagged on the slide.
- **Retries.** A call that fails with HTTP 429 or a 5xx code is tried again after 60 s, up to 3 times, inside the cost meter, as the Claude replays retried transient errors (§12).
- **Tool:** `tools/live_policy/gemini_replay.py` (sha256 fd102a14602b2cd7…), with `gemini_replay_rows.txt` (sha256 e1d05b9c2345192a…).

## 4. Rows, order and money

- **Rows:** rounds 1, 3 and 2 of the frame (§12), in that order: stage 8 of the 12 runs, then stage 3, then stage 13. Stage 3 comes before stage 13 because its graphs are less than half the size and so cost least; the order is fixed before any output exists. Within a round the rows run seed by seed, and within a seed in the order 853 official, 871 filter, 871 official, 853 filter, so that a stop inside a round leaves the scenes and arms as even as it can. Round 4 is not run: October's members on it stay exploratory and enter no test here.
- **One row at a time,** its members together. The next row starts only when the cap leaves room for all its members at the cost of the dearest member so far.
- **Cap:** $122.00 for everything in this file, the smoke test included. It is what the project's ledgers leave of the $200 credit ($37.36 spent in September and $39.84 in October, both counted without the discount for cached tokens, so the true balance is no lower). The cap is checked in code before every call, from the usage the API reports, at the list prices read on 11-19 ($1.25 in, $0.125 cached and $10 out per million tokens for prompts up to 200,000 tokens; $2.50, $0.25 and $15 above; thoughts billed as output).
- **Smoke test first:** two members on one input outside the frame (`e1_00871_s44_official_60m` stage 17, from the Claude smoke set). It is scored for cost and plumbing only, and its cost per member sets the number of members (§3).
- **A stop.** The replay stops at once on HTTP 402, on any other reply that names prepaid credit or billing, and when one call has failed its third retry. It is not started again. A row cut short is left out and named.
- **Analysis set.** The confirmatory set is the rows of the whole rounds finished: every row of the round has all its members ended (ok or dropped). The finished rows of a round that did not finish are scored and reported as exploratory, apart.

## 5. Tests

Scores, truth, labels, comparators, the unit (the cluster) and the exact sign-flip test over clusters are those of §5 to §10, from the frozen scorer's own code. A wrapper outside the frozen folder (`semantic_gemini.py`) feeds it Gemini's members. No frozen file changes, the wrapper changes no state of the frozen modules, and `freeze.py check` must pass before scoring. The wrapper is committed, and its sha256 is appended to this file in a dated note, before any call on a frame row. A cluster's score is the mean over its rows in the confirmatory set.

**5a. Gemini in the author's loop against Claude in our port (confirmatory).** Gemini minus each Claude model, at L2 and at L3, on the rows of the confirmatory set where both have a score. The two differ in more than the model: Gemini runs the author's own loop (his seed, his temperature, his turn limit, default thinking); Claude ran our port of it (no seed, adaptive thinking, effort medium, 50 turns). One-sided (Gemini above), because October's exploratory rows point that way. Family: {Opus, Haiku} × {L2, L3}, four hypotheses, Holm, α = 0.05. Each is reported with its two-sided 95% interval. L1 is reported, not tested: every source is near 100% there.
- Reach. With n clusters the smallest p the test can give is 1 / 2^n, and Holm asks 0.0125 of the smallest of four. So 5a can find a difference only with 7 clusters or more. With fewer, 5a is reported as exploratory and no hypothesis is called.
- Gemini minus DeepSeek and Gemini minus random guesses (B1) are given the same way, outside the family.

**5b. The registered rule at L3, applied to the paper's model (confirmatory).** One hypothesis, α = 0.05: Gemini at L3 against B5, D and B3L, with §10's p (the largest over the three), §10's margin (3 points against D) and §10's verdict rule (Supported, Rejected, Inconclusive). It needs 5 clusters or more to find anything.
- L1 and L2 are scored by §10's rule too, and reported as exploratory, with the ceiling said beside them: B3 scores 100% at L1 in nearly every row, so "Supported" there is out of reach for any model; at L2 B3 scores about 93%, so "Supported" needs a score near 100%. L3 has no such ceiling: its comparators score 2% to 12%.
- No thesis line is drawn. §10's thesis is about the Claude models and stays as filed.
- Beside each line the slide gives the model's own score and each comparator's own score, and at L2 the contrast with random guesses (B1), which has no ceiling.

**5c. Reported, no verdict:** the wrong-house gate (§10) on the confirmatory set; every secondary line of §11 that the scorer writes; the paper's room count on these replays (1 of 4 and 2 of 4 members).

## 6. How the result may be worded

- 5a, Gemini above both Claude models at L2 and at L3: "The Claude result does not carry over to the paper's model: on the same inputs Gemini 2.5 Pro names more of what is there and puts more of it in fitting regions."
- 5a, no hypothesis found: "On the same inputs Gemini 2.5 Pro, in the author's loop, was not detectably above Claude", with the four intervals.
- Anything else: the four lines as they fall.
- 5b at L3, Supported: "Gemini 2.5 Pro puts its guesses in fitting regions more often than the controls." Rejected: "Gemini 2.5 Pro did not beat a trade of region contents by the 3-point margin." Inconclusive: said as such, with the interval.
- If the fallback model ran, every sentence names Gemini 3.8 Flash and says it is not the paper's model.
- Whatever the result: saved inputs from two homes; no robot acted on these guesses; the comparators at L1 and L2 sit at the ceiling.

## 7. Not done

No live Gemini run. No second Gemini model, unless the fallback of §3 applies. No replay of round 4. No change to the Claude results or to §10's thesis line.

## Note 1 (2026-11-19 12:00 IST, before any generation call has returned an output)

**The smoke test on `gemini-2.5-pro` was refused.** At 11:58:35 IST on 11-19 the first call of each of the two members came back with HTTP 404: "This model models/gemini-2.5-pro is no longer available to new users." No output was produced; the ledger charges the two calls at the reserve, $0.16 in all. `models.get` lists the model for our key, but the key may not generate with it. So §3's fallback applies: the replay runs on `gemini-3.8-flash`, and every sentence about its result names that model and says it is not the paper's.

**What follows from it, fixed here before any output exists.**
- The smoke test is run again on `gemini-3.8-flash`: the same input, two members. Its mean cost per member sets the number of members per row, as §3 says. The refused attempt's folder is kept under another name.
- Prices for the cap: $0.75 in, $0.075 cached and $3.75 out per million tokens (the public price page, read on 11-19).
- A fault of the set-up must not use up rows. As the tool stood, the 404 above would have marked every row done with all its members dropped. So a call that fails for a reason other than those of §3 and §4, before its member has had one good call, stops the replay. The fault is then fixed and the replay is started again, once for each such fault; rows already done are not run again, and the row in flight is run afresh.
- A timeout or a broken connection is retried like a 5xx reply, as §12 retried them for Claude.
- The tool is now `gemini_replay.py` with sha256 3ec7cbba60144604… (it was fd102a14602b2cd7…). The rows file is unchanged.
- The wrapper's hash follows in a second note, before any frame row is called.

## Note 2 (2026-11-19 12:17 IST, before any call on a frame row)

**The smoke test on `gemini-3.8-flash`.** It ran from 12:01 to 12:07 IST on 11-19: two members on the input outside the frame, both parsed, with 45 and 24 calls, at $0.41 and $0.31 (mean $0.36). The API billed 85% of the input at the cached price. 48 members at that mean come to $17.3, well under the $121.12 the cap leaves, so rows get 4 members (§3). The ledger stood at $0.88 when this note was written: the two refused calls at the reserve, and the smoke test. The smoke test's two graphs were read with the frozen reader to check that they load; nothing was scored.

**The wrapper.** `tools/live_policy/semantic_gemini.py`, sha256 4d6852e00715fac6fa8c3cc3421f4c0797c1092b5025fc2e4337a3c39a7ccc4b, with its tests in `tools/tests/test_semantic_gemini.py`. An independent review read it against §5 before this hash and found three faults, all fixed: the row list could be shortened after the scores were seen (it is now the committed rows file, checked by its sha256); the check of this registration took the file and its hash from the caller (it now checks this file against `PREREGISTRATION_GEMINI.sha256`); and a member whose graph cannot be read was left out of the drop rate (it now counts as dropped). Its tests show that it scores a member file exactly as the frozen code scored Claude's (16 rows, 64 members, 1,042 scores equal to the filed Haiku records) and that it reads the author's own output format as the frozen code does (29 of October's Gemini members).

**Points §5 left open, settled here before any frame row.**
- The exploratory lines at L1 and L2 (5b) are given unadjusted, each alone.
- A comparator's own score is taken on the rows it shares with Gemini.
- A member marked ok whose graph cannot be read counts as dropped.
- With fewer than 7 clusters, 5a gives its numbers and no sentence.
- The drop-rate flag of §3 is read on all rows run. Sentences of §6 are written for the confirmatory set only.

## Note 3: one more model on round 1 (2026-11-19 18:51 IST, after the Flash result was seen, before any call on the new model)

**Why.** The replay used $56.83 of the $122 cap, and the student's word was to use what credit is left on this question. The registered result is for Gemini 3.8 Flash, the small tier. The paper says of its own choice of model that "smaller, less expensive LLMs do not yet provide consistent enough performance" (section IV), and its model is closed to our key. `gemini-4-argon` is the top model on the public price page on 11-19 and is listed for our key, as Gemini 2.5 Pro was the top tier when the paper was written. So the same test is put to it, on round 1.

**What had been seen when this was written.** Everything in §2, and the whole Flash result (`results_semantic_1113/gemini_1119/`): above both Claude models at L2 and at L3; Rejected at L3 against the region trade; its own L3 score of 7.5% beside 8.5%, 8.7% and 11.0% for its three controls. No output of `gemini-4-argon` on any input of ours. §7 said that no second Gemini model would be run. This note changes that after a result was seen, and the slide says so.

**E1. What runs.**
- Model `gemini-4-argon`, with no fallback: if the smoke test cannot get a member through, nothing more is run.
- Loop, inputs, seeds, drops, retries and stops as in §3, §4 and Note 1.
- Rows: round 1 only, the 12 stage-8 rows, in the order of the rows file (`gemini_replay_rows_round1.txt`, sha256 5625603c06e1055a…).
- Smoke test first: two members on the same input outside the frame.
- Members: 4 a row if 48 times the smoke test's mean cost per member fits in what the cap leaves after it; 2 a row (members 0 and 1) if 24 times fits; otherwise it is not run.
- Cap: $65.00 for this extension, the smoke test included, on a ledger of its own. Prices read on 11-19: $2.00 in, $0.10 cached and $10.00 out per million tokens. The tool is `gemini_replay.py` with those prices added (sha256 cd332f07ed7f8d7b…); nothing else in it changed.

**E2. Tests.** The wrapper of Note 2, unchanged, scores it on an output folder of its own. The confirmatory set is round 1 if all 12 rows finish; if they do not, everything is exploratory.
- **E2a (confirmatory):** the new model minus Opus and minus Haiku, at L2 and at L3, exactly as 5a: four hypotheses, Holm, α = 0.05, one-sided, with intervals. A cluster has one row here.
- **E2b (confirmatory):** the registered rule at L3, exactly as 5b: one hypothesis.
- **Exploratory:** the new model minus Gemini 3.8 Flash on the same 12 rows at L2 and at L3. Both ran the author's loop, so this contrast is of the model alone; it is computed after the fact and marked so. L1 and L2 under §10's rule, with the ceiling said beside them.

**E3. Wording.** The sentences of §6 with the model's name; each says it is not the paper's model. The slide says that this extension was registered after the Flash result was seen.

## Note 4: the same model on the rows it has not seen (2026-11-19 20:54 IST, after round 1 of Note 3 was seen, before any call on these rows)

**Why.** On round 1, Gemini 4 Argon minus Haiku at L2 came out at +13.6 points with a 95% interval from -1.4 to +28.5: one-sided p 0.036 by itself, 0.107 after Holm over the four hypotheses of E2a. So the registered reading is "not detectably above", on 12 clusters of one row each. The student asked whether that reading is too cautious, since nearly all of the interval lies above zero. More rows answer that, and rounds 3 and 2 are rows this model has never been given. About $46 of the allotted credit is left.

**What had been seen when this was written.** Everything in Note 3, and the whole round-1 result of Gemini 4 Argon (`results_semantic_1113/gemini_argon_1119/`): above Opus at L2; not detectably above Opus at L3 or Haiku at L2 and L3; Inconclusive at L3 against the region trade (upper end +3.1 against a margin of 3); and, exploratory, not above Gemini 3.8 Flash. Also Gemini 3.8 Flash's scores on rounds 3 and 2, and Claude's. No output of Gemini 4 Argon on any row of rounds 3 or 2.

**Why this one contrast.** It is the only line of E2a that missed with most of its interval above zero. Opus at L2 was already found, and the two L3 lines sat within 1.2 points of zero. The contrast, the level, the rows and the stop rule are all fixed here before any new output, and the test uses new rows only.

**What to expect.** A smaller difference than round 1's. On rounds 3 and 2, Gemini 3.8 Flash minus Haiku at L2 was +8.1 points, and on round 1 Argon scored 2.9 points below Flash. An independent reviewer's simulation from the saved scores put the interval at about ±10 points if both rounds finish, and the chance of finding a true difference at about 0.85 if it is 13.6 points and about 0.5 if it is 8. (It was made for the design as drafted; with 2 members a row the interval may be somewhat wider.) With round 3 alone those chances fall to about 0.6 and 0.3.

**R1. What runs.** Model, loop, inputs, seeds, drops, retries and stops as in Note 3. Rows: rounds 3 and 2, the 24 rows, in the order of `gemini_replay_rows_r32.txt` (sha256 12bb1074e5a131a6…; rounds 3 then 2, rows as in `gemini_replay_rows.txt`), in a new folder with a ledger of its own. Members: 2 a row (members 0 and 1), about $21 by round 1's ledger, so that both rounds fit under the cap. Cap: $46.00, within the $46.38 that Note 3's cap leaves. If the cap still stops the run inside round 2, the whole-rounds rule of §4 applies and round 3 alone is the set.

**R2. Tests, on the new rows only.** Round 1 is left out of every confirmatory line here, because it was seen before this note. The wrapper of Note 2, unchanged, scores the new rows as a set of their own. R2a and R2b are separate questions, each at α = 0.05; the slide says that two were tested.
- **R2a (confirmatory, one hypothesis):** Gemini 4 Argon minus Haiku at L2, one-sided (Argon above), read from the wrapper's one-sided p for that line before Holm, with that line's interval. R2a ignores the wrapper's "found" column and its sentences for 5a, which apply Holm over four. Wording: p below 0.05, "On the 24 other stages of the same 12 runs Gemini 4 Argon named objects better than Haiku"; otherwise "On the 24 other stages of the same 12 runs Gemini 4 Argon was again not detectably above Haiku at naming objects", with the interval.
- **R2b (confirmatory, one hypothesis):** the registered rule at L3, as 5b, on the new rows.
- **Reported with intervals, no verdict:** the other three contrasts with Claude on the new rows.

**R3. All 36 rows together (exploratory).** So that Gemini 4 Argon can be set beside Gemini 3.8 Flash on the same 36 rows, `gemini_pair.py` contrasts them from the wrapper's records files (round 1 with 4 members a row, rounds 3 and 2 with 2), and Argon with each Claude model the same way. Every line of it is exploratory, because it holds the 12 rows seen before this note, and the slide says so. The wrapper is not run on the 36 rows together.

**R4. Wording.** As Note 3: each sentence names the model and says it is not the paper's. The slide says that round 1 came first and that this check was registered after it.

## Note 5: a correction of fact in Notes 3 and 4 (2026-11-19 20:56 IST, while the run of Note 4 is under way; no rule changes)

Notes 3 and 4 call `gemini-4-argon` "the top model on the public price page on 11-19". That is wrong. The page read at 11:44 that day was an old cached copy, in which Gemini 4 Argon was the only Gemini 4 model and was described as the flagship. A fresh read of the same page at 20:55 lists four Gemini 4 models and describes Gemini 4 Carbon as "our most capable reasoning model" and Gemini 4 Argon as "our efficient Gemini 4 frontier reasoning model", with "lower token spend per turn compared to Gemini 4 Carbon". Press reports of 18 and 19 November say that Carbon was released before that week and Gemini 4 Neon on 18 November.

So Gemini 4 Argon is not Google's top model. It is the second of the Gemini 4 line, at the same list price as Carbon ($2.00 in, $0.10 cached and $10.00 out per million tokens through 30 November; the fresh page confirms the prices the ledgers used, for Argon and for Gemini 3.8 Flash). The reason Note 3 gave for choosing it, "as Gemini 2.5 Pro was the top tier when the paper was written", therefore does not hold as written: the test was put to a strong current model one step below the top, not to the top one.

Nothing else changes. The model, rows, members, caps and tests of Notes 3 and 4 stand, and the run of Note 4 goes on. Every sentence on a slide or in a document that calls Gemini 4 Argon the top model is corrected to say what it is.

## Note 6: Gemini 4 Neon, the last run (2026-11-19 21:05 IST, before any call on this model)

**Why.** The student chose this model on 11-19 for the last run on what credit is left: Gemini 4 Neon was released on 18 November, and public benchmark reports of that week place it above Gemini 4 Argon. Our key lists it. Google's top model, Gemini 4 Carbon (Note 5), is not tried. §7 and Note 3 each said that no further model would be run, and each was overtaken; this time the money is gone.

**What had been seen when this was written.** Everything in Notes 1 to 5: the Gemini 3.8 Flash result on 36 rows and the Gemini 4 Argon result on round 1. The run of Note 4 (Argon on rounds 3 and 2) was under way, with 1 of 24 rows done, and none of its output had been scored. No output of Gemini 4 Neon on any input of ours. An independent design review of a draft of this note, made before the hash, changed the design; what it changed is said under N1 and N2.

**N1. What runs.**
- Model `gemini-4-neon`, with no fallback: if the smoke test cannot get a member through, nothing more is run. Note 1's rule on a fault of the set-up applies (stop, fix, start again once).
- Loop, inputs, seeds, drops, retries and stops as in §3, §4 and Note 1. It starts only after the run of Note 4 has ended.
- Smoke test first: two members on the input outside the frame.
- Rows: `gemini_replay_rows.txt` in its registered order (rounds 1, 3, 2), 2 members a row (members 0 and 1). The run goes on if 30 times the smoke test's mean cost per member fits in what the cap leaves after it (the 24 members of round 1, with room for the dearest); otherwise nothing more is run. The cap decides how far the run goes, and the whole-rounds rule of §4 fixes the confirmatory set. The draft had round 1 alone at 4 members if they fit. The reviewer's simulation from the saved scores showed that 4 members against 2 hardly narrow the interval (about ±5.2 against ±5.3 points at L3 on round 1), where a second round does (about ±3.1 with rounds 1 and 3). Rounds 3 and 2 alone would be tighter still, but Flash's scores on them were seen before this choice, so the registered order is kept.
- Cap: what the $122 leaves when the run of Note 4 has ended, to the dollar below: 122.00 less the ledger totals of Flash (56.83), Argon on round 1 (18.62) and Note 4's run. It is expected to be $26 to $34. It is a matter of money only: nothing of Note 4's scored output enters it. The run has a ledger of its own.
- Prices, from the price page read fresh on 11-19 at 20:55: $3.00 in, $0.15 cached and $15.00 out per million tokens. The tool is `gemini_replay.py`, sha256 87f70036bae3b8be… (it was cd332f07ed7f8d7b… in Notes 3 and 4, and the run of Note 4 uses that copy); the only change is one more line in the price table.
- Expected cost, from Argon's token use at Neon's prices: about $13 for round 1 and about $23 for rounds 1 and 3. All three rounds, about $40, will not fit.

**N2. Test.** The wrapper of Note 2, unchanged, on an output folder of its own.
- **N2 (confirmatory, one hypothesis, α = 0.05):** §10's rule at L3, as 5b, on the whole rounds finished. Flash has already shown that a Gemini model can score above Claude at L2 and L3; the open question is whether a stronger model beats the trade of regions. If round 1 does not finish, everything is exploratory.
- The wrapper's 5a table (the contrasts with Claude) is reported with its intervals and no verdict; its "found" column and its sentences for 5a are ignored.
- **Reach,** by the reviewer's simulation, rough: with rounds 1 and 3 the interval at L3 is about ±3 points. If Neon truly equals the region trade, "Rejected" comes out about half the time. "Supported" needs Neon above all three L3 controls: about 0.44 if it is 3 points above them and about 0.94 if 5. At L2 the interval against Haiku is about ±11 points, so L2 can confirm little.
- **Exploratory:** Neon minus Gemini 3.8 Flash and minus Gemini 4 Argon, at L2 and L3, on all the rows both models ran, by `gemini_pair.py` (all three ran the author's loop, so these contrasts are of the models alone). L1 and L2 under §10's rule, with the ceiling said beside them. The finished rows of a round that did not finish.

**N3. Wording.** The sentences of §6 for 5b with the model's name; each says it is not the paper's model. Fixed now, for the slide: "Three Gemini models were tried in turn (3.8 Flash, 4 Argon, 4 Neon), each chosen after the last result was seen. All three are reported; they are not three independent confirmations, and none is the paper's model." A "Supported" for Neon is also given against α = 0.05/3.

## Note 7: one row more for Gemini 4 Neon, so that round 3 is whole (2026-11-20 00:39 IST, before any output of Neon has been scored or read)

The run of Note 6 went from 23:08:44 on 11-19 to 00:38:01 on 11-20 and stopped at its cap, as the note said it would: $27.77 of $28.00 by its ledger, 23 rows done, 46 of 46 members parsed, no failed call. Round 1 is whole (12 rows). Round 3 is one row short: 11 of 12, and the row `e2_00853_s44_filter_st03` did not start because $0.23 could not cover it. By Note 6's rule the confirmatory set would be round 1 alone, and eleven finished rows would count for nothing in the test.

One more row is run: that row, 2 members, about $1, under a cap of $29.50 on the same ledger. This takes the ledgers under this registration to about $123, about $1 over the $122 allotted. The allotment was our own cautious estimate of what the key holds, and the student's word was to use what is left on it.

This is decided on money and row counts alone. When this note was written no output of Gemini 4 Neon had been scored or read by anyone: only the tool's log of costs and of whether members parsed. If the row finishes, round 3 is whole and Note 6's rule makes rounds 1 and 3 the confirmatory set. If it does not finish, the set is round 1 alone, and nothing further is run. Nothing else in Note 6 changes.
