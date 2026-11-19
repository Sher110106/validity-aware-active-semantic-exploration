# Gemini replay: results (Gemini 4 Neon)

Model `gemini-4-neon`. Frozen scorer; `freeze.py check` passed. Pre-registration sha256 `ce6be9d661c4d54abe8b32d59b83788f1641cb819c424694e01bee63cc3b0d70`.

## Analysis set

- Rounds in play: [1, 2, 3]; finished: [1, 3]. Members per row: 2.
- All rows run (confirmatory and exploratory together; the 25% flag is on this total): 24 rows; 48 members: 48 ok, 0 dropped (0 parse, 0 error, 0 ok but unreadable); drop rate 0.0%.
- Confirmatory (whole rounds finished): 24 rows; 48 members: 48 ok, 0 dropped (0 parse, 0 error, 0 ok but unreadable); drop rate 0.0%; 12 clusters, 24 rows with a score.
- Exploratory (finished rows of unfinished rounds): 0 rows; 0 members: 0 ok, 0 dropped (0 parse, 0 error, 0 ok but unreadable); drop rate n/a.
- Rows not done (12): e1_00853_s42_official_st13 (no row.json); e1_00853_s43_official_st13 (no row.json); e1_00853_s44_official_st13 (no row.json); e1_00871_s42_official_st13 (no row.json); e1_00871_s43_official_st13 (no row.json); e1_00871_s44_official_st13 (no row.json); e2_00853_s42_filter_st13 (no row.json); e2_00853_s43_filter_st13 (no row.json); e2_00853_s44_filter_st13 (no row.json); e2_00871_s42_filter_st13 (no row.json); e2_00871_s43_filter_st13 (no row.json); e2_00871_s44_filter_st13 (no row.json).

## Confirmatory set

### Own scores (mean over clusters, rows with a score; comparators on the rows shared with Gemini)

| level | Gemini | B3 | B1 | B5 | D | B3L |
|---|---|---|---|---|---|---|
| L1 | 94.1% | 95.1% | 95.3% | - | - | - |
| L2 | 74.3% | 92.5% | 67.3% | - | - | - |
| L3 | 8.7% | - | - | 7.6% | 5.7% | 10.2% |

### 5a. Gemini in the author's loop against Claude in our port

| contrast | level | clusters | Gemini | other | diff (pts) | p (one-sided) | Holm p | 95% interval | found |
|---|---|---|---|---|---|---|---|---|---|
| Gemini minus Opus (reported, not tested) | L1 | 12 | 94.1% | 92.5% | +1.6 | - | - | no interval | - |
| Gemini minus Opus | L2 | 12 | 74.3% | 65.7% | +8.5 | 0.0396 | 0.1582 | 95% interval [-1.1, +18.0] points | no |
| Gemini minus Opus | L3 | 12 | 8.7% | 5.4% | +3.3 | 0.1006 | 0.2012 | 95% interval [-1.4, +8.6] points | no |
| Gemini minus Haiku (reported, not tested) | L1 | 12 | 92.4% | 91.7% | +0.7 | - | - | no interval | - |
| Gemini minus Haiku | L2 | 12 | 74.3% | 73.7% | +0.6 | 0.4590 | 0.4590 | 95% interval [-10.0, +12.0] points | no |
| Gemini minus Haiku | L3 | 12 | 8.7% | 4.7% | +4.0 | 0.0410 | 0.1582 | 95% interval [-0.4, +8.5] points | no |
| Gemini minus deepseek (reported, not tested) | L1 | 12 | 94.1% | 99.0% | -4.9 | - | - | no interval | - |
| Gemini minus deepseek (outside family) | L2 | 12 | 74.3% | 71.2% | +3.1 | 0.0273 | - | 95% interval [-0.1, +6.3] points | - |
| Gemini minus deepseek (outside family) | L3 | 12 | 8.7% | 5.5% | +3.2 | 0.1245 | - | 95% interval [-2.3, +8.9] points | - |
| Gemini minus B1 (reported, not tested) | L1 | 12 | 94.1% | 95.3% | -1.2 | - | - | no interval | - |
| Gemini minus B1 (outside family) | L2 | 12 | 74.3% | 67.3% | +6.9 | 0.0325 | - | 95% interval [-0.5, +14.3] points | - |
| Gemini minus B1 (outside family) | L3 | 12 | 8.7% | 2.5% | +6.2 | 0.0205 | - | 95% interval [+0.2, +12.5] points | - |

### 5b. The registered rule (section 10), one level at a time, no Holm; L3 is the confirmatory hypothesis

| level | status | clusters | p (largest over comparators) | named | upper bound vs named (pts) | margin | verdict |
|---|---|---|---|---|---|---|---|
| L1 | exploratory | 12 | 1.0000 | B3 | +0.0 | 5.0 | Rejected |
| L2 | exploratory | 12 | 1.0000 | B3 | -15.4 | 5.0 | Rejected |
| L3 | confirmatory | 12 | 0.8806 | D | +6.3 | 3.0 | Inconclusive |

Ceiling: B3 scores about 100% at L1 and about 93% at L2, so Supported there is out of reach for most models. L3 has no such ceiling. No thesis line.

### 5c. Reported, no verdict

- Wrong-house gate L1: pairs 6, p 0.0625, no pass.
- Wrong-house gate L2: pairs 6, p 0.0156, pass.
- Paper's room count on these replays, 1 of 2 members, untyped: 36 of 138 regions unseen at stage 0.
- Paper's room count on these replays, 1 of 2 members, typed: 11 of 138 regions unseen at stage 0.
- Paper's room count on these replays, 2 of 2 members, untyped: 25 of 138 regions unseen at stage 0.
- Paper's room count on these replays, 2 of 2 members, typed: 7 of 138 regions unseen at stage 0.
- Secondary lines, extras and validity: `results.json`.

### Wording

- On the same inputs Gemini 4 Neon, in the author's loop, was not detectably above Claude. Gemini 4 Neon is not the paper's model.
- Gemini 4 Neon minus Opus at L2: +8.5 points, 95% interval [-1.1, +18.0] points, Holm p 0.1582, 12 clusters; not detectably above. Gemini 4 Neon is not the paper's model.
- Gemini 4 Neon minus Opus at L3: +3.3 points, 95% interval [-1.4, +8.6] points, Holm p 0.2012, 12 clusters; not detectably above. Gemini 4 Neon is not the paper's model.
- Gemini 4 Neon minus Haiku at L2: +0.6 points, 95% interval [-10.0, +12.0] points, Holm p 0.4590, 12 clusters; not detectably above. Gemini 4 Neon is not the paper's model.
- Gemini 4 Neon minus Haiku at L3: +4.0 points, 95% interval [-0.4, +8.5] points, Holm p 0.1582, 12 clusters; not detectably above. Gemini 4 Neon is not the paper's model.
- 5b at L3: Inconclusive, Gemini 4 Neon minus D +2.9 points, 95% interval [-0.4, +6.3] points. Gemini 4 Neon is not the paper's model.
- Saved inputs from two homes; no robot acted on these guesses; the comparators at L1 and L2 sit at the ceiling. Gemini 4 Neon is not the paper's model.
