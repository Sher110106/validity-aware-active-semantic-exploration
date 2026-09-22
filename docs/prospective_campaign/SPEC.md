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

## Done when

1. `python3 -m unittest discover -s tools/prospective_campaign/tests` passes.
2. Queue, pair reservations, budget caps, controls, atomic status/events,
   artifact markers, manifests, and claim gates are covered by tests.
3. `GOAL.md`, `PLAN.md`, `CONTROL.md`, `STATUS.md`, and `WORKING_MEMORY.md`
   remain namespaced under this directory.

## Feedback loop

Run `PYTHONPATH=tools python3 -m unittest discover -s tools/prospective_campaign/tests`
after each control-plane change; run repository tests, `compileall`, diff inspection, and secret scan
before commit. These validate orchestration without paid APIs or live runs.
