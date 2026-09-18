"""Immutable, explicitly validated prospective campaign contract."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

MODEL: Final = "gemini-3.8-flash"
THINKING_LEVEL: Final = "medium"
BASELINE: Final = "official_asp"
EXPERIMENTAL: Final = "validator_plus_unanimity_raw_tau_1_0"
SCENES: Final = ("00069", "00573", "00853")
SEEDS: Final = (42, 43, 44)
HORIZON_M: Final = (120, 75, 50, 25)
USER_CAP_MICROUSD: Final = 200_000_000
BROKER_CEILING_MICROUSD: Final = 190_000_000
NORMAL_CEILING_MICROUSD: Final = 180_000_000
RECOVERY_CEILING_MICROUSD: Final = 10_000_000
PHASE_CAPS_MICROUSD: Final = {
    "capability_probe": 2_000_000,
    "engineering_pilot": 18_000_000,
    "scientific_normal": 160_000_000,
    "recovery": RECOVERY_CEILING_MICROUSD,
    "absolute": BROKER_CEILING_MICROUSD,
}
# Authoritative DeepSeek 120m prior, repriced at Gemini standard rates, no thinking tokens.
PRIOR_120M_ONE_POLICY_MICROUSD: Final = {"00069": 62_520_000, "00573": 71_490_000, "00853": 60_460_000}
PRIOR_25M_ONE_POLICY_MICROUSD: Final = {"00069": 11_693_000, "00573": 8_729_900, "00853": 11_987_800}
PILOT_PAIR_PRIOR_MICROUSD: Final = 1_540_000
HISTORICAL_PRIOR_BLOCK_MICROUSD: Final = {25: 64_820_000, 50: 117_620_000,
                                          75: 243_075_000, 120: 388_920_000}


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class PolicySpec:
    name: str
    description: str


POLICIES: Final = (
    PolicySpec(BASELINE, "official ASP"),
    PolicySpec(EXPERIMENTAL, "validated completions plus raw-support unanimity; observed map preserved"),
)


def validate_contract() -> None:
    if MODEL != "gemini-3.8-flash" or THINKING_LEVEL != "medium":
        raise ContractError("model or reasoning contract changed")
    if BROKER_CEILING_MICROUSD != NORMAL_CEILING_MICROUSD + RECOVERY_CEILING_MICROUSD:
        raise ContractError("budget ledger caps inconsistent")
    if USER_CAP_MICROUSD <= BROKER_CEILING_MICROUSD:
        raise ContractError("user margin missing")
    if tuple(SCENES) != ("00069", "00573", "00853") or tuple(SEEDS) != (42, 43, 44):
        raise ContractError("scene/seed contract changed")


def phase_cost_allowed(phase: str, amount_micro_usd: int) -> bool:
    if type(amount_micro_usd) is not int or amount_micro_usd < 0:
        return False
    return amount_micro_usd <= PHASE_CAPS_MICROUSD.get(phase, -1) and amount_micro_usd <= BROKER_CEILING_MICROUSD
