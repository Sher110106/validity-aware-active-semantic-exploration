# Prospective motion/detour evaluation

`tools/prospective_eval` is a passive, append-only instrumentation layer. It
does not call `agent.set_state`, step Habitat, alter observations, consume RNG,
or change controller decisions. Its primary event is a **navmesh/path audit**;
it does not call that event a robot collision.

## What is measurable

Passive mode can record requested/result poses, nominal and pose-derived
distance, planner/reachability outcomes, read-only navmesh admissibility,
clipping, reset/teleport/rotation flags, hashes, and timestamps. A
`physical_contact` event is valid only when a controller-altered adapter reports
an engine contact signal. Object-box overlap and planner failure remain their
own taxonomy values.

The optional `collision_aware_experiment` contract is disabled by default. It
changes execution semantics and must be evaluated as a separate experiment;
results are not method-faithful comparisons unless both policies use it.

## Detour preregistration

Emit `false_positive_detour` only when the same exact snapshot is restored,
the counterfactual is demonstrably FP-dependent, both branches execute live,
the reference supports the FP claim, the alternative is shorter, and no
preregistered useful-observation criterion is lost. Reference-unmatched labels
are never treated as physical absence; otherwise the result is
`tradeoff`, `unknown`, or `not_identifiable`.

`BranchRunner` fails closed when exact state restoration cannot be verified.
Use `fixed_stage_samples` and report both eligible and missing stages.

## Overlay guidance

Deploy this package only through a controlled sibling/overlay wrapper around
the pinned author pipeline. The wrapper should observe command/pose boundaries,
invoke `PassiveNavmeshAuditor` with a read-only Habitat adapter, and append
`MotionEvent.as_dict()` records. Do not patch the pinned checkout or silently
replace `set_state`. No LLM calls are made by this package.
