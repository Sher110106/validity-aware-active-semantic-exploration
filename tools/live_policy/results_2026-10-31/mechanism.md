## Precision of new hypothesis objects against the human labels (counted runs; counts are (stage, member) instances, runs are the independent unit)

| arm | scene | part | new objects | within 0.5 m (hits) | within 1 m (hits) | within 2 m (hits) | per-run range at 0.5 m |
|---|---|---|---|---|---|---|---|
| Filter | 00853 | final | 3019 | 2.45% (74) | 8.74% (264) | 20.83% (629) | 2.02-3.11% |
| Filter | 00853 | raw | 4434 | 2.26% (100) | 8.30% (368) | 19.58% (868) |  |
| Filter | 00853 | removed | 1415 | 1.84% (26) | 7.35% (104) | 16.96% (240) |  |
| Filter | 00871 | final | 2879 | 3.68% (106) | 12.61% (363) | 27.34% (787) | 2.04-4.93% |
| Filter | 00871 | raw | 4031 | 3.35% (135) | 10.99% (443) | 25.60% (1032) |  |
| Filter | 00871 | removed | 1158 | 2.59% (30) | 7.43% (86) | 20.98% (243) |  |
| Official (DeepSeek) | 00853 | final | 3099 | 1.39% (43) | 6.29% (195) | 16.13% (500) | 1.37-1.41% |
| Official (DeepSeek) | 00871 | final | 4565 | 4.16% (190) | 12.64% (577) | 29.05% (1326) | 3.14-4.80% |
| Oracle | 00871 | final | 3313 | 100.00% (3313) | 100.00% (3313) | 100.00% (3313) | 100.00-100.00% |
| Placebo | 00853 | final | 4178 | 0.62% (26) | 2.42% (101) | 7.11% (297) | 0.43-0.84% |
| Placebo | 00871 | final | 3962 | 0.40% (16) | 1.62% (64) | 5.40% (214) | 0.34-0.56% |

## Later found (D3, descriptive): share of each run's unique hypotheses found later in the final map (later_found.json, counted runs)

| arm | scene | runs | unique hypotheses | found | share (pooled) | per-run range |
|---|---|---|---|---|---|---|
| Filter | 00853 | 3 | 2258 | 13 | 0.58% | 0.24-0.83% |
| Filter | 00871 | 3 | 2018 | 10 | 0.50% | 0.35-0.67% |
| Official (DeepSeek) | 00853 | 2 | 2084 | 10 | 0.48% | 0.46-0.50% |
| Official (DeepSeek) | 00871 | 3 | 3134 | 28 | 0.89% | 0.31-1.75% |
| Oracle | 00871 | 3 | 625 | 109 | 17.44% | 12.08-21.30% |
| Placebo | 00853 | 3 | 3693 | 4 | 0.11% | 0.00-0.29% |
| Placebo | 00871 | 3 | 3475 | 7 | 0.20% | 0.10-0.28% |

## Base mapping rate and scanned share (stage_diagnostics.json)

| run | arm | base rate k+1 | base rate k+2 | share of new hypotheses in scanned space |
|---|---|---|---|---|
| e1_00853_s42_official_60m | official | 0.123 | 0.161 | 0.637 |
| e1_00853_s42_placebo_60m | placebo | 0.101 | 0.121 | 0.673 |
| e1_00853_s43_official_60m | official | 0.099 | 0.130 | 0.641 |
| e1_00853_s43_placebo_60m | placebo | 0.111 | 0.143 | 0.655 |
| e1_00853_s44_official_60m | official | 0.081 | 0.097 | 0.710 |
| e1_00853_s44_official_60m_rerun1 | official | 0.103 | 0.133 | 0.734 |
| e1_00853_s44_placebo_60m | placebo | 0.095 | 0.109 | 0.672 |
| e1_00871_s42_official_60m | official | 0.052 | 0.071 | 0.633 |
| e1_00871_s42_placebo_60m | placebo | 0.068 | 0.085 | 0.568 |
| e1_00871_s43_official_60m | official | 0.055 | 0.084 | 0.653 |
| e1_00871_s43_placebo_60m | placebo | 0.096 |  |  |
| e1_00871_s43_placebo_60m_rerun1 | placebo | 0.072 | 0.076 | 0.626 |
| e1_00871_s44_official_60m | official | 0.063 | 0.086 | 0.677 |
| e1_00871_s44_placebo_60m | placebo | 0.065 | 0.084 | 0.761 |
| e2_00853_s42_filter_only_60m | filter_only | 0.126 | 0.150 | 0.645 |
| e2_00853_s43_filter_only_60m | filter_only | 0.109 | 0.130 | 0.703 |
| e2_00853_s44_filter_only_60m | filter_only | 0.121 | 0.164 | 0.722 |
| e2_00871_s42_filter_only_60m | filter_only | 0.066 | 0.088 | 0.680 |
| e2_00871_s43_filter_only_60m | filter_only | 0.053 | 0.057 | 0.746 |
| e2_00871_s44_filter_only_60m | filter_only | 0.043 | 0.053 | 0.769 |
| e3_00853_s42_oracle_visible_60m_rerun1 | oracle_visible | 0.132 | 0.187 | 0.596 |
| e3_00853_s43_oracle_visible_60m | oracle_visible | 0.136 | 0.173 | 0.657 |
| e3_00871_s42_oracle_visible_60m | oracle_visible | 0.054 | 0.067 | 0.527 |
| e3_00871_s43_oracle_visible_60m | oracle_visible | 0.084 | 0.113 | 0.636 |
| e3_00871_s44_oracle_visible_60m | oracle_visible | 0.082 | 0.101 | 0.620 |

## E3 gate: drawn vs undrawn eligible candidates (one-sided permutation p within stage and track)

Source: registered single-run gate files (E3_gate_*.json, seed 0).

| run | source | subset | approach gap | p | mapping gap (k+1) | p | k+2 gap | drawn / undrawn rows | later found (unique drawn) |
|---|---|---|---|---|---|---|---|---|---|
| e3_00853_s42_oracle_visible_60m | E3_gate_00853_s42.json | all | +0.035 | 0.065 | +0.004 | 0.291 | +0.015 | 945 / 1386 | 161 (0.236) |
| e3_00853_s42_oracle_visible_60m | E3_gate_00853_s42.json | scanned | +0.069 | 0.021 | -0.000 | 0.453 | +0.015 | 547 / 857 | 161 (0.236) |
| e3_00853_s42_oracle_visible_60m | E3_gate_00853_s42.json | unscanned | -0.026 | 0.559 | +0.009 | 0.297 | +0.010 | 398 / 529 | 161 (0.236) |
| e3_00853_s42_oracle_visible_60m_rerun1 | E3_gate_00853_s42_rerun1.json | all | +0.027 | 0.369 | -0.007 | 0.727 | -0.009 | 1071 / 1596 | 160 (0.300) |
| e3_00853_s42_oracle_visible_60m_rerun1 | E3_gate_00853_s42_rerun1.json | scanned | +0.034 | 0.375 | +0.008 | 0.434 | +0.005 | 615 / 941 | 160 (0.300) |
| e3_00853_s42_oracle_visible_60m_rerun1 | E3_gate_00853_s42_rerun1.json | unscanned | +0.015 | 0.559 | -0.026 | 0.938 | -0.030 | 456 / 655 | 160 (0.300) |
| e3_00853_s43_oracle_visible_60m | E3_gate_00853_s43.json | all | +0.031 | 0.216 | -0.011 | 0.847 | -0.002 | 1040 / 1465 | 163 (0.325) |
| e3_00853_s43_oracle_visible_60m | E3_gate_00853_s43.json | scanned | +0.039 | 0.386 | -0.004 | 0.691 | +0.007 | 637 / 919 | 163 (0.325) |
| e3_00853_s43_oracle_visible_60m | E3_gate_00853_s43.json | unscanned | +0.014 | 0.138 | -0.023 | 0.772 | -0.018 | 403 / 546 | 163 (0.325) |
| e3_00871_s42_oracle_visible_60m | E3_gate_00871_s42.json | all | +0.036 | 0.039 | +0.003 | 0.544 | +0.001 | 890 / 2515 | 207 (0.121) |
| e3_00871_s42_oracle_visible_60m | E3_gate_00871_s42.json | scanned | +0.028 | 0.032 | +0.010 | 0.154 | +0.005 | 441 / 1335 | 207 (0.121) |
| e3_00871_s42_oracle_visible_60m | E3_gate_00871_s42.json | unscanned | +0.042 | 0.094 | -0.005 | 0.888 | -0.003 | 449 / 1180 | 207 (0.121) |
| e3_00871_s43_oracle_visible_60m | E3_gate_00871_s43.json | all | +0.050 | 0.067 | -0.000 | 0.490 | +0.002 | 740 / 1799 | 196 (0.189) |
| e3_00871_s43_oracle_visible_60m | E3_gate_00871_s43.json | scanned | +0.058 | 0.069 | -0.003 | 0.666 | +0.009 | 433 / 1093 | 196 (0.189) |
| e3_00871_s43_oracle_visible_60m | E3_gate_00871_s43.json | unscanned | +0.030 | 0.270 | +0.002 | 0.244 | -0.013 | 307 / 706 | 196 (0.189) |
| e3_00871_s44_oracle_visible_60m | E3_gate_00871_s44.json | all | +0.005 | 0.444 | +0.010 | 0.230 | +0.012 | 1091 / 2944 | 216 (0.213) |
| e3_00871_s44_oracle_visible_60m | E3_gate_00871_s44.json | scanned | -0.007 | 0.541 | +0.008 | 0.378 | +0.008 | 623 / 1836 | 216 (0.213) |
| e3_00871_s44_oracle_visible_60m | E3_gate_00871_s44.json | unscanned | +0.024 | 0.183 | +0.016 | 0.134 | +0.019 | 468 / 1108 | 216 (0.213) |
