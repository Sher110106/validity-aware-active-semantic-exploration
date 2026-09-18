from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Union

SHA256 = re.compile(r"^[0-9a-f]{64}$")
PATH_FIELDS = ("start_state_ref", "output_root", "ledger_root")


@dataclass(frozen=True)
class RuntimeManifest:
    model: str
    reasoning: str
    policy: str
    scene: str
    seed: int
    run_id: str
    attempt_id: str
    start_state_ref: str
    start_state_sha256: str
    output_root: str
    ledger_root: str
    path_budget_m: int
    wall_clock_limit_s: float
    approved_source_sha256: str
    approved_prompt_sha256: str
    approved_policy_sha256: str
    approved_navmesh_sha256: str
    approved_reference_sha256: str
    broker_allocation_id: str
    broker_ledger_id: str
    stage_mode: str = "full"

    def validate(self, *, repo_root: Optional[Union[str, Path]] = None) -> None:
        if self.model != "gemini-3.8-flash" or self.reasoning != "medium": raise ValueError("exact model/reasoning required")
        if self.policy not in {"official_asp", "validator_plus_unanimity_raw_tau_1_0"}: raise ValueError("unsupported policy")
        if not self.scene or not isinstance(self.seed, int) or self.seed < 0: raise ValueError("scene/seed invalid")
        if not self.run_id or not self.attempt_id or self.stage_mode not in {"full", "pilot"}: raise ValueError("run identity invalid")
        if isinstance(self.path_budget_m, bool) or not isinstance(self.path_budget_m, int) or self.path_budget_m not in {25, 50, 75, 120}:
            raise ValueError("path budget must be an exact integer 25/50/75/120 meters")
        if not isinstance(self.wall_clock_limit_s, (int, float)) or self.wall_clock_limit_s <= 0: raise ValueError("finite wall-clock limit required")
        for name in ("start_state_sha256", "approved_source_sha256", "approved_prompt_sha256", "approved_policy_sha256", "approved_navmesh_sha256", "approved_reference_sha256"):
            if not isinstance(getattr(self, name), str) or not SHA256.fullmatch(getattr(self, name)): raise ValueError(f"invalid {name}")
        for name in ("broker_allocation_id", "broker_ledger_id"):
            if not getattr(self, name): raise ValueError(f"missing {name}")
        root = Path(repo_root or Path.cwd()).resolve()
        for name in PATH_FIELDS:
            path = Path(getattr(self, name))
            if not path.is_absolute() or path.is_symlink(): raise ValueError(f"{name} must be absolute and not symlink")
            try: path.resolve().relative_to(root)
            except ValueError: pass
            else: raise ValueError(f"{name} must be outside repository")

    def as_dict(self) -> dict[str, Any]: return asdict(self)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "RuntimeManifest":
        allowed = set(cls.__dataclass_fields__)
        if set(raw) - allowed: raise ValueError("unknown manifest fields")
        result = cls(**dict(raw)); result.validate(); return result

    @classmethod
    def load(cls, path: Union[str, Path]) -> "RuntimeManifest":
        with Path(path).open() as handle: return cls.from_mapping(json.load(handle))


def file_sha256(path: Union[str, Path]) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
