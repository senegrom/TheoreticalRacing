# AI development and promotion

`RaceAi` intentionally keeps two complete move-selection bodies:

- **AI1** is the experimental frontier.
- **AI2** is the frozen champion and independent comparison standard.

Shared geometry, reachability and simulation helpers may be cleaned up, but the two top-level scorers stay separate so an experiment cannot silently change its own benchmark.

## Fast development loop

```bash
sh ./run_tests.sh
sh ./run_golden_tests.sh
python3 tracks/ai_probe.py --allow-divergence --seeds 3 sprint hairpin lemans hungaroring
python3 tracks/bench_ai.py --seeds 5 lemans monaco hungaroring zandvoort
python3 tracks/bench_ai.py --h2h --seeds 5
python3 tracks/bench_ai.py --4p --seeds 5
```

The golden corpus always drives **AI2**. Changing a fixture is a champion-promotion action, not routine maintenance. `ai_probe.py` is the go/no-go test: it compares normalized AI1/AI2 move logs and reports the first changed decision, so inert experiments are rejected before expensive benchmarking.

## Forensic toolchain

Tools live in `tracks/`. Temporary reach dumps and race logs may be placed in `RACING_WORK_DIR` (default: `tracks/`). Produce a reach dump with:

```bash
java -jar theoreticRacing.jar --auto --track TRACK --props tracks/bench.properties --dump-reach reach_TRACK.bin
```

Reach dumps named `tracks/reach_*.bin` are ignored by Git. The shared `forensics_common.py` module owns the log grammar, validated reach reader, board reconstruction and persistent oracle process used by the forensic scripts.

- **`oracle_roll.py`** — fidelity ceiling. Drives one interactive `--query-moves - -` JVM with `tracks/bench.properties`. `verify` must reproduce a logged race move-for-move; `cand` rolls each candidate forward with the real scorer as every car's policy.
- **`board_at.py`** — reconstructs a board at a log move and classifies candidates quickly. The oracle mask remains authoritative for geometry.
- **`policy_matrix.py`** — evaluates cheap simulated policies against known crash sites before Java implementation.
- **`crash_scan.py`** — summarizes crashed players and final speeds.
- **`extract_baseline.py`** — builds `BENCH_BASELINE` caches so candidate benchmarks can skip the frozen AI2 column. Rebuild caches after every promotion.
- **`bench_iso.py`** — isolated all-AI battery runner, including 4-car and 2-car modes that `bench_ai.py` does not expose as all-AI comparisons.

`racing-memory.md` keeps the detailed historical campaign record; this file only documents the current workflow.

## Full promotion battery

The manual **AI promotion battery** runs independent stages for:

- 8-car self-play on seeds 1–5, 6–10 and 11–15
- 4v4 mixed AI1/AI2 on the same three seed sets
- 2v2 on seeds 1–5
- 1v1 on seeds 1–5
- slow synthetic tracks on seeds 1–5

Every race must execute and produce a valid log. Promotion still requires reading the reports: aggregate move averages can worsen when a candidate saves a slow back-marker, and small crash differences can be noise.

## Current champion and frontier baseline

Round 69 was promoted on 2026-08-09, so AI1 and AI2 are identical again. The current stack contains two bounded safety proofs:

- Round 68's dense slow-pack trigger invokes the expensive real-scorer-rival rollout only when a fast-enough car is inside an all-field funnel and a near-equal low-trap alternative exists. On Le Mans seed 4 it changes player 7's move 55 from `SE` to `SW`, converting 6 finishes / 1 crash into 7 / 0.
- Round 69's cross-model certificate handles locally narrow fast-pack moves. The topology-shaped model must prove the chosen move dies and propose a survivor; the independent scorer-rival model must also keep that alternative alive. On Hungaroring seed 20 it changes player 5's last avoidable choice at move 181 and prevents its move-221 crash.

The ungated cross-model version was rejected because it introduced a Hungaroring seed-6 crash. Requiring trap penalty >= 0.5 retained the seed-20 rescue and removed that false switch. The round-69 candidate's canonical 22-track seeds-1-to-5 column finished 770 / 0 at 63.81 average moves; the round-68 champion baseline was 770 / 0 at 63.82. After promotion, a nine-track, three-seed probe found all 27 races move-for-move identical between AI1 and AI2.

Shared runtime cleanup now caches `Direction.values()`, constructs one opponent mobility projection per turn, memoizes overlapping mobility states, and mixes packed edge-cache keys before `HashMap` lookup. These changes are behavior-preserving; focused A/B checks showed the mobility memo substantially reducing its exercised workload and repeat reachability improving by roughly 11%.

## Highest-value next directions

1. **Bottleneck-aware triggers** — detect narrow future cut sets or collapsing route width, then invoke expensive rollout based on topology instead of track-shaped heuristics.
2. **Joint-rollout transposition caches** — extend the new per-turn mobility memo to detached multi-car rollout states keyed by board, mover, horizon and policy flags; discard it after each real move.
3. **Small opponent-policy beams** — retain two plausible moves for the nearest rivals and evaluate a bounded pessimistic beam instead of trusting one prediction.
4. **Event-driven horizons** — roll until the car escapes the bottleneck, the pack disperses, it finishes/dies, or a node budget is exhausted.
5. **Learned risk trigger** — train only the decision to invoke expensive verification; keep final move selection deterministic and inspectable.
6. **Three-car endgame search** — extend the exact 1v1 solver under a tight low-branching trigger.
7. **Progress coordinates** — add centerline/arclength progress to improve ordering on hairpins and nearby parallel straights.
8. **Counterexample search** — mutate starts/tracks automatically and minimize any crash to its shortest reproducible prefix.
