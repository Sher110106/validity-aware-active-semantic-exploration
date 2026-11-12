#!/usr/bin/env bash
# Usage: stop_coverage_tour.sh <run_name>
# stop_frontier_reference.sh (unchanged) stops the tour by its PID, tears down the
# mapper and restores frontier_config.yaml. Its pkill backstop names
# frontier_baseline.py only, so force-kill a tour process that hangs on exit here.
RUN_NAME="$1"
bash /workspace/stop_frontier_reference.sh "$RUN_NAME"
sleep 2
pkill -9 -f "python coverage_tour.py" 2>/dev/null || true
