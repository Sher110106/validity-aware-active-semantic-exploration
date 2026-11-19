> **Exploratory.** Written 2026-11-19 after every result was seen. No verdict rests on it. See `DEVIATIONS_NOVEMBER.md`.

# Readout 1: what each comparator itself scores

Each comparator's own score and the model's, on the registered analysis rows (rounds [1, 2, 3, 4]), built as section 8 says: member, then row, then cluster means, on the rows where both have a score. Scores are in %. "Max gain" is what a model that scores 1.0 in every member could show over the comparator (100 minus the comparator's score). Every model-minus-comparator mean was checked against `claude/results.json` and matches.

| Model | Level | Comparator | Rows | Clusters | Model score | Comparator score | Diff (points) | Rows comparator = 1.0 | Clusters comparator = 1.0 | Max gain |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | L1 | B3 | 41 | 12 | 85.4% | 91.2% | -5.8 | 37 | 9 | 8.8% |
| claude-opus-5-5 | L1 | B1 | 41 | 12 | 85.4% | 87.5% | -2.1 | 31 | 5 | 12.5% |
| claude-opus-5-5 | L2 | B3 | 44 | 12 | 58.3% | 93.4% | -35.1 | 37 | 5 | 6.6% |
| claude-opus-5-5 | L2 | B1 | 44 | 12 | 58.3% | 60.6% | -2.3 | 0 | 0 | 39.4% |
| claude-opus-5-5 | L3 | B5 | 44 | 12 | 4.2% | 4.4% | -0.2 | 0 | 0 | 95.6% |
| claude-opus-5-5 | L3 | D | 43 | 12 | 4.3% | 3.7% | +0.5 | 0 | 0 | 96.3% |
| claude-opus-5-5 | L3 | B3L | 44 | 12 | 4.2% | 10.5% | -6.3 | 0 | 0 | 89.5% |
| claude-haiku-5-5 | L1 | B3 | 24 | 12 | 89.6% | 100.0% | -10.4 | 24 | 12 | 0.0% |
| claude-haiku-5-5 | L1 | B1 | 24 | 12 | 89.6% | 94.8% | -5.2 | 19 | 7 | 5.2% |
| claude-haiku-5-5 | L2 | B3 | 44 | 12 | 68.8% | 93.7% | -24.9 | 39 | 7 | 6.3% |
| claude-haiku-5-5 | L2 | B1 | 44 | 12 | 68.8% | 60.6% | +8.2 | 0 | 0 | 39.4% |
| claude-haiku-5-5 | L3 | B5 | 44 | 12 | 4.4% | 4.9% | -0.5 | 0 | 0 | 95.1% |
| claude-haiku-5-5 | L3 | D | 43 | 12 | 4.4% | 3.6% | +0.8 | 0 | 0 | 96.4% |
| claude-haiku-5-5 | L3 | B3L | 44 | 12 | 4.4% | 10.2% | -5.8 | 0 | 0 | 89.8% |

## Best p a perfect model could get against B3

A model with 1.0 in every member, on the clusters of each B3 contrast. The one-sided exact sign-flip test (`semantic/stats.py`) on d = 1 minus the comparator's cluster score. This is the smallest p the test could have returned. Holm for six tests assumes that test ranks first and the other five have p = 1, so it is min(1, 6p). The registered p is the saved one for the model's real score.

| Model | Level | Clusters | Clusters with d = 0 | Smallest p | After Holm (6) | Could pass 0.05 | Saved p (real model) |
|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | L1 | 12 | 9 | 0.125 | 0.75 | no | 1 |
| claude-opus-5-5 | L2 | 12 | 5 | 0.0078125 | 0.046875 | yes | 1 |
| claude-haiku-5-5 | L1 | 12 | 12 | 1 | 1 | no | 1 |
| claude-haiku-5-5 | L2 | 12 | 7 | 0.03125 | 0.1875 | no | 1 |

Clusters with d = 0 are those where B3 itself scores 1.0. They stay in the test and raise the smallest p to 2^z / 2^n.
