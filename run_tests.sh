#!/bin/sh
set -eu

cd "$(dirname "$0")"

feature=$(javac --version 2>&1 | sed -E 's/^[^0-9]*([0-9]+).*/\1/')
if [ "$feature" -lt 25 ]; then
    echo "JDK 25 or newer is required; javac reports $(javac --version 2>&1)" >&2
    exit 2
fi

rm -rf test-bin
mkdir -p test-bin
find src tests -name '*.java' -print | LC_ALL=C sort > .test-java-sources
trap 'rm -f .test-java-sources' EXIT
javac --release 25 -Xlint:all -Werror -encoding UTF-8 -d test-bin @.test-java-sources
java -ea -Djava.awt.headless=true -cp test-bin tr.logic.CoreTests
