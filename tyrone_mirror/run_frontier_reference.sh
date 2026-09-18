#!/usr/bin/env bash
# Pure launcher - does NOT block or auto-cleanup. frontier_baseline.py never
# exits on its own after reaching FINISHED state (confirmed by reading
# run_pipeline() directly: FINISHED just loops sleeping 1s until an external
# SIGINT/SIGTERM or the 'Esc' keypress sets stop_requested). Detect
# completion by watching logs/frontier_baseline.log for "Exploration
# complete. No more frontiers found. Stopping." then run
# stop_frontier_reference.sh to shut everything down cleanly.
#
# Usage: run_frontier_reference.sh <scene_id_path> <scene_number> <run_name> <display_num>
set -eo pipefail
SCENE_ID="$1"
SCENE_NUMBER="$2"
RUN_NAME="$3"
DISPLAY_NUM="$4"

ROOT=/workspace/catkin_ws/src/active_semantic_perception
RUN=/workspace/runs/${RUN_NAME}
CFG=$ROOT/exploration/config/frontier_config.yaml
mkdir -p "$RUN/logs" "$RUN/stages" "$RUN/config"
cp "$CFG" "$RUN/config/frontier_config.original.yaml"

python3 - "$CFG" "$SCENE_ID" "$SCENE_NUMBER" "$RUN/stages" <<'PYEOF'
import re, sys
cfg_path, scene_id, scene_number, base_dir = sys.argv[1:5]
text = open(cfg_path).read()
text = re.sub(r'^SCENE_ID: .*$', f'SCENE_ID: "{scene_id}"', text, flags=re.MULTILINE)
text = re.sub(r'^SCENE_NUMBER: .*$', f'SCENE_NUMBER: {scene_number}', text, flags=re.MULTILINE)
text = re.sub(r"^BASE_DIRECTORY: .*$", f"BASE_DIRECTORY: '{base_dir}'", text, flags=re.MULTILINE)
open(cfg_path, 'w').write(text)
PYEOF

cp "$CFG" "$RUN/config/frontier_config.yaml"
printf "%s\n" "f1ea141b1886d33ab8f4e4b791db4d3c92150b27" > "$RUN/config/commit.txt"
printf "scene_id=%s scene_number=%s\n" "$SCENE_ID" "$SCENE_NUMBER" > "$RUN/config/run_manifest.txt"

source /opt/ros/noetic/setup.bash
source /workspace/catkin_ws/devel/setup.bash
source /workspace/environments/semantic_perception/bin/activate

echo "[run_frontier_reference] starting roslaunch for $RUN_NAME (scene $SCENE_NUMBER)"
roslaunch clio_ros realsense.launch dataset_name:=realsense_frontier start_visualizer:=false start_rviz:=false \
  > "$RUN/logs/roslaunch.log" 2>&1 &
ROSLAUNCH_PID=$!

sleep 30
echo "[run_frontier_reference] roslaunch presumed ready, starting Xvfb + frontier_baseline.py"

Xvfb :${DISPLAY_NUM} -screen 0 1024x768x24 > "$RUN/logs/xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 3

cd "$ROOT/exploration/scripts"
DISPLAY=:${DISPLAY_NUM} python frontier_baseline.py > "$RUN/logs/frontier_baseline.log" 2>&1 &
FRONTIER_PID=$!

sleep 20
DISPLAY=:${DISPLAY_NUM} xdotool key s
echo "[run_frontier_reference] sent 's' keypress, exploration should now be running"
echo "ROSLAUNCH_PID=$ROSLAUNCH_PID XVFB_PID=$XVFB_PID FRONTIER_PID=$FRONTIER_PID" | tee "$RUN/config/pids.txt"
