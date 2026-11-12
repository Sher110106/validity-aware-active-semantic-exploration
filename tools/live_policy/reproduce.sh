#!/bin/bash
# reproduce.sh [copy_dir] [expected_dir] [out_dir]
# Regenerate all_scores.json and the E1/E2/E3 analysis JSONs from the off-host
# copy of the live campaign, then compare them with the committed outputs
# (FINAL_PLAN_2026-10-29.md section 7, item 3). The copy is laid out like the
# host's /workspace: <copy>/runs/live_campaign/<run>/stages/... plus the two
# frontier reference graphs under <copy>/runs/scene*_frontier_reference/.
# The run list is the committed runs.txt, so the same runs are scored.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
COPY=${1:-/Users/sher/cvp_live_campaign_copy}
EXPECTED=${2:-$HERE/results_2026-10-31/analysis}
OUT=${3:-$(mktemp -d)}
PY=${PY:-$REPO/.venv_offline/bin/python}
C=$COPY/runs/live_campaign
E3_SEEDS=${E3_SEEDS:-42,43,44}
export ASP_WORKSPACE=$COPY PYTHONPATH=$REPO/tools:$REPO/tools/evaluator PYTHONDONTWRITEBYTECODE=1
mkdir -p "$OUT"
cd "$HERE"

args=""
while read -r r; do
  [ -z "$r" ] && continue
  args="$args $C/$r=$(echo "$r" | sed -E 's/^e[0-9]+_([0-9]{5})_.*/\1/')"
done < "$EXPECTED/runs.txt"
cp "$EXPECTED/runs.txt" "$OUT/runs.txt"
"$PY" -B live_score.py $args > "$OUT/all_scores.raw.json"
# The host read everything under /workspace; put that prefix back on the path fields.
"$PY" - "$OUT/all_scores.raw.json" "$OUT/all_scores.json" "$COPY" <<'EOF'
import json, sys
rows = json.load(open(sys.argv[1]))
for r in rows:
    for k in ("run_dir", "reference", "hm3d_reference"):
        if isinstance(r.get(k), str) and r[k].startswith(sys.argv[3]):
            r[k] = "/workspace" + r[k][len(sys.argv[3]):]
json.dump(rows, open(sys.argv[2], "w"), indent=1)
EOF

for ref in hm3d_ none; do
  tag=${ref%_}; [ "$ref" = none ] && tag=frontier
  for b in 60 50; do
    if [ "$ref" = none ]; then common="--budget $b --ref= --exclude-dir $C"; else common="--budget $b --ref $ref --exclude-dir $C"; fi
    "$PY" -B e1_analysis.py "$OUT/all_scores.json" --a official --b placebo $common > "$OUT/E1_${tag}_${b}m.json"
    "$PY" -B e1_analysis.py "$OUT/all_scores.json" --a official --b filter_only $common > "$OUT/E2_${tag}_${b}m.json"
    "$PY" -B e1_analysis.py "$OUT/all_scores.json" --a oracle_visible --b placebo --seeds "$E3_SEEDS" $common > "$OUT/E3_${tag}_${b}m.json"
    "$PY" -B e1_analysis.py "$OUT/all_scores.json" --a oracle_visible --b official --seeds "$E3_SEEDS" $common > "$OUT/E3_vs_official_${tag}_${b}m.json"
  done
done

# Registered E2 latency rule (DEVIATIONS item 21d): E2 without cells 00853/42 and 00871/44.
printf '["e1_00853_s42_official_60m","e2_00853_s42_filter_only_60m","e1_00871_s44_official_60m","e2_00871_s44_filter_only_60m"]' > "$OUT/latency_cells.json"
for b in 60 50; do
  "$PY" -B e1_analysis.py "$OUT/all_scores.json" --a official --b filter_only --budget $b --ref hm3d_ --exclude-dir $C --exclude "$OUT/latency_cells.json" > "$OUT/E2_hm3d_${b}m_latency_rule.json"
done
# Registered secondary metrics (canonical F1, recall, nGED AUC to 60 m, HM3D reference).
mkdir -p "$OUT/secondary"
for m in object_f1 af_recall object_recall normalized_ged; do
  "$PY" -B e1_analysis.py "$OUT/all_scores.json" --a official --b placebo --metric $m --budget 60 --ref hm3d_ --exclude-dir $C > "$OUT/secondary/E1_hm3d_${m}_60m.json"
  "$PY" -B e1_analysis.py "$OUT/all_scores.json" --a official --b filter_only --metric $m --budget 60 --ref hm3d_ --exclude-dir $C > "$OUT/secondary/E2_hm3d_${m}_60m.json"
  "$PY" -B e1_analysis.py "$OUT/all_scores.json" --a oracle_visible --b placebo --seeds "$E3_SEEDS" --metric $m --budget 60 --ref hm3d_ --exclude-dir $C > "$OUT/secondary/E3_hm3d_${m}_60m.json"
done

# Compare parsed JSON, so key order and whitespace do not count. Strings and
# integers must match exactly; floats may differ by 1e-12 relative, because the
# host container's older Python sums statistics.mean in a different order
# (seen as last-digit differences in mde_alpha05_power80).
"$PY" - "$EXPECTED" "$OUT" <<'EOF'
import glob, json, math, os, sys
exp, out = sys.argv[1], sys.argv[2]

def close(a, b, path, diffs):
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            diffs.append(f"{path}: keys differ")
        for k in set(a) & set(b):
            close(a[k], b[k], f"{path}/{k}", diffs)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append(f"{path}: length {len(a)} vs {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            close(x, y, f"{path}[{i}]", diffs)
    elif isinstance(a, float) or isinstance(b, float):
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-15)):
            diffs.append(f"{path}: {a} vs {b}")
    elif a != b:
        diffs.append(f"{path}: {a!r} vs {b!r}")

# Only the files this script generates; the F1-point secondaries, extra_tables.json
# and agreement.json come from results_2026-10-31/scripts and are not compared here.
names = ["all_scores.json"] + sorted(os.path.relpath(p, out) for p in glob.glob(os.path.join(out, "E*.json")) + glob.glob(os.path.join(out, "secondary", "E*_60m.json")))
bad = exact = 0
for n in names:
    a = json.load(open(os.path.join(exp, n)))
    b = json.load(open(os.path.join(out, n)))
    diffs = []
    close(a, b, "", diffs)
    exact += a == b
    bad += bool(diffs)
    print(("exact   " if a == b else "within 1e-12 " if not diffs else "DIFFERS ") + n + ("".join("\n    " + d for d in diffs[:5])))
print(f"{len(names) - bad} of {len(names)} files reproduce ({exact} exactly); output in {out}")
sys.exit(1 if bad else 0)
EOF
