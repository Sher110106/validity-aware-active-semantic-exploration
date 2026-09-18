"""Integer, sequential terminal scope decision."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from .contract import ContractError


@dataclass(frozen=True)
class ScopeDecision:
    pilot_cost_micro_usd: int
    available_after_pilot_micro_usd: int
    selected_horizon_m: int | None
    admitted_block_costs_micro_usd: tuple[int, ...]
    terminal_reason: str


def decide_scope(*, pilot_cost_micro_usd: int, available_after_pilot_micro_usd: int,
                 candidate_block_costs_micro_usd: tuple[int, ...], selected_horizon_m: int | None,
                 unresolved_micro_usd: int) -> ScopeDecision:
    values = (pilot_cost_micro_usd, available_after_pilot_micro_usd, unresolved_micro_usd)
    if any(type(x) is not int or x < 0 for x in values) or any(type(x) is not int or x < 0 for x in candidate_block_costs_micro_usd):
        raise ContractError("scope costs must be nonnegative integer microUSD")
    remaining = available_after_pilot_micro_usd - unresolved_micro_usd
    accepted = []
    if selected_horizon_m is not None:
        for cost in candidate_block_costs_micro_usd:
            if cost <= remaining: accepted.append(cost); remaining -= cost
            else: break
    reason = "terminal: sequentially admitted only blocks fitting worst-case cost, unresolved spend, and caps"
    return ScopeDecision(pilot_cost_micro_usd, available_after_pilot_micro_usd, selected_horizon_m, tuple(accepted), reason)


def terminal_scope_json(decision: ScopeDecision) -> dict:
    return {"schema": "prospective_scope_decision_v2", **asdict(decision)}
