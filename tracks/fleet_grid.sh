#!/bin/sh
# Validated, resumable lap fleet. Defaults: seeds 1-10, as many workers as the
# available memory holds at the heap (RACING_HEAP, default -Xmx8g).
# Usage: sh tracks/fleet_grid.sh [A-B|N] [jobs] [output-directory]
# RACING_JAR/JAVA/PROPS/HEAP/TRACKS and RACING_TIMEOUT customize the run.
# Resume requires an identical manifest; failures are retryable and nonzero.
set -eu
exec python3 "$(dirname "$0")/fleet_grid.py" "$@"
