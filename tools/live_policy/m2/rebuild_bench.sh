#!/usr/bin/env bash
# Rebuild the October offline bench from scratch and compare it with the
# registered output. Read-only on tools/live_policy/review_2026-10-29/ and on
# results_2026-10-31/. Writes only /tmp/cvp_review, /tmp/cvp_bench and $SCRATCH.
#
#   bash tools/live_policy/m2/rebuild_bench.sh            # farm + copy + run + compare
#   bash tools/live_policy/m2/rebuild_bench.sh --no-run   # farm + copy only
#
# Env: NPROC (default 6), SCRATCH, OFFHOST, PY.
set -euo pipefail

REPO=${REPO:-/Users/sher/project/cvp/project}
OFFHOST=${OFFHOST:-/Users/sher/cvp_live_campaign_copy}
SCRATCH=${SCRATCH:-/Users/sher/project/cvp/scratch_m2}
PY=${PY:-$REPO/.venv_offline/bin/python}
NPROC=${NPROC:-6}

LP=$REPO/tools/live_policy
REV=$LP/review_2026-10-29
REG=$REV/bench/build            # registered output; never written
RES=$LP/results_2026-10-31

FARM=/tmp/cvp_review
BENCHREFS=/tmp/cvp_bench
COPY=$SCRATCH/bench_copy

export PYTHONDONTWRITEBYTECODE=1   # no __pycache__ next to the repo files

# 1. Check every input first.
need() { [ -e "$1" ] || { echo "MISSING: $1" >&2; miss=1; }; }
miss=0
need "$OFFHOST/runs/live_campaign"
need "$REPO/tools/decision_replay_reference/calculate_uncertainty.py"
need "$LP/live_policy.py"
need "$LP/placebo_calibration.json"
need "$RES/oracle_sets.json"
need "$RES/analysis/runs.txt"
need "$REV/A/parsed_runs.json"
need "$REV/A/replay2_results.jsonl"
need "$REV/audit/audit/stages.jsonl"
need "$REV/bench/walls/00853_walls.npz"
need "$REV/bench/walls/00871_walls.npz"
need "$REG/stages.jsonl"
need "$PY"
[ "$miss" = 0 ] || exit 2

# 2. Symlink farm. Rebuilt from nothing each time.
rm -rf "$FARM" "$BENCHREFS"
mkdir -p "$FARM/refs" "$FARM/analysis_pre" "$FARM/pipeline_pinned_copy/scripts" \
         "$FARM/work_A" "$FARM/audit/audit" "$BENCHREFS/refs"

# work_A and audit/audit are real folders that hold one symlink per repo file.
# A folder link would send the scratch writes (work_A/tmp) into the repo.
for f in "$REV"/A/*;            do ln -s "$f" "$FARM/work_A/$(basename "$f")"; done
for f in "$REV"/audit/audit/*;  do ln -s "$f" "$FARM/audit/audit/$(basename "$f")"; done
mkdir -p "$FARM/work_A/tmp"

ln -s "$OFFHOST/runs/live_campaign" "$FARM/runs"
ln -s "$RES/oracle_sets.json" "$FARM/refs/oracle_sets.json"
ln -s "$REPO/tools/decision_replay_reference/calculate_uncertainty.py" \
      "$FARM/pipeline_pinned_copy/scripts/calculate_uncertainty.py"
head -24 "$RES/analysis/runs.txt" > "$FARM/analysis_pre/runs.txt"   # line 25 (e3_00871_s44) is not in the bench
for s in 00853 00871; do ln -s "$REV/bench/walls/${s}_walls.npz" "$BENCHREFS/refs/${s}_walls.npz"; done

# 3. Working copy of the bench code. The registered stages.jsonl is not copied.
rm -rf "$COPY"
mkdir -p "$COPY"
for f in bench.py summarize.py report.py crosscheck.py; do cp "$REG/$f" "$COPY/$f"; done

echo "farm: $FARM, $BENCHREFS; copy: $COPY"
[ "${1:-}" = "--no-run" ] && exit 0

# 4. Run the bench from the copy.
cd "$COPY"
df -h /Users/sher | tail -1 | sed 's/^/disk before: /'
START=$(date +%s)
NPROC=$NPROC "$PY" -B bench.py 2>&1 | tee "$SCRATCH/bench_run_log.txt" | tail -3
echo "bench wall seconds: $(( $(date +%s) - START ))"
df -h /Users/sher | tail -1 | sed 's/^/disk after:  /'

# 5. Registered summaries on the new output (registered code, run in the copy).
"$PY" -B summarize.py > "$SCRATCH/summarize_log.txt" 2>&1 || echo "summarize.py failed; see $SCRATCH/summarize_log.txt"

# 6. Compare with the registered output.
"$PY" -B - "$REG" "$COPY" <<'PYEOF'
import json, sys
reg_dir, new_dir = sys.argv[1], sys.argv[2]
load = lambda p: {(r["run"], r["stage"]): r for r in map(json.loads, open(p))}
R, N = load(f"{reg_dir}/stages.jsonl"), load(f"{new_dir}/stages.jsonl")
print("stages registered / new:", len(R), len(N), "| keys equal:", set(R) == set(N))
SETS = ["actual", "none", "placebo_A", "placebo_B", "oracle"]
RULES = ["R1", "R2", "R3", "R4", "R5"]
tot = ok = 0
bad = []
for k in sorted(R):
    r, n = R[k], N.get(k, {})
    for s in SETS:
        for u in RULES:
            tot += 1
            a = r["picks"][s][u]
            b = n.get("picks", {}).get(s, {}).get(u)
            if a == b:
                ok += 1
            else:
                bad.append((k, s, u, a, b))
print(f"picks identical: {ok} of {tot}")
for b in bad[:40]:
    print("  MISMATCH stage", b[0], "set", b[1], "rule", b[2], "registered cand", b[3], "new cand", b[4])
more = {"r6_picks": 0, "Uwall": 0, "Ucone": 0, "regret": 0, "top10_match": 0, "n_cand": 0}
for k in R:
    for key in more:
        if R[k].get(key) != N.get(k, {}).get(key):
            more[key] += 1
print("stages whose field differs (0 = all equal):", more)
errs = [k for k, v in N.items() if "error" in v or "drop" in v]
print("new rows with error or drop:", errs)
try:
    rs, ns = json.load(open(f"{reg_dir}/summary.json")), json.load(open(f"{new_dir}/summary.json"))
    for r in ["R1", "R2", "R3", "R4"]:
        a, b = rs["decision"][r]["a"] if "a" in rs["decision"][r] else rs["decision"][r], ns["decision"][r]
        b = b["a"] if "a" in b else b
        print(r, "ratio registered", round(a["ratio"], 4), "new", round(b["ratio"], 4), "equal:", a["ratio"] == b["ratio"])
    print("go_live registered", rs["decision"]["go_live"], "new", ns["decision"]["go_live"])
    print("summary.json identical:", rs == ns)
except Exception as e:
    print("summary compare failed:", repr(e))
PYEOF
