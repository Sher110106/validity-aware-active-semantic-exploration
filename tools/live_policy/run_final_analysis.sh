#!/bin/bash
# run_final_analysis.sh [out_dir] : inside asp-noetic-e, score every live run and run the
# registered analyses (FINAL_PLAN_2026-10-29.md sections 4-5; PREREGISTRATION_E1/E2/E3.md).
#   docker exec asp-noetic-e bash /workspace/tools/live_policy/run_final_analysis.sh /tmp/final
set -e
source /workspace/environments/semantic_perception/bin/activate
export PYTHONDONTWRITEBYTECODE=1 MAGNUM_LOG=quiet HABITAT_SIM_LOG=quiet
cd /workspace/tools/live_policy
C=/workspace/runs/live_campaign
O=${1:-/tmp/final_analysis}
E3_SEEDS=${E3_SEEDS:-42,43,44}
mkdir -p "$O"
RUNS=$(cd $C && ls -d e1_*_60m* e2_*_60m* e3_*_60m* 2>/dev/null | grep -v "FAILED\|ABORTED" | sort -u)
echo "$RUNS" > "$O/runs.txt"
args=""
for r in $RUNS; do args="$args $C/$r=$(echo $r | sed -E 's/^e[0-9]+_([0-9]{5})_.*/\1/')"; done
python -B live_score.py $args > "$O/all_scores.json" 2> "$O/live_score.err"
for ref in hm3d_ none; do
  r=$ref; [ "$ref" = none ] && r=""
  tag=${ref%_}; [ "$ref" = none ] && tag=frontier
  for b in 60 50; do
    common="--budget $b --ref $r --exclude-dir $C"
    [ -z "$r" ] && common="--budget $b --ref= --exclude-dir $C"
    python -B e1_analysis.py "$O/all_scores.json" --a official --b placebo $common > "$O/E1_${tag}_${b}m.json"
    python -B e1_analysis.py "$O/all_scores.json" --a official --b filter_only $common > "$O/E2_${tag}_${b}m.json"
    python -B e1_analysis.py "$O/all_scores.json" --a oracle_visible --b placebo --seeds "$E3_SEEDS" $common > "$O/E3_${tag}_${b}m.json"
    python -B e1_analysis.py "$O/all_scores.json" --a oracle_visible --b official --seeds "$E3_SEEDS" $common > "$O/E3_vs_official_${tag}_${b}m.json"
  done
done
python -B stage_precision.py $C "$O/stage_precision.json" $RUNS > /dev/null
python -B stage_diagnostics.py $C "$O/stage_diagnostics.json" $RUNS > /dev/null
python -B covariates.py $C "$O/covariates.json" $RUNS > /dev/null
python -B later_found.py $C "$O/later_found.json" $RUNS > /dev/null
echo "done: $O"
