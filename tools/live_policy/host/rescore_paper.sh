#!/usr/bin/env bash
# One command that reruns the paper-scale rescore (PREREGISTRATION_PAPER.md, Amendment 2).
#   bash tools/live_policy/host/rescore_paper.sh [--mode auto|interim|final] [--out-dir DIR] [--no-copy] [--ged-recheck N]
# Reads the host over ssh; starts no GPU job and touches no run folder there.
# It finds the November runs (Amendment 3, e8_...) and the control runs (Amendment 5, e9_...) by name in
# runs/live_campaign/ on the host. The filing of 11-18 used:
#   bash tools/live_policy/host/rescore_paper.sh --mode final \
#     --nov-also-stopped e8_00853_s43_official_105m=22 --nov-also-without e8_00853_s43_official_105m
# The same command files the control arms once their folders exist; no option picks lengths, references or runs.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
cd "$repo"
PYTHONPATH=tools exec .venv_offline/bin/python tools/live_policy/host/rescore_paper.py "$@"
