# Validity-Aware Active Semantic Exploration

This repository contains the completed implementation and evidence record for a course project built on the Active Semantic Perception (ASP) pipeline. The project reproduced the pinned ASP baseline, added a fail-closed graph validator, ensemble-support filtering, leave-one-scene-out calibration, risk-sensitive decision replay, a metered Gemini integration, and an auditable campaign control plane.

The experiments are frozen. No more paid runs are planned. The final interpretation is deliberately narrower than the original proposal: unanimity filtering is a useful static graph diagnostic for this backend; calibration and the risk term are not positive contributions; decision replay is informative but cannot establish live navigation improvement, detour reduction, or collision reduction.

Start here:

- [Final closeout](FINAL_REPORT.md) for the project conclusion, scope, and remaining limits.
- [Results index](docs/RESULTS_INDEX.md) for the run inventory and the primary numbers.
- [Reproduction guide](docs/REPRODUCE.md) for offline tests and replay commands.
- [Evidence map](tyrone_mirror/README.md) for the mirrored run artifacts and their provenance.
- [Deviation log](tyrone_mirror/DEVIATIONS.md) for the dated engineering audit trail.

The implementation is under `tools/`. The most important entry points are:

- `tools/evaluator/` reproduces the author's tracked-graph precision, recall, F1, and GED measurements.
- `tools/asp_offline/` contains the canonical graph adapter, validator, support policy, calibration, and static evaluator.
- `tools/extension_policy_replay.py` compares completion policies over the same cached artifacts.
- `tools/decision_replay.py` replays candidate selection with the pinned uncertainty calculator.
- `tools/phase13_diagnostics.py` generates the frozen multi-scene diagnostics.
- `tools/gemini_campaign/`, `tools/prospective_campaign/`, `tools/prospective_runtime/`, and `tools/prospective_integration/` contain the metered campaign components and overlay.

The pinned research checkout is not included or modified here. The campaign ran against a sibling checkout and preserved the relevant metadata under `tyrone_mirror/`. Credentials, live ledgers, raw provider requests, and machine-local runtime state are excluded from this repository.

## Verification

The final source tree was merged from the completed `prospective/integration` branch. The offline suites cover the ledger, campaign control plane, runtime overlay, evaluator, validator, and evidence instrumentation. Run the commands in [docs/REPRODUCE.md](docs/REPRODUCE.md) before publishing a new revision.

## Publishing

The working tree is prepared as a clean local Git history, but this checkout
does not have a GitHub remote configured. Add the destination repository as
`origin` and push the final commit when you are ready.
