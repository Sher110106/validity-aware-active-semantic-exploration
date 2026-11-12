# Scores on the paper's scale

F1 x 100, stage value at the last stage with navigation time at most t. Each cell reads `mean [min-max] n`; n counts runs with a value at t. The paper column is Fig. 4 (left) of arXiv 2510.05430v2. Budget B: 00853 = 632.1751 s (--budget), 00871 = 809.0840 s (default: end of the frontier-made reference run (section 4 fallback)).

## Reference: hm3d

| Scene | Arm | Paper method | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|---|
| 00853 | official | Ours(ASP) | 8.0 [6.8-9.3] n=2 | 34.4 | 21.6 [20.5-22.6] n=2 | 60.8 | null (0/2) | 66.7 |
| 00853 | filter_only | Ours(ASP) | 7.6 [5.7-10.3] n=3 | 34.4 | 24.1 [19.3-29.4] n=3 | 60.8 | null (0/3) | 66.7 |
| 00853 | placebo | none | 6.4 [4.7-7.8] n=3 | - | 23.1 [20.5-25.6] n=3 | - | null (0/3) | - |
| 00853 | frontier_60m | Frontier | 9.7 [8.8-10.4] n=3 | 18.6 | 26.7 [23.7-29.8] n=3 | 46.5 | null (0/3) | 58.8 |
| 00853 | frontier_end_ref | Frontier | null (0/1) | 18.6 | null (0/1) | 46.5 | null (0/1) | 58.8 |
| 00853 | frontier_end | Frontier | 7.7 [6.3-8.9] n=5 | 18.6 | 21.9 [19.9-23.9] n=5 | 46.5 | 32.9 [30.2-35.6] n=3/5 | 58.8 |
| 00871 | official | Ours(ASP) | 7.6 [6.6-9.2] n=3 | 30.5 | null (0/3) | 62.4 | null (0/3) | 68.0 |
| 00871 | filter_only | Ours(ASP) | 8.4 [7.9-9.2] n=3 | 30.5 | 21.1 [21.1-21.1] n=1/3 | 62.4 | null (0/3) | 68.0 |
| 00871 | placebo | none | 6.3 [6.0-6.7] n=3 | - | 9.8 [9.8-9.8] n=1/3 | - | null (0/3) | - |
| 00871 | oracle_visible | none | 8.2 [7.7-9.0] n=3 | - | null (0/3) | - | null (0/3) | - |
| 00871 | frontier_60m | Frontier | 7.1 [6.6-8.2] n=3 | 29.2 | 10.4 [10.1-10.9] n=3 | 55.7 | null (0/3) | 65.3 |
| 00871 | frontier_end_ref | Frontier | null (0/1) | 29.2 | null (0/1) | 55.7 | 24.2 [24.2-24.2] n=1 | 65.3 |
| 00871 | frontier_end | Frontier | 6.3 [6.3-6.3] n=1 | 29.2 | 13.7 [13.7-13.7] n=1 | 55.7 | 21.3 [21.3-21.3] n=1 | 65.3 |
| 00871 | crashed_frontier_1st | none | 6.5 [5.5-7.4] n=4 | - | 11.6 [8.0-16.6] n=4 | - | null (0/4) | - |
| 00871 | crashed_frontier_rerun | none | 7.0 [6.3-7.9] n=4 | - | 11.8 [11.8-11.8] n=1/4 | - | null (0/4) | - |

Sensitivity, means only (F1 x 100), at 10/50/100% of 0.8 B and of 1.2 B; `-` means no run has a value.

| Scene | Arm | 0.8B 10% | 0.8B 50% | 0.8B 100% | 1.2B 10% | 1.2B 50% | 1.2B 100% |
|---|---|---|---|---|---|---|---|
| 00853 | official | 7.5 (n=2) | 14.1 (n=2) | - | 8.5 (n=2) | 26.8 (n=1) | - |
| 00853 | filter_only | 6.6 (n=3) | 19.2 (n=3) | - | 7.6 (n=3) | 27.8 (n=2) | - |
| 00853 | placebo | 6.1 (n=3) | 19.6 (n=3) | - | 7.3 (n=3) | 25.9 (n=1) | - |
| 00853 | frontier_60m | 9.7 (n=3) | 22.4 (n=3) | - | 9.8 (n=3) | 28.2 (n=3) | - |
| 00853 | frontier_end_ref | - | - | - | - | - | - |
| 00853 | frontier_end | 7.5 (n=5) | 20.6 (n=5) | 31.7 (n=5) | 7.8 (n=5) | 26.3 (n=5) | 33.5 (n=1) |
| 00871 | official | 7.2 (n=3) | 18.3 (n=3) | - | 7.8 (n=3) | - | - |
| 00871 | filter_only | 7.7 (n=3) | 13.5 (n=2) | - | 8.7 (n=3) | - | - |
| 00871 | placebo | 5.8 (n=3) | 9.5 (n=2) | - | 6.8 (n=3) | - | - |
| 00871 | oracle_visible | 7.3 (n=3) | 18.1 (n=3) | - | 9.8 (n=3) | - | - |
| 00871 | frontier_60m | 7.2 (n=3) | 10.2 (n=3) | - | 7.6 (n=3) | 13.2 (n=3) | - |
| 00871 | frontier_end_ref | - | - | - | - | - | - |
| 00871 | frontier_end | 5.6 (n=1) | 8.5 (n=1) | 19.5 (n=1) | 6.3 (n=1) | 15.1 (n=1) | 21.9 (n=1) |
| 00871 | crashed_frontier_1st | 6.3 (n=4) | 11.1 (n=4) | 20.0 (n=1) | 7.0 (n=4) | 12.2 (n=3) | - |
| 00871 | crashed_frontier_rerun | 6.6 (n=4) | 9.5 (n=1) | - | 7.5 (n=4) | 15.4 (n=1) | - |

## Reference: apr

| Scene | Arm | Paper method | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|---|
| 00853 | official | Ours(ASP) | 16.5 [13.8-19.1] n=2 | 34.4 | 38.7 [37.2-40.1] n=2 | 60.8 | null (0/2) | 66.7 |
| 00853 | filter_only | Ours(ASP) | 14.8 [12.1-18.4] n=3 | 34.4 | 48.3 [40.9-52.2] n=3 | 60.8 | null (0/3) | 66.7 |
| 00853 | placebo | none | 13.8 [10.8-16.1] n=3 | - | 43.9 [39.4-48.2] n=3 | - | null (0/3) | - |
| 00853 | frontier_60m | Frontier | 15.3 [12.9-16.9] n=3 | 18.6 | 45.6 [41.7-52.4] n=3 | 46.5 | null (0/3) | 58.8 |
| 00853 | frontier_end_ref | Frontier | null (0/1) | 18.6 | null (0/1) | 46.5 | null (0/1) | 58.8 |
| 00853 | frontier_end | Frontier | 12.4 [10.8-14.7] n=5 | 18.6 | 39.5 [33.9-42.0] n=5 | 46.5 | 55.6 [53.5-59.6] n=3/5 | 58.8 |
| 00871 | official | Ours(ASP) | 32.3 [30.5-35.6] n=3 | 30.5 | null (0/3) | 62.4 | null (0/3) | 68.0 |
| 00871 | filter_only | Ours(ASP) | 30.2 [28.6-32.3] n=3 | 30.5 | 57.7 [57.7-57.7] n=1/3 | 62.4 | null (0/3) | 68.0 |
| 00871 | placebo | none | 27.2 [26.0-28.6] n=3 | - | 35.9 [35.9-35.9] n=1/3 | - | null (0/3) | - |
| 00871 | oracle_visible | none | 37.6 [31.7-42.8] n=3 | - | null (0/3) | - | null (0/3) | - |
| 00871 | frontier_60m | Frontier | 28.0 [27.0-28.8] n=3 | 29.2 | 34.5 [31.4-39.3] n=3 | 55.7 | null (0/3) | 65.3 |
| 00871 | frontier_end_ref | Frontier | null (0/1) | 29.2 | null (0/1) | 55.7 | 67.7 [67.7-67.7] n=1 | 65.3 |
| 00871 | frontier_end | Frontier | 26.4 [26.4-26.4] n=1 | 29.2 | 43.2 [43.2-43.2] n=1 | 55.7 | 62.8 [62.8-62.8] n=1 | 65.3 |
| 00871 | crashed_frontier_1st | none | 26.1 [23.1-28.5] n=4 | - | 37.2 [30.7-46.7] n=4 | - | null (0/4) | - |
| 00871 | crashed_frontier_rerun | none | 27.0 [24.9-28.3] n=4 | - | 38.2 [38.2-38.2] n=1/4 | - | null (0/4) | - |

Sensitivity, means only (F1 x 100), at 10/50/100% of 0.8 B and of 1.2 B; `-` means no run has a value.

| Scene | Arm | 0.8B 10% | 0.8B 50% | 0.8B 100% | 1.2B 10% | 1.2B 50% | 1.2B 100% |
|---|---|---|---|---|---|---|---|
| 00853 | official | 15.8 (n=2) | 26.4 (n=2) | - | 18.3 (n=2) | 47.4 (n=1) | - |
| 00853 | filter_only | 12.6 (n=3) | 41.1 (n=3) | - | 14.8 (n=3) | 53.0 (n=2) | - |
| 00853 | placebo | 13.6 (n=3) | 39.5 (n=3) | - | 14.3 (n=3) | 48.4 (n=1) | - |
| 00853 | frontier_60m | 15.3 (n=3) | 39.7 (n=3) | - | 15.0 (n=3) | 48.8 (n=3) | - |
| 00853 | frontier_end_ref | - | - | - | - | - | - |
| 00853 | frontier_end | 12.8 (n=5) | 37.6 (n=5) | 55.6 (n=5) | 12.2 (n=5) | 45.6 (n=5) | 57.7 (n=1) |
| 00871 | official | 31.0 (n=3) | 55.2 (n=3) | - | 32.5 (n=3) | - | - |
| 00871 | filter_only | 29.3 (n=3) | 42.1 (n=2) | - | 31.9 (n=3) | - | - |
| 00871 | placebo | 26.3 (n=3) | 34.7 (n=2) | - | 29.2 (n=3) | - | - |
| 00871 | oracle_visible | 33.7 (n=3) | 61.1 (n=3) | - | 40.9 (n=3) | - | - |
| 00871 | frontier_60m | 28.1 (n=3) | 33.1 (n=3) | - | 28.5 (n=3) | 41.1 (n=3) | - |
| 00871 | frontier_end_ref | - | - | - | - | - | - |
| 00871 | frontier_end | 25.4 (n=1) | 35.7 (n=1) | 60.1 (n=1) | 26.4 (n=1) | 47.0 (n=1) | 62.2 (n=1) |
| 00871 | crashed_frontier_1st | 26.1 (n=4) | 35.5 (n=4) | 55.4 (n=1) | 27.2 (n=4) | 40.1 (n=3) | - |
| 00871 | crashed_frontier_rerun | 26.4 (n=4) | 32.9 (n=1) | - | 28.2 (n=4) | 46.8 (n=1) | - |

## Reference: frontier_made

This reference comes from the frontier explorer, so it favours frontier arms. The frontier_end_ref run scored against its own final map is self-referential.

| Scene | Arm | Paper method | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|---|
| 00853 | official | Ours(ASP) | 17.6 [15.2-20.1] n=2 | 34.4 | 39.9 [39.3-40.5] n=2 | 60.8 | null (0/2) | 66.7 |
| 00853 | filter_only | Ours(ASP) | 19.8 [18.6-21.6] n=3 | 34.4 | 52.6 [51.2-54.3] n=3 | 60.8 | null (0/3) | 66.7 |
| 00853 | placebo | none | 16.3 [12.2-18.6] n=3 | - | 49.2 [47.2-52.2] n=3 | - | null (0/3) | - |
| 00853 | frontier_60m | Frontier | 19.7 [18.2-21.5] n=3 | 18.6 | 55.1 [53.6-57.0] n=3 | 46.5 | null (0/3) | 58.8 |
| 00853 | frontier_end_ref | Frontier | null (0/1) | 18.6 | null (0/1) | 46.5 | null (0/1) | 58.8 |
| 00853 | frontier_end | Frontier | 17.9 [12.3-21.5] n=5 | 18.6 | 45.0 [37.9-53.3] n=5 | 46.5 | 64.5 [63.6-65.6] n=3/5 | 58.8 |
| 00871 | official | Ours(ASP) | 33.3 [32.0-35.8] n=3 | 30.5 | null (0/3) | 62.4 | null (0/3) | 68.0 |
| 00871 | filter_only | Ours(ASP) | 34.2 [31.2-38.0] n=3 | 30.5 | 61.4 [61.4-61.4] n=1/3 | 62.4 | null (0/3) | 68.0 |
| 00871 | placebo | none | 30.1 [29.7-30.7] n=3 | - | 38.6 [38.6-38.6] n=1/3 | - | null (0/3) | - |
| 00871 | oracle_visible | none | 39.6 [34.0-44.3] n=3 | - | null (0/3) | - | null (0/3) | - |
| 00871 | frontier_60m | Frontier | 37.6 [36.4-39.5] n=3 | 29.2 | 47.1 [43.9-51.9] n=3 | 55.7 | null (0/3) | 65.3 |
| 00871 | frontier_end_ref | Frontier | null (0/1) | 29.2 | null (0/1) | 55.7 | 88.1 [88.1-88.1] n=1 | 65.3 |
| 00871 | frontier_end | Frontier | 30.1 [30.1-30.1] n=1 | 29.2 | 51.0 [51.0-51.0] n=1 | 55.7 | 67.0 [67.0-67.0] n=1 | 65.3 |
| 00871 | crashed_frontier_1st | none | 34.8 [32.7-36.7] n=4 | - | 46.7 [42.0-56.6] n=4 | - | null (0/4) | - |
| 00871 | crashed_frontier_rerun | none | 33.4 [30.2-36.5] n=4 | - | 48.6 [48.6-48.6] n=1/4 | - | null (0/4) | - |

Sensitivity, means only (F1 x 100), at 10/50/100% of 0.8 B and of 1.2 B; `-` means no run has a value.

| Scene | Arm | 0.8B 10% | 0.8B 50% | 0.8B 100% | 1.2B 10% | 1.2B 50% | 1.2B 100% |
|---|---|---|---|---|---|---|---|
| 00853 | official | 17.3 (n=2) | 28.0 (n=2) | - | 19.5 (n=2) | 46.4 (n=1) | - |
| 00853 | filter_only | 18.3 (n=3) | 44.6 (n=3) | - | 19.8 (n=3) | 55.9 (n=2) | - |
| 00853 | placebo | 16.1 (n=3) | 44.4 (n=3) | - | 17.6 (n=3) | 53.1 (n=1) | - |
| 00853 | frontier_60m | 19.0 (n=3) | 48.0 (n=3) | - | 20.0 (n=3) | 57.6 (n=3) | - |
| 00853 | frontier_end_ref | - | - | - | - | - | - |
| 00853 | frontier_end | 17.5 (n=5) | 42.6 (n=5) | 62.8 (n=5) | 17.9 (n=5) | 52.1 (n=5) | 66.9 (n=1) |
| 00871 | official | 33.1 (n=3) | 59.5 (n=3) | - | 33.6 (n=3) | - | - |
| 00871 | filter_only | 33.2 (n=3) | 47.4 (n=2) | - | 36.5 (n=3) | - | - |
| 00871 | placebo | 29.1 (n=3) | 34.3 (n=2) | - | 30.8 (n=3) | - | - |
| 00871 | oracle_visible | 34.9 (n=3) | 63.7 (n=3) | - | 44.0 (n=3) | - | - |
| 00871 | frontier_60m | 37.1 (n=3) | 45.3 (n=3) | - | 38.0 (n=3) | 53.6 (n=3) | - |
| 00871 | frontier_end_ref | - | - | - | - | - | - |
| 00871 | frontier_end | 30.0 (n=1) | 42.2 (n=1) | 66.1 (n=1) | 30.1 (n=1) | 53.5 (n=1) | 67.4 (n=1) |
| 00871 | crashed_frontier_1st | 34.4 (n=4) | 44.5 (n=4) | 67.5 (n=1) | 35.9 (n=4) | 49.6 (n=3) | - |
| 00871 | crashed_frontier_rerun | 33.4 (n=4) | 43.6 (n=1) | - | 34.6 (n=4) | 60.4 (n=1) | - |

## GED (the author's own code)

gmatch4py GraphEditDistance(1, 1, 1, 1) with the author's costs, mean over graph0 and graph1, stage value at t. Lower is better. `mean [min-max] n`.

### Reference: hm3d

| Scene | Arm | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|
| 00853 | official | 624 [624-625] n=2 | 249.5 | 708 [700-716] n=2 | 147.0 | null | 147.0 |
| 00853 | filter_only | 620 [612-628] n=3 | 249.5 | 740 [708-774] n=3 | 147.0 | null | 147.0 |
| 00853 | placebo | 612 [610-616] n=3 | - | 726 [724-728] n=3 | - | null | - |
| 00853 | frontier_60m | 618 [617-619] n=3 | 279.0 | 745 [727-773] n=3 | 243.4 | null | 177.0 |
| 00853 | frontier_end_ref | null | 279.0 | null | 243.4 | null | 177.0 |
| 00853 | frontier_end | 611 [600-620] n=5 | 279.0 | 716 [688-748] n=5 | 243.4 | 812 [794-842] n=3 | 177.0 |
| 00871 | official | 823 [814-838] n=3 | 279.0 | null | 204.5 | null | 194.5 |
| 00871 | filter_only | 824 [816-841] n=3 | 279.0 | 949 | 204.5 | null | 194.5 |
| 00871 | placebo | 807 [802-816] n=3 | - | 856 | - | null | - |
| 00871 | oracle_visible | 842 [824-862] n=3 | - | null | - | null | - |
| 00871 | frontier_60m | 819 [814-827] n=3 | 292.1 | 866 [860-876] n=3 | 233.0 | null | 203.5 |
| 00871 | frontier_end_ref | null | 292.1 | null | 233.0 | 1032 | 203.5 |
| 00871 | frontier_end | 808 | 292.1 | 919 | 233.0 | 1028 | 203.5 |
| 00871 | crashed_frontier_1st | 812 [801-824] n=4 | - | 874 [844-930] n=4 | - | null | - |
| 00871 | crashed_frontier_rerun | 816 [812-819] n=4 | - | 880 | - | null | - |

### Reference: apr

| Scene | Arm | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|
| 00853 | official | 346 [340-351] n=2 | 249.5 | 272 [256-288] n=2 | 147.0 | null | 147.0 |
| 00853 | filter_only | 345 [338-350] n=3 | 249.5 | 270 [234-291] n=3 | 147.0 | null | 147.0 |
| 00853 | placebo | 341 [330-350] n=3 | - | 252 [226-272] n=3 | - | null | - |
| 00853 | frontier_60m | 341 [338-346] n=3 | 279.0 | 257 [228-274] n=3 | 243.4 | null | 177.0 |
| 00853 | frontier_end_ref | null | 279.0 | null | 243.4 | null | 177.0 |
| 00853 | frontier_end | 346 [341-349] n=5 | 279.0 | 260 [240-273] n=5 | 243.4 | 230 [210-244] n=3 | 177.0 |
| 00871 | official | 308 [292-316] n=3 | 279.0 | null | 204.5 | null | 194.5 |
| 00871 | filter_only | 327 [304-344] n=3 | 279.0 | 270 | 204.5 | null | 194.5 |
| 00871 | placebo | 312 [305-318] n=3 | - | 323 | - | null | - |
| 00871 | oracle_visible | 302 [288-321] n=3 | - | null | - | null | - |
| 00871 | frontier_60m | 335 [328-340] n=3 | 292.1 | 335 [332-339] n=3 | 233.0 | null | 203.5 |
| 00871 | frontier_end_ref | null | 292.1 | null | 233.0 | 220 | 203.5 |
| 00871 | frontier_end | 320 | 292.1 | 329 | 233.0 | 226 | 203.5 |
| 00871 | crashed_frontier_1st | 320 [314-328] n=4 | - | 315 [302-323] n=4 | - | null | - |
| 00871 | crashed_frontier_rerun | 326 [318-340] n=4 | - | 343 | - | null | - |

### Reference: frontier_made

| Scene | Arm | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|
| 00853 | official | 284 [283-286] n=2 | 249.5 | 256 [238-273] n=2 | 147.0 | null | 147.0 |
| 00853 | filter_only | 278 [266-285] n=3 | 249.5 | 193 [166-234] n=3 | 147.0 | null | 147.0 |
| 00853 | placebo | 275 [263-286] n=3 | - | 211 [188-224] n=3 | - | null | - |
| 00853 | frontier_60m | 271 [266-276] n=3 | 279.0 | 206 [195-214] n=3 | 243.4 | null | 177.0 |
| 00853 | frontier_end_ref | null | 279.0 | null | 243.4 | null | 177.0 |
| 00853 | frontier_end | 270 [264-280] n=5 | 279.0 | 219 [180-242] n=5 | 243.4 | 170 [155-182] n=3 | 177.0 |
| 00871 | official | 270 [264-280] n=3 | 279.0 | null | 204.5 | null | 194.5 |
| 00871 | filter_only | 273 [252-292] n=3 | 279.0 | 238 | 204.5 | null | 194.5 |
| 00871 | placebo | 265 [260-268] n=3 | - | 276 | - | null | - |
| 00871 | oracle_visible | 258 [238-272] n=3 | - | null | - | null | - |
| 00871 | frontier_60m | 268 [262-271] n=3 | 292.1 | 253 [249-258] n=3 | 233.0 | null | 203.5 |
| 00871 | frontier_end_ref | null | 292.1 | null | 233.0 | 96 | 203.5 |
| 00871 | frontier_end | 262 | 292.1 | 266 | 233.0 | 174 | 203.5 |
| 00871 | crashed_frontier_1st | 265 [262-268] n=4 | - | 252 [236-261] n=4 | - | null | - |
| 00871 | crashed_frontier_rerun | 268 [252-290] n=4 | - | 262 | - | null | - |

## Seconds per metre

Final navigation time over final path length, from each run's last scored stage.

| Scene | Arm | Runs | s/m mean [min-max] | Final time s (mean) | Final path m (mean) |
|---|---|---|---|---|---|
| 00853 | official | 2 | 6.53 [6.37-6.68] | 377.1 | 57.7 |
| 00853 | filter_only | 3 | 6.33 [6.10-6.66] | 392.6 | 62.0 |
| 00853 | placebo | 3 | 5.84 [5.63-6.13] | 381.6 | 65.3 |
| 00853 | frontier_60m | 3 | 6.80 [6.46-7.09] | 435.0 | 64.0 |
| 00853 | frontier_end_ref | 1 | 6.61 [6.61-6.61] | 632.1 | 95.7 |
| 00853 | frontier_end | 5 | 6.98 [6.40-7.84] | 696.0 | 100.6 |
| 00871 | official | 3 | 6.07 [5.66-6.62] | 378.5 | 62.4 |
| 00871 | filter_only | 3 | 6.23 [5.26-6.97] | 369.6 | 59.0 |
| 00871 | placebo | 3 | 6.25 [5.26-7.58] | 380.0 | 60.7 |
| 00871 | oracle_visible | 3 | 5.52 [5.31-5.78] | 344.6 | 62.4 |
| 00871 | frontier_60m | 3 | 8.67 [7.97-9.18] | 539.0 | 62.1 |
| 00871 | frontier_end_ref | 1 | 6.73 [6.73-6.73] | 809.1 | 120.2 |
| 00871 | frontier_end | 1 | 6.72 [6.72-6.72] | 1263.5 | 188.1 |
| 00871 | crashed_frontier_1st | 4 | 8.10 [7.97-8.29] | 607.2 | 75.0 |
| 00871 | crashed_frontier_rerun | 4 | 8.62 [8.16-9.42] | 276.0 | 31.9 |

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
