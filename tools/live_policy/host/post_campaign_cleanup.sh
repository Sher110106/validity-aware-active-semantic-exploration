#!/bin/bash
# Remove the extra campaign containers, their catkin_ws copies and the live image.
# Run only after the campaign has ended and every run is scored: asp-noetic-e is
# the scoring container. Run outputs live in runs/live_campaign and are kept.
# Usage: post_campaign_cleanup.sh [--yes]   (without --yes it only reports)
set -u
W=/home/sher/active-semantic-perception-workspace
EXTRA="asp-noetic-b asp-noetic-c asp-noetic-d asp-noetic-f asp-noetic-g asp-noetic-e"
IMAGE=asp-noetic:live-2026-10-28

busy=0
if pgrep -f campaign_chain.sh >/dev/null || pgrep -f live_runner.py >/dev/null; then
  echo "campaign chain or a runner is still running"; busy=1
fi
for c in asp-noetic $EXTRA; do
  docker inspect "$c" >/dev/null 2>&1 || continue
  if docker exec "$c" pgrep -f "run_pipeline_with_policy|exploration_pipeline" >/dev/null 2>&1; then
    echo "$c still runs a pipeline"; busy=1
  fi
done
ls "$W"/runs/live_campaign/.active_* >/dev/null 2>&1 && { echo "active run markers remain"; busy=1; }
[ $busy = 0 ] || { echo "refusing to clean up"; exit 1; }

echo "would remove: $EXTRA, $IMAGE, $W/parallel/{b,c,d,f,g}"
du -sh "$W"/parallel/* 2>/dev/null
[ "${1:-}" = "--yes" ] || exit 0

for c in $EXTRA; do docker rm -f "$c" 2>/dev/null && echo "removed $c"; done
# The catkin_ws copies hold root-owned build files; delete them as root in the main container.
docker exec asp-noetic rm -rf /workspace/parallel/b /workspace/parallel/c /workspace/parallel/d \
  /workspace/parallel/f /workspace/parallel/g && echo "removed parallel workspaces"
rmdir "$W/parallel" 2>/dev/null || docker exec asp-noetic rmdir /workspace/parallel 2>/dev/null
docker rmi "$IMAGE" && echo "removed $IMAGE"
docker ps -a --format '{{.Names}}\t{{.Image}}' | grep asp
df -h /home | tail -1
