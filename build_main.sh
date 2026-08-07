#!/bin/sh
set -eu

cd "$(dirname "$0")"

rm -rf bin
mkdir -p bin

find src -name '*.java' -print | sort > .java-sources
trap 'rm -f .java-sources' EXIT
javac -encoding UTF-8 -d bin @.java-sources
jar cfe theoreticRacing.jar tr.main.Main -C bin tr -C . default.properties
