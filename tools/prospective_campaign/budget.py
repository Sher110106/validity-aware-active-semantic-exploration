"""Strict in-memory ledger fake for tests only; no real broker integration."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FakeGeminiLedger:
    ceiling_micro_usd: int = 190_000_000
    allocations: dict[str, int] = field(default_factory=dict)
    draws: dict[str, int] = field(default_factory=dict)

    def available_micro_usd(self) -> int:
        return self.ceiling_micro_usd - sum(self.allocations.values())

    def reserve_block(self, allocation_id: str, amount_micro_usd: int) -> bool:
        if type(amount_micro_usd) is not int or amount_micro_usd < 0 or allocation_id in self.allocations:
            return False
        if amount_micro_usd > self.available_micro_usd():
            return False
        self.allocations[allocation_id] = amount_micro_usd
        return True

    def draw(self, allocation_id: str, request_id: str, amount_micro_usd: int) -> bool:
        if allocation_id not in self.allocations or request_id in self.draws:
            return False
        used = sum(v for k, v in self.draws.items() if k.startswith(allocation_id + ':'))
        if type(amount_micro_usd) is not int or amount_micro_usd < 0 or used + amount_micro_usd > self.allocations[allocation_id]:
            return False
        self.draws[allocation_id + ':' + request_id] = amount_micro_usd
        return True

    def release(self, allocation_id: str) -> None:
        raise RuntimeError("allocations are immutable and cannot be released after draw")
