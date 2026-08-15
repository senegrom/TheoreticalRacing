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
python3 tests/ai1_staged_pace_regression.py
python3 tests/ai1_energy_pace_regression.py
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
- **`bench_iso.py`** — isolated all-AI battery runner, including 4-car and 2-car modes that `bench_ai.py` does not expose as all-AI comparisons. It always starts from canonical `tracks/bench.properties` (or explicit `RACING_PROPS`) and uses process-unique temp files, so concurrent checkouts cannot corrupt each other's evidence.

`racing-memory.md` keeps the detailed historical campaign record; this file only documents the current workflow.

## Full promotion battery

The manual **AI promotion battery** runs independent stages for:

- 8-car self-play on seeds 1–5, 6–10 and 11–15
- 4v4 mixed AI1/AI2 on the same three seed sets
- 2v2 on seeds 1–5
- 1v1 on seeds 1–5
- homogeneous 4-car and 2-car self-play on seeds 1–5
- slow synthetic tracks on seeds 1–5

Every race must execute and produce a valid log. Promotion still requires reading the reports: aggregate move averages can worsen when a candidate saves a slow back-marker, and small crash differences can be noise.

## Round 91 promoted: proof-gated stationary launches

The staged pace proof used a velocity dot product to decide whether a rival was
ahead. A stationary car has no velocity half-plane, so the rule could never
open on the starting grid. The broad first experiment used the reachability
map's distance-to-finish heuristic throughout, but exact debugging showed that
the sole measured gain came from player 6's first Silverstone seed-15 move.
The promotion candidate is therefore narrower: it uses track-distance ordering
only for a zero-velocity car still inside the start zone. Moving cars retain
the Round-90 geometric rule, and equal or unavailable map distances fail
closed. Admission remains homogeneous-only and every existing private-route,
eight-round self/field, seal and downstream danger proof is unchanged. The
same narrowed policy is mirrored into AI1 and AI2; the 27-race strict probe is
move-identical post-mirror.

The canonical 22-track eight-car bands remained 770/0 in both columns for
seeds 1–5, 6–10 and 11–15, with no slower track. Silverstone seed 15 is the
only result change in those bands: the final finisher completes in 85 rather
than 86 moves, reducing the exact finisher-move sum from 585 to 584. An
independent integer A/B replayed both versions over all 22 tracks and seeds
1–15 (660 executions): each produced 2310 finishers and zero crashes, 329 of
330 race tuples were identical, and total finisher moves fell 144811 ->
144810. Seeds 16–30 are identical, and the Zandvoort 31–45 doom band is
unchanged (seed 32 remains the sole 6/1 race). Homogeneous 4-car (330/0),
homogeneous 2-car (110/0), and slow (140/0) batteries are exact ties. The
standard Java, golden,
pace, mixed-safety, field-neutral, staged and energy regressions all pass. The
expanded pre-mirror mixed battery was place-neutral. Its only crashes were the
same Le Mans seed-7 player-6 trajectory once in each symmetric ordering, so
they are a pre-existing mixed-field safety gap rather than a Round-91
asymmetry.

The exact post-mirror matrix is a complete self-tie: all three 22-track
eight-car bands are 770/0 in both columns at 62.714, 62.668 and 62.683 mean
finisher moves, with every per-track delta `+0.000`. Mixed 4v4 is
4.500/4.500 in all three bands (crashes 0/0, 1/1, 0/0); 2v2 is
2.500/2.500, 1v1 1.500/1.500, homogeneous 4-car 330/0, homogeneous 2-car
110/0, and slow 140/0. The corrected 12-job promotion workflow, CI and CodeQL
all pass on the exact promoted commit.

Two narrower alternatives were rejected before this candidate: reopening
zero-uncertainty high-energy moves under a strict field improvement changed a
Zandvoort trajectory but no finish result, while sweeping the staged minimum
from 35 through 30/24/16 likewise produced no aggregate gain. Ranking already
certified staged candidates by rollout outcome was inert on every pinned case.
The later exact remote screen confirmed that result on 500 race pairs. A
certified private-lane runner-up fallback was also rejected after 62 current-
champion differential pairs were move-identical and isolated instrumentation
found no rank-1 attempt in its pinned cases; it would add a second scorer
rollout on rare failures without a demonstrated pace gain. A later
progress-quorum branch was not ported: it had no differential or faster-race
evidence, counted ties and rivals up to three distance rings behind as part of
its quorum, and could invoke extra exact and deep rollouts.

## Round 92 runtime cleanup: skip a redundant smoke rollout

The dense-slow-pack and static-funnel gates already force the scorer-rival
danger search, but both scorer bodies first paid for a separate five-round
smoke simulation whose result could not change that decision. Round 92 skips
that smoke call only when one of those gates already mandates escalation;
diagnostic runs retain it. The downstream horizon, rival cap, candidate search
and selected move are unchanged. Pre/post builds produced byte-identical full
logs on Silverstone seed 15, Hungaroring seed 40, Le Mans seed 1, and
Zandvoort seeds 32/37/44. Seven interleaved warm-cache Hungaroring seed-40
runs measured 10.678 s -> 10.551 s median (about 1.2% faster) and
10.639 s -> 10.565 s trimmed mean (about 0.7% faster) for the final narrowed
Round-91 plus Round-92 build.

## Round 93: sparse fast-trap scorer recheck

The remaining mixed Le Mans seed-7 crash sat just beyond two existing model
boundaries. At global move 502, player 6 was at `(13,101)`, velocity
`(-2,-8)`. The selected `S` landing had trap tier exactly L2 and one rival
within Chebyshev distance 10. The normal three-round smom check kept it alive
but at final tier 1; the real-scorer-rival model proved it dead in round four
and kept `SW` alive. The new arm therefore applies only to a fast exact-L2
landing with one or two nearby rivals whose normal three-round verdict is
alive but final tier at most 1. Larger packs retain the established eight-
round machinery. A four-round, three-rival scorer recheck remains
survival-only and is mirrored in both AI bodies.

In both kind orderings, move 502 changes `S` to `SW`, player 6 finishes at
move 563/place 5, and the old symmetric 1/1 crashes become 0/0 while mean
place remains 4.500/4.500. An isolated old-versus-new corpus covered 1,670
paired races (3,340 executions): all 330 homogeneous eight-car pairs were
exact; 658/660 mixed eight-car pairs were exact and the other two were the
intended Le Mans rescues; homogeneous 4/2-car (220 pairs), mixed 2v2 (220),
mixed 1v1 (220), and slow synthetic (20) were all exact. The Zandvoort
seeds 31-45 doom band remains 104/1 in both columns. A 15-pair warm
exact-behaviour control produced byte-identical logs and no child-JVM CPU
regression; the repaired seed-7 race itself runs longer because the crashed
car now remains alive and finishes.

## Round 96 promoted: neutral-coast finish acceleration

The Round-94 dual-model finish sprint deliberately stopped at empty-map TTF
20. A full frontier probe through TTF 30 found many apparent one-turn
shortcuts, but both the existing full-to-finish certificate and a shorter
scorer-field proof rejected every broad extension. Exact continuation isolated
one real boundary instead: Zigzag seed 2, global move 312, player 8, where the
champion coasted with `NONE` at `(9,27)`, velocity `(2,-3)`, while cardinal
`E` reached the same safe forecast one empty-map turn sooner.

The promoted arm therefore does not raise the finish cap generally. It admits
only TTF 21-30 candidates when the incumbent is `NONE`, the candidate is a
cardinal non-coast acceleration exactly one map turn faster, kinetic-energy
gain is positive but at most five, at least five rivals remain in a mover-kind
homogeneous field, trap and uncertainty are both exactly zero, and the
candidate already has a strictly better scorer value. The incumbent and
candidate are then compared in the same eight-round, six-rival scorer-field
world. Their mover outcome and aggregate field cost must be exactly equal; any
failure or ambiguity preserves the incumbent. The established downstream
danger search remains an independent final veto.

On Zigzag seed 2, move 312 changes `NONE` to `E`. Safety remains seven
finishers / zero crashes, while finisher moves improve from
`[65,66,66,66,67,67,68]` to `[65,66,66,66,66,67,68]` (465 -> 464). The exact
frontier differential covered 22 regular tracks through seed 60 plus four slow
tracks through seed 25: 1,419 of 1,420 pairs were byte-identical, the sole
change was this one-move gain, and there were no invalid races, safety changes,
slower races, neutral divergences, or equal-sum redistributions.

The eleven-stage AI1 promotion battery was also never worse. Only eight-car
seeds 1-5 changed: both columns were 770/0, mean finisher moves improved
62.704 -> 62.703, and Zigzag improved 66.457 -> 66.429. The other ten mixed,
small-field, homogeneous, canonical and slow stages were exact ties. A warmed,
alternating-order runtime check measured target AI1/AI2 ratios of 1.0190
median and 1.0138 trimmed mean; the exact control already measured 1.0069 and
1.0041, and the target remained below the five-percent rejection boundary.
The rule was mirrored explicitly into AI2 only after those gates passed. The
post-mirror champion gate, run `31863230797`, proved all 22 regular tracks
through seeds 1-15 move-identical and all eleven promotion matrices exact ties.
The permanent regression pins both agents at the promoted 464-move result.

## Round 95 promoted: exact faster cross-model retention

Deep-pack safety arbitration normally trusts a topology-shaped opponent model
before the exact scorer-rival selector. Silverstone seed 1 exposed a narrow
false negative: at global move 147, player 3's chosen `W` line had empty-map
TTF 64, while topology preferred `N` at TTF 65. The eight-round, six-rival
scorer-field world kept both alive and rated `W` strictly better for the mover
(57 versus 58) and aggregate field (404 versus 405).

Round 95 retains the original line only for exact-L2, zero-uncertainty,
one-map-turn-faster states with at least five live rivals in a kind-homogeneous
field, and only when the common scorer-field rollout proves strict mover and
field improvement. Every geometry, seal, private-lane and downstream danger
veto remains final. Silverstone seed 1 stays seven finishers / zero crashes and
falls from 595 to 593 aggregate finisher moves.

The exact AI1-versus-frozen-AI2 differential covered 1,320 regular-track pairs
through seed 60 plus 100 slow-track pairs through seed 25: 1,419 of 1,420 were
byte-identical, one was faster by two moves, and none was invalid, unsafe,
slower, or redistributed. The eleven-stage promotion battery changed only the
eight-car seeds 1-5 band: 770/0 in both columns, mean 62.706 -> 62.704, with
Silverstone 85.000 -> 84.943. A warmed paired runtime test was noise-neutral:
target median/trimmed ratios 1.0007/1.0020 and exact-control ratios
0.9915/0.9980. The explicit AI2 mirror and complete post-mirror identity gate
passed before merge to master `434da856d1a454a417eecb373eb7f15869296b23`.

## Round 94: homogeneous finish-sprint extension

Round 75's finish sprint accepts a strictly faster candidate only when two
independent joint worlds both finish at its empty-map lower bound. A broad
experimental cap increase from map TTF 15 to 20 contained real pace, but its
workflow searched for `DIVERGENT` while the probe emitted `DIVERGED`. The raw
26-track artifacts actually contained 21 changed races: 11 faster, nine
outcome-neutral, and one four-move Le Mans seed-12 regression caused by a new
`NONE` choice. Mixed 4v4 screens also exposed small place redistributions.

The promoted rule therefore preserves the legacy TTF<=15 policy everywhere.
Only the new TTF 16-20 band requires mover-kind homogeneity and forbids
`NONE`; the trap-L1 ceiling, strict empty-map improvement, dual optimal-finish
proof, and downstream danger search remain unchanged. On current Round-93
master, the 22-track seeds 1-15 A/B completed 2,310 finishers with zero crashes
in both columns: 312/330 races were exact, ten were faster, eight changed line
without changing their finish list, none was slower, and total finisher moves
fell from 144,810 to 144,793. Cog seeds 1-15 adds one three-move gain, making
the measured 345-pair corpus 20 moves faster overall. The independent
Nurburgring seed-19 golden adds one more finisher-move gain (last finisher
99 -> 98; total game turns 752 -> 750), for 21 measured moves across 346 pairs.

Big Oval seed 7 is the smallest active pin: `[20,21,22,22,22,22,23]` becomes
`[20,20,21,21,22,22,23]`. Homogeneous four-car seeds 1-5 also improve from
61.103 to 61.091 with 330/0 in both columns. Two-car, 1v1, 2v2, slow, and the
Zandvoort seeds 31-45 doom band are exact; the mixed Gear, Big Oval, Spa, Long
Loop and Le Mans seeds 1-15 checks all return 4.500/4.500 with zero crashes
after the homogeneity gate. The mirrored final bodies pass the strict 27-race
identity probe.

## Round 90 frontier candidate: refined high-energy forward packs

Above-cap staged candidates need four rivals ahead plus the existing fail-closed
exact private-route proof. They must recover nonzero uncertainty; with five or
more rivals ahead, the field rollout must improve strictly. This retains the
Nurburgring seed-1 and Interlagos seed-29/47 boundaries while keeping six-move
Spa seed-17 and Zandvoort seed-44 gains on the current funnel-guarded frontier.
AI2 and mixed fields are unchanged; seal and danger vetoes remain final.

## Round 82 frontier candidate: stable three-ahead slow packs

Round 82 composes the Round 81 staged-pace proof with the promoted Round 78
scorer-fidelity champion. The four-ahead admission is byte-for-byte unchanged.
The adjacent **exactly three rivals ahead** class may now enter the same
eight-round, six-rival scorer certificate only when the incumbent landing has
reached the existing slow-pack speed floor (`speed² >= 16`) and the incumbent
field rollout is finite. Candidate selection, trap and uncertainty bounds,
energy cap, strict self improvement, non-worsening aggregate rival cost, seal
guard and final danger veto all remain unchanged.

The unrestricted three-ahead arm exposed the structural boundaries. A
Hungaroring seed-8 decision at speed² 4 cost three field moves, while every
recovered gain fired at speed² 17–25. Le Mans seed 3 produced an equal-sum
field redistribution only when the incumbent scorer world contained a failed
rival; the finite-field guard retains the integrated-frontier finish list
`[65, 67, 69, 70, 71, 72, 74]`. No track or seed name appears in the policy.

A 126-race hot screen, including the fresh Coil, Hungaroring and Zandvoort
counterexamples, returned **123 identical races and three pace improvements**:
Coil seed 18 saved one move, Hungaroring seed 10 saved four, and Hungaroring
seed 25 saved three. Net delta was **-8 moves**, with no crash, pace or
redistribution regression.

The JDK-25 promotion battery passed exact verification and every matrix. The
five eight-car bands remained 770/0 in both columns, with AI1/AI2 mean finisher
moves of 62.72/63.69, 62.67/63.66, 62.68/63.64, 62.72/63.64 and
62.66/63.62 for seeds 1–5 through 21–25. Canonical seeds 1–15 have no slower
reported track. Mixed, small-field and slow stages remain crash-free; the
self-play-only gate is inert in heterogeneous fields.

Doom-dense Zandvoort seeds 31–45 and Spielberg seeds 16–20 were compared
candidate-versus-integrated-frontier, not merely against frozen AI2. Their
outputs are byte-identical, proving that the inherited Zandvoort crash profile
and Spielberg `+0.11` line are not Round 82 regressions. The candidate also
preserves AI1's seed-42 Zandvoort rescue over AI2.

## Round 79 frontier candidate: field-neutral private lanes and convoys

Round 79 is an **AI1-only** candidate rebased on the Round 75 champion after
Round 76's certified-L2 arm was rejected and reverted. It retains Round 78's
adversarial private-lane pace proof:

- a cheap three-ply rectangle over-approximates every rival acceleration and
  follows an empty-map-optimal line until it reaches three private alive exits;
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

The rounds-79-to-94 stack plus the round-83 funnel guards were promoted on 2026-08-14, so AI1 and AI2 are identical again. The champion races roughly a full move per finisher faster than its Round-78 predecessor with a strictly better crash ledger; Round 91 additionally saves one proven Silverstone seed-15 finisher move through a proof-gated stationary launch, Round 93 removes the symmetric mixed Le Mans seed-7 crashes through a sparse fast-trap scorer recheck, and Round 94 recovers 21 measured finisher moves by extending the dual-model finish sprint only in homogeneous fields. The pre-Round-91 composition battery swept never-worse on every stage (770/0 across all 8-car bands at -0.95 to -0.99 with zero slower tracks, mixed-field places won crash-free, 4-car repaired and -0.64, 1v1 -0.30, slow exact). The final mirrored body is move-identical across the strict probe. Self-play pace gates key on kind-homogeneity with the mover rather than AI1-ness. The champion retains the earlier bounded safety proofs:

- Round 75 recovers provably safe finish pace. Within 15 empty-map turns of the flag, a strictly faster low-trap candidate may replace the scorer choice only when both the score-shaped-rival and scorer-rival joint models finish at that candidate's empty-map lower bound. The first partial simulated round is accounted for explicitly, and the normal danger-joint search remains an independent downstream veto. On Monaco eight-car seed 16, this changes two late `S` choices at map ttf 15 to `SW` at ttf 14 and saves two racer-turns without changing the seven-finisher, zero-crash result.
- Round 68's dense slow-pack trigger invokes the expensive real-scorer-rival rollout only when a fast-enough car is inside an all-field funnel and a near-equal low-trap alternative exists. On Le Mans seed 4 it changes player 7's move 55 from `SE` to `SW`, converting 6 finishes / 1 crash into 7 / 0.
- Round 69's cross-model certificate handles locally narrow fast-pack moves. The topology-shaped model must prove the chosen move dies and propose a survivor; the independent scorer-rival model must also keep that alternative alive. On Hungaroring seed 20 it changes player 5's last avoidable choice at move 181 and prevents its move-221 crash.
- Round 70 extends the real-scorer-rival rollout from five to six rounds only for slow moves already at trap tier L1. On four-car Interlagos seeds 3 and 4, it sees the chosen `W` die one round beyond the old horizon and selects oracle-proven survivor `NONE` at move 456.
- Round 71 generalises the dense slow-pack trigger to four-car fields. It still requires every live rival within Chebyshev radius 10 plus a near-equal low-trap escape, but lowers the speed floor from 16 to 12 when exactly three rivals remain. On Monaco four-car seed 9 it changes player 1's move 27 from `E` to `W` and removes the move-148 crash.
- Round 72 makes the worst-case seal guard trap-monotone. The guard may replace a sealable scorer choice only with an unsealable move whose local trap penalty is no worse. On Nurburgring eight-car seed 19 the old guard overrode scorer-preferred `N` (trap 0.5, oracle-alive) with `E` (trap 2.0, doomed); retaining `N` converts 6 finishes / 1 crash into 7 / 0.
- Round 73 certifies convergence dooms the smom pre-screen cannot see. When the deep pre-screen reads a fast pack move as alive and non-fragile but at least three rivals sit ahead of the landing (positive dot with the landing velocity), the chosen move is re-verdicted in the scorer-rival world with the rival cap widened from the nearest 3 to 6 — on Interlagos eight-car seed 10 the killers are ranks 4-6 by landing distance while the nearest 3 are the harmless rear queue. The switch stays survival-only. This repaired the round-72 promotion regression (Interlagos 8-car s6-10: 769/1 back to 770/0, and the mixed-field crash to zero) with exact ties on every other battery stage.
- Round 74 covers the complementary compressed-rear-queue shape. When all seven rivals are within the deep-pack radius, at most one is ahead, at least two rival bodies already occupy the mover's neutral 3x3 landing grid, and a near-equal low-trap escape exists, the same widened scorer-rival certificate arbitrates the move. On Zigzag eight-car seed 22, the smom model incorrectly keeps `S` alive at move 72; the scorer-rival model proves it dead within two rounds and keeps `NW` alive, preventing player 8's move-104 crash. The trigger was seen only 13 times in a 129-race harvest and changed only the failing target.
- Round 78 repairs two stacked fidelity gaps found by the second fresh-seed harvest. The round-60 slow smoke test now runs the scorer-rival world instead of the smom proxy (a chaser converging from behind lands in the round-59 nearest-rival set, so behind-convergence dooms are finally visible), and the slow escalation certifies alternatives with a scorer-modeled self (`scorerSelf`) because the selfMove proxy killed the only true survivor at Zandvoort seed-45 move 920 in every offline world. One upgrade on existing surfaces — no new trigger gates — eliminated three of the five harvest crashes (Zandvoort s45 and s34, Hungaroring s40) and improved the doom-dense Zandvoort 31-45 band from three crashes to one, with never-worse full gates and both mixed-field bands crash-free.
- Round 93 covers the sparse fast-L2 fidelity gap. Only one or two nearby rivals, a live-but-tier-1-or-worse three-round smom verdict, and trap exactly L2 may invoke the four-round scorer-rival recheck. On mixed Le Mans seed 7 it changes player 6's move 502 from `S` to `SW`; player 6 then finishes fifth instead of crashing 30 global moves later. Both symmetric kind orderings are repaired, while 1,668 of 1,670 old/new corpus pairs are exact and the other two are precisely those rescues.
- Round 94 extends the Round-75 dual optimal-finish proof from map TTF 15 to 20 only when every live rival shares the mover's policy kind, and forbids `NONE` in the new band. That boundary removes the broad experiment's sole slower race and its mixed-field place shifts while retaining all eleven measured faster races. On Big Oval seed 7 it changes move 12 from `N` to `NW` and saves three finisher moves; the canonical 22-track seeds 1-15 total improves by 17 moves with no slower race or safety change. Nürburgring seed 19 adds another one-move finisher gain and updates its golden from 752 to 750 total turns with unchanged 7/0 results.

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
