#!/bin/bash
# e9_queue.sh <job> [<job> ...]     job = <run name>:<policy>:<seed>:<target metres>
#
# Runs the no-LLM control runs of PREREGISTRATION_PAPER.md, Amendment 5, one at a time, with no
# help from outside the host. For each job, in the order given:
#   1. wait until the pre-launch checks pass twice, five minutes apart (e8_prelaunch_check.sh);
#   2. start live_runner.py on a queue file holding that one run;
#   3. watch it every 30 s and ask the runner to stop it (STOP_<container>) when its roslaunch.log
#      shows an "out of memory" line or a line saying nvblox_node has died, or when two readings
#      of free host memory 15 s apart are both under 20 GB (A5.3);
#   4. when the runner has ended, compress the run's raw graph files (compress_old_dsg.sh).
# A job whose checks have not passed after E9_WAIT_MAX_S seconds ends the queue: nothing later starts.
#
# Usage, on the host, from a fresh login:
#   systemd-run --user --scope --unit=e9-queue-<stamp> bash e9_queue.sh <job> ...
#   bash e9_queue.sh --print <job> ...      prints each job's queue file and changes nothing
#
# The runner kills every process in its container but the first before and after each run, so
# nothing else may share that container (the Gemini replay runs in a container of its own).

set -u
PRINT=0; [ "${1:-}" = "--print" ] && { PRINT=1; shift; }
[ $# -ge 1 ] || { echo "give at least one job: <run name>:<policy>:<seed>:<target metres>"; exit 2; }
HERE="$(cd "$(dirname "$0")" && pwd)"
WS="${ASP_WS:-$HOME/active-semantic-perception-workspace}"
CAMPAIGN="$WS/runs/live_campaign"
CONTAINER="${ASP_CONTAINER:-asp-noetic}"
SCENE=00853
DISPLAY_NO=99
CAMPAIGN_CAP=25
# Amendment 5, A5.2: the per-stage median of llm_wait_s over the three official_nov runs; the last value repeats.
SCHEDULE="127,171,182,175,176,287,355,342,318,259,301,232,288,275,259,308,274,407,373,366,324,385,384,420,361,429,439"
WAIT_MAX_S="${E9_WAIT_MAX_S:-172800}"
LOG="$CAMPAIGN/e9_queue.log"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }
mem_gb() { awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo; }
queue_json() {  # name policy seed target
  printf '{"runs": [{"name": "%s", "scene": "%s", "seed": %s, "policy": "%s", "target_m": %s, "max_hours": 12, "max_cost_usd": 0.0, "no_llm_delay_schedule": "%s"}]}\n' \
    "$1" "$SCENE" "$3" "$2" "$4" "$SCHEDULE"
}

for job in "$@"; do
  IFS=: read -r name policy seed target <<< "$job"
  case "$policy" in placebo|observed_only) ;; *) echo "REFUSED: $job: the policy must be placebo or observed_only"; exit 2 ;; esac
  case "$name" in e9_${SCENE}_s${seed}_${policy}_${target}m|dryrun_e9_${SCENE}_s${seed}_${policy}_${target}m|e9_${SCENE}_s${seed}_${policy}_${target}m_relaunch1) ;;
    *) echo "REFUSED: $job: the name does not match its policy, seed and target"; exit 2 ;; esac
done
if [ "$PRINT" = 1 ]; then
  for job in "$@"; do IFS=: read -r name policy seed target <<< "$job"; echo "$CAMPAIGN/queue_$name.json:"; queue_json "$name" "$policy" "$seed" "$target"; done
  exit 0
fi

log "queue started with $# job(s): $*"
waited=0
for job in "$@"; do
  IFS=: read -r name policy seed target <<< "$job"

  passes=0
  while :; do
    if bash "$HERE/e8_prelaunch_check.sh" "$name" > "$CAMPAIGN/e9_check_$name.txt" 2>&1; then passes=$((passes+1)); else
      [ "$passes" -gt 0 ] && log "$name: a check failed after a pass; counting again"
      passes=0
    fi
    [ "$passes" -ge 2 ] && break
    if [ "$waited" -ge "$WAIT_MAX_S" ]; then
      log "$name: gave up after waiting $waited s; last check: $(grep -E '^(FAIL|NOT READY)' "$CAMPAIGN/e9_check_$name.txt" | tr '\n' ' ')"
      log "queue ended early; not started: $name and every job after it"
      exit 3
    fi
    [ "$passes" -eq 0 ] && [ $((waited % 1800)) -eq 0 ] && log "$name: waiting; $(grep -E '^FAIL' "$CAMPAIGN/e9_check_$name.txt" | head -3 | tr '\n' ' ')"
    sleep 300; waited=$((waited+300))
  done
  log "$name: checks passed twice; $(grep -E 'GPU memory free|host memory free|disk free' "$CAMPAIGN/e9_check_$name.txt" | sed 's/^ok *//' | tr '\n' ';')"

  q="$CAMPAIGN/queue_$name.json"
  queue_json "$name" "$policy" "$seed" "$target" > "$q"
  [ -f "$CAMPAIGN/status_$CONTAINER.json" ] && cp -p "$CAMPAIGN/status_$CONTAINER.json" "$CAMPAIGN/status_$CONTAINER.before_$name.json"
  cd "$CAMPAIGN" || exit 1
  python3 "$WS/tools/live_policy/live_runner.py" --container "$CONTAINER" --queue "$q" --display "$DISPLAY_NO" --campaign-cap "$CAMPAIGN_CAP" > "runner_$name.out" 2>&1 < /dev/null &
  rp=$!
  log "$name: runner started (pid $rp)"

  asked=""
  while kill -0 "$rp" 2>/dev/null; do
    if [ -z "$asked" ]; then
      rl="$CAMPAIGN/$name/logs/roslaunch.log"
      if [ -f "$rl" ] && grep -q -i -E 'out of memory|nvblox_node.*(has died|process has died)' "$rl"; then
        asked="a line of A5.3 in roslaunch.log"
      else
        m1="$(mem_gb)"
        if [ "${m1:-99}" -lt 20 ]; then
          sleep 15; m2="$(mem_gb)"
          if [ "${m2:-99}" -lt 20 ]; then asked="free host memory $m1 GB, then $m2 GB 15 s later"; else log "$name: memory dipped to $m1 GB; $m2 GB 15 s later; no stop"; fi
        fi
      fi
      if [ -n "$asked" ]; then touch "$CAMPAIGN/STOP_$CONTAINER"; log "$name: STOP asked: $asked"; fi
    fi
    sleep 30
  done
  wait "$rp"; rc=$?
  [ -n "$asked" ] && rm -f "$CAMPAIGN/STOP_$CONTAINER"
  [ -f "$CAMPAIGN/status_$CONTAINER.json" ] && cp -p "$CAMPAIGN/status_$CONTAINER.json" "$CAMPAIGN/status_$CONTAINER.$name.json"
  stages="$(ls "$CAMPAIGN/$name/stages" 2>/dev/null | wc -l | tr -d ' ')"
  log "$name: runner ended (exit $rc); stage folders $stages; $(tail -1 "$CAMPAIGN/runner_$name.out" 2>/dev/null | cut -c1-300)"

  if COMPRESS_ROOTS=/workspace/runs/live_campaign bash "$HERE/compress_old_dsg.sh" --go > "$CAMPAIGN/e9_compress_$name.txt" 2>&1; then
    log "$name: graphs compressed; $(grep -E '^(compressed and checked|end )' "$CAMPAIGN/e9_compress_$name.txt" | tr '\n' ';')"
  else
    log "$name: compression not done ($(head -1 "$CAMPAIGN/e9_compress_$name.txt")); the next job's disk check decides"
  fi
done
log "queue done: every job has been through the runner"
