# Pre-registration addendum: live campaign E2 (filter_only vs official), 2026-10-28

Frozen before any E2 run; sha256 in /workspace/runs/live_campaign/PREREGISTRATION_E2.sha256. Everything not stated here follows PREREGISTRATION_E1.md (metric, references, test, exclusions, spend rules).

## Question
Does the project's structural validator, applied to every completion before viewpoint scoring and routing, change how well the live robot maps objects per metre, compared with the author's unfiltered pipeline on the same model?

## Arms and cells
- filter_only: the official pipeline with each of the 8 completions reduced to its observed nodes plus the predicted nodes that pass tools/asp_offline/validator.validate_completion (the keep-set rule of tools/decision_replay.py). On 20 real 1017 completions it kept 165 of 221 predicted objects, 24 of 30 unflagged LLM rooms and 4 of 6 flagged rooms.
- official: the six E1 official runs (00853 and 00871 x seeds 42, 43, 44), reused.
Same model, pin, settings, 60 m budget and per-run cap ($1.50) as E1. The six filter_only runs run together in one wave after E1's runs; unlike E1, the two arms of a cell do not run at the same time, so host load and provider latency may differ between arms. This is stated with the result.

## Test
Same statistic and scene-blocked exact permutation as E1 (official minus filter_only, two-sided). Holm over the two contrasts E1 (official vs placebo) and E2. Same exclusions. Because E1 is a pilot under its own rule (DEVIATIONS.md item 1), E2 inherits pilot status for any joint claim; E2's own contrast does not involve the placebo code.

## Spend
Six runs at about $0.7-0.9 each; per-run cap $1.50; the runner's campaign cap is raised from $10 to $20 for this wave (DeepSeek spend so far is under $3; the key's $40 limit stays the backstop).
