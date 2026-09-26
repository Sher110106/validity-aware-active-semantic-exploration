# Validity-Aware Active Semantic Exploration

A computer-vision course project that reproduces an **Active Semantic Perception (ASP)** pipeline and studies whether validating and filtering language-model scene-graph predictions makes them more useful for exploration.

**Main result:** requiring all four ensemble members to support a prediction improves static graph precision, F1, and normalized graph edit distance on three DeepSeek scenes. Calibration and the risk-sensitive viewpoint score did not establish an additional benefit. The experiments do not demonstrate better live navigation.

**Status, 26 September 2026:** implementation and the selected analyses are complete; experiments are frozen. The remaining work is evidence packaging, submission preparation, and operational closeout. No new runs are required for the conclusions reported here.

## What we built and evaluated

| Work | Delivered | Evidence status |
|---|---|---|
| ASP reproduction | Pinned-author evaluation, graph matching, path-budget metrics, run provenance | Baseline and short-run results recorded |
| Graph validation | Canonical graph adapter; structural and geometric checks; rejection/removal reasons | Tested on fixtures and saved completions |
| Ensemble support | Fixed four-member denominator and support-threshold ablations | Unanimity improves the three-scene static result |
| Calibration | Leave-one-scene-out support calibration and diagnostics | No useful incremental policy gain established |
| Risk-sensitive selection | Fixed-candidate decision replay and risk-weight sweeps | No demonstrated live-navigation benefit |
| Experiment infrastructure | Metered Gemini requests, budget ledger, queue/control plane, runtime overlay, evidence instrumentation | Exercised during a partial Gemini campaign |
| Frozen analysis | Three 120 m DeepSeek runs; Gemini breadth attempts and a 19.5 m v6 block | Results and limitations are linked below |

ASP maintains a graph of rooms and objects observed by a robot. A language model predicts missing structure, and the pipeline uses those predictions when scoring possible viewpoints. Our extension checks those predictions and measures how filtering changes graph quality and replayed decisions. See [the architecture guide](docs/ARCHITECTURE.md) for the full data flow and terminology.

## Read the project

| If you want to… | Read |
|---|---|
| Understand the goal, work completed, findings, and limitations | [Final report](FINAL_REPORT.md) |
| Find the exact result files and metric definitions | [Results index](docs/RESULTS_INDEX.md) |
| Understand the code and module boundaries | [Architecture and implementation](docs/ARCHITECTURE.md) |
| Inspect evidence or verify the code locally | [Offline reproduction guide](docs/REPRODUCE.md) |
| Know what remains without launching new runs | [Remaining work](docs/REMAINING_WORK.md) |
| See the SSH audit and corrected cost accounting | [26 September audit](docs/REMOTE_AUDIT_2026-09-26.md) |
| Trace a historical change or discarded interpretation | [Archive guide](docs/archive/README.md) and [deviation log](tyrone_mirror/DEVIATIONS.md) |

## Repository map

```text
tools/                  Evaluators, policies, campaign components, and tests
docs/                   Current technical documentation and closeout checklist
docs/audit/             Sanitized, dated accounting aggregates
docs/archive/           Historical plans, reviews, and intermediate reports
tyrone_mirror/          Selected existing results and reference graphs
FINAL_REPORT.md         Project narrative and supported conclusions
```

The local repository is an implementation and selected-evidence package. The full simulator, datasets, model weights, author checkout, and complete raw run directories live in the separate remote workspace. The mirror supports result inspection and a small cached example; it is not a complete reproduction bundle for every experiment.

## Verify locally

After installing the offline dependencies described in [REPRODUCE.md](docs/REPRODUCE.md):

```sh
PYTHONPATH=tools .venv_offline/bin/python -m pytest -q \
  tools/tests tools/gemini_campaign/tests tools/prospective_campaign/tests \
  tools/prospective_eval/tests tools/matrix_supervisor/tests tools/evaluator/tests
```

Verified on 26 September 2026: **286 tests and 9 subtests passed**. These tests use local fixtures and mocks. They do not start ASP or call a model provider.

## Closeout notes

- The best-supported contribution is a backend-specific static filtering result, accompanied by calibration/risk negative results and an auditable implementation.
- Recorded Gemini settled cost is **$37.353274 across five ledgers**, including **$18.552664 for v6**. Three earlier probe/verification requests remain unresolved. See the [accounting audit](docs/REMOTE_AUDIT_2026-09-26.md#corrected-gemini-accounting).
- No active exploration pipeline was observed on the SSH host. The old supervisor service remains active with a paused internal state; retiring it is a documented closeout task.
- An `origin` GitHub remote is configured. Publication of subsequent changes is a separate action; this documentation review does not push commits.
