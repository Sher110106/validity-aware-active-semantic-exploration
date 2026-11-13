#!/bin/bash
# The Claude replays of PREREGISTRATION_SEMANTIC.md §12 (M4): Haiku 5.5 and Opus 5.5 on the 44 frame
# rows, 4 members each, in the four rounds of semantic/sample_frame.txt, Haiku first in each round.
# The key comes from the environment (ANTHROPIC_API_KEY) and is never printed. Safe to run again:
# finished members are skipped.
set -u
cd "$(dirname "$0")/../../.." || exit 1
IN=${REPLAY_INPUTS:-/Users/sher/project/cvp/replay_inputs/frame_inputs}
OUT=${REPLAY_OUT:-/Users/sher/project/cvp/replay_outputs/m4}
mkdir -p "$OUT"
env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_CUSTOM_HEADERS \
  caffeinate -i .venv_offline/bin/python tools/llm_anthropic/claude_static.py "$IN" "$OUT" \
  --models claude-haiku-5-5,claude-opus-5-5 --effort medium --members 4 \
  --order tools/live_policy/semantic/sample_frame.txt --resume --prewarm --concurrency 4 \
  --cap-model claude-opus-5-5=280 --cap-model claude-haiku-5-5=20 --cap-campaign 300 \
  --reserve claude-opus-5-5=1.5 --reserve claude-haiku-5-5=0.35 \
  --admit claude-opus-5-5=0.25 --admit claude-haiku-5-5=0.01 "$@" 2>&1 | grep -v "sk-ant"
