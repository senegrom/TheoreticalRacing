# Private-lane and lifecycle correctness follow-up (2026-09-12)

Base: `745798f613406790f88b44607a2a827ad7856a98`.
This fixes the four reproduced findings in the subsequent review, without
changing the referee's movement, classification or lap rules. The two-move
champion and optional third-move extension remain selected as before.

## Physical occupancy and progress

The private-lane exact fallback now stores full `(x, y, vx, vy, lap, gate)`
states, rather than packing velocities into the AI planner's limited range.
All nine physical accelerations are considered, including legal speeds beyond
that planning cap. A deterministic insertion-ordered frontier retains the
shared per-decision node budget and cache ordering. Exhaustion or an arithmetic
state that cannot be represented is unknown (`may occupy`), not proof of absence.

Every edge uses `evaluateMove` with detached progress. A rival disappears only
on a legal terminal result, not merely on crossing the start/finish line.
Ordinary laps, owed checkpoints and combined checkpoint/lap events preserve
continuing rival states. Collisions and timeouts are ignored conservatively,
so the search can add rival paths but cannot use those omissions to exclude one.
The rectangular outer bound, own planning cap and private-lane pace criteria
remain unchanged. No persisted map format is affected.

## Stop a rollout when the race stops

The rollout tracks remaining live cars and stops at the referee's last-survivor
threshold, including slot wrap and an immediately finishing candidate. The
one-car exception is preserved. A classified survivor owes zero future moves
and has terminal tier 3, even when it would be physically doomed on another
turn. Projected rival costs retain already simulated moves and retirements;
no fictitious future failure or thread-fragility step is charged after the race.
Pending candidate moves also obey mover-first timeout precedence.
The existing optional non-vanishing finish model remains a diagnostic choice;
this repair does not turn it into the standard disappearing-finish model.

## Timeout actions participate in Undo

An interactive timeout records `MoveSnapshot` before any retirement mutation.
Undo restores that player's clock, position, velocity, lap/checkpoint ledger,
classification, path history and log length. AI snapshots are traversed to the
previous human turn as before. Declined crash consent still creates no committed
action, finished races stay closed, and automatic races retain no Undo history.

## Regression and measurement boundary

`PrivateLanePhysicalTests` reproduces the full false-certificate fixture,
positive/negative speeds outside the old encoding, final/non-final crossings,
combined checkpoint events, progress-distinct rivals, the bundled Circle seam,
empty budgets and independent physical occupancy enumeration through three plies.
`RolloutTerminationTests` checks the live referee against the doomed-survivor
fixture at every slot, plus finishes, timeouts, the solo exception, optional
cost vectors and non-mutation of the live board.
`TimeoutUndoTests` executes the shared engine through the non-modal browser
adapter, covering repeated Undo, intervening AI retirement, declined consent,
completed games and automatic-mode history. Normal CI runs its standalone
adapter regression on both supported JDKs.

Policy measurement uses a disposable comparison build containing a renamed,
unchanged copy of the base scorer/private-lane helper for the control cohort.
The fixed cohort and base cohort run in the same races with mirrored slots.
The unrelated third-move experiment is disabled for both measurement cohorts;
it is not silently bundled into this correctness comparison. Neither the old
scorer copies nor the measurement dispatch exist in the shipped source.
All-course, ten-seed comparisons use the explicit `-Xmx8g` reference heap and
legacy, informed and scattered starts. Exact outcomes and completed validation
are recorded with the publication evidence; incomplete runs are not clearance.
