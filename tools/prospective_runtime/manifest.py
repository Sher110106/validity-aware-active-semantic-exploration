from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping, Optional, Union


@dataclass(frozen=True)
class RuntimeManifest:
    model: str
    reasoning: str
    policy: str
    seed: int
    start_state: str
    output_dir: str
    ledger_path: str
    path_budget_m: float = 120.0
    wall_clock_limit_s: Optional[float] = None
    broker_contract: Optional[str] = None
    campaign_contract: Optional[str] = None

    def validate(self, *, live: bool = False) -> None:
        if self.model != "gemini-3.8-flash":
            raise ValueError("model must be exactly gemini-3.8-flash")
        if self.reasoning != "medium":
            raise ValueError("reasoning must be exactly medium")
        if self.policy not in {"official_asp", "validator_plus_unanimity_raw_tau_1_0"}:
            raise ValueError("unsupported policy")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a non-negative integer")
        if self.path_budget_m <= 0:
            raise ValueError("path_budget_m is a meter budget, and must be positive")
        for field in ("start_state", "output_dir", "ledger_path"):
            value = Path(getattr(self, field))
            if not value.is_absolute():
                raise ValueError(f"{field} must be an absolute path")
        if live and (not self.broker_contract or not self.campaign_contract):
            raise ValueError("live mode requires audited broker and campaign contracts")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "RuntimeManifest":
        allowed = set(cls.__dataclass_fields__)
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError("unknown manifest fields: " + ", ".join(sorted(unknown)))
        result = cls(**{k: raw[k] for k in raw})
        result.validate()
        return result

    @classmethod
    def load(cls, path: Union[str, Path]) -> "RuntimeManifest":
        with Path(path).open() as handle:
            return cls.from_mapping(json.load(handle))


def file_sha256(path: Union[str, Path]) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
