#!/bin/sh
# Validated, resumable lap fleet. Defaults: seeds 1-10, one worker per core.
# Usage: sh tracks/fleet_grid.sh [A-B|N] [jobs] [output-directory]
# RACING_JAR/JAVA/PROPS/HEAP/TRACKS and RACING_TIMEOUT customize the run.
# Resume requires an identical manifest; failures are retryable and nonzero.
set -eu
exec python3 "$(dirname "$0")/fleet_grid.py" "$@"
