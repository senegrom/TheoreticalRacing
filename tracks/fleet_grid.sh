#!/bin/sh
# The 8-car lap grid: every lap-capable track x a seed range, one JVM per track.
#
# This is the campaign's primary instrument. The unit is a batch race
# (--seed A-B), which builds the track's reachability once and reuses it
# in-process, so a track costs one BFS plus N races. Tracks run in parallel
# over a work queue; a track that already has a result row is skipped, so an
# interrupted grid resumes by re-running the same command.
#
#   sh tracks/fleet_grid.sh                    # seeds 1-10, all cores
#   sh tracks/fleet_grid.sh 11-20 8 /mnt/f216  # a fresh-seed slice, 8 wide
#
# Output is one row per (track, seed):
#   <track> <seed> fin=<n> crash=<n> timeout=<n> moves=<n>
# and one summary line, F216DONE-style, that a ship-or-revert round compares
# against the previous build. Tracks that cannot be lapped print NOLOOP.
#
# RACING_REACH_CACHE should point at a disk that survives the run; rebuilding
# the maps costs far more than the races do. On the AWS box that is an instance
# directory, so a later grid on the same build starts warm.
set -u
cd "$(dirname "$0")/.."
SEEDS="${1:-1-10}"
JOBS="${2:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}"
OUT="${3:-${TMPDIR:-/tmp}/fleet_grid}"
JAR="${RACING_JAR:-$PWD/theoreticRacing.jar}"
JAVA="${RACING_JAVA:-java}"
PROPS="${RACING_PROPS:-$PWD/tracks/lap_bench.properties}"
# 8 GB is sized for the biggest board in the fleet: the Nordschleife's 89M
# states carry ~2.5 GB of arrays and it dies with OutOfMemoryError below 6 GB.
HEAP="${RACING_HEAP:--Xmx8g}"
mkdir -p "$OUT"
export OUT JAR JAVA PROPS HEAP SEEDS

cat > "$OUT/worker.sh" <<'WORKER'
race_track() {
  t=$1
  [ -s "$OUT/$t.row" ] && return 0
  "$JAVA" $HEAP -Djava.awt.headless=true -jar "$JAR" --auto --track "$t" \
    --props "$PROPS" --log "$OUT/$t.log" --seed "$SEEDS" > "$OUT/$t.out" 2>&1
  # A course with no lap gates races once instead of three times, and a name
  # the jar cannot resolve must not pass as a row of quiet MISSING seeds.
  if grep -q 'laps disabled' "$OUT/$t.out"; then echo "$t NOLOOP" > "$OUT/$t.row"; return 0; fi
  if grep -q 'Track not found' "$OUT/$t.out"; then echo "$t NOTRACK" > "$OUT/$t.row"; return 0; fi
  : > "$OUT/$t.row"
  lo=${SEEDS%%-*}; hi=${SEEDS##*-}
  s=$lo
  while [ "$s" -le "$hi" ]; do
    log="$OUT/${t}_s$s.log"
    if [ -f "$log" ]; then
      printf '%s %s fin=%s crash=%s timeout=%s moves=%s\n' "$t" "$s" \
        "$(grep -c FINISH "$log")" "$(grep -c CRASH "$log")" \
        "$(grep -c TIMEOUT "$log")" "$(grep -cE '^[0-9]+ p' "$log")" >> "$OUT/$t.row"
    else
      echo "$t $s MISSING" >> "$OUT/$t.row"
    fi
    s=$((s + 1))
  done
}
WORKER

# RACING_TRACKS names a subset (comma or space separated) to re-run a few
# tracks without the rest of the grid; unset means the whole fleet.
if [ -n "${RACING_TRACKS:-}" ]; then
  echo "$RACING_TRACKS" | tr ', ' '\n\n' | grep -v '^$'
else
  ls tracks/*.track | sed 's#.*/##; s#\.track$##'
fi | xargs -P "$JOBS" -I{} sh -c '. "$OUT/worker.sh"; race_track "$1"' _ {} > /dev/null 2>&1
cat "$OUT"/*.row > "$OUT/fleet.txt"
sum() { grep -o "$1=[0-9]*" "$OUT/fleet.txt" | cut -d= -f2 | awk '{s+=$1} END{print s+0}'; }
bad=$(grep -c 'NOTRACK\|MISSING' "$OUT/fleet.txt" || true)
echo "FLEETDONE seeds=$SEEDS races=$(grep -c ' fin=' "$OUT/fleet.txt")" \
     "crashes=$(sum crash) timeouts=$(sum timeout) moves=$(sum moves) unusable=$bad"
echo "rows: $OUT/fleet.txt"
