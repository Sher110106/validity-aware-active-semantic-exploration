#!/bin/bash
# frontier_seeds_analysis.sh [copy_dir] [out_dir]
# Plan step 7 (PREREGISTRATION_FRONTIER_SEEDS.md): score the six seeded
# frontier runs from the off-host copy, merge them with the campaign's
# all_scores.json, and run the two registered contrasts (official - frontier,
# placebo - frontier) with e1_analysis.py at 60 m and 50 m on the HM3D
# reference. Holm over the two 60 m p-values is applied in frontier_holm.json.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
COPY=${1:-/Users/sher/cvp_live_campaign_copy}
OUT=${2:-$HERE/results_2026-10-31/frontier_seeds}
PY=${PY:-$REPO/.venv_offline/bin/python}
C=$COPY/runs/live_campaign
F=$COPY/runs/frontier_seeds
export ASP_WORKSPACE=$COPY PYTHONPATH=$REPO/tools:$REPO/tools/evaluator PYTHONDONTWRITEBYTECODE=1
mkdir -p "$OUT"
cd "$HERE"

args=""
for r in "$F"/e4_*_frontier_60m; do
  args="$args $r=$(basename "$r" | sed -E 's/^e[0-9]+_([0-9]{5})_.*/\1/')"
done
"$PY" -B live_score.py $args > "$OUT/frontier_seeds_scores.raw.json"
# Same /workspace prefix as the campaign rows, then merge.
"$PY" - "$OUT/frontier_seeds_scores.raw.json" "$HERE/results_2026-10-31/analysis/all_scores.json" "$OUT/all_scores_with_frontier.json" "$COPY" <<'EOF'
import json, sys
new = json.load(open(sys.argv[1]))
for r in new:
    if "error" in r:
        sys.exit(f"scoring error: {r}")
    for k in ("run_dir", "reference", "hm3d_reference"):
        if isinstance(r.get(k), str) and r[k].startswith(sys.argv[4]):
            r[k] = "/workspace" + r[k][len(sys.argv[4]):]
old = json.load(open(sys.argv[2]))
json.dump(old + new, open(sys.argv[3], "w"), indent=1)
print(f"{len(old)} campaign rows + {len(new)} frontier rows", file=sys.stderr)
EOF

for b in 60 50; do
  common="--budget $b --ref hm3d_ --exclude-dir $C"
  "$PY" -B e1_analysis.py "$OUT/all_scores_with_frontier.json" --a official --b frontier $common > "$OUT/E4_official_vs_frontier_hm3d_${b}m.json"
  "$PY" -B e1_analysis.py "$OUT/all_scores_with_frontier.json" --a placebo --b frontier $common > "$OUT/E4_placebo_vs_frontier_hm3d_${b}m.json"
done

"$PY" - "$OUT" <<'EOF'
import json, sys
out = sys.argv[1]
res = {}
for c in ("official", "placebo"):
    r60 = json.load(open(f"{out}/E4_{c}_vs_frontier_hm3d_60m.json"))
    r50 = json.load(open(f"{out}/E4_{c}_vs_frontier_hm3d_50m.json"))
    res[c] = {"d60": r60["statistic"], "p60": r60["blocked_permutation_p"], "ci60": r60["permutation_95ci"],
              "n_relabelings": r60["n_relabelings"], "min_attainable_p": r60["min_attainable_p"],
              "mde60": r60["mde_alpha05_power80"], "per_scene60": r60["per_scene"],
              "d50": r50["statistic"], "p50": r50["blocked_permutation_p"],
              "signs_agree": (r60["statistic"] > 0) == (r50["statistic"] > 0)}
# Holm over the two registered contrasts (60 m p-values).
order = sorted(res, key=lambda c: res[c]["p60"])
running = 0.0
for i, c in enumerate(order):
    running = max(running, min(1.0, (len(order) - i) * res[c]["p60"]))
    res[c]["p60_holm"] = running
for c in res:
    res[c]["significant"] = res[c]["p60_holm"] < 0.05 and res[c]["signs_agree"]
json.dump(res, open(f"{out}/frontier_holm.json", "w"), indent=1)
print(json.dumps(res, indent=1))
EOF
