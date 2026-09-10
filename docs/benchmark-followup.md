# Follow-up measurement corrections (2026-09-10)

These fixes address the four findings from the follow-up review of `fe1e6123`.
They retain the newer workflow dependency versions on `6f9491d` and change no
engine source, AI decisions, game rules, track files or champion fixtures.

## Uncached experiments

`bench_ai.py` now records and validates experiment identity for every self-play
comparison, independently of `BENCH_BASELINE`. Candidate/champion track contents
must match before any race is started. Both JARs, the properties, selected
tracks and runtime identity are checked again before reporting results. The
cache option controls storage/reuse only; it no longer switches validation on.
`BENCH_CHAMPION_JAR` continues to run the preserved champion binary for AI2.

## Cross-era classifications and fresh starts

The legacy exhibition referee now assigns finishes from first place upward and
crashes from last place downward. It stops immediately after the seventh
retirement, awarding the remaining car the next finishing place without giving
that car another turn. Retired state uses the Java sentinel position and zero
velocity. A 400-round horizon without completion is an error, not a set of
invented places. No performance report is emitted unless all mirrored races
complete. Oracle processes are closed on success, failure and failed setup.

Start generation uses a unique temporary output for each invocation, requires a
successful Java exit, validates the complete log against the configured roster,
and resolves starts by player number. Old `cross_start_*.log` files are never
read or overwritten; concurrent invocations do not share output files. Java
errors are returned to the caller instead of being replaced with stale starts.

This historical tool speaks the five-field oracle protocol. It now explicitly
rejects checkpoint courses (including checkpoint-based one-lap races), multi-lap
profiles and scattered starts rather than discarding state it cannot represent.
The default demonstration course is the non-checkpoint `hairpin`. For the
modern checkpoint/multi-lap campaign, run both policies in one binary with
`candidateSlots` and use validated mirrored `head_to_head.py` grids.

## Text baseline extraction is retired

`extract_baseline.py BENCH_LOG OUT_JSON [COLUMN]` now exits with status 2 and a
migration message, without creating or replacing any output. Printed summaries
cannot recover the seed, configuration, track, runtime and build provenance
required by a valid baseline. In particular, the helper does not manufacture a
manifest for rounded historical aggregates.

Create a new cache directly from a validated benchmark instead:

```sh
BENCH_BASELINE=/tmp/new-baseline.json \
BENCH_CHAMPION_JAR=/path/to/frozen/theoreticRacing.jar \
python3 tracks/bench_ai.py --seeds 5 --seed-start 1 hairpin chicane
```

Keep matching track files beside the frozen JAR. Preserve historical reports
and old caches as evidence; do not relabel them as current measurements.

## Verification

`tests/test_followup_tooling.py` adds 23 tests for these failure and success
paths. Together with the previous tests, 96 Python tests pass locally. The
external classification also matches the actual Java referee in 17 controlled
geometric-outcome sequences, including mixed finishes/crashes, skipped retired
slots and an end on the final permitted move. This differential runs in both
JDK 25 and JDK 26 CI jobs after core-test compilation:

```sh
sh run_tests.sh
python3 tests/cross_era_referee_regression.py
```

Supplementary local OpenJDK 21 integration runs reject different courses under
the same track name without caching, accept matching-course comparisons at
17.143 moves per finisher for both identical binaries, reject a real Java
missing-properties exit, and score identical cross-era policies 4.500 versus
4.500 over mirrored hairpin races. These are validation checks, not a new AI
promotion or a replacement for the campaign's racecraft evaluation.
