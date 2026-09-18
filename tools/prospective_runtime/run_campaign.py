from __future__ import annotations

import argparse
from pathlib import Path
from .manifest import RuntimeManifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Prospective runtime entrypoint (dry-run only)")
    parser.add_argument("manifest")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--approved-hashes")
    parser.add_argument("--credential-file")
    parser.add_argument("--ledger")
    parser.add_argument("--attempt-dir")
    parser.add_argument("--broker-contract")
    parser.add_argument("--campaign-contract")
    args = parser.parse_args()
    manifest = RuntimeManifest.load(args.manifest)
    if args.live:
        controls = (args.approved_hashes, args.credential_file, args.ledger, args.attempt_dir,
                    args.broker_contract, args.campaign_contract)
        if any(value is None for value in controls):
            raise SystemExit("live mode requires approved hashes, credential file, ledger, isolated attempt directory, and both contracts")
        credential = Path(args.credential_file)
        if not credential.is_file() or credential.stat().st_mode & 0o077:
            raise SystemExit("credential file must exist with owner-only permissions")
        if not Path(args.attempt_dir).is_absolute() or not Path(args.ledger).is_absolute():
            raise SystemExit("ledger and attempt directory must be absolute isolated paths")
        raise SystemExit("refusing live mode: broker/campaign integration contracts are not audited")
    manifest.validate()
    print("DRY-RUN: no Habitat, ROS, network, or paid campaign operation requested")
    return 0

if __name__ == "__main__": raise SystemExit(main())
