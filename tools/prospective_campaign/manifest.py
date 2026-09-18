"""Manifest extension with strict secret redaction and source hashes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SECRET_WORDS = ("key", "token", "secret", "password", "credential", "authorization")
REQUIRED_HASHES = ("scene", "reference", "navmesh", "calibrator", "prompt", "policy")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact(value: Any, key: str = "") -> Any:
    if any(word in key.lower() for word in SECRET_WORDS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def build_manifest(*, source_tag: str, author_commit: str, environment: dict[str, Any],
                   hashes: dict[str, str], model: str, thinking_level: str, seed: int,
                   start_state: str, budget_ledger_id: str, controller_mode: str,
                   audit_mode: str) -> dict[str, Any]:
    missing = [name for name in REQUIRED_HASHES if name not in hashes]
    if missing:
        raise ValueError("manifest missing required hashes: " + ", ".join(missing))
    result = {"schema": "prospective_campaign_manifest_v1", "source_tag": source_tag,
              "author_commit": author_commit, "environment": environment,
              "hashes": hashes, "model": model, "reasoning": {"thinking_level": thinking_level},
              "seed": seed, "start_state": start_state, "budget_ledger_id": budget_ledger_id,
              "controller_mode": controller_mode, "audit_mode": audit_mode}
    return redact(result)


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(redact(manifest), indent=2, sort_keys=True) + "\n")
