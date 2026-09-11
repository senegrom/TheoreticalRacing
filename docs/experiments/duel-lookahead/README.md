# Two-move duel proofs: experimental racecraft branch

Baseline: `7220dd5784d1ae6cb8833616a819c11d7c3243e9` (round-233 champion).
Branch: `racecraft/two-move-duel-proofs`.

**Status: implemented, tested as an opt-in candidate, not promoted.** The
bounded mixed-field screen found no finishing-place gain. The complete fleet
promotion battery and the required JDK 25 release build have not been cleared.
No champion/golden expectation, track, physics, map or `user.properties` changed.

## Ideas implemented

1. **Set up a guaranteed finish, rather than seeing only this turn's flag.**
   Search our move, every physical rival reply, then our finishing reply. Carry
   exact checkpoint and lap credit through both projected moves. A rival that
   can finish first invalidates the setup.
2. **Create a blockade one turn before it becomes immediately decisive.**
   Accept a setup only when every surviving rival reply admits a legal move
   that leaves it no physical escape. This extends the existing last-rival
   tactic without guessing the opponent's policy or paying a proximity penalty.
3. **Prefer quicker proofs and preserve the unproved fallback.** The existing
   immediate tactic keeps precedence. The new search prefers the smallest
   worst-case terminal horizon, with deterministic direction-order ties. Any
   unproved position goes back to the unchanged scorer.

These follow the position-first rule in `AGENTS.md` and the lessons in
`racing-memory.md`, round 233: do not restore blanket caution/spread penalties,
and do not promote the previously inconclusive multi-car blocking arm again.
This branch's experiment journal is recorded here, separately from that ledger.

## Certificate and integration

`RaceAiDuelSearch` considers exactly two live cars, even in an eight-slot roster
or across the array wrap. The detached state includes position, velocity, lap
and next checkpoint. All hypothetical transitions use `RaceGame.evaluateMove`.
An illegal rival reply loses; a rival finish refutes; a legal reply must have
an answering proof. All nine physical rival accelerations count, including
reachability-dead landings and velocities outside the AI's own planning cap.

Our velocity stays within the AI domain. A dead own landing is accepted only
when the duel provably ends before our next turn. Terminal finish precedence,
combined checkpoint/finish moves, vacated old cells, and timeout checks before
each move are preserved. Projected counters use `long`; retired slots consume
no moves but still count in the original roster's timeout budget.

The finite tree is at most four plies, with fewer than 7,400 referee evaluations
before short-circuiting. It is not an unbounded minimax search, an estimate of
finishing place, or a proof for three or more live cars. Players, histories,
progress, occupancy and decision frames are not mutated.

`RaceAiTactics.winNow` calls it only after the existing immediate tactic
abstains **and only for slots selected by `candidateSlots`**. Both AI labels
support it. An unset property preserves the champion's decisions; it does not
silently turn AI1 into the candidate. For an eight-car mixed race, use a
separate properties file with `candidateSlots=1,3,5,7`, then mirror with
`candidateSlots=2,4,6,8`. For all candidate cars use all actual roster slots.
The proof still waits until only two cars are live.

## Measured results

The completed screen uses seven tracks (Hairpin, Chicane, Big Oval, Circle,
Gear, Silverstone and Zigzag), seeds 1-2, both mirrored cohorts, two/eight-car
rosters and all three start modes: **168 races / 84 mirrored pairs**. Every
pair was validated with the existing schema-2 fleet manifests and
`tracks/head_to_head.py`; failed/incomplete grids were not scored.

| Roster | Start placement | Races | Candidate mean place | Champion mean place | Candidate/champion wins |
| --- | --- | ---: | ---: | ---: | ---: |
| 2 | legacy | 28 | 1.500 | 1.500 | 14 / 14 |
| 2 | informed | 28 | 1.500 | 1.500 | 14 / 14 |
| 2 | scatter | 28 | 1.500 | 1.500 | 14 / 14 |
| 8 | legacy | 28 | 4.500 | 4.500 | 14 / 14 |
| 8 | informed | 28 | 4.500 | 4.500 | 14 / 14 |
| 8 | scatter | 28 | 4.500 | 4.500 | 14 / 14 |

Every track's mirrored place difference is zero on this small slice. The
informed two-car cohort has one crash per policy; the other cohorts have none.
Crash counts are descriptive, not a separate promotion veto. Six retained
`*-head-to-head.txt` reports contain the complete printed comparisons.

The candidate does change decisions: 18/84 mirror pairs have different move
logs after removing candidate-assignment metadata. There is one concrete pace
example: **Circle, legacy start, seed 2, winning slot 2 finishes in 114 moves
with the candidate, versus 115 with the baseline**. Re-running the actual
baseline JAR without any candidate slots confirmed the 115-move finish and
the same finishing order. This one example is not a fleet-wide pace or
win-rate claim. Aggregate candidate/champion move totals in the mixed screen
are equal; switching the winner's policy also ends the trailing car's race
one turn sooner in that example.

The eight constructed Hairpin blockade setups expand to **64 variants** across
both labels, both slot orders and two/eight-slot rosters. The end-to-end V2 test
checks **360 legal first rival continuations**, asks the actual AI for each
follow-up, and checks every final physical reply. All carry out the promised
win. These are constructed tactical states, not 64 naturally occurring wins.

An independent detached-player verifier checks 12,000 deterministic sampled
positions: 5,060 valid boards, 1,652 certificates, including 351 that need the
second own move. It also checks progress, finish/refutation precedence,
timeout boundaries, human speed-cap escapes, extra live rivals, slot isolation
and absence of live-state mutation. The randomized census is a soundness
screen, not a frequency estimate for normal racing.

Core/Main tests, all 12 unchanged golden races, all 24 `ai1_*_regression.py`
scripts (23 existing plus the new duel test), 99 Python tooling tests, headless
smoke, query replay, lap progression and 17 cross-era/live-referee differentials
passed on the supplementary JDK-21 build. No expected result was re-frozen.

## Reproduce

With JDK 25 or newer:

```sh
sh build_main.sh
sh run_tests.sh
python3 tests/golden_races.py
for test in tests/ai1_*_regression.py; do python3 "$test" || exit; done
python3 -m unittest discover -s tests -p 'test_*.py'
```

The measured bounded screen (do not run several large-heap grids concurrently
on a memory-limited host):

```sh
python3 docs/experiments/duel-lookahead/run_screen.py \
  --out /tmp/duel-screen --heap=-Xmx768m \
  --tracks hairpin chicane bigoval circle gear silverstone zigzag
```

The wrapper defaults include Monaco and a 2 GiB heap; it creates independent
profiles, mirrors actual roster slots, validates completion, and refuses to
overwrite a different existing profile. It never changes `user.properties`.
Use a fresh output directory whenever the build/configuration changes.

A full mixed-policy track/seed slice, **not performed in this branch's local
validation**, is selectable without changing the runner:

```sh
python3 docs/experiments/duel-lookahead/run_screen.py \
  --out /tmp/duel-full --tracks ALL --seeds 1-10 --heap=-Xmx2g
```

Promotion still requires the repository's complete homogeneous fleet grids
for every start mode, mirrored head-to-head clearance, a fresh seed slice,
and supported-JDK validation. This small screen does not waive those gates.

## Environment and limitations

The available runtime was OpenJDK 21.0.11. The normal `build_main.sh` correctly
refused it because JDK 25 is required; that guard was not changed. Supplementary
native compilation used `javac --release 21 -Xlint:all -Werror` on all current
sources, and the resulting JAR passed `jar --validate`. The release-JDK and
browser parity suites were not run, so this is not release validation.

Measured candidate JAR SHA-256:
`a16df03ef9c46c40ae16862bdf19458a6352adca914c2dc89bfbb85097d4c9f8`.
Baseline JDK-21 JAR SHA-256:
`e902d71486bfc949b75b5de9e692ede8fd0eb7024dcc5ad041cf3fd4249d2b88`.

Initial low-heap runs exhausted Java memory on larger maps; another concurrent
run exceeded the host's 4 GiB limit. Those incomplete grids are excluded.
The final screen used one 768 MiB JVM at a time and omitted Monaco; the core
regression corpus used an explicit 2 GiB heap, including its Monaco and Le Mans
cases. `validation.json` records the final completed checks and measured scope.
