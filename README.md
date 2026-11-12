# Validity-Aware Active Semantic Exploration

A replication and audit of Active Semantic Perception (ASP), [arXiv 2510.05430](https://arxiv.org/abs/2510.05430). We rebuilt the ASP evaluation, added a filter for the language model's scene-graph guesses, and tested whether the filter helps a robot explore.

Team: Sher Partap Singh, Preesha Katial, Ananya Singla. Course: computer vision and perception.

## Findings so far

1. **The September "main result" is withdrawn.** We first reported that requiring all four ensemble members to agree (unanimity) improves F1 and graph edit distance. That filter keeps 19 of 8,943 predicted nodes, and it scores within 0.0002 of the observed map alone (F1 0.5218 / 0.4349 / 0.4957 against 0.5219 / 0.4351 / 0.4957). The gain came from dropping the guesses, not from filtering them. Source: `tools/live_policy/results_2026-10-31/WRITEUP.md` §9, erratum 2.
2. **October live test, with a random-guess placebo.** Source: the same WRITEUP.
   - E1, LLM guesses minus random guesses: +0.013 F1 AUC to 60 m, 95% interval -0.012 to +0.040, p 0.22. This is a pilot; effects up to +0.040 are not ruled out.
   - Our filter made no detectable difference.
   - E3, exact objects minus random guesses: +0.034 on scene 871, p 0.10. That p is the smallest a 3 v 3 test can give, so it cannot decide either way.
3. **November paper-scale scores** (author's F1 rules, F1 x 100, reference rebuilt by our tours; `tools/live_policy/results_paper_compare_1112/paper_compare.md`, scene 00853). The paper columns are Fig. 4 of the paper. The paper's 14-16 point ASP lead over frontier on 853 does not appear: our `official` arm leads our frontier by 4.1 at 10% and trails it by 0.8 at 50%.

   | Row | Arm | 10% | 50% | 100% |
   |---|---|---|---|---|
   | Frontier | ours (`frontier_end`) | 12.4 | 39.5 | 55.6 (3 of 5 runs) |
   | Frontier | paper | 18.6 | 46.5 | 58.8 |
   | ASP | ours (`official`) | 16.5 | 38.7 | no value |
   | ASP | paper | 34.4 | 60.8 | 66.7 |

   Our `filter_only` ASP arm scores 14.8 / 48.3 / no value. "No value" means no run reached the stage.

## Where things stand

- Status: [docs/STATUS_2026-11-12.md](docs/STATUS_2026-11-12.md).
- What comes next: [docs/ENDSEM_PLAN_2026-11-03.md](docs/ENDSEM_PLAN_2026-11-03.md).

## Doc map

| Doc | Purpose |
|---|---|
| `README.md` | This page. |
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
