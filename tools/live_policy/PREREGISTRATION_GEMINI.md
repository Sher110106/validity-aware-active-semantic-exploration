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
