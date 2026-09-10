# Benchmark integrity corrections (2026-09-10)

These corrections follow review of master `ed6be1a`. They change measurement
validation and an informed-start browser fixture, not the engine, physics,
placement policy, AI decisions, track data or existing champion pins.

## Complete classifications

`tracks/benchmark_io.py` validates the full roster, numbered move sequence,
terminal places and final classification. An eight-car race normally has seven
terminal events: its last survivor receives the remaining place without needing
a FINISH event. A solo race requires its own terminal event. TIMEOUT is not
counted as CRASH.

Both benchmark modes and the head-to-head reader use this contract. A results
header alone, missing players, unknown or duplicate names, duplicated places,
incorrect terminal places and a mismatched configured roster fail validation.
Names containing spaces are supported; scoring uses player numbers after the
unambiguous names in the classification have been resolved. Duplicate display
names cannot be resolved reliably from the current log format and are rejected.
An incomplete experiment exits nonzero and has no valid aggregate score.

## Mirrored fleet pairs

```
python3 tracks/head_to_head.py ODD_GRID EVEN_GRID [ODD_GRID EVEN_GRID ...]
```

Each pair must contain both complementary, equally sized candidate assignments,
with matching builds, runtime/options, configuration, track contents and seed
window. Every expected log must have a validated completion marker and checksum.
The reader locks the directories against a concurrent fleet writer. Duplicate
paths (including aliases), overlapping track/seed pairs, missing or unexpected
logs, malformed results and incompatible experiments are errors, not dropped
observations. Independent nonoverlapping seed slices can be combined.

Fleet manifests are now schema 2. They retain the exact properties-file hash
and additionally bind a comparison profile that excludes only `candidateSlots`.
Java properties escapes, continuations and last-wins duplicate keys are decoded
before calculating that profile. Thus opposite assignments can be compared
without ignoring unrelated settings. Old manifests cannot establish this
contract: keep them as historical artifacts and rerun into fresh output
directories. Do not overwrite or relabel existing experimental evidence.

## Frozen champion caches

`BENCH_BASELINE` now contains a manifest and checksummed result rows. It binds
exact seeds, properties, tracks, parser/runner versions, JVM/options and the
actual champion binary. Incompatible or legacy unmanifested caches are rejected
before races start. Failed or interrupted measurements never publish a baseline;
successful writes are atomic, and mid-run input changes invalidate the run.

By default the current JAR is also the champion identity, so changing that JAR
invalidates the cache. To rebuild candidates while keeping the champion fixed,
set `BENCH_CHAMPION_JAR` to a separately preserved champion JAR, with its matching
`tracks/` directory beside it. The self-play benchmark actually executes this
binary for AI2 when creating the cache; it does not trust a manually assigned
champion label. Candidate and champion track files must match. The candidate
can change between invocations, but neither binary may change during a run.
`BENCH_CHAMPION_JAR` applies to self-play, not the mixed-field modes, which still
require both policies in one binary. Field totals remain descriptive, not a
replacement for the campaign's head-to-head finishing-place criterion.

## Informed-start browser fixture

The `hairpin-informed-s1-2p` fixture is synchronized to the already-promoted
Round 233 engine (`06280d78`). Native CI artifact `10163663595`, from run
`34505246298`, contains byte-identical desktop/browser logs. Fresh local
OpenJDK 21 desktop and Java-17-targeted adapter runs reproduce those exact bytes:
31 moves, A first, B the last survivor, no crashes. The golden-normalized digest
is `978446be4a76a37684b8363b57b9fb55a01da2e737613840119811bbe934d103`.
The reason is recorded beside the fixture. Native parity and Chromium/WebKit
still enforce the fixture; no assertions, CI jobs or publication gates were
removed. The production JDK 25/26 checks remain CI's responsibility.
