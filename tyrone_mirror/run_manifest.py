#!/usr/bin/env python3
"""Content-hash manifest for one scored run (REVIEW_2026-09-14.md Step 1.5:
"Create a single run manifest schema and use it for every future run").

Hashes the inputs and outputs a reported number actually depends on, so a
later reader can tell whether "the same" evaluator/config/reference graph
produced it, without re-trusting a path or a date in prose. This does not
replace DEVIATIONS.md's narrative log - it is the machine-checkable
complement to it.

Usage:
    python3 run_manifest.py --run <run_dir> \
        --config <pipeline_config.yaml> --commit <commit.txt> \
        --reference <ground_truth.yaml> \
        --evaluator-src <dir_or_file> [--evaluator-src <dir_or_file> ...] \
        --result <result.json> [--result <result.json> ...] \
        --out <manifest.json>

Every path argument is optional except --run and --out - fill in whatever
exists for that run. Missing files are recorded as null, not skipped
silently, so a reader can tell "not hashed" from "hashed and matches."
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_tree(path: Path) -> Dict[str, str]:
    """Hash every file under a directory, keyed by path relative to it."""
    out = {}
    for p in sorted(path.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            out[str(p.relative_to(path))] = _sha256_file(p)
    return out


def _hash_path(label: str, path: Optional[Path]) -> Dict[str, object]:
    if path is None:
        return {"path": None, "sha256": None, "present": False}
    if not path.exists():
        return {"path": str(path), "sha256": None, "present": False}
    if path.is_dir():
        return {"path": str(path), "present": True, "files": _sha256_tree(path)}
    return {"path": str(path), "sha256": _sha256_file(path), "present": True}


def build_manifest(
    run_dir: Path,
    *,
    config: Optional[Path] = None,
    commit: Optional[Path] = None,
    reference: Optional[Path] = None,
    evaluator_sources: Optional[List[Path]] = None,
    results: Optional[List[Path]] = None,
) -> Dict[str, object]:
    manifest = {
        "schema": "asp_run_manifest_v1",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_dir": str(run_dir),
        "pipeline_config": _hash_path("pipeline_config", config),
        "commit": _hash_path("commit", commit),
        "reference_graph": _hash_path("reference_graph", reference),
        "evaluator_sources": {str(p): _hash_path("evaluator_source", p) for p in (evaluator_sources or [])},
        "results": {str(p): _hash_path("result", p) for p in (results or [])},
    }
    commit_path = commit
    if commit_path and commit_path.exists():
        manifest["commit_text"] = commit_path.read_text().strip()
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--commit", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--evaluator-src", action="append", type=Path, default=[])
    parser.add_argument("--result", action="append", type=Path, default=[])
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    manifest = build_manifest(
        args.run,
        config=args.config,
        commit=args.commit,
        reference=args.reference,
        evaluator_sources=args.evaluator_src,
        results=args.result,
    )
    args.out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Manifest written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
