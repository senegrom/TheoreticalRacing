#!/bin/sh
set -eu

cd "$(dirname "$0")"

rm -rf test-bin
mkdir -p test-bin
find src tests -name '*.java' -print | sort > .test-java-sources
trap 'rm -f .test-java-sources' EXIT
javac -Xlint:all -Werror -encoding UTF-8 -d test-bin @.test-java-sources
java -ea -Djava.awt.headless=true -cp test-bin tr.logic.CoreTests
