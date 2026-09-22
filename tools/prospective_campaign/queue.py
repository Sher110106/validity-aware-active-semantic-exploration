"""Deterministic, order-aware queue and transactional block admission."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contract import BASELINE, EXPERIMENTAL, HORIZON_M, SCENES, SEEDS, ContractError


ORDERS = {42: (('00069', 'O→E'), ('00573', 'E→O'), ('00853', 'O→E')),
          43: (('00573', 'E→O'), ('00853', 'O→E'), ('00069', 'E→O')),
          44: (('00853', 'O→E'), ('00069', 'E→O'), ('00573', 'O→E'))}


def _strict_horizon(value: int) -> int:
    if type(value) is not int or value not in HORIZON_M:
        raise ContractError("horizon_m must be one of the preregistered path budgets")
    return value


@dataclass(frozen=True)
class Pair:
    scene: str
    seed: int
    order: str
    horizon_m: int

    def __post_init__(self):
        if self.scene not in SCENES or self.seed not in SEEDS or self.order not in ('O→E', 'E→O'):
            raise ContractError("invalid pair identity")
        _strict_horizon(self.horizon_m)
        if (self.scene, self.order) not in ORDERS[self.seed]:
            raise ContractError("scene/order is not the fixed queue order")

    @property
    def id(self) -> str:
        return f"{self.scene}-seed{self.seed}-{self.order}-{self.horizon_m}m"

    @property
    def slug(self) -> str:
        """A `control.SLUG`-safe form of `id`, for use as e.g. PairState.pair_id.

        `id`'s arrow (O→E / E→O) is not ASCII and fails control.py's
        `^[a-z0-9][a-z0-9_-]{0,63}$` identifier regex, so nothing in this
        package can pass `id` itself into save_state()/CampaignLedgerAdapter.
        """
        direction = "o2e" if self.order == "O→E" else "e2o"
        return f"{self.scene}-seed{self.seed}-{direction}-{self.horizon_m}m"

    @property
    def policies(self) -> tuple[str, str]:
        return (BASELINE, EXPERIMENTAL) if self.order == 'O→E' else (EXPERIMENTAL, BASELINE)


def deterministic_queue(horizon_m: int = 120) -> tuple[Pair, ...]:
    _strict_horizon(horizon_m)
    return tuple(Pair(scene, seed, order, horizon_m) for seed in SEEDS for scene, order in ORDERS[seed])


class GeminiLedger(Protocol):
    def available_micro_usd(self) -> int: ...
    def reserve_block(self, allocation_id: str, amount_micro_usd: int) -> bool: ...
    def draw(self, allocation_id: str, request_id: str, amount_micro_usd: int) -> bool: ...


class TechnicalHealth(Protocol):
    def healthy(self) -> bool: ...


@dataclass(frozen=True)
class Admission:
    admitted: bool
    reason: str
    allocation_id: str | None = None
    amount_micro_usd: int = 0


def validate_block(pairs: tuple[Pair, ...], seed: int, horizon_m: int) -> None:
    _strict_horizon(horizon_m)
    expected = tuple(Pair(scene, seed, order, horizon_m) for scene, order in ORDERS[seed])
    if pairs != expected or len({p.scene for p in pairs}) != 3 or len({p.id for p in pairs}) != 3:
        raise ContractError("block must contain exactly the three unique scenes in fixed order")


def choose_horizon_m(available_micro_usd: int, prior_block_micro_usd: dict[int, int],
                     pilot_multiplier_num: int, pilot_multiplier_den: int,
                     unresolved_micro_usd: int = 0) -> int | None:
    """Select common block path budget before outcomes, including unresolved spend."""
    if type(available_micro_usd) is not int or type(unresolved_micro_usd) is not int:
        raise ContractError("money must be integer microUSD")
    if pilot_multiplier_num <= 0 or pilot_multiplier_den <= 0:
        raise ContractError("invalid pilot multiplier")
    for horizon in HORIZON_M:
        base = prior_block_micro_usd.get(horizon)
        if base is None:
            continue
        worst = (base * pilot_multiplier_num + pilot_multiplier_den - 1) // pilot_multiplier_den
        if worst + unresolved_micro_usd <= available_micro_usd:
            return horizon
    return None


class PairAdmissionController:
    def __init__(self, ledger: GeminiLedger, health: TechnicalHealth, *, worst_block_micro_usd: int):
        self.ledger, self.health, self.worst_block_micro_usd = ledger, health, worst_block_micro_usd

    def admit_block(self, pairs: tuple[Pair, ...], *, allocation_id: str) -> Admission:
        if not self.health.healthy():
            return Admission(False, "technical health is not healthy")
        validate_block(pairs, pairs[0].seed if pairs else -1, pairs[0].horizon_m if pairs else -1)
        amount = self.worst_block_micro_usd
        if self.ledger.available_micro_usd() < amount:
            return Admission(False, "complete block does not fit conservative budget")
        if not self.ledger.reserve_block(allocation_id, amount):
            return Admission(False, "ledger rejected transactional block reservation")
        return Admission(True, "complete block reserved", allocation_id, amount)


def allocate_block_costs(remaining_micro_usd: int, block_costs: tuple[int, ...]) -> tuple[int, ...]:
    """Sequentially decrement each admitted block; never report future blocks as fitting."""
    if any(type(x) is not int or x < 0 for x in block_costs):
        raise ContractError("invalid block cost")
    accepted = []
    for cost in block_costs:
        if cost <= remaining_micro_usd:
            accepted.append(cost); remaining_micro_usd -= cost
        else:
            break
    return tuple(accepted)
