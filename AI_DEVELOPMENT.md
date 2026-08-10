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

- **`oracle_roll.py`** — fidelity ceiling. Drives one interactive `--query-moves - -` JVM. It infers field size from the log; set `RACING_PROPS` to matching properties for non-eight-car analysis. `verify` must reproduce a logged race move-for-move; `cand` rolls each candidate forward with the real scorer as every car's policy.
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

Round 72 was promoted on 2026-08-10, so AI1 and AI2 are identical again. The champion now contains five bounded safety proofs:

- Round 68's dense slow-pack trigger invokes the expensive real-scorer-rival rollout only when a fast-enough car is inside an all-field funnel and a near-equal low-trap alternative exists. On Le Mans seed 4 it changes player 7's move 55 from `SE` to `SW`, converting 6 finishes / 1 crash into 7 / 0.
- Round 69's cross-model certificate handles locally narrow fast-pack moves. The topology-shaped model must prove the chosen move dies and propose a survivor; the independent scorer-rival model must also keep that alternative alive. On Hungaroring seed 20 it changes player 5's last avoidable choice at move 181 and prevents its move-221 crash.
- Round 70 extends the real-scorer-rival rollout from five to six rounds only for slow moves already at trap tier L1. On four-car Interlagos seeds 3 and 4, it sees the chosen `W` die one round beyond the old horizon and selects oracle-proven survivor `NONE` at move 456.
- Round 71 generalises the dense slow-pack trigger to four-car fields. It still requires every live rival within Chebyshev radius 10 plus a near-equal low-trap escape, but lowers the speed floor from 16 to 12 when exactly three rivals remain. On Monaco four-car seed 9 it changes player 1's move 27 from `E` to `W` and removes the move-148 crash.
- Round 72 makes the worst-case seal guard trap-monotone. The guard may replace a sealable scorer choice only with an unsealable move whose local trap penalty is no worse. On Nurburgring eight-car seed 19 the old guard overrode scorer-preferred `N` (trap 0.5, oracle-alive) with `E` (trap 2.0, doomed); retaining `N` converts 6 finishes / 1 crash into 7 / 0.

The Round 71 four-car Monaco seeds 6–10 slice improves 14 finishes / 1 crash to 15 / 0. Its target 2v2 seed keeps exact 2.500 place parity while changing one AI2 crash to zero AI1 crashes. Round 72 preserves the Le Mans seed-4, Hungaroring seeds 6/20, Monaco four-car seed-9 and Interlagos four-car seeds 3/4 rescue trajectories byte-for-byte. A same-policy A/B over 25 short-track eight-car races found 23 identical logs; the two deliberate seal-guard divergences remained crash-free and had a net zero turn-count change. The existing zigzag seed-4 golden case also remains crash-free and completes two turns sooner (530 instead of 532), so its champion fixture is intentionally updated. In the Nurburgring seed-19 mixed field, AI1 had zero crashes while the pre-promotion AI2 side had one.

The frozen golden corpus now includes the two new boundary cases (`monaco-s9-4p` and `nurburgring-s19-8p`) in addition to the existing short, long, congested, slow and endgame races. Shared runtime cleanup still caches `Direction.values()`, constructs one opponent mobility projection per turn, memoizes overlapping mobility states, and mixes packed edge-cache keys before `HashMap` lookup.

## Highest-value next directions

1. **Bottleneck-aware triggers** — detect narrow future cut sets or collapsing route width, then invoke expensive rollout based on topology instead of track-shaped heuristics.
2. **Joint-rollout transposition caches** — extend the new per-turn mobility memo to detached multi-car rollout states keyed by board, mover, horizon and policy flags; discard it after each real move.
3. **Small opponent-policy beams** — retain two plausible moves for the nearest rivals and evaluate a bounded pessimistic beam instead of trusting one prediction.
4. **Event-driven horizons** — roll until the car escapes the bottleneck, the pack disperses, it finishes/dies, or a node budget is exhausted.
5. **Learned risk trigger** — train only the decision to invoke expensive verification; keep final move selection deterministic and inspectable.
6. **Three-car endgame search** — extend the exact 1v1 solver under a tight low-branching trigger.
7. **Progress coordinates** — add centerline/arclength progress to improve ordering on hairpins and nearby parallel straights.
8. **Counterexample search** — mutate starts/tracks automatically and minimize any crash to its shortest reproducible prefix.
