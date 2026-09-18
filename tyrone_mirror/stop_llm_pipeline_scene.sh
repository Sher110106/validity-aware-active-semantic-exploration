#!/usr/bin/env bash
# Usage: stop_llm_pipeline_scene.sh <run_name>
set -eo pipefail
RUN_NAME="$1"
RUN=/workspace/runs/${RUN_NAME}
ROOT=/workspace/catkin_ws/src/active_semantic_perception
CFG=$ROOT/exploration/config/pipeline_config.yaml

source "$RUN/config/pids.txt"
echo "[stop_llm_pipeline_scene] stopping exploration_pipeline.py (pid $PIPE_PID)"
kill -9 "$PIPE_PID" 2>/dev/null || true
sleep 2

kill "$XVFB_PID" 2>/dev/null || true
kill "$ROSLAUNCH_PID" 2>/dev/null || true
sleep 2
pkill -9 -f hydra_ros_node 2>/dev/null || true
pkill -9 -f "clio_ros/app/task_server" 2>/dev/null || true
pkill -9 -f exploration_pipeline.py 2>/dev/null || true

if [ -f "$RUN/config/pipeline_config.original.yaml" ]; then
  cp "$RUN/config/pipeline_config.original.yaml" "$CFG"
fi
echo "[stop_llm_pipeline_scene] cleanup complete for $RUN_NAME"
ls "$RUN/stages" 2>/dev/null | sort -n | tail -5
cat "$RUN/prompts/_call_counter" 2>/dev/null
