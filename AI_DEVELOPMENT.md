# AI development and promotion

`RaceAi` intentionally keeps two complete move-selection bodies:

- **AI1** is the experimental frontier.
- **AI2** is the frozen champion and independent comparison standard.

Shared geometry, reachability and simulation helpers may be cleaned up, but the two top-level scorers stay separate so an experiment cannot silently change its own benchmark.

## Fast development loop

```bash
sh ./run_tests.sh
sh ./run_golden_tests.sh
python3 tests/ai1_pace_regression.py
python3 tests/ai1_mixed_safety_regression.py
python3 tests/ai1_field_neutral_regression.py
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

## Round 79 frontier candidate: field-neutral private lanes and convoys

Round 79 is an **AI1-only** candidate rebased on the Round 75 champion after
Round 76's certified-L2 arm was rejected and reverted. It retains Round 78's
adversarial private-lane pace proof:

- a cheap three-ply rectangle over-approximates every rival acceleration and
  requires three private empty-map-optimal continuations;
- when the rectangle is pessimistic, a geometry-clipped four-ply search answers
  only queried occupancy cells, ignores rival collisions conservatively,
  removes finished rivals, and fails closed after a shared 512-state budget;
- the narrower two-exit certificate is limited to slow lines or homogeneous
  AI1 fields with bounded uncertainty; mixed fields retain three exits;
- an independent scorer-rival rollout must keep the selected line alive, and
  the existing seal and danger guards retain final veto authority.

Round 78 added comparative field arbitration for a compressed fast pack. A
private line can be safe for its mover while perturbing the other scorers into
a slower or failed race, so candidate and incumbent are rolled through the
same five-round, six-rival scorer world. The candidate must strictly improve
its own final TTF without increasing the aggregate rival cost. The original
trigger covered fields of at least six live cars only when every rival was
within Chebyshev radius 10, repairing Zigzag seed 1.

Round 79 generalises that trigger to a **kinematically aligned convoy** without
naming tracks or progress coordinates. A wider train qualifies only when all
live rivals remain within two mover-velocity spans, every body is at most four
cells from the mover's velocity ray, and at most one rival is ahead. The same
strict-self/non-worsening-field comparison then arbitrates the move; all other
private-lane decisions keep the cheaper survival-only path.

The new boundary came from Cog seed 1 at global move 89. Player 1's private `S`
line improved its own rollout TTF from 35 to 34 versus champion `E`, but its
real finish gain cost the rest of the field three moves. The compact-radius
trigger missed the rear train because its seven rivals extended 18 cells along
the same velocity corridor. The convoy trigger retains `E`, restoring the
exact AI2 finish list `[46, 46, 46, 47, 48, 48, 48]`; Cog seed 2 keeps its
one-move AI1 gain. The field-neutral regression now pins both Zigzag seed 1 and
Cog seed 1 move-for-move.

The exact JDK-25 promotion battery is crash-free and never slower on any
reported track. The three 22-track eight-car bands each finish 770/0 in both
columns, with AI1/AI2 mean finisher moves 62.73/63.69, 62.69/63.66 and
62.70/63.64. The three 4v4 bands favour AI1 at mean places 4.472/4.528,
4.473/4.527 and 4.477/4.523, with zero crashes on either side. The 2v2 and 1v1
gates are 2.461/2.539 and 1.486/1.514, also crash-free. The slow stage is 140/0
in both columns and one net AI1 move faster (both print 104.16). This clears
the AI1 frontier gate; AI2 remains frozen until an explicit mirror,
golden-fixture review and post-promotion self-tie battery.

## Current champion and frontier baseline

Round 78 was promoted on 2026-08-12 and is the frozen AI2 champion; AI1 now carries the cumulative Round 81 frontier candidate above. The champion contains eight bounded safety proofs plus one bounded pace proof:

- Round 75 recovers provably safe finish pace. Within 15 empty-map turns of the flag, a strictly faster low-trap candidate may replace the scorer choice only when both the score-shaped-rival and scorer-rival joint models finish at that candidate's empty-map lower bound. The first partial simulated round is accounted for explicitly, and the normal danger-joint search remains an independent downstream veto. On Monaco eight-car seed 16, this changes two late `S` choices at map ttf 15 to `SW` at ttf 14 and saves two racer-turns without changing the seven-finisher, zero-crash result.
- Round 68's dense slow-pack trigger invokes the expensive real-scorer-rival rollout only when a fast-enough car is inside an all-field funnel and a near-equal low-trap alternative exists. On Le Mans seed 4 it changes player 7's move 55 from `SE` to `SW`, converting 6 finishes / 1 crash into 7 / 0.
- Round 69's cross-model certificate handles locally narrow fast-pack moves. The topology-shaped model must prove the chosen move dies and propose a survivor; the independent scorer-rival model must also keep that alternative alive. On Hungaroring seed 20 it changes player 5's last avoidable choice at move 181 and prevents its move-221 crash.
- Round 70 extends the real-scorer-rival rollout from five to six rounds only for slow moves already at trap tier L1. On four-car Interlagos seeds 3 and 4, it sees the chosen `W` die one round beyond the old horizon and selects oracle-proven survivor `NONE` at move 456.
- Round 71 generalises the dense slow-pack trigger to four-car fields. It still requires every live rival within Chebyshev radius 10 plus a near-equal low-trap escape, but lowers the speed floor from 16 to 12 when exactly three rivals remain. On Monaco four-car seed 9 it changes player 1's move 27 from `E` to `W` and removes the move-148 crash.
- Round 72 makes the worst-case seal guard trap-monotone. The guard may replace a sealable scorer choice only with an unsealable move whose local trap penalty is no worse. On Nurburgring eight-car seed 19 the old guard overrode scorer-preferred `N` (trap 0.5, oracle-alive) with `E` (trap 2.0, doomed); retaining `N` converts 6 finishes / 1 crash into 7 / 0.
- Round 73 certifies convergence dooms the smom pre-screen cannot see. When the deep pre-screen reads a fast pack move as alive and non-fragile but at least three rivals sit ahead of the landing (positive dot with the landing velocity), the chosen move is re-verdicted in the scorer-rival world with the rival cap widened from the nearest 3 to 6 — on Interlagos eight-car seed 10 the killers are ranks 4-6 by landing distance while the nearest 3 are the harmless rear queue. The switch stays survival-only. This repaired the round-72 promotion regression (Interlagos 8-car s6-10: 769/1 back to 770/0, and the mixed-field crash to zero) with exact ties on every other battery stage.
- Round 74 covers the complementary compressed-rear-queue shape. When all seven rivals are within the deep-pack radius, at most one is ahead, at least two rival bodies already occupy the mover's neutral 3x3 landing grid, and a near-equal low-trap escape exists, the same widened scorer-rival certificate arbitrates the move. On Zigzag eight-car seed 22, the smom model incorrectly keeps `S` alive at move 72; the scorer-rival model proves it dead within two rounds and keeps `NW` alive, preventing player 8's move-104 crash. The trigger was seen only 13 times in a 129-race harvest and changed only the failing target.
- Round 78 repairs two stacked fidelity gaps found by the second fresh-seed harvest. The round-60 slow smoke test now runs the scorer-rival world instead of the smom proxy (a chaser converging from behind lands in the round-59 nearest-rival set, so behind-convergence dooms are finally visible), and the slow escalation certifies alternatives with a scorer-modeled self (`scorerSelf`) because the selfMove proxy killed the only true survivor at Zandvoort seed-45 move 920 in every offline world. One upgrade on existing surfaces — no new trigger gates — eliminated three of the five harvest crashes (Zandvoort s45 and s34, Hungaroring s40) and improved the doom-dense Zandvoort 31-45 band from three crashes to one, with never-worse full gates and both mixed-field bands crash-free.

The Round 71 four-car Monaco seeds 6–10 slice improves 14 finishes / 1 crash to 15 / 0. Its target 2v2 seed keeps exact 2.500 place parity while changing one AI2 crash to zero AI1 crashes. Round 72 preserves the Le Mans seed-4, Hungaroring seeds 6/20, Monaco four-car seed-9 and Interlagos four-car seeds 3/4 rescue trajectories byte-for-byte. A same-policy A/B over 25 short-track eight-car races found 23 identical logs; the two deliberate seal-guard divergences remained crash-free and had a net zero turn-count change. The existing zigzag seed-4 golden case also remains crash-free and completes two turns sooner (530 instead of 532), so its champion fixture is intentionally updated. In the Nurburgring seed-19 mixed field, AI1 had zero crashes while the pre-promotion AI2 side had one.

The frozen golden corpus now includes six promoted boundary cases (`monaco-s9-4p`, `monaco-s16-8p`, `nurburgring-s19-8p`, `interlagos-s10-8p`, `zigzag-s22-8p` and `zandvoort-s45-8p`) in addition to the existing short, long, congested, slow and endgame races. Round 78 pins the Zandvoort seed-45 rescue (7 finishes / 0 crashes) and intentionally updates two slow-class fixtures (`lemans-s4-8p`, `monaco-s9-4p`): both remain crash-free and Monaco completes three turns sooner; every other hash is unchanged. Shared runtime cleanup still caches `Direction.values()`, constructs one opponent mobility projection per turn, memoizes overlapping mobility states, and stores mixed packed-edge keys in a primitive open-addressed long-to-boolean table. Against the pulled Round 73 build, Nurburgring seed 19 improved 6.7% on median cold startup (13.533s to 12.628s) and 1.9% with a warm reachability cache (2.584s to 2.535s), with identical race-log hashes throughout. A primitive mobility-memo prototype was rejected after a separate nine-pair warm A/B made the trimmed mean 0.8% slower.

Round 75 completed all three 22-track eight-car bands with 770/0 finishes and no track slower: mean finisher moves improved from 63.82 to 63.69, 63.79 to 63.66, and 63.78 to 63.64. It won all three mixed 4v4 bands at zero crashes (4.483/4.517, 4.483/4.517, and 4.475/4.525), slightly won 2v2 (2.498/2.502), tied 1v1 exactly, and improved the five-seed slow suite from 104.27 to 104.16 at 140/0 finishes. Seven interleaved warm Monaco seed-16 pairs measured a small compute cost: roughly 1.8% by trimmed mean and 3.2% by median. This is a racing-pace improvement, not a CPU-speed optimization.

## Highest-value next directions

1. **Bottleneck-aware triggers** — detect narrow future cut sets or collapsing route width, then invoke expensive rollout based on topology instead of track-shaped heuristics.
2. **Joint-rollout transposition caches** — extend the new per-turn mobility memo to detached multi-car rollout states keyed by board, mover, horizon and policy flags; discard it after each real move.
3. **Small opponent-policy beams** — retain two plausible moves for the nearest rivals and evaluate a bounded pessimistic beam instead of trusting one prediction.
4. **Event-driven horizons** — roll until the car escapes the bottleneck, the pack disperses, it finishes/dies, or a node budget is exhausted.
5. **Learned risk trigger** — train only the decision to invoke expensive verification; keep final move selection deterministic and inspectable.
6. **Three-car endgame search** — extend the exact 1v1 solver under a tight low-branching trigger.
7. **Progress coordinates** — add centerline/arclength progress to improve ordering on hairpins and nearby parallel straights.
8. **Counterexample search** — mutate starts/tracks automatically and minimize any crash to its shortest reproducible prefix.
