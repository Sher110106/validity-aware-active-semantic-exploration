# Notes on the 13 Nov paper-scale rescore

**State: interim.** Written 2026-11-13T19:13:50+05:30. Rerun with `bash tools/live_policy/host/rescore_paper.sh`. The rules are `PREREGISTRATION_PAPER.md`, Amendment 2 and its Note. Tables: `paper_compare.md` and `.json`. Evidence: `acceptance_*.json`, `folder_map_*`, `c2_*.json`, `budgets_*.json`, `comparison_vs_1112.json`, `rescore_summary.json`.

## What changed against 11-12, and why

1. **Acceptance first.** `check_paper_runs.py` ran on the host before any score (`acceptance_20261113T191301.json`). 6 e7 runs count as valid: 00853_s42, 00853_s43, 00853_s44, 00853_s45, 00853_s46, 00871_s46. 8 other attempts fail A2.1 and stay out of every paper cell: 00871 s42 #1, 00871 s42 #2, 00871 s43 #1, 00871 s43 #2, 00871 s44 #1, 00871 s44 #2, 00871 s45 #1, 00871 s45 #2: no 'Exploration complete' and no 250 m / 4 h stop, roslaunch.log shows out of memory or nvblox_node dead.
2. **Budget B** is now set by script (A2.3). The primary B is the median end time of the valid runs that logged "Exploration complete"; fewer than 2 means the registered fallback. 00853: B = 632.1751 s (median, 5 run(s)); 11-12 used 632.1751 s; 00871: B = 809.0840 s (fallback, 1 run(s)); 11-12 used 809.0840 s. No valid run stopped at a cap, so the second line (B with capped runs) equals the primary.
3. **C2** was computed and filed (`c2_20261113T191301.json`) before any run was scored. 00853: F1 0.7511 (precision 0.7545, recall 0.7477); APR-b holds 110 objects, APR-a 111; nvblox did not die during it. It is below 0.90, so the slide says the reference moves by more than the paper's margins (2.7-7.9 points), and also says APR-a's damage is part of it. 00871: not computed. The only APR-b run is frozen and its rerun has not run. C2 waits for it. In both APR-a tours nvblox died partway, and each final graph lacks about the last 60 s of its tour (results_paper_compare_1112/NOTES.md, items 3 and 4). A C2 below 0.90 therefore mixes that damage with real movement of the reference, and the slide says so.
4. **Tours.** Object nodes at stage 0 and at the end (every object node, as the frozen test counts them; the F1 count, which leaves out doors, is in `c2_*.json`): `apr_00853_a` 5 to 118; `apr_00853_b` 4 to 117; `apr_00853_b_FAILED_ATTEMPT_1707` 2 to 2 (frozen); `apr_00871_a` 3 to 117; `apr_00871_b` 4 to 4 (frozen).
5. **Folders.** The queue renames an older attempt to `*_FAILED_ATTEMPT_HHMM` when the next one launches, and HHMM is that launch's time. The map is in `folder_map_*.json`. The laptop copy for this run is `runs_1113/` beside the 11-12 `runs/`, which stays as it was: in the old copy the folder `apr_00853_b` holds the old frozen tour, which on the host now sits in `apr_00853_b_FAILED_ATTEMPT_1707`.
6. **GED.** 14 runs reuse their 11-12 GED, because their stage list (stage, path length, time) is equal. 0 runs were computed on the host. Recheck of reused values on the host: `e7_00871_s45_frontier_end` max difference 0 over 11 stages. Reuse goes by content, not by folder name, because the queue gives the plain name to the next attempt.
7. **00853 against 11-12.** 162 cells compared; 162 identical, 0 different. B moved: False. Nothing changed for 00853 (same five valid runs, same B, same reference), so its numbers are final and equal 11-12's.
8. **00871 against 11-12.** 243 cells compared; 243 identical, 0 different. B moved: False. The inputs are the same as on 11-12 (one valid run, the fallback B, the same crashed attempts), so the numbers are the same, and they are interim.

## Budgets

| Scene | Primary B (s) | Rule | Valid runs with "Exploration complete" | B with capped runs (s) | 11-12 B (s) |
|---|---|---|---|---|---|
| 00853 | 632.1751 | median | 5 | 632.1751 | 632.1751 |
| 00871 | 809.0840 | fallback | 1 | 809.0840 | 809.0840 |

## Status of the two scenes

- **00853: final.** B did not move; the 00853 cells equal 11-12's.
- **00871: interim, awaiting the third attempts of seeds 42, 43, 44, 45 and the APR-b rerun.** B is the registered fallback, from fewer than 2 valid runs. Every 00871 number in this folder is provisional. The 00871 numbers in `results_paper_compare_1112/` are **superseded** as soon as B changes; until then they equal these.

## Carried over from 11-12 (`results_paper_compare_1112/NOTES.md`)

- Item 1, order of the checks: C1-C5 were computed with the first scoring on 11-12 (deviation 42). Still true as history. This run files C2 first.
- Item 2, C2 not valid: superseded for 00853 by the rerun above. Still open for 00871 until its APR-b rerun runs.
- Item 3, APR-a final graphs end about 60 s early: holds. APR-a is unchanged and stays the reference on both scenes.
- Item 4, nvblox died partway through APR-a on both scenes and through APR-b on 00871: holds. The 00853 APR-b rerun is in the table above.
- Item 5, end times leave out the final leg: holds, and B uses the same rule for every run.
- Item 6, the 853 100% cell covers 3 of 5 runs: holds while B is 632.1751 s; read the n in each cell.
- Item 7, stages without a graph take the graph of the stage before: holds for the crashed first attempt of seed 44.
- Item 8, GPU sharing: corrected by deviation 40. The first attempt of seed 42 launched under the 12 GB check. The third attempts launch under it too.
- Item 9, C1 floor area far off: holds. C1, C3, C4 and C5 depend on APR-a only and are not recomputed (`results_paper_compare_1112/c_checks.json`).
- The frontier clock finding (11-12 NOTES, last section): holds, unchanged.

## When the third attempts land

Run the same command. It reads the queue log, maps the folders, copies, recomputes B and C2, and computes GED only for runs whose stage list has no 11-12 value. It refuses `--mode final` while an attempt is running or not yet launched. Then the lead updates deviation 46 from `folder_map_*.md` and marks the 11-12 00871 numbers superseded.
