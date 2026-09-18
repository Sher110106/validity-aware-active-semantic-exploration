"""Auditable cost-adaptive terminal scope decision (pure, no execution)."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ScopeDecision:
    pilot_cost: float
    worst_case_pair_cost: float
    selected_horizon: int | None
    seed42_block_fits: bool
    seed43_block_fits: bool
    seed44_block_fits: bool
    terminal_reason: str


def decide_scope(*, pilot_cost: float, available_after_pilot: float,
                 worst_case_pair_cost: float, horizon: int | None) -> ScopeDecision:
    pair = (worst_case_pair_cost * horizon / 120.0) if horizon else float("inf")
    first = pair * 3 <= available_after_pilot
    later = first and pair * 3 <= available_after_pilot - pair * 3
    reason = "seed42 then complete seed blocks only while each block fits"
    if not first:
        reason = "no complete 3-pair block fits conservative post-pilot budget"
    return ScopeDecision(pilot_cost, worst_case_pair_cost, horizon, first, later, later, reason)


def terminal_scope_json(decision: ScopeDecision) -> dict:
    return {"schema": "prospective_scope_decision_v1", **asdict(decision)}
