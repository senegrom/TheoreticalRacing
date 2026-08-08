#!/bin/sh
set -eu

cd "$(dirname "$0")"

require_jdk26_tool() {
    tool=$1
    first_line=$($tool --version 2>&1 | sed -n '1p')
    major=$(printf '%s\n' "$first_line" | sed -E 's/^[^0-9]*([0-9]+).*/\1/')
    if [ "$major" != "26" ]; then
        printf '%s\n' "This project requires JDK 26; $tool reports: $first_line" >&2
        exit 2
    fi
}

require_jdk26_tool java
require_jdk26_tool javac
require_jdk26_tool jar

rm -rf build/classes theoreticRacing.jar
mkdir -p build/classes
find src -name '*.java' -print | LC_ALL=C sort > build/main-sources.txt

javac \
    --release 26 \
    -encoding UTF-8 \
    -Xlint:all \
    -Werror \
    -d build/classes \
    @build/main-sources.txt

jar \
    --create \
    --file theoreticRacing.jar \
    --main-class tr.main.Main \
    --date=2026-01-01T00:00:00Z \
    -C build/classes .

jar --validate --file theoreticRacing.jar
