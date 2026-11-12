#!/usr/bin/env bash
# Run the six seeded frontier runs one at a time in asp-noetic (PREREGISTRATION_FRONTIER_SEEDS.md).
# Stop rule: first stage with total_path_length_meters >= 60, "Exploration complete", or 6 h.
# A run below 50 m is rerun once. Writes a log to runs/frontier_seeds/queue.log.
W=/home/sher/active-semantic-perception-workspace
Q=$W/runs/frontier_seeds; mkdir -p "$Q"; LOG=$Q/queue.log
declare -A SID=([00853]=/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/val/00853-5cdEh9F2hJL/5cdEh9F2hJL.basis.glb
                [00871]=/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/val/00871-VBzV5z6i1WS/VBzV5z6i1WS.basis.glb)
log() { echo "$(date -Iseconds) $*" >> "$LOG"; }
path_of() { python3 - "$1" <<'PY'
import glob, json, os, sys
best = 0.0
for f in glob.glob(os.path.join(sys.argv[1], "stages", "*", "navigation_stats.json")):
    try: best = max(best, float(json.load(open(f)).get("total_path_length_meters", 0)))
    except Exception: pass
print(best)
PY
}
run_one() {  # scene seed name
  local scene=$1 seed=$2 name=$3 R=$Q/$3
  if [ -e "$R" ]; then mv "$R" "${R}_FAILED_ATTEMPT_$(date +%H%M)"; fi
  local avail=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)
  if [ "$avail" -lt 25 ]; then log "skip $name: only ${avail} GB free"; return 1; fi
  log "launch $name (seed $seed, ${avail} GB free)"
  docker exec -d asp-noetic bash /workspace/run_frontier_seed.sh "${SID[$scene]}" "${scene#00}" "frontier_seeds/$name" 95 "$seed"
  local start=$(date +%s) why=""
  while true; do
    sleep 60
    local p=$(path_of "$R")
    if awk "BEGIN{exit !($p >= 60)}"; then why="target_reached at $p m"; break; fi
    if grep -q "Exploration complete" "$R/logs/frontier_baseline.log" 2>/dev/null; then why="exploration_complete at $p m"; break; fi
    if [ $(( $(date +%s) - start )) -gt 21600 ]; then why="wall_clock_6h at $p m"; break; fi
    local a=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)
    if [ "$a" -lt 12 ]; then why="host_memory_stop at $p m (${a} GB free)"; break; fi
  done
  sleep 20   # let the last stage finish writing
  docker exec asp-noetic bash /workspace/stop_frontier_reference.sh "frontier_seeds/$name" >> "$LOG" 2>&1
  sleep 10
  log "finished $name: $why"
  echo "$p"
}
for spec in "00853 42" "00871 42" "00853 43" "00871 43" "00853 44" "00871 44"; do
  set -- $spec; name="e4_${1}_s${2}_frontier_60m"
  [ -f "$Q/STOP" ] && { log "STOP file found"; break; }
  p=$(run_one $1 $2 $name | tail -1)
  if awk "BEGIN{exit !(${p:-0} < 50)}"; then log "rerun $name once (ended below 50 m)"; run_one $1 $2 $name >/dev/null; fi
done
log "queue done"
