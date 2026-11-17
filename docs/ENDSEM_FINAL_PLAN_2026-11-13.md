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
- [x] When the queue ends: acceptance checks on all six runs (§4), and the folder map in deviation 46. Done 11-17 17:01 (`acceptance_20261117T170055.json`, written before any score; deviation 46 completed). Reviewed by Opus 11-17; fixes in c4701d7.
- [x] Copy only YAML and stats files to the laptop (rsync include list, dry run first; never a DSG file). Done 11-17 17:01 by the rescore script (`rsync_dryrun_20261117T170055.txt`). Reviewed by Opus 11-17; fixes in c4701d7.
- [x] The author's GED on the host for the new runs. Done 11-17 17:03: four runs computed, fourteen reused by content. Reviewed by Opus 11-17; fixes in c4701d7.
- [x] Rescore: budget by script as Amendment 2 A2.3 says, C2 written to file first, crashed rows pointed at the right folders, the 11-12 values for 871 marked superseded. Final 11-17 17:04 (bd5c403): B for 871 is 1300.25 s (was 809.08 s), C2 is 0.751 on 853 and 0.771 on 871, 853 is unchanged. Reviewed by Opus 11-17; fixes in c4701d7.
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
- F0 is an identity, not a finding. (11-13: the result did not bear this out. All true objects for every member score below random guesses, -0.017 with an interval of -0.031 to -0.004, and `ig` is zero for every candidate in only 2 of 384 stages. The write-up and the deck report it as it came out, with no account of why.)
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
- 11-13 22:08: the write-up's last eight wording changes pushed (4f3f96b); 1,749 numbers audited. 22:22: the deck brought in line with the write-up and pushed (3ff6ffd): the answer slides follow the write-up's own lists, part 3 uses points throughout, the stage slide draws one real hit and one real miss, the C1 table shows the labelled floor and the outline, and a backup answers why all true objects do not raise ASP's score. Parts 1 and 3 of the talk are finished; part 2 keeps its 871 cells and the 853 full-budget row marked as open.
- 11-13 22:24: a mail to the paper's authors is drafted for the student to send (kept outside the repository). It asks for their reference graphs, the time budget, how rooms and area were counted, the runs behind Fig. 4, and any saved Gemini samples.
- 11-13 22:24: the GPU is still held (43.0 of 48 GB, since 18:05). Open and waiting on it: the 871 tour and seeds, the acceptance checks, the final rescore with deviation 46's folder map, and ASP on 853.
- 11-14 06:14: twelve hours on, the GPU is still held by the other user's job (45.3 of 48 GB) and the queue still waits at its check; nothing GPU-bound has run since 11-13 18:04. A watch on the queue resumes the work when it launches a job or ends.
- 11-14 17:50: a day on, the GPU is still held by the other user's job (43.0 of 48 GB) and the queue still waits at its check. It gives up at about 18:05 on 11-16.
- 11-16 08:55: the GPU has been held for 63 hours (43.2 of 48 GB). The queue began this wait at 18:04 on 11-13, and its script gives up after 72 hours: at about 18:10 today it will log "gave up waiting for GPU after 72 h" and end without launching the 871 tour or the four 871 seeds. Under the Note to Amendment 2 (A2.2) an attempt the queue never launched has not happened, so those runs may still be launched once later. The laptop's WARP had reconnected, which cut the link to the host; it was turned off again, as agreed on 11-13.
- 11-16 18:16: the queue gave up at 18:10:28 ("gave up waiting for GPU after 72 h", then "paper queue done") and its scope ended. Of its six jobs only the 853 APR-b tour ran (11-13, 17:07 to 18:04). The 871 APR-b tour and the third attempts of the 871 seeds 42 to 45 were never launched, so under A2.2 they have not happened. The GPU is still held (43.5 of 48 GB). Whether to queue the 871 jobs again is the student's to decide; nothing was restarted.
- 11-16 18:20: with the student's approval, the queue was started again for the five 871 jobs (scope `paper-queue-rerun4`, the same reviewed script and 12 GB check; deviation 61). It waits for the GPU and gives up at about 18:25 on 11-19. Only one queue may run: the container holds one run at a time.
- 11-17 09:16: no change. The GPU has been held for 87 hours (43.3 of 48 GB; 5.2 GB free against the 12 GB the check needs). The fourth queue is alive and still waits; it has launched nothing. Host memory (92 GB free) and disk (37 GB free) are within limits.
- 11-17 09:28: looked at the job that holds the GPU, from outside only (`nvidia-smi`, `ps`, the socket table, the time stamps of its terminal; nothing was sent to it). It is an inference server, started by hand at 18:04 on 11-13, and it is idle: GPU use was 0% in all 48 samples over four minutes (27 W), it used 4.8 s of CPU in those 240 s, it listens on the loopback address only and had no open connection. Its terminal last showed output at 19:04 on 11-16, so it has been used since it started, but not in the last 14 hours. It reserves a fixed 85% share of GPU memory whether or not it is serving, so it will not free the GPU until its owner stops it. Waiting alone will not start the 871 jobs.
- 11-17 10:21: the other job ended between 10:10 and 10:12 and the GPU is free (46.7 of 48 GB). The queue passed its check twice and launched the 871 APR-b tour at 10:20:57 (memory 95 GB, disk 36 GB). The earlier 871 tour folder, from 11-09, was moved aside by the script as `apr_00871_b_FAILED_ATTEMPT_1020`. The four 871 frontier seeds follow. The pre-launch check for the ASP runs now flags a live queue under any name (it named the third queue).
- 11-17 11:06: the 871 APR-b tour finished at 11:06:13 with "Exploration complete": 66 of 66 waypoints reached, 67 stages, 137.1 m in 2,644 s, no "Timeout" line, no "out of memory" line and no dead process. The acceptance check proper runs with the final rescore. The queue goes on to the 871 frontier seeds.
- 11-17 12:30: 871 frontier seed 42 ran from 11:11:58 to 12:29:17 and ended with "Exploration complete": 168.15 m in 4,570 s, 93 stage folders, no "out of memory" line and no dead process. Its log has two "Timeout! Did not find an updated/stable file" lines (stages 19 and 66, first graph file only); the run went on after each. Disk fell to 27 GB while the run's graph files were uncompressed. Seeds 43 to 45 follow.
- 11-17 14:14: 871 frontier seed 43 ran from 12:42:00 to 14:12:22 and ended with "Exploration complete": 223.72 m in 5,352 s, 107 stage folders, no "out of memory" line, no dead process, one "Timeout" line. Two things changed on the host at about 14:00: another user's jobs took 10.8 GB of the GPU (36 GB stays free, above the 12 GB check), and free disk fell to 17 GB, about 6 GB more than this run's own files explain. The queue skips a launch below 10 GB of disk and stops a run below 6 GB. A run writes 7 to 10 GB before its graph files are compressed.
- 11-17 15:26: seed 44 was launched at 14:27:00 and is 65 stages in with no error. Disk will be short for the ASP runs on 853: about 21 GB will be free when the queue ends, the check before each launch needs 20 GB, and a run writes 2 to 3 GB. The student approved compressing the old graph files in `runs/frontier_seeds` and `runs/live_campaign` in place with zstd, as the queue does for its own runs, after the queue ends and never while a run is live. Nothing is deleted. It will be filed as a deviation with counts and a hash list.
- 11-17 15:49: 871 frontier seed 44 ran from 14:27:00 to 15:48:21 and stopped at the registered 250 m path cap (255.7 m at the stop, 4,811 s, 86 stage folders), with no "out of memory" line, no dead process and three "Timeout" lines. Free disk fell to 15 GB at its lowest. A script now compresses old graph files with a hash check on each (`host/compress_old_dsg.sh`, five tests, dry run on the host: 1,478 files, 31.8 GB); it runs after the queue ends. Seed 45 follows.
- 11-17 16:57: 871 frontier seed 45 ran from 16:01:24 to 16:55:39 and ended with "Exploration complete": 138.15 m in 3,186 s, 59 stage folders, no "out of memory" line, no dead process, two "Timeout" lines. All five jobs of the fourth queue have run: the tour and seeds 42, 43 and 45 complete, seed 44 at the 250 m cap. Free disk never fell below 15 GB, so nothing was compressed while a run was live. Next: the final rescore, then the compression of old graph files, then the ASP runs on 853.
- 11-17 17:16: the queue ended at 17:00:27. The final rescore ran from 17:00:55 to 17:04:25 and is filed (bd5c403): all four third attempts and the 871 tour are valid, B for 871 moved from 809.08 s to 1300.25 s, and every 871 number of 11-12 is superseded. Against the scripted-tour reference our frontier on 871 reads 31.9, 59.2 and 66.6 at 10%, 50% and 100% of the budget (the paper's frontier: 29.2, 55.7, 65.3); no ASP run of ours reaches 50% of that budget. The old graph files were compressed from 17:04:48 to 17:05:59 (deviation 62; disk 20 to 45 GB). The pre-launch check passed at 17:06:37 and the ASP dry run on 853 was launched at 17:07:46. An Opus review of the rescore and a Sonnet lane for part 2 of the deck are running.
- 11-17 17:22: the ASP dry run on 853 ran from 17:07:46 to 17:20:32 and passed every rule of the Note to Amendment 3: the runner launched it, it wrote four stage folders (three with graphs), all 110 calls were served by DeepInfra with the pinned model, and its `roslaunch.log` has no "out of memory" line and no line saying nvblox died. It reached 6.4 m and cost $0.11. The pre-launch check passed again at 17:21:36 (GPU 40.9 GB free, memory 93 GB, disk 46 GB, hashes as registered) and seed 42 (`e8_00853_s42_official_105m`) was launched at 17:21:41, with a 12 h limit and a $3 limit. Campaign spend before it: $14.97 of the $25 cap.
- 11-17 17:27: the Opus review of the final rescore is back. It recomputed both budgets, both C2 values, thirteen 871 cells and the 853 comparison with its own code, and none differs from the filed value; the order (acceptance, folder map and C2 before any score) holds, and every valid or invalid call is right. It found one false sentence (deviation 62 said no file was deleted) and five smaller gaps: two unclear sentences in NOTES, one stale one, a log line without a hash, and missing tests for the compression script. All are fixed (c4701d7). NOTES.md was rewritten offline from the saved result files; no score was recomputed. Not checked by the review: the GED values, the other two references, and the host logs.
- 11-17 17:44: part 2 of the deck carries the final 871 numbers (f3be049) and was reviewed by Opus. Every printed number matched the result files, and nothing still called 871 pending. Two things had to change and did: the slide 9 headline said ours are 1.3 to 3.5 points above the paper's, which is right at our budget but turns negative in two of four cells at 0.8 of it, and the script's stated length was short by half a minute. Slide 9 now reads "within 3.5 points of the paper's" and says that the paper's value lies inside our range in three of four cells and that on 853 ours are 3 to 22 points lower. The builder stops if the data cease to fit a typed sentence. The row for ASP to the full budget on 853 stays open until the three seeds end.
- 11-17 19:18: seed 42 is two hours in: 17 stage folders, 49.8 m of path and 308.8 s of navigation time at its last full stage (6.2 s per metre), 1,433 calls, $1.16, two planning errors, no "out of memory" line and no line saying nvblox died. It is using 28.8 calls per metre, more than October's 17 to 23. At that rate it reaches B (632.18 s, about 102 m) at about 2,940 calls and the 105 m target at about 3,020, so the launcher's 3,000-call limit may end it between the two. The limit is registered and stays as it is.
- 11-17 20:57: seed 42 ran from 17:21:41 to 20:55:34 and reached its target: 108.0 m, 28 stage folders, 2,363 calls (all DeepInfra, the pinned model), $2.08, two planning errors, no "out of memory" line and no line saying nvblox died. Its last full stage (26) shows 652.12 s of navigation time, past B (632.18 s), so it counts at 100% under A3.2. The call rate fell in the second half, so the 3,000-call limit was not reached. While it ran, another user's jobs came back on the GPU (24.5 GB held at 20:56). The pre-launch check passed at 20:57:02 with 22.4 GB of GPU memory free, 93 GB of host memory and 50 GB of disk, and seed 43 was launched at 20:57:06. Campaign spend before it: $17.05 of the $25 cap.
- 11-17 23:36: seed 43 is at 86.6 m (514 s at its last full stage, 24 stage folders, $1.71, no line of A3.2). At 23:34:08 the watcher read 1 GB of free host memory; half a minute later the host showed 63 GB, and it has held 57 to 60 GB since. The run was not stopped by hand, and why is filed as deviation 64 before the run's outcome is known: seed 43's row is to be given with and without it. The other user's server now holds 29.9 GB of the GPU, which leaves 11.9 GB free with our run on it. WARP had reconnected at some point after 20:57 and was turned off again at 22:53; the host stayed reachable.
- 11-17 23:54: seed 43 ran from 20:57:06 to 23:53:02 on 11-17 and reached its target: 109.05 m, 27 stage folders, 2,052 calls (all DeepInfra, the pinned model), $1.88, no planning error, no "out of memory" line and no line saying nvblox died. Its last full stage (25) shows 646.08 s of navigation time, past B, so it counts at 100% under A3.2, with deviation 64 beside it. The watcher logged no second memory dip. The pre-launch check passed at 23:54:29 (GPU 17.0 GB free with another user's jobs holding 31.5 GB, memory 94 GB, disk 39 GB) and seed 44, the last, was launched at 23:54:33. Campaign spend before it: $18.93 of the $25 cap.
