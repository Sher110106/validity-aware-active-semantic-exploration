# Reproduce and inspect

All commands below are offline. They do not start the pipeline or call a provider.

## Environment

The offline tools require Python 3.10+ and the packages in
`tools/asp_offline/requirements.txt`. A local setup is:

```sh
python3 -m venv .venv_offline
.venv_offline/bin/python -m pip install -r tools/asp_offline/requirements.txt pytest
export PYTHONPATH=tools
```

## Tests

From the repository root:

```sh
PYTHONPATH=tools .venv_offline/bin/python -m unittest discover -s tools/tests -v
PYTHONPATH=tools .venv_offline/bin/python -m unittest discover -s tools/gemini_campaign/tests -v
PYTHONPATH=tools .venv_offline/bin/python -m unittest discover -s tools/prospective_campaign/tests -v
PYTHONPATH=tools .venv_offline/bin/python -m unittest discover -s tools/prospective_eval/tests -v
PYTHONPATH=tools .venv_offline/bin/python -m unittest discover -s tools/matrix_supervisor/tests -v
PYTHONPATH=tools .venv_offline/bin/pytest -q tools/evaluator/tests
PYTHONPATH=tools .venv_offline/bin/python -m compileall -q tools
```

The evaluator fixture suite uses pytest. Real author YAML replay additionally
requires PyYAML. Decision replay uses the pinned reference implementation in
`tools/decision_replay_reference/`; when the original Linux checkout is
available, the replay script still prefers that checkout.

## Author-faithful evaluator

```sh
PYTHONPATH=tools python3 tools/evaluator/evaluate_run.py \
  --run <run>/stages \
  --gt <reference>/stages/<checkpoint>/habitat_scene_graph_original_graph0.yaml \
  --out eval_results.json
```

This scores the tracked graph produced by the author pipeline. It does not merge LLM completions into the tracked graph.

## Static extension replay

```sh
PYTHONPATH=tools python3 tools/extension_policy_replay.py \
  --run <run>/stages \
  --reference <reference>/stages/<checkpoint>/habitat_scene_graph_original_graph0.yaml \
  --budget-m 120 \
  --output extension_policy_replay.json
```

The four-member denominator is explicit. Read `calibration.status` before interpreting calibrated rows.

## Decision replay and Phase 13

```sh
PYTHONPATH=tools python3 tools/decision_replay.py \
  --scene-id 00069 \
  --run <run>/stages \
  --reference <reference>/stages/<checkpoint>/habitat_scene_graph_original_graph0.yaml \
  --out-dir <new-output-dir> \
  --out-filename decision_replay.json

PYTHONPATH=tools python3 tools/phase13_diagnostics.py \
  --workspace-root <workspace> \
  --output-dir <new-output-dir>
```

Decision replay is a fixed-pose approximation. It does not claim reachability, detour, path-length, or collision outcomes.

## Evidence policy

Do not commit credentials, live ledgers, raw provider request bodies, or machine-specific paths. Keep new results in a unique evidence directory, add a row to `docs/RESULTS_INDEX.md`, and record material deviations in `tyrone_mirror/DEVIATIONS.md`.
