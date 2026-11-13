#!/usr/bin/env bash
# Host version of rebuild_bench.sh: rebuild the October offline bench on the
# shared 112-core host and compare it with the registered output.
# Read-only on the repo clone's review_2026-10-29/ and results_2026-10-31/ and on
# the saved runs. Writes only /tmp/cvp_review, /tmp/cvp_bench and $WORK.
#
#   bash rebuild_bench_host.sh            # farm + copy + run + compare
#   bash rebuild_bench_host.sh --no-run   # farm + copy only
#
# Env: NPROC (default 48; never more), WORK, REPO, RUNS, PY.
# Start a long run from ssh as:
#   systemd-run --user --scope --quiet --unit=endsem-rebuild-bench \
#     nice -n 19 bash /home/sher/endsem_cpu/repo/tools/live_policy/m2/rebuild_bench_host.sh
set -euo pipefail

REPO=${REPO:-/home/sher/endsem_cpu/repo}
WORK=${WORK:-/home/sher/endsem_cpu/m2}
RUNS=${RUNS:-/home/sher/active-semantic-perception-workspace/runs/live_campaign}
PY=${PY:-/home/sher/endsem_cpu/venv/bin/python}
NPROC=${NPROC:-48}
[ "$NPROC" -le 48 ] || { echo "NPROC above 48 is not allowed" >&2; exit 2; }

LP=$REPO/tools/live_policy
REV=$LP/review_2026-10-29
REG=$REV/bench/build            # registered output; never written
RES=$LP/results_2026-10-31

FARM=/tmp/cvp_review
BENCHREFS=/tmp/cvp_bench
COPY=$WORK/bench_copy

export PYTHONDONTWRITEBYTECODE=1   # no __pycache__ next to the repo files
# One thread per worker: 48 workers must not each start a BLAS pool.
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

# 1. Check every input first.
need() { [ -e "$1" ] || { echo "MISSING: $1" >&2; miss=1; }; }
miss=0
need "$RUNS"
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

# The bench's paths are hard-coded under /tmp. Remove a folder only if it is mine.
for d in "$FARM" "$BENCHREFS"; do
  if [ -e "$d" ] || [ -L "$d" ]; then
    [ -O "$d" ] || { echo "REFUSE: $d is not owned by $(id -un)" >&2; exit 2; }
    rm -rf "$d"
  fi
done

# 2. Symlink farm, mode 700.
umask 077
mkdir -m 700 "$FARM" "$BENCHREFS"
mkdir -p "$FARM/refs" "$FARM/analysis_pre" "$FARM/pipeline_pinned_copy/scripts" \
         "$FARM/work_A" "$FARM/audit/audit" "$BENCHREFS/refs" "$WORK"

# work_A and audit/audit are real folders that hold one symlink per repo file.
for f in "$REV"/A/*;            do ln -s "$f" "$FARM/work_A/$(basename "$f")"; done
for f in "$REV"/audit/audit/*;  do ln -s "$f" "$FARM/audit/audit/$(basename "$f")"; done
mkdir -p "$FARM/work_A/tmp"

# replay.py loads live_policy.py by an absolute Mac path (line 43). On the host
# that path does not exist, so work_A/replay.py is a copy with that one path
# changed to this clone. Nothing else differs; checked below.
rm "$FARM/work_A/replay.py"
sed "s#/Users/sher/project/cvp/project/tools/live_policy/live_policy.py#$LP/live_policy.py#" \
    "$REV/A/replay.py" > "$FARM/work_A/replay.py"
[ "$(diff "$REV/A/replay.py" "$FARM/work_A/replay.py" | grep -c '^>')" = 1 ] \
  || { echo "replay.py patch changed more than one line" >&2; exit 2; }

ln -s "$RUNS" "$FARM/runs"
ln -s "$RES/oracle_sets.json" "$FARM/refs/oracle_sets.json"
ln -s "$REPO/tools/decision_replay_reference/calculate_uncertainty.py" \
      "$FARM/pipeline_pinned_copy/scripts/calculate_uncertainty.py"
head -24 "$RES/analysis/runs.txt" > "$FARM/analysis_pre/runs.txt"   # line 25 (e3_00871_s44) is not in the bench
for s in 00853 00871; do ln -s "$REV/bench/walls/${s}_walls.npz" "$BENCHREFS/refs/${s}_walls.npz"; done

# 3. Working copy of the bench code. The registered stages.jsonl is not copied.
rm -rf "$COPY"
mkdir -p "$COPY"
for f in bench.py summarize.py report.py crosscheck.py; do cp "$REG/$f" "$COPY/$f"; done

echo "farm: $FARM, $BENCHREFS; copy: $COPY; python: $("$PY" -c 'import sys,numpy;print(sys.version.split()[0],"numpy",numpy.__version__)')"
[ "${1:-}" = "--no-run" ] && exit 0

# 4. Run the bench from the copy.
cd "$COPY"
free -g | sed -n 2p | sed 's/^/memory before: /'
START=$(date +%s)
NPROC=$NPROC "$PY" -B bench.py > "$WORK/bench_run_log.txt" 2>&1 || echo "bench.py exited with an error; see $WORK/bench_run_log.txt"
tail -3 "$WORK/bench_run_log.txt"
echo "bench wall seconds: $(( $(date +%s) - START ))"

# 5. Registered summaries on the new output (registered code, run in the copy).
"$PY" -B summarize.py > "$WORK/summarize_log.txt" 2>&1 || echo "summarize.py failed; see $WORK/summarize_log.txt"
echo "total wall seconds: $(( $(date +%s) - START ))"

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
