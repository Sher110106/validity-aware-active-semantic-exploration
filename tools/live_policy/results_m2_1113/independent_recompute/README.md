# Independent recompute of M2's summary

An Opus reviewer wrote `recompute.py` from the text of `PREREGISTRATION_M2.md` (§3, §5, §6) and item 54 of `DEVIATIONS_NOVEMBER.md`, without opening `m2/summarise_factorial.py`, `m2/passcheck.py`, `m2/factorial.py` or the tests. It reads the two per-stage files and rebuilds every figure of the summary. `compare.py` sets its output (`mine.json`) beside the filed `pass2/summary_factorial.json`; `notes_check.py` checks the statements of `NOTES.md`.

- Every mean, every interval end and every verdict matches the filed summary; the largest difference is 1.4e-16. That covers the main view, `ig` alone, the audit's U_cone, U_360, and the official-arm stages alone.
- The verdicts rest on the interval of X − 0.5·A, as §6 asks. Every arm reads "not shown sufficient" on every view, but for one: on U_360, room types alone (C) read "inconclusive" (C − 0.5·A = +0.035, −0.004 to +0.074).
- `ig` is 0 for every candidate on 2 of 384 stages for F0 (and for F6), so that does not explain why F0 sits near F5.
- With another random stream from the same seed, the interval ends move by up to 0.0007; no verdict moves.

What the recompute covers: the step from per-stage, per-candidate scores and yardsticks to the summary. What it does not cover: how each arm's graphs were built and scored on the bench. That step was checked by code review and by the bench reproducing its registered 9,600 picks. The runs clustered by scene and seed were not rechecked.

Choices the checker had to make, all matching the filed code: scipy's `spearmanr` with average ranks, undefined when either input is constant; Rademacher weights from `default_rng(20261113).choice([-1, 1], (9999, 24))`; under `ig` alone, the 2 stages where F6's `ig` is constant are dropped for every arm.

To rerun: `python recompute.py && python compare.py`. Both per-stage files must be present (`pass1/` and `pass2/factorial_stages.jsonl`; they are not committed, see `../NOTES.md` for their hashes).
