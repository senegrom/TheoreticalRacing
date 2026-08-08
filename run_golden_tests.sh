#!/bin/sh
set -eu

cd "$(dirname "$0")"
sh ./build_main.sh
# Windows shells often alias python3 to the Store shim; allow an override.
PYTHON_BIN="${PYTHON:-python3}"
"$PYTHON_BIN" tests/headless_smoke.py
exec "$PYTHON_BIN" tests/golden_races.py "$@"
