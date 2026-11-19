# Gemini replay: results (Gemini 4 Argon)

Model `gemini-4-argon`. Frozen scorer; `freeze.py check` passed. Pre-registration sha256 `66628cd363b2eaa1010be5b239fdc536568dd7bc3ee4ee814373de6b52efa73e`.

## Analysis set

- Rounds in play: [1, 2, 3]; finished: [1]. Members per row: 4.
- All rows run (confirmatory and exploratory together; the 25% flag is on this total): 12 rows; 48 members: 48 ok, 0 dropped (0 parse, 0 error, 0 ok but unreadable); drop rate 0.0%.
- Confirmatory (whole rounds finished): 12 rows; 48 members: 48 ok, 0 dropped (0 parse, 0 error, 0 ok but unreadable); drop rate 0.0%; 12 clusters, 12 rows with a score.
- Exploratory (finished rows of unfinished rounds): 0 rows; 0 members: 0 ok, 0 dropped (0 parse, 0 error, 0 ok but unreadable); drop rate n/a.
- Rows not done (24): e1_00853_s42_official_st13 (no row.json); e1_00853_s43_official_st13 (no row.json); e1_00853_s44_official_st13 (no row.json); e1_00871_s42_official_st13 (no row.json); e1_00871_s43_official_st13 (no row.json); e1_00871_s44_official_st13 (no row.json); e2_00853_s42_filter_st13 (no row.json); e2_00853_s43_filter_st13 (no row.json); e2_00853_s44_filter_st13 (no row.json); e2_00871_s42_filter_st13 (no row.json); e2_00871_s43_filter_st13 (no row.json); e2_00871_s44_filter_st13 (no row.json); e1_00853_s42_official_st03 (no row.json); e1_00853_s43_official_st03 (no row.json); e1_00853_s44_official_st03 (no row.json); e1_00871_s42_official_st03 (no row.json); e1_00871_s43_official_st03 (no row.json); e1_00871_s44_official_st03 (no row.json); e2_00853_s42_filter_st03 (no row.json); e2_00853_s43_filter_st03 (no row.json); e2_00853_s44_filter_st03 (no row.json); e2_00871_s42_filter_st03 (no row.json); e2_00871_s43_filter_st03 (no row.json); e2_00871_s44_filter_st03 (no row.json).

## Confirmatory set

### Own scores (mean over clusters, rows with a score; comparators on the rows shared with Gemini)

| level | Gemini | B3 | B1 | B5 | D | B3L |
|---|---|---|---|---|---|---|
| L1 | 99.0% | 99.0% | 93.8% | - | - | - |
| L2 | 79.3% | 96.5% | 64.7% | - | - | - |
| L3 | 6.2% | - | - | 5.7% | 6.2% | 6.6% |

### 5a. Gemini in the author's loop against Claude in our port

| contrast | level | clusters | Gemini | other | diff (pts) | p (one-sided) | Holm p | 95% interval | found |
|---|---|---|---|---|---|---|---|---|---|
| Gemini minus Opus (reported, not tested) | L1 | 12 | 99.0% | 98.6% | +0.3 | - | - | no interval | - |
| Gemini minus Opus | L2 | 12 | 79.3% | 61.8% | +17.5 | 0.0051 | 0.0205 | 95% interval [+5.0, +30.3] points | yes |
| Gemini minus Opus | L3 | 12 | 6.2% | 6.6% | -0.4 | 0.5615 | 0.6445 | 95% interval [-5.7, +4.9] points | no |
| Gemini minus Haiku (reported, not tested) | L1 | 6 | 100.0% | 66.7% | +33.3 | - | - | no interval | - |
| Gemini minus Haiku | L2 | 12 | 79.3% | 65.7% | +13.6 | 0.0356 | 0.1069 | 95% interval [-1.4, +28.5] points | no |
| Gemini minus Haiku | L3 | 12 | 6.2% | 5.0% | +1.2 | 0.3223 | 0.6445 | 95% interval [-4.4, +6.7] points | no |
| Gemini minus deepseek (reported, not tested) | L1 | 12 | 99.0% | 97.9% | +1.0 | - | - | no interval | - |
| Gemini minus deepseek (outside family) | L2 | 12 | 79.3% | 69.7% | +9.6 | 0.0071 | - | 95% interval [+2.6, +16.0] points | - |
| Gemini minus deepseek (outside family) | L3 | 12 | 6.2% | 7.7% | -1.5 | 0.7412 | - | 95% interval [-6.3, +3.2] points | - |
| Gemini minus B1 (reported, not tested) | L1 | 12 | 99.0% | 93.8% | +5.2 | - | - | no interval | - |
| Gemini minus B1 (outside family) | L2 | 12 | 79.3% | 64.7% | +14.6 | 0.0088 | - | 95% interval [+3.5, +25.8] points | - |
| Gemini minus B1 (outside family) | L3 | 12 | 6.2% | 1.7% | +4.5 | 0.0059 | - | 95% interval [+0.7, +8.5] points | - |

### 5b. The registered rule (section 10), one level at a time, no Holm; L3 is the confirmatory hypothesis

| level | status | clusters | p (largest over comparators) | named | upper bound vs named (pts) | margin | verdict |
|---|---|---|---|---|---|---|---|
| L1 | exploratory | 12 | 1.0000 | B3 | +0.0 | 5.0 | Rejected |
| L2 | exploratory | 12 | 1.0000 | B3 | -10.5 | 5.0 | Rejected |
| L3 | confirmatory | 12 | 0.6172 | D | +3.1 | 3.0 | Inconclusive |

Ceiling: B3 scores about 100% at L1 and about 93% at L2, so Supported there is out of reach for most models. L3 has no such ceiling. No thesis line.

### 5c. Reported, no verdict

- Wrong-house gate L1: pairs 6, p 0.2500, no pass.
- Wrong-house gate L2: pairs 6, p 0.7500, no pass.
- Paper's room count on these replays, 1 of 4 members, untyped: 22 of 138 regions unseen at stage 0.
- Paper's room count on these replays, 1 of 4 members, typed: 6 of 138 regions unseen at stage 0.
- Paper's room count on these replays, 2 of 4 members, untyped: 16 of 138 regions unseen at stage 0.
- Paper's room count on these replays, 2 of 4 members, typed: 6 of 138 regions unseen at stage 0.
- Secondary lines, extras and validity: `results.json`.

### Wording

- 5a, some hypotheses found and some not: the four lines as they fall. Gemini 4 Argon is not the paper's model.
- Gemini 4 Argon minus Opus at L2: +17.5 points, 95% interval [+5.0, +30.3] points, Holm p 0.0205, 12 clusters; above. Gemini 4 Argon is not the paper's model.
- Gemini 4 Argon minus Opus at L3: -0.4 points, 95% interval [-5.7, +4.9] points, Holm p 0.6445, 12 clusters; not detectably above. Gemini 4 Argon is not the paper's model.
- Gemini 4 Argon minus Haiku at L2: +13.6 points, 95% interval [-1.4, +28.5] points, Holm p 0.1069, 12 clusters; not detectably above. Gemini 4 Argon is not the paper's model.
- Gemini 4 Argon minus Haiku at L3: +1.2 points, 95% interval [-4.4, +6.7] points, Holm p 0.6445, 12 clusters; not detectably above. Gemini 4 Argon is not the paper's model.
- 5b at L3: Inconclusive, Gemini 4 Argon minus D +0.0 points, 95% interval [-2.8, +3.1] points. Gemini 4 Argon is not the paper's model.
- Saved inputs from two homes; no robot acted on these guesses; the comparators at L1 and L2 sit at the ceiling. Gemini 4 Argon is not the paper's model.
