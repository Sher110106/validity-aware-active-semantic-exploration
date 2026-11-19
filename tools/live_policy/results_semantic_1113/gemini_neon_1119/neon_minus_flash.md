> **Exploratory.** Computed after both results were seen. No verdict rests on it. See `PREREGISTRATION_GEMINI.md`, Note 3.

# gemini-4-neon minus gemini-3.8-flash, on the rows both ran

Both ran the author's own loop. Exact sign-flip test over clusters, two-sided; 95% interval from the same test.

| level | clusters | rows | gemini-4-neon | gemini-3.8-flash | diff (pts) | p (two-sided) | 95% interval (pts) |
|---|---|---|---|---|---|---|---|
| L1 | 12 | 24 | 94.1% | 98.4% | -4.3 | 0.2500 | [-9.4, +0.4] |
| L2 | 12 | 24 | 74.3% | 84.4% | -10.1 | 0.0005 | [-13.1, -7.3] |
| L3 | 12 | 24 | 8.7% | 7.2% | +1.5 | 0.3818 | [-1.5, +5.0] |
