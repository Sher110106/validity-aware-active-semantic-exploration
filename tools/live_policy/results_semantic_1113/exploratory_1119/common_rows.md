> **Exploratory.** Written 2026-11-19 after every result was seen. No verdict rests on it. See `DEVIATIONS_NOVEMBER.md`.

# Readout 2: every source on the rows that hold Gemini guesses

Rows: the 8 rows where gemini has members (round(s) [4]). Per level, only rows where all five sources have a row score count. A row score is the mean over a source's members that have a score (section 8). The mean below is over those rows, each row once. B3 is the other-house prior paired with Gemini's own members on those rows.

| Level | Rows | gemini | claude-opus-5-5 | claude-haiku-5-5 | deepseek | placebo | B3 (Gemini's members) | Gemini members | Clusters |
|---|---|---|---|---|---|---|---|---|---|
| L1 | 5 | 100.0% | 100.0% | 100.0% | 95.0% | 100.0% | 100.0% | 18 | 3 |
| L2 | 8 | 91.3% | 69.6% | 70.5% | 73.9% | 65.4% | 98.8% | 29 | 3 |
| L3 | 8 | 13.8% | 5.6% | 7.8% | 7.6% | 2.3% | n/a | 29 | 3 |

Rows where gemini is above each other source (above / tie / below):

| Level | claude-opus-5-5 | claude-haiku-5-5 | deepseek | placebo |
|---|---|---|---|---|
| L1 | 0 / 5 / 0 | 0 / 5 / 0 | 1 / 4 / 0 | 0 / 5 / 0 |
| L2 | 7 / 0 / 1 | 6 / 0 / 2 | 8 / 0 / 0 | 8 / 0 / 0 |
| L3 | 5 / 3 / 0 | 4 / 2 / 2 | 5 / 2 / 1 | 5 / 3 / 0 |

Rows used:
- L1: fa1_00853_s42_official_st04, fa1_00853_s43_official_st02, fa1_00853_s43_official_st05, fa1_00871_s42_official_st05, fa1_00871_s42_official_st06
- L2: fa1_00853_s42_official_st04, fa1_00853_s43_official_st01, fa1_00853_s43_official_st02, fa1_00853_s43_official_st05, fa1_00871_s42_official_st02, fa1_00871_s42_official_st03, fa1_00871_s42_official_st05, fa1_00871_s42_official_st06
- L3: fa1_00853_s42_official_st04, fa1_00853_s43_official_st01, fa1_00853_s43_official_st02, fa1_00853_s43_official_st05, fa1_00871_s42_official_st02, fa1_00871_s42_official_st03, fa1_00871_s42_official_st05, fa1_00871_s42_official_st06
