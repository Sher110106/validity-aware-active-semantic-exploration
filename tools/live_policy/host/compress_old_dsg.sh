#!/bin/bash
# Compress old graph files (*_dsg.json) in place with zstd, to free disk on the host
# (DEVIATIONS_NOVEMBER.md, item 62; approved by the student on 2026-11-17).
#
# Nothing is removed without proof: for each file it takes the sha256 of the raw file,
# compresses it, unpacks the result again, and removes the raw file only if the unpacked bytes
# give the same sha256. The hashes go to a list. `zstd -d <file>.zst` restores any file bit for bit.
#
# It works in runs/frontier_seeds and runs/live_campaign only, and leaves the four 871 seed
# folders of the November queue alone (the queue compressed those itself).
#
# Usage, on the host:  bash compress_old_dsg.sh --dry-run     (counts and sizes; changes nothing)
#                      bash compress_old_dsg.sh --go          (does the work)
# With --go it refuses to work while a paper queue or a runner is live, or while the container
# holds other processes: a timed run must not share the machine with it.
#
# COMPRESS_ROOTS="/workspace/runs/frontier_seeds" narrows the work to one of the two folders.
#
# For tests only: COMPRESS_LOCAL_ROOTS="dir1 dir2" COMPRESS_SCRATCH=dir runs the same steps in
# a plain shell on those folders, with no container and no checks for live runs. It refuses
# any folder inside the workspace.

set -u
MODE="${1:?give --dry-run or --go}"
case "$MODE" in --dry-run|--go) ;; *) echo "give --dry-run or --go"; exit 2 ;; esac
WS="${ASP_WS:-$HOME/active-semantic-perception-workspace}"
CONTAINER="${ASP_CONTAINER:-asp-noetic}"
export JOBS="${COMPRESS_JOBS:-4}"
STAMP="$(date +%Y%m%dT%H%M%S)"

if [ -n "${COMPRESS_LOCAL_ROOTS:-}" ]; then
  LOCAL=1; ROOTS="$COMPRESS_LOCAL_ROOTS"; SCRATCH="${COMPRESS_SCRATCH:?give COMPRESS_SCRATCH too}"; DFPATH="$SCRATCH"
  for r in $ROOTS; do case "$r" in /workspace|/workspace/*|"$WS"|"$WS"/*) echo "REFUSED: the test mode does not work inside the workspace ($r)"; exit 2 ;; esac; done
  run() { bash -c "$1"; }
else
  LOCAL=0; ROOTS="${COMPRESS_ROOTS:-/workspace/runs/frontier_seeds /workspace/runs/live_campaign}"; SCRATCH=/workspace/scratch; DFPATH="$WS"
  for r in $ROOTS; do case "$r" in /workspace/runs/frontier_seeds|/workspace/runs/live_campaign) ;; *) echo "REFUSED: $r is not one of the two run folders"; exit 2 ;; esac; done
  run() { docker exec -e LIST -e FAILS -e JOBS "$CONTAINER" bash -c "$1"; }   # the files belong to root in the container
fi
export LIST="$SCRATCH/dsg_compress_${STAMP}.sha256"
export FAILS="$SCRATCH/dsg_compress_${STAMP}.failed"
FIND="find $ROOTS -type f -name '*_dsg.json' -not -path '*/e7_00871_s4[2-5]_frontier_end/*'"
free_gb() { df -Pk "$DFPATH" | awk 'NR==2{printf "%d", $4/1048576}'; }

if [ "$MODE" = "--go" ] && [ "$LOCAL" = 0 ]; then
  live="$(systemctl --user list-units 'paper-queue-*.scope' --state=active,activating --no-legend --plain 2>/dev/null | awk '{print $1}')"
  [ -n "$live" ] && { echo "REFUSED: a rerun queue is live: $(echo $live)"; exit 1; }
  pgrep -u "$(id -u)" -f 'paper_queue\.sh' >/dev/null && { echo "REFUSED: a paper_queue.sh process is running"; exit 1; }
  pgrep -u "$(id -u)" -f 'live_runner\.py' >/dev/null && { echo "REFUSED: a live_runner.py process is running"; exit 1; }
  others="$(docker exec "$CONTAINER" ps -eo pid=,args= 2>/dev/null | grep -v -E '^ *1 |ps -eo pid=,args=' | grep -v '<defunct>' | grep -v '^$')"
  [ -n "$others" ] && { echo "REFUSED: the container holds other processes:"; printf '%s\n' "$others" | head -5; exit 1; }
fi

echo "start $(date '+%Y-%m-%d %H:%M:%S %Z'), mode $MODE, disk free $(free_gb) GB"
run "$FIND -print0 | xargs -0 wc -c" | awk -v roots="$ROOTS" '
  NF == 2 && $2 == "total" { next }
  { n++; s += $1; k = "other"; m = split(roots, r, " ")
    for (i = 1; i <= m; i++) if (index($2, r[i] "/") == 1) k = r[i]
    c[k]++; b[k] += $1 }
  END { printf "raw graph files to compress: %d, %.2f GB\n", n, s/1e9
        for (k in c) printf "  %s: %d files, %.2f GB\n", k, c[k], b[k]/1e9 }'

if [ "$MODE" = "--dry-run" ]; then
  echo "compressed files there already: $(run "find $ROOTS -type f -name '*_dsg.json.zst' | wc -l" | tr -d ' ')"
  echo "dry run: nothing changed"
  exit 0
fi

# One file: hash, compress, unpack and compare, and only then remove the raw file.
run '
one() {
  f="$1"
  [ -e "$f.zst" ] && { echo "exists already: $f.zst" >> "$FAILS"; return 0; }
  h="$(sha256sum < "$f" | cut -d" " -f1)"
  zstd -q -f -3 "$f" -o "$f.zst.part" || { echo "zstd failed: $f" >> "$FAILS"; rm -f "$f.zst.part"; return 0; }
  h2="$(zstd -q -dc < "$f.zst.part" | sha256sum | cut -d" " -f1)"
  if [ -n "$h" ] && [ "$h" = "$h2" ]; then mv "$f.zst.part" "$f.zst" && printf "%s  %s\n" "$h" "$f" >> "$LIST.part.$$" && rm -f "$f"
  else echo "round trip differs: $f" >> "$FAILS"; rm -f "$f.zst.part"; fi
}
export -f one
: > "$FAILS"
IO=""; command -v ionice >/dev/null 2>&1 && IO="ionice -c3"
'"$FIND"' -print0 | $IO nice -n 19 xargs -0 -P "$JOBS" -n 8 bash -c "for f in \"\$@\"; do one \"\$f\"; done" _
cat "$LIST".part.* 2>/dev/null | sort -k2 > "$LIST"
rm -f "$LIST".part.*
echo "compressed and checked: $(wc -l < "$LIST" | tr -d " ") files"
echo "not compressed: $(wc -l < "$FAILS" | tr -d " ") files (list: $FAILS)"
echo "hash list: $LIST, sha256 $(sha256sum < "$LIST" | cut -d" " -f1)"
'
echo "raw graph files left: $(run "$FIND | wc -l" | tr -d ' ')"
echo "end $(date '+%Y-%m-%d %H:%M:%S %Z'), disk free $(free_gb) GB"
