#!/usr/bin/env bash
# Usage: stop_frontier_reference.sh <run_name>
# Sends a clean SIGTERM to frontier_baseline.py (so it prints its summary
# and calls sim.close()), waits briefly, then tears down roslaunch/
# hydra_ros_node/task_server/Xvfb and restores the original frontier_config.yaml.
set -eo pipefail
RUN_NAME="$1"
RUN=/workspace/runs/${RUN_NAME}
ROOT=/workspace/catkin_ws/src/active_semantic_perception
CFG=$ROOT/exploration/config/frontier_config.yaml

source "$RUN/config/pids.txt"
echo "[stop_frontier_reference] stopping frontier_baseline.py (pid $FRONTIER_PID) cleanly"
kill -TERM "$FRONTIER_PID" 2>/dev/null || true
sleep 5
tail -20 "$RUN/logs/frontier_baseline.log"

kill "$XVFB_PID" 2>/dev/null || true
kill "$ROSLAUNCH_PID" 2>/dev/null || true
sleep 2
pkill -9 -f hydra_ros_node 2>/dev/null || true
pkill -9 -f "clio_ros/app/task_server" 2>/dev/null || true
pkill -9 -f frontier_baseline.py 2>/dev/null || true

if [ -f "$RUN/config/frontier_config.original.yaml" ]; then
  cp "$RUN/config/frontier_config.original.yaml" "$CFG"
fi
echo "[stop_frontier_reference] cleanup complete for $RUN_NAME"
ls "$RUN/stages" | sort -n | tail -5
