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

- [x] Amendment 2 to `PREREGISTRATION_PAPER.md` (rerun rules, frozen-tour test, budget rule).
- [~] `tools/live_policy/DEVIATIONS_NOVEMBER.md`, items 40 onward.
- [ ] When the queue ends: acceptance checks on all six runs (§4), and the folder map in deviation 46.
- [ ] Copy only YAML and stats files to the laptop (rsync include list, dry run first; never a DSG file).
- [ ] The author's GED on the host for the new runs.
- [ ] Rescore: budget by script as Amendment 2 A2.3 says, C2 written to file first, crashed rows pointed at the right folders, the 11-12 values for 871 marked superseded.
- [ ] The C1 area table: navmesh island, HM3D labelled floor, waypoint grid, the paper's figure.
- [ ] Optional, needs the student's yes: ASP on 853 to the full budget (§6).

### 3.2 Part 3: the author's defense

**M0b, pre-registration**
- [ ] Inventory of saved inputs and truth files (what is on the laptop, what needs the host).
- [ ] Host session: region footprints rasterised from the semantic mesh, other houses' label files for the B3b prior, slices rendered for the smoke test and the 44 inputs.
- [ ] `PREREGISTRATION_SEMANTIC.md` drafted. It fixes:
  - truth: region types, the "seen" rule, the unobserved stratum for L3;
  - levels L1 to L3, the label normaliser and the synonym table;
  - comparators B1, B2, B3, B4, B5 and D, and how B3a or B3b is chosen;
  - the family, 2 Claude models × 3 levels, with Holm;
  - verdicts: "the claim holds" means Supported at L3 on the unobserved stratum; the rejection comparator is named; the detectable differences are recomputed;
  - the validity layer's settings and its five readouts, as secondaries;
  - the paper's room test with a chance rate;
  - the M4 round order and the cost addendum;
  - the full list of numbers already seen.
- [ ] Opus review, then hash, commit and push.
- [ ] Truth files hashed as an addendum before the first score.

**M1, the semantic test on saved data ($0)**
- [ ] `tools/live_policy/semantic/`: region truth, prediction extraction, baselines, level scoring, the room test, statistics, and the one-pass driver with the validity views.
- [ ] Tests on synthetic houses with known answers.
- [ ] Opus review of the code against the pre-registration.
- [ ] Scorer freeze: hash and commit (order rule 3).
- [ ] Run on the saved DeepSeek, Gemini and placebo guesses. DeepSeek's verdicts are exploratory.
- [ ] Opus recompute of the headline numbers with its own code.

**M2, would right meaning be enough? ($0)**
- [ ] Rebuild the bench from a copy and reproduce 9,600 of 9,600 picks. Fallback: `audit/counterfactual.py` on the 121 official stages.
- [ ] The trimmed factorial: ceiling and floor arms (F1, F5, F6), then F-room and F3 at DeepSeek's measured error, then each Claude model's error.
- [ ] Opus review. The verdict reads "not shown sufficient, on a yardstick biased toward rejection" unless the data say otherwise.

**M3, the Claude loop**
- [ ] A direct port of the author's tool loop to the Anthropic SDK, with a test that it matches his loop on scripted replies. It runs outside the container's shared Python.
- [ ] Meter and caps: priced per call on the right price card, reserve the measured p99 call, check caps on settled spend, resume by (model, stage, member).
- [ ] Opus review of the loop against the API reference.
- [ ] Smoke test: 24 members (Opus medium, Opus low, Haiku medium), cap $30, scored for cost and plumbing only.

**M4, Claude on the same 44 inputs**
- [ ] Gate: scorer hash committed, smoke passed, cost addendum and round order hashed.
- [ ] Rounds, Haiku first in each: stage 8 of all 12 runs; stage 13; stage 3; the 8 Gemini inputs. Caps: Opus $280, Haiku $20.
- [ ] Last, exploratory: Haiku without the prompt's room hint (about $5).
- [ ] Score with the frozen scorer. Opus recompute.

### 3.3 The talk

- [ ] Deck with parts 1 and 2 final, and part 3 slots for all four outcomes (works, mixed, fails, inconclusive).
- [ ] `numbers.csv` rows for every new number.
- [ ] Write-up section and the limits slide (§5).
- [ ] Independent recompute of M1, M2 and M4 from raw files.
- [ ] Opus review of the deck against its sources.

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

## 6. Cut, and what stays optional

**Cut:** E6 (live Claude); M6; H5; the Sonnet replay; the direct probe; Haiku on 259 inputs; scenes 69 and 573; the genai shim; M2's subset repeats and error sweep; per-stage GED in the one-pass driver; ASP on 871 to the full budget.

**Optional, needs the student's yes: ASP on 853 to the full budget.** Three seeds, about $6 of DeepSeek, one run at a time, 4 to 9 hours each, reported as its own row and never pooled with October. It fills the one column of the paper's table where we have no ASP value. It starts only if a readiness check passes: the DeepSeek model is still served, the runner can go past 60 m without the broken scheduler, and the plan and pre-registration are amended first. If the check fails or a run dies, it is dropped with no retry.

## 7. Decisions and the defaults in force

| Decision | Default until the student says otherwise |
|---|---|
| End-sem date | Rehearsals 26-27 Nov, numbers frozen 24 Nov. |
| Claude spend | Nothing is spent until the student gives the key and the cap. Asked cap: $330 ($30 smoke, $280 Opus, $20 Haiku). |
| Push to GitHub | Commits are local until the student agrees to a push. |
| ASP on 853 | Not run. |
| The author's files | They change part 2 only if they arrive by 11-20. |

## 8. What the five reviews changed

- **Schedule.** M1 is 5 to 6 days of work for one worker, so it runs in parallel lanes. The bench starts at once, from a copy. The frozen scorer gates M4. H5 has no job left. The rescore is half a day, not two hours.
- **Method.** Rules must precede data: Amendment 2 tonight, and the scorer hash before Claude. The budget rule in the draft was wrong: by §4, one valid rerun on 871 already moves every 871 number. Verdict rules needed rewriting for 2 models and no probe. The list of numbers already seen was incomplete.
- **Claude backend and cost.** Build a native loop, not a patch of the genai client. Change the smoke test so it measures what M4 will cost. Haiku has a second price card above 100K prompt tokens. Run in rounds so a cap stop leaves a balanced set. The $330 total stands.
- **Host operations.** Nobody watched the queue and the liveness test was wrong. The acceptance check must also catch a mapper death with no out-of-memory line. The scheduler is not fit for new live runs.
- **Examiner.** The paper's room test needs a slot. The deck needs more than a day and should start now. The C1 gap is half explained by numbers already in the repo. ASP to the full budget is the only way to face the paper's headline column.

## 9. Progress log

- 11-13 17:54: Amendment 2 hashed (sha256 1286c2c5…). Deviations 40-47 written. This plan saved.
