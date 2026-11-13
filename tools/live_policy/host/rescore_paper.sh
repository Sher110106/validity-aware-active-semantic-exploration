#!/usr/bin/env bash
# One command that reruns the paper-scale rescore (PREREGISTRATION_PAPER.md, Amendment 2).
#   bash tools/live_policy/host/rescore_paper.sh [--mode auto|interim|final] [--out-dir DIR] [--no-copy] [--ged-recheck N]
# Reads the host over ssh; starts no GPU job and touches no run folder there.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
cd "$repo"
PYTHONPATH=tools exec .venv_offline/bin/python tools/live_policy/host/rescore_paper.py "$@"
