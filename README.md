# Theoretical Racing

A Java Swing implementation of the classic pen-and-paper [Racetrack](https://en.wikipedia.org/wiki/Racetrack_(game)) game, with deterministic computer players, exact empty-track reachability, benchmark tooling, and a library of real and synthetic tracks.

Players draw or select a track, place their cars in the start zone, then take turns racing by adjusting their velocity vector. Each turn changes velocity by at most 1 in each axis; the new position is the current position plus the updated velocity. Leaving the track or landing on another live car crashes the player.

## Requirements

- JDK 17 or later
- Python 3.9+ for benchmark and track-generation tooling
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

The tests currently cover direction/index invariants, player-kind parsing, track point parsing/serialization, segment-intersection geometry, and start-zone construction. GitHub Actions builds and tests on JDK 17 and JDK 21 and syntax-checks the Python tooling.

## Benchmarks

The AI benchmark suite remains separate from the fast CI tests because the full promotion battery is intentionally expensive.

Build first, then run, for example:

```bash
sh ./build_main.sh
sh ./run_bench_main.sh silverstone monza
sh ./run_bench_main.sh --seeds 5 silverstone
sh ./run_bench_main.sh --h2h --seeds 5
sh ./run_bench_main.sh --4p --seeds 5
sh ./run_bench_main.sh --1v1 --seeds 5
sh ./run_bench_main.sh --slow --seeds 5
```

`tracks/run_bench.py` gives the historical `bench_ai.py` harness portable paths and a temporary copy of `tracks/bench.properties`, so benchmark runs no longer mutate a developer's `user.properties`.

## How to play

1. **Start dialog** — Configure 1–9 players, player names, colours, AI kinds, dimensions, and optionally choose a bundled track.
2. **Draw/select the track** — For a new track, click grid points to draw the left border, press OK, then draw the right border. The first border points define the start and the last points define the finish.
3. **Place players** — Click inside the start zone to place human cars; AI cars can be auto-placed.
4. **Race** — Pick NW/N/NE/W/-/E/SW/S/SE to adjust velocity by one unit per axis. Human moves are previewed before confirmation.
5. **Finish** — Cross the finish in the forward racing direction. Leaving the corridor or colliding eliminates the car.

## Configuration

Personal settings are stored in `user.properties` next to the running JAR and are intentionally ignored by Git. Defaults live in `default.properties`. Benchmark defaults live separately in `tracks/bench.properties`.

Important properties include `windowX`, `windowY`, `gameX`, `gameY`, `nPlayers`, `maxPlayers`, `playerNName`, `playerNColor`, and `playerNKind` (`HUMAN`, `AI1`, or `AI2`).

## Project structure

```text
src/tr/main/          application entry point
src/tr/logic/         game rules, track IO/geometry, reachability, AI
src/tr/gui/           Swing UI and rendering
tracks/               bundled circuits, generators, benchmark tooling
tests/tr/logic/       dependency-free regression tests
.github/workflows/    continuous integration
racing-memory.md      AI research/promotion history
```

`RaceAi` intentionally contains both the frozen champion and the experimental frontier. AI changes should be benchmarked against the frozen body and promoted only after the repository's multi-stage regression battery passes.

## License

GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
