#!/bin/sh
set -eu

cd "$(dirname "$0")"

resolve_jdk_tool() {
    tool=$1
    if command -v "$tool" >/dev/null 2>&1; then
        command -v "$tool"
        return
    fi
    if [ -n "${JAVA_HOME:-}" ] && [ -x "$JAVA_HOME/bin/$tool" ]; then
        printf '%s\n' "$JAVA_HOME/bin/$tool"
        return
    fi
    java_home_dir=$(java -XshowSettings:properties -version 2>&1 | sed -n 's/^ *java\.home = //p')
    printf '%s\n' "$java_home_dir/bin/$tool"
}

require_jdk25_or_newer() {
    tool_path=$1
    tool_name=$2
    if ! version_output=$("$tool_path" --version 2>&1); then
        printf '%s\n' "Cannot determine $tool_name version: $version_output" >&2
        exit 2
    fi
    major=$(printf '%s\n' "$version_output" | sed -nE "s/^$tool_name ([0-9]+)([. +\\-].*)?$/\\1/p")
    case "$major" in
        ''|*[!0-9]*)
            printf '%s\n' "Unrecognized $tool_name version: $version_output" >&2
            exit 2 ;;
    esac
    if [ "$major" -lt 25 ]; then
        printf '%s\n' "JDK 25 or newer is required; $tool_path reports: $version_output" >&2
        exit 2
    fi
}

JAVAC_TOOL=$(resolve_jdk_tool javac)
JAR_TOOL=$(resolve_jdk_tool jar)
require_jdk25_or_newer "$JAVAC_TOOL" javac
require_jdk25_or_newer "$JAR_TOOL" jar

rm -rf build/classes theoreticRacing.jar
mkdir -p build/classes
find src -name '*.java' -print | LC_ALL=C sort > build/main-sources.txt

"$JAVAC_TOOL" \
    --release 25 \
    -encoding UTF-8 \
    -Xlint:all \
    -Werror \
    -d build/classes \
    @build/main-sources.txt

"$JAR_TOOL" \
    --create \
    --file theoreticRacing.jar \
    --main-class tr.main.Main \
    --date=2026-01-01T00:00:00Z \
    -C build/classes .

"$JAR_TOOL" --validate --file theoreticRacing.jar
