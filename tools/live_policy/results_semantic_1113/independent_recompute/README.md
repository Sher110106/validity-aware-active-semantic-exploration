# Independent recompute of the semantic scores

An Opus reviewer wrote `recompute.py` from the text of `PREREGISTRATION_SEMANTIC.md` alone, without opening the scorer's code, and ran it on the raw files. `compare.py` sets its output beside the scorer's.

- DeepSeek, Claude Opus 5.5 and Claude Haiku 5.5: every count of claims, items and hits matches the scorer; the differences against the other-house prior, the placebo and the prior's labels at the model's places match to the last digit; the p-values match exactly. The two randomised controls (the region trade D and the swap B5) match within the noise of their draws.
- The six verdicts and the thesis line match.
- `margin_summary.json`: the one close verdict, Opus at L3 against D. The checker reran D with ten other seeds at the registered 200 draws and five at 5,000 draws. The interval's upper end ran from 0.0283 to 0.0298, below the 0.03 margin in all fifteen runs, and settled near 0.029 with many draws. The scorer's registered figure is 0.0295.

`out_<model>.json` holds the checker's per-row and per-member output.
