#!/bin/sh
# Build the main-repo jar (CWD = repo root).
cd "$(dirname "$0")" || exit 1
javac -encoding UTF-8 -d bin $(git ls-files "src/*.java" | tr '\n' ' ') || exit 1
exec "/d/Programs/Java/JDK26/bin/jar" cfe theoreticRacing.jar tr.main.Main -C bin tr -C . default.properties
