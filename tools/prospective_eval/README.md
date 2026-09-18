# Prospective motion/detour evaluation

This package is a passive overlay contract. Passive mode never calls
`set_state`, steps Habitat, consumes RNG, changes observations, or changes
controller decisions. It records requested distance, actual displacement,
target position/rotation error, and clipping separately. `REACHED` requires
both position and rotation errors within `1e-4`.

Navmesh/pathfinder rejection, clipping, planner failure, object-box overlap,
physical contact, blocked motion, and unknown are separate event classes.
Pathfinder exceptions and invalid distances become `unknown`; no exception is
treated as contact. A Habitat adapter must implement only query operations and
must document that it does not mutate simulator state.

`ControllerMode.COLLISION_AWARE_EXPERIMENT` is disabled by default. Contact or
blocked motion requires a validated allowlisted engine receipt with source,
event type, matching execution ID, timestamp, provenance hash, and the relevant
flag. It is a separate controller-altered experiment.

## Exact detour evidence

`evaluate_intervention` accepts only immutable, hashed receipts: an externally
reviewed FP label, complete common snapshot manifest, restore and execution
receipts for both branches, reachability/target receipts, monotonic path
samples, completion, useful-observation criteria, and state/external hashes.
It recomputes path lengths and fails closed on missing or forged evidence.
`reference_unmatched` remains `unknown`. Independent policy trajectories use
`paired_policy_comparison`, a descriptive path/attribution result whose causal
false-positive-detour field is always `not_identifiable`.

`BranchRunner` requires declared exact-restore, RNG, observation, filesystem,
and isolation capabilities; it restores a clean baseline after both branches.

`AppendOnlyLog` requires a contained owner-only regular file, uses an exclusive
lock and fsync, and chains sequence/digest values. `verify()` detects tampering.
No secrets or free-form credentials belong in receipt payloads; only stable IDs
and hashes should be imported from external systems.
