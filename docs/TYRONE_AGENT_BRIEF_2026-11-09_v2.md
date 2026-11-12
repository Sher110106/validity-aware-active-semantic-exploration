# Brief v2 for the agent on tyrone: hand the running queue over to the fixed version

> **Done, and followed by `TYRONE_AGENT_BRIEF_2026-11-09_v3.md`.** The handover worked at 17:52 on 11-09. Its step 4 and its copy of the control script are out of date.

You ran the first brief and restarted the queue at 16:20. Thank you for the report. This brief replaces the first one.

## Why this is needed
Your report found one problem, and review of the first brief found one more:
1. **Buffered output.** The explorer's `Exploration complete` line does not reach its log while it idles, so the queue ends every finished run as `stalled`, 20 minutes late. The fix is to launch jobs with `PYTHONUNBUFFERED=1`.
2. **Tours capped at 250 m.** The queue stops every job at 250 m. The pre-registration (`PREREGISTRATION_PAPER.md` §2b) gives the tours only a 4 h cap. Only e7 jobs should stop at 250 m.

Both fixes go into `paper_queue.sh`. A running bash script must not be edited, so the running queue has to stop first. The plan:
- let the running queue finish its **current** job, then stop it with `STOP_PAPER`;
- a background watcher then restarts the queue with the fixed `paper_queue.sh` and the jobs left.

The jobs that ran under the old queue (the dry run and perhaps e7 853/42) keep their data. Their `stalled` label is recognised as a finished run when the explorer's log holds `Exploration complete`, or, for a tour, its summary says complete.

All of this is in one tested script, `paper_queue_ctl.sh`, which you write below. Its checks stop it on anything unexpected.

## Rules (as before)
1. Work as user `sher`, on the host, not in the container.
2. Never read, print or copy `.gemini_credentials`, `.openrouter_credentials`, `.hm3d_credentials` or `.cvp-secrets/`.
3. Never touch another user's process, and never contact other users. That includes another user's vLLM server if it comes back.
4. This brief allows exactly these changes:
   - writing `runs/apr/paper_queue_ctl.sh`;
   - creating `runs/apr/STOP_PAPER` and `runs/apr/HANDOVER_1109`;
   - starting the watcher.

   The script itself patches `paper_queue.sh` and restarts the queue. Make no other edit, and don't commit or push.
5. Don't delete or rename run directories, and don't copy `*_dsg.json*` files anywhere.
6. When the script prints `VERDICT: STOP`, change nothing more and report its whole output to Sher.
7. Run every block below as its own command, with bash.

## Step 1. Write the script, then check it
Run this block as it stands. It is long: copy all of it, down to the `PAPER_QUEUE_CTL_EOF` line.
```bash
W=/home/sher/active-semantic-perception-workspace
cat > $W/runs/apr/paper_queue_ctl.sh <<'PAPER_QUEUE_CTL_EOF'
#!/usr/bin/env bash
# paper_queue_ctl.sh check|handover|restart|status   (docs/TYRONE_AGENT_BRIEF_2026-11-09.md)
# Run on the tyrone host as user sher, never inside the container.
#   check     reads only; prints the facts and one VERDICT line.
#   handover  swaps a running queue for the fixed paper_queue.sh. Needs STOP_PAPER and
#             HANDOVER_1109 in runs/apr. Waits (up to 6 h) for the running queue to finish
#             its current job and exit, repeats every check, then restarts with the jobs left.
#   restart   for a queue killed by a reboot: repeats every check, then restarts.
#   status    reads only; for watching the queue.
# Before restarting, handover and restart fix the container's GPU access if needed, tidy a
# cut-off run, and patch paper_queue.sh: no 250 m cap for tours (PREREGISTRATION_PAPER.md
# section 2b), and PYTHONUNBUFFERED=1 so "Exploration complete" reaches the log at once.
# Every STOP verdict means: change nothing more, report the output to Sher.
set -u
MODE=${1:-check}
W=${PAPER_W:-/home/sher/active-semantic-perception-workspace}
Q=$W/runs/apr
LOG=$Q/paper_queue.log
MARK=$Q/HANDOVER_1109
CFG=/workspace/catkin_ws/src/active_semantic_perception/exploration/config/frontier_config.yaml
SCRIPTS=$W/catkin_ws/src/active_semantic_perception/exploration/scripts
OUTAGE="2026-11-09 09:00"
OLD_QUEUE_SHA=46f4d0d30a9db26fe51c5d98faf6c75405b7c4e6461ddeae91919d99da656468
NEW_QUEUE_SHA=6ffb56015253a361e1c4baf082a17364ae43bb8b9d75bff92bb2d1551848e253
ALL="dry:00853:a:3 e7:00853:42 e7:00871:42 apr:00853:a apr:00871:a apr:00853:b apr:00871:b e7:00853:43 e7:00871:43 e7:00853:44 e7:00871:44 e7:00853:45 e7:00871:45 e7:00853:46 e7:00871:46"
RUN_PATTERN="roslaunch|rosmaster|frontier_baseline|coverage_tour|Xvfb|hydra_ros_node|nvblox|task_server"

stop() { echo "VERDICT: STOP - $*"; echo "Change nothing more. Report this whole output to Sher."; exit 1; }
sha() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -c1-64; else shasum -a 256 "$1" | cut -c1-64; fi; }
queue_alive() { pgrep -u sher -f '^bash paper_queue\.sh' >/dev/null; }
container_running() { [ "$(docker inspect -f '{{.State.Running}}' asp-noetic 2>/dev/null)" = true ]; }
container_gpu() { docker exec asp-noetic nvidia-smi -L >/dev/null 2>&1; }
# Live (not zombie) run processes in the container. grep runs on the host, so it cannot match itself.
container_runs() { docker exec asp-noetic ps -eo stat=,args= 2>/dev/null | awk '$1 !~ /^Z/' | grep -E "$RUN_PATTERN"; }
name_of() {  # job -> run name, as paper_queue.sh names it
  local k s a n; IFS=: read -r k s a n <<< "$1"
  case $k in
    e7)  echo "frontier_seeds/e7_${s}_s${a}_frontier_end" ;;
    dry) echo "apr/dryrun_apr_${s}_${a}_${n}wp" ;;
    apr) echo "apr/apr_${s}_${a}" ;;
  esac
}
tour_complete() {  # run name -> true if its tour_summary.json says complete
  [ -f "$W/runs/$1/config/tour_summary.json" ] &&
    python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("complete") else 1)' "$W/runs/$1/config/tour_summary.json"
}
# "finished" lines whose reason is not a normal end for that kind of job, from line $1 on.
# The unpatched queue could not see "Exploration complete" (buffered stdout), so a finished
# run ended there as "stalled". Such a line counts as normal if the run's log holds
# "Exploration complete" (written when the stop flushed it) or, for a tour, its summary says complete.
abnormal() {
  local from=${1:-1} ts word name why rest
  tail -n "+$from" "$LOG" | while read -r ts word name why rest; do
    [ "$word" = finished ] || continue
    name=${name%:}
    case "$why" in
      exploration_complete) continue ;;
      path_cap_250m|wall_clock_4h) case $name in frontier_seeds/*) continue ;; esac ;;
      stalled:)
        grep -q "Exploration complete" "$W/runs/$name/logs/frontier_baseline.log" 2>/dev/null && continue
        case $name in apr/*) tour_complete "$name" && continue ;; esac ;;
    esac
    echo "$ts $word $name: $why $rest"
  done
}
last_launch() { awk '$2 == "launch" {x = $3} END {print x}' "$LOG"; }
last_finished() { awk '$2 == "finished" {x = $3} END {sub(/:$/, "", x); print x}' "$LOG"; }
has_line() { grep -qF -- "$1" "$LOG"; }

status() {
  echo "== $(date '+%F %T')  GPU: $(nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader 2>&1)  disk: $(df -h / | awk 'NR==2{print $4}') free"
  if queue_alive; then echo "queue: running"; else echo "queue: NOT running"; fi
  [ -e "$MARK" ] && echo "handover: pending (the running queue stops after its current job; the watcher then restarts the fixed queue)"
  echo "-- last log lines"; tail -n 12 "$LOG"
  local cur; cur=$(last_launch)
  if [ -n "$cur" ] && ! has_line " finished $cur: "; then
    local R=$W/runs/$cur
    echo "-- current job $cur: $(ls "$R/stages" 2>/dev/null | wc -l | tr -d ' ') stages, path $(python3 -c 'import glob,json,sys
b=0.0
for f in glob.glob(sys.argv[1]+"/stages/*/navigation_stats.json"):
    try: b=max(b,float(json.load(open(f)).get("total_path_length_meters",0)))
    except Exception: pass
print(round(b,1))' "$R") m"
    echo "   explorer: $(docker exec asp-noetic ps -eo stat=,args= 2>/dev/null | awk '$1 !~ /^Z/' | grep -cE 'frontier_baseline.py|coverage_tour.py') process(es) alive"
  fi
  local R
  for R in "$Q"/dryrun_apr_* "$Q"/apr_00*; do
    [ -f "$R/config/tour_summary.json" ] || continue
    echo "-- $(basename "$R"): $(python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); print({k: s.get(k) for k in ("complete","waypoints_listed","waypoints_reached","floor_y")})' "$R/config/tour_summary.json")"
  done
  local from bad; from=$(awk '$2 == "restarted" {n = NR} END {print n + 0}' "$LOG")
  bad=$(abnormal "$((from + 1))")
  if [ -n "$bad" ]; then
    echo "$bad"
    echo "VERDICT: STOP THE QUEUE - a job since the last restart ended badly. Run: touch $Q/STOP_PAPER   then report this output to Sher."
    exit 1
  fi
  if tail -n 1 "$LOG" | grep -q "paper queue done"; then
    if [ -e "$MARK" ]; then echo "VERDICT: OK - the old queue has stopped; the handover watcher takes over now"
    else echo "VERDICT: DONE - the queue has finished. Report this output to Sher."; fi
  elif ! queue_alive && [ ! -e "$MARK" ]; then
    echo "VERDICT: STOP - the queue is not running and did not finish. Report this output to Sher."
    exit 1
  else
    echo "VERDICT: OK"
  fi
}

case "$MODE" in
  status) status; exit 0 ;;
  check|restart|handover) ;;
  *) echo "usage: $0 check|handover|restart|status"; exit 2 ;;
esac

echo "== $(date '+%F %T') user $(whoami), boot $(uptime -s), mode $MODE"
[ "$(whoami)" = sher ] || stop "not running as user sher"
[ "$(ps -p 1 -o comm=)" = systemd ] || stop "cannot see the host's processes (PID 1 is not systemd): run this on the host, outside any sandbox or container"
docker info >/dev/null 2>&1 || stop "cannot use docker as this user"
[ -s "$LOG" ] || stop "queue log $LOG is missing or empty"

if [ "$MODE" = handover ]; then
  exec 9> "$Q/.handover.lock"
  flock -n 9 || stop "another handover watcher is already running"
  [ -e "$Q/STOP_PAPER" ] && [ -e "$MARK" ] || stop "handover needs both $Q/STOP_PAPER and $MARK"
  waited=0
  while queue_alive; do
    [ $((waited % 1800)) -eq 0 ] && echo "$(date '+%F %T') waiting for the running queue to finish its current job"
    [ "$waited" -ge 21600 ] && stop "the running queue has not stopped after 6 h"
    sleep "${PAPER_POLL_S:-60}"; waited=$((waited + 60))
  done
  echo "$(date '+%F %T') the running queue has exited"
fi

echo "-- GPU"; nvidia-smi --query-gpu=memory.used,memory.free,memory.total,utilization.gpu --format=csv,noheader
nvidia-smi --query-compute-apps=pid,used_memory,process_name --format=csv,noheader
echo "-- memory $(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo 2>/dev/null) GB available, disk $(df -BG --output=avail / 2>/dev/null | tail -1 | tr -d ' ') free"
echo "-- last log lines"; tail -n 15 "$LOG"

if queue_alive; then
  pgrep -u sher -af '^bash paper_queue\.sh'
  [ -e "$MARK" ] && echo "-- handover pending: the watcher restarts the fixed queue once this one exits"
  if container_running && container_gpu; then
    echo "VERDICT: ALIVE - the queue is running. Don't restart anything; run 'status' and report."
    exit 0
  fi
  stop "URGENT: the queue is alive but the container cannot see the GPU, so every job it launches will fail"
fi

if [ "$MODE" = handover ]; then
  tail -n 1 "$LOG" | grep -q "paper queue done" || stop "the old queue exited without logging 'paper queue done'"
else
  [ -e "$MARK" ] && stop "a handover is pending: check with 'status' that its watcher runs; don't restart by hand"
  [ -e "$Q/STOP_PAPER" ] && stop "STOP_PAPER exists: someone asked the queue to stop"
  GAVE_UP=0
  if tail -n 1 "$LOG" | grep -q "paper queue done"; then
    if tail -n 2 "$LOG" | grep -q "gave up waiting for GPU"; then GAVE_UP=1
    else stop "the queue ended by itself (all jobs done or skipped, or STOP_PAPER); nothing to restart"; fi
  fi
  BOOT=$(uptime -s)
  if [ "$GAVE_UP" = 0 ] && [[ ! "$BOOT" > "$OUTAGE" ]]; then
    stop "the queue is dead but the machine did not restart (boot $BOOT): something else killed it"
  fi
fi

INTERRUPTED=""
L=$(last_launch)
[ -n "$L" ] && ! has_line " finished $L: " && INTERRUPTED=$L
[ -n "$INTERRUPTED" ] && [ "$MODE" = handover ] && stop "job $INTERRUPTED never finished although the old queue exited"
F=$(last_finished)
if [ -n "$F" ] && ! has_line "stages of $F and compressed"; then
  stop "job $F finished but its conversion and compression did not (cut off?)"
fi
if has_line " finished apr/dryrun_apr_" && ! grep -qE "dry run (passed|FAILED)" "$LOG"; then
  stop "the dry run finished but has no pass/fail line"
fi
has_line "dry run FAILED (skipped:" && stop "the dry run was skipped for memory or disk, not failed; Sher must decide about the tours"
BAD=$(abnormal 1)
[ -n "$BAD" ] && { echo "$BAD"; stop "these jobs ended badly; Sher must look before anything reruns"; }

if [ -n "$INTERRUPTED" ]; then
  echo "-- the outage cut off $INTERRUPTED. How the machine went down:"
  last -x -F reboot shutdown 2>/dev/null | head -4
  PREV=$(last -x reboot shutdown 2>/dev/null | awk '$1 == "reboot" || $1 == "shutdown" {print $1}' | head -2 | paste -sd' ' -)
  [ "$PREV" = "reboot shutdown" ] || stop "a run was cut off and the machine did not shut down cleanly (or this can't be told). Our run might have caused it, so Sher must check before it reruns"
fi

if container_running; then
  RUNS=$(container_runs)
  [ -n "$RUNS" ] && { echo "$RUNS"; stop "run processes are still alive in the container although the queue is dead"; }
  if container_gpu; then echo "-- container: running, sees the GPU"; else echo "-- container: running, but CANNOT see the GPU (a restart stops and starts it)"; fi
else
  echo "-- container: not running (a restart starts it)"
fi

QSHA=$(sha "$Q/paper_queue.sh")
[ "$QSHA" = "$OLD_QUEUE_SHA" ] || [ "$QSHA" = "$NEW_QUEUE_SHA" ] || stop "paper_queue.sh is not a reviewed version ($QSHA)"
while read -r want f; do
  got=$(sha "$f" 2>/dev/null)
  [ "$got" = "$want" ] || stop "$f is not the reviewed version (${got:-missing})"
done <<EOF
3e8d7af6e95b184c8bd4088b193b0958f37ca4be4f89c6ba189ab82cb696ffcb $W/run_coverage_tour.sh
5067d41e63162274c13107d64921fb6c9a76507d5b187c7490a5b9a143e34f0c $W/stop_coverage_tour.sh
9c2c70344479f936a83136f78b7040d5faf272f821cb37ccefd31019986353cc $W/run_frontier_seed.sh
d05b42f7f411bb0ff22e74cb81f58417f6587db72b1fb50417d93693d440bbdc $SCRIPTS/coverage_tour.py
1b61cdcfab98e058ddae4db2dff36906a52ed654e6c40bbf88e7975c1ac411b3 $SCRIPTS/tour_waypoints.py
EOF

DRY_FAILED=0; has_line "dry run FAILED" && DRY_FAILED=1
REMAIN=""; SKIPPED=""
for j in $ALL; do
  name=$(name_of "$j"); k=${j%%:*}
  if has_line " skip $name:" || has_line " skip $j:"; then SKIPPED="$SKIPPED $j"; continue; fi
  if [ "$k" = dry ]; then has_line "dry run passed" && continue; [ "$DRY_FAILED" = 1 ] && continue
  elif [ "$k" = apr ] && [ "$DRY_FAILED" = 1 ]; then continue
  elif has_line " finished $name: "; then continue
  fi
  REMAIN="$REMAIN $j"
done
REMAIN=${REMAIN# }
echo "-- dry run failed: $DRY_FAILED; skipped by the queue (not rerun):${SKIPPED:- none}"
echo "-- interrupted: ${INTERRUPTED:-none}"
echo "-- jobs left: ${REMAIN:-none}"
[ -n "$REMAIN" ] || stop "no jobs left"

if [ "$MODE" = check ]; then
  echo "VERDICT: RESTART OK - run: bash $Q/paper_queue_ctl.sh restart"
  exit 0
fi

# --- restart (both restart and handover) ---
if ! container_running; then docker start asp-noetic >/dev/null && sleep 5; fi
if ! container_gpu; then
  echo "-- the container cannot see the GPU: stopping and starting it once"
  docker stop asp-noetic >/dev/null && docker start asp-noetic >/dev/null && sleep 5
fi
container_gpu || stop "the container still cannot see the GPU after a stop and start"
if [ -n "$INTERRUPTED" ]; then
  docker exec asp-noetic bash -c "f=/workspace/runs/$INTERRUPTED/config/frontier_config.original.yaml; if [ -f \$f ]; then cp \$f $CFG && echo '-- restored frontier_config.yaml from the cut-off run'; else echo '-- no saved config in the cut-off run; frontier_config.yaml left as is'; fi"
fi
docker exec asp-noetic bash -c 'pgrep -x Xvfb >/dev/null || rm -f /tmp/.X95-lock /tmp/.X11-unix/X95'
if [ "$(sha "$Q/paper_queue.sh")" = "$OLD_QUEUE_SHA" ]; then
  python3 - "$Q/paper_queue.sh" <<'PY'
import os, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
for old, new in [
    ('path >= 250 m;\n', 'path >= 250 m (e7 only: \u00a72b gives tours no path cap);\n'),
    ('    if awk "BEGIN{exit !($p >= 250)}"; then', '    if [ "$kind" = e7 ] && awk "BEGIN{exit !($p >= 250)}"; then'),
    ('zstd-compressed (reversible).\nW=', 'zstd-compressed (reversible).\n'
     '# Jobs run with PYTHONUNBUFFERED=1: Python holds back stdout written to a file, and the explorer\n'
     '# logs "Exploration complete" and then idles, so without it the line never reaches the log.\nW='),
    ('  docker exec -d asp-noetic "${launch[@]}"', '  docker exec -d -e PYTHONUNBUFFERED=1 asp-noetic "${launch[@]}"'),
]:
    assert s.count(old) == 1, old
    s = s.replace(old, new)
open(p + ".new", "w", encoding="utf-8").write(s)
os.replace(p + ".new", p)
PY
fi
[ "$(sha "$Q/paper_queue.sh")" = "$NEW_QUEUE_SHA" ] || stop "paper_queue.sh did not patch cleanly"
echo "-- paper_queue.sh: tours have no 250 m cap; jobs run with PYTHONUNBUFFERED=1"
cd "$Q" || stop "cannot cd to $Q"
rm -f "$Q/STOP_PAPER" "$MARK"
echo "$(date '+%Y-%m-%dT%H:%M:%S%z') restarted ($MODE) with: $REMAIN" >> "$LOG"
(setsid nohup bash paper_queue.sh $REMAIN >> "$Q/paper_queue_restart.out" 2>&1 < /dev/null 9>&- &)
sleep 5
queue_alive || stop "the queue did not stay up; see $Q/paper_queue_restart.out"
pgrep -u sher -af '^bash paper_queue\.sh'
echo "VERDICT: RESTARTED - check again with 'status' in 10 minutes, from a new command."
PAPER_QUEUE_CTL_EOF
sha256sum $W/runs/apr/paper_queue_ctl.sh
```
The hash must be exactly:
```
2b71ee2035eb10f755ff62f2aa8aa8bcca1efc1c1ce09bb7d7973f12439be83f
```
If it differs, the paste changed something. Delete only that new file (`rm $W/runs/apr/paper_queue_ctl.sh`), write it again, and if it still differs, stop and report.

## Step 2. Check the current state
```bash
bash /home/sher/active-semantic-perception-workspace/runs/apr/paper_queue_ctl.sh check
```
Expected: `VERDICT: ALIVE` (the old queue is running). If you see anything else, stop and report.

Also record whether the dry run's log now holds the line. It should, once the queue has stopped the dry run (about 16:50):
```bash
grep -c "Exploration complete" /home/sher/active-semantic-perception-workspace/runs/apr/dryrun_apr_00853_a_3wp/logs/coverage_tour.log
```

## Step 3. Arm the handover and start the watcher
```bash
Q=/home/sher/active-semantic-perception-workspace/runs/apr
touch $Q/STOP_PAPER $Q/HANDOVER_1109
cd $Q && (setsid nohup bash paper_queue_ctl.sh handover >> $Q/handover_1109.out 2>&1 < /dev/null &)
```
Then, **in a new command** a few seconds later:
```bash
Q=/home/sher/active-semantic-perception-workspace/runs/apr
pgrep -u sher -af '^bash paper_queue_ctl\.sh handover'
tail -n 5 $Q/handover_1109.out
```
You should see one watcher process, and the output should end with `waiting for the running queue to finish its current job`. If you see two watchers or a `VERDICT: STOP`, stop and report.

What happens next:
- **If e7 853/42 has not started yet,** the old queue stops within 5 minutes, and the watcher restarts the fixed queue at once, beginning with e7 853/42.
- **If e7 853/42 is running,** the old queue finishes it first. That takes 1-4 h, plus 20 minutes, because the old queue can't see the end. The watcher then restarts the fixed queue with e7 871/42 and the rest.

The watcher writes its checks and one `VERDICT` line to `handover_1109.out`:
- `VERDICT: RESTARTED` means all is well;
- `VERDICT: STOP` means nothing restarted, and `STOP_PAPER` stays in place, so nothing runs until Sher decides.

## Step 4. Watch and report
Every 30-60 minutes, if you can stay, run:
```bash
Q=/home/sher/active-semantic-perception-workspace/runs/apr
bash $Q/paper_queue_ctl.sh status; tail -n 25 $Q/handover_1109.out
```
Report to Sher straight away when:
- `handover_1109.out` shows a `VERDICT` line;
- `status` prints `VERDICT: STOP THE QUEUE`. Run the `touch` command it gives, then report;
- `status` prints `VERDICT: STOP` or `VERDICT: DONE`;
- free GPU memory falls under about 2 GB while a job runs, or a vLLM process appears in the GPU list. Don't act on it; just report it.

If you must leave, run the block above once more and hand its output to Sher. The watcher and the queue run on without you.
