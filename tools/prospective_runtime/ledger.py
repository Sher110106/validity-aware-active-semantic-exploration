from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Union


class AppendOnlyLedger:
    """JSONL ledger with a hash chain; values are deliberately redaction-safe."""

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.previous = self._last_hash()

    def _last_hash(self) -> str:
        if not self.path.exists() or not self.path.stat().st_size:
            return "0" * 64
        last = self.path.read_text().splitlines()[-1]
        return str(json.loads(last).get("hash", "0" * 64))

    def append(self, event: str, data: Mapping[str, Any]) -> str:
        if not event or not isinstance(data, Mapping):
            raise ValueError("event and mapping data are required")
        safe = {"event": event, "data": dict(data), "previous": self.previous}
        encoded = json.dumps(safe, sort_keys=True, separators=(",", ":")).encode()
        current = hashlib.sha256(encoded).hexdigest()
        record = dict(safe, hash=current)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        self.previous = current
        return current

    def verify(self) -> bool:
        previous = "0" * 64
        if not self.path.exists():
            return True
        for line in self.path.read_text().splitlines():
            record = json.loads(line)
            if record.get("previous") != previous:
                return False
            unsigned = {k: record[k] for k in ("event", "data", "previous")}
            if hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest() != record.get("hash"):
                return False
            previous = record["hash"]
        return True
