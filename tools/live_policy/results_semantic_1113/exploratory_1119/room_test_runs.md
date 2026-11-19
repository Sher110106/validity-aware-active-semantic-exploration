> **Exploratory.** Written 2026-11-19 after every result was seen. No verdict rests on it. See `DEVIATIONS_NOVEMBER.md`.

# Readout 3: the paper's room test at run level

**Source.** `results_semantic_1113/claude/room_test.json, live.runs[]`. Its live part is the same in `exploratory/room_test.json` (checked). Per live run I read `n_regions_unseen_at_stage0` (rooms that could be predicted before found) and the length of the list in the field named below (rooms predicted before found, type matched).

**Rule.** type matched; at least 2 of 8 members put a new room of that type within 2.5 m of the region centre before the region is first seen (section 11). The first view, "eight_member_stages", is the section 11 rule: it counts only stages that hold all 8 members. The second, "all_stages", counts every stage that has members. Both use the type-matched lists; no field of the untyped count is used.

## View `eight_member_stages`: field `predicted_stages_with_8_members_typed`

| Run | Scene | Arm | Could be | Predicted | Rate | Stages with 8 members | Stages |
|---|---|---|---|---|---|---|---|
| e1_00853_s42_official_60m | 00853 | official | 10 | 2 | 20.0% | 4 | 18 |
| e1_00853_s42_placebo_60m | 00853 | placebo | 10 | 1 | 10.0% | 16 | 16 |
| e1_00853_s43_official_60m | 00853 | official | 10 | 1 | 10.0% | 11 | 21 |
| e1_00853_s43_placebo_60m | 00853 | placebo | 10 | 2 | 20.0% | 18 | 18 |
| e1_00853_s44_placebo_60m | 00853 | placebo | 10 | 0 | 0.0% | 21 | 21 |
| e1_00871_s42_official_60m | 00871 | official | 13 | 2 | 15.4% | 4 | 17 |
| e1_00871_s42_placebo_60m | 00871 | placebo | 13 | 2 | 15.4% | 15 | 15 |
| e1_00871_s43_official_60m | 00871 | official | 13 | 3 | 23.1% | 10 | 18 |
| e1_00871_s43_placebo_60m_rerun1 | 00871 | placebo | 13 | 0 | 0.0% | 12 | 12 |
| e1_00871_s44_official_60m | 00871 | official | 13 | 2 | 15.4% | 8 | 19 |
| e1_00871_s44_placebo_60m | 00871 | placebo | 13 | 1 | 7.7% | 28 | 28 |
| e2_00853_s42_filter_only_60m | 00853 | filter_only | 10 | 1 | 10.0% | 4 | 16 |
| e2_00853_s43_filter_only_60m | 00853 | filter_only | 10 | 0 | 0.0% | 6 | 19 |
| e2_00853_s44_filter_only_60m | 00853 | filter_only | 10 | 1 | 10.0% | 7 | 20 |
| e2_00871_s42_filter_only_60m | 00871 | filter_only | 13 | 0 | 0.0% | 7 | 20 |
| e2_00871_s43_filter_only_60m | 00871 | filter_only | 13 | 0 | 0.0% | 2 | 16 |
| e2_00871_s44_filter_only_60m | 00871 | filter_only | 13 | 0 | 0.0% | 6 | 15 |
| e3_00871_s42_oracle_visible_60m | 00871 | oracle_visible | 13 | 2 | 15.4% | 13 | 13 |
| e3_00871_s43_oracle_visible_60m | 00871 | oracle_visible | 13 | 1 | 7.7% | 12 | 12 |
| e3_00871_s44_oracle_visible_60m | 00871 | oracle_visible | 13 | 2 | 15.4% | 17 | 17 |

Pooled rate per arm (sum of predicted over sum of could-be):

| Arm | Runs | Predicted | Could be | Rate |
|---|---|---|---|---|
| filter_only | 6 | 2 | 69 | 2.9% |
| official | 5 | 10 | 59 | 16.9% |
| oracle_visible | 3 | 5 | 39 | 12.8% |
| placebo | 6 | 6 | 69 | 8.7% |

Exact permutation test. Arm labels are swapped between runs within a scene; every relabeling is enumerated. Statistic: pooled rate of the arm minus pooled rate of placebo. Two-sided p.

| Test | Observed difference (points) | Relabelings | As extreme or more | p (two-sided) |
|---|---|---|---|---|
| official_vs_placebo | +8.3 | 200 | 25 | 0.1250 |
| filter_only_vs_placebo | -5.8 | 400 | 116 | 0.2900 |

Relabelings per scene: official_vs_placebo: 00853 10, 00871 20; filter_only_vs_placebo: 00853 20, 00871 20

## View `all_stages`: field `predicted_all_stages_typed`

| Run | Scene | Arm | Could be | Predicted | Rate | Stages with 8 members | Stages |
|---|---|---|---|---|---|---|---|
| e1_00853_s42_official_60m | 00853 | official | 10 | 2 | 20.0% | 4 | 18 |
| e1_00853_s42_placebo_60m | 00853 | placebo | 10 | 1 | 10.0% | 16 | 16 |
| e1_00853_s43_official_60m | 00853 | official | 10 | 2 | 20.0% | 11 | 21 |
| e1_00853_s43_placebo_60m | 00853 | placebo | 10 | 2 | 20.0% | 18 | 18 |
| e1_00853_s44_placebo_60m | 00853 | placebo | 10 | 0 | 0.0% | 21 | 21 |
| e1_00871_s42_official_60m | 00871 | official | 13 | 2 | 15.4% | 4 | 17 |
| e1_00871_s42_placebo_60m | 00871 | placebo | 13 | 2 | 15.4% | 15 | 15 |
| e1_00871_s43_official_60m | 00871 | official | 13 | 4 | 30.8% | 10 | 18 |
| e1_00871_s43_placebo_60m_rerun1 | 00871 | placebo | 13 | 0 | 0.0% | 12 | 12 |
| e1_00871_s44_official_60m | 00871 | official | 13 | 3 | 23.1% | 8 | 19 |
| e1_00871_s44_placebo_60m | 00871 | placebo | 13 | 1 | 7.7% | 28 | 28 |
| e2_00853_s42_filter_only_60m | 00853 | filter_only | 10 | 1 | 10.0% | 4 | 16 |
| e2_00853_s43_filter_only_60m | 00853 | filter_only | 10 | 2 | 20.0% | 6 | 19 |
| e2_00853_s44_filter_only_60m | 00853 | filter_only | 10 | 1 | 10.0% | 7 | 20 |
| e2_00871_s42_filter_only_60m | 00871 | filter_only | 13 | 3 | 23.1% | 7 | 20 |
| e2_00871_s43_filter_only_60m | 00871 | filter_only | 13 | 0 | 0.0% | 2 | 16 |
| e2_00871_s44_filter_only_60m | 00871 | filter_only | 13 | 0 | 0.0% | 6 | 15 |
| e3_00871_s42_oracle_visible_60m | 00871 | oracle_visible | 13 | 2 | 15.4% | 13 | 13 |
| e3_00871_s43_oracle_visible_60m | 00871 | oracle_visible | 13 | 1 | 7.7% | 12 | 12 |
| e3_00871_s44_oracle_visible_60m | 00871 | oracle_visible | 13 | 2 | 15.4% | 17 | 17 |

Pooled rate per arm (sum of predicted over sum of could-be):

| Arm | Runs | Predicted | Could be | Rate |
|---|---|---|---|---|
| filter_only | 6 | 7 | 69 | 10.1% |
| official | 5 | 13 | 59 | 22.0% |
| oracle_visible | 3 | 5 | 39 | 12.8% |
| placebo | 6 | 6 | 69 | 8.7% |

Exact permutation test. Arm labels are swapped between runs within a scene; every relabeling is enumerated. Statistic: pooled rate of the arm minus pooled rate of placebo. Two-sided p.

| Test | Observed difference (points) | Relabelings | As extreme or more | p (two-sided) |
|---|---|---|---|---|
| official_vs_placebo | +13.3 | 200 | 8 | 0.0400 |
| filter_only_vs_placebo | +1.4 | 400 | 400 | 1.0000 |

Relabelings per scene: official_vs_placebo: 00853 10, 00871 20; filter_only_vs_placebo: 00853 20, 00871 20

**Caution.** Official runs hold few 8-member stages (4 to 11 of 17 to 21) and filter_only runs fewer still (2 to 7 of 15 to 20); placebo runs hold all of them. The 8-member view gives those runs fewer stages in which to predict a room, so the arms do not have equal chances under that rule. Runs are the unit; seeds are not paired, as asked.
