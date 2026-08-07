#!/bin/sh
set -eu

cd "$(dirname "$0")"
sh ./build_main.sh
python3 tests/headless_smoke.py
exec python3 tests/golden_races.py "$@"
