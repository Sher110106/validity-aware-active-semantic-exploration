#!/usr/bin/env python3
"""Replay author YAML completions through the offline validator.

This is the bridge used by the Linux cache audit: it reads the author's
``habitat_scene_graph_new_graph_*.yaml`` files, converts them to the canonical
offline schema, validates the whole ensemble, and optionally attaches
post-hoc labels from a reference graph. It never calls an LLM or changes the
source artifacts.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from asp_offline.author_io import load_author_graph
from asp_offline.validator import ValidationConfig, label_against_reference, validate_ensemble


def replay(completions_dir: Path, observed_path: Path, reference_path: Optional[Path] = None, expected_count: Optional[int] = None) -> Dict[str, Any]:
    completion_paths = sorted(completions_dir.glob("habitat_scene_graph_new_graph_*.yaml"))
    completions = [load_author_graph(path) for path in completion_paths]
    observed = load_author_graph(observed_path, observed=True)
    reference = load_author_graph(reference_path, observed=True) if reference_path else None
    results = validate_ensemble(completions, observed, ValidationConfig(allow_parsed_mapping=True))

    payload_results: List[Dict[str, Any]] = []
    for index, result in enumerate(results):
        payload = result.as_dict()
        if index < len(completions) and reference is not None:
            payload["issues"] = [issue.as_dict() for issue in label_against_reference(completions[index], result.issues, reference)]
        if index < len(completion_paths):
            payload["source"] = str(completion_paths[index])
        else:
            payload["source"] = "ensemble_fallback"
        payload_results.append(payload)

    issue_counts = Counter(issue.code for result in results for issue in result.issues)
    return {
        "observed": str(observed_path),
        "reference": str(reference_path) if reference_path else None,
        "completion_count": len(completions),
        "expected_count": expected_count,
        "missing_completion_count": max(0, expected_count - len(completions)) if expected_count is not None else None,
        "accepted_count": sum(result.accepted for result in results),
        "rejected_count": sum(result.rejected for result in results),
        "removed_node_count": sum(len(result.removed_nodes) for result in results),
        "issue_counts": dict(sorted(issue_counts.items())),
        "results": payload_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--completions-dir", required=True, type=Path)
    parser.add_argument("--observed", required=True, type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = replay(args.completions_dir, args.observed, args.reference, args.expected_count)
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
