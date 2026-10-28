#!/bin/bash
# launch_pair.sh <official_container> <placebo_container> <scene> <seed> <placebo_schedule> [campaign_cap]
set -e
W=/home/sher/active-semantic-perception-workspace
cd $W/runs/live_campaign
OC=$1; PC=$2; SC=$3; SD=$4; SCHED=$5; CAP=${6:-10.0}
for c in $OC $PC; do $W/tools/live_policy/clean_container.sh $c > /dev/null; done
python3 - "$OC" "$PC" "$SC" "$SD" "$SCHED" <<'PY'
import json, sys
oc, pc, sc, sd, sched = sys.argv[1:6]
sd = int(sd)
base = {'scene': sc, 'seed': sd, 'target_m': 60, 'max_hours': 4.5}
json.dump({'runs': [dict(base, name=f'e1_{sc}_s{sd}_official_60m', policy='official', max_cost_usd=1.5)]}, open(f'queue_pair_{sc}_s{sd}_official.json', 'w'))
json.dump({'runs': [dict(base, name=f'e1_{sc}_s{sd}_placebo_60m', policy='placebo', max_cost_usd=0.0, no_llm_delay_schedule=sched)]}, open(f'queue_pair_{sc}_s{sd}_placebo.json', 'w'))
PY
awk '/MemAvailable/{printf "MemAvailable %.1f GB\n", $2/1048576}' /proc/meminfo
$W/tools/live_policy/start_runner.sh $OC queue_pair_${SC}_s${SD}_official.json 99 $CAP
$W/tools/live_policy/start_runner.sh $PC queue_pair_${SC}_s${SD}_placebo.json 99 $CAP
