# Scores on the paper's scale

F1 x 100, stage value at the last stage with navigation time at most t. Each cell reads `mean [min-max] n`; n counts runs with a value at t. The paper column is Fig. 4 (left) of arXiv 2510.05430v2. Budget B: 00853 = 632.1256 s, 00871 = 809.0840 s.

## Reference: hm3d

| Scene | Arm | Paper method | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|---|
| 00853 | official | Ours(ASP) | 8.0 [6.8-9.3] n=2 | 34.4 | 21.6 [20.5-22.6] n=2 | 60.8 | null (0/2) | 66.7 |
| 00853 | filter_only | Ours(ASP) | 7.6 [5.7-10.3] n=3 | 34.4 | 24.1 [19.3-29.4] n=3 | 60.8 | null (0/3) | 66.7 |
| 00853 | placebo | none | 6.4 [4.7-7.8] n=3 | - | 23.1 [20.5-25.6] n=3 | - | null (0/3) | - |
| 00853 | frontier_60m | Frontier | 9.7 [8.8-10.4] n=3 | 18.6 | 26.7 [23.7-29.8] n=3 | 46.5 | null (0/3) | 58.8 |
| 00853 | frontier_end_ref | Frontier | null (0/1) | 18.6 | null (0/1) | 46.5 | 36.4 [36.4-36.4] n=1 | 58.8 |
| 00853 | frontier_end | Frontier | 8.7 [8.7-8.7] n=1 | 18.6 | 21.8 [21.8-21.8] n=1 | 46.5 | 36.4 [36.4-36.4] n=1 | 58.8 |
| 00871 | official | Ours(ASP) | 7.6 [6.6-9.2] n=3 | 30.5 | null (0/3) | 62.4 | null (0/3) | 68.0 |
| 00871 | filter_only | Ours(ASP) | 8.4 [7.9-9.2] n=3 | 30.5 | 21.1 [21.1-21.1] n=1/3 | 62.4 | null (0/3) | 68.0 |
| 00871 | placebo | none | 6.3 [6.0-6.7] n=3 | - | 9.8 [9.8-9.8] n=1/3 | - | null (0/3) | - |
| 00871 | oracle_visible | none | 8.2 [7.7-9.0] n=3 | - | null (0/3) | - | null (0/3) | - |
| 00871 | frontier_60m | Frontier | 7.1 [6.6-8.2] n=3 | 29.2 | 10.4 [10.1-10.9] n=3 | 55.7 | null (0/3) | 65.3 |
| 00871 | frontier_end_ref | Frontier | null (0/1) | 29.2 | null (0/1) | 55.7 | 24.2 [24.2-24.2] n=1 | 65.3 |
| 00871 | frontier_end | Frontier | 7.0 [7.0-7.0] n=1 | 29.2 | 17.7 [17.7-17.7] n=1 | 55.7 | 24.2 [24.2-24.2] n=1 | 65.3 |

Sensitivity, means only (F1 x 100), at 10/50/100% of 0.8 B and of 1.2 B; `-` means no run has a value.

| Scene | Arm | 0.8B 10% | 0.8B 50% | 0.8B 100% | 1.2B 10% | 1.2B 50% | 1.2B 100% |
|---|---|---|---|---|---|---|---|
| 00853 | official | 7.5 (n=2) | 14.1 (n=2) | - | 8.5 (n=2) | 26.8 (n=1) | - |
| 00853 | filter_only | 6.6 (n=3) | 19.2 (n=3) | - | 7.6 (n=3) | 27.8 (n=2) | - |
| 00853 | placebo | 6.1 (n=3) | 19.6 (n=3) | - | 7.3 (n=3) | 25.9 (n=1) | - |
| 00853 | frontier_60m | 9.7 (n=3) | 22.4 (n=3) | - | 9.8 (n=3) | 28.2 (n=3) | - |
| 00853 | frontier_end_ref | - | - | - | - | - | - |
| 00853 | frontier_end | 8.8 (n=1) | 18.8 (n=1) | 29.6 (n=1) | 8.7 (n=1) | 26.4 (n=1) | - |
| 00871 | official | 7.2 (n=3) | 18.3 (n=3) | - | 7.8 (n=3) | - | - |
| 00871 | filter_only | 7.7 (n=3) | 13.5 (n=2) | - | 8.7 (n=3) | - | - |
| 00871 | placebo | 5.8 (n=3) | 9.5 (n=2) | - | 6.8 (n=3) | - | - |
| 00871 | oracle_visible | 7.3 (n=3) | 18.1 (n=3) | - | 9.8 (n=3) | - | - |
| 00871 | frontier_60m | 7.2 (n=3) | 10.2 (n=3) | - | 7.6 (n=3) | 13.2 (n=3) | - |
| 00871 | frontier_end_ref | - | - | - | - | - | - |
| 00871 | frontier_end | 6.3 (n=1) | 14.0 (n=1) | 23.8 (n=1) | 7.0 (n=1) | 20.4 (n=1) | - |

## Reference: frontier_made

This reference comes from the frontier explorer, so it favours frontier arms. The frontier_end_ref run scored against its own final map is self-referential.

| Scene | Arm | Paper method | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|---|
| 00853 | official | Ours(ASP) | 17.6 [15.2-20.1] n=2 | 34.4 | 39.9 [39.3-40.5] n=2 | 60.8 | null (0/2) | 66.7 |
| 00853 | filter_only | Ours(ASP) | 19.8 [18.6-21.6] n=3 | 34.4 | 52.6 [51.2-54.3] n=3 | 60.8 | null (0/3) | 66.7 |
| 00853 | placebo | none | 16.3 [12.2-18.6] n=3 | - | 49.2 [47.2-52.2] n=3 | - | null (0/3) | - |
| 00853 | frontier_60m | Frontier | 19.7 [18.2-21.5] n=3 | 18.6 | 55.1 [53.6-57.0] n=3 | 46.5 | null (0/3) | 58.8 |
| 00853 | frontier_end_ref | Frontier | null (0/1) | 18.6 | null (0/1) | 46.5 | 85.9 [85.9-85.9] n=1 | 58.8 |
| 00853 | frontier_end | Frontier | 26.3 [26.3-26.3] n=1 | 18.6 | 60.8 [60.8-60.8] n=1 | 46.5 | 85.9 [85.9-85.9] n=1 | 58.8 |
| 00871 | official | Ours(ASP) | 33.3 [32.0-35.8] n=3 | 30.5 | null (0/3) | 62.4 | null (0/3) | 68.0 |
| 00871 | filter_only | Ours(ASP) | 34.2 [31.2-38.0] n=3 | 30.5 | 61.4 [61.4-61.4] n=1/3 | 62.4 | null (0/3) | 68.0 |
| 00871 | placebo | none | 30.1 [29.7-30.7] n=3 | - | 38.6 [38.6-38.6] n=1/3 | - | null (0/3) | - |
| 00871 | oracle_visible | none | 39.6 [34.0-44.3] n=3 | - | null (0/3) | - | null (0/3) | - |
| 00871 | frontier_60m | Frontier | 37.6 [36.4-39.5] n=3 | 29.2 | 47.1 [43.9-51.9] n=3 | 55.7 | null (0/3) | 65.3 |
| 00871 | frontier_end_ref | Frontier | null (0/1) | 29.2 | null (0/1) | 55.7 | 88.1 [88.1-88.1] n=1 | 65.3 |
| 00871 | frontier_end | Frontier | 38.1 [38.1-38.1] n=1 | 29.2 | 74.5 [74.5-74.5] n=1 | 55.7 | 88.1 [88.1-88.1] n=1 | 65.3 |

Sensitivity, means only (F1 x 100), at 10/50/100% of 0.8 B and of 1.2 B; `-` means no run has a value.

| Scene | Arm | 0.8B 10% | 0.8B 50% | 0.8B 100% | 1.2B 10% | 1.2B 50% | 1.2B 100% |
|---|---|---|---|---|---|---|---|
| 00853 | official | 17.3 (n=2) | 28.0 (n=2) | - | 19.5 (n=2) | 46.4 (n=1) | - |
| 00853 | filter_only | 18.3 (n=3) | 44.6 (n=3) | - | 19.8 (n=3) | 55.9 (n=2) | - |
| 00853 | placebo | 16.1 (n=3) | 44.4 (n=3) | - | 17.6 (n=3) | 53.1 (n=1) | - |
| 00853 | frontier_60m | 19.0 (n=3) | 48.0 (n=3) | - | 20.0 (n=3) | 57.6 (n=3) | - |
| 00853 | frontier_end_ref | - | - | - | - | - | - |
| 00853 | frontier_end | 24.5 (n=1) | 55.9 (n=1) | 77.0 (n=1) | 26.3 (n=1) | 71.7 (n=1) | - |
| 00871 | official | 33.1 (n=3) | 59.5 (n=3) | - | 33.6 (n=3) | - | - |
| 00871 | filter_only | 33.2 (n=3) | 47.4 (n=2) | - | 36.5 (n=3) | - | - |
| 00871 | placebo | 29.1 (n=3) | 34.3 (n=2) | - | 30.8 (n=3) | - | - |
| 00871 | oracle_visible | 34.9 (n=3) | 63.7 (n=3) | - | 44.0 (n=3) | - | - |
| 00871 | frontier_60m | 37.1 (n=3) | 45.3 (n=3) | - | 38.0 (n=3) | 53.6 (n=3) | - |
| 00871 | frontier_end_ref | - | - | - | - | - | - |
| 00871 | frontier_end | 36.8 (n=1) | 57.9 (n=1) | 85.8 (n=1) | 37.9 (n=1) | 80.1 (n=1) | - |

## GED (the author's own code)

gmatch4py GraphEditDistance(1, 1, 1, 1) with the author's costs, mean over graph0 and graph1, stage value at t. Lower is better. `mean [min-max] n`.

### Reference: hm3d

| Scene | Arm | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|
| 00853 | official | 624 [624-625] n=2 | 249.5 | 708 [700-716] n=2 | 147.0 | null | 147.0 |
| 00853 | filter_only | 620 [612-628] n=3 | 249.5 | 740 [708-774] n=3 | 147.0 | null | 147.0 |
| 00853 | placebo | 612 [610-616] n=3 | - | 726 [724-728] n=3 | - | null | - |
| 00853 | frontier_60m | 618 [617-619] n=3 | 279.0 | 745 [727-773] n=3 | 243.4 | null | 177.0 |
| 00853 | frontier_end_ref | null | 279.0 | null | 243.4 | 836 | 177.0 |
| 00853 | frontier_end | 621 | 279.0 | 734 | 243.4 | 836 | 177.0 |
| 00871 | official | 823 [814-838] n=3 | 279.0 | null | 204.5 | null | 194.5 |
| 00871 | filter_only | 824 [816-841] n=3 | 279.0 | 949 | 204.5 | null | 194.5 |
| 00871 | placebo | 807 [802-816] n=3 | - | 856 | - | null | - |
| 00871 | oracle_visible | 842 [824-862] n=3 | - | null | - | null | - |
| 00871 | frontier_60m | 819 [814-827] n=3 | 292.1 | 866 [860-876] n=3 | 233.0 | null | 203.5 |
| 00871 | frontier_end_ref | null | 292.1 | null | 233.0 | 1032 | 203.5 |
| 00871 | frontier_end | 818 | 292.1 | 974 | 233.0 | 1032 | 203.5 |

### Reference: frontier_made

| Scene | Arm | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|
| 00853 | official | 284 [283-286] n=2 | 249.5 | 256 [238-273] n=2 | 147.0 | null | 147.0 |
| 00853 | filter_only | 278 [266-285] n=3 | 249.5 | 193 [166-234] n=3 | 147.0 | null | 147.0 |
| 00853 | placebo | 275 [263-286] n=3 | - | 211 [188-224] n=3 | - | null | - |
| 00853 | frontier_60m | 271 [266-276] n=3 | 279.0 | 206 [195-214] n=3 | 243.4 | null | 177.0 |
| 00853 | frontier_end_ref | null | 279.0 | null | 243.4 | 53 | 177.0 |
| 00853 | frontier_end | 260 | 279.0 | 168 | 243.4 | 53 | 177.0 |
| 00871 | official | 270 [264-280] n=3 | 279.0 | null | 204.5 | null | 194.5 |
| 00871 | filter_only | 273 [252-292] n=3 | 279.0 | 238 | 204.5 | null | 194.5 |
| 00871 | placebo | 265 [260-268] n=3 | - | 276 | - | null | - |
| 00871 | oracle_visible | 258 [238-272] n=3 | - | null | - | null | - |
| 00871 | frontier_60m | 268 [262-271] n=3 | 292.1 | 253 [249-258] n=3 | 233.0 | null | 203.5 |
| 00871 | frontier_end_ref | null | 292.1 | null | 233.0 | 96 | 203.5 |
| 00871 | frontier_end | 257 | 292.1 | 202 | 233.0 | 96 | 203.5 |

## Seconds per metre

Final navigation time over final path length, from each run's last scored stage.

| Scene | Arm | Runs | s/m mean [min-max] | Final time s (mean) | Final path m (mean) |
|---|---|---|---|---|---|
| 00853 | official | 2 | 6.53 [6.37-6.68] | 377.1 | 57.7 |
| 00853 | filter_only | 3 | 6.33 [6.10-6.66] | 392.6 | 62.0 |
| 00853 | placebo | 3 | 5.84 [5.63-6.13] | 381.6 | 65.3 |
| 00853 | frontier_60m | 3 | 6.80 [6.46-7.09] | 435.0 | 64.0 |
| 00853 | frontier_end_ref | 1 | 6.61 [6.61-6.61] | 632.1 | 95.7 |
| 00853 | frontier_end | 1 | 6.61 [6.61-6.61] | 632.1 | 95.7 |
| 00871 | official | 3 | 6.07 [5.66-6.62] | 378.5 | 62.4 |
| 00871 | filter_only | 3 | 6.23 [5.26-6.97] | 369.6 | 59.0 |
| 00871 | placebo | 3 | 6.25 [5.26-7.58] | 380.0 | 60.7 |
| 00871 | oracle_visible | 3 | 5.52 [5.31-5.78] | 344.6 | 62.4 |
| 00871 | frontier_60m | 3 | 8.67 [7.97-9.18] | 539.0 | 62.1 |
| 00871 | frontier_end_ref | 1 | 6.73 [6.73-6.73] | 809.1 | 120.2 |
| 00871 | frontier_end | 1 | 6.73 [6.73-6.73] | 809.1 | 120.2 |

## Not comparable

- The references differ. The paper scores against a hand-driven full-scene map. We use the HM3D human-label map, the frontier-made map (biased toward frontier), and a coverage-tour map when one exists.
- ASP runs stop at 60 m of path, which took 289-468 s here. A run has no value at a t past its last stage, so its 100% readout is null, and a 50% readout is null when the run ended sooner.
- The e4 frontier runs stop at 60 m too (405-574 s), so their 100% readout is null as well. Only the frontier-to-end runs reach B.
- Navigation time counts moving time only, so it depends on seconds per metre, which differs by arm.
- Scenes 00069 and 00573 have no run here; their paper cells stay in the JSON only.
- GED comes from the author's own code on the host; see the GED section.

## Missing stage files

- scene00853_frontier_reference stage 33: navigation_stats.json absent from the run dir (filled from the fallback root).
- scene00853_frontier_reference stage 33: habitat_scene_graph_original_graph1.yaml absent from the run dir (filled from the fallback root).
- scene00853_frontier_reference: 1 stage(s) scored. Only the final stage exists in the off-host copy, so the readouts before B are null.
- scene00871_frontier_reference stage 54: navigation_stats.json absent from the run dir (filled from the fallback root).
- scene00871_frontier_reference stage 54: habitat_scene_graph_original_graph1.yaml absent from the run dir (filled from the fallback root).
- scene00871_frontier_reference: 1 stage(s) scored. Only the final stage exists in the off-host copy, so the readouts before B are null.
