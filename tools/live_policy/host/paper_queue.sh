#!/usr/bin/env bash
# paper_queue.sh <job> [<job> ...]   (PREREGISTRATION_PAPER.md §2, run order as registered)
# Jobs, one at a time in asp-noetic:
#   e7:<scene>:<seed>        frontier to its natural end   -> runs/frontier_seeds/e7_<scene>_s<seed>_frontier_end
#   dry:<scene>:<mode>:<n>   short tour test (n waypoints)  -> runs/apr/dryrun_apr_<scene>_<mode>_<n>wp
#   apr:<scene>:<mode>       coverage tour (APR)            -> runs/apr/apr_<scene>_<mode>
# Before each launch: wait for >= 12 GB of free GPU memory (another user's server can hold it).
# Stops: "Exploration complete"; the explorer's "An unhandled exception occurred" line; its process gone; path >= 250 m (e7 only: §2b gives tours no path cap);
# 4 h wall clock; no new stage for 20 min; MemAvailable < 12 GB; free disk < 6 GB.
# A failed dry run cancels the apr jobs. After each run: the author's converter writes the
# YAML of every stage that has DSG files, then the DSG files are zstd-compressed (reversible).
# Jobs run with PYTHONUNBUFFERED=1: Python holds back stdout written to a file, and the explorer
# logs "Exploration complete" and then idles, so without it the line never reaches the log.
W=/home/sher/active-semantic-perception-workspace
LOG=$W/runs/apr/paper_queue.log; STOP=$W/runs/apr/STOP_PAPER
P=/workspace/environments/semantic_perception/bin/python
declare -A SID=([00853]=/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/val/00853-5cdEh9F2hJL/5cdEh9F2hJL.basis.glb
                [00871]=/workspace/datasets/hm3d/versioned_data/hm3d-0.2/hm3d/val/00871-VBzV5z6i1WS/VBzV5z6i1WS.basis.glb)
log() { echo "$(date -Iseconds) $*" >> "$LOG"; }
free_gb() { df -BG --output=avail / | tail -1 | tr -dc 0-9; }
mem_gb() { awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo; }
gpu_free_mb() { nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1 | tr -dc 0-9; }
path_of() { python3 - "$1" <<'PY'
import glob, json, os, sys
best = 0.0
for f in glob.glob(os.path.join(sys.argv[1], "stages", "*", "navigation_stats.json")):
    try: best = max(best, float(json.load(open(f)).get("total_path_length_meters", 0)))
    except Exception: pass
print(best)
PY
}
wait_gpu() {
  local ok=0 waited=0
  while true; do
    [ -f "$STOP" ] && return 1
    if [ "$(gpu_free_mb)" -ge 12000 ]; then ok=$((ok+1)); else ok=0; fi
    [ $ok -ge 2 ] && return 0
    [ $((waited % 3600)) -eq 0 ] && log "waiting for GPU: $(gpu_free_mb) MB free"
    sleep 300; waited=$((waited+300))
    [ $waited -gt 259200 ] && { log "gave up waiting for GPU after 72 h"; return 1; }
  done
}
convert_and_compress() {  # host run dir
  local R=$1 c=0
  for sd in "$R"/stages/*/; do
    [ -f "$sd/graph0_dsg.json" ] || continue
    local k=${sd#$W/}
    docker exec asp-noetic bash -c "nice -n 19 $P -B /workspace/runs/frontier_seeds/convert_frontier_reference.py /workspace/${k%/}" 2>&1 | grep -q '^wrote' && c=$((c+1))
  done
  docker exec asp-noetic bash -c "cd /workspace/${R#$W/}/stages && for f in */graph*_dsg.json; do y=\$(dirname \$f)/habitat_scene_graph_original_\$(basename \$f _dsg.json).yaml; [ -f \"\$y\" ] && nice -n 19 zstd -q --rm -3 \"\$f\"; done" 2>&1 | tail -2
  log "converted $c stages of ${R#$W/runs/} and compressed their DSG (disk $(free_gb) GB free)"
}
run_job() {  # kind scene arg n -> sets RESULT
  local kind=$1 scene=$2 arg=$3 n=$4 name R logf stop_cmd
  case $kind in
    e7)  name=frontier_seeds/e7_${scene}_s${arg}_frontier_end; logf=frontier_baseline.log
         launch=(bash /workspace/run_frontier_seed.sh "${SID[$scene]}" "${scene#00}" "$name" 95 "$arg")
         stop_cmd=(bash /workspace/stop_frontier_reference.sh "$name") ;;
    dry) name=apr/dryrun_apr_${scene}_${arg}_${n}wp; logf=coverage_tour.log
         launch=(bash /workspace/run_coverage_tour.sh "${SID[$scene]}" "${scene#00}" "$name" 95 "$arg" "$n")
         stop_cmd=(bash /workspace/stop_coverage_tour.sh "$name") ;;
    apr) name=apr/apr_${scene}_${arg}; logf=coverage_tour.log
         launch=(bash /workspace/run_coverage_tour.sh "${SID[$scene]}" "${scene#00}" "$name" 95 "$arg")
         stop_cmd=(bash /workspace/stop_coverage_tour.sh "$name") ;;
  esac
  R=$W/runs/$name
  if [ -e "$R" ]; then mv "$R" "${R}_FAILED_ATTEMPT_$(date +%H%M)"; fi
  if [ "$(mem_gb)" -lt 25 ] || [ "$(free_gb)" -lt 10 ]; then RESULT="skipped: mem $(mem_gb) GB, disk $(free_gb) GB"; log "skip $name: $RESULT"; return; fi
  log "launch $name (mem $(mem_gb) GB, disk $(free_gb) GB, GPU free $(gpu_free_mb) MB)"
  docker exec -d -e PYTHONUNBUFFERED=1 asp-noetic "${launch[@]}"
  local start=$(date +%s) last_n=0 last_change=$(date +%s) why="" p=0 pid=""
  sleep 90
  while true; do
    sleep 60
    p=$(path_of "$R")
    [ -z "$pid" ] && [ -f "$R/config/pids.txt" ] && pid=$(sed -n 's/.*FRONTIER_PID=\([0-9]*\).*/\1/p' "$R/config/pids.txt")
    if grep -q "Exploration complete" "$R/logs/$logf" 2>/dev/null; then why="exploration_complete at $p m"; break; fi
    # Only the explorer's own catch-all line counts: healthy October runs logged callback tracebacks.
    if grep -q "An unhandled exception occurred" "$R/logs/$logf" 2>/dev/null; then why="crashed at $p m: $(grep -m1 'An unhandled exception occurred' "$R/logs/$logf" | cut -c1-200)"; break; fi
    if [ -n "$pid" ] && ! docker exec asp-noetic kill -0 "$pid" 2>/dev/null; then
      if docker exec asp-noetic true 2>/dev/null; then why="explorer process gone at $p m"; break; fi
    fi
    if [ "$kind" = e7 ] && awk "BEGIN{exit !($p >= 250)}"; then why="path_cap_250m at $p m"; break; fi
    if [ $(( $(date +%s) - start )) -gt 14400 ]; then why="wall_clock_4h at $p m"; break; fi
    if [ "$(mem_gb)" -lt 12 ]; then why="host_memory_stop at $p m"; break; fi
    if [ "$(free_gb)" -lt 6 ]; then why="disk_stop at $p m"; break; fi
    local n_now=$(ls "$R/stages" 2>/dev/null | wc -l)
    if [ "$n_now" -ne "$last_n" ]; then last_n=$n_now; last_change=$(date +%s); fi
    if [ $(( $(date +%s) - last_change )) -gt 1200 ]; then why="stalled: no new stage for 20 min at $p m (GPU free $(gpu_free_mb) MB)"; break; fi
  done
  sleep 20
  docker exec asp-noetic "${stop_cmd[@]}" >> "$LOG" 2>&1
  sleep 10
  RESULT=$why
  log "finished $name: $why"
  convert_and_compress "$R"
}
DRY_OK=1
for job in "$@"; do
  [ -f "$STOP" ] && { log "STOP_PAPER found"; break; }
  IFS=: read -r kind scene arg n <<< "$job"
  if [ "$kind" = apr ] && [ "$DRY_OK" -ne 1 ]; then log "skip $job: the dry run failed"; continue; fi
  wait_gpu || break
  RESULT=""
  run_job "$kind" "$scene" "$arg" "$n"
  if [ "$kind" = dry ]; then
    S=$W/runs/apr/dryrun_apr_${scene}_${arg}_${n}wp/config/tour_summary.json
    if python3 - "$S" "$n" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); n = int(sys.argv[2])
ok = s.get("complete") and s.get("waypoints_reached") == n and abs(s.get("floor_y", 9)) < 0.5
print("dry run summary:", {k: s.get(k) for k in ("complete", "waypoints_listed", "waypoints_reached", "floor_y", "start_snap_moved_m")}, "counts", s.get("counts"))
sys.exit(0 if ok else 1)
PY
    then log "dry run passed: $(python3 -c "import json;s=json.load(open('$S'));print(s['counts'])")"; else DRY_OK=0; log "dry run FAILED ($RESULT); apr jobs cancelled"; fi
  fi
done
log "paper queue done"
