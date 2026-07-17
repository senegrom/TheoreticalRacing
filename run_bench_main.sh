#!/bin/sh
# Run the pace bench with CWD = repo root (game resolves tracks/ from CWD).
cd "$(dirname "$0")" || exit 1
exec /d/PyEnv/p14/Scripts/python.exe tracks/bench_ai.py "$@"
