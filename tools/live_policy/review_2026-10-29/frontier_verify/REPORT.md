# Step 7: independent recompute (Opus 5.5 verifier, 2026-10-30 01:35 IST)

The verifier wrote its own scorer (score.py) and exact permutation test (permtest.py, permtest_lib.py) from the pre-registration. It ran them before opening e1_analysis.py or any output, and only then compared.

## Result
- **Registered result confirmed.** Neither contrast is significant.
- **Per-run AUCs:** all 31 match all_scores_with_frontier.json within 4.9e-5. The per-stage F1 and AUC equal the author's match_objects / load_eval_graph / area_under_curve exactly.
- **Counted and dropped runs:** the same as e1_analysis.py. Dropped by the 50 m rule: e1_00853_s44_official_60m (46.80 m), its _rerun1 (44.25 m), and e1_00871_s43_placebo_60m (0 m).

| | official − frontier | placebo − frontier |
|---|---|---|
| Statistic, 60 m | −0.011967 | −0.024940 |
| Per scene, 00853 / 00871 | −0.05184 / +0.02791 | −0.04717 / −0.00270 |
| p, 60 m (relabellings) | 0.47 (200) | 0.07 (400) |
| Holm p | 0.47 | 0.14 |
| 95% CI, shifts with p ≥ 0.05 | [−0.0533, +0.0287] | [−0.0506, +0.0025] |
| Statistic, 50 m (p) | −0.016605 (0.34) | −0.023675 (0.065) |
| Signs agree | yes | yes |

## Differences from the main analysis (none changes a conclusion)
- **Official 50 m p:** 0.34 exact, against 0.345 in E4_official_vs_frontier_hm3d_50m.json. e1_analysis.py tests on AUCs rounded to 4 decimals, so one relabelling 9.4e-7 below the observed statistic ties it.
- **CI endpoints:** e1_analysis.py searches a 0.0005 grid and keeps shifts with p ≥ 0.05, so its endpoints lie up to one step inside the exact ones. Using p > 0.05 instead moves endpoints by up to 0.003.
- **Minimum attainable p:** e1_analysis.py reports 2/n = 0.01 for the official contrast. The true value is 0.005, because 00853's 2-v-3 split lets one relabelling be the sole extreme. The reported value is the more cautious one.

## Fairness checks
- **Reference:** the same HM3D reference files for every arm; hashes match MANIFEST.sha256. (verified)
- **Frames:** every run's executed_path maps habitat to world with exactly the reference transform; median object offsets from the reference are 1-3 cm. The start jitter did not shift the frontier maps. (verified)
- **Mapper:** the same launch file and the same printed parameters for frontier, official and placebo runs. (verified)
- **No predicted nodes** in any scored file. (verified)
- **Unscored last graph:** ASP writes a stage's stats only after its motion, so its last graph can go unscored; frontier never loses one. This happens once: e1_00853_s43_official_60m has a stage-20 graph at about 55.9 m. Counting it would add 0.0008 to that run's AUC and 0.0002 to the official contrast. (verified)
- **Stage density:** frontier has more stages (41-46 on 00871, against 12-28 for ASP). Thinning frontier to every 2nd or 3rd stage moves its AUC by at most 0.0032. (verified)
- **Scans per metre:** both explorers turn a full 360° at every stop, and the 60 m budget counts only forward motion. On 00871 the frontier therefore makes 2-3 times as many stops, and turns, per metre. This is the explorer's behaviour under the registered budget, not a scoring error. (code read)
- **Jitter:** seed 43 on 00853 moved the start 0.31 m in x, beyond 0.25 m, because of the navmesh snap that the pre-registration allows. (verified)
- **Converters:** the verifier could not run the two YAML converters on the same input, because the off-host copy has no DSG files. The main session did so on the host on two ASP stages: identical nodes, positions and edges. (main session, verified)
