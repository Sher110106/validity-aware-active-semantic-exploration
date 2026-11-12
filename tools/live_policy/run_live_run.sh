#!/usr/bin/env bash
# Launcher for one run of the 2026-10-28 live campaign (DeepSeek 1017 on
# DeepInfra fp8, hard-pinned, metered, with a live completion policy).
# Same shape as /workspace/run_llm_pipeline_scene.sh; differences:
#   - model deepseek/deepseek-v4.1-flash-1017, no provider fallback
#   - per-call usage.jsonl and a per-run cost cap (shim env vars)
#   - 600 s request timeout and 15 s retry backoff
#   - runs tools/live_policy/run_pipeline_with_policy.py with ASP_LIVE_POLICY
# Does not block. The caller (live_runner.py) cleans up processes first and
# stops the run.
#
# Usage: run_live_run.sh <scene_id> <scene_number> <run_name> <display> \
#          <policy> <seed> <max_cost_usd> [no_llm_delay_schedule]
# no_llm_delay_schedule: comma list of seconds for stages 0, 1, ...; the last
# value repeats (ASP_LIVE_NO_LLM_DELAY_SCHEDULE).
set -eo pipefail
SCENE_ID="$1"
SCENE_NUMBER="$2"
RUN_NAME="$3"
DISPLAY_NUM="$4"
POLICY="$5"
SEED="$6"
MAX_COST_USD="$7"
NO_LLM_DELAY_SCHEDULE="${8:-0}"

MODEL=deepseek/deepseek-v4.1-flash-1017
REASONING_EFFORT=low
MAX_TOKENS=16000
MAX_CALLS=3000

ROOT=/workspace/catkin_ws/src/active_semantic_perception
HERE=/workspace/tools/live_policy
RUN=/workspace/runs/live_campaign/${RUN_NAME}
CFG=$ROOT/exploration/config/pipeline_config.yaml
mkdir -p "$RUN/config" "$RUN/logs" "$RUN/prompts"
cp "$CFG" "$RUN/config/pipeline_config.original.yaml"

python3 - "$CFG" "$SCENE_ID" "$SCENE_NUMBER" "$RUN/stages" "$SEED" "$MODEL" <<'PYEOF'
import re, sys
cfg_path, scene_id, scene_number, base_dir, seed, model = sys.argv[1:7]
text = open(cfg_path).read()
text = re.sub(r'^SCENE_ID: .*$', f'SCENE_ID: "{scene_id}"', text, flags=re.MULTILINE)
text = re.sub(r'^SCENE_NUMBER: .*$', f'SCENE_NUMBER: {scene_number}', text, flags=re.MULTILINE)
text = re.sub(r'^BASE_DIRECTORY: .*$', f'BASE_DIRECTORY: "{base_dir}"', text, flags=re.MULTILINE)
text = re.sub(r'^SEED: .*$', f'SEED: {seed}', text, flags=re.MULTILINE)
text = re.sub(r'^LLM_MODEL_NAME: .*$', f'LLM_MODEL_NAME: "openrouter:{model}"', text, flags=re.MULTILINE)
open(cfg_path, 'w').write(text)
PYEOF

cp "$CFG" "$RUN/config/pipeline_config.yaml"
printf "%s\n" "f1ea141b1886d33ab8f4e4b791db4d3c92150b27" > "$RUN/config/commit.txt"
{
  printf "live campaign 2026-10-28; scene %s seed %s; policy=%s; no_llm_delay_schedule=%s\n" "$SCENE_NUMBER" "$SEED" "$POLICY" "$NO_LLM_DELAY_SCHEDULE"
  printf "ASP_DSG_QUIESCENT_S=%s ASP_DSG_QUIESCENT_MAX_S=%s\n" "${ASP_DSG_QUIESCENT_S:-}" "${ASP_DSG_QUIESCENT_MAX_S:-}"
  printf "model=%s provider=deepinfra/fp8 allow_fallbacks=0 reasoning effort=%s, max_tokens=%s, call budget=%s, max_cost_usd=%s\n" \
    "$MODEL" "$REASONING_EFFORT" "$MAX_TOKENS" "$MAX_CALLS" "$MAX_COST_USD"
  md5sum /workspace/tools/llm_openrouter/_asp_openrouter_shim.py "$HERE/live_policy.py" \
    "$HERE/run_pipeline_with_policy.py" "$HERE/run_live_run.sh" "$HERE/placebo_calibration.json" \
    /workspace/environments/semantic_perception/lib/python3.9/site-packages/_asp_openrouter_shim.py \
    "$ROOT/exploration/scripts/exploration_pipeline.py" \
    "$ROOT/exploration/scripts/llm_completion.py" "$ROOT/exploration/scripts/calculate_uncertainty.py"
} > "$RUN/config/run_manifest.txt"

source /opt/ros/noetic/setup.bash
source /workspace/catkin_ws/devel/setup.bash
source /workspace/environments/semantic_perception/bin/activate
set +x
source /workspace/.openrouter_credentials
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"
export GOOGLE_API_KEY="${OPENROUTER_API_KEY:-}"
export DISPLAY=:${DISPLAY_NUM}
export ASP_LLM_PROVIDER=openrouter
export ASP_OPENROUTER_MODEL=$MODEL
export ASP_OPENROUTER_PROVIDER_ORDER=deepinfra/fp8
export ASP_OPENROUTER_QUANTIZATIONS=fp8
export ASP_OPENROUTER_ALLOW_FALLBACKS=0
export ASP_OPENROUTER_TIMEOUT_S=600
export ASP_OPENROUTER_TOTAL_TIMEOUT_S=900
export ASP_OPENROUTER_RETRY_BACKOFF_S=15
export ASP_OPENROUTER_MAX_COST_USD=${MAX_COST_USD}
export ASP_OPENROUTER_REASONING_EFFORT=${REASONING_EFFORT}
export ASP_OPENROUTER_MAX_TOKENS=${MAX_TOKENS}
export ASP_LLM_LOG_DIR="$RUN/prompts"
export ASP_LLM_MAX_CALLS=${MAX_CALLS}
export ASP_LIVE_POLICY=${POLICY}
export ASP_LIVE_NO_LLM_DELAY_SCHEDULE=${NO_LLM_DELAY_SCHEDULE}

echo "[run_live_run] starting roslaunch for $RUN_NAME (scene $SCENE_NUMBER, policy $POLICY)"
roslaunch clio_ros realsense.launch start_visualizer:=false start_rviz:=false \
  > "$RUN/logs/roslaunch.log" 2>&1 &
ROSLAUNCH_PID=$!

sleep 30
echo "[run_live_run] roslaunch presumed ready, starting Xvfb + pipeline"

Xvfb :${DISPLAY_NUM} -screen 0 1024x768x24 > "$RUN/logs/xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 3

cd "$ROOT/exploration/scripts"
python "$HERE/run_pipeline_with_policy.py" > "$RUN/logs/exploration_pipeline.log" 2>&1 &
PIPE_PID=$!

sleep 20
DISPLAY=:${DISPLAY_NUM} xdotool key s
echo "[run_live_run] sent 's' keypress"
echo "ROSLAUNCH_PID=$ROSLAUNCH_PID XVFB_PID=$XVFB_PID PIPE_PID=$PIPE_PID" | tee "$RUN/config/pids.txt"
