"""Fail-closed branch execution contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Protocol

from .schema import EvidenceReceipt, stable_hash


@dataclass(frozen=True)
class AdapterCapabilities:
    exact_snapshot_restore: bool
    external_rng_hash: bool
    observation_hash: bool
    filesystem_hash: bool
    isolated_execution: bool


@dataclass(frozen=True)
class SnapshotManifest:
    manifest_id: str
    simulator_hash: str
    agent_hash: str
    mapping_hash: str
    controller_hash: str
    rng_hash: str
    filesystem_hash: str
    inputs_hash: str
    state_hash: str
    manifest_hash: str

    @classmethod
    def create(cls, **values: str) -> "SnapshotManifest":
        required = {"manifest_id", "simulator_hash", "agent_hash", "mapping_hash", "controller_hash", "rng_hash", "filesystem_hash", "inputs_hash", "state_hash"}
        if set(values) != required or any(not value for value in values.values()):
            raise ValueError("complete immutable snapshot manifest required")
        digest = stable_hash(values)
        return cls(**values, manifest_hash=digest)

    def verify(self) -> bool:
        data = self.__dict__.copy()
        digest = data.pop("manifest_hash")
        return digest == stable_hash(data) and all(isinstance(v, str) and v for v in data.values())


class SnapshotAdapter(Protocol):
    def capabilities(self) -> AdapterCapabilities: ...
    def snapshot_manifest(self) -> SnapshotManifest: ...
    def restore(self, manifest: SnapshotManifest) -> EvidenceReceipt: ...
    def current_manifest_hash(self) -> str: ...
    def external_hashes(self) -> dict[str, str]: ...


@dataclass(frozen=True)
class StageSample:
    stage_id: str
    eligible: bool
    reason: str


class BranchRunner:
    def __init__(self, adapter: SnapshotAdapter) -> None:
        self.adapter = adapter

    def _restore(self, manifest: SnapshotManifest, label: str) -> EvidenceReceipt:
        receipt = self.adapter.restore(manifest)
        if not receipt.verify() or receipt.kind != "restore" or receipt.payload.get("branch") != label:
            raise RuntimeError("invalid restore receipt")
        if self.adapter.current_manifest_hash() != manifest.manifest_hash:
            raise RuntimeError("snapshot state mismatch")
        return receipt

    def run_pair(self, original: Callable[[], Any], counterfactual: Callable[[], Any]) -> tuple[Any, Any]:
        caps = self.adapter.capabilities()
        if not all((caps.exact_snapshot_restore, caps.external_rng_hash, caps.observation_hash, caps.filesystem_hash, caps.isolated_execution)):
            raise RuntimeError("adapter lacks exact restore, external-hash, or isolation capability")
        manifest = self.adapter.snapshot_manifest()
        if not manifest.verify():
            raise RuntimeError("invalid immutable snapshot manifest")
        baseline_external = self.adapter.external_hashes()
        self._restore(manifest, "original")
        if self.adapter.external_hashes() != baseline_external:
            raise RuntimeError("external state changed before original branch")
        first = original()
        self._restore(manifest, "counterfactual")
        if self.adapter.external_hashes() != baseline_external:
            raise RuntimeError("external state changed before counterfactual branch")
        second = counterfactual()
        self._restore(manifest, "cleanup")
        if self.adapter.external_hashes() != baseline_external:
            raise RuntimeError("cleanup did not restore external state")
        return first, second


def fixed_stage_samples(stage_ids: Iterable[str], *, stride: int = 1, offset: int = 0) -> list[StageSample]:
    if stride < 1 or offset < 0:
        raise ValueError("stride must be positive and offset non-negative")
    return [StageSample(str(stage_id), index >= offset and (index - offset) % stride == 0, "fixed_stride") for index, stage_id in enumerate(stage_ids)]
