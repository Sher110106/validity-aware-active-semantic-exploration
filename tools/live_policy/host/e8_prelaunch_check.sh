#!/bin/bash
# Checks to make by hand before each launch of Amendment 3's runs (PREREGISTRATION_PAPER.md,
# Amendment 3 and its Note, A3.1). Read-only: it starts, stops and writes nothing.
#
# Usage, on the host:  bash e8_prelaunch_check.sh <run name>
#   e.g. bash e8_prelaunch_check.sh dryrun_e8_00853_s42_official_5m
#        bash e8_prelaunch_check.sh e8_00853_s42_official_105m
# Exit status 0 only if every check passes.

set -u
RUN_NAME="${1:?give the name of the run to be launched}"
WS="${ASP_WS:-$HOME/active-semantic-perception-workspace}"
CAMPAIGN="$WS/runs/live_campaign"
CONTAINER="${ASP_CONTAINER:-asp-noetic}"
QUEUE_UNIT="${PAPER_QUEUE_UNIT:-paper-queue-rerun3.scope}"
MIN_GPU_MB=12000
MIN_MEM_GB=60
MIN_DISK_GB=20
SCRIPTS="$WS/catkin_ws/src/active_semantic_perception/exploration/scripts"

fails=0
ok()   { printf 'ok    %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; fails=$((fails+1)); }
check_prefix() {  # <label> <command that prints a hash> <expected prefix>
  local got; got="$($2 "$3" 2>/dev/null | cut -c1-8)"
  if [ "$got" = "$4" ]; then ok "$1 is $4…"; else bad "$1 is ${got:-missing}…, expected $4…"; fi
}

# 1. The rerun queue has ended. Waiting is not ended: once the GPU frees it would start a run
#    in the same container.
state="$(systemctl --user is-active "$QUEUE_UNIT" 2>/dev/null)"
if [ "$state" = "active" ] || [ "$state" = "activating" ]; then bad "the rerun queue ($QUEUE_UNIT) is $state"
elif pgrep -u "$(id -u)" -f 'paper_queue\.sh' >/dev/null; then bad "a paper_queue.sh process is still running"
else ok "the rerun queue has ended"; fi

# 2. Nothing but its first process runs in the container (the runner's clean-up kills the rest).
#    Ended processes not yet reaped ("<defunct>") hold nothing and are only counted.
all="$(docker exec "$CONTAINER" ps -eo pid=,args= 2>/dev/null | grep -v -E '^ *1 |ps -eo pid=,args=' )"
procs="$(printf '%s\n' "$all" | grep -v '<defunct>' | grep -v '^$')"
dead="$(printf '%s\n' "$all" | grep -c '<defunct>')"
if [ -z "$procs" ]; then ok "the container holds only its first process ($dead ended, unreaped)"
else bad "the container holds other processes:"; printf '%s\n' "$procs" | head -8 | sed 's/^/        /'; fi

# 3. GPU memory, host memory, disk.
gpu="$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1 | tr -d ' ')"
if [ "${gpu:-0}" -ge "$MIN_GPU_MB" ]; then ok "GPU memory free: $gpu MiB"; else bad "GPU memory free: ${gpu:-?} MiB, need $MIN_GPU_MB"; fi
mem="$(free -g | awk '/^Mem:/{print $7}')"
if [ "${mem:-0}" -ge "$MIN_MEM_GB" ]; then ok "host memory free: $mem GB"; else bad "host memory free: ${mem:-?} GB, need $MIN_MEM_GB"; fi
disk="$(df -BG --output=avail "$WS" | tail -1 | tr -dc '0-9')"
if [ "${disk:-0}" -ge "$MIN_DISK_GB" ]; then ok "disk free: $disk GB"; else bad "disk free: ${disk:-?} GB, need $MIN_DISK_GB"; fi

# 4. The files are those the amendment and its Note name.
check_prefix "live_policy.py sha256"       sha256sum "$WS/tools/live_policy/live_policy.py"   6e4710cf
check_prefix "run_live_run.sh sha256"      sha256sum "$WS/tools/live_policy/run_live_run.sh"  25cfe606
check_prefix "live_runner.py sha256"       sha256sum "$WS/tools/live_policy/live_runner.py"   940be66b
check_prefix "exploration_pipeline.py md5" md5sum    "$SCRIPTS/exploration_pipeline.py"       223ed036
check_prefix "llm_completion.py md5"       md5sum    "$SCRIPTS/llm_completion.py"             dc70801e
check_prefix "calculate_uncertainty.py md5" md5sum   "$SCRIPTS/calculate_uncertainty.py"      9cec96c6

# 5. The campaign folder: no control file, no runner at work, and no folder of this name.
ctl="$(ls -a "$CAMPAIGN" 2>/dev/null | grep -E '^(PAUSE|STOP)|^\.active_' )"
if [ -z "$ctl" ]; then ok "no PAUSE, STOP or .active file in the campaign folder"; else bad "control files present: $(echo $ctl)"; fi
if pgrep -u "$(id -u)" -f 'live_runner\.py' >/dev/null; then bad "a live_runner.py process is running"; else ok "no runner is running"; fi
if [ -e "$CAMPAIGN/$RUN_NAME" ]; then bad "a folder named $RUN_NAME exists already"; else ok "no folder named $RUN_NAME yet"; fi

# 6. The quiet-wait option stays unset.
if [ -n "${ASP_DSG_QUIESCENT_S:-}${ASP_DSG_QUIESCENT_MAX_S:-}" ]; then bad "the quiet-wait variables are set in this shell"; else ok "the quiet-wait variables are unset"; fi

echo
if [ "$fails" -eq 0 ]; then echo "READY: every check passes for $RUN_NAME ($(date '+%Y-%m-%d %H:%M:%S %Z'))"; exit 0
else echo "NOT READY: $fails check(s) failed for $RUN_NAME ($(date '+%Y-%m-%d %H:%M:%S %Z'))"; exit 1; fi
