#!/bin/bash
# start_runner.sh <container> <queue.json> <display> : start live_runner.py detached on tyrone
W=/home/sher/active-semantic-perception-workspace
cd $W/runs/live_campaign || exit 1
tag=$(basename "$2" .json)
setsid nohup python3 $W/tools/live_policy/live_runner.py --container "$1" --queue "$2" --display "$3" --campaign-cap "$4" ${@:5} > "runner_${tag}.out" 2>&1 < /dev/null &
sleep 4
cat "runner_${tag}.out"
