#!/bin/sh
# Prove the reachability disk cache is behavior-invisible on one track:
#   1. race with a fresh cache dir (cold: computes the map and writes the cache)
#   2. race again (warm: loads the cache) -- race logs must be byte-identical
#   3. dump the reachability map warm, wipe the cache, dump again cold --
#      the two dumps must be byte-identical.
# Usage: verify_reach_cache.sh [track] [seed]   (default: nurburgring 19)
# RACING_JAR overrides the jar under test (default: repo-root theoreticRacing.jar).
set -eu
cd "$(dirname "$0")/.."
TRACK="${1:-nurburgring}"
SEED="${2:-19}"
JAR="${RACING_JAR:-$PWD/theoreticRacing.jar}"
WORK="${TMPDIR:-/tmp}/reachcache_verify_$$"
mkdir -p "$WORK"
export RACING_REACH_CACHE="$WORK/cache"
PROPS="$WORK/bench8.properties"
sed -E 's/^(player[1-8]Kind=).*/\1AI2/; s/^nPlayers=.*/nPlayers=8/' tracks/bench.properties > "$PROPS"

java -jar "$JAR" --auto --track "$TRACK" --props "$PROPS" --seed "$SEED" \
  --log "$WORK/cold.log" > "$WORK/cold.out" 2>&1
java -jar "$JAR" --auto --track "$TRACK" --props "$PROPS" --seed "$SEED" \
  --log "$WORK/warm.log" > "$WORK/warm.out" 2>&1
grep -q "cache-hit" "$WORK/warm.out" || { echo "FAIL: second run did not hit the cache"; exit 1; }
cmp "$WORK/cold.log" "$WORK/warm.log" || { echo "FAIL: cold and warm race logs differ"; exit 1; }

java -jar "$JAR" --track "$TRACK" --props "$PROPS" --dump-reach "$WORK/warm.reach" > "$WORK/dumpwarm.out" 2>&1
grep -q "cache-hit" "$WORK/dumpwarm.out" || { echo "FAIL: warm dump did not hit the cache"; exit 1; }
rm -rf "$WORK/cache"
java -jar "$JAR" --track "$TRACK" --props "$PROPS" --dump-reach "$WORK/cold.reach" > "$WORK/dumpcold.out" 2>&1
cmp "$WORK/cold.reach" "$WORK/warm.reach" || { echo "FAIL: cold and warm reachability dumps differ"; exit 1; }

grep -o "bfs=[0-9]*ms" "$WORK/cold.out" | head -1
grep -o "total=[0-9]*ms" "$WORK/warm.out" | head -1
echo "PASS: cache is behavior-invisible on $TRACK seed $SEED"
rm -rf "$WORK"
