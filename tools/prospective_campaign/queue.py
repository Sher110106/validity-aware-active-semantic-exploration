"""Deterministic queue and outcome-blind pair/block admission."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contract import EXPERIMENTAL, BASELINE, HORIZONS, SCENES, SEEDS


@dataclass(frozen=True)
class Pair:
    scene: str
    seed: int
    order: str
    horizon: int

    @property
    def id(self) -> str:
        return f"{self.scene}-seed{self.seed}-{self.order}-{self.horizon}m"

    @property
    def policies(self) -> tuple[str, str]:
        return (BASELINE, EXPERIMENTAL)


def deterministic_queue(horizon: int = 120) -> tuple[Pair, ...]:
    orders = {
        42: (("00069", "O→E"), ("00573", "E→O"), ("00853", "O→E")),
        43: (("00573", "E→O"), ("00853", "O→E"), ("00069", "E→O")),
        44: (("00853", "O→E"), ("00069", "E→O"), ("00573", "O→E")),
    }
    return tuple(Pair(scene, seed, order, horizon) for seed in SEEDS for scene, order in orders[seed])


class BudgetBroker(Protocol):
    def available(self) -> float: ...
    def reserve(self, reservation_id: str, amount: float) -> bool: ...
    def release(self, reservation_id: str) -> None: ...


class TechnicalHealth(Protocol):
    def healthy(self) -> bool: ...


@dataclass(frozen=True)
class Admission:
    admitted: bool
    reason: str
    reservation_id: str | None = None
    amount: float = 0.0


def choose_horizon(remaining: float, worst_case_pair_cost: float) -> int | None:
    """Choose before outcomes: largest ladder rung whose full pair is affordable."""
    if worst_case_pair_cost <= 0:
        raise ValueError("worst_case_pair_cost must be positive")
    for horizon in HORIZONS:
        if worst_case_pair_cost * horizon / 120.0 <= remaining:
            return horizon
    return None


class PairAdmissionController:
    def __init__(self, broker: BudgetBroker, health: TechnicalHealth, *, cost_per_120m: float):
        self.broker, self.health = broker, health
        self.cost_per_120m = cost_per_120m
        self.reserved: set[str] = set()

    def admit_pair(self, pair: Pair) -> Admission:
        # Only budget and technical health are consulted; no score/result argument exists.
        if not self.health.healthy():
            return Admission(False, "technical health is not healthy")
        amount = self.cost_per_120m * pair.horizon / 120.0
        reservation = f"pair:{pair.id}"
        if reservation in self.reserved:
            return Admission(False, "pair already reserved", reservation, amount)
        if self.broker.available() < amount:
            return Admission(False, "full pair does not fit conservative budget")
        if not self.broker.reserve(reservation, amount):
            return Admission(False, "budget broker rejected full-pair reservation")
        self.reserved.add(reservation)
        return Admission(True, "full pair reserved", reservation, amount)

    def admit_block(self, pairs: tuple[Pair, ...]) -> Admission:
        if not pairs:
            return Admission(False, "empty block")
        if not self.health.healthy():
            return Admission(False, "technical health is not healthy")
        amount = sum(self.cost_per_120m * p.horizon / 120.0 for p in pairs)
        reservation = "block:" + ",".join(p.id for p in pairs)
        if self.broker.available() < amount or not self.broker.reserve(reservation, amount):
            return Admission(False, "complete block does not fit conservative budget")
        self.reserved.add(reservation)
        return Admission(True, "complete block reserved", reservation, amount)
