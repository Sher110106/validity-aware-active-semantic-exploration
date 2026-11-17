# Validity-Aware Active Semantic Exploration

A replication and audit of Active Semantic Perception (ASP), [arXiv 2510.05430](https://arxiv.org/abs/2510.05430). We rebuilt the ASP evaluation, added a filter for the language model's scene-graph guesses, and tested whether the filter helps a robot explore.

Team: Sher Partap Singh, Preesha Katial, Ananya Singla. Course: computer vision and perception.

## Findings so far

1. **The September "main result" is withdrawn.** We first reported that requiring all four ensemble members to agree (unanimity) improves F1 and graph edit distance. That filter keeps 19 of 8,943 predicted nodes, and it scores within 0.0002 of the observed map alone (F1 0.5218 / 0.4349 / 0.4957 against 0.5219 / 0.4351 / 0.4957). The gain came from dropping the guesses, not from filtering them. Source: `tools/live_policy/results_2026-10-31/WRITEUP.md` §9, erratum 2.
2. **October live test, with a random-guess placebo.** Source: the same WRITEUP.
   - E1, LLM guesses minus random guesses: +0.013 F1 AUC to 60 m, 95% interval -0.012 to +0.040, p 0.22. This is a pilot; effects up to +0.040 are not ruled out.
   - Our filter made no detectable difference.
   - E3, exact objects minus random guesses: +0.034 on scene 871, p 0.10. That p is the smallest a 3 v 3 test can give, so it cannot decide either way.
3. **November paper-scale scores** (author's F1 rules, F1 x 100, reference rebuilt by our tours; final rescore of 17 Nov in `tools/live_policy/results_paper_compare_1113/paper_compare.md`, scenes 00853 and 00871). The paper columns are Fig. 4 of the paper, one run per cell; ours carry n. The paper's 14-16 point ASP lead over frontier on 853 does not appear: our `official` arm leads our frontier by 4.1 at 10% and trails it by 0.8 at 50%.

   | Row | Arm | 10% | 50% | 100% |
   |---|---|---|---|---|
   | Frontier | ours (`frontier_end`) | 12.4 | 39.5 | 55.6 (3 of 5 runs) |
   | Frontier | paper | 18.6 | 46.5 | 58.8 |
   | ASP | ours (`official`) | 16.5 | 38.7 | no value |
   | ASP | paper | 34.4 | 60.8 | 66.7 |

   Our `filter_only` ASP arm scores 14.8 / 48.3 / no value. "No value" means no run reached the stage.

   On 871 (budget 1,300 s: the median end of the 4 frontier runs that logged "Exploration complete"; the fifth stopped at the 250 m path cap and is left out) our ASP runs stop at 60 m, so they have a value at 10% only. There our `official` arm leads our frontier by 2.0 points (33.9 v 31.9; n=3 v n=5) and the paper's ASP leads its frontier by 1.3 (30.5 v 29.2); the ranges overlap. At 50% and 100% no ASP run of ours has a value, so ASP and frontier cannot be compared there. Where the paper and we both have a cell, ours are 1.3 to 3.5 points above the paper's. Our LLM is DeepSeek, the paper's Gemini 2.5 Pro, and our reference is a scripted stand-in for the author's hand-driven tour.

   | Row | Arm | 10% | 50% | 100% |
   |---|---|---|---|---|
   | Frontier | ours (`frontier_end`) | 31.9 | 59.2 | 66.6 (3 of 5 runs) |
   | Frontier | paper | 29.2 | 55.7 | 65.3 |
   | ASP | ours (`official`) | 33.9 | no value | no value |
   | ASP | paper | 30.5 | 62.4 | 68.0 |

   Our `filter_only` ASP arm scores 33.0 / no value / no value. The 871 repeat tour is not frozen; the two tours agree at F1 0.771 (853: 0.751), below the 0.90 line, so the reference moves by more than the paper's margins, with the first tour's damage mixed in.
4. **November semantic test: are the guesses right in meaning?** Source: [tools/live_policy/results_semantic_1113/RESULTS.md](tools/live_policy/results_semantic_1113/RESULTS.md). The test was pre-registered, and blind for the two Claude models: we replayed Claude Opus 5.5 and Haiku 5.5 on 44 saved planner inputs from scenes 853 and 871, with the author's prompt and tool loop, and scored them once with a scorer frozen beforehand. All six hypotheses read Rejected. The registered line is "the claim fails", for the first half of the author's claim (that the guesses are right in meaning), in these two houses.
   - Naming unseen objects, against a prior built from 179 other HM3D houses that makes as many claims: Opus -35.1 points (-41.3 to -29.1), Haiku -24.9 (-31.5 to -18.1).
   - Placing content in the right unseen region, against a trade of region contents: Opus +0.5 points (-1.9 to +2.95), Haiku +0.8 (-0.8 to +2.4), with a margin of 3. Rejected means the interval rules out a gain as large as the margin; a smaller gain is not ruled out.
   - DeepSeek's saved guesses read the same way; that result is exploratory.
   - A recompute written from the rules alone, without reading the scorer, reproduces every number.
   - Limits: two houses; HM3D labels stand in for what the camera saw; static replays, not live runs. The paper used Gemini 2.5 Pro, so this does not speak for Gemini.
5. **Would right meaning be enough for ASP's score?** Source: the same write-up, section 8. Offline, on a provisional yardstick: true objects at true places beat random guesses by +0.218 in rank correlation (+0.195 to +0.241). Moved by each model's own placement error they fall to -0.020 (DeepSeek), -0.006 (Haiku) and -0.029 (Opus); room types alone give +0.024. Every arm reads "not shown sufficient, on a provisional yardstick".

## Where things stand

- Plan, checklist and progress log: [docs/ENDSEM_FINAL_PLAN_2026-11-13.md](docs/ENDSEM_FINAL_PLAN_2026-11-13.md).
- The end-sem talk: [docs/endsem_2026-11/](docs/endsem_2026-11/) (deck, script and number sources).
- Done: the 871 reruns and the final rescore for finding 3 (17 Nov; `tools/live_policy/results_paper_compare_1113/NOTES.md`, state final).
- Open: three ASP runs on 853 to the paper's full budget. They are running.
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

`pytest.ini` sets `pythonpath = tools`. Install `networkx`, `scipy` and `requests` first; with them, 470 tests are collected: 453 pass and 17 skip (checked 12 Nov). Without `requests`, collection stops at `test_openrouter_shim_metering.py` ( see [docs/REPRODUCE.md](docs/REPRODUCE.md)). They use local fixtures and do not call a model provider. Some tests are skipped unless `ASP_AUTHOR_SCRIPTS` points at the author's code.

## Data outside the repo

- **GPU host:** the simulator, datasets, model weights, author checkout and full run directories. Host steps are in the runbook in `tools/live_policy/README.md`.
- **Off-host copy:** a private copy of the October campaign (maps, stats, logs). Scripts that regenerate the E1-E3 package need it. It is not in this repo.
- This repo holds code, write-ups and selected evidence. It does not reproduce every run on its own.
