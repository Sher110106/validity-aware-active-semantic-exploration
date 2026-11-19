# Gemini replay: results (Gemini 3.8 Flash)

Model `gemini-3.8-flash`. Frozen scorer; `freeze.py check` passed. Pre-registration sha256 `1a702c3bcec9e80c6db02031314be25710f143704e93289e0b85be28b6a5c925`.

## Analysis set

- Rounds in play: [1, 2, 3]; finished: [1, 2, 3]. Members per row: 4.
- All rows run (confirmatory and exploratory together; the 25% flag is on this total): 36 rows; 144 members: 137 ok, 7 dropped (0 parse, 7 error, 0 ok but unreadable); drop rate 4.9%.
- Confirmatory (whole rounds finished): 36 rows; 144 members: 137 ok, 7 dropped (0 parse, 7 error, 0 ok but unreadable); drop rate 4.9%; 12 clusters, 36 rows with a score.
- Exploratory (finished rows of unfinished rounds): 0 rows; 0 members: 0 ok, 0 dropped (0 parse, 0 error, 0 ok but unreadable); drop rate n/a.
- Rows not done (0): none.

## Confirmatory set

### Own scores (mean over clusters, rows with a score; comparators on the rows shared with Gemini)

| level | Gemini | B3 | B1 | B5 | D | B3L |
|---|---|---|---|---|---|---|
| L1 | 91.7% | 91.7% | 87.5% | - | - | - |
| L2 | 78.3% | 90.7% | 59.6% | - | - | - |
| L3 | 7.5% | - | - | 8.5% | 8.7% | 11.0% |

### 5a. Gemini in the author's loop against Claude in our port

| contrast | level | clusters | Gemini | other | diff (pts) | p (one-sided) | Holm p | 95% interval | found |
|---|---|---|---|---|---|---|---|---|---|
| Gemini minus Opus (reported, not tested) | L1 | 12 | 91.7% | 86.7% | +5.0 | - | - | no interval | - |
| Gemini minus Opus | L2 | 12 | 78.3% | 57.2% | +21.0 | 0.0002 | 0.0010 | 95% interval [+13.5, +28.8] points | yes |
| Gemini minus Opus | L3 | 12 | 7.5% | 4.8% | +2.7 | 0.0344 | 0.0381 | 95% interval [-0.3, +5.8] points | yes |
| Gemini minus Haiku (reported, not tested) | L1 | 12 | 100.0% | 87.5% | +12.5 | - | - | no interval | - |
| Gemini minus Haiku | L2 | 12 | 78.3% | 67.4% | +10.9 | 0.0115 | 0.0344 | 95% interval [+1.6, +20.5] points | yes |
| Gemini minus Haiku | L3 | 12 | 7.5% | 4.4% | +3.1 | 0.0190 | 0.0381 | 95% interval [+0.4, +6.0] points | yes |
| Gemini minus deepseek (reported, not tested) | L1 | 12 | 91.7% | 89.6% | +2.1 | - | - | no interval | - |
| Gemini minus deepseek (outside family) | L2 | 12 | 78.3% | 65.5% | +12.7 | 0.0002 | - | 95% interval [+9.5, +15.8] points | - |
| Gemini minus deepseek (outside family) | L3 | 12 | 7.5% | 5.1% | +2.4 | 0.0234 | - | 95% interval [+0.0, +4.8] points | - |
| Gemini minus B1 (reported, not tested) | L1 | 12 | 91.7% | 87.5% | +4.2 | - | - | no interval | - |
| Gemini minus B1 (outside family) | L2 | 12 | 78.3% | 59.6% | +18.6 | 0.0002 | - | 95% interval [+12.8, +24.4] points | - |
| Gemini minus B1 (outside family) | L3 | 12 | 7.5% | 1.8% | +5.7 | 0.0015 | - | 95% interval [+2.1, +9.4] points | - |

### 5b. The registered rule (section 10), one level at a time, no Holm; L3 is the confirmatory hypothesis

| level | status | clusters | p (largest over comparators) | named | upper bound vs named (pts) | margin | verdict |
|---|---|---|---|---|---|---|---|
| L1 | exploratory | 12 | 1.0000 | B3 | +0.0 | 5.0 | Rejected |
| L2 | exploratory | 12 | 0.9993 | B3 | -6.3 | 5.0 | Rejected |
| L3 | confirmatory | 12 | 1.0000 | D | +1.4 | 3.0 | Rejected |

Ceiling: B3 scores about 100% at L1 and about 93% at L2, so Supported there is out of reach for most models. L3 has no such ceiling. No thesis line.

### 5c. Reported, no verdict

- Wrong-house gate L1: pairs 6, p 0.0312, pass.
- Wrong-house gate L2: pairs 6, p 0.0156, pass.
- Paper's room count on these replays, 1 of 4 members, untyped: 37 of 138 regions unseen at stage 0.
- Paper's room count on these replays, 1 of 4 members, typed: 7 of 138 regions unseen at stage 0.
- Paper's room count on these replays, 2 of 4 members, untyped: 27 of 138 regions unseen at stage 0.
- Paper's room count on these replays, 2 of 4 members, typed: 5 of 138 regions unseen at stage 0.
- Secondary lines, extras and validity: `results.json`.

### Wording

- The Claude result does not carry over to Gemini 3.8 Flash: on the same inputs Gemini 3.8 Flash names more of what is there and puts more of it in fitting regions. Gemini 3.8 Flash is not the paper's model.
- Gemini 3.8 Flash minus Opus at L2: +21.0 points, 95% interval [+13.5, +28.8] points, Holm p 0.0010, 12 clusters; above. Gemini 3.8 Flash is not the paper's model.
- Gemini 3.8 Flash minus Opus at L3: +2.7 points, 95% interval [-0.3, +5.8] points, Holm p 0.0381, 12 clusters; above. Gemini 3.8 Flash is not the paper's model.
- Gemini 3.8 Flash minus Haiku at L2: +10.9 points, 95% interval [+1.6, +20.5] points, Holm p 0.0344, 12 clusters; above. Gemini 3.8 Flash is not the paper's model.
- Gemini 3.8 Flash minus Haiku at L3: +3.1 points, 95% interval [+0.4, +6.0] points, Holm p 0.0381, 12 clusters; above. Gemini 3.8 Flash is not the paper's model.
- Gemini 3.8 Flash did not beat a trade of region contents by the 3-point margin. Gemini 3.8 Flash is not the paper's model.
- Saved inputs from two homes; no robot acted on these guesses; the comparators at L1 and L2 sit at the ceiling. Gemini 3.8 Flash is not the paper's model.
