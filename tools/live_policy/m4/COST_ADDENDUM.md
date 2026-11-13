# Cost addendum: the smoke test, and the settings of the Claude replays

`PREREGISTRATION_SEMANTIC.md` §12 asks for the measured cost per member before round 1. This file gives it. Its sha256 is in `COST_ADDENDUM.sha256`, taken and pushed before round 1 starts.

## The smoke test (2026-11-13, 19:09 to 19:18 IST)

28 members on three inputs outside the sample frame, through `tools/llm_anthropic/claude_static.py`, with a cache pre-warm per input and 4 members at a time. Every member ended `ok`; none was refused, truncated or dropped; the served model matched the model asked for on every call. The author's `parse_response`, run on the host, parsed all 28 final texts. Total spend: $2.84 against a $30 cap.

| Setting | Input | Members | Cost per member, mean (max) | Calls per member | Tool calls per member | Prompt tokens, first call |
|---|---|---|---|---|---|---|
| Haiku 5.5, effort medium | 00069 stage 1 | 4 | $0.0047 ($0.0054) | 2.5 | 5.8 | 32,564 |
| Haiku 5.5, effort medium | 00069 stage 3 | 4 | $0.0049 ($0.0054) | 2.5 | 7.0 | 34,551 |
| Haiku 5.5, effort medium | 00871 seed 44 stage 17 | 4 | $0.0047 ($0.0056) | 2.5 | 6.0 | 51,184 |
| Opus 5.5, effort medium | 00069 stage 1 | 4 | $0.144 ($0.156) | 2.5 | 9.2 | 32,564 |
| Opus 5.5, effort medium | 00069 stage 3 | 4 | $0.143 ($0.176) | 2.0 | 9.0 | 34,551 |
| Opus 5.5, effort medium | 00871 seed 44 stage 17 | 4 | $0.157 ($0.174) | 2.8 | 8.8 | 51,184 |
| Opus 5.5, effort low | 00871 seed 44 stage 17 | 4 | $0.100 ($0.122) | 2.5 | 6.5 | 51,184 |

- Both models make several tool calls in one turn, so a member takes 2 or 3 calls, not the 8 that DeepSeek averaged in October.
- Each member's first call read the cache its input's pre-warm wrote. No Haiku prompt came near the 100,000-token price step (largest: 57,180).
- A member took 31 to 51 seconds.
- Each member proposed 4 to 10 new objects and 0 to 2 new rooms.

The smoke test was scored for cost and plumbing only. Its inputs are not in the sample frame, and nothing in it was compared with truth.

## Settings of the replays (round 1 onward)

- Models and effort: Claude Haiku 5.5 and Claude Opus 5.5, both at effort "medium"; 4 members per row; `max_tokens` 64,000; no fallback.
- Rounds: as in `semantic/sample_frame.txt`; Haiku first within a round.
- Caps, on settled spend: Opus $280, Haiku $20.
- Measured cost per member used for the check before each round: Opus $0.25, Haiku $0.01. Both sit above the largest member seen in the smoke test, to cover the pre-warm calls.
- Reserve per call in flight: Opus $1.50, Haiku $0.35.
- Projected spend for all four rounds (176 members per model, 44 pre-warms per model): about $40 for Opus and about $1.50 for Haiku.
