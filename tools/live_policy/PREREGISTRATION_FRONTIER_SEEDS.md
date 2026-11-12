# Pre-registration: seeded frontier explorer (plan step 7)

Written 2026-10-29 22:25 IST, before any run below starts. This is step 7 (B1) of the plan in docs/checkin/review_2026-10-29/SYNTHESIS_AND_NEXT_PLAN.md §6. Today there is one deterministic frontier run per scene, so no statement comparing ASP's arms with frontier exploration is possible.

## Runs
- Explorer: the author's `frontier_baseline.py` at commit f1ea141b, with one opt-in change. If `ASP_START_JITTER_SEED` is set, the start moves by dx, dz ~ U(−0.25, 0.25) m (habitat x and z, numpy default_rng(seed)), snapped to the navmesh. The file's hash goes from 25c6a5d5 to e5ffa2a9; the original is kept beside it as `.orig_25c6a5d5`. With the variable unset, behaviour is unchanged.
- Cells: scenes 00853 and 00871 × seeds 42, 43, 44, so 6 runs, one at a time in container asp-noetic, run names `frontier_seeds/e4_<scene>_s<seed>_frontier_60m` (so e1_analysis.py parses them as arm "frontier").
- Stop: at the first stage whose navigation_stats.json gives total_path_length_meters ≥ 60, or when the explorer reports "Exploration complete", or after 6 h.
- Exclusion: a run that stops below 50 m is rerun once with the same seed.

## Metric
Author-faithful object F1 AUC to 60 m against the HM3D human annotation (live_score.py, hm3d_auc_af_f1_to_60m), the E1 primary metric. AUC to 50 m serves as the sign check. The frontier-made reference is not used, because it is one frontier run's own map.

## Tests
Two contrasts, run the way E1 is: e1_analysis.py, a scene-blocked exact permutation, two-sided, with alpha 0.05 for each.
- official − frontier: counted official runs (2 on 00853, 3 on 00871) against the 3 seeded frontier runs per scene; 200 relabelings.
- placebo − frontier: counted placebo runs (3 per scene) against the 3 frontier runs; 400 relabelings.

Holm over the two. Effects count only if the 60 m and 50 m results agree in sign. Null results use the registered null form; never "equal".

## Reading (the plan's decision rule)
- **Neither contrast is significant:** report "neither LLM nor random guesses beat nearest-frontier on these homes", with the CI of each contrast.
- **Frontier is significantly above an arm:** say so for that arm.
- **An arm is significantly above frontier:** say so. No sentence credits LLM content unless official − frontier is significant and placebo − frontier is not, and even then only as a difference between two tests, not a test of content.

## Not changed
No registered E1-E3 result changes. These runs are new evidence beside them.
