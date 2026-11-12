#!/usr/bin/env bash
# Pure launcher - does NOT block or auto-cleanup. Modelled line by line on
# run_frontier_reference.sh; it runs coverage_tour.py (the author-protocol
# reference tour, PREREGISTRATION_PAPER.md 2b) in place of frontier_baseline.py.
# Like the frontier explorer, coverage_tour.py never exits on its own once it
# reaches FINISHED. Watch logs/coverage_tour.log for "Exploration complete"
# (the tour logs the same line as the frontier explorer), then run
# stop_frontier_reference.sh <run_name> unchanged.
#
# Usage: run_coverage_tour.sh <scene_id_path> <scene_number> <run_name> <display_num> <mode> [max_waypoints]
#   mode is a or b. max_waypoints caps the tour for a short dry run (docker exec does
#   not pass the host's environment, so the cap is an argument). Optional, from the
#   container environment: APR_SPACING, APR_ARCHIVE_EVERY (see coverage_tour.py).
# Stop it with stop_coverage_tour.sh <run_name>.
# coverage_tour.py and tour_waypoints.py must already sit in exploration/scripts/.
set -eo pipefail
SCENE_ID="$1"
SCENE_NUMBER="$2"
RUN_NAME="$3"
DISPLAY_NUM="$4"
MODE="$5"
MAX_WAYPOINTS="${6:-}"

ROOT=/workspace/catkin_ws/src/active_semantic_perception
RUN=/workspace/runs/${RUN_NAME}
CFG=$ROOT/exploration/config/frontier_config.yaml

case "$MODE" in
  a|b) ;;
  *) echo "[run_coverage_tour] mode must be a or b, got '$MODE'" >&2; exit 2 ;;
esac
for f in coverage_tour.py tour_waypoints.py; do
  if [ ! -f "$ROOT/exploration/scripts/$f" ]; then
    echo "[run_coverage_tour] missing $ROOT/exploration/scripts/$f" >&2
    exit 2
  fi
done

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
printf "scene_id=%s scene_number=%s mode=%s apr_spacing=%s apr_archive_every=%s apr_max_waypoints=%s\n" \
  "$SCENE_ID" "$SCENE_NUMBER" "$MODE" "${APR_SPACING:-1.5}" "${APR_ARCHIVE_EVERY:-10}" "${MAX_WAYPOINTS:-none}" \
  > "$RUN/config/run_manifest.txt"

# The tour starts at the author's start pose: no jitter.
unset ASP_START_JITTER_SEED
export APR_MODE="$MODE"
export APR_WAYPOINTS_OUT="$RUN/config/waypoints.json"
export APR_SUMMARY_OUT="$RUN/config/tour_summary.json"
if [ -n "$MAX_WAYPOINTS" ]; then export APR_MAX_WAYPOINTS="$MAX_WAYPOINTS"; else unset APR_MAX_WAYPOINTS; fi

source /opt/ros/noetic/setup.bash
source /workspace/catkin_ws/devel/setup.bash
source /workspace/environments/semantic_perception/bin/activate

echo "[run_coverage_tour] starting roslaunch for $RUN_NAME (scene $SCENE_NUMBER, mode $MODE)"
roslaunch clio_ros realsense.launch dataset_name:=realsense_frontier start_visualizer:=false start_rviz:=false \
  > "$RUN/logs/roslaunch.log" 2>&1 &
ROSLAUNCH_PID=$!

sleep 30
echo "[run_coverage_tour] roslaunch presumed ready, starting Xvfb + coverage_tour.py"

Xvfb :${DISPLAY_NUM} -screen 0 1024x768x24 > "$RUN/logs/xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 3

cd "$ROOT/exploration/scripts"
DISPLAY=:${DISPLAY_NUM} python coverage_tour.py > "$RUN/logs/coverage_tour.log" 2>&1 &
FRONTIER_PID=$!  # the tour process; stop_frontier_reference.sh reads this name

# stop_frontier_reference.sh runs "tail -20 logs/frontier_baseline.log" under set -e.
# A missing file would abort it before it kills anything, so link the name to the tour log.
ln -sf coverage_tour.log "$RUN/logs/frontier_baseline.log"
# Write the PIDs now, so a stop during the start-up window still finds them.
echo "ROSLAUNCH_PID=$ROSLAUNCH_PID XVFB_PID=$XVFB_PID FRONTIER_PID=$FRONTIER_PID" > "$RUN/config/pids.txt"

# The tour builds its waypoint list before the keyboard listener starts, so one
# early 's' could be lost. Press until the tour logs that it started.
sleep 20
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  DISPLAY=:${DISPLAY_NUM} xdotool key s || true
  sleep 10
  if grep -q "Starting pipeline" "$RUN/logs/coverage_tour.log" 2>/dev/null; then break; fi
done
echo "[run_coverage_tour] sent 's' keypress, the tour should now be running"
echo "ROSLAUNCH_PID=$ROSLAUNCH_PID XVFB_PID=$XVFB_PID FRONTIER_PID=$FRONTIER_PID" | tee "$RUN/config/pids.txt"
