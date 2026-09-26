# Reproduce and inspect

"Offline" below means no simulation run and no provider call after setup. Installing dependencies may still use a package index.

Use one interpreter consistently: `.venv_offline/bin/python` with `PYTHONPATH=tools`.

## Environment

The offline tools require Python 3.10+ and the packages in
`tools/asp_offline/requirements.txt`. A local setup is:

```sh
python3 -m venv .venv_offline
.venv_offline/bin/python -m pip install -r tools/asp_offline/requirements.txt pytest
```

## Tier 1: inspect published results (no code needed)

Read the frozen numbers and their provenance:

- `docs/RESULTS_INDEX.md` for the run inventory and per-scene sources.
- `tyrone_mirror/runs/matrix120m_scoring/STATIC_REPLAY_SHA256SUMS` for the matrix replay digests.
- `docs/audit/2026-09-26-ledger-summary.json` for sanitized cost aggregates.
- `docs/ARCHITECTURE.md` for which evaluator each table uses.

## Tier 2: run the fixture test suite

From the repository root:

```sh
PYTHONPATH=tools .venv_offline/bin/python -m pytest -q \
  tools/tests tools/gemini_campaign/tests tools/prospective_campaign/tests \
  tools/prospective_eval/tests tools/matrix_supervisor/tests tools/evaluator/tests
.venv_offline/bin/python -m compileall -q tools
```

Last verified 26 September 2026: 286 tests and 9 subtests passed. Tests use local fixtures and mocks; they start no pipeline and call no provider.

Caveats:

- `tools/gemini_campaign` summary/export/checksum commands open the ledger database, which can create, initialize, or chmod the file and enable WAL. They are offline but not filesystem-read-only. Point them at a copy if the original must stay untouched.
- The matrix supervisor `--check` and `--once --dry-run` modes inspect a host; plain `--once` and `--daemon` can act on processes and containers. Do not run them against a live host as a "test".
- `tools/prospective_runtime/run_campaign.py` refuses live mode without audited contracts; default invocation is a dry run.

## Tier 3: replay locally included artifacts

These commands read cached graphs and write new output files beside them. They need the referenced inputs to exist locally; the mirror does not contain every host-side corpus (see `docs/RESULTS_INDEX.md`, input availability).

```sh
PYTHONPATH=tools .venv_offline/bin/python tools/evaluator/evaluate_run.py \
  --run <run>/stages \
  --gt <reference>/stages/<checkpoint>/habitat_scene_graph_original_graph0.yaml \
  --out eval_results.json
```

This scores the tracked graph produced by the author pipeline. It does not merge LLM completions into the tracked graph. It emits per-stage metrics, not its own AUC summary.

```sh
PYTHONPATH=tools .venv_offline/bin/python tools/extension_policy_replay.py \
  --run <run>/stages \
  --reference <reference>/stages/<checkpoint>/habitat_scene_graph_original_graph0.yaml \
  --budget-m 120 \
  --output extension_policy_replay.json
```

The four-member denominator is explicit. Read `calibration.status` before interpreting calibrated rows. References outside the four known `/workspace/...` calibration paths yield `UNCALIBRATED_PROVISIONAL`.

```sh
PYTHONPATH=tools .venv_offline/bin/python tools/decision_replay.py \
  --scene-id 00069 \
  --run <run>/stages \
  --reference <reference>/stages/<checkpoint>/habitat_scene_graph_original_graph0.yaml \
  --out-dir <new-output-dir> \
  --out-filename decision_replay.json

PYTHONPATH=tools .venv_offline/bin/python tools/phase13_diagnostics.py \
  --workspace-root <workspace> \
  --output-dir <new-output-dir>
```

Decision replay is a fixed-pose approximation. It does not claim reachability, detour, path-length, or collision outcomes. It also needs the four-scene calibration corpus, not just `--run`. Phase 13 requires the fixed workspace layout and refuses existing designated outputs.

## Tier 4: host-only regeneration

Full Phase 13 regeneration and full-matrix rescoring need the original exported workspace (calibration `stages/` corpora, matrix run directories, v6 stage graphs). Those inputs are not in this mirror. Do not present Tier 4 as available from a clean clone.

## Evidence policy

Do not commit credentials, live ledgers, raw provider request bodies, or machine-specific paths. Keep new results in a unique evidence directory, add a row to `docs/RESULTS_INDEX.md`, and record material deviations in `tyrone_mirror/DEVIATIONS.md`.
