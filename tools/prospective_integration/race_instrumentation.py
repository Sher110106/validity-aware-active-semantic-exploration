"""Pure instrumentation, zero behavior change: records which ensemble
member's completion finishes first in complete_scene_graph()'s
ProcessPoolExecutor pool.

Real finding (2026-09-21, verified against exploration_pipeline.py and the
pinned llm_completion.py directly): `for future in as_completed(futures)`
yields in COMPLETION order, not submission order, and nothing sorts
`all_generated_files` afterward. execute_planning() then uses
`generated_graphs[0]` -- literally whichever of up to 8 concurrent
ensemble-member completions (across BOTH scene-graph tracks) finished
first, not "ensemble member 0." This makes even official_asp's baseline
navigation decision a race outcome, not fully determined by SEED. This
module only records that race for later analysis; it does not change it.

Multiple worker processes call append() concurrently -- serialized with
flock, same pattern as raw_archive.py."""
from __future__ import annotations

import fcntl
import json
import os
import time
from pathlib import Path
from typing import Union


class RaceInstrumentation:
    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        if self.path.exists() and self.path.is_symlink():
            raise ValueError("refusing symlink instrumentation path")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record_member_finished(self, *, scene_index: int, ensemble_index: int,
                               graph_id: int, result_path) -> None:
        record = {
            "timestamp": time.time(), "scene_index": scene_index,
            "ensemble_index": ensemble_index, "graph_id": graph_id,
            "result_path": str(result_path) if result_path else None,
            "pid": os.getpid(),
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
