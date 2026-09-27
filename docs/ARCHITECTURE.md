# Architecture and implementation

This page describes what the code does, where the research boundary is, and which metric each result uses. It reflects the source tree, not the historical campaign narrative.

## System boundary

The full simulator (ROS, Habitat, semantic mapping, datasets, weights) lives outside this repository in the remote workspace. This repository contains:

- offline evaluators and replay tools that read exported artifacts;
- the validity/support/calibration/decision policy code;
- metered request, budget, queue, and evidence infrastructure;
- tests, fixtures, and selected mirrored results.

The operative baseline is the pinned author commit plus documented working-tree deviations, not the bare commit alone. See `docs/prospective_overlay/README.md` and `tyrone_mirror/DEVIATIONS.md`.

## Dataflow

1. Mapping produces scene graphs; author preprocessing writes two tracked graphs (`graph0`, `graph1`).
2. Each track gets its own four-member language-model completion ensemble (eight intended files per checkpoint).
3. Completions feed viewpoint scoring only. They are never merged into the tracked map.
4. Three separate analyses read the frozen artifacts:
   - tracked-map evaluation (author-faithful evaluator);
   - static completion evaluation (canonical evaluator plus policies);
   - decision replay (fixed-candidate viewpoint comparison).

## Modules

| Area | Code | Role |
|---|---|---|
| Canonical adapter | `tools/asp_offline/author_io.py` | Converts author YAML (`node_type`, singular `dimension`, stringified vectors, pair-shaped edges) to the canonical schema; derives object-room parents |
| Structural validator | `tools/asp_offline/validator.py` | `validate_completion` rejects unparseable completions and completions that drop observed nodes; removes geometrically or structurally invalid predictions; `label_against_reference` adds post-hoc labels only |
| Support policy | `tools/asp_offline/support_policy.py` | `support_filtered_graph` keeps predicted nodes with support above `tau`; support is hits over the intended four (`expected_size=4`), never over the surviving count |
| Calibration | `tools/asp_offline/calibration.py`, `support_policy.fit_loso_calibrator` | Leave-one-scene-out isotonic mapping from raw support to calibrated probability; pooled across room/object hypotheses |
| Static evaluator | `tools/asp_offline/evaluator.py` | `evaluate_graph` and path-normalized `area_under_curve` used by the extension replay |
| Author-faithful evaluator | `tools/evaluator/` | `evaluate_run.py` scores tracked graphs with author-style matching and NetworkX GED |
| Static replay | `tools/extension_policy_replay.py` | Compares official, filter-only, raw-support, and calibrated-support policies on shared completions; averages members within tracks, tracks within stages, then integrates over path |
| Decision replay | `tools/decision_replay.py`, `tools/decision_replay_reference/` | Replays viewpoint selection with the pinned uncertainty calculator over one shared candidate pool; reports selection displacement and reference visibility, not trajectories |
| Phase 13 | `tools/phase13_diagnostics.py` | Frozen calibration, validator, guardrail, replay, and availability diagnostics; fails closed on missing inputs |
| Metered ledger | `tools/gemini_campaign/` | SQLite allocations, reservation/dispatch/settlement states, bounded retries, offline summary/export/checksum |
| Campaign control | `tools/prospective_campaign/` | `CampaignSupervisor` records launch intent and certifies paired members; it does not execute runs itself |
| Runtime transport | `tools/prospective_runtime/` | Gemini request shaping, token bounds, dry-run launcher (`run_campaign.py` refuses live mode without audited contracts) |
| Author overlay | `tools/prospective_integration/` | Hash-checked pipeline patch that routes model calls through the ledger; historical deployment surface |
| Prospective evidence | `tools/prospective_eval/` | Receipt, classification, detour, and runner helpers; consistency checks, not authenticated causal proof |
| Matrix supervisor | `tools/matrix_supervisor/` | Host-side DeepSeek run queue, safety checks, and state machine; `--check` and `--once --dry-run` are the inspection modes |

## Metric glossary

Two evaluators produce numbers that look similar but are not interchangeable. Name the evaluator beside every result.

| Metric | Author-faithful (`tools/evaluator/`) | Static/canonical (`tools/asp_offline/evaluator.py`) |
|---|---|---|
| Graph population | Object and room nodes only; door-named and other types dropped (`graph_io.py`) | Object and room nodes from the canonical schema |
| Object matching | Greedy prediction-order, exact-name, distance below 0.5 m (`matching.py`) | Globally distance-sorted, same-label, distance at or below 0.5 m; rooms at 4.0 m (`evaluator.py`) |
| GED | NetworkX edit distance with parent-aware substitution costs; reported values are best-found upper bounds under the 60 s timeout (`ged.py`) | Node plus edge edit proxy computed from the fixed mapping; predicted edges with unmatched endpoints are dropped before the edge comparison (`evaluator.py`) |
| Aggregation | Per-stage precision/recall/F1/GED | Path-normalized area under the curve; state the budget (120 m matrix, 19.5 m partial Gemini block) |

Other terms:

- `tau`: raw support cutoff over `{0, 0.5, 0.75, 1.0}`; `tau=1.0` keeps predictions supported by all four intended members.
- `calibration.status`: read before interpreting any calibrated row; `LOSO_CALIBRATED` is the fitted result, `UNCALIBRATED_PROVISIONAL` is not.
- Guardrail policy: `filter_plus_support_threshold_calibrated_tau_1.0` (validator plus unanimity), requiring absolute F1 loss at most 0.05 and normalized-GED relative increase at most 10 percent. The measured GED decrease is an outcome, not a gate.
- Full-graph true-positive retention near 99.7 percent is dominated by the unchanged observed map; it is a FULL-GRAPH measure, not predicted-only retention. Predicted-only true positives drop (see Phase 13 validator diagnostics).

## Status labels

- Implemented and fixture-tested: adapter, validator, support denominator, LOSO plumbing, static replay, decision-replay harness, ledger accounting, control-plane transitions, overlay routing.
- Historically exercised: metered Gemini generation across partial blocks; host-side DeepSeek matrix runs.
- Not integrated or not established: live navigation improvement, detour reduction, collision reduction, cross-platform deployment, authenticated causal evidence.

## Known limitations (recorded, not fixed here)

- `Node.as_dict()` does not serialize the in-memory `observed` flag (`models.py`). `support_filtered_graph()` concatenates observed nodes with kept completion nodes (`support_policy.py`). An echoed observed id that reaches support without a marker can therefore appear twice. The mirrored v6 summary shows one stage where the unanimity count (38) exceeds every validated member count (max 37), consistent with this path. The canonical extension replay follows a separate normalization path; it is not automatically invalidated by this finding, but no blanket unaffected claim is warranted. No frozen number was changed.
- The validator is a deterministic structural filter, not a full consistency proof: predicted rooms check for a center but not finite coordinates; parent checks precede later removals without a final cascade; room overlap checks cannot operate on center-only room boxes; geometry is axis-aligned and ignores orientation.
- Decision replay changes the stage-one shortlist and rescores without reapplying risk; it bypasses the reference history-distance candidate filter and has no ROS reachability gate.
- Budget accounting is per SQLite file and sums historical reservations; settlement does not release reservation slack. Ceiling arithmetic is not spending permission.
- `EvidenceReceipt` checks hashes, not issuer authenticity; an empty reviewer allowlist permits arbitrary reviewer strings; branch cleanup is not in a `finally` block.
- `tools/matrix_supervisor/CONTROL.json` retains its historical `"paused": false` value. Operational retirement is enforced by the inactive, disabled supervisor service, verified on 27 September 2026; no matching experiment processes were observed.
- The [input manifest](audit/2026-09-27-input-manifest.json) records three source files that differ between the host and this repository: `tools/asp_offline/models.py`, `tools/asp_offline/validator.py`, and `tools/decision_replay.py`. It preserves both hashes; matching frozen result inputs does not make these source versions interchangeable.
