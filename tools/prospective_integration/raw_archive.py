"""Optional raw request/response archive for GeminiTransport.

Deliberately separate from gemini_campaign/events.py's sanitized,
allowlisted log: that one is the financial-audit trail and stays
metadata-only by design. This one captures full request/response bodies
on purpose, for engineering debugging of a live run, and is never
consulted for accounting. It never receives the credential -- transport.py's
on_raw_response hook only ever sees the request/response JSON bodies,
never the auth header.

Multiple ProcessPoolExecutor workers may call this concurrently (one real
Gemini call each); appends are serialized with flock, matching the same
pattern already used by gemini_campaign/events.py and
prospective_eval/schema.py's AppendOnlyLog.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
from typing import Any, Mapping, Union


class RawResponseArchive:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        if self.path.exists() and self.path.is_symlink():
            raise ValueError("refusing symlink archive path")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, *, request: Mapping[str, Any], payload: Mapping[str, Any], context: Any) -> None:
        record = {
            "run_id": context.run_id, "stage_id": context.stage_id,
            "member_id": context.member_id, "turn_id": context.turn_id,
            "attempt_id": context.attempt_id,
            "request": request, "response": payload,
        }
        line = json.dumps(record, sort_keys=True, default=str) + "\n"
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
