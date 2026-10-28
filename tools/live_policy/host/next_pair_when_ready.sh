#!/bin/bash
# next_pair_when_ready.sh <prev_official_run> <prev_placebo_run> <off_container> <pla_container> <scene> <seed>
# Launch the next pair when both previous runs have finished, or one has and MemAvailable >= 70 GB.
W=/home/sher/active-semantic-perception-workspace; C=$W/runs/live_campaign
done_run() { grep -h "finished $1: " $C/runner_*.log 2>/dev/null | grep -v adopt_failed | awk -v t="$2" '$1 > t' | grep -q .; }
START=$(date +%Y-%m-%dT%H:%M:%S)
while true; do
  a=0; b=0
  done_run "$1" "2026-10-28T07:00" && a=1
  done_run "$2" "2026-10-28T07:00" && b=1
  mem=$(awk '/MemAvailable/{printf "%d", $2/1048576}' /proc/meminfo)
  if [ $((a+b)) -eq 2 ] || { [ $((a+b)) -eq 1 ] && [ "$mem" -ge 70 ]; }; then break; fi
  sleep 60
done
cd $C
OFFS=$(ls -d e1_*_official_60m 2>/dev/null | while read r; do grep -q "finished $r: target_reached" runner_*.log && echo $r; done)
SCHED=$(python3 $W/tools/live_policy/pacing_update.py $OFFS | tail -1)
echo "$(date +%H:%M) pair $5/$6: placebo pacing from completed official runs ($OFFS): $SCHED" >> DEVIATIONS.md
$W/tools/live_policy/launch_pair.sh $3 $4 $5 $6 $SCHED 10.0
