# Notes on the 13 Nov paper-scale rescore

**State: final.** Written 2026-11-17T17:04:25+05:30. Rerun with `bash tools/live_policy/host/rescore_paper.sh`. The rules are `PREREGISTRATION_PAPER.md`, Amendment 2 and its Note. Tables: `paper_compare.md` and `.json`. Evidence: `acceptance_*.json`, `folder_map_*`, `c2_*.json`, `budgets_*.json`, `comparison_vs_1112.json`, `rescore_summary.json`.

## What changed against 11-12, and why

1. **Acceptance first.** `check_paper_runs.py` ran on the host before any score (`acceptance_20261117T170055.json`). 10 e7 runs count as valid: 00853_s42, 00853_s43, 00853_s44, 00853_s45, 00853_s46, 00871_s42, 00871_s43, 00871_s44, 00871_s45, 00871_s46. 8 other attempts fail A2.1 and stay out of every paper cell: 00871 s42 #1, 00871 s42 #2, 00871 s43 #1, 00871 s43 #2, 00871 s44 #1, 00871 s44 #2, 00871 s45 #1, 00871 s45 #2: no 'Exploration complete' and no 250 m / 4 h stop, roslaunch.log shows out of memory or nvblox_node dead.
2. **Budget B** is now set by script (A2.3). The primary B is the median end time of the valid runs that logged "Exploration complete"; fewer than 2 means the registered fallback. 00853: B = 632.1751 s (median, 5 valid run(s)); 11-12 used 632.1751 s; 00871: B = 1300.2523 s (median, 4 valid run(s)); 11-12 used 809.0840 s. A capped run changes the second line; it is scored in `alt_B_with_capped/`.
3. **C2** was computed and filed (`c2_20261117T170055.json`) before any run was scored. 00853: F1 0.7511 (precision 0.7545, recall 0.7477); APR-b holds 110 objects, APR-a 111; nvblox did not die during it. It is below 0.90, so the slide says the reference moves by more than the paper's margins (2.7-7.9 points), and also says APR-a's damage is part of it. 00871: F1 0.7714 (precision 0.7570, recall 0.7864); APR-b holds 107 objects, APR-a 103; nvblox did not die during it. It is below 0.90, so the slide says the reference moves by more than the paper's margins (2.7-7.9 points), and also says APR-a's damage is part of it. In both APR-a tours nvblox died partway, and each final graph lacks about the last 60 s of its tour (results_paper_compare_1112/NOTES.md, items 3 and 4). A C2 below 0.90 therefore mixes that damage with real movement of the reference, and the slide says so.
4. **Tours.** The table below gives, for every tour, whether nvblox died, the "Timeout! Did not find" lines, the last archived stop whose graph changed, and the object nodes at stage 0 and at the end (A2.4).
5. **Folders.** The queue renames an older attempt to `*_FAILED_ATTEMPT_HHMM` when the next one launches, and HHMM is that launch's time. The map is in `folder_map_*.json`. The laptop copy for this run is `runs_1113/` beside the 11-12 `runs/`, which stays as it was: in the old copy the folder `apr_00853_b` holds the old frozen tour, which on the host now sits in `apr_00853_b_FAILED_ATTEMPT_1707`. The folder `e7_00853_s42_frontier_end_FAILED_ATTEMPT1_gpu_oom` holds an attempt from before the queue log (11-06) that made no stage graph: its roslaunch.log shows 2 out-of-memory line(s) and 1 line(s) saying nvblox_node died. The queue log has no launch line for it, so it is in no row. Seed 42 of 00853 is scored from its later attempt.
6. **GED.** 14 runs reuse their 11-12 GED, because their stage list (stage, path length, time) is equal. 4 runs were computed on the host. Recheck of reused values on the host: not asked for. Reuse goes by content, not by folder name, because the queue gives the plain name to the next attempt.
7. **00853 against 11-12.** 162 cells compared; 162 identical, 0 different. B did not move and the inputs match 11-12's, so these numbers equal 11-12's.
8. **00871 against 11-12.** 243 cells compared; 102 identical, 141 different. B moved, from 809.0840 s to 1300.2523 s, so the cells differ. Every 00871 number in `results_paper_compare_1112/` is superseded by this folder.

## Budgets

| Scene | Primary B (s) | Rule | Valid runs with "Exploration complete" | B with capped runs (s) | 11-12 B (s) |
|---|---|---|---|---|---|
| 00853 | 632.1751 | median | 5 | 632.1751 | 632.1751 |
| 00871 | 1300.2523 | median | 4 | 1337.0149 | 809.0840 |

## Tours (A2.4)

Object nodes count every object node, doors included, as the frozen test counts them (the F1 count, which leaves out doors, is in `c2_*.json`). Frozen means the final graph0 holds the same object nodes as stage 0.

| Tour folder | Attempt | Frozen | nvblox died | Timeout lines | Last stop whose graph changed | Objects, stage 0 | Objects, end | Waypoints reached/listed |
|---|---|---|---|---|---|---|---|---|
| `apr_00853_a` | 1 | no | yes | 0 | 85 | 5 | 118 | 85/85 |
| `apr_00853_b` | 2 | no | no | 0 | 85 | 4 | 117 | 85/85 |
| `apr_00853_b_FAILED_ATTEMPT_1707` | 1 | yes | no | 18 | none | 2 | 2 | 85/85 |
| `apr_00871_a` | 1 | no | yes | 7 | 66 | 3 | 117 | 66/66 |
| `apr_00871_b` | 2 | no | no | 0 | 66 | 7 | 119 | 66/66 |
| `apr_00871_b_FAILED_ATTEMPT_1020` | 1 | yes | yes | 14 | none | 4 | 4 | 66/66 |

## Status of the two scenes

- **00853: final.** B did not move.
- **00871: final.** B moved from 809.0840 s to 1300.2523 s, so every 00871 number in `results_paper_compare_1112/` is **superseded** by this folder.

## Carried over from 11-12 (`results_paper_compare_1112/NOTES.md`)

- Item 1, order of the checks: C1-C5 were computed with the first scoring on 11-12 (deviation 42). Still true as history. This run files C2 first.
- Item 2, C2 not valid: superseded for 00853 by its APR-b rerun (F1 0.7511); superseded for 00871 by its APR-b rerun (F1 0.7714).
- Item 3, APR-a final graphs end about 60 s early: holds. APR-a is unchanged and stays the reference on both scenes.
- Item 4, nvblox died partway through some tours: the tour table above gives it per tour (died in apr_00853_a, apr_00871_a, apr_00871_b_FAILED_ATTEMPT_1020). APR-a is still used because the tours move on navmesh paths and Hydra kept growing the graph.
- Item 5, end times leave out the final leg: holds, and B uses the same rule for every run.
- Item 6, the 853 100% cell covers 3 of 5 runs: holds while B is 632.1751 s; read the n in each cell.
- Item 7, stages without a graph take the graph of the stage before: holds for the crashed first attempt of seed 44 (its folder is unchanged since 11-12).
- Item 8, GPU sharing: the Note to Amendment 2 corrects the statement (the first attempt of seed 42 launched under the 12 GB check), and so does deviation 40. The third attempts were queued under the 12 GB check (deviation 45); this pipeline does not test the GPU at launch.
- Item 9, C1 floor area far off: holds. C1, C3, C4 and C5 depend on APR-a only and are not recomputed (`results_paper_compare_1112/c_checks.json`).
- The frontier clock finding (11-12 NOTES, last section): holds, unchanged.

## For the deviations file

**11-06: an attempt of e7 00853 seed 42 that made no stage.** The folder `e7_00853_s42_frontier_end_FAILED_ATTEMPT1_gpu_oom` holds an attempt from before the queue log (11-06) that made no stage graph: its roslaunch.log shows 2 out-of-memory line(s) and 1 line(s) saying nvblox_node died. The queue log has no launch line for it, so it is in no row. Seed 42 of 00853 is scored from its later attempt.
