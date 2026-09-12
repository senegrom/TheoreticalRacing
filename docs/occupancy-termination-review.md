# Physical occupancy, terminal rollouts and timeout Undo (2026-09-12)

Follow-up to the four findings at `745798f`, applied on `9668703`. The newer
round-238 funnel deletion and the existing two-move champion/opt-in third move
are preserved. These are corrections to model/referee agreement, not a new
racing heuristic or a promotion of the third-move candidate.

## A private lane must exclude every physical rival continuation

The bounded occupancy fallback now carries exact position, velocity, lap and
next-gate state. It does not pack rival speeds into the AI map's limited velocity
range or apply that planning cap to opponents. Additions are widened before
checking the board, so large query velocities cannot wrap into a valid cell.

Each transition uses `RaceGame.evaluateMove` with the rival's projected progress.
Only an illegal move or an actual terminal finish removes a path. Ordinary lap
crossings and crossings with checkpoints still owed do not erase a live rival.
States with equal coordinates and velocity but different progress remain distinct.

The broad kinematic rectangles and the session's shared node budget are retained.
Collisions and timeouts are deliberately ignored in the occupancy proof: this
can add possible rival paths, never remove a legal one. Budget exhaustion still
means "may occupy", not a private-lane certificate. Insertion-ordered state sets
keep the budget deterministic. No persisted reachability-map format changes.

## Rollouts stop at the referee's terminal classification

The rollout counts remaining active cars and stops immediately after a finish,
crash or timeout leaves one survivor (zero in a one-car race). It also handles a
candidate that ends the race before another projected turn. The survivor has no
remaining driving cost and receives terminal tier 3; it is not asked to survive
a nonexistent next move. Rival cost vectors retain already-incurred moves and
failed-rival diagnostic costs, but do not charge a classified survivor for an
unreachable finish. These are diagnostic costs, not a new policy objective.

A pending candidate is checked against mover-first timeout precedence before
its transition, so a timed-out mover cannot receive a fictitious finish. The
already-applied query path does not count that candidate a second time. Player
frames and all live state remain protected by the existing detached workspace
and restoration path. The counterfactual finish-vanish option is retained.

## Timeout is an action for Undo

Interactive timeout retirement now snapshots the complete pre-action state,
just as a committed ordinary move does. Undo restores the retiring player's
clock, slot, log, positions, velocities, history and progress rather than
consuming the previous human move. Auto-play still allocates no Undo snapshot.
Declining a crash confirmation still does not create a committed action, and
finished races retain the existing disabled-Undo rule.

## Regression evidence and measurement boundaries

`ReviewBoundaryTests`, run by `run_tests.sh`, covers positive/negative speed-13
replies, out-of-map initial speed, fail-closed budgets, the reported false
private-exit certificate, non-final and final crossings on unchanged bundled
Circle, owed checkpoints and continued occupancy after a lap crossing. A separate
detached-Player expansion checks 26,199 nonterminal states against the bounded
occupancy oracle. This is finite differential evidence, not a universal proof.

The lifecycle tests exercise all three mover positions (including round wrap),
forced rival crashes, rival timeouts, rival finishes, a terminal candidate, the
one-car exception and optional tier/field/rival outputs. The actual referee
independently classifies the forced-crash fixtures after exactly two moves.
The browser adapter's `BrowserTests` includes nonmodal tests of the shared
production commit/Undo path, including repeat/redo and first-action timeouts.

Each of the four new regressions fails against the pre-fix source and passes
with the corresponding repair. Original courses and user settings are preserved.
All 24 existing champion regression scripts pass locally without changing their
expectations. Supported-JDK and fleet results belong to the validation evidence;
local Java checks use supplementary OpenJDK 21.

## Measured golden updates, not relaxed assertions

Three AI2 trajectory hashes change because the rollout no longer predicts moves
after the referee has classified the survivor. Rebuilding the original source
reproduces all three committed expectations. A separate build with ONLY the
rollout fix reproduces each corrected full-patch log byte-for-byte after the
existing normalization. No private-lane change is needed to explain these cases.
Every finishing order, finisher count and crash count is unchanged:

| Case | Original turns | Corrected turns | Corrected normalized SHA-256 |
| --- | ---: | ---: | --- |

| monaco-s9-4p | 551 | 549 | `02674393f530f40a853f07b60effa7a95caa2024b9df7be164ded9c811e2887e` |
| monaco-s16-8p | 1124 | 1124 | `fc0ec00bfd89988b51b6aff4363c945d0ebf09d1309acbe065eb152a0dbcc241` |
| interlagos-s10-8p | 999 | 999 | `fefc488ec4923427e16c7699d1df004f25014ccb4f1b2a98ea7d34ff220b4b2b` |

Monaco seed 9 first diverges at move 539, where P3 takes NW rather than W;
its eventual third-place finish is two turns earlier. The other two cases
change trajectories without changing the number of turns. The nine unaffected
goldens retain their exact expectations. The suite still checks full hashes
and summaries, rather than ignoring these late-race differences.

## Before/after measurement design

The separate validation fleet builds both versions into one measurement-only
JAR. Candidate slots select the corrected private-lane and rollout models;
unselected slots use exact copies of the pre-fix methods. Both cohorts retain
the same two-move champion, with the optional third-move extension disabled on
both sides, so it cannot confound this comparison. The production commit does
not include the old methods, cohort shim or helper workflow.

The intended coverage is all 84 courses, seeds 1-10, complementary eight-car
assignments, and legacy/informed/scatter starts at explicit -Xmx8g: 5,040 races.
Track subsets are disjoint and all raw logs are validated again by the normal
head_to_head.py scorer when combining them. Only completed validation artifacts
establish those results; this document does not label a pending job as passed.
Crashes and summed moves remain descriptive, not independent acceptance gates.
