#!/usr/bin/env bash
# run_frontier_seed.sh <scene_id_path> <scene_number> <run_name> <display_num> <jitter_seed>
# run_frontier_reference.sh plus ASP_START_JITTER_SEED (PREREGISTRATION_FRONTIER_SEEDS.md).
set -eo pipefail
export ASP_START_JITTER_SEED="$5"
exec bash /workspace/run_frontier_reference.sh "$1" "$2" "$3" "$4"
