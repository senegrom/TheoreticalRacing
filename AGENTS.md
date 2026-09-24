# theoreticRacing — instructions for coding agents

The live authority for the racing AI campaign is `racing-memory.md` (newest
entry first). Read its top entries before changing `src/tr/logic/RaceAi*.java`
or the maps in `Reachability.java` / `OptimalPotential.java`, and add an entry
there for every change you push: what it does, and what it measured.

## Racecraft evaluation rule (decided by the owner, 2026-09-07)

We care about **lexicographic performance**: every car races for its own
finishing position first and its own time second. Judge a policy by how the
cars running it finish, not by the field's summed moves.

- Every agent tries to be as fast as possible. A move by the winner that slows
  the second car is **not** to be punished.
- Forcing a rival into a crash is legitimate racecraft and is **not** to be
  punished. A car that can be forced out has itself to blame for being there:
  the burden is on every car never to enter a state a rival can close.
- **No active cooperation.** The car behind must never let the car ahead win;
  no yielding, no waiting, no team play of any kind.

Consequences for measurement. Where a change touches how cars interact, the
criterion is the head-to-head place comparison: run candidate cars and champion
cars in the SAME races, mirror the slot assignment so grid advantage cancels,
and compare their finishing places (`tracks/head_to_head.py`). A car that
crashes already scores as that car's last place, so mean place prices safety
correctly and needs no separate gate.

The fleet's summed-moves and crash counters are FIELD metrics. They never
veto a candidate. In particular a faster leading car whose pace costs the
second car a crash is an improvement, and a field made entirely of the
candidate is allowed to crash more often than the champion's field. Report
those numbers as description, never as a rejection.

## Rank-first rule (decided by the owner, 2026-09-23)

Wherever the AI compares simulated outcomes -- the chooser, the danger and
thread searches, every pace override -- it ranks the mover's **place first
and its time second**. A rollout in which a rival finishes ahead of the mover
is worse than any rollout in which fewer do, whatever the times; finishing
first and being classified behind a finisher are never the same verdict. The
rollout verdict carries it: `ahead * VERDICT_PLACE_STRIDE + time`
(`RaceAi.rankVerdict`), identical to the old verdict when nobody finishes
ahead. This is mandatory, not a tuning: a candidate that ranks outcomes by
time alone does not conform, whatever it measures.

## Single-player rule (decided by the owner, 2026-09-21; literal since 2026-09-23)

With **no live rival within 20 cells** (Chebyshev), a car races the
single-player optimum: the exact solo descent (the round-214 alone path), in
every race mode, exactly as it drives alone. The faithful joint world (the
round-260 chooser) is consulted only when a rival is within that distance.
Round 261 priced the chooser gate at +0.001 places in 8-car packs (81 of 84
boards tied) and +0.004 on scattered starts, all of it one synthetic course;
round 267 priced the solo descent at 20 cells instead of 40 at -0.000 on
random and held-out starts, -0.005 scattered, +0.001 computed and +0.008 in
duels (one course, hybrid1). The owner takes that for the guarantee.
`AI1_CHOOSER_MAXDIST` in `RaceAi.java` is the rule's constant for both;
changing it is a rule change, not a tuning, and needs the owner.

## Measurement discipline

- Any change that can alter a decision gets a fleet grid before it ships
  (`tracks/fleet_grid.sh`; 730 races a seed slice), on random starts
  (`aiStartPlacement=legacy`, the headless default), computed starts
  (`aiStartPlacement=informed`) and scattered starts (`aiStartPlacement=scatter`).
  A few dozen races rank candidates; they do not clear them.
- Correctness fixes that the fleet clears ship even at noise cost; pinned
  artifacts are re-frozen from measurement, with the reason beside the number.
- Before a promotion, also run the lone-candidate check
  (`docs/experiments/duel-lookahead/run_1vfield.py`): one candidate car
  against n-1 champions, rotated through every seat and paired with the
  all-champion race on the same track, seed and seat. It answers whether the
  candidate gains places on the current champion as a lone entrant, which
  the mirrored half-and-half screen does not (owner, 2026-09-23).
- Build with `sh build_main.sh` (JDK 25, warnings are errors); run
  `sh run_tests.sh`, `python tests/golden_races.py` and every
  `tests/ai1_*_regression.py` before publishing.
- Never edit `user.properties`; never regenerate fleet tracks in place; do not
  change tooling under `tracks/` while a fleet grid is running, the runner
  binds it into the grid's manifest.
