#!/bin/sh
set -eu

cd "$(dirname "$0")"

rm -rf test-bin
mkdir -p test-bin
find src tests -name '*.java' -print | sort > .test-java-sources
# The tests build maps for their own fixture boards. Keep those out of the
# player's reach cache: a fixture sharing a production track's key once
# changed every later race on that track (2026-09-18; review, 2026-09-27).
RACING_REACH_CACHE=$(mktemp -d "${TMPDIR:-/tmp}/tr-test-cache.XXXXXX")
export RACING_REACH_CACHE
trap 'rm -f .test-java-sources; rm -rf "$RACING_REACH_CACHE"' EXIT
javac -Xlint:all -Werror -encoding UTF-8 -d test-bin @.test-java-sources
java -ea -Djava.awt.headless=true -cp test-bin tr.logic.CoreTests
java -ea -Djava.awt.headless=true -cp test-bin tr.main.MainTests
java -ea -Djava.awt.headless=true -cp test-bin tr.logic.PreparationSafetyTests
java -ea -Djava.awt.headless=true -cp test-bin tr.logic.TrackImportTests
java -ea -Djava.awt.headless=true -cp test-bin tr.logic.SimulationBoundaryTests
java -ea -Djava.awt.headless=true -cp test-bin tr.logic.OwnerRuleTests
java -ea -Djava.awt.headless=true -cp test-bin tr.logic.SimulationFollowupTests
java -ea -Djava.awt.headless=true -cp test-bin tr.logic.EndgamePhysicalTests
java -ea -Djava.awt.headless=true -cp test-bin tr.logic.RaceAiDuelSearchTests

java -ea --add-modules jdk.jdi -cp test-bin tr.logic.LapMemoPublicationTests src/tr/logic/Reachability.java

java -ea -Djava.awt.headless=true -cp test-bin tr.logic.RacecraftNextTests

java -ea -Djava.awt.headless=true -cp test-bin tr.logic.RacecraftFixTests
