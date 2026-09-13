#!/usr/bin/env python3
"""Evaluate exported checkpoint graphs without ROS or an LLM."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from asp_offline.evaluator import evaluate_run, summarize_metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = evaluate_run(args.run, args.reference)
    payload = {"checkpoints": rows, "summary": summarize_metrics(rows, budget_m=120.0)}
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
