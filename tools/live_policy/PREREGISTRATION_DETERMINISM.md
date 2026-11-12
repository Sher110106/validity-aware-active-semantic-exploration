# Pre-registration: deterministic stage snapshot (plan step 8)

Written 2026-10-29 22:45 IST, before any run below starts. This is step 8 of docs/checkin/review_2026-10-29/SYNTHESIS_AND_NEXT_PLAN.md §6 (A's B2). Same-seed runs of one arm split at the first stop in 14 of 15 pairs. The working cause: the pipeline snapshots the map file at its first stable size after the scan, before the mapper has taken in the whole scan.

## Change
`exploration_pipeline.py` (backup `.orig_2f17aa29`; patched hash 4b1bcb52) gains an opt-in quiet wait. When ASP_DSG_QUIESCENT_S is set, a snapshot is taken only after the map file's bytes stay identical for that many seconds, capped at ASP_DSG_QUIESCENT_MAX_S (default 120 s). Unset, the author's rule is unchanged. live_runner.py passes a job's `env` into the container (hash 940be66b), and run_live_run.sh records the setting in each run's manifest (hash 25cfe606).

## Runs
Three replicates: placebo, scene 00853, seed 42, target 15 m, max_hours 2, pacing 260,400,500 (as e1_00853_s42_placebo_60m), ASP_DSG_QUIESCENT_S=15, ASP_DSG_QUIESCENT_MAX_S=120. Names e5_00853_s42_placebo_15m_q1, _q2, _q3, run one at a time in asp-noetic after the frontier queue. $0.

## Measures
For each replicate pair:
- **(a) Stage-0 maps match:** in both tracks the same object label multiset, and every object within 0.10 m (xy) of a same-label object in the other replicate.
- **(b) Stops agree:** the stage-0 stop (last point of stages/1/executed_path.json) lies within 0.25 m of the other replicate's.
- **(c)** The same two checks at stages 1 and 2.

The comparison baseline is the three same-seed placebo attempts on 00853/42 without the change: the counted run and its two archived attempts. Measures (a) and (b) are computed for them too.

## Decision (the plan's)
- **All three pairs meet (a) and (b):** runs can be paired by seed, so future designs should pair them.
- **Otherwise:** plan at least 5 replicates per cell, and say whether the change moved the replicates closer than the baseline did.
