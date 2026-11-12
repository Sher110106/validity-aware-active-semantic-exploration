#!/usr/bin/env bash
# Start the step-8 determinism queue once the step-7 frontier queue is done.
W=/home/sher/active-semantic-perception-workspace; C=$W/runs/live_campaign
until grep -q "queue done" $W/runs/frontier_seeds/queue.log 2>/dev/null; do sleep 120; done
echo "$(date -Iseconds) frontier queue done; starting determinism queue" >> $C/chain_determinism.log
cd $W/tools/live_policy && python3 live_runner.py --container asp-noetic --queue $C/queue_determinism.json \
  --display 99 --campaign-cap 0 > $C/runner_determinism.out 2>&1
echo "$(date -Iseconds) determinism queue finished (rc=$?)" >> $C/chain_determinism.log
