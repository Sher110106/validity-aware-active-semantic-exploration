"""The preregistered prospective paired-policy contract."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

MODEL: Final = "gemini-3.8-flash"
THINKING_LEVEL: Final = "medium"
BASELINE: Final = "official_asp"
EXPERIMENTAL: Final = "validator_plus_unanimity_raw_tau_1_0"
HORIZONS: Final = (120, 75, 50, 25)
SCENES: Final = ("00069", "00573", "00853")
SEEDS: Final = (42, 43, 44)
BROKER_CEILING: Final = 190.0
NORMAL_CEILING: Final = 180.0
RECOVERY_CEILING: Final = 10.0
USER_CAP: Final = 200.0
PHASE_CAPS: Final = {
    "capability_probe": 2.0,
    "engineering_pilot": 18.0,
    "scientific_normal": 160.0,
    "recovery": RECOVERY_CEILING,
    "absolute": BROKER_CEILING,
}


@dataclass(frozen=True)
class PolicySpec:
    name: str
    description: str


POLICIES: Final = (
    PolicySpec(BASELINE, "official ASP"),
    PolicySpec(
        EXPERIMENTAL,
        "validated completions plus raw-support unanimity; observed map preserved",
    ),
)


@dataclass(frozen=True)
class RunKey:
    scene: str
    seed: int
    policy: str
    order: str
    horizon_minutes: int
    attempt: int = 1

    @property
    def path(self) -> str:
        return (
            f"runs/prospective_gemini/{self.campaign}/{self.scene}/{self.seed}/"
            f"{self.policy}/{self.attempt}/"
        )

    @property
    def campaign(self) -> str:
        return "paired_v5"


def validate_contract() -> None:
    assert MODEL == "gemini-3.8-flash"
    assert THINKING_LEVEL == "medium"
    assert BASELINE != EXPERIMENTAL
    assert BROKER_CEILING == NORMAL_CEILING + RECOVERY_CEILING
    assert USER_CAP > BROKER_CEILING
    assert PHASE_CAPS["capability_probe"] == 2.0
    assert PHASE_CAPS["engineering_pilot"] == 18.0
    assert PHASE_CAPS["scientific_normal"] == 160.0


def phase_cost_allowed(phase: str, amount: float) -> bool:
    """Enforce phase and absolute ceilings without making a broker call."""
    return 0 <= amount <= PHASE_CAPS.get(phase, -1) and amount <= BROKER_CEILING
