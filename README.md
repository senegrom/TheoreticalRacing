# Theoretical Racing

A Java Swing implementation of the classic pen-and-paper [Racetrack](https://en.wikipedia.org/wiki/Racetrack_(game)) game, with deterministic computer players, exact empty-track reachability, benchmark tooling, and a library of real and synthetic tracks.

Players draw or select a track, place their cars in the start zone, then take turns racing by adjusting their velocity vector. Each turn changes velocity by at most 1 in each axis; the new position is the current position plus the updated velocity. Leaving the track or landing on another live car crashes the player.

## Requirements

- JDK 25 or later
- Python 3.9+ for benchmark and track-generation tooling (CI runs 3.13); `tracks/build_track_from_geojson.py` additionally needs `shapely`
- `sh` for the convenience scripts

The Java game itself has no third-party dependencies.

## Build and run

```bash
sh ./build_main.sh
java -jar theoreticRacing.jar
```

The build script compiles every Java source under `src/` and creates `theoreticRacing.jar` using the JDK on `PATH`.

Useful command-line modes include:

```bash
java -jar theoreticRacing.jar --list-tracks
java -jar theoreticRacing.jar --auto --track silverstone --props some.properties --log race.log --seed 1
```

## Tests

The repository keeps the core test layer dependency-free:

```bash
sh ./run_tests.sh
```

The tests cover direction/index invariants, player-kind parsing, point serialization, track geometry, structural validation of every bundled circuit, and other pure core helpers. Compilation uses `-Xlint:all -Werror`.

The AI also has deterministic golden-race regression tests (eight-car and four-car races whose normalized logs are hashed):

```bash
sh ./run_golden_tests.sh
```

And a set of regression pins for pace, mixed-field safety, field externality, and staged self-play pace, for example:

```bash
python3 tests/ai1_pace_regression.py
python3 tests/ai1_mixed_safety_regression.py
python3 tests/ai1_field_neutral_regression.py
python3 tests/ai1_staged_pace_regression.py
python3 tests/ai1_energy_pace_regression.py
```

The corpus spans short, long, congested, slow and endgame races, including the Le Mans seed-4, Monaco four-car seed-9, Nurburgring seed-19, Interlagos seed-10, Zandvoort seed-45, Hungaroring seed-13, and Le Mans four-car seed-1 counterexamples. GitHub Actions compiles on JDK 25 and JDK 26, runs the golden corpus plus every regression pin on JDK 25, and syntax-checks the Python and shell tooling.

## Benchmarks

The AI benchmark suite remains separate from the fast CI tests because the full promotion battery is intentionally expensive.

Build first, then run, for example:

```bash
sh ./build_main.sh
python3 tracks/bench_ai.py silverstone monza
python3 tracks/bench_ai.py --seeds 5 silverstone
python3 tracks/bench_ai.py --h2h --seeds 5
python3 tracks/bench_ai.py --4p --seeds 5
python3 tracks/bench_ai.py --1v1 --seeds 5
python3 tracks/bench_ai.py --slow --seeds 5
```

The campaign's primary instrument is the 8-car lap grid: every lap-capable track over a seed range, one JVM per track across a work queue.

```bash
sh tracks/fleet_grid.sh                 # seeds 1-10, one job per core
RACING_TRACKS=rand19,cog sh tracks/fleet_grid.sh 11-20 8
```

It writes one `<track> <seed> fin= crash= timeout= moves=` row per race plus a `FLEETDONE` summary line. The Python runner behind the shell entry point validates every completed log, publishes completion markers atomically, and returns nonzero on a failed JVM, missing result or timeout. Only successfully completed, validated courses without lap gates are marked `NOLOOP`.

Use a separate output directory for each experiment, for example `sh tracks/fleet_grid.sh 11-20 2 /tmp/fleet-candidate-s11-20`. Resuming the **same** command validates its manifest and log hashes; failed or incomplete tracks are retried. The manifest binds the results to the JAR, properties, track data, exact seeds, runner and Java runtime/options. A changed experiment or an old unmanifested output directory is rejected rather than silently reused. Aggregation includes only the selected tracks, and an OS lock prevents two writers from sharing an output directory.

`RACING_JAR`, `RACING_JAVA`, `RACING_PROPS` and `RACING_HEAP` select the build, JVM, race shape and heap. `RACING_TRACKS` selects a comma/space-separated subset from the tracks beside the selected JAR. `RACING_TIMEOUT` bounds each track batch in seconds (default 3600). Choose concurrency to fit available memory: the default heap is 8 GB **per JVM**, not for the entire work queue.

`tracks/bench_ai.py` creates an isolated temporary properties/log directory, so benchmarks do not mutate a developer's `user.properties`. Use `--seed-start 6 --seeds 5` for seeds 6–10.

Reachability maps are cached on disk per track geometry (the reverse-BFS dominates race startup; seeds only move start placements). The cache lives in `%LOCALAPPDATA%/theoreticRacing/reach_cache` (or `~/.theoreticRacing/reach_cache`), can be overridden with `RACING_REACH_CACHE`, and is always safe to delete — a corrupt or missing file just recomputes. `tracks/verify_reach_cache.sh [track] [seed]` proves the cache is behavior-invisible (byte-identical race logs and reachability dumps, cold vs warm).

Before a large run, locate AI1/AI2 behavior changes cheaply:

```bash
python3 tracks/ai_probe.py --allow-divergence --seeds 3 chicane hairpin lemans hungaroring
```

For a promotion candidate, run the manual **AI promotion battery** workflow in GitHub Actions. It executes the three independent five-seed 8-car and mixed-field sets plus 4-car, 1v1 and slow-track stages in parallel, uploading every report. See [racing-memory.md](racing-memory.md) for the campaign ledger -- every round's measurements, the instruments and the current frontier; [AI_DEVELOPMENT.md](AI_DEVELOPMENT.md) keeps the older-era notes.

## Replay and rule-contract tests

`python3 tests/query_replay_regression.py` records a two-lap race and replays every move through the versioned oracle, including standalone simulation queries and query-order isolation. It runs in CI alongside the existing goldens and champion pins. The core tests include illegal finish approaches, checkpoint transitions and convergence guards; the tooling tests inject failed JVMs, stale logs, interrupted runs and mismatched replay outcomes.

`tracks/oracle_roll.py` and `tracks/needle_audit.py` carry complete lap/gate state. Set `RACING_PROPS` to the recorded roster and lap profile before replaying. The legacy five-field protocol is retained with explicit first-lap defaults; it is not a full multi-lap snapshot. Older diagnostics using incomplete reconstruction reject multi-lap logs instead of silently dropping progress. See [docs/replay-protocol.md](docs/replay-protocol.md) for V2 and [docs/review-corrections.md](docs/review-corrections.md) for the finish-rule and golden-fixture changes.

## How to play

1. **Start dialog** — Configure 1–9 players, player names, colours, AI kinds, dimensions, and optionally choose a bundled track.
2. **Draw/select the track** — For a new track, click grid points to draw the left border, press OK, then draw the right border. The first border points define the start and the last points define the finish.
3. **Place players** — Click inside the start zone to place human cars; AI cars can be auto-placed.
4. **Race** — Pick NW/N/NE/W/-/E/SW/S/SE to adjust velocity by one unit per axis. Human moves are previewed before confirmation.
5. **Finish** — Cross the finish in the forward racing direction. Leaving the corridor or colliding eliminates the car.

## Configuration

Personal settings are stored in `user.properties` next to the running JAR and are intentionally ignored by Git. Missing personal settings are filled from code defaults. Benchmark defaults live separately in `tracks/bench.properties`.

Important properties include `windowX`, `windowY`, `gameX`, `gameY`, `nPlayers`, `maxPlayers`, `playerNName`, `playerNColor`, and `playerNKind` (`HUMAN`, `AI1`, or `AI2`).

## Project structure

```text
src/tr/main/          application entry point
src/tr/logic/         game rules, track IO/geometry, reachability, AI
src/tr/gui/           Swing UI and rendering
tracks/               bundled circuits, generators, benchmark tooling
tests/tr/logic/       dependency-free regression tests
tests/ai1_*.py        champion AI regression pins, run by CI on every push
.github/workflows/    fast CI and the manual promotion battery
racing-memory.md      the AI campaign ledger: rounds, measurements, instruments, frontier
AI_DEVELOPMENT.md     older-era AI notes (rounds 168-177), kept as history
BRANCH_ARCHIVE.md     where the deleted development branches stay recoverable
```

`RaceAi` holds one promoted policy; the `AI1` and `AI2` kinds are two labels for it, kept so that an experiment can gate one kind while it is being measured against the other. AI changes are benchmarked against the previous champion on the fleet grid and promoted only when that measurement and the regression battery both pass.

## License

GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
