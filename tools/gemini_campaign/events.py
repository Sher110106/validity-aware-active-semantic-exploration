"""Chained, append-only sanitized event log."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import time
from typing import Any

from .ledger import _ID

_ALLOWED = {
    "event", "request_id", "campaign_id", "phase_id", "run_id", "stage_id",
    "member_id", "tool_turn_id", "attempt_id", "model", "thinking_level",
    "state", "finish_reason", "response_id", "error_code", "timestamp",
}
_IDENTIFIER_KEYS = _ALLOWED - {"event", "model", "thinking_level", "state", "finish_reason", "timestamp"}


def _safe_event(event: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise ValueError("event is invalid")
    safe = {key: event[key] for key in _ALLOWED if key in event}
    for key in _IDENTIFIER_KEYS:
        if key in safe and (not isinstance(safe[key], str) or "://" in safe[key] or not _ID.fullmatch(safe[key])):
            raise ValueError("event identifier is invalid")
    for key in ("event", "model", "thinking_level", "state", "finish_reason", "error_code"):
        if key in safe and (not isinstance(safe[key], str) or len(safe[key]) > 128):
            raise ValueError("event value is invalid")
    safe["timestamp"] = safe.get("timestamp", int(time.time()))
    if not isinstance(safe["timestamp"], int):
        raise ValueError("event timestamp is invalid")
    return safe


def append_event(path: str, event: dict[str, Any]) -> None:
    safe = _safe_event(event)
    flags = os.O_RDWR | os.O_CREAT | os.O_APPEND | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
            raise OSError("event file policy rejected")
        try:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX)
        except (ImportError, OSError) as exc:
            raise OSError("event lock unavailable") from exc
        try:
            with os.fdopen(fd, "r+", encoding="utf-8", closefd=False) as handle:
                handle.seek(0)
                previous = "0" * 64
                sequence = 0
                for line in handle:
                    record = json.loads(line)
                    sequence = record["sequence"]
                    previous = record["hash"]
                payload = dict(safe, sequence=sequence + 1, previous_hash=previous)
                encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                record = dict(payload, hash=hashlib.sha256(previous.encode() + encoded).hexdigest())
                handle.seek(0, os.SEEK_END)
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(fd)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
