# End-sem final plan (2026-11-13)

This is the working plan for the end-sem talk, *Right in meaning, wrong in place?* It replaces the dates in `ENDSEM_PLAN_2026-11-03.md` §7 and the cut list in its §8. The older file still defines the milestones (M0b, M1, M2, M3, M4) and the decision rules; this file says what we do, in what order, and what is cut.

How it was made: a draft plan on 11-13, then five independent Opus reviews of it (schedule, method, Claude backend and cost, host operations, examiner). §8 lists what each review changed.

## 1. How we work (the student's instructions, 11-13)

- Do the steps in dependency order, as fast as the work allows. The dates in the first draft were a ceiling, not a timetable.
- Each finished level gets an independent Opus review before the next level builds on it.
- Ask the student only for what needs them: the Claude key, spend, a push, a host run that could hurt other users.
- Another session watches tonight's rerun queue on tyrone. This plan uses its results and does not touch the queue.

## 2. Order rules that never bend

1. **Rerun rules before rerun results.** `PREREGISTRATION_PAPER.md` Amendment 2 was hashed on 11-13 at 17:54 IST, before any third e7 871 attempt started.
2. **The semantic pre-registration is hashed before any LLM-against-baseline number exists.** Until then, scorer code runs on synthetic data only.
3. **The scorer is frozen before Claude.** The scorer code, label map, truth files and M2 code are hashed and committed before any Claude output is scored. That hash gates M4. A later change is a deviation that shows both numbers.
4. **Paid runs have caps,** set in code and in the Console.
5. **No number reaches a slide without a `numbers.csv` row** and an independent recompute.

## 3. Work list

Status marks: `[ ]` open, `[~]` in progress, `[x]` done and reviewed.

### 3.1 Part 2: the paper's scale

- [x] Amendment 2 to `PREREGISTRATION_PAPER.md` (rerun rules, frozen-tour test, budget rule), reviewed by Opus; a Note corrects one statement and settles open cases (hashed 18:35, pushed before any 871 rerun).
- [x] `tools/live_policy/DEVIATIONS_NOVEMBER.md`, items 40 to 47 (more are added as they arise).
- [ ] When the queue ends: acceptance checks on all six runs (§4), and the folder map in deviation 46.
- [ ] Copy only YAML and stats files to the laptop (rsync include list, dry run first; never a DSG file).
- [ ] The author's GED on the host for the new runs.
- [ ] Rescore: budget by script as Amendment 2 A2.3 says, C2 written to file first, crashed rows pointed at the right folders, the 11-12 values for 871 marked superseded.
- [x] The C1 area table: navmesh island, HM3D labelled floor, waypoint grid, the paper's figure (`results_paper_compare_1113/c1_area_table.md`, deviation 59). The paper's figure is 2.7 and 4.0 times the navmesh island, and within 7% of the convex hull of all labelled geometry.
- [~] ASP on 853 to the full budget, behind the readiness check (§6). Approved 11-13. Rules set and reviewed: Amendment 3 (hashed 21:20) and its Note (hashed 21:37, deviation 58). Scoring code for its own row is written, reviewed by Opus and fixed (6fb5888); the checks made before each launch are a script (`host/e8_prelaunch_check.sh`). The runs wait for the GPU.

### 3.2 Part 3: the author's defense

**M0b, pre-registration**
- [x] Inventory of saved inputs and truth files (`semantic/DATA_INVENTORY.md`).
- [x] Host session: region footprints from the semantic mesh, the label summary of 181 annotated houses, and the 44 frame inputs plus 3 smoke inputs exported and copied (0 hash mismatches; slices byte-identical to October's Gemini inputs on 4 rows).
- [x] `PREREGISTRATION_SEMANTIC.md`: drafted, reviewed three times by Opus, hashed 11-13 18:59 IST (sha256 59c97ad6…) and pushed, before any model output was scored. It fixes:
  - truth: region types, the "seen" rule, the unobserved stratum for L3;
  - levels L1 to L3, the label normaliser and the synonym table;
  - comparators B1, B2, B3, B4, B5 and D, and how B3a or B3b is chosen;
  - the family, 2 Claude models × 3 levels, with Holm;
  - verdicts: "the claim holds" means Supported at L3 on the unobserved stratum; the rejection comparator is named; the detectable differences are recomputed;
  - the validity layer's settings and its five readouts, as secondaries;
  - the paper's room test with a chance rate;
  - the M4 round order and the cost addendum;
  - the full list of numbers already seen.
- [x] Opus review, then hash, commit and push (commit 49307ed).
- [x] Truth files, label table and frame hashed (`semantic/TRUTH.sha256`, pushed 20:12) before the first score.

**M1, the semantic test on saved data ($0)**
- [x] `tools/live_policy/semantic/`: labels, region truth, extraction, level scoring, comparators, statistics, the validity views, the room test and one driver (437 tests).
- [x] Tests on synthetic houses with known answers.
- [x] Opus review of the code against the pre-registration: a hand-computed toy house agreed on every number; one must-fix and six smaller items, all fixed.
- [x] Scorer freeze: `semantic/FREEZE.sha256`, committed and pushed 11-13 20:14 (04e6afc), before any Claude output was scored.
- [x] Run on the saved DeepSeek, Gemini and placebo guesses (`results_semantic_1113/exploratory/`). DeepSeek's verdicts are exploratory.
- [x] Opus recompute of the headline numbers with its own code, written from the rules without reading the scorer: reproduced (DeepSeek and both Claude models).

**M2, would right meaning be enough? ($0)**
- [x] Rebuild the bench from a copy and reproduce 9,600 of 9,600 picks (done on the laptop, `tools/live_policy/m2/`; the same on tyrone's CPUs is in progress).
- [x] The trimmed factorial on tyrone's CPUs: F1, F5, F6, F0, F-room, and F3 with DeepSeek's, Haiku's and Opus's measured errors (`results_m2_1113/`).
- [x] Opus review of the M2 rules (before the hash) and of the code (before the run). Every arm reads "not shown sufficient, on a provisional yardstick".

**M3, the Claude loop**
- [x] A direct port of the author's tool loop to the Anthropic SDK, with a test that it matches his loop on scripted replies; reviewed by Opus, fixed (62 tests). It runs on the laptop.
- [x] Meter and caps: priced per call on the right price card, reserves, caps on settled spend, resume by (model, effort, input, member).
- [x] Opus review of the loop against the API reference (four must-fix items, all fixed).
- [x] Smoke test: 28 members (Haiku medium, Opus medium, Opus low), $2.84 of a $30 cap; all ended ok and all parse; checked by Opus (`m4/COST_ADDENDUM.md`).

**M4, Claude on the same 44 inputs**
- [x] Gate for running the replays: smoke passed, cost addendum hashed and pushed (the scorer freeze gates scoring, not running).
- [x] Rounds, Haiku first in each: stage 8 of all 12 runs; stage 13; stage 3; the 8 Gemini inputs. Done 11-13 20:38: 352 members, $35.78; 351 parse, one Haiku member a counted drop.
- [x] Exploratory: Haiku without the prompt's room hint on the round-1 rows ($0.30; `results_semantic_1113/nohint_haiku/`).
- [x] Scored once with the frozen scorer (commit 2e46ec8); the independent recompute reproduces it.

### 3.3 The talk

- [x] Deck with parts 1 to 3 (`docs/endsem_2026-11/`): rebuilt after a first Opus review (20 slides), then part 3 filled from the result files (22 slides and 2 backup). Two Opus reviews, no wrong number in either; their fixes are in (3ff6ffd): 24 main slides and 4 backup, about 15 minutes spoken.
- [x] A numbers table for every part-3 number (`results_semantic_1113/numbers_part3.csv`, 1,247 rows, built and audited by script).
- [x] Write-up (`results_semantic_1113/RESULTS.md`) and the limits slides. Two Opus reviews traced about 650 numbers, none wrong; their wording fixes and the required items are in (41ebff0, 4f3f96b); 1,749 numbers audited.
- [x] Independent recompute from raw files: M1 and M4 reproduced (`results_semantic_1113/independent_recompute/`); M2's summary and verdicts reproduced from its per-stage files to within 1.4e-16 (`results_m2_1113/independent_recompute/`). How M2's arms were built was checked by code review, not rebuilt.
- [x] Opus review of the deck against its sources: done twice; the second also checked the deck against the write-up.

## 4. Rules for runs on the host

**A run is accepted only if:**
- its log holds "Exploration complete", or it stopped at a registered cap;
- its `roslaunch.log` has no "out of memory" line and no nvblox "process has died" line;
- its last graph differs from its first;
- for a tour: waypoints reached equal waypoints listed.

**Operations:**
- Test whether the queue lives with `systemctl --user is-active paper-queue-rerun3.scope`. The control script's `status` gives a false alarm.
- Never install into the container's shared Python. Never run the live runner in `asp-noetic` while the queue or a replay runs there: its cleanup kills every process.
- Start long host jobs under `systemd-run --user --scope` from a fresh login.
- Start no host work with less than 15 GB of disk free.
- Never touch another user's processes or the credential files. Never copy a DSG file.

## 5. Rules for the talk

- Say "no detectable difference", never "did as well" or "failed to replicate".
- On the paper's scale, say "did not appear on 853 at 10% and 50%, with DeepSeek and a rebuilt reference".
- F0 is an identity, not a finding.
- Under a null the verdict is Inconclusive, not Mixed. The slide says that L1 cannot decide at 44 inputs.
- The limits slide carries the live test's open points: the interval reaches +0.040; the placebo differed in pacing and in member agreement; the LLM arm led at 60 m.
- What each outcome lets the talk claim:

  | Outcome | Claim |
  |---|---|
  | Supported at L3 | Claude beats the named comparators, in two houses, on proxy truth. Not shown to reach the map. |
  | Mixed | Right at house level, wrong in place. |
  | Both models Rejected | The "fails" line, without its M2 clause. |
  | Inconclusive | The registered null wording, with the detectable differences. |
  | M4 dropped | DeepSeek's results are exploratory, and no thesis line applies. |

## 6. Cut, and the one added run

**Cut:** E6 (live Claude); M6; H5; the Sonnet replay; the direct probe; Haiku on 259 inputs; scenes 69 and 573; the genai shim; M2's subset repeats and error sweep; per-stage GED in the one-pass driver; ASP on 871 to the full budget.

**ASP on 853 to the full budget (approved 11-13).** Three seeds, about $6 of DeepSeek, one run at a time, 4 to 9 hours each, reported as its own row and never pooled with October. It fills the one column of the paper's table where we have no ASP value. It starts only if a readiness check passes: the DeepSeek model is still served, the runner can go past 60 m without the broken scheduler, and the plan and pre-registration are amended first. If the check fails or a run dies, it is dropped with no retry.

## 7. Decisions and the defaults in force

| Decision | State |
|---|---|
| End-sem date | Assumed: rehearsals 26-27 Nov, numbers frozen 24 Nov. Not yet confirmed. |
| Claude spend | Approved 11-13: up to $330 ($30 smoke, $280 Opus, $20 Haiku). The smoke test's measured cost is reported before the replays. |
| Push to GitHub | Approved 11-13: hash commits go to the branch `endsem-2026-11`, not to main. The student merges later. |
| ASP on 853 to the full budget | Approved 11-13, behind the readiness check in §6. |
| The author's files | They change part 2 only if they arrive by 11-20. |

## 8. What the five reviews changed

- **Schedule.** M1 is 5 to 6 days of work for one worker, so it runs in parallel lanes. The bench starts at once, from a copy. The frozen scorer gates M4. H5 has no job left. The rescore is half a day, not two hours.
- **Method.** Rules must precede data: Amendment 2 tonight, and the scorer hash before Claude. The budget rule in the draft was wrong: by §4, one valid rerun on 871 already moves every 871 number. Verdict rules needed rewriting for 2 models and no probe. The list of numbers already seen was incomplete.
- **Claude backend and cost.** Build a native loop, not a patch of the genai client. Change the smoke test so it measures what M4 will cost. Haiku has a second price card above 100K prompt tokens. Run in rounds so a cap stop leaves a balanced set. The $330 total stands.
- **Host operations.** Nobody watched the queue and the liveness test was wrong. The acceptance check must also catch a mapper death with no out-of-memory line. The scheduler is not fit for new live runs.
- **Examiner.** The paper's room test needs a slot. The deck needs more than a day and should start now. The C1 gap is half explained by numbers already in the repo. ASP to the full budget is the only way to face the paper's headline column.

## 9. Progress log

- 11-13 17:54: Amendment 2 hashed (sha256 1286c2c5…). Deviations 40-47 written. This plan saved.
- 11-13 17:55: committed as 60e2973. 18:00: pushed to `origin/endsem-2026-11`, before the first third attempt of an e7 871 seed started.
- 11-13 18:04: the 853 APR-b rerun ended with "Exploration complete" at 183.3 m; its graph grew at every archived stop.
- 11-13 18:05-18:20: lanes started: bench rebuild, Claude loop, data inventory, statistics module, deck, host truth files. The Claude key works against the API (a free model-list call).
- 11-13 18:05-18:10: another user's GPU job came back (41.7 GB). The queue waits at its 12 GB check before the 871 APR-b tour. No run is harmed. GPU-bound work (871 tour, 871 seeds, ASP on 853) waits for that job to end.
- 11-13 18:13: truth files built on the host (CPU only): 12 regions on 00853, 16 on 00871; floor masks hold too few object centres, so the footprint is the mask of all triangles.
- 11-13 18:30: Opus reviews back. Amendment 2: one false statement and several open cases, fixed by a Note (commit aa3886d, pushed 18:35). Semantic pre-registration: ten must-fix items, all taken into a rewrite.
- 11-13 18:40: frame and smoke inputs on the laptop. Scorer lanes started against a shared contract (`semantic/model.py`): labels, truth and extraction, scoring and comparators. Opus review of the Claude loop started.
- Readiness for ASP on 853, item 1: the pinned DeepSeek model is still served by DeepInfra at fp8 (checked 18:20). October's 60 m runs used 1,022 to 1,362 calls, so a 105 m run fits under the launcher's 3,000-call cap.
- 11-13 18:59: `PREREGISTRATION_SEMANTIC.md` hashed (59c97ad6…) after three Opus reviews, pushed 19:00 (49307ed). The reviews changed: the footprint (all triangles, not the floor), "answers to" (the detector calls a bed "duvet"), the open-room rule, the guess rule (place only; ids and flags ignored), the wrong-house comparator (a separate gate over 6 pairs), and the label table's rules.
- 11-13 19:00: the paper runs that exist pass or fail Amendment 2's tests as expected: 853 seeds 42-46 and 871 seed 46 valid; the eight crashed 871 attempts invalid; the 853 APR-b rerun not frozen (117 object nodes), so C2 for 853 can be computed.
- 11-13 18:57: Opus review of the Claude loop: four must-fix items before any paid call (gateway address, per-model caps, the per-round cost check, reserves); fixes in progress.
- 11-13 18:47: tyrone's CPUs taken into use for the bench and the factorial (`~/endsem_cpu`), at the student's request, while the GPU is held by another user's job.
- 11-13 19:02: lanes running: scorer integration; M2 pre-registration review; bench and factorial code on tyrone; part-2 rescore pipeline; Claude loop fixes.
- 11-13 19:15: `PREREGISTRATION_M2.md` hashed (5b8a8400…) after an Opus review, pushed (f30ee25), before any of its arms was scored.
- 11-13 19:10-19:18: Claude smoke test: 28 of 28 members ok, $2.84. Opus at effort medium costs about $0.15 a member, Haiku about half a cent: both models make their tool calls in one or two turns. All 28 texts parse with the author's parser on the host.
- 11-13 19:13: part-2 rescore pipeline ran in interim mode: 853 equals the 11-12 numbers cell for cell; C2 for 853 is 0.751, below the 0.90 line (commit 7948b04). 871 awaits its third attempts.
- 11-13 19:25: cost addendum hashed (cb0a131a…) and pushed (2e8a06c) after an Opus check of the smoke records. 19:26: the full Claude replay started (both models, four rounds). Its outputs are not scored until the scorer is frozen.
- 11-13 20:02: Opus code review of the scorer: its hand-computed toy house agreed with the code on every number; one must-fix (how a finished round is judged) and six smaller items, fixed by 20:10 (437 tests).
- 11-13 20:12: truth files, label table and frame hashed and pushed (61d5965). 20:13: first real scoring run, exploratory (DeepSeek, Gemini, placebo). 20:14: scorer frozen and pushed (04e6afc), before any Claude output is scored.
- Detectable differences from the freeze: 5.7 points at L1, 5.2 at L2, 1.1 at L3. All three levels can decide; the plan had feared 20 points at L1.
- Exploratory result, DeepSeek on the 44 rows: against the other-house prior, L1 −1.7 points (−5.2 to 0.0) and L2 −26.3 (−33.2 to −19.4); against the placebo, L1 +1.7 and L2 +5.8; at L3, −0.6 (−1.9 to +0.6) against the region trade. Rejected at all three levels under the frozen rules. Its guesses lie a median 7.7 m from the nearest unseen object they could name (Gemini 5.8 m, placebo 9.0 m).
- 11-13 20:05: tyrone reproduces the bench's 9,600 picks in about 10 minutes on 48 cores; the factorial code is staged there and under Opus review.
- 11-13 20:38: the Claude replays ended: 352 members, all four rounds for both models, $35.78 (with the smoke test, $38.62 of the $330 approved). 351 parse with the author's parser; one Haiku member, cut off at the token limit, is a counted drop.
- **11-13 20:41: the blind test, scored once with the frozen scorer (commit 2e46ec8).** All six hypotheses read Rejected, and the thesis line is "the claim fails". Against the other-house prior: Opus L1 −5.8 points (−12.2 to 0.0), L2 −35.1 (−41.3 to −29.1); Haiku L1 −10.4 (−20.8 to 0.0), L2 −24.9 (−31.5 to −18.1). At L3 against the region trade: Opus +0.5 (−1.9 to +2.9), Haiku +0.8 (−0.8 to +2.4), margin 3. No model passes the wrong-house gate. Against the placebo, Haiku is ahead at L2 by 8.2 points (p 0.014); Opus is not.
- 11-13 21:08: an independent recompute, from code written without reading the scorer, reproduces DeepSeek's and both Claude models' numbers, the six verdicts and the thesis line. The one close verdict, Opus at L3 (upper end 0.0295 against a margin of 0.03), held in fifteen reruns of the randomised control with other seeds and up to 5,000 draws (deviation 55).
- 11-13 20:30 and 21:05: M2 on tyrone's CPUs, both passes complete (384 stages each). True objects at true places beat random guesses by +0.218 in rank correlation with the yardstick (+0.195 to +0.241). Moved by each model's own placement error (medians 7.7 m DeepSeek, 7.1 m Haiku, 8.1 m Opus) they fall to −0.020, −0.006 and −0.029; room types alone give +0.024. Every arm reads "not shown sufficient, on a provisional yardstick".
- 11-13 20:55-21:02: tyrone was unreachable because Cloudflare WARP on the laptop was connected and blocks Tailscale. The student said to leave WARP off until the work is done; it is to be reconnected at the end.
- Still blocked on the GPU (another user's job holds 43 of 48 GB since about 18:05): the 871 APR-b tour, the four 871 seeds, and ASP on 853. The queue waits at its check; nothing is harmed.
- 11-13 21:33: the part-3 write-up and its numbers table committed and pushed (f5101c3). An Opus review traced about 400 of its numbers to the result files and found none wrong. It asked for eight sentences to be cut back to what the rules allow (for example: "Rejected" means the interval rules out a gain as large as the margin, not that the model is worse) and for seven required items the scorer did not save (label shares, flag counts, the copy-the-map comparator, M2's regret figures). A lane is fixing these; the missing counts come from a supplement script that imports the frozen scorer and changes no result file.
- 11-13 21:37: an Opus review of Amendment 3 found one false statement (the 853 full-budget runs use E1's official code path, not E1's files: three files changed since, none in the official arm) and cases the rules left open. A Note corrects and settles them, hashed 21:37:37 (67f48d61…) and pushed before any run (f9ef216, deviation 58). Each seed is now launched on its own behind checks made by hand; a run killed by another job's use of the GPU is not rerun; the dry run's cost limit is $1.00. The review projects 5 to 10 hours and $1.5 to $2.2 a run, and guesses that one run in three ends before the budget.
- 11-13 21:41: Opus review of the deck with part 3 filled: no wrong number in about 165 checked against the raw files; three wrong labels, ten sentences that said too much (the answer slide above all), too many words on every part-3 slide, and one missing answer (why Claude, when the paper used Gemini). A lane is fixing these.
- 11-13 21:44: the C1 area table (9b245c7, deviation 59).
- 11-13 21:47: the GPU is still held by the other user's job (43.0 of 48 GB); the queue checks every five minutes and waits up to 72 hours. Nothing GPU-bound has moved since 18:05.
- 11-13 21:49: an independent recompute of M2's summary, written from the frozen rules without reading the summary code, matches every mean, interval end and verdict (6c94a74). On one secondary yardstick (U_360) room types alone read "inconclusive"; on every other view every arm reads "not shown sufficient".
- 11-13 21:56: the write-up revised after its review and pushed (41ebff0): eight sentences cut back, the required items added, and a supplement script for the counts the frozen scorer does not save (deviation 60); 1,738 numbers audited. At 21:52 the deck with part 3 and its review fixes was pushed (42fdbc9): 23 main slides and 3 backup.
- 11-13 22:06: scoring code for the November ASP row pushed (6fb5888) after an Opus code review: the runs enter only through the checks of A3.2, as their own arm, one folder per seed; with no such run every output is unchanged (1,063 tests pass).
- 11-13 22:03: a second Opus look at the write-up and the deck together: about 250 more numbers traced and eight supplement counts redone from the raw graphs, no mismatch. It asked for eight more small wording changes in the write-up and for the deck's answer slides to follow the write-up's own lists; both are in progress.
- 11-13 22:07: the GPU is still held (43.0 of 48 GB). The 871 tour, the four 871 seeds and ASP on 853 have not moved.
- 11-13 22:13: the write-up's last eight wording changes pushed (4f3f96b); 1,749 numbers audited. 22:22: the deck brought in line with the write-up and pushed (3ff6ffd): the answer slides follow the write-up's own lists, part 3 uses points throughout, the stage slide draws one real hit and one real miss, the C1 table shows the labelled floor and the outline, and a backup answers why all true objects do not raise ASP's score. Parts 1 and 3 of the talk are finished; part 2 keeps its 871 cells and the 853 full-budget row marked as open.
- 11-13 22:24: a mail to the paper's authors is drafted for the student to send (kept outside the repository). It asks for their reference graphs, the time budget, how rooms and area were counted, the runs behind Fig. 4, and any saved Gemini samples.
- 11-13 22:24: the GPU is still held (43.0 of 48 GB, since 18:05). Open and waiting on it: the 871 tour and seeds, the acceptance checks, the final rescore with deviation 46's folder map, and ASP on 853.
