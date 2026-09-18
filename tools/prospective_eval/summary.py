"""Small deterministic summaries for append-only event logs."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


def summarize_jsonl(path: str) -> dict[str, Any]:
    taxonomy: Counter[str] = Counter()
    modes: Counter[str] = Counter()
    stages = 0
    eligible = 0
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            record = json.loads(line)
            taxonomy[str(record.get("taxonomy", "unknown"))] += 1
            modes[str(record.get("controller_mode", "unknown"))] += 1
            stages += 1
            if record.get("passive_navmesh_admissible") is not None:
                eligible += 1
    return {"events": stages, "audited_events": eligible, "taxonomy": dict(taxonomy), "controller_modes": dict(modes)}
