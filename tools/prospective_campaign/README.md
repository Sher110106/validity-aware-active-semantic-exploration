# Prospective paired campaign v5 contract

This is the historical offline contract that governed the campaign
implementation. The campaign is now complete and frozen; this file is kept
for provenance and must not be read as authorization for another paid run.

## Goal

Provide an unattended, outcome-blind control plane for a prospective paired
comparison of official ASP (`official_asp`) and
`validator_plus_unanimity_raw_tau_1_0`. The latter is equivalent in node
selection to Phase13 `filter_plus_support_threshold_calibrated_tau_1.0`
because `calibrator(raw_tau=1.0)` is the cutoff. It validates completions,
retains predictions supported by all four intended members per independent
graph track, and always preserves the observed map.

It is **not** the old beta-R risk reranker and must never be called an exact
test of that policy. DeepSeek LOSO probabilities are not Gemini probabilities.

## Fixed facts

- Model: `gemini-3.8-flash`, exact source tag `authoritative-v5-2026-09-17`,
  standard rates $0.75/M input + $3.75/M candidate output. Thinking-token cost
  remains unresolved and is included conservatively after the pilot.
- Reasoning: `thinking_level=medium`; no fallback.
- User cap $200; broker ceiling $190 = normal $180 + recovery $10; $10 margin.
- The final campaign used the audited sibling runtime and is represented by
  the evidence under `../../tyrone_mirror/`; this contract itself performs no
  paid calls and authorizes no new launch.
- Queue is fixed seed-major by the order in `tools/prospective_campaign/queue.py`.
- Horizons are cumulative path-distance budgets `horizon_m` from 120/75/50/25
  meters, never minutes, selected before outcomes and common to every pair in a
  complete three-scene seed block. Wall-clock runtime is independent.
- Pilot: paired scene 00069 seed 42, exactly one planning/navigation stage,
  then stop; excluded from confirmatory tables.
- Historical prior: one-policy 120m three-scene costs $194.46 ($62.52 +
  $71.49 + $60.46), one-policy 25m costs $11.693/$8.7299/$11.9878, a paired
  25m block costs about $64.82, and the one-stage pair costs about $1.54.
  These exclude unknown Gemini thinking tokens; 75m/120m paired blocks are
  ruled out under $200, while 50m ($117.62 base) may be rejected after pilot.

## Non-goals and limitations

This does not reproduce the original Gemini/ASP paper, transfer DeepSeek
probabilities, test beta-R, or establish live navigation without complete
paired blocks. Connectivity loss, unknown in-flight spend, invalid controls,
artifact uncertainty, and technical stalls fail closed.

## Scorecard and claim gates

Record paired completion, invalid-hypothesis validity, FP-detour reduction,
F1 loss, and GED increase. Combined usefulness requires a complete paired
block, valid invalid-hypothesis gate, measurable positive FP-detour reduction,
F1 loss <= 0.05, and GED increase <= 10%. A zero baseline detour or missing
detour instrumentation is `not_identifiable`; incomplete pairs are excluded.

## Controls

Merged from the former `CONTROL.md`. The enforcing code is `control.py` (the `Control` dataclass).

Only these sidecar controls are permitted: `paused`, `stop`, monotonically increasing `resume_generation`, exact `approved_hashes`, and conservative attempt, disk, stall and runtime floors. Unknown keys or changed approved hashes pause without taking a resource action. `stop=true` is terminal for the controller instance. Connectivity loss and unknown spend are automatic stops.

## Campaign scorecard and admission rule

Merged from the former `GOAL.md`, the implementation goal for this control plane. It was a historical contract. The control plane and its tests are complete and the campaign is frozen; the final disposition is in [`../../docs/RESULTS.md`](../../docs/RESULTS.md).

Scorecard:

- Deterministic queue and exact policy names: 100% order-test pass.
- Admission safety: every admitted unit has a full-pair or block budget reservation and a healthy technical state.
- Crash safety: status is atomic, events are append-only, markers follow hash validation, and partial trajectories are never merged.
- Scientific safety: claim gates return `not_established` or `not_identifiable` when prerequisites are missing.

Workflow:

1. Probe capability (maximum $2), then an engineering pilot (maximum $18): paired scene 00069 seed 42, exactly one planning/navigation stage, then stop.
2. Exclude the pilot from confirmatory tables. Compute the enforceable worst-case pair cost, including unresolved spend and thinking-token uncertainty. Pick a common cumulative path horizon in meters before any outcome is inspected.
3. Admit the seed-42 3-pair block only if its complete reservation fits. **Admit seed 43/44 blocks only if each complete block fits. Never promise 18 runs.**

The implementation is offline-safe by default; no new paid API call is planned.

## Implementation plan and scope decision

Merged from the former `PLAN.md`. All items were done except one:

- Open: implement adapters for the budget broker and the motion/detour runner in separate cherry-pickable branches.

Scope decision artifact: after the pilot, the controller writes a terminal scope decision. It holds the pilot ledger, the worst-case pair estimate, the selected horizon, the reservations, and whether each complete block fit. It is a decision record, not a promise to run a fixed number of attempts.

Prior (same numbers as "Historical prior" above): paired 120m and 75m are ruled out under the $200 cap. A paired 50m block has a $117.62 base estimate before thinking and may be rejected. 25m is the likely minimum useful block. Admitting a block lowers the remaining ledger for the next one.

## Working rule

Merged from the former `WORKING_MEMORY.md`, a placeholder that was never filled in. Its one rule: never replace an existing attempt directory or infer outcomes from queue position. Pilot ledger, worst-case pair cost, horizon, reservations, stop reasons and the scope decision belong in append-only machine artifacts.

## Status

Merged from the former `STATUS.md`. Implementation is complete and the campaign is frozen. No new campaign, paid call or credential operation is planned. The terminal scope decision and evidence summary are in [`../../docs/RESULTS.md`](../../docs/RESULTS.md). The experimental policy is `validator_plus_unanimity_raw_tau_1_0`, not beta-R. The live-navigation and detour claim gates stay closed because the evidence does not establish those outcomes.

## Done when

1. `python3 -m unittest discover -s tools/prospective_campaign/tests` passes.
2. Queue, pair reservations, budget caps, controls, atomic status/events,
   artifact markers, manifests, and claim gates are covered by tests.
3. `GOAL.md`, `PLAN.md`, `CONTROL.md`, `STATUS.md`, and `WORKING_MEMORY.md`
   remain namespaced under this directory.

*Note added 2026-11-12:* item 3 is historical. It named five sibling files in `docs/prospective_campaign/`. Those files (`GOAL.md`, `PLAN.md`, `CONTROL.md`, `STATUS.md`, `WORKING_MEMORY.md`) are now merged into this README as the sections "Controls", "Campaign scorecard and admission rule", "Implementation plan and scope decision", "Working rule" and "Status". They remain in git history.

## Feedback loop

Run `PYTHONPATH=tools python3 -m unittest discover -s tools/prospective_campaign/tests`
after each control-plane change; run repository tests, `compileall`, diff inspection, and secret scan
before commit. These validate orchestration without paid APIs or live runs.
