from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping, Union

ID = re.compile(r"^[A-Za-z0-9_.:/-]{1,200}$")
SCHEMAS = {
    "attempt_started": {"run_id", "attempt_id"},
    "request_dispatched": {"run_id", "stage_id", "member_id", "turn_id", "request_hash"},
    "request_unresolved": {"run_id", "stage_id", "member_id", "turn_id", "reason"},
    "motion_audited": {"run_id", "stage_id", "command_id", "event"},
    "policy_written": {"run_id", "stage_id", "track_id", "output_hash"},
}


class AppendOnlyRuntimeLog:
    """Non-financial, allowlisted hash-chain log; broker remains financial authority."""

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        if self.path.exists() and self.path.is_symlink(): raise ValueError("log symlink refused")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists(): os.chmod(self.path, 0o600)

    def append(self, event: str, data: Mapping[str, Any]) -> str:
        if event not in SCHEMAS or set(data) != SCHEMAS[event]: raise ValueError("event schema mismatch")
        for value in data.values():
            if not isinstance(value, str) or "://" in value or not ID.fullmatch(value):
                raise ValueError("IDs/log values must be bounded, URL-free strings")
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"): flags |= os.O_NOFOLLOW
        fd = os.open(str(self.path), flags, 0o600)
        try:
            with os.fdopen(fd, "a", encoding="utf-8") as handle:
                fcntl.flock(handle, fcntl.LOCK_EX)
                previous, sequence = self._tail()
                unsigned = {"sequence": sequence + 1, "event": event, "data": dict(data), "previous": previous}
                digest = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                handle.write(json.dumps(dict(unsigned, hash=digest), sort_keys=True, separators=(",", ":")) + "\n")
                handle.flush(); os.fsync(handle.fileno()); fcntl.flock(handle, fcntl.LOCK_UN)
                return digest
        except Exception:
            raise

    def _tail(self) -> tuple[str, int]:
        if not self.path.exists() or not self.path.stat().st_size: return "0" * 64, 0
        lines = self.path.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[-1]); return record["hash"], int(record["sequence"])

    def verify(self) -> bool:
        previous, sequence = "0" * 64, 0
        if not self.path.exists(): return True
        for line in self.path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record["sequence"] != sequence + 1 or record["previous"] != previous: return False
            unsigned = {k: record[k] for k in ("sequence", "event", "data", "previous")}
            if hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest() != record["hash"]: return False
            sequence, previous = record["sequence"], record["hash"]
        return True


AppendOnlyLedger = AppendOnlyRuntimeLog
