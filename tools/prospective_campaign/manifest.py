"""Explicit allowlist manifest; no recursive environment/key redaction."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .contract import BASELINE, EXPERIMENTAL, MODEL, THINKING_LEVEL, ContractError

HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
SAFE_TAG = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
SECRET = re.compile(r"(?i)(api[_-]?key|secret|token|password|credential|authorization)")
ALLOWED_MODES = {"dry", "unattended", "strict"}
REQUIRED_HASHES = ("scene", "reference", "navmesh", "calibrator", "prompt", "policy")


def _hash(value: str, name: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value): raise ContractError(f"invalid {name} hash")
    return value


def build_manifest(*, source_tag: str, author_commit: str, container_digest: str, environment_tag: str,
                   hashes: dict[str, str], model: str, thinking_level: str, policy: str,
                   controller_mode: str, audit_mode: str, scene: str, seed: int,
                   start_state_hash: str, horizon_m: int, budget_ledger_id: str,
                   allocation_id: str) -> dict[str, Any]:
    if not SAFE_TAG.fullmatch(source_tag) or not HEX64.fullmatch(author_commit) or not HEX64.fullmatch(container_digest):
        raise ContractError("invalid source/commit/container identifier")
    if model != MODEL or thinking_level != THINKING_LEVEL or policy not in (BASELINE, EXPERIMENTAL):
        raise ContractError("manifest model/reasoning/policy is not the immutable contract")
    if controller_mode not in ALLOWED_MODES or audit_mode not in ALLOWED_MODES: raise ContractError("invalid mode")
    if scene not in ("00069", "00573", "00853") or type(seed) is not int or seed not in (42, 43, 44): raise ContractError("invalid scene/seed")
    if type(horizon_m) is not int or horizon_m not in (25, 50, 75, 120): raise ContractError("invalid horizon_m")
    if not SAFE_ID.fullmatch(budget_ledger_id) or not SAFE_ID.fullmatch(allocation_id): raise ContractError("unsafe ledger id")
    if set(hashes) != set(REQUIRED_HASHES): raise ContractError("manifest hash allowlist mismatch")
    checked_hashes = {key: _hash(hashes[key], key) for key in REQUIRED_HASHES}
    _hash(start_state_hash, "start_state")
    if SECRET.search(environment_tag) or "://" in environment_tag or any(ord(c) < 32 for c in environment_tag):
        raise ContractError("unsafe environment tag")
    return {"schema": "prospective_campaign_manifest_v2", "source_tag": source_tag,
            "author_commit": author_commit, "container_digest": container_digest,
            "environment_tag": environment_tag, "hashes": checked_hashes, "model": model,
            "reasoning": {"thinking_level": thinking_level}, "policy": policy,
            "controller_mode": controller_mode, "audit_mode": audit_mode, "scene": scene,
            "seed": seed, "start_state_hash": start_state_hash, "horizon_m": horizon_m,
            "budget_ledger_id": budget_ledger_id, "allocation_id": allocation_id}


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    if path.is_symlink(): raise ContractError("manifest path is symlink")
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
