#!/bin/bash
# campaign_chain.sh <jobs_file> <prev_run_a> <prev_run_b>
# Runs jobs one after another on tyrone. Each line of jobs_file:
#   pair <scene> <seed>                      E1: official + placebo (placebo paced from completed official runs)
#   e2 <scene1> <seed1> <scene2> <seed2>     E2: two filter_only runs
#   rerun <scene> <seed> <policy> [...]      E1: rerun once (as ..._rerun1) each named run
#                                            that stopped below 50 m; skipped if it reached 50 m
# A job starts when both runs of the previous job have finished, or one has
# and MemAvailable >= 70 GB. Containers are picked from those with no active runner.
W=/home/sher/active-semantic-perception-workspace; C=$W/runs/live_campaign; CAP=20.0
START=$(date +%Y-%m-%dT%H:%M:%S)
POOL="asp-noetic asp-noetic-b asp-noetic-c asp-noetic-d asp-noetic-f asp-noetic-g"
log() { echo "$(date +%Y-%m-%dT%H:%M:%S) $*" | tee -a $C/campaign_chain.log; }
finished() { grep -h "finished $1: " $C/runner_*.log 2>/dev/null | awk -v t="$START" '$1 > t' | grep -q .; }
# Idle = no runner attached AND no pipeline inside (a runner can crash while its run goes on).
idle() { for c in $POOL; do pgrep -f "live_runner.py --container $c --" >/dev/null && continue; docker exec $c pgrep -f run_pipeline_with_policy.py >/dev/null 2>&1 && continue; echo $c; done; }
wait_prev() {
  while true; do
    n=0; finished "$1" && n=$((n+1)); finished "$2" && n=$((n+1))
    mem=$(awk '/MemAvailable/{printf "%d", $2/1048576}' /proc/meminfo)
    if [ $n -eq 2 ] || { [ $n -eq 1 ] && [ "$mem" -ge 70 ]; }; then return; fi
    sleep 60
  done
}
prev_a=$2; prev_b=$3
while read -r kind s1 d1 s2 d2 p3 p4; do
  [ -z "$kind" ] && continue
  log "waiting for $prev_a and $prev_b before: $kind $s1 $d1 $s2 $d2"
  wait_prev "$prev_a" "$prev_b"
  set -- $(idle); c1=$1; c2=$2
  if [ -z "$c2" ]; then log "fewer than two idle containers; waiting"; sleep 120; set -- $(idle); c1=$1; c2=$2; fi
  for c in $c1 $c2; do $W/tools/live_policy/clean_container.sh $c > /dev/null; done
  cd $C
  if [ "$kind" = pair ]; then
    OFFS=$(ls -d e1_*_official_60m 2>/dev/null | while read r; do grep -q "finished $r: target_reached" runner_*.log && echo $r; done)
    SCHED=$(python3 $W/tools/live_policy/pacing_update.py $OFFS | tail -1)
    echo "$(date +%H:%M) pair $s1/$d1: placebo pacing from completed official runs ($(echo $OFFS)): $SCHED" >> DEVIATIONS.md
    log "launch pair $s1/$d1 on $c1 (official) $c2 (placebo), pacing $SCHED"
    $W/tools/live_policy/launch_pair.sh $c1 $c2 $s1 $d1 $SCHED $CAP >> $C/campaign_chain.log 2>&1
    prev_a=e1_${s1}_s${d1}_official_60m; prev_b=e1_${s1}_s${d1}_placebo_60m
  elif [ "$kind" = rerun ]; then
    names=""
    for spec in "$s1 $d1 $s2" "$d2 $p3 $p4"; do
      set -- $spec; [ -z "${3:-}" ] && continue
      orig=e1_${1}_s${2}_${3}_60m
      path=$(python3 -c "import glob,json,sys; print(max([json.load(open(f))['total_path_length_meters'] for f in glob.glob(sys.argv[1]+'/stages/*/navigation_stats.json')], default=0))" $orig)
      if python3 -c "import sys; sys.exit(0 if float(sys.argv[1]) >= 50 else 1)" $path; then log "rerun $orig skipped: reached $path m"; continue; fi
      c=$(idle | head -1); [ -z "$c" ] && { log "no idle container for rerun $orig; waiting"; sleep 120; c=$(idle | head -1); }
      OFFS=$(ls -d e1_*_official_60m 2>/dev/null | while read r; do grep -q "finished $r: target_reached" runner_*.log && echo $r; done)
      SCHED=$(python3 $W/tools/live_policy/pacing_update.py $OFFS | tail -1)
      python3 -c "import json,sys; o,p,sc,sd,sch=sys.argv[1:6]; r={'name':o+'_rerun1','scene':sc,'seed':int(sd),'policy':p,'target_m':60,'max_hours':4.5,'max_cost_usd':1.5 if p=='official' else 0.0}; r.update({'no_llm_delay_schedule':sch} if p=='placebo' else {}); json.dump({'runs':[r]}, open('queue_'+o+'_rerun1.json','w'))" $orig $3 $1 $2 $SCHED
      [ "$3" = placebo ] && echo "$(date +%H:%M) rerun ${orig}_rerun1 (stopped at $path m): placebo pacing from completed official runs ($(echo $OFFS)): $SCHED" >> DEVIATIONS.md
      log "launch rerun ${orig}_rerun1 on $c (original stopped at $path m)"
      $W/tools/live_policy/clean_container.sh $c > /dev/null
      $W/tools/live_policy/start_runner.sh $c queue_${orig}_rerun1.json 99 $CAP >> $C/campaign_chain.log 2>&1
      sleep 30
      names="$names ${orig}_rerun1"
    done
    set -- $names
    [ -n "${1:-}" ] && { prev_a=$1; prev_b=${2:-$1}; }
  else
    for spec in "$c1 $s1 $d1" "$c2 $s2 $d2"; do
      set -- $spec
      python3 -c "import json,sys; json.dump({'runs':[{'name':f'e2_{sys.argv[1]}_s{sys.argv[2]}_filter_only_60m','scene':sys.argv[1],'seed':int(sys.argv[2]),'policy':'filter_only','target_m':60,'max_cost_usd':1.5,'max_hours':4.5}]}, open(f'queue_e2_{sys.argv[1]}_s{sys.argv[2]}.json','w'))" $2 $3
      log "launch e2 $2/$3 on $1"
      $W/tools/live_policy/clean_container.sh $1 > /dev/null
      $W/tools/live_policy/start_runner.sh $1 queue_e2_$2_s$3.json 99 $CAP >> $C/campaign_chain.log 2>&1
    done
    prev_a=e2_${s1}_s${d1}_filter_only_60m; prev_b=e2_${s2}_s${d2}_filter_only_60m
  fi
  sleep 30
done < "$1"
log "all jobs launched"
