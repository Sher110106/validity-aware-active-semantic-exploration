"""Strictly isolated snapshot/branch contracts and deterministic stage sampling."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol, Sequence


class SnapshotAdapter(Protocol):
    def snapshot(self) -> Any: ...
    def restore(self, snapshot: Any) -> bool: ...
    def state_hash(self) -> str: ...


@dataclass(frozen=True)
class StageSample:
    stage_id: str
    eligible: bool
    reason: str


class BranchRunner:
    def __init__(self, adapter: SnapshotAdapter) -> None:
        self.adapter = adapter

    def run_pair(self, original, counterfactual):
        snapshot = self.adapter.snapshot()
        before = self.adapter.state_hash()
        if not self.adapter.restore(snapshot) or self.adapter.state_hash() != before:
            raise RuntimeError("exact snapshot restoration is not guaranteed; refusing branch comparison")
        first = original()
        if not self.adapter.restore(snapshot) or self.adapter.state_hash() != before:
            raise RuntimeError("snapshot restore failed between branches")
        second = counterfactual()
        return first, second


def fixed_stage_samples(stage_ids: Iterable[str], *, stride: int = 1, offset: int = 0) -> list[StageSample]:
    if stride < 1 or offset < 0:
        raise ValueError("stride must be positive and offset non-negative")
    result = []
    for index, stage_id in enumerate(stage_ids):
        result.append(StageSample(str(stage_id), index >= offset and (index - offset) % stride == 0, "fixed_stride"))
    return result
