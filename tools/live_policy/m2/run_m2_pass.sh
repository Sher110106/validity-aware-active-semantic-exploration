#!/usr/bin/env bash
# Run one pass of the M2 study on the host, detached, then summarise it. Reads the saved runs; writes only under
# /home/sher/endsem_cpu/m2/<pass>/ and /tmp/cvp_review, /tmp/cvp_bench.
#
#   bash run_m2_pass.sh first DEEPSEEK_ERRORS.json
#       F1 F5 F6 F0 F-room and F3 with DeepSeek's error file -> m2/pass1/ (writes pass1/left_out_stages.json)
#   bash run_m2_pass.sh later HAIKU_ERRORS.json OPUS_ERRORS.json
#       F3 with the two Claude models -> m2/pass2/, summary of both passes on pass1's left-out list
#
# An error file is a JSON list of distances in metres. The run refuses unless PREREGISTRATION_M2.sha256 matches
# PREREGISTRATION_M2.md (factorial.py checks). 48 workers, nice 19, one thread each; 24 workers if less than
# 55 GB of memory is available at the start. NPROC overrides (never above 48).
set -euo pipefail

MODE=${1:?first|later}; shift
ROOT=${M2_ROOT:-/home/sher/endsem_cpu}
REPO=$ROOT/repo
M2=$REPO/tools/live_policy/m2
PY=$ROOT/venv/bin/python
case "$MODE" in
  first) [ $# -eq 1 ] || { echo "usage: run_m2_pass.sh first DEEPSEEK_ERRORS.json" >&2; exit 2; }; NAME=pass1 ;;
  later) [ $# -eq 2 ] || { echo "usage: run_m2_pass.sh later HAIKU_ERRORS.json OPUS_ERRORS.json" >&2; exit 2; }; NAME=pass2 ;;
  *) echo "mode must be first or later" >&2; exit 2 ;;
esac
OUT=$ROOT/m2/$NAME
LOG=$ROOT/m2/$NAME.log
for f in "$@"; do [ -s "$f" ] || { echo "MISSING or empty error file: $f" >&2; exit 2; }; done
if [ "$MODE" = later ]; then
  [ -s $ROOT/m2/pass1/PASS_COMPLETE ] || { echo "REFUSE: pass1/PASS_COMPLETE is missing: the first pass is not complete" >&2; exit 2; }
  [ -s $ROOT/m2/pass1/left_out_stages.json ] || { echo "MISSING pass1/left_out_stages.json: run the first pass first" >&2; exit 2; }
  [ -s $ROOT/m2/pass1/factorial_stages.jsonl ] || { echo "MISSING pass1/factorial_stages.jsonl" >&2; exit 2; }
fi
[ ! -e "$OUT/factorial_stages.jsonl" ] || { echo "REFUSE: $OUT already holds a pass; move it away first" >&2; exit 2; }

if [ -z "${M2_INNER:-}" ]; then   # detach: survive the ssh session
  export M2_INNER=1
  mkdir -p "$ROOT/m2"
  setsid systemd-run --user --scope --quiet -p MemoryMax=30G --unit="endsem-m2-$NAME-$(date +%H%M%S)" nice -n 19 bash "$0" "$MODE" "$@" > "$LOG" 2>&1 < /dev/null &
  echo "started $NAME; log $LOG; follow with: tail -f $LOG"
  exit 0
fi

export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
AVAIL=$(free -g | awk '/^Mem:/ {print $7}')
NPROC=${NPROC:-$(( AVAIL < 55 ? 24 : 48 ))}
[ "$NPROC" -le 48 ] || { echo "NPROC above 48 is not allowed" >&2; exit 2; }
echo "start $(date -Is) mode=$MODE nproc=$NPROC available_memory_gb=$AVAIL"

# the bench's /tmp farm (made by rebuild_bench_host.sh); rebuild it if it is gone
if [ ! -e /tmp/cvp_review/audit/audit/stages.jsonl ] || [ ! -d /tmp/cvp_review/runs ] || [ ! -e /tmp/cvp_bench/refs/00853_walls.npz ]; then
  bash "$M2/rebuild_bench_host.sh" --no-run
fi

mkdir -p "$OUT"
cd "$ROOT/m2"
START=$(date +%s)
if [ "$MODE" = first ]; then
  "$PY" -B "$M2/factorial.py" --out "$OUT" --nproc "$NPROC" --arms F1,F5,F6,F0,F-room,F3 --error-file "deepseek=$1"
  echo "study wall seconds: $(( $(date +%s) - START ))"
  "$PY" -B "$M2/summarise_factorial.py" "$OUT/factorial_stages.jsonl" --left-out "$OUT/left_out_stages.json" --out "$OUT/summary_factorial.json" | tee "$OUT/summary_factorial.txt"
else
  "$PY" -B "$M2/factorial.py" --out "$OUT" --nproc "$NPROC" --arms F3 --error-file "haiku=$1" --error-file "opus=$2"
  echo "study wall seconds: $(( $(date +%s) - START ))"
  "$PY" -B "$M2/summarise_factorial.py" "$ROOT/m2/pass1/factorial_stages.jsonl" "$OUT/factorial_stages.jsonl" \
        --left-out "$ROOT/m2/pass1/left_out_stages.json" --out "$OUT/summary_factorial.json" | tee "$OUT/summary_factorial.txt"
fi
echo "done $(date -Is); total wall seconds: $(( $(date +%s) - START ))"
