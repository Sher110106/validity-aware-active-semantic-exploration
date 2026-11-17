<!-- written by rescore_paper.py: another reading of the November ASP row -->

**Another reading of the row "ASP + DeepSeek, November": without `e8_00853_s43_official_105m`.** Every other row equals `../paper_compare.md`, which holds the runs as they ran. Why: `DEVIATIONS_NOVEMBER.md`.

# Scores on the paper's scale

F1 x 100, stage value at the last stage with navigation time at most t. Each cell reads `mean [min-max] n`; n counts runs with a value at t. The paper column is Fig. 4 (left) of arXiv 2510.05430v2. Budget B: 00853 = 632.1751 s (--budget), 00871 = 1300.2523 s (--budget).

## Reference: hm3d

| Scene | Arm | Paper method | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|---|
| 00853 | official | Ours(ASP) | 8.0 [6.8-9.3] n=2 | 34.4 | 21.6 [20.5-22.6] n=2 | 60.8 | null (0/2) | 66.7 |
| 00853 | ASP + DeepSeek, November | Ours(ASP) | 9.0 [8.3-9.7] n=2 | 34.4 | 27.6 [24.5-30.6] n=2 | 60.8 | 35.7 [35.7-35.7] n=1/2 | 66.7 |
| 00853 | filter_only | Ours(ASP) | 7.6 [5.7-10.3] n=3 | 34.4 | 24.1 [19.3-29.4] n=3 | 60.8 | null (0/3) | 66.7 |
| 00853 | placebo | none | 6.4 [4.7-7.8] n=3 | - | 23.1 [20.5-25.6] n=3 | - | null (0/3) | - |
| 00853 | frontier_60m | Frontier | 9.7 [8.8-10.4] n=3 | 18.6 | 26.7 [23.7-29.8] n=3 | 46.5 | null (0/3) | 58.8 |
| 00853 | frontier_end_ref | Frontier | null (0/1) | 18.6 | null (0/1) | 46.5 | null (0/1) | 58.8 |
| 00853 | frontier_end | Frontier | 7.7 [6.3-8.9] n=5 | 18.6 | 21.9 [19.9-23.9] n=5 | 46.5 | 32.9 [30.2-35.6] n=3/5 | 58.8 |
| 00871 | official | Ours(ASP) | 8.5 [6.7-9.5] n=3 | 30.5 | null (0/3) | 62.4 | null (0/3) | 68.0 |
| 00871 | filter_only | Ours(ASP) | 10.1 [8.1-13.5] n=3 | 30.5 | null (0/3) | 62.4 | null (0/3) | 68.0 |
| 00871 | placebo | none | 8.1 [7.3-9.6] n=3 | - | null (0/3) | - | null (0/3) | - |
| 00871 | oracle_visible | none | 10.9 [7.7-12.6] n=3 | - | null (0/3) | - | null (0/3) | - |
| 00871 | frontier_60m | Frontier | 8.7 [8.2-9.2] n=3 | 29.2 | null (0/3) | 55.7 | null (0/3) | 65.3 |
| 00871 | frontier_end_ref | Frontier | null (0/1) | 29.2 | null (0/1) | 55.7 | null (0/1) | 65.3 |
| 00871 | frontier_end | Frontier | 9.1 [6.3-11.9] n=5 | 29.2 | 19.8 [17.6-22.9] n=5 | 55.7 | 25.1 [24.0-26.8] n=3/5 | 65.3 |
| 00871 | crashed_frontier_1st | none | 7.9 [7.0-9.6] n=4 | - | 20.0 [20.0-20.0] n=1/4 | - | null (0/4) | - |
| 00871 | crashed_frontier_rerun | none | 8.6 [6.6-9.6] n=3/4 | - | null (0/4) | - | null (0/4) | - |

Sensitivity, means only (F1 x 100), at 10/50/100% of 0.8 B and of 1.2 B; `-` means no run has a value.

| Scene | Arm | 0.8B 10% | 0.8B 50% | 0.8B 100% | 1.2B 10% | 1.2B 50% | 1.2B 100% |
|---|---|---|---|---|---|---|---|
| 00853 | official | 7.5 (n=2) | 14.1 (n=2) | - | 8.5 (n=2) | 26.8 (n=1) | - |
| 00853 | ASP + DeepSeek, November | 8.8 (n=2) | 22.4 (n=2) | 32.3 (n=2) | 10.2 (n=2) | 29.3 (n=2) | - |
| 00853 | filter_only | 6.6 (n=3) | 19.2 (n=3) | - | 7.6 (n=3) | 27.8 (n=2) | - |
| 00853 | placebo | 6.1 (n=3) | 19.6 (n=3) | - | 7.3 (n=3) | 25.9 (n=1) | - |
| 00853 | frontier_60m | 9.7 (n=3) | 22.4 (n=3) | - | 9.8 (n=3) | 28.2 (n=3) | - |
| 00853 | frontier_end_ref | - | - | - | - | - | - |
| 00853 | frontier_end | 7.5 (n=5) | 20.6 (n=5) | 31.7 (n=5) | 7.8 (n=5) | 26.3 (n=5) | 33.5 (n=1) |
| 00871 | official | 8.0 (n=3) | - | - | 9.5 (n=3) | - | - |
| 00871 | filter_only | 8.7 (n=3) | - | - | 10.4 (n=3) | - | - |
| 00871 | placebo | 6.8 (n=3) | - | - | 8.2 (n=3) | - | - |
| 00871 | oracle_visible | 10.4 (n=3) | - | - | 12.0 (n=3) | - | - |
| 00871 | frontier_60m | 7.6 (n=3) | 14.9 (n=2) | - | 9.2 (n=3) | - | - |
| 00871 | frontier_end_ref | - | - | - | - | - | - |
| 00871 | frontier_end | 8.1 (n=5) | 17.0 (n=5) | 24.1 (n=5) | 9.4 (n=5) | 21.6 (n=5) | 25.6 (n=2) |
| 00871 | crashed_frontier_1st | 7.0 (n=4) | 13.4 (n=3) | - | 8.3 (n=4) | - | - |
| 00871 | crashed_frontier_rerun | 7.5 (n=4) | - | - | 8.6 (n=3) | - | - |

## Reference: apr

| Scene | Arm | Paper method | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|---|
| 00853 | official | Ours(ASP) | 16.5 [13.8-19.1] n=2 | 34.4 | 38.7 [37.2-40.1] n=2 | 60.8 | null (0/2) | 66.7 |
| 00853 | ASP + DeepSeek, November | Ours(ASP) | 19.1 [17.1-21.2] n=2 | 34.4 | 53.6 [45.7-61.5] n=2 | 60.8 | 62.9 [62.9-62.9] n=1/2 | 66.7 |
| 00853 | filter_only | Ours(ASP) | 14.8 [12.1-18.4] n=3 | 34.4 | 48.3 [40.9-52.2] n=3 | 60.8 | null (0/3) | 66.7 |
| 00853 | placebo | none | 13.8 [10.8-16.1] n=3 | - | 43.9 [39.4-48.2] n=3 | - | null (0/3) | - |
| 00853 | frontier_60m | Frontier | 15.3 [12.9-16.9] n=3 | 18.6 | 45.6 [41.7-52.4] n=3 | 46.5 | null (0/3) | 58.8 |
| 00853 | frontier_end_ref | Frontier | null (0/1) | 18.6 | null (0/1) | 46.5 | null (0/1) | 58.8 |
| 00853 | frontier_end | Frontier | 12.4 [10.8-14.7] n=5 | 18.6 | 39.5 [33.9-42.0] n=5 | 46.5 | 55.6 [53.5-59.6] n=3/5 | 58.8 |
| 00871 | official | Ours(ASP) | 33.9 [30.8-36.4] n=3 | 30.5 | null (0/3) | 62.4 | null (0/3) | 68.0 |
| 00871 | filter_only | Ours(ASP) | 33.0 [29.9-37.6] n=3 | 30.5 | null (0/3) | 62.4 | null (0/3) | 68.0 |
| 00871 | placebo | none | 31.7 [30.2-32.6] n=3 | - | null (0/3) | - | null (0/3) | - |
| 00871 | oracle_visible | none | 42.8 [31.7-48.6] n=3 | - | null (0/3) | - | null (0/3) | - |
| 00871 | frontier_60m | Frontier | 30.2 [28.8-31.6] n=3 | 29.2 | null (0/3) | 55.7 | null (0/3) | 65.3 |
| 00871 | frontier_end_ref | Frontier | null (0/1) | 29.2 | null (0/1) | 55.7 | null (0/1) | 65.3 |
| 00871 | frontier_end | Frontier | 31.9 [27.8-37.4] n=5 | 29.2 | 59.2 [52.2-67.1] n=5 | 55.7 | 66.6 [64.4-68.3] n=3/5 | 65.3 |
| 00871 | crashed_frontier_1st | none | 28.9 [25.0-31.8] n=4 | - | 55.4 [55.4-55.4] n=1/4 | - | null (0/4) | - |
| 00871 | crashed_frontier_rerun | none | 31.7 [28.7-33.4] n=3/4 | - | null (0/4) | - | null (0/4) | - |

Sensitivity, means only (F1 x 100), at 10/50/100% of 0.8 B and of 1.2 B; `-` means no run has a value.

| Scene | Arm | 0.8B 10% | 0.8B 50% | 0.8B 100% | 1.2B 10% | 1.2B 50% | 1.2B 100% |
|---|---|---|---|---|---|---|---|
| 00853 | official | 15.8 (n=2) | 26.4 (n=2) | - | 18.3 (n=2) | 47.4 (n=1) | - |
| 00853 | ASP + DeepSeek, November | 18.8 (n=2) | 46.2 (n=2) | 62.1 (n=2) | 21.9 (n=2) | 57.2 (n=2) | - |
| 00853 | filter_only | 12.6 (n=3) | 41.1 (n=3) | - | 14.8 (n=3) | 53.0 (n=2) | - |
| 00853 | placebo | 13.6 (n=3) | 39.5 (n=3) | - | 14.3 (n=3) | 48.4 (n=1) | - |
| 00853 | frontier_60m | 15.3 (n=3) | 39.7 (n=3) | - | 15.0 (n=3) | 48.8 (n=3) | - |
| 00853 | frontier_end_ref | - | - | - | - | - | - |
| 00853 | frontier_end | 12.8 (n=5) | 37.6 (n=5) | 55.6 (n=5) | 12.2 (n=5) | 45.6 (n=5) | 57.7 (n=1) |
| 00871 | official | 32.9 (n=3) | - | - | 37.3 (n=3) | - | - |
| 00871 | filter_only | 31.9 (n=3) | - | - | 34.0 (n=3) | - | - |
| 00871 | placebo | 29.2 (n=3) | - | - | 33.6 (n=3) | - | - |
| 00871 | oracle_visible | 42.1 (n=3) | - | - | 47.2 (n=3) | - | - |
| 00871 | frontier_60m | 28.5 (n=3) | 44.2 (n=2) | - | 31.3 (n=3) | - | - |
| 00871 | frontier_end_ref | - | - | - | - | - | - |
| 00871 | frontier_end | 29.6 (n=5) | 51.3 (n=5) | 65.0 (n=5) | 33.0 (n=5) | 62.9 (n=5) | 67.4 (n=2) |
| 00871 | crashed_frontier_1st | 27.2 (n=4) | 42.8 (n=3) | - | 29.5 (n=4) | - | - |
| 00871 | crashed_frontier_rerun | 28.5 (n=4) | - | - | 32.9 (n=3) | - | - |

## Reference: frontier_made

This reference comes from the frontier explorer, so it favours frontier arms. The frontier_end_ref run scored against its own final map is self-referential.

| Scene | Arm | Paper method | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|---|
| 00853 | official | Ours(ASP) | 17.6 [15.2-20.1] n=2 | 34.4 | 39.9 [39.3-40.5] n=2 | 60.8 | null (0/2) | 66.7 |
| 00853 | ASP + DeepSeek, November | Ours(ASP) | 19.6 [17.4-21.8] n=2 | 34.4 | 56.1 [52.2-60.0] n=2 | 60.8 | 65.2 [65.2-65.2] n=1/2 | 66.7 |
| 00853 | filter_only | Ours(ASP) | 19.8 [18.6-21.6] n=3 | 34.4 | 52.6 [51.2-54.3] n=3 | 60.8 | null (0/3) | 66.7 |
| 00853 | placebo | none | 16.3 [12.2-18.6] n=3 | - | 49.2 [47.2-52.2] n=3 | - | null (0/3) | - |
| 00853 | frontier_60m | Frontier | 19.7 [18.2-21.5] n=3 | 18.6 | 55.1 [53.6-57.0] n=3 | 46.5 | null (0/3) | 58.8 |
| 00853 | frontier_end_ref | Frontier | null (0/1) | 18.6 | null (0/1) | 46.5 | null (0/1) | 58.8 |
| 00853 | frontier_end | Frontier | 17.9 [12.3-21.5] n=5 | 18.6 | 45.0 [37.9-53.3] n=5 | 46.5 | 64.5 [63.6-65.6] n=3/5 | 58.8 |
| 00871 | official | Ours(ASP) | 35.6 [33.2-39.1] n=3 | 30.5 | null (0/3) | 62.4 | null (0/3) | 68.0 |
| 00871 | filter_only | Ours(ASP) | 38.6 [33.9-44.3] n=3 | 30.5 | null (0/3) | 62.4 | null (0/3) | 68.0 |
| 00871 | placebo | none | 33.5 [31.6-35.0] n=3 | - | null (0/3) | - | null (0/3) | - |
| 00871 | oracle_visible | none | 46.0 [34.0-53.1] n=3 | - | null (0/3) | - | null (0/3) | - |
| 00871 | frontier_60m | Frontier | 40.3 [38.6-41.8] n=3 | 29.2 | null (0/3) | 55.7 | null (0/3) | 65.3 |
| 00871 | frontier_end_ref | Frontier | null (0/1) | 29.2 | null (0/1) | 55.7 | null (0/1) | 65.3 |
| 00871 | frontier_end | Frontier | 39.4 [31.6-46.5] n=5 | 29.2 | 65.1 [56.8-72.1] n=5 | 55.7 | 69.6 [67.2-71.5] n=3/5 | 65.3 |
| 00871 | crashed_frontier_1st | none | 37.4 [36.2-39.6] n=4 | - | 67.5 [67.5-67.5] n=1/4 | - | null (0/4) | - |
| 00871 | crashed_frontier_rerun | none | 38.0 [32.5-41.8] n=3/4 | - | null (0/4) | - | null (0/4) | - |

Sensitivity, means only (F1 x 100), at 10/50/100% of 0.8 B and of 1.2 B; `-` means no run has a value.

| Scene | Arm | 0.8B 10% | 0.8B 50% | 0.8B 100% | 1.2B 10% | 1.2B 50% | 1.2B 100% |
|---|---|---|---|---|---|---|---|
| 00853 | official | 17.3 (n=2) | 28.0 (n=2) | - | 19.5 (n=2) | 46.4 (n=1) | - |
| 00853 | ASP + DeepSeek, November | 19.6 (n=2) | 47.5 (n=2) | 62.6 (n=2) | 22.3 (n=2) | 58.9 (n=2) | - |
| 00853 | filter_only | 18.3 (n=3) | 44.6 (n=3) | - | 19.8 (n=3) | 55.9 (n=2) | - |
| 00853 | placebo | 16.1 (n=3) | 44.4 (n=3) | - | 17.6 (n=3) | 53.1 (n=1) | - |
| 00853 | frontier_60m | 19.0 (n=3) | 48.0 (n=3) | - | 20.0 (n=3) | 57.6 (n=3) | - |
| 00853 | frontier_end_ref | - | - | - | - | - | - |
| 00853 | frontier_end | 17.5 (n=5) | 42.6 (n=5) | 62.8 (n=5) | 17.9 (n=5) | 52.1 (n=5) | 66.9 (n=1) |
| 00871 | official | 34.3 (n=3) | - | - | 40.1 (n=3) | - | - |
| 00871 | filter_only | 36.5 (n=3) | - | - | 39.8 (n=3) | - | - |
| 00871 | placebo | 30.8 (n=3) | - | - | 33.6 (n=3) | - | - |
| 00871 | oracle_visible | 44.8 (n=3) | - | - | 50.4 (n=3) | - | - |
| 00871 | frontier_60m | 38.0 (n=3) | 55.5 (n=2) | - | 41.9 (n=3) | - | - |
| 00871 | frontier_end_ref | - | - | - | - | - | - |
| 00871 | frontier_end | 36.7 (n=5) | 56.8 (n=5) | 69.2 (n=5) | 40.0 (n=5) | 68.2 (n=5) | 68.2 (n=2) |
| 00871 | crashed_frontier_1st | 35.9 (n=4) | 51.9 (n=3) | - | 37.8 (n=4) | - | - |
| 00871 | crashed_frontier_rerun | 35.2 (n=4) | - | - | 38.9 (n=3) | - | - |

## GED (the author's own code)

gmatch4py GraphEditDistance(1, 1, 1, 1) with the author's costs, mean over graph0 and graph1, stage value at t. Lower is better. `mean [min-max] n`.

### Reference: hm3d

| Scene | Arm | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|
| 00853 | official | 624 [624-625] n=2 | 249.5 | 708 [700-716] n=2 | 147.0 | null | 147.0 |
| 00853 | ASP + DeepSeek, November | 623 [616-630] n=2 | 249.5 | 758 [734-782] n=2 | 147.0 | 826 | 147.0 |
| 00853 | filter_only | 620 [612-628] n=3 | 249.5 | 740 [708-774] n=3 | 147.0 | null | 147.0 |
| 00853 | placebo | 612 [610-616] n=3 | - | 726 [724-728] n=3 | - | null | - |
| 00853 | frontier_60m | 618 [617-619] n=3 | 279.0 | 745 [727-773] n=3 | 243.4 | null | 177.0 |
| 00853 | frontier_end_ref | null | 279.0 | null | 243.4 | null | 177.0 |
| 00853 | frontier_end | 611 [600-620] n=5 | 279.0 | 716 [688-748] n=5 | 243.4 | 812 [794-842] n=3 | 177.0 |
| 00871 | official | 825 [804-842] n=3 | 279.0 | null | 204.5 | null | 194.5 |
| 00871 | filter_only | 836 [824-855] n=3 | 279.0 | null | 204.5 | null | 194.5 |
| 00871 | placebo | 823 [812-833] n=3 | - | null | - | null | - |
| 00871 | oracle_visible | 866 [824-888] n=3 | - | null | - | null | - |
| 00871 | frontier_60m | 825 [817-834] n=3 | 292.1 | null | 233.0 | null | 203.5 |
| 00871 | frontier_end_ref | null | 292.1 | null | 233.0 | null | 203.5 |
| 00871 | frontier_end | 834 [814-857] n=5 | 292.1 | 996 [962-1042] n=5 | 233.0 | 1060 [1041-1074] n=3 | 203.5 |
| 00871 | crashed_frontier_1st | 826 [818-831] n=4 | - | 980 | - | null | - |
| 00871 | crashed_frontier_rerun | 830 [828-832] n=3 | - | null | - | null | - |

### Reference: apr

| Scene | Arm | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|
| 00853 | official | 346 [340-351] n=2 | 249.5 | 272 [256-288] n=2 | 147.0 | null | 147.0 |
| 00853 | ASP + DeepSeek, November | 329 [326-332] n=2 | 249.5 | 243 [230-256] n=2 | 147.0 | 194 | 147.0 |
| 00853 | filter_only | 345 [338-350] n=3 | 249.5 | 270 [234-291] n=3 | 147.0 | null | 147.0 |
| 00853 | placebo | 341 [330-350] n=3 | - | 252 [226-272] n=3 | - | null | - |
| 00853 | frontier_60m | 341 [338-346] n=3 | 279.0 | 257 [228-274] n=3 | 243.4 | null | 177.0 |
| 00853 | frontier_end_ref | null | 279.0 | null | 243.4 | null | 177.0 |
| 00853 | frontier_end | 346 [341-349] n=5 | 279.0 | 260 [240-273] n=5 | 243.4 | 230 [210-244] n=3 | 177.0 |
| 00871 | official | 308 [302-320] n=3 | 279.0 | null | 204.5 | null | 194.5 |
| 00871 | filter_only | 323 [310-342] n=3 | 279.0 | null | 204.5 | null | 194.5 |
| 00871 | placebo | 313 [308-322] n=3 | - | null | - | null | - |
| 00871 | oracle_visible | 295 [270-321] n=3 | - | null | - | null | - |
| 00871 | frontier_60m | 322 [315-327] n=3 | 292.1 | null | 233.0 | null | 203.5 |
| 00871 | frontier_end_ref | null | 292.1 | null | 233.0 | null | 203.5 |
| 00871 | frontier_end | 324 [314-330] n=5 | 292.1 | 255 [208-299] n=5 | 233.0 | 216 [206-225] n=3 | 203.5 |
| 00871 | crashed_frontier_1st | 318 [315-321] n=4 | - | 284 | - | null | - |
| 00871 | crashed_frontier_rerun | 323 [315-330] n=3 | - | null | - | null | - |

### Reference: frontier_made

| Scene | Arm | 10% ours | 10% paper | 50% ours | 50% paper | 100% ours | 100% paper |
|---|---|---|---|---|---|---|---|
| 00853 | official | 284 [283-286] n=2 | 249.5 | 256 [238-273] n=2 | 147.0 | null | 147.0 |
| 00853 | ASP + DeepSeek, November | 282 [280-283] n=2 | 249.5 | 192 [182-202] n=2 | 147.0 | 170 | 147.0 |
| 00853 | filter_only | 278 [266-285] n=3 | 249.5 | 193 [166-234] n=3 | 147.0 | null | 147.0 |
| 00853 | placebo | 275 [263-286] n=3 | - | 211 [188-224] n=3 | - | null | - |
| 00853 | frontier_60m | 271 [266-276] n=3 | 279.0 | 206 [195-214] n=3 | 243.4 | null | 177.0 |
| 00853 | frontier_end_ref | null | 279.0 | null | 243.4 | null | 177.0 |
| 00853 | frontier_end | 270 [264-280] n=5 | 279.0 | 219 [180-242] n=5 | 243.4 | 170 [155-182] n=3 | 177.0 |
| 00871 | official | 256 [249-261] n=3 | 279.0 | null | 204.5 | null | 194.5 |
| 00871 | filter_only | 264 [252-276] n=3 | 279.0 | null | 204.5 | null | 194.5 |
| 00871 | placebo | 264 [256-268] n=3 | - | null | - | null | - |
| 00871 | oracle_visible | 248 [236-272] n=3 | - | null | - | null | - |
| 00871 | frontier_60m | 259 [254-262] n=3 | 292.1 | null | 233.0 | null | 203.5 |
| 00871 | frontier_end_ref | null | 292.1 | null | 233.0 | null | 203.5 |
| 00871 | frontier_end | 264 [250-272] n=5 | 292.1 | 211 [160-252] n=5 | 233.0 | 178 [159-198] n=3 | 203.5 |
| 00871 | crashed_frontier_1st | 265 [260-275] n=4 | - | 197 | - | null | - |
| 00871 | crashed_frontier_rerun | 260 [246-271] n=3 | - | null | - | null | - |

## Seconds per metre

Final navigation time over final path length, from each run's last scored stage.

| Scene | Arm | Runs | s/m mean [min-max] | Final time s (mean) | Final path m (mean) |
|---|---|---|---|---|---|
| 00853 | official | 2 | 6.53 [6.37-6.68] | 377.1 | 57.7 |
| 00853 | ASP + DeepSeek, November | 2 | 5.70 [5.36-6.04] | 628.1 | 110.4 |
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
| 00871 | frontier_end | 5 | 7.25 [6.72-7.95] | 1399.0 | 194.8 |
| 00871 | crashed_frontier_1st | 4 | 8.10 [7.97-8.29] | 607.2 | 75.0 |
| 00871 | crashed_frontier_rerun | 4 | 8.62 [8.16-9.42] | 276.0 | 31.9 |

## Not comparable

- The references differ. The paper scores against a hand-driven full-scene map. We use the HM3D human-label map, the frontier-made map (biased toward frontier), and a coverage-tour map when one exists.
- October's ASP runs stop at 60 m of path, which took 289-468 s here. The row "ASP + DeepSeek, November" ran to the first checkpoint at or past 105 m of path (604-652 s). A run has no value at a t past its last stage, so an October run's 100% readout is null, a November run has a 100% value only if it reached B, and a 50% readout is null when the run ended sooner.
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
