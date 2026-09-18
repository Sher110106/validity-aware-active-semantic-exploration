"""Versioned crash-safe state, telemetry, secure artifacts, and chained events."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .contract import BASELINE, EXPERIMENTAL, MODEL, THINKING_LEVEL, ContractError

HEX64 = re.compile(r"^[0-9a-f]{64}$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
EVENTS = {"reserve", "launch_intent", "heartbeat", "pause", "stop", "retry", "complete", "incomplete"}


@dataclass(frozen=True)
class Control:
    paused: bool = False
    stop: bool = False
    resume_generation: int = 0
    approved_hashes: tuple[str, ...] = ()
    max_attempts: int = 2
    min_free_disk_gb: int = 25
    stall_seconds: int = 1800
    runtime_seconds: int = 8 * 3600


@dataclass(frozen=True)
class Telemetry:
    technical_health: bool | None
    connectivity: bool | None
    free_disk_gb: int | None
    heartbeat_age_seconds: int | None
    elapsed_runtime_seconds: int | None
    ledger_reconciled: bool | None


def validate_control(raw: dict, expected_hashes: Iterable[str]) -> Control:
    allowed = set(Control.__dataclass_fields__)
    if set(raw) - allowed:
        raise ContractError("unknown control keys")
    try:
        control = Control(**raw)
    except (TypeError, ValueError) as exc:
        raise ContractError("malformed control") from exc
    if control.max_attempts != 2 or control.min_free_disk_gb < 25 or control.stall_seconds < 60:
        raise ContractError("unsafe control limits")
    if control.runtime_seconds <= 0 or control.resume_generation < 0:
        raise ContractError("invalid control values")
    if set(control.approved_hashes) != set(expected_hashes):
        raise ContractError("approved hashes do not match exact contract")
    return control


def validate_telemetry(t: Telemetry) -> None:
    if any(value is None for value in (t.technical_health, t.connectivity, t.free_disk_gb,
                                       t.heartbeat_age_seconds, t.elapsed_runtime_seconds, t.ledger_reconciled)):
        raise ContractError("missing health telemetry; fail closed")
    if t.free_disk_gb < 0 or t.heartbeat_age_seconds < 0 or t.elapsed_runtime_seconds < 0:
        raise ContractError("invalid health telemetry")


def can_continue(*, telemetry: Telemetry, control: Control) -> tuple[bool, str]:
    validate_telemetry(telemetry)
    if control.stop or control.paused: return False, "operator pause/stop"
    if not telemetry.connectivity: return False, "connectivity loss; fail closed"
    if not telemetry.ledger_reconciled: return False, "ledger is not reconciled"
    if not telemetry.technical_health: return False, "technical health failed"
    if telemetry.free_disk_gb < control.min_free_disk_gb: return False, "disk floor"
    if telemetry.heartbeat_age_seconds > control.stall_seconds: return False, "stall limit"
    if telemetry.elapsed_runtime_seconds > control.runtime_seconds: return False, "runtime limit"
    return True, "healthy"


def atomic_json(path: Path, value: dict) -> None:
    if path.exists() and path.is_symlink(): raise ContractError("target is symlink")
    path = path.resolve(strict=False)
    _secure_parent(path.parent)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(tmp, flags, 0o600)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, path)
        fd_dir = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(fd_dir)
        finally: os.close(fd_dir)
    finally:
        if tmp.exists(): tmp.unlink()


def _secure_parent(path: Path) -> None:
    current = Path(path.anchor) if path.is_absolute() else Path.cwd()
    for component in path.parts[1:] if path.is_absolute() else path.parts:
        if component in ("", ".", ".."): raise ContractError("unsafe path component")
        current /= component
        if current.exists() and current.is_symlink(): raise ContractError("symlink in secure path")
        current.mkdir(exist_ok=True)
        if not stat.S_ISDIR(current.stat(follow_symlinks=False).st_mode): raise ContractError("parent is not directory")


def secure_attempt(root: Path, campaign: str, scene: str, seed: int, policy: str, attempt: int) -> Path:
    values = (campaign, scene, str(seed), policy, str(attempt))
    if any(not SLUG.fullmatch(value) for value in values) or scene not in ("00069", "00573", "00853"):
        raise ContractError("unsafe attempt identifier")
    if type(seed) is not int or type(attempt) is not int or attempt not in (1, 2): raise ContractError("invalid attempt")
    root = root.resolve(strict=False)
    path = root / "runs" / "prospective_gemini" / campaign / scene / str(seed) / policy / str(attempt)
    if path.is_symlink() or not path.resolve(strict=False).is_relative_to(root): raise ContractError("path escapes run root")
    _secure_parent(path.parent)
    path.mkdir(exist_ok=False, mode=0o700)
    return path


def parse_hash_file(path: Path, required: tuple[str, ...]) -> dict[str, str]:
    if path.is_symlink() or not path.is_file(): raise ContractError("hash file is not a regular file")
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if len(line) < 67 or line[64:66] != "  ": raise ContractError("malformed hash line")
        digest, relative = line[:64], line[66:]
        if not HEX64.fullmatch(digest) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ContractError("unsafe hash entry")
        normalized = Path(relative).as_posix()
        if normalized != relative or relative in result: raise ContractError("duplicate/non-normalized hash entry")
        result[relative] = digest
    if set(required) - set(result): raise ContractError("required artifact is not hashed")
    return result


def validate_artifacts(run_dir: Path, required: tuple[str, ...]) -> tuple[bool, str]:
    try: hashes = parse_hash_file(run_dir / "ARTIFACTS.sha256", required)
    except (OSError, ContractError) as exc: return False, str(exc)
    for relative in required:
        path = run_dir / relative
        if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.stat(follow_symlinks=False).st_mode): return False, f"unsafe artifact: {relative}"
        if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[relative]: return False, f"artifact hash mismatch: {relative}"
    return True, "validated"


def write_completion_marker(run_dir: Path, *, required: tuple[str, ...], linkage: dict[str, str]) -> None:
    ok, reason = validate_artifacts(run_dir, required)
    if not ok: raise ContractError(reason)
    if set(linkage) != {"manifest_hash", "start_state_hash", "policy_hash", "allocation_id", "hash_set_hash"}:
        raise ContractError("incomplete completion linkage")
    atomic_json(run_dir / "COMPLETE.json", {"complete": True, "artifact_validation": reason, "linkage": linkage})


class EventLog:
    def __init__(self, path: Path):
        self.path, self.previous, self.next_sequence = path, "0" * 64, 0
        if path.exists():
            for line in path.read_text().splitlines():
                try: row = json.loads(line)
                except json.JSONDecodeError as exc: raise ContractError("corrupt event log") from exc
                if row.get("sequence") != self.next_sequence or row.get("previous_hash") != self.previous:
                    raise ContractError("event chain or sequence invalid")
                body = {k: row[k] for k in ("sequence", "event", "run_id", "allocation_id", "previous_hash")}
                if hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest() != row.get("hash"):
                    raise ContractError("event hash invalid")
                self.previous, self.next_sequence = row["hash"], self.next_sequence + 1

    def append(self, event: str, *, sequence: int, run_id: str, allocation_id: str) -> None:
        if event not in EVENTS or type(sequence) is not int or sequence != self.next_sequence:
            raise ContractError("invalid event")
        if not SLUG.fullmatch(run_id) or not SLUG.fullmatch(allocation_id): raise ContractError("unsafe event id")
        body = {"sequence": sequence, "event": event, "run_id": run_id, "allocation_id": allocation_id, "previous_hash": self.previous}
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        current = hashlib.sha256(encoded).hexdigest(); body["hash"] = current
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as handle: handle.write(json.dumps(body, sort_keys=True) + "\n"); handle.flush(); os.fsync(handle.fileno())
        self.previous, self.next_sequence = current, self.next_sequence + 1
