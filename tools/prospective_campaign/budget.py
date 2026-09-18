"""Small fakeable budget ledger; it never contacts a paid service."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FakeBudgetBroker:
    ceiling: float = 190.0
    reservations: dict[str, float] = field(default_factory=dict)

    def available(self) -> float:
        return self.ceiling - sum(self.reservations.values())

    def reserve(self, reservation_id: str, amount: float) -> bool:
        if amount < 0 or amount > self.available():
            return False
        self.reservations[reservation_id] = amount
        return True

    def release(self, reservation_id: str) -> None:
        self.reservations.pop(reservation_id, None)
