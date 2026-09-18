#!/usr/bin/env bash
# Pure launcher (does not block) for a bounded LLM-driven exploration run on
# a given scene, for extension-ablation/calibration data collection.
# Starts its own roslaunch (dataset_name:=realsense, the LLM-pipeline's
# established default) since no persistent Terminal 1 is assumed to exist -
# caller must have done a thorough process cleanup first (see DEVIATIONS.md
# #57 for why this matters: a stale rosmaster/segmenter_yoso.py survivor
# causes a real startup race).
#
# Usage: run_llm_pipeline_scene.sh <scene_id> <scene_number> <run_name> \
#          <display_num> <reasoning_effort> <max_tokens> <max_calls> <seed>
set -eo pipefail
SCENE_ID="$1"
SCENE_NUMBER="$2"
RUN_NAME="$3"
DISPLAY_NUM="$4"
REASONING_EFFORT="$5"
MAX_TOKENS="$6"
MAX_CALLS="$7"
SEED="${8:-42}"

ROOT=/workspace/catkin_ws/src/active_semantic_perception
RUN=/workspace/runs/${RUN_NAME}
CFG=$ROOT/exploration/config/pipeline_config.yaml
mkdir -p "$RUN/config" "$RUN/logs" "$RUN/prompts"
cp "$CFG" "$RUN/config/pipeline_config.original.yaml"

python3 - "$CFG" "$SCENE_ID" "$SCENE_NUMBER" "$RUN/stages" "$SEED" <<'PYEOF'
import re, sys
cfg_path, scene_id, scene_number, base_dir, seed = sys.argv[1:6]
text = open(cfg_path).read()
text = re.sub(r'^SCENE_ID: .*$', f'SCENE_ID: "{scene_id}"', text, flags=re.MULTILINE)
text = re.sub(r'^SCENE_NUMBER: .*$', f'SCENE_NUMBER: {scene_number}', text, flags=re.MULTILINE)
text = re.sub(r'^BASE_DIRECTORY: .*$', f'BASE_DIRECTORY: "{base_dir}"', text, flags=re.MULTILINE)
text = re.sub(r'^SEED: .*$', f'SEED: {seed}', text, flags=re.MULTILINE)
open(cfg_path, 'w').write(text)
PYEOF

cp "$CFG" "$RUN/config/pipeline_config.yaml"
printf "%s\n" "f1ea141b1886d33ab8f4e4b791db4d3c92150b27" > "$RUN/config/commit.txt"
printf "DeepSeek via OpenRouter; scene %s seed %s; reasoning effort=%s, max_tokens=%s, call budget=%s\n" \
  "$SCENE_NUMBER" "$SEED" "$REASONING_EFFORT" "$MAX_TOKENS" "$MAX_CALLS" > "$RUN/config/run_manifest.txt"

source /opt/ros/noetic/setup.bash
source /workspace/catkin_ws/devel/setup.bash
source /workspace/environments/semantic_perception/bin/activate
source /workspace/.openrouter_credentials
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"
export GOOGLE_API_KEY="${OPENROUTER_API_KEY:-}"
export DISPLAY=:${DISPLAY_NUM}
export ASP_LLM_PROVIDER=openrouter
export ASP_OPENROUTER_MODEL=deepseek/deepseek-v4.1-flash
# 2026-09-16: pin to DeepInfra's fp8 endpoint (confirmed via OpenRouter's
# /models/.../endpoints as tag "deepinfra/fp8", ~99% uptime) so every future
# run in the matrix uses the same known quantization instead of whichever
# provider auto-routing happens to land on - avoids a quantization-level
# confound across runs. Soft preference, not a hard pin: the shim always
# sets allow_fallbacks=true for a non-empty order list, so a brief DeepInfra
# outage fails over instead of stalling the run - same lesson as the
# reverted hard pin to "Together" (see DEVIATIONS.md).
export ASP_OPENROUTER_PROVIDER_ORDER=deepinfra/fp8
# 2026-09-16: order alone let a fallback land on Relace (fp4), not just
# Morph (also fp8) - confirmed live against the real API. quantizations
# keeps every call, primary or fallback, restricted to fp8.
export ASP_OPENROUTER_QUANTIZATIONS=fp8
export ASP_OPENROUTER_REASONING_EFFORT=${REASONING_EFFORT}
export ASP_OPENROUTER_MAX_TOKENS=${MAX_TOKENS}
export ASP_LLM_LOG_DIR="$RUN/prompts"
export ASP_LLM_MAX_CALLS=${MAX_CALLS}

echo "[run_llm_pipeline_scene] starting roslaunch for $RUN_NAME (scene $SCENE_NUMBER)"
roslaunch clio_ros realsense.launch start_visualizer:=false start_rviz:=false \
  > "$RUN/logs/roslaunch.log" 2>&1 &
ROSLAUNCH_PID=$!

sleep 30
echo "[run_llm_pipeline_scene] roslaunch presumed ready, starting Xvfb + exploration_pipeline.py"

Xvfb :${DISPLAY_NUM} -screen 0 1024x768x24 > "$RUN/logs/xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 3

cd "$ROOT/exploration/scripts"
python exploration_pipeline.py > "$RUN/logs/exploration_pipeline.log" 2>&1 &
PIPE_PID=$!

sleep 20
DISPLAY=:${DISPLAY_NUM} xdotool key s
echo "[run_llm_pipeline_scene] sent 's' keypress"
echo "ROSLAUNCH_PID=$ROSLAUNCH_PID XVFB_PID=$XVFB_PID PIPE_PID=$PIPE_PID" | tee "$RUN/config/pids.txt"
