# Private-lane and lifecycle correctness follow-up (2026-09-12)

Initial review base: `745798f613406790f88b44607a2a827ad7856a98`.
Integrated onto `9668703dc1489383bde78f2460476e9f6daa1da0`; the subsequent
round-238 funnel deletion and all campaign notes are preserved.
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

## Golden trajectory audit

The three changed golden trajectories are isolated to the rollout correction:
private-lane-only builds reproduce each original hash; rollout-only builds
reproduce each fixed hash. Original and fixed profiles, full logs and executable
audit scripts accompany the review evidence. `experiments/lifecycle/golden-audit.json`
records both normalized and raw-log hashes plus the first differing move.

| Fixture | First different move | Turns before -> after | Finishing order / crashes |
| --- | --- | --- | --- |
| Monaco, seed 9, four cars | 539, P3: W -> NW | 551 -> 549 | unchanged / 0 |
| Monaco, seed 16, eight cars | 1117, P5: SW -> NONE | 1124 -> 1124 | unchanged / 0 |
| Interlagos, seed 10, eight cars | 927, P7: S -> SW | 999 -> 999 | unchanged / 0 |

Only these three measured golden hashes and the one changed turn count are
re-frozen, with the reason beside each fixture. The other nine goldens and all
24 champion regression expectations stay unchanged. This is not a blanket
regeneration of the corpus or a change to the measurement's success criteria.
The new physical and lifecycle regressions also reject the unchanged base
production code, including the actual Circle lap-seam assertion, not merely an
uninitialized test fixture. Local source-isolation runs are supplementary JDK 21;
final supported-JDK checks validate the committed expectations independently.

## Integration boundary

The first fixes and golden-source isolation used `745798f`. Master subsequently
advanced to `9668703`, changing only the campaign ledger and removing the old
funnel guard from `RaceAi`. This integration keeps that deletion. The final
supported-JDK suites, golden corpus and comparison fleets use the combined
source against the newer base. Earlier partial or complete fleet outputs are
not substituted for those integration results.

## Completed integrated validation

The integrated source passed JDK 25/26 Java contracts and the full JDK 25
golden, champion, Python, real-CLI and native-browser parity suites.
The same-race comparisons completed 5,040 races (40,320 car-races) over
84 courses, seeds 1-10, all three start modes and mirrored eight-car fields.
The base is `9668703`; both measurement cohorts have the third-move
experiment disabled. Reports and provenance are retained in
`experiments/lifecycle/integrated-fleet/`. Crashes are descriptive, not a veto.
Fleet workflow: 34705252476. Release validation: 34705411385.
The earlier temporary browser step lacked CairoSVG; this validation uses
the repository-declared icon dependencies and reruns the complete suites.
