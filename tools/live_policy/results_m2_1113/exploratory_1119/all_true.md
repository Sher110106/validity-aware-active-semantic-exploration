> **Exploratory.** Written 2026-11-19 after every result was seen. No verdict rests on it. See `DEVIATIONS_NOVEMBER.md`.

# Readout 4: why the all-true arm does not gain

**Layout read.** One line per stage in `factorial_stages.jsonl`: `arms[<arm>]['ig']` is a list of 300 values, one per first-stage candidate. Arms: F1 oracle graphs, F5a/F5b placebo sets, F6 no guesses (the no-guess arm), F0 the all-true anchor, F-room, F3-deepseek/-haiku/-opus. `ig` is the members' disagreement about a candidate, read in bits as the brief does. The cap tested is 2.0.

**Files.** pass 1: `tools/live_policy/results_m2_1113/pass1/factorial_stages.jsonl`; pass 2: `tools/live_policy/results_m2_1113/pass2/factorial_stages.jsonl`. Pass 2's file holds only F3-haiku and F3-opus; F0 and F6 are in pass 1's, so both files were read (merged by run and stage, as `summarise_factorial.load_rows` does).

| Arm | Stages | Largest ig (bits) | Where | Values above 2.0 |
|---|---|---|---|---|
| F1 | 384 | 5.2500 | e1_00871_s43_placebo_60m_rerun1 stage 4 cand 44 | 32947 |
| F5a | 384 | 5.3585 | e1_00871_s43_official_60m stage 2 cand 16 | 44825 |
| F5b | 384 | 5.5000 | e1_00871_s43_official_60m stage 1 cand 53 | 44505 |
| F6 | 384 | 2.0000 | e1_00853_s42_official_60m stage 6 cand 191 | 0 |
| F0 | 384 | 2.0000 | e1_00853_s42_official_60m stage 6 cand 281 | 0 |
| F3-deepseek | 384 | 4.7500 | e2_00853_s43_filter_only_60m stage 7 cand 132 | 18977 |
| F-room | 384 | 5.1556 | e3_00853_s42_oracle_visible_60m_rerun1 stage 5 cand 211 | 13400 |
| F3-haiku | 384 | 4.8366 | e1_00853_s44_official_60m stage 1 cand 111 | 20743 |
| F3-opus | 384 | 5.0589 | e3_00853_s42_oracle_visible_60m_rerun1 stage 4 cand 1 | 16783 |

- F0 exceeds 2.0 bits: **no**; F6 exceeds it: **no**. Largest F0: 2.0000; largest F6: 2.0000.
- Spearman correlation of F0's `ig` with F6's `ig` across the candidates of a stage, mean over stages: **+0.6350** (median +0.6760) on **382** stages. 2 of 384 stages have no defined correlation (a constant `ig` in one arm, as in `_rho_copy`) and are left out.
