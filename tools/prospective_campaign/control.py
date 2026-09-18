"""Crash-safe, fail-closed controller primitives for paired runs."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class Control:
    paused: bool = False
    stop: bool = False
    resume_generation: int = 0
    approved_hashes: tuple[str, ...] = ()
    max_attempts: int = 2
    min_free_disk_gb: float = 25.0
    stall_seconds: int = 1800
    runtime_seconds: int = 8 * 3600


def validate_control(raw: dict, expected_hashes: Iterable[str]) -> Control:
    allowed = set(Control.__dataclass_fields__)
    if set(raw) - allowed:
        raise ValueError("unknown control keys")
    control = Control(**raw)
    if control.max_attempts != 2 or control.min_free_disk_gb < 25 or control.stall_seconds < 60:
        raise ValueError("unsafe control limits")
    if control.runtime_seconds <= 0 or control.resume_generation < 0:
        raise ValueError("invalid control values")
    if set(control.approved_hashes) != set(expected_hashes):
        raise ValueError("approved hashes do not match exact contract")
    return control


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


class EventLog:
    def __init__(self, path: Path):
        self.path = path

    def append(self, event: str, **details: object) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as handle:
            handle.write(json.dumps({"event": event, "time": time.time(), **details}, sort_keys=True) + "\n")


def validate_artifacts(run_dir: Path, required: tuple[str, ...]) -> tuple[bool, str]:
    for relative in required:
        path = run_dir / relative
        if not path.is_file() or not path.stat().st_size:
            return False, f"missing or empty artifact: {relative}"
    digest_file = run_dir / "ARTIFACTS.sha256"
    if not digest_file.is_file():
        return False, "missing ARTIFACTS.sha256"
    expected = {}
    for line in digest_file.read_text().splitlines():
        digest, _, relative = line.partition("  ")
        expected[relative] = digest
    for relative, digest in expected.items():
        if not (run_dir / relative).is_file():
            return False, f"hashed artifact missing: {relative}"
        actual = hashlib.sha256((run_dir / relative).read_bytes()).hexdigest()
        if actual != digest:
            return False, f"artifact hash mismatch: {relative}"
    return True, "validated"


def write_completion_marker(run_dir: Path, *, required: tuple[str, ...], marker: str = "COMPLETE.json") -> None:
    ok, reason = validate_artifacts(run_dir, required)
    if not ok:
        raise ValueError(reason)
    atomic_json(run_dir / marker, {"complete": True, "artifact_validation": reason})


def isolated_attempt(root: Path, campaign: str, scene: str, seed: int, policy: str, attempt: int) -> Path:
    path = root / "runs" / "prospective_gemini" / campaign / scene / str(seed) / policy / str(attempt)
    path.mkdir(parents=True, exist_ok=False)
    return path


def can_continue(*, connectivity_ok: bool, disk_gb: float, stalled: bool, runtime_exceeded: bool,
                 control: Control, spend_known: bool = True) -> tuple[bool, str]:
    if control.stop or control.paused:
        return False, "operator pause/stop"
    if not connectivity_ok:
        return False, "connectivity loss; fail closed"
    if not spend_known:
        return False, "unknown in-flight spend"
    if disk_gb < control.min_free_disk_gb:
        return False, "disk floor"
    if stalled:
        return False, "stall limit"
    if runtime_exceeded:
        return False, "runtime limit"
    return True, "healthy"
