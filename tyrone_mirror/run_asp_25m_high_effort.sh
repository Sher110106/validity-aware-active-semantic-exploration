#!/usr/bin/env bash
set -eo pipefail
ROOT=/workspace/catkin_ws/src/active_semantic_perception
RUN=/workspace/runs/scene00069_seed42_25m_20260914_high_effort_v5
CFG=$ROOT/exploration/config/pipeline_config.yaml
mkdir -p "$RUN/config" "$RUN/logs" "$RUN/prompts"
cp "$CFG" "$RUN/config/pipeline_config.original.yaml"
sed "s#BASE_DIRECTORY: .*#BASE_DIRECTORY: \"$RUN/stages\"#" "$CFG" > "$CFG.tmp"
mv "$CFG.tmp" "$CFG"
cp "$CFG" "$RUN/config/pipeline_config.yaml"
cp "$ROOT/mapping/clio/clio_ros/launch/realsense.launch" "$RUN/config/realsense.launch"
printf "%s\n" "f1ea141b1886d33ab8f4e4b791db4d3c92150b27" > "$RUN/config/commit.txt"
printf "%s\n" "DeepSeek via OpenRouter; 25m final bounded instrumentation; reasoning effort=high, max_tokens=24000, sized call budget for 5 full stages" > "$RUN/config/run_manifest.txt"
source /opt/ros/noetic/setup.bash
source /workspace/catkin_ws/devel/setup.bash
source /workspace/environments/semantic_perception/bin/activate
source /workspace/.openrouter_credentials
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"
export GOOGLE_API_KEY="${OPENROUTER_API_KEY:-}"
export DISPLAY=:106
export ASP_LLM_PROVIDER=openrouter
export ASP_OPENROUTER_MODEL=deepseek/deepseek-v4.1-flash
export ASP_OPENROUTER_REASONING_EFFORT=high
export ASP_OPENROUTER_MAX_TOKENS=24000
export ASP_LLM_LOG_DIR="$RUN/prompts"
export ASP_LLM_MAX_CALLS=1500
Xvfb :106 -screen 0 1024x768x24 >"$RUN/logs/xvfb.log" 2>&1 &
XVFB_PID=$!
cleanup() {
  kill "$XVFB_PID" 2>/dev/null || true
  cp "$RUN/config/pipeline_config.original.yaml" "$CFG"
}
trap cleanup EXIT
cd "$ROOT/exploration/scripts"
python exploration_pipeline.py >"$RUN/logs/exploration_pipeline.log" 2>&1 &
PIPE_PID=$!
sleep 35
DISPLAY=:106 xdotool key s
wait "$PIPE_PID"
