# Physical occupancy, rollout termination and timeout Undo (2026-09-12)

> Landed on master as round 248 (2026-09-15) after the mirrored-fleet battery
> against the round-247 champion: -0.102 places in eight-car random-start
> fields, -0.129 on computed starts, -0.131 on held-out seeds, -0.014 on
> scattered starts, -0.010 in duels. The branch-status remarks below are
> historical; racing-memory.md is the authority.

**Historical validation record:** the prepared patch was published as `55a63eff`
on the review branch. See [the follow-up](simulation-followup-review.md) for the
subsequent legal-blockade and mover-progress repairs and current release scope.

Review findings originally reproduced at `745798f613`. This patch is based on
`9668703dc1489383bde78f2460476e9f6daa1da0` and preserves the subsequent round-238
cleanup, the promoted two-move tactic and the opt-in third-move extension.

## Occupancy is about the physical opponent, not the AI map domain

`RaceAiPrivateLane.ExactRivalReach` now stores exact coordinates, velocities,
lap counts and pending gates. It no longer packs rival states into the
AI-capped reachability index or discards accelerations beyond that cap.
Every transition uses the referee's detached `evaluateMove` result. A rival
is removed only for an illegal move or a genuinely race-ending finish;
a geometric finish-line crossing with laps or gates still owed remains live.

The insertion-ordered frontier keeps traversal deterministic. The existing
per-session node budget and answer cache remain; exhausted search reports
possible occupancy, never an exclusion. Collision and turn-limit constraints
are deliberately ignored in this occupancy over-approximation, since including
extra paths is conservative. The outer kinematic rectangles remain unchanged.

The speed-13 counterexample now retains the rival's landing at (33,10) and
rejects the incorrect three-private-exit certificate. The unchanged bundled
Circle reproduction now retains the first-lap crosser at (52,8). Tests also
cover positive/negative starting speeds outside the map domain, real final
finishes, owed checkpoints, combined checkpoint/finish events, differing
progress ledgers, multi-step continuations and budget exhaustion.

## Classify the survivor before scheduling another move

`simOutcomeCore` counts the live cars in its projected board, including
already-classified players and an initial finishing candidate. After a modeled
retirement it applies the same last-survivor threshold as `checkFinished`.
A one-car time trial still has to finish and is not classified immediately.
The existing `simFinishVanish` choice still controls finish removal in a
rollout; this patch does not change that modeling parameter.

At termination the survivor has zero remaining distance. Optional rival costs
retain already incurred projected moves; they do not charge another move or
an unreachable-distance penalty to the classified survivor. Costs of rivals
that already failed remain recorded. Thread-fragility audits likewise do not
count a nonexistent next turn. An initial candidate also respects the real
referee's mover-first turn limit before any finishing credit is applied.

Regressions cover every mover slot and array wrap, two rival crashes, a
finish followed by a crash, timeouts, already-finished rivals, the last horizon
ply, a finishing candidate, optional cost vectors without field output, and
the solo exception. The original live-referee fixture awards first place after
two rival moves; the corrected rollout now agrees instead of predicting a
third, fatal move for the survivor.

## Timeouts are committed interactive actions

The timeout branch snapshots the pre-move state before logging or retiring a
player, just as other committed interactive actions do. Automatic races still
allocate no Undo snapshots. Declining crash consent still creates no action.

The browser adapter regression executes the shared production `commitMove`
and `clickedUndo` methods with non-modal dialog transport. Undo restores the
timed-out player's slot, clock, classification, coordinates, velocity, lap
ledger, path history and log bytes. Repeating the timeout and undoing again is
deterministic, and a second Undo reaches exactly the preceding human action.

## Validation and publication status

The new Java suite is in `run_tests.sh`; timeout checks are in the existing
`BrowserTests`, already executed by native browser parity CI. New regressions
fail on the unmodified base source and pass with this patch. No referee rule,
map format, bundled track, saved user configuration or golden expectation is
changed. These fixes can affect AI decisions; they are not a claimed policy
promotion or a measured campaign gain.

Local validation uses supplementary OpenJDK 21. The 159 Python tests, Java
contracts, all 24 champion regression scripts, real configuration runners and
six-case native adapter parity pass. Browser tooling (29 tests), worker contracts
(8 tests), HTTP ranges and syntax checks also pass.
Nine of twelve frozen races still match; Monaco s9/4p, Monaco s16/8p and
Interlagos s10/8p have changed hashes. Their finishing orders, finisher counts
and crash counts are unchanged; Monaco s9 takes 549 moves rather than 551.
The unmodified base passes all three under the identical JDK and 2300 MiB heap.
A component-isolated Monaco s9 check reproduces the base with occupancy-only
changes and the new trace with rollout-only changes. The existing golden
expectations are deliberately not rewritten without campaign evidence.

These are real behavioral differences, so this is not a release-cleared patch.
Supported JDK 25/26 validation and the full required fleet campaign remain
release checks, not completed claims. This session could read GitHub, but exposed no write action, and the
shell could not resolve github.com. The patch is therefore prepared locally,
not published to master. The accompanying evidence report records exact local
commands, successes and any remaining validation limitations.
