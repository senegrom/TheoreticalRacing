# Racecraft: prove the last-rival win

Reviewed baseline: `8db66b3b87bcd3957e5fc595de09641699308879`.

This change adds exact, immediate two-car tactics before the existing scorer.
It does not retune weights, increase rollout depths, alter track rules, change
starting positions, or substitute a cheaper browser AI. Both AI labels share it.

## Missed opportunity

The older few-rival seal is deliberately conservative: it requires a later
array slot and future escape certificates. With exactly two active cars those
conditions can miss a decisive move. The opponent moves next even across the
last-slot/first-slot boundary, and after its forced retirement the referee ends
the race immediately. A hypothetical future escape after that point is irrelevant.

`RaceAiTactics.winNow` first takes any actual immediate finish, including a move
that passes the last checkpoint and the finish together. It then examines a
last-rival blockade, using the referee rather than a prediction of the opponent.

## Certificate

With exactly two live cars, remove the mover's old cell from occupancy and
enumerate the opponent's nine accelerations. If any really finishes, abstain:
a terminal landing cannot be blocked. If more than one is legal, abstain:
distinct accelerations have distinct destinations, so one car cannot block all
of them. If none is legal, leave the existing policy to handle the already
trapped opponent. Otherwise there is one unique legal destination.

If the mover can occupy that cell with an immediately legal move, it wins the
best remaining classification: on the next turn every opponent acceleration
crashes (or the race limit retires it first), and `RaceGame.checkFinished`
immediately classifies the sole survivor.
The mover need not be empty-track reachability-alive after this *terminal duel*.
This is not permission to choose a dead landing in an ordinary multi-car fight.

The helper abstains unless exactly two cars remain and the mover is not already
subject to the referee's turn limit. Retired slots do not count as opponents.
It neither installs hypothetical player state nor changes decision frames.
The existing multi-rival scorer and its fallback logic remain in place.

All **physical** opponent replies are counted, including reachability-dead
landings and velocities beyond the AI's planning cap. A human can accelerate
from 12 to 13; pretending that this legal reply does not exist would invent a
false victory. The mover still respects its own AI planning domain.

## Regressions

`RaceAiTacticsTests` runs with the core suite. It checks array wrap, retired
slots, an additional live rival, unreachable blocks, finish precedence,
non-final crossings, combined checkpoint/finish moves, turn-limit precedence,
physical human replies beyond the planning cap, and 12,000 deterministic
randomized soundness trials. A live-referee test commits a block and the
opponent crash in both slot orders and checks actual final classification.

`tests/ai1_racecraft_regression.py` is picked up by the existing champion-test
loop. Seven constructed Hairpin duel positions expand to 56 checks across
both AI labels, both mover slot orders, and two-player/eight-slot rosters.
Every proposed block is legal; the V2 referee classifies all nine opponent
replies as crashes. Track geometry is frozen in a test fixture.

Those seven original-slot examples were losses under the baseline continuation
and are now proved wins. Three came from discovery seed 725; four came from a
separate same-heading search with seed 20260906. They are **constructed tactical
positions**, not a claim that seven naturally occurring benchmark races flipped.

## Reproduce

```sh
sh run_tests.sh
sh build_main.sh
python3 tests/ai1_racecraft_regression.py
python3 tests/query_replay_regression.py
python3 tests/lap_progress_regression.py
python3 tests/golden_races.py
for test in tests/ai1_*_regression.py; do python3 "$test" || exit; done
sh web/build.sh
python3 web/tests/parity.py --quick
```

The ordinary-race comparison is a bounded regression screen, not the expensive
whole-fleet promotion battery or a measurement of general overtaking strength.
No golden/champion fixture expectation is changed to accommodate this tactic.

The completed native comparison covers 74 baseline/candidate pairs on
Silverstone, Hairpin, Triangle, Chicane, Big Oval, Circle, Gear and Monaco,
with two/eight cars, separate seed windows, and one/three-lap profiles. All
74 pairs retain identical behavior-bearing logs and finishing orders: 21,032
moves, 230 successful finishes, zero crashes and zero timeouts per build.
This deliberately reports no ordinary-race win-rate or pace improvement.
