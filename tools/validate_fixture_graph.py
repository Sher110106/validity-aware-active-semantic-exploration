#!/usr/bin/env python3
"""Validate one cached ASP completion against an observed graph."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from asp_offline.validator import validate_completion


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("completion", type=Path)
    parser.add_argument("--observed", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    completion = args.completion.read_text()
    observed = json.loads(args.observed.read_text())
    result = validate_completion(completion, observed)
    payload = result.as_dict()
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text + "\n")
    else:
        print(text)
    return 0 if result.accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
