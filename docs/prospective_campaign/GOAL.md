# Goal: implement the prospective campaign control plane

## Scorecard

- Deterministic queue and exact policy names: 100% order test pass.
- Admission safety: every admitted unit has a full-pair/block budget
  reservation and healthy technical state.
- Crash safety: status is atomic, events append-only, markers follow hash
  validation, and partial trajectories are never merged.
- Scientific safety: claim gates return `not_established` or
  `not_identifiable` when their prerequisites are missing.

## Done when

The commands in `SPEC.md` pass; no paid API, credential, Tailscale, or run is
invoked; and the branch contains the namespaced implementation and contract
docs with an auditable scope decision.

## Workflow

1. Probe capability (maximum $2), then engineering pilot (maximum $18):
   paired scene 00069 seed 42, exactly one planning/navigation stage, then stop.
2. Exclude pilot from confirmatory tables. Compute enforceable worst-case pair
   cost, including unresolved spend and thinking-token uncertainty, and select a
   common cumulative path horizon in meters before any outcome is inspected.
3. Admit the seed-42 3-pair block only if its complete reservation fits;
   admit seed 43/44 blocks only if each complete block fits. Never promise 18
   runs.
