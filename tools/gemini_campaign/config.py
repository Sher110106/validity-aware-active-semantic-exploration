"""Immutable campaign policy and exact integer pricing."""
from __future__ import annotations

MODEL_ID = "gemini-3.8-flash"
THINKING_LEVEL = "medium"
CONTEXT_LIMIT = 1_048_576
OUTPUT_LIMIT = 65_536
INPUT_MICROUSD_PER_MILLION = 750_000
OUTPUT_MICROUSD_PER_MILLION = 3_750_000
PRICING_VERSION = "standard-2026-12-31"
USER_CAP_MICROUSD = 200_000_000
CAMPAIGN_CEILING_MICROUSD = 190_000_000
NORMAL_CEILING_MICROUSD = 180_000_000
RECOVERY_RESERVE_MICROUSD = 10_000_000
PROBE_CAP_MICROUSD = 2_000_000
PHASE_CAPS = {
    "probe": PROBE_CAP_MICROUSD,
    "engineering": 18_000_000,
    "scientific": 160_000_000,
    "recovery": RECOVERY_RESERVE_MICROUSD,
}


def cost_microdollars(input_tokens: int, generated_tokens: int) -> int:
    """Charge all prompt tokens and all generated candidate/thought tokens."""
    if not isinstance(input_tokens, int) or not isinstance(generated_tokens, int):
        raise ValueError("token counts must be integers")
    if input_tokens < 0 or generated_tokens < 0:
        raise ValueError("token counts must be non-negative")

    def ceil_div(n: int, d: int) -> int:
        return (n + d - 1) // d

    return ceil_div(input_tokens * INPUT_MICROUSD_PER_MILLION, 1_000_000) + ceil_div(
        generated_tokens * OUTPUT_MICROUSD_PER_MILLION, 1_000_000
    )
