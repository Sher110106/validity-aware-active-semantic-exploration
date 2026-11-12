#!/bin/bash
# convert_runs.sh <run_name>...: write habitat_scene_graph_original_graph{0,1}.yaml
# into every stage of each frontier_seeds run, with the author's converter
# (convert_frontier_reference.py imports f1_score_plot.convert_dsg_to_yaml).
for run in "$@"; do
  for sd in /home/sher/active-semantic-perception-workspace/runs/frontier_seeds/$run/stages/*/; do
    k=$(basename "$sd")
    [ -f "$sd/graph0_dsg.json" ] || continue
    docker exec asp-noetic bash -c "nice -n 19 /workspace/environments/semantic_perception/bin/python -B /workspace/runs/frontier_seeds/convert_frontier_reference.py /workspace/runs/frontier_seeds/$run/stages/$k 2>&1 | grep -E '^(wrote|MISSING)'" \
      | sed "s|^|$(date -Iseconds) |"
  done
  echo "$(date -Iseconds) converted $run"
done
