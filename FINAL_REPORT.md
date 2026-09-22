# Project closeout

The project is complete as an evidence-backed replication and extension study. The repository now contains the implementation, the offline evaluators, the campaign safeguards, the selected run artifacts, and a single results index. No further runs are assumed.

The original goal was to reproduce ASP and test three additions: whole-graph validation, calibrated ensemble support, and a risk-sensitive viewpoint score. The final evidence supports a smaller conclusion. Full ensemble unanimity removes many unsupported predicted nodes in the static graph and improves precision and normalized GED on the three-scene, 120 m DeepSeek matrix. The effect is stable across those runs, but the mechanism is best read as a property of that backend's ensemble disagreement. Calibration does not improve the static result at the useful endpoint and is harmful at some intermediate thresholds. The risk term is either nearly inactive or selects counterproductive viewpoints. Corrected decision replay shows a descriptive filtering effect on novel reference-object visibility, but it does not replay ROS reachability or a live counterfactual trajectory.

The completed DeepSeek matrix used scenes 00069, 00573, and 00853 with seed 42 and reached the 120 m target in all three runs. The full-budget, 120 m-capped static-policy results were:

| Scene | Official F1 | Unanimity F1 | Official normalized GED | Unanimity normalized GED | Recall change |
|---|---:|---:|---:|---:|---:|
| 00069 | 0.4789 | 0.5218 | 0.8969 | 0.8254 | 0.4747 → 0.4739 |
| 00573 | 0.3980 | 0.4349 | 0.9576 | 0.8877 | 0.3754 → 0.3743 |
| 00853 | 0.4578 | 0.4957 | 0.8561 | 0.7930 | 0.4461 → 0.4449 |

The guardrails passed on all three scenes: F1 loss stayed below the preregistered 0.05 limit and normalized GED did not increase. The frozen Phase 13 report records 752 expected completion slots, 686 available, 667 accepted, 19 rejected, and 66 missing. It also records the limits that remain material: false-positive detours are not identifiable, robot collisions are not instrumented, and combined live usefulness is not established.

The earlier 00069 short-run work established the baseline and exposed the main failure modes. The low-effort v3 25 m run reached tracked-graph AUC P=0.671, R=0.241, F1=0.352, normalized GED=1.075. The high-effort v5 comparison performed worse at its matched budget, with P=0.655, R=0.198, F1=0.302, normalized GED=1.189. This was a configuration result, not a clean causal estimate of reasoning effort, because parser survival and token configuration differed.

The later Gemini campaign ran the full 3-scene × 3-seed breadth design but did not reach the planned 120 m checkpoints. The final usable block, 00069 seed 42 v6, reached 19.5 m before the shared allocation exhausted its reservation budget. Its tracked graph reached P=0.692, R=0.336, F1=0.452, normalized GED=1.109 at stage 6. The zero-cost fixed-parser analysis found 55 available completions, all accepted, with 35 predicted nodes removed. The completion-policy AUC at the strictest support threshold was object P=0.769, R=0.184, F1=0.284, normalized GED=0.937. These are static prediction replays, not a claim about a live counterfactual trajectory.

The Gemini block consumed $18.552664 in settled spend across 898 requests. The summed reservation amount was $65.749854, which explains why the shared allocation stopped even though settled spend was lower. No further run is needed to interpret that result, and the remaining allocation is preserved for accounting rather than treated as permission to launch new work.

Across all ledgers, the code ceiling has $183.50 allocated of $190.00, leaving $6.50 for a new allocation. The settled total is approximately $18.80: capability probe $0.0038, native-count verification $0.0163, engineering pilot $0.5498, and scientific campaign $18.23. The scientific allocation is the only one with meaningful remaining room, but it is deliberately frozen. Unresolved entries remain accounted for in the original ledgers and are not silently treated as zero spend.

The project also produced substantive engineering results. The metered ledger now validates provider identities and usage, bounds retries, records raw responses without credentials, and separates stage and block identity in request IDs. The offline graph adapter now accepts the pipeline's real `node_type`, singular `dimension`, stringified vector, and pair-shaped edge fields. The final source tree includes regression tests for those cases and for the campaign control plane.

The repository is organized around four durable surfaces:

- `tools/` is the runnable implementation and test suite.
- `docs/RESULTS_INDEX.md` is the compact map from run family to result artifact.
- `tyrone_mirror/` contains selected evidence copied from the remote host, including evaluator JSON, policy replays, Phase 13 diagnostics, frontier references, and the final Gemini analysis.
- `docs/archive/` contains the chronological plans, reviews, reports, and operational notes that explain how the final result was reached without competing with the closeout documents.

The evidence supports publishing this project as a careful replication and negative-result study. It does not support claiming that the proposed calibrated risk-sensitive policy improves active exploration in live navigation.

## Verification

The final source tree was checked without starting a pipeline or contacting a provider. The offline suites pass: 186 `tools/tests` tests, 21 Gemini ledger tests, 14 prospective-campaign tests, 11 prospective-evaluation tests, 43 matrix-supervisor tests, and 11 evaluator fixture tests. Python bytecode compilation and canonical-document link checks also pass. The dependency setup and exact commands are in [docs/REPRODUCE.md](docs/REPRODUCE.md).
