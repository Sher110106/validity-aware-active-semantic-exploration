"""Is a pass of the M2 study complete? One check, used by factorial.py (before it writes PASS_COMPLETE) and by
summarise_factorial.py (before it reads a pass). Standard library only.

A pass folder holds factorial_meta.json (n_jobs, arms), factorial_stages.jsonl and, when complete, PASS_COMPLETE.
A pass is complete when: the jsonl holds exactly n_jobs rows, one per (run, stage); no row is an error or a drop;
every arm the pass was asked for is present on every row.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import List

MARKER = "PASS_COMPLETE"
STAGES = "factorial_stages.jsonl"
META = "factorial_meta.json"


class IncompletePass(Exception):
    """Raised with a message that lists what is wrong."""


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def problems(folder) -> List[str]:
    """Everything wrong with the pass in `folder`; an empty list means complete."""
    folder = Path(folder)
    out: List[str] = []
    meta_p, jsonl_p = folder / META, folder / STAGES
    if not meta_p.exists():
        return [f"{meta_p} is missing"]
    if not jsonl_p.exists():
        return [f"{jsonl_p} is missing"]
    meta = json.loads(meta_p.read_text())
    want_rows, want_arms = int(meta["n_jobs"]), list(meta["arms"])
    rows, bad_lines = [], 0
    for line in open(jsonl_p):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            bad_lines += 1          # a truncated last line
    if bad_lines:
        out.append(f"{bad_lines} unreadable line(s) in {jsonl_p.name}")
    if len(rows) != want_rows:
        out.append(f"{jsonl_p.name} holds {len(rows)} rows, {META} says {want_rows}")
    keys = [(r.get("run"), r.get("stage")) for r in rows]
    if len(set(keys)) != len(keys):
        out.append(f"{len(keys) - len(set(keys))} duplicate (run, stage) row(s)")
    errs = [f"{r.get('run')}:{r.get('stage')}" for r in rows if "error" in r]
    drops = [f"{r.get('run')}:{r.get('stage')}" for r in rows if "drop" in r]
    if errs:
        out.append(f"{len(errs)} error row(s), first: {errs[:5]}")
    if drops:
        out.append(f"{len(drops)} drop row(s), first: {drops[:5]}")
    for r in rows:
        if "error" in r or "drop" in r:
            continue
        missing = [a for a in want_arms if a not in (r.get("arms") or {})]
        if missing:
            out.append(f"row {r.get('run')}:{r.get('stage')} lacks arm(s) {missing}")
            if len(out) > 20:
                break
    return out


def require_complete(folder) -> None:
    """Raise IncompletePass unless the pass is complete, its marker exists, and the marker's hash still matches."""
    folder = Path(folder)
    p = problems(folder)
    marker = folder / MARKER
    if not marker.exists():
        p.append(f"{marker} does not exist (the pass was not completed)")
    else:
        m = json.loads(marker.read_text())
        if (folder / STAGES).exists() and m.get("sha256") != sha256_file(folder / STAGES):
            p.append(f"{STAGES} changed after {MARKER} was written")
    if p:
        raise IncompletePass(f"pass {folder} is not complete:\n  " + "\n  ".join(p))


def write_marker(folder) -> None:
    folder = Path(folder)
    p = problems(folder)
    if p:
        raise IncompletePass(f"pass {folder} is not complete:\n  " + "\n  ".join(p))
    meta = json.loads((folder / META).read_text())
    (folder / MARKER).write_text(json.dumps({"n_rows": int(meta["n_jobs"]), "arms": meta["arms"],
                                             "sha256": sha256_file(folder / STAGES)}, indent=1))
