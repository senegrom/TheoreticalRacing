# Preparation and replay safety corrections (2026-09-11)

These changes address the three findings reviewed at `7220dd5`. The promoted
AI policy, referee rules, track files and behavioral golden hashes are unchanged.

## Shared fallback geometry cache

`RaceGame` now publishes its lazy fallback cache under a monitor. The fallback
also synchronizes lookups and writes, protecting the key/state pair, probing,
size and resize as one table. Allocations complete before either replacement
array is published, so a failed allocation cannot leave half of a resized table.
Duplicate misses may compute the same immutable geometry outside the lock.
The dense two-bit cache and its fast path are unchanged.

Regression coverage forces the fallback without allocating a huge board: four
writers insert mixed true/false verdicts through resizing at both tiny and
production initial capacities; simultaneous real geometry queries are compared
with the uncached referee; and actual reachability, gate and exact-potential
maps are compared in full between serial and parallel builds. The concurrency
test fails against the previous unsynchronized implementation.

The follow-up review also found that previously saved maps could retain a bad
verdict despite having a valid checksum. All map-cache paths now live in a new
`maps-v2` directory beneath the same configured cache root (including
`RACING_REACH_CACHE`). The first run rebuilds maps; old files are neither loaded
nor deleted. This namespace covers reachability, derived maps and edge caches.
An end-to-end test puts valid map files in the old location, proves they are
ignored, then verifies fresh cold/warm race logs are identical and old files
were not modified.

## One-lap checkpoint replay

New logs explicitly declare `# checkpoints enabled` or `# checkpoints disabled`,
independently of lap count. Five-field diagnostic reconstruction requires one
disabled marker and rejects checkpoint/lap events and scattered-start gate state
anywhere in the log. Absence of a checkpoint crossing before the requested move
is not evidence of an ungated course.

This fail-closed boundary protects `policy_matrix.py` and `board_at.py`. Historical
logs without the declaration are still replayable with `complete=True` through
V2, `oracle_roll.py` and `needle_audit.py`. Do not rewrite old logs to bypass the
guard. Raw legacy oracle queries retain their explicit first-lap defaults; they
are not a complete replay mechanism.

The real one-lap Circle race is replayed through V2, including its recorded finish
with gate 0 owed; legacy reconstruction rejects it even at the first move. The
non-checkpoint Hairpin legacy path remains usable. Existing two-lap replay and
query-order-isolation checks remain in place. Metadata is excluded by the
existing normalized-log projection, so no golden or champion pin is refrozen.

## Desktop preparation failures

The AI-turn preparation barrier handles both `RuntimeException` and `Error`,
including a published `OutOfMemoryError`. It leaves PLAY and disables controls
before reporting the failure, clears preview/velocity indicators and writes a
persistent error status. Already queued callbacks cannot restart the race. No
move, final classification or successful game log is fabricated.

Failure-injection tests exercise the actual handler with an out-of-memory error,
a runtime exception and a linkage error. These are injected failures, not a claim
that an ordinary reviewed race exhausted the Java heap.

## Validation and follow-up review

The new contracts run through `run_tests.sh` and the existing query-replay CI step.
Eleven Python tests cover checkpoint and historical-log boundaries. Source changes
are restricted to cache synchronization/generation, error recovery and log metadata;
no new AI candidate or performance promotion is proposed. The full fleet promotion
grid is not claimed as run for this maintenance change.

See the accompanying validation evidence for exact test results, runtime versions
and the published commit. Local Java runs use supplementary OpenJDK 21; the supported
JDK 25/26 builds and real Chromium/WebKit checks run in GitHub CI.
