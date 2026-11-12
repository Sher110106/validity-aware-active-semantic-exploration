# Brief for an agent on tyrone: restart the paper-scale run queue

> **Superseded by `TYRONE_AGENT_BRIEF_2026-11-09_v2.md`.** This version ran at 16:20 on 11-09. Review later found that its `pgrep` check can match the agent's own shell, that values set in one block are lost in the next, and that the queue capped tours at 250 m. Kept as the record of what ran.

You are on tyrone, a shared GPU server. Sher's laptop can't reach it over the VPN, so you are doing what would normally be done from the laptop: check the queue of simulator runs and restart it if it died. All the code is already on this machine. You only run it.

## What the queue is
- `paper_queue.sh` runs 15 jobs, one at a time, inside the Docker container `asp-noetic`. It runs on the host as user `sher`, not inside the container.
- The jobs are robot-exploration runs in the Habitat simulator. They call no LLM or paid API, so they cost nothing.
- Before each job it waits until the GPU has at least 12 GB free on two checks 5 minutes apart. Another user's vLLM server often holds the GPU, and then the queue just waits. That is expected.
- Each job stops by itself (exploration complete, 250 m path, 4 h, a crash, or no progress for 20 min), then the queue converts and compresses its output and moves on.
- The queue was started on 2026-11-06 at about 17:40 IST. Tyrone dropped off the network at about 09:23 IST on 2026-11-09, so the queue may have died with it.

## Rules
1. Work as user `sher`. If `whoami` is not `sher`, stop and report.
2. Never read, print or copy `.gemini_credentials`, `.openrouter_credentials`, `.hm3d_credentials` or anything in `.cvp-secrets/` in the workspace root.
3. Never kill, stop, pause, renice or signal another user's process, and never contact other users. Another user's vLLM server must be left alone even if it blocks the GPU.
4. Don't edit any script, config or document, apart from the one config restore in step 4. Don't commit or push.
5. Don't delete or rename any run directory. The queue renames an interrupted run's directory itself when it reruns that job.
6. Don't rerun a job that already has a `finished` line in the queue log, whatever its reason. Don't change the queue's limits (12 GB of GPU memory, 4 h, 250 m and so on).
7. Don't copy scene-graph files (`*_dsg.json*`) anywhere: the disk is nearly full.
8. If anything doesn't match what this brief expects, stop and report what you saw. Don't improvise a fix.

Use these names in every shell:
```bash
W=/home/sher/active-semantic-perception-workspace
LOG=$W/runs/apr/paper_queue.log
CFG=/workspace/catkin_ws/src/active_semantic_perception/exploration/config/frontier_config.yaml
```

## Step 1. Look (read-only)
```bash
whoami; date; uptime -s; uptime
nvidia-smi --query-gpu=memory.used,memory.free,memory.total,utilization.gpu --format=csv
nvidia-smi --query-compute-apps=pid,used_memory,process_name --format=csv
free -g | head -2; df -h / | tail -1
pgrep -u sher -af "bash paper_queue.sh"
ls -l $W/runs/apr/STOP_PAPER 2>/dev/null
tail -n 40 $LOG
docker ps -a --filter name=asp-noetic --format '{{.Names}} {{.Status}}'
```
`uptime -s` gives the boot time. A boot time after 2026-11-09 09:00 means the machine restarted.

## Step 2. Is the queue still alive?
If `pgrep` printed a `bash paper_queue.sh` process, the queue survived and only the network failed. Don't start a second queue. Go to step 7 and report.

Otherwise, go on.

## Step 3. Make sure the container sees the GPU
```bash
docker ps --filter name=asp-noetic --format '{{.Status}}'   # empty means it is not running
docker start asp-noetic                                       # only if it is not running
docker exec asp-noetic nvidia-smi --query-gpu=name --format=csv,noheader
```
If the last command fails (for example `Failed to initialize NVML: Unknown Error`), restart the container once. This is safe only because the queue is dead:
```bash
docker stop asp-noetic && docker start asp-noetic
docker exec asp-noetic nvidia-smi --query-gpu=name --format=csv,noheader
```
If it still fails, stop and report.

Now check that no run is still going inside the container:
```bash
docker exec asp-noetic pgrep -af "roslaunch|rosmaster|frontier_baseline|coverage_tour|Xvfb|hydra_ros_node|nvblox|task_server"
```
A single `<defunct>` roslaunch entry is a harmless leftover from 11-06. Anything else, live, means a run is still going: stop and report.

## Step 4. Tidy up after an interrupted run
Find the last job the queue launched, and check whether it finished:
```bash
LAST=$(grep -o 'launch [^ ]*' $LOG | tail -1 | cut -d' ' -f2); echo "last launched: $LAST"
[ -n "$LAST" ] && ! grep -qF "finished $LAST:" $LOG && echo "INTERRUPTED: $LAST"
```
If it printed `INTERRUPTED`, put the explorer's config back the way it was before that run:
```bash
docker exec asp-noetic bash -c "f=/workspace/runs/$LAST/config/frontier_config.original.yaml; [ -f \$f ] && cp \$f $CFG && echo restored"
```
Then clear a stale virtual-display lock, if no display server is running:
```bash
docker exec asp-noetic bash -c 'pgrep -x Xvfb >/dev/null || rm -f /tmp/.X95-lock /tmp/.X11-unix/X95'
```

## Step 5. Check the code is the reviewed version
```bash
sha256sum $W/runs/apr/paper_queue.sh $W/run_coverage_tour.sh $W/stop_coverage_tour.sh $W/run_frontier_seed.sh \
  $W/catkin_ws/src/active_semantic_perception/exploration/scripts/coverage_tour.py \
  $W/catkin_ws/src/active_semantic_perception/exploration/scripts/tour_waypoints.py
```
Expected, in that order:
```
46f4d0d30a9db26fe51c5d98faf6c75405b7c4e6461ddeae91919d99da656468  paper_queue.sh
3e8d7af6e95b184c8bd4088b193b0958f37ca4be4f89c6ba189ab82cb696ffcb  run_coverage_tour.sh
5067d41e63162274c13107d64921fb6c9a76507d5b187c7490a5b9a143e34f0c  stop_coverage_tour.sh
9c2c70344479f936a83136f78b7040d5faf272f821cb37ccefd31019986353cc  run_frontier_seed.sh
d05b42f7f411bb0ff22e74cb81f58417f6587db72b1fb50417d93693d440bbdc  coverage_tour.py
1b61cdcfab98e058ddae4db2dff36906a52ed654e6c40bbf88e7975c1ac411b3  tour_waypoints.py
```
If any hash differs, stop and report. Don't fix the file.

## Step 6. Work out the jobs left, then restart the queue
This drops every job with a `finished` line. If the dry run failed, it also drops the four tours (`apr:` jobs), as the pre-registration requires.
```bash
ALL="dry:00853:a:3 e7:00853:42 e7:00871:42 apr:00853:a apr:00871:a apr:00853:b apr:00871:b e7:00853:43 e7:00871:43 e7:00853:44 e7:00871:44 e7:00853:45 e7:00871:45 e7:00853:46 e7:00871:46"
DRY_FAILED=0; grep -q "dry run FAILED" $LOG && DRY_FAILED=1
REMAIN=""
for j in $ALL; do
  IFS=: read -r k s a n <<< "$j"
  case $k in
    e7)  name=frontier_seeds/e7_${s}_s${a}_frontier_end ;;
    dry) name=apr/dryrun_apr_${s}_${a}_${n}wp ;;
    apr) name=apr/apr_${s}_${a} ;;
  esac
  if [ "$k" = dry ]; then
    grep -q "dry run passed" $LOG && continue
    [ "$DRY_FAILED" = 1 ] && continue
  elif [ "$k" = apr ] && [ "$DRY_FAILED" = 1 ]; then continue
  elif grep -qF "finished $name:" $LOG; then continue
  fi
  REMAIN="$REMAIN $j"
done
echo "dry run failed: $DRY_FAILED"; echo "remaining jobs:$REMAIN"
```
Don't start the queue if:
- `STOP_PAPER` exists (someone asked it to stop; leave the file and report);
- `REMAIN` is empty (everything is done; report);
- the log shows a `finished` line for a job that ended `crashed`, `stalled` or `explorer process gone` **and** no later job has run. Report it first, because a fault may repeat.

Otherwise start it exactly like this, from that directory:
```bash
cd $W/runs/apr && echo "$(date -Iseconds) restarted after the 11-09 outage with:$REMAIN" >> $LOG && \
  (setsid nohup bash paper_queue.sh $REMAIN > paper_queue.out 2>&1 < /dev/null &)
sleep 5; pgrep -u sher -af "bash paper_queue.sh"; tail -n 3 $LOG
```
`$REMAIN` must stay unquoted, so each job is a separate argument. You should see one queue process. Within 5 minutes the log shows either `waiting for GPU` (another user holds it, which is fine) or, after its second check, `launch ...`.

## Step 7. Watch and report
Check every 30-60 minutes if you can stay; otherwise run this once and hand the output to Sher:
```bash
date; nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader
pgrep -u sher -af "bash paper_queue.sh"; tail -n 30 $LOG
for R in $W/runs/apr/dryrun_apr_* $W/runs/apr/apr_00* $W/runs/frontier_seeds/e7_*_frontier_end; do
  [ -d "$R" ] || continue
  echo "$R: $(ls $R/stages 2>/dev/null | wc -l) stages"
  [ -f $R/config/tour_summary.json ] && python3 -c "import json,sys; s=json.load(open(sys.argv[1])); print('  ', {k: s.get(k) for k in ('complete','waypoints_listed','waypoints_reached','floor_y')})" $R/config/tour_summary.json
done
df -h / | tail -1
```
Report straight away when:
- the dry run ends (`dry run passed` or `dry run FAILED`);
- any job's `finished` line says anything other than `exploration_complete`, `path_cap_250m` or `wall_clock_4h`;
- a job is skipped for memory or disk;
- the log says `paper queue done` or `gave up waiting for GPU`.

The first job is a short dry run (3 waypoints, under an hour). The rest take about 1-4 hours each.

## Stopping, only if Sher asks
- **After the current job:** `touch $W/runs/apr/STOP_PAPER`. The queue stops before its next job.
- **Now:** stop the queue with `pkill -u sher -f "^bash paper_queue.sh"`, then stop the running job inside the container, using the run name from the last `launch` line:
  - frontier (`frontier_seeds/...`): `docker exec asp-noetic bash /workspace/stop_frontier_reference.sh <name>`;
  - tour or dry run (`apr/...`): `docker exec asp-noetic bash /workspace/stop_coverage_tour.sh <name>`.
