"""Offline ledger and dry-run probe commands."""
from __future__ import annotations

import argparse
import json

from .config import MODEL_ID, PROBE_CAP_MICROUSD, THINKING_LEVEL
from .ledger import Ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gemini-campaign")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("summary", "export", "checksum"):
        command = subcommands.add_parser(name)
        command.add_argument("db")
    probe = subcommands.add_parser("probe")
    probe.add_argument("--paid-enable", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "probe":
        if args.paid_enable:
            raise SystemExit("paid probes are disabled until direct runtime transport is integrated")
        print(json.dumps({
            "dry_run": True,
            "paid_invocation": False,
            "model": MODEL_ID,
            "thinking_level": THINKING_LEVEL,
            "cap_microusd": PROBE_CAP_MICROUSD,
            "tests": ["model", "thinking", "function_calling", "structured_output", "truncation", "usage"],
        }, sort_keys=True))
        return 0

    ledger = Ledger(args.db)
    try:
        print(json.dumps(getattr(ledger, args.command)(), sort_keys=True, default=str))
    finally:
        ledger.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
