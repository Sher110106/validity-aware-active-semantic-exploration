# Validity-Aware Active Semantic Exploration

A replication and audit of Active Semantic Perception (ASP), [arXiv 2510.05430](https://arxiv.org/abs/2510.05430). We rebuilt the ASP evaluation, added a filter for the language model's scene-graph guesses, and tested whether the filter helps a robot explore.

Team: Sher Partap Singh, Preesha Katial, Ananya Singla. Course: computer vision and perception.

## Findings so far

1. **The September "main result" is withdrawn.** We first reported that requiring all four ensemble members to agree (unanimity) improves F1 and graph edit distance. That filter keeps 19 of 8,943 predicted nodes, and it scores within 0.0002 of the observed map alone (F1 0.5218 / 0.4349 / 0.4957 against 0.5219 / 0.4351 / 0.4957). The gain came from dropping the guesses, not from filtering them. Source: `tools/live_policy/results_2026-10-31/WRITEUP.md` §9, erratum 2.
2. **October live test, with a random-guess placebo.** Source: the same WRITEUP.
   - E1, LLM guesses minus random guesses: +0.013 F1 AUC to 60 m, 95% interval -0.012 to +0.040, p 0.22. This is a pilot; effects up to +0.040 are not ruled out.
   - Our filter made no detectable difference.
   - E3, exact objects minus random guesses: +0.034 on scene 871, p 0.10. That p is the smallest a 3 v 3 test can give, so it cannot decide either way.
3. **November paper-scale scores** (author's F1 rules, F1 x 100, reference rebuilt by our tours; final rescore of 18 Nov in `tools/live_policy/results_paper_compare_1113/paper_compare.md`, scenes 00853 and 00871). The paper columns are Fig. 4 of the paper, one run each; ours carry n (in brackets in the tables). On 853, by the clock, November's ASP runs (three runs to 105 m) sit above our frontier, as in the paper, by less than in the paper: at the full budget ASP reads 61.6 (n=2) and our frontier 55.6 (n=3) against the paper's 66.7 and 58.8, and the gaps at 10%, 50% and 100% are 4.8, 11.6 and 6.0 points against the paper's 15.8, 14.3 and 7.9. November's ASP logs 5.8 s per metre (n=3) and our frontier 7.0 (n=5), and frontier's clock also counts its waits for a path, so part of each gap may come from the clock. October's shorter ASP runs (to 60 m) led by 4.1 at 10% and trailed by 0.8 at 50%; the two ASP batches differ by 12.4 points at 50%, as much as November's gap there, and October's random-guess runs (no LLM) read 43.9 at 50%, between them. At 100% the gap depends on the reference: 6.0 here (`apr`), 1.5 under `hm3d` and -0.2 under `frontier_made`. This is one home with n of 3 (2 at 100%); it does not test the paper's claim. By the rule's letter (deviation 64) seed 43, a run that went through a short dip in host memory, keeps its 10% and 50% values and loses its 100% one, which then reads 62.9 (n=1 of 3); with seed 43 left out altogether the row reads 19.1 / 53.6 / 62.9 (n=2, 2, 1), a further sensitivity. The two ASP batches are never pooled. By the metre the sign depends on the reference (exploratory, `results_paper_compare_1113/equal_path/equal_path.md`; deviations 66 and 71): at 50 m ASP reads 48.2 (n=3) and our frontier 47.4 (n=5) against the scripted reference, 0.8 ahead, and 25.4 against 27.3 under the human labels (`hm3d`), 1.9 behind; at 100 m, 62.5 (n=3) against 58.7 (n=2 of 5), 3.8 ahead, and 32.5 against 34.1, 1.6 behind. Two control arms that share ASP's clock (random guesses, no guesses) are registered and running (`PREREGISTRATION_PAPER.md`, Amendment 5); no result of theirs is in this file.

   | Row | Arm | 10% | 50% | 100% |
   |---|---|---|---|---|
   | Frontier | ours (`frontier_end`) | 12.4 (n=5) | 39.5 (n=5) | 55.6 (n=3 of 5) |
   | Frontier | paper | 18.6 | 46.5 | 58.8 |
   | ASP, October (60 m) | ours (`official`) | 16.5 (n=2) | 38.7 (n=2) | no value |
   | ASP, November (105 m) | ours (`official_nov`) | 17.2 (n=3) | 51.1 (n=3) | 61.6 (n=2 of 3) |
   | ASP | paper | 34.4 | 60.8 | 66.7 |

   Our `filter_only` ASP arm scores 14.8 (n=3) / 48.3 (n=3) / no value. "No value" means no run reached the stage. One November run ended at 604 s, short of the 632 s budget, so it has no 100% value.

   On 871 (budget 1,300 s: the median end of the 4 frontier runs that logged "Exploration complete"; the fifth stopped at the 250 m path cap and is left out) our ASP runs stop at 60 m, so they have a value at 10% only, and no ASP run of ours reaches 50% of the budget. Where the paper and we both have a cell, ours are within 1.3 to 3.5 points of the paper's (above it at B; two of the four gaps turn negative at 0.8 B); on 853 ours are 3.2 to 22.1 below. The paper's value lies inside our range in 3 of 4 cells. At 10% our `official` arm is 2.0 points above our frontier (33.9 v 31.9; n=3 v n=5) and the paper's ASP is 1.3 above its frontier (30.5 v 29.2); the ranges overlap. At 50% and 100% of that budget ASP and frontier cannot be compared. Our LLM is DeepSeek, the paper's Gemini 2.5 Pro, and our reference is a scripted stand-in for the author's hand-driven tour. The budget for 871, 1,300 s, is about twice 853's, 632 s; the paper says a run has 25 to 30 steps, which suggests a shorter budget (our inference, not its figure). At 750 s (exploratory, `budget_sensitivity/budget_sensitivity.md`) our frontier reads 26.1 / 43.6 / 62.4 against the paper's 29.2 / 55.7 / 65.3, 2.9 to 12.1 points below it. At 50 m of path (exploratory, scripted reference) the arms read: exact objects 57.8 (n=3), ASP 52.6 (n=3), November's frontier 49.2 (n=5), random guesses 42.1 (n=3), October's frontier 36.3 (n=3). Our two frontier batches differ by 12.9, more than ASP differs from November's frontier (3.4) or from random guesses (10.5), so this shows no ordering.

   | Row | Arm | 10% | 50% | 100% |
   |---|---|---|---|---|
   | Frontier | ours (`frontier_end`) | 31.9 (n=5) | 59.2 (n=5) | 66.6 (n=3 of 5) |
   | Frontier | paper | 29.2 | 55.7 | 65.3 |
   | ASP | ours (`official`) | 33.9 (n=3) | no value | no value |
   | ASP | paper | 30.5 | 62.4 | 68.0 |

   Our `filter_only` ASP arm scores 33.0 (n=3) / no value / no value. The 871 repeat tour is not frozen; the two tours agree at F1 0.771 (853: 0.751), below the 0.90 line, so the reference moves by more than the paper's margins, with the first tours' damage mixed in.
4. **November semantic test: are the guesses right in meaning?** Source: [tools/live_policy/results_semantic_1113/RESULTS.md](tools/live_policy/results_semantic_1113/RESULTS.md). The test was pre-registered, and blind for the two Claude models: we replayed Claude Opus 5.5 and Haiku 5.5 on 44 saved planner inputs from scenes 853 and 871, with the author's prompt and tool loop, and scored them once with a scorer frozen beforehand. What the data show: in these two houses, Claude's guesses carried no detectable gain over house base rates at naming, or over a trade of region contents at placing. All six hypotheses read Rejected, so the registered line is "the claim fails", for the first half of the claim as the author put it to us (that the guesses are right in meaning). The remark is not in the paper; it comes from the author's demo and what the author told the student, and the paper's nearest text is in section IV-B. The line says less than it seems to (exploratory readout, `results_semantic_1113/exploratory_1119/ceiling.md`): the other-house prior scores 91.2% and 100.0% at L1 and 93.4% and 93.7% at L2, so a perfect score could not have been Supported at L1 for either model, and at L2 only for Opus; the line rests on L3, where Opus's interval ends at 2.95 against a margin of 3. The comparators' own scores were not checked before the test was frozen.
   - Naming unseen objects, against a prior built from 179 other HM3D houses that makes as many claims: Opus -35.1 points (-41.3 to -29.1), Haiku -24.9 (-31.5 to -18.1).
   - Placing content in the right unseen region, against a trade of region contents: Opus +0.5 points (-1.9 to +2.95), Haiku +0.8 (-0.8 to +2.4), with a margin of 3. Rejected means the interval rules out a gain as large as the margin; a smaller gain is not ruled out.
   - DeepSeek's saved guesses read the same way; that result is exploratory.
   - Earlier, exploratory (`exploratory_1119/common_rows.md`): on the 8 rows that hold October's Gemini 3.8 Flash guesses (3 clusters, 29 members, rows chosen in October; not the paper's Gemini 2.5 Pro), Gemini scores 91.3% at L2 against DeepSeek 73.9%, Haiku 70.5%, Opus 69.6% and random guesses 65.4%, and 13.8% at L3 against 7.6%, 7.8%, 5.6% and 2.3%. The other-house prior scores 98.8% at L2 on Gemini's members, above Gemini. October's lead on 8 rows repeated on 36 new ones (next bullet).
   - Is it the model? Registered replay (`PREREGISTRATION_GEMINI.md` with Notes 1 and 2; `results_semantic_1113/gemini_1119/RESULTS_GEMINI.md`; `DEVIATIONS_NOVEMBER.md`, item 72). Gemini 3.8 Flash, the registered fallback (the paper's Gemini 2.5 Pro is no longer offered to new users), ran the author's own loop on the 36 inputs of rounds 1 to 3 that Claude saw: 4 members each, 137 of 144 parsed (drop rate 4.9%). Confirmatory, 12 clusters, one-sided, Holm over four: Gemini minus Opus +21.0 points at L2 (95% interval +13.5 to +28.8, Holm p 0.0010) and +2.7 at L3 (-0.3 to +5.8, p 0.0381); Gemini minus Haiku +10.9 at L2 (+1.6 to +20.5, p 0.0344) and +3.1 at L3 (+0.4 to +6.0, p 0.0381). All four are found, so the registered sentence is: "The Claude result does not carry over to Gemini 3.8 Flash: on the same inputs Gemini 3.8 Flash names more of what is there and puts more of it in fitting regions. Gemini 3.8 Flash is not the paper's model." Read it with its limits: Gemini ran the author's loop and Claude our port of it, so the contrast is of model and loop together; against Opus at L3 the interval includes zero; Gemini also made more guesses per member, and 5a does not adjust for that; saved inputs from two homes; no robot acted on these guesses; the comparators at L1 and L2 sit at the ceiling.
   - The registered rule at L3 reads Rejected for Gemini 3.8 Flash too: "Gemini 3.8 Flash did not beat a trade of region contents by the 3-point margin. Gemini 3.8 Flash is not the paper's model." Its L3 score is 7.5%, below all three controls (8.5%, 8.7% for the trade of regions, 11.0%), and its interval against the trade ends at +1.4 points against a margin of 3. Both hold: it reaches fitting regions more often than Claude (4.8% and 4.4%), yet no more often than a trade of regions gives for its own guesses; its lead is in the raw rate and does not show that its labels fit their regions. Exploratory: at L2 it scores 78.3%, about 12 points below the other-house prior that makes as many claims (90.7%; -12.4, -18.5 to -6.3) and above random guesses (59.6%; +18.6, +12.8 to +24.4); it passes the wrong-house check at L1 (p 0.031) and L2 (p 0.016) over 6 pairs. A further extension to one more Gemini model followed (next bullet).
   - The extension of Note 3 (registered after the Flash result was seen; `results_semantic_1113/gemini_argon_1119/RESULTS_GEMINI.md`, `argon_minus_flash.md`; `DEVIATIONS_NOVEMBER.md`, item 73): Gemini 4 Argon, the top model on Google's price page on 19 November, in the author's loop, on the 12 round-1 inputs, 4 members each, 48 of 48 parsed; 12 clusters of one row each, so the intervals are wide. Argon minus Opus +17.5 points at L2 (95% interval +5.0 to +30.3, Holm p 0.0205): above. Not detectably above: Opus at L3 (-0.4, -5.7 to +4.9, p 0.6445), Haiku at L2 (+13.6, -1.4 to +28.5, p 0.1069) and Haiku at L3 (+1.2, -4.4 to +6.7, p 0.6445). The registered rule at L3 reads Inconclusive: Argon minus the region trade +0.0 points, interval -2.8 to +3.1, against a margin of 3; its own L3 score is 6.2%, beside 5.7%, 6.2% (the trade) and 6.6% for its three controls. Exploratory, computed after both results were seen (both ran the author's loop, so the models alone): Argon minus Flash on the same 12 rows is -2.9 points at L2 (-9.1 to +3.4) and -5.4 at L3 (-13.1 to +2.0); at L2 Argon scores 79.3%, below the other-house prior (96.5%; -17.2, -23.9 to -10.5). Not the paper's model. Together: two Gemini models scored above Opus at L2 (Flash above Haiku too, Argon not detectably); neither was found to beat a trade of regions at L3 (Flash Rejected, Argon Inconclusive); neither is the paper's model.
   - The paper's room test, exploratory (`exploratory_1119/room_test_runs.md`): on stages with 8 members, the count of registration section 11, DeepSeek's live runs predict 10 of 59 rooms and random guesses 6 of 69 (p 0.125); on all stages, 13 of 59 (p 0.040). Our filter arm, also built from DeepSeek's guesses, is not ahead of random guesses: 2 of 69 (p 0.290) on 8-member stages, 7 of 69 (p 1.000) on all stages. Opus, replayed, places 16.7% of its rooms in a fitting unobserved region against 2.7% for random guesses (p 0.016, one contrast, not adjusted). The paper reports 9 of 28 with no chance rate.
   - A recompute written from the rules alone, without reading the scorer, reproduces every number.
   - Limits: two houses; HM3D labels stand in for what the camera saw; static replays, not live runs. The paper used Gemini 2.5 Pro, so this does not speak for Gemini.
5. **Would right meaning be enough for ASP's score?** Source: the same write-up, section 8. Offline, on a provisional yardstick: true objects at true places beat random guesses by +0.218 in rank correlation (+0.195 to +0.241). Moved by each model's own placement error they fall to -0.020 (DeepSeek), -0.006 (Haiku) and -0.029 (Opus); room types alone give +0.024. Every arm reads "not shown sufficient, on a provisional yardstick". M2 varied place, not meaning. All true objects for every member (+0.048) is read in `results_m2_1113/exploratory_1119/all_true.md` (exploratory): with identical members the score reads mainly where the two observed maps disagree; the arm's gain never passes 2.0 bits, like the no-guess arm's, and the two correlate at 0.64.

## Where things stand

- Plan, checklist and progress log: [docs/ENDSEM_FINAL_PLAN_2026-11-13.md](docs/ENDSEM_FINAL_PLAN_2026-11-13.md).
- The end-sem talk: [docs/endsem_2026-11/](docs/endsem_2026-11/) (deck, script and number sources).
- Final: part 1; the registered scores of part 2 (the 871 reruns of 17 Nov and the three November ASP runs on 853 are in the final rescore, `tools/live_policy/results_paper_compare_1113/NOTES.md`, written 18 Nov); the registered test of part 3 (finding 4).
- Reading as of 19 Nov, after an independent review: on 853, ASP reads above frontier by the clock, and by the metre the sign depends on the reference (finding 3); on 871 the gap to the paper depends on the budget (finding 3); the registered line "the claim fails" says less than it seems to (finding 4). The readouts behind this are exploratory and filed under the `exploratory_1119/`, `equal_path/` and `budget_sensitivity/` folders (`tools/live_policy/DEVIATIONS_NOVEMBER.md`, items 66 and 71).
- Registered and running, with no result in this file: two control arms on 853 (`PREREGISTRATION_PAPER.md`, Amendment 5). Both Gemini replays are final (finding 4).
- Open: the authors' budget and files, if they reply by 23:59 IST on 24 Nov (Amendment 4).
- Earlier status: [docs/STATUS_2026-11-12.md](docs/STATUS_2026-11-12.md). The plan the final one grew from: [docs/ENDSEM_PLAN_2026-11-03.md](docs/ENDSEM_PLAN_2026-11-03.md).

## Doc map

| Doc | Purpose |
|---|---|
| `README.md` | This page. |
| [docs/ENDSEM_FINAL_PLAN_2026-11-13.md](docs/ENDSEM_FINAL_PLAN_2026-11-13.md) | The end-sem plan as carried out: checklist and progress log. |
| [docs/endsem_2026-11/](docs/endsem_2026-11/) | End-sem deck, script and number sources. |
| [tools/live_policy/results_semantic_1113/RESULTS.md](tools/live_policy/results_semantic_1113/RESULTS.md) | The semantic test and M2: results, limits, and what the talk may say. |
| [docs/STATUS_2026-11-12.md](docs/STATUS_2026-11-12.md) | What is done and what is open, 12 Nov. |
| [docs/ENDSEM_PLAN_2026-11-03.md](docs/ENDSEM_PLAN_2026-11-03.md) | End-semester plan, budget and cut rules. |
| [docs/RESULTS.md](docs/RESULTS.md) | All results, metric definitions, costs and errata. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Code, data flow and terms. |
| [docs/REPRODUCE.md](docs/REPRODUCE.md) | How to check the evidence and run the tests. |
| [docs/HISTORY.md](docs/HISTORY.md) | Timeline, archive guide and where removed docs went. |
| [docs/audit/](docs/audit/) | Dated audits and cost accounting (September). |
| [docs/archive/](docs/archive/) | September plans, reviews and reports. Superseded. |
| [docs/checkin/](docs/checkin/) | Check-in 1 deck and the 29 Oct review package. |
| [docs/checkin_2026-11/](docs/checkin_2026-11/) | Check-in 2 deck, script and number sources. |
| [paper/](paper/README.md) | Course paper (PDF, Word) and table provenance. |
| [tools/live_policy/README.md](tools/live_policy/README.md) | Live-test code, pre-registrations, host runbook. |
| `tools/*/README.md`, [docs/prospective_overlay/README.md](docs/prospective_overlay/README.md) | Module guides. |
| [tools/live_policy/results_2026-10-31/WRITEUP.md](tools/live_policy/results_2026-10-31/WRITEUP.md) | October live-test write-up (E1-E3, errata, deviations). |
| [tyrone_mirror/](tyrone_mirror/README.md) | Read-only evidence copied from the GPU host, and the 93-item deviation log. |

## Repository layout

```text
docs/                         Documentation (map above)
paper/                        Course paper
tools/asp_offline/            Offline ASP graph and scoring helpers
tools/evaluator/              Evaluation and graph edit distance
tools/live_policy/            October-November live tests and paper-scale scoring
tools/gemini_campaign/        Metered Gemini campaign (September)
tools/prospective_*/          Prospective campaign: runtime, eval, overlay, integration
tools/matrix_supervisor/      Run queue and control plane (September)
tools/legacy/                 Old provider shim
tools/fixtures/               Small test inputs
tools/tests/                  Main test suite
tyrone_mirror/                Evidence mirror
```

## Run the tests

```sh
.venv_offline/bin/python -m pytest
```

`pytest.ini` sets `pythonpath = tools`. Install `networkx`, `scipy` and `requests` first; with them, 1293 tests are collected (counted 19 Nov with `pytest -q -p no:cacheprovider --collect-only`). Without `requests`, collection stops at `test_openrouter_shim_metering.py` ( see [docs/REPRODUCE.md](docs/REPRODUCE.md)). They use local fixtures and do not call a model provider. Some tests are skipped unless `ASP_AUTHOR_SCRIPTS` points at the author's code.

## Data outside the repo

- **GPU host:** the simulator, datasets, model weights, author checkout and full run directories. Host steps are in the runbook in `tools/live_policy/README.md`.
- **Off-host copy:** a private copy of the October campaign (maps, stats, logs). Scripts that regenerate the E1-E3 package need it. It is not in this repo.
- This repo holds code, write-ups and selected evidence. It does not reproduce every run on its own.
