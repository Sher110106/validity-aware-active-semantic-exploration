# Gemini replay: results (Gemini 4 Argon)

Model `gemini-4-argon`. Frozen scorer; `freeze.py check` passed. Pre-registration sha256 `4d7824b778ad98101e54522e8c1a3199db006510afdf04b14d202f5e2c8bf174`.

## Analysis set

- Rounds in play: [1, 2, 3]; finished: [2, 3]. Members per row: 2.
- All rows run (confirmatory and exploratory together; the 25% flag is on this total): 24 rows; 48 members: 48 ok, 0 dropped (0 parse, 0 error, 0 ok but unreadable); drop rate 0.0%.
- Confirmatory (whole rounds finished): 24 rows; 48 members: 48 ok, 0 dropped (0 parse, 0 error, 0 ok but unreadable); drop rate 0.0%; 12 clusters, 24 rows with a score.
- Exploratory (finished rows of unfinished rounds): 0 rows; 0 members: 0 ok, 0 dropped (0 parse, 0 error, 0 ok but unreadable); drop rate n/a.
- Rows not done (12): e1_00853_s42_official_st08 (no row.json); e1_00853_s43_official_st08 (no row.json); e1_00853_s44_official_st08 (no row.json); e1_00871_s42_official_st08 (no row.json); e1_00871_s43_official_st08 (no row.json); e1_00871_s44_official_st08 (no row.json); e2_00853_s42_filter_st08 (no row.json); e2_00853_s43_filter_st08 (no row.json); e2_00853_s44_filter_st08 (no row.json); e2_00871_s42_filter_st08 (no row.json); e2_00871_s43_filter_st08 (no row.json); e2_00871_s44_filter_st08 (no row.json).

## Confirmatory set

### Own scores (mean over clusters, rows with a score; comparators on the rows shared with Gemini)

| level | Gemini | B3 | B1 | B5 | D | B3L |
|---|---|---|---|---|---|---|
| L1 | 87.5% | 89.6% | 84.4% | - | - | - |
| L2 | 73.6% | 86.2% | 57.1% | - | - | - |
| L3 | 4.9% | - | - | 4.7% | 4.6% | 7.2% |

### 5a. Gemini in the author's loop against Claude in our port

| contrast | level | clusters | Gemini | other | diff (pts) | p (one-sided) | Holm p | 95% interval | found |
|---|---|---|---|---|---|---|---|---|---|
| Gemini minus Opus (reported, not tested) | L1 | 12 | 87.5% | 76.6% | +10.9 | - | - | no interval | - |
| Gemini minus Opus | L2 | 12 | 73.6% | 55.0% | +18.7 | 0.0005 | 0.0020 | 95% interval [+10.8, +26.7] points | yes |
| Gemini minus Opus | L3 | 12 | 4.9% | 3.8% | +1.1 | 0.2520 | 0.4023 | 95% interval [-2.7, +4.8] points | no |
| Gemini minus Haiku (reported, not tested) | L1 | 11 | 95.5% | 100.0% | -4.5 | - | - | no interval | - |
| Gemini minus Haiku | L2 | 12 | 73.6% | 68.3% | +5.4 | 0.0906 | 0.2717 | 95% interval [-2.8, +13.5] points | no |
| Gemini minus Haiku | L3 | 12 | 4.9% | 4.1% | +0.9 | 0.2012 | 0.4023 | 95% interval [-1.1, +2.9] points | no |
| Gemini minus deepseek (reported, not tested) | L1 | 12 | 87.5% | 87.5% | +0.0 | - | - | no interval | - |
| Gemini minus deepseek (outside family) | L2 | 12 | 73.6% | 63.5% | +10.2 | 0.0005 | - | 95% interval [+5.7, +14.7] points | - |
| Gemini minus deepseek (outside family) | L3 | 12 | 4.9% | 3.8% | +1.2 | 0.0752 | - | 95% interval [-0.5, +2.9] points | - |
| Gemini minus B1 (reported, not tested) | L1 | 12 | 87.5% | 84.4% | +3.1 | - | - | no interval | - |
| Gemini minus B1 (outside family) | L2 | 12 | 73.6% | 57.1% | +16.6 | 0.0002 | - | 95% interval [+11.3, +22.0] points | - |
| Gemini minus B1 (outside family) | L3 | 12 | 4.9% | 1.8% | +3.2 | 0.0430 | - | 95% interval [-0.3, +6.8] points | - |

### 5b. The registered rule (section 10), one level at a time, no Holm; L3 is the confirmatory hypothesis

| level | status | clusters | p (largest over comparators) | named | upper bound vs named (pts) | margin | verdict |
|---|---|---|---|---|---|---|---|
| L1 | exploratory | 12 | 1.0000 | B3 | +0.0 | 5.0 | Rejected |
| L2 | exploratory | 12 | 0.9998 | B3 | -7.3 | 5.0 | Rejected |
| L3 | confirmatory | 12 | 0.9180 | D | +2.8 | 3.0 | Rejected |

Ceiling: B3 scores about 100% at L1 and about 93% at L2, so Supported there is out of reach for most models. L3 has no such ceiling. No thesis line.

### 5c. Reported, no verdict

- Wrong-house gate L1: pairs 6, p 0.6250, no pass.
- Wrong-house gate L2: pairs 6, p 0.8125, no pass.
- Paper's room count on these replays, 1 of 2 members, untyped: 15 of 138 regions unseen at stage 0.
- Paper's room count on these replays, 1 of 2 members, typed: 3 of 138 regions unseen at stage 0.
- Paper's room count on these replays, 2 of 2 members, untyped: 11 of 138 regions unseen at stage 0.
- Paper's room count on these replays, 2 of 2 members, typed: 1 of 138 regions unseen at stage 0.
- Secondary lines, extras and validity: `results.json`.

### Wording

- 5a, some hypotheses found and some not: the four lines as they fall. Gemini 4 Argon is not the paper's model.
- Gemini 4 Argon minus Opus at L2: +18.7 points, 95% interval [+10.8, +26.7] points, Holm p 0.0020, 12 clusters; above. Gemini 4 Argon is not the paper's model.
- Gemini 4 Argon minus Opus at L3: +1.1 points, 95% interval [-2.7, +4.8] points, Holm p 0.4023, 12 clusters; not detectably above. Gemini 4 Argon is not the paper's model.
- Gemini 4 Argon minus Haiku at L2: +5.4 points, 95% interval [-2.8, +13.5] points, Holm p 0.2717, 12 clusters; not detectably above. Gemini 4 Argon is not the paper's model.
- Gemini 4 Argon minus Haiku at L3: +0.9 points, 95% interval [-1.1, +2.9] points, Holm p 0.4023, 12 clusters; not detectably above. Gemini 4 Argon is not the paper's model.
- Gemini 4 Argon did not beat a trade of region contents by the 3-point margin. Gemini 4 Argon is not the paper's model.
- Saved inputs from two homes; no robot acted on these guesses; the comparators at L1 and L2 sit at the ceiling. Gemini 4 Argon is not the paper's model.
