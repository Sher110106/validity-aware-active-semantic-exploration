# Notes on the 13 Nov paper-scale rescore

**State: final.** Written 2026-11-21T02:55:10+05:30. Rerun with `bash tools/live_policy/host/rescore_paper.sh`. The rules are `PREREGISTRATION_PAPER.md`, Amendment 2 and its Note, and for the November ASP row Amendment 3 and its Note, and for the control arms Amendment 5. Tables: `paper_compare.md` and `.json`. Evidence: `acceptance_*.json`, `folder_map_*`, `c2_*.json`, `budgets_*.json`, `comparison_vs_1112.json`, `rescore_summary.json`.

## What changed against 11-12, and why

1. **Acceptance first.** `check_paper_runs.py` ran on the host before any score (`acceptance_20261121T025004.json`). 10 e7 runs count as valid: 00853_s42, 00853_s43, 00853_s44, 00853_s45, 00853_s46, 00871_s42, 00871_s43, 00871_s44, 00871_s45, 00871_s46. 8 other attempts fail A2.1 and stay out of every paper cell: 00871 s42 #1, 00871 s42 #2, 00871 s43 #1, 00871 s43 #2, 00871 s44 #1, 00871 s44 #2, 00871 s45 #1, 00871 s45 #2: no 'Exploration complete' and no 250 m / 4 h stop, roslaunch.log shows out of memory or nvblox_node dead.
2. **Budget B** is now set by script (A2.3). The primary B is the median end time of the valid runs that logged "Exploration complete"; fewer than 2 means the registered fallback. 00853: B = 632.1751 s (median, 5 valid run(s)); 11-12 used 632.1751 s; 00871: B = 1300.2523 s (median, 4 valid run(s)); 11-12 used 809.0840 s. A capped run changes the second line; it is scored in `alt_B_with_capped/`.
3. **C2** was computed and filed (`c2_20261121T025004.json`) before any run was scored. 00853: F1 0.7511 (precision 0.7545, recall 0.7477); APR-b holds 110 objects, APR-a 111; nvblox did not die during it. It is below 0.90, so the slide says the reference moves by more than the paper's margins (2.7-7.9 points), and also says APR-a's damage is part of it. 00871: F1 0.7714 (precision 0.7570, recall 0.7864); APR-b holds 107 objects, APR-a 103; nvblox did not die during it. It is below 0.90, so the slide says the reference moves by more than the paper's margins (2.7-7.9 points), and also says APR-a's damage is part of it. In both APR-a tours nvblox died partway, and each final graph lacks about the last 60 s of its tour (results_paper_compare_1112/NOTES.md, items 3 and 4). A C2 below 0.90 therefore mixes that damage with real movement of the reference, and the slide says so.
4. **Tours.** The table below gives, for every tour, whether nvblox died, the "Timeout! Did not find" lines, the last archived stop whose graph changed, and the object nodes at stage 0 and at the end (A2.4).
5. **Folders.** The queue renames an older attempt to `*_FAILED_ATTEMPT_HHMM` when the next one launches, and HHMM is that launch's time. The map is in `folder_map_*.json`. The laptop copy for this run is `runs_1113/` beside the 11-12 `runs/`, which stays as it was: in the old copy the folder `apr_00853_b` holds the old frozen tour, which on the host now sits in `apr_00853_b_FAILED_ATTEMPT_1707`. The folder `e7_00853_s42_frontier_end_FAILED_ATTEMPT1_gpu_oom` holds an attempt from before the queue log (11-06) that made no stage graph: its roslaunch.log shows 2 out-of-memory line(s) and 1 line(s) saying nvblox_node died. The queue log has no launch line for it, so it is in no row. Seed 42 of 00853 is scored from its later attempt.
6. **GED.** 14 runs reuse their 11-12 GED, because their stage list (stage, path length, time) is equal. 13 runs were computed on the host. Recheck of reused values on the host: not asked for. Reuse goes by content, not by folder name, because the queue gives the plain name to the next attempt.
7. **00853 against 11-12.** 162 cells compared; 162 identical, 0 different. B did not move. 81 new cells appear, in observed_only_nov, official_nov, placebo_nov.
8. **00871 against 11-12.** 243 cells compared; 102 identical, 141 different. B moved, from 809.0840 s to 1300.2523 s, so the cells differ. Of the 102 identical cells, 102 hold no value in either filing; every cell that holds a value changed. 42 cells held a value on 11-12 and hold none now (crashed_frontier_1st, crashed_frontier_rerun, filter_only, frontier_60m, frontier_end_ref, official, oracle_visible, placebo, at 50% and 100% of B): B grew, and those runs end before the new marks. Every 00871 number in `results_paper_compare_1112/` is superseded by this folder.

## Budgets

| Scene | Primary B (s) | Rule | Valid runs with "Exploration complete" | B with capped runs (s) | 11-12 B (s) |
|---|---|---|---|---|---|
| 00853 | 632.1751 | median | 5 | 632.1751 | 632.1751 |
| 00871 | 1300.2523 | median | 4 | 1337.0149 | 809.0840 |

## November ASP row (Amendment 3)

The row "ASP + DeepSeek, November" holds `e8_00853_s42..44_official_105m` (a `_relaunch1` name where the rule gave one). Its runs are never pooled with October's `official` arm: the two rows have their own n beside every cell. B for 853 is 632.1751 s, the same B as above. 3 of 3 runs count in the cells (3 are on the host); 2 reached B and have a 100% value. A run that did not reach B keeps its 10% and 50% values. A run that fails the GPU check or an E1 exclusion is left out of every cell and listed here. A `dryrun_e8_` folder is never scored.

| Run | State | Navigation time at its last full stage (s) | Reached B | In the cells | Left out because | Note |
|---|---|---|---|---|---|---|
| `e8_00853_s42_official_105m` | finished | 652.1 | yes | yes | - | - |
| `e8_00853_s43_official_105m` | finished | 646.1 | yes | yes | - | - |
| `e8_00853_s44_official_105m` | finished | 604.0 | no | yes | - | ended before B (604.0 s): no 100% value, the 10% and 50% values stay |

What the A3.2 checks read in each run's files:

| Run | "out of memory" lines | nvblox-died lines | Calls | Calls by another provider or model | Members dropped (%) |
|---|---|---|---|---|---|
| `e8_00853_s42_official_105m` | 0 | 0 | 2363 | 0 | 7.3 |
| `e8_00853_s43_official_105m` | 0 | 0 | 2052 | 0 | 9.6 |
| `e8_00853_s44_official_105m` | 0 | 0 | 1918 | 0 | 7.4 |

**The readouts A3.3 asks for,** at 10%, 50% and 100% of B: object F1 x 100 as the stage value and as the running maximum, and GED with the author's code (lower is better). Mean [min-max] and n. No p-value.

| Reference | Readout | 10% | 50% | 100% |
|---|---|---|---|---|
| apr | F1, stage value | 17.2 [13.3-21.2] n=3 | 51.1 [45.7-61.5] n=3 | 61.6 [60.3-62.9] n=2 of 3 |
| apr | F1, running maximum | 17.2 [13.3-21.2] n=3 | 51.1 [45.7-61.5] n=3 | 61.8 [60.7-62.9] n=2 of 3 |
| apr | GED | 328.3 [325.5-332.5] n=3 | 246.2 [229.5-256.0] n=3 | 210.2 [194.5-226.0] n=2 of 3 |
| frontier_made | F1, stage value | 18.7 [16.9-21.8] n=3 | 54.7 [52.0-60.0] n=3 | 64.3 [63.5-65.2] n=2 of 3 |
| frontier_made | F1, running maximum | 18.7 [16.9-21.9] n=3 | 54.7 [52.0-60.0] n=3 | 64.5 [63.9-65.2] n=2 of 3 |
| frontier_made | GED | 278.0 [271.0-283.0] n=3 | 188.2 [181.0-201.5] n=3 | 185.0 [170.5-199.5] n=2 of 3 |
| hm3d | F1, stage value | 8.1 [6.3-9.7] n=3 | 26.7 [24.5-30.6] n=3 | 34.4 [33.1-35.7] n=2 of 3 |
| hm3d | F1, running maximum | 8.1 [6.3-9.7] n=3 | 26.7 [24.5-30.6] n=3 | 34.6 [33.5-35.7] n=2 of 3 |
| hm3d | GED | 616.5 [603.0-630.0] n=3 | 750.0 [733.5-782.0] n=3 | 820.2 [814.5-826.0] n=2 of 3 |

The Note expected the sensitivity cell at 100% of 1.2 B to be empty, since a 105 m run would most likely end before 759 s. It is empty: no run reached it.

**The row under the other readings of one run.** `DEVIATIONS_NOVEMBER.md` says why. Object F1 x 100 against the APR reference, stage value, mean [min-max]. The first line is the row as filed above.

| Reading | 10% | 50% | 100% | Full tables |
|---|---|---|---|---|
| As the runs ran | 17.2 [13.3-21.2] n=3 | 51.1 [45.7-61.5] n=3 | 61.6 [60.3-62.9] n=2 of 3 | `paper_compare.md` |
| `e8_00853_s43_official_105m` read as stopped by hand after stage 22 (514.2 s): the Note's own rule, under which it ended before B and keeps the values it has | 17.2 [13.3-21.2] n=3 | 51.1 [45.7-61.5] n=3 | 62.9 [62.9-62.9] n=1 of 3 | `alt_nov_e8_00853_s43_official_105m_stopped_after_stage_22/` |
| Without `e8_00853_s43_official_105m`: a further sensitivity | 19.1 [17.1-21.2] n=2 | 53.6 [45.7-61.5] n=2 | 62.9 [62.9-62.9] n=1 of 2 | `alt_nov_without_e8_00853_s43_official_105m/` |

## Control arms (Amendment 5)

The rows `placebo_nov` and `observed_only_nov` hold `e9_00853_s42..44_placebo_115m` and `e9_00853_s42..44_observed_only_115m` (a `_relaunch1` name where the rule gave one). Each run is picked by its own anchored name pattern. They are never pooled with October's `placebo` arm or any other, and a `dryrun_e9_` folder is never scored. B for 853 is 632.1751 s, the same B as above. 6 of 6 runs count in the cells (6 are on the host). A run has a value at a time or a path only if its last stage with stats and both graph files reaches it. A run with an "out of memory" line or a line saying nvblox_node has died has no value at 100% of B or later and none at 100 m; its other cells are reported and marked. A run with no `logs/roslaunch.log` is read the same way, as `official_nov` is left out for it. There is no rerun of any kind (A5.3).

| Run | State | Navigation time at its last full stage (s) | Path at its last full stage (m) | Reached B | Reached 100 m | In the cells | Marked: no value at 100% of B and at 100 m | Note |
|---|---|---|---|---|---|---|---|---|
| `e9_00853_s42_observed_only_115m` | finished | 857.9 | 116.3 | yes | yes | yes | no | - |
| `e9_00853_s42_placebo_115m` | finished | 647.3 | 115.9 | yes | yes | yes | no | - |
| `e9_00853_s43_observed_only_115m` | finished | 824.2 | 117.3 | yes | yes | yes | no | - |
| `e9_00853_s43_placebo_115m` | finished | 689.5 | 115.1 | yes | yes | yes | no | - |
| `e9_00853_s44_observed_only_115m` | finished | 815.2 | 116.5 | yes | yes | yes | no | - |
| `e9_00853_s44_placebo_115m` | finished | 724.5 | 119.0 | yes | yes | yes | no | - |

What the A5.3 checks read in each run's files:

| Run | "out of memory" lines | nvblox-died lines |
|---|---|---|
| `e9_00853_s42_observed_only_115m` | 0 | 0 |
| `e9_00853_s42_placebo_115m` | 0 | 0 |
| `e9_00853_s43_observed_only_115m` | 0 | 0 |
| `e9_00853_s43_placebo_115m` | 0 | 0 |
| `e9_00853_s44_observed_only_115m` | 0 | 0 |
| `e9_00853_s44_placebo_115m` | 0 | 0 |

**Readout 1 (A5.5),** at 10%, 50% and 100% of B: object F1 x 100 as the stage value and as the running maximum, and GED with the author's code (lower is better), against all three references. Mean [min-max] and n. No p-value.

`placebo_nov`:

| Reference | Readout | 10% | 50% | 100% |
|---|---|---|---|---|
| apr | F1, stage value | 15.9 [14.6-17.7] n=3 | 43.2 [27.1-52.3] n=3 | 58.2 [41.5-66.8] n=3 |
| apr | F1, running maximum | 15.9 [14.6-17.7] n=3 | 43.3 [27.2-52.3] n=3 | 58.2 [41.5-66.8] n=3 |
| apr | GED | 341.0 [333.0-347.5] n=3 | 276.2 [247.5-300.0] n=3 | 238.8 [202.0-286.0] n=3 |
| frontier_made | F1, stage value | 20.5 [20.3-20.7] n=3 | 45.0 [31.0-53.0] n=3 | 59.7 [48.9-65.4] n=3 |
| frontier_made | F1, running maximum | 20.5 [20.3-20.7] n=3 | 45.4 [31.1-53.0] n=3 | 60.2 [48.9-66.4] n=3 |
| frontier_made | GED | 279.7 [276.5-282.0] n=3 | 218.7 [173.0-259.0] n=3 | 195.2 [161.5-240.5] n=3 |
| hm3d | F1, stage value | 6.7 [6.2-7.8] n=3 | 21.0 [13.1-25.3] n=3 | 30.8 [23.2-35.0] n=3 |
| hm3d | F1, running maximum | 6.7 [6.2-7.8] n=3 | 21.0 [13.1-25.3] n=3 | 30.9 [23.2-35.3] n=3 |
| hm3d | GED | 619.8 [617.0-623.5] n=3 | 720.7 [674.0-749.0] n=3 | 807.8 [759.0-843.0] n=3 |

`observed_only_nov`:

| Reference | Readout | 10% | 50% | 100% |
|---|---|---|---|---|
| apr | F1, stage value | 17.4 [15.3-18.5] n=3 | 30.9 [18.8-37.4] n=3 | 35.7 [19.3-49.1] n=3 |
| apr | F1, running maximum | 17.4 [15.3-18.5] n=3 | 30.9 [18.8-37.4] n=3 | 35.8 [19.3-49.4] n=3 |
| apr | GED | 321.0 [308.0-330.0] n=3 | 308.8 [292.5-332.5] n=3 | 309.8 [270.0-357.5] n=3 |
| frontier_made | F1, stage value | 18.2 [15.1-21.5] n=3 | 28.2 [19.6-32.8] n=3 | 32.7 [19.3-47.1] n=3 |
| frontier_made | F1, running maximum | 18.3 [15.1-21.5] n=3 | 28.7 [21.3-32.8] n=3 | 33.5 [21.3-47.1] n=3 |
| frontier_made | GED | 273.0 [262.0-278.5] n=3 | 253.7 [232.0-285.0] n=3 | 244.5 [191.0-286.0] n=3 |
| hm3d | F1, stage value | 8.5 [6.7-10.3] n=3 | 13.8 [10.9-16.2] n=3 | 16.6 [10.3-24.8] n=3 |
| hm3d | F1, running maximum | 8.5 [6.7-10.3] n=3 | 13.8 [10.9-16.2] n=3 | 16.9 [10.9-24.8] n=3 |
| hm3d | GED | 614.5 [602.0-622.0] n=3 | 659.8 [633.5-677.0] n=3 | 697.0 [648.5-759.5] n=3 |

**Readout 2 (A5.5),** object F1 x 100 (stage value) at equal path: at each length the last stage whose path is at most L, all three references. Mean [min-max] and n ("n=k of m" when some of the m runs have no value).

- `official_nov`: first made after the results were seen (deviation 66).
- `placebo_nov`: registered (A5.5).
- `observed_only_nov`: registered (A5.5).
- `frontier_end`: first made after the results were seen (deviation 66).

Reference apr:

| Arm | 50 m | 60 m | 80 m | 100 m |
|---|---|---|---|---|
| `official_nov` | 48.2 [43.4-55.6] n=3 | 53.2 [47.2-61.5] n=3 | 59.7 [56.2-64.3] n=3 | 62.5 [60.7-65.6] n=3 |
| `placebo_nov` | 43.2 [27.1-52.3] n=3 | 44.9 [29.2-54.2] n=3 | 52.6 [36.6-60.9] n=3 | 57.4 [41.5-65.6] n=3 |
| `observed_only_nov` | 30.8 [18.7-37.4] n=3 | 33.5 [17.9-45.0] n=3 | 34.8 [18.6-47.1] n=3 | 34.8 [19.0-48.5] n=3 |
| `frontier_end` | 47.4 [42.3-56.1] n=5 | 52.5 [48.8-57.7] n=5 | 56.1 [53.5-59.6] n=5 | 58.7 [57.7-59.7] n=2 of 5 |

Reference hm3d:

| Arm | 50 m | 60 m | 80 m | 100 m |
|---|---|---|---|---|
| `official_nov` | 25.4 [23.7-28.1] n=3 | 27.9 [25.4-30.6] n=3 | 31.4 [30.7-31.9] n=3 | 32.5 [30.9-33.4] n=3 |
| `placebo_nov` | 21.0 [13.1-25.3] n=3 | 22.3 [13.9-28.7] n=3 | 27.7 [20.7-32.7] n=3 | 30.2 [23.2-35.1] n=3 |
| `observed_only_nov` | 13.7 [10.9-16.2] n=3 | 15.1 [10.3-20.0] n=3 | 15.9 [10.8-22.2] n=3 | 16.0 [9.7-24.6] n=3 |
| `frontier_end` | 27.3 [25.1-30.2] n=5 | 30.1 [28.7-31.3] n=5 | 31.9 [30.2-33.5] n=5 | 34.1 [33.5-34.8] n=2 of 5 |

Reference frontier_made:

| Arm | 50 m | 60 m | 80 m | 100 m |
|---|---|---|---|---|
| `official_nov` | 51.4 [48.6-53.5] n=3 | 56.2 [52.3-60.0] n=3 | 60.4 [58.7-61.6] n=3 | 63.0 [61.8-63.9] n=3 |
| `placebo_nov` | 45.0 [31.0-53.0] n=3 | 45.7 [31.0-55.5] n=3 | 55.2 [43.9-61.6] n=3 | 59.7 [48.9-65.8] n=3 |
| `observed_only_nov` | 28.1 [19.5-32.8] n=3 | 29.7 [18.4-39.4] n=3 | 31.8 [18.3-45.4] n=3 | 31.0 [16.1-46.4] n=3 |
| `frontier_end` | 54.9 [50.6-58.3] n=5 | 59.8 [56.9-64.4] n=5 | 64.3 [62.6-66.9] n=5 | 65.6 [64.3-66.9] n=2 of 5 |

**Readout 3 (A5.5),** seconds of navigation time per metre, from each run's last scored stage:

- `official`: 6.53 s/m [6.37-6.68], n=2
- `official_nov`: 5.77 s/m [5.36-6.04], n=3
- `placebo_nov`: 5.89 s/m [5.59-6.09], n=3
- `observed_only_nov`: 7.14 s/m [7.00-7.38], n=3
- `filter_only`: 6.33 s/m [6.10-6.66], n=3
- `placebo`: 5.84 s/m [5.63-6.13], n=3
- `frontier_60m`: 6.80 s/m [6.46-7.09], n=3
- `frontier_end_ref`: 6.61 s/m [6.61-6.61], n=1
- `frontier_end`: 6.98 s/m [6.40-7.84], n=5

**The reading (A5.6).** S is the mean of a run's F1 x 100 at 50, 60, 80 and 100 m of path, once against APR and once against the HM3D labels. A run that did not reach 100 m has no S. `official_nov` is the three runs `e8_00853_s42..44_official_105m` as they ran, each with S. The equal-time cells of readout 1 above are shown beside it and decide nothing. The tables print S to one decimal; every comparison of S is made at full precision, never on the rounded figures.

S against apr:

| Arm | Run | S | Reached 100 m |
|---|---|---|---|
| `official_nov` | `e8_00853_s42_official_105m` | 53.6 | - |
| `official_nov` | `e8_00853_s43_official_105m` | 52.5 | - |
| `official_nov` | `e8_00853_s44_official_105m` | 61.7 | - |
| `placebo_nov` | `e9_00853_s42_placebo_115m` | 58.1 | yes |
| `placebo_nov` | `e9_00853_s43_placebo_115m` | 56.9 | yes |
| `placebo_nov` | `e9_00853_s44_placebo_115m` | 33.6 | yes |
| `observed_only_nov` | `e9_00853_s42_observed_only_115m` | 37.4 | yes |
| `observed_only_nov` | `e9_00853_s43_observed_only_115m` | 44.5 | yes |
| `observed_only_nov` | `e9_00853_s44_observed_only_115m` | 18.6 | yes |

S against hm3d:

| Arm | Run | S | Reached 100 m |
|---|---|---|---|
| `official_nov` | `e8_00853_s42_official_105m` | 29.0 | - |
| `official_nov` | `e8_00853_s43_official_105m` | 28.5 | - |
| `official_nov` | `e8_00853_s44_official_105m` | 30.4 | - |
| `placebo_nov` | `e9_00853_s42_placebo_115m` | 30.4 | yes |
| `placebo_nov` | `e9_00853_s43_placebo_115m` | 27.7 | yes |
| `placebo_nov` | `e9_00853_s44_placebo_115m` | 17.7 | yes |
| `observed_only_nov` | `e9_00853_s42_observed_only_115m` | 14.4 | yes |
| `observed_only_nov` | `e9_00853_s43_observed_only_115m` | 20.8 | yes |
| `observed_only_nov` | `e9_00853_s44_observed_only_115m` | 10.4 | yes |

- `placebo_nov`: apr: above on average, not separated, hm3d: above on average, not separated. Statement: **in between**.
- `observed_only_nov`: apr: separated above, hm3d: separated above. Statement: **reads above**.

Slide: The slide gives both S tables and the statements as they fall.

What this cannot show: three runs a side in one home, no p-value. "Not shown to come from the guesses" is not "the guesses do nothing". The controls ran two days later, under another load on the GPU, lose no members to dropped replies, and sleep for a median wait, not the wait itself (A5.6).

**S of `official_nov` under the other readings of one run.** `DEVIATIONS_NOVEMBER.md` says why. They decide nothing.

| Reading | Run | S apr (mean) | S hm3d (mean) | Folder |
|---|---|---|---|---|
| stopped after stage 22 | `e8_00853_s43_official_105m` | s42: 53.6, s43: none, s44: 61.7 (mean 57.6) | s42: 29.0, s43: none, s44: 30.4 (mean 29.7) | `alt_nov_e8_00853_s43_official_105m_stopped_after_stage_22/` |
| without the run | `e8_00853_s43_official_105m` | s42: 53.6, s44: 61.7 (mean 57.6) | s42: 29.0, s44: 30.4 (mean 29.7) | `alt_nov_without_e8_00853_s43_official_105m/` |

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
- Item 7, stages without a graph take the graph of the stage before: the rule stands, but with the new B for 00871 it decides no cell. The review of 11-17 checked every run: none is read at a stage without a graph, and the crashed first attempt of seed 44 ends before the new 50% mark.
- Item 8, GPU sharing: the Note to Amendment 2 corrects the statement (the first attempt of seed 42 launched under the 12 GB check), and so does deviation 40. The third attempts were queued under the 12 GB check (deviation 45); this pipeline does not test the GPU at launch.
- Item 9, C1 floor area far off: holds. C1, C3, C4 and C5 depend on APR-a only and are not recomputed (`results_paper_compare_1112/c_checks.json`).
- The frontier clock finding (11-12 NOTES, last section): holds, unchanged.

## For the deviations file

**11-06: an attempt of e7 00853 seed 42 that made no stage.** The folder `e7_00853_s42_frontier_end_FAILED_ATTEMPT1_gpu_oom` holds an attempt from before the queue log (11-06) that made no stage graph: its roslaunch.log shows 2 out-of-memory line(s) and 1 line(s) saying nvblox_node died. The queue log has no launch line for it, so it is in no row. Seed 42 of 00853 is scored from its later attempt.
