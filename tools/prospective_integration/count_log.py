"""Records every native_input_bound() measurement -- real count, byte
bound, which one was used, and (on any failure) the exception type and
message. Deliberately separate from the sanitized ledger event log and
from raw_archive.py's full-payload archive.

Advisor review (2026-09-21/22): the campaign's invariant is that nothing
touching the real credential goes unaccounted. count_tokens() is free and
never reserves anything, but a silent fallback on failure (a transient
rate limit, say) is indistinguishable from "the fix doesn't work" without
a record -- this module is that record. Multiple worker processes call
append() concurrently -- serialized with flock, same pattern as
race_instrumentation.py/raw_archive.py."""
from __future__ import annotations

import fcntl
import json
import os
import time
from pathlib import Path
from typing import Optional, Union


class CountLog:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        if self.path.exists() and self.path.is_symlink():
            raise ValueError("refusing symlink instrumentation path")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, *, real_count: Optional[int], byte_bound: int, used: int,
              error: Optional[BaseException]) -> None:
        record = {
            "timestamp": time.time(), "pid": os.getpid(),
            "real_count": real_count, "byte_bound": byte_bound, "used": used,
            "fell_back": error is not None,
            "error_type": type(error).__name__ if error is not None else None,
            "error_message": str(error) if error is not None else None,
        }
        line = json.dumps(record, sort_keys=True) + "\n"
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(str(self.path), flags, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                os.write(fd, line.encode("utf-8"))
                os.fsync(fd)
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
