# Current-master simulation integration — 2026-09-15

## Source and scope

This integrates the two saved repair commits through `8d18dbd3cd720977dfb649e8f585fbaa80200740`
onto `094f242214b7bc5176a2a236df8bb1cac4d04b86`. The round-247 one-level soft
rollout, the newer default four-own-move real-decision tactics, all intervening
dependency updates, the referee's rules and every bundled track are preserved.
The six engine corrections are independent of the AI policy promotions:

* Exact private-lane rival frontiers retain physical velocities and progress;
  planning-speed limits and non-final lap crossings do not erase rivals.
* The mover's candidate and recursive private-lane paths retain their own lap
  and checkpoint ledger; only an actual terminal finish bypasses occupancy.
* Rollouts stop when the referee would classify the last survivor. The solo
  exception and optional cost outputs respect the same terminal boundary.
* A real scorer's legal map-dead blockade is executed, not turned into a
  retirement. Approximate-model abstention uses a physical legal continuation
  where possible; an actual selected illegal action still crashes.
* An interactive timeout creates its Undo snapshot before retiring the mover.

The original branch-stage records in `simulation-boundary-review.md` and
`simulation-followup-review.md` describe the repairs in detail. They are not
current release-clearance claims. The complete clock, both turn orders,
physical speed-13 counterexample, non-final/final crossings, proxy continuation,
last-survivor and consent/Undo controls remain regression-tested.

## A replay test is not an AI trajectory-selection test

The current two-lap Circle seed-1 race has 83 recorded moves and ends with a
crash and survivor, not a FINISH event. The repaired test replays that entire
race rather than searching it for a terminal event that need not exist.
Deliberate Circle boards independently test ordinary lap credit, owed gates,
terminal finishing and timeout-before-finish. A physical Hairpin blockade
checks crash/survivor termination without an extra turn. Standalone simulation
initialization, query-order isolation, legacy rejection and historical log
reconstruction remain covered. The same test passed on JDK 25 and 26.

## Measurement identity

The integrated decision source before corpus updates has tree
`119d2e50c6a3539349ed95082be1421acf445890`. Its strict JDK-25 JAR is
`ac8e0b77eb01b5c791435a6a444cde2dac97067862b26f73366026f5590e515e`.
No Java source, tracks or benchmark tooling changes after that measurement.

The comparison-only build contains an exact renamed copy of the current
champion and selects the policy only at actual race turns via candidateSlots.
Each policy retains its own hypothetical model; neither is told which policy
an opponent uses. These duplicate classes and dispatch instrumentation are not
part of the production source. All-control and all-corrected full races match
their standalone binaries in 12 paired cases (24 races), including two cases
where the two policies demonstrably produce different outcomes/trajectories.

Validation run `34960851599` performs 84 courses, ten seeds, two complementary
mirrors, two/eight-car fields and legacy/informed/scatter starts at explicit
-Xmx8g: 10,080 races. Every pair uses the production manifest-validating runner
and finishing-place scorer. Outcome artifacts retain profiles, completion
markers and complete logs. Full-fleet acceptance is separate from compilation
or successful transport; partial shards are not release clearance.

## Corpus changes measured before publication

The original strict JDK-25 comparison job fails five golden cases and nine of
the 24 champion scripts. These failures are retained, not waived. The new
expected data was measured from complete races using the same integrated JAR,
then all twelve goldens and all 24 scripts passed normal local JDK-25 execution.
The diagnostic survey that recorded every mismatch is not counted as a test
pass. All actual assertions run again without instrumentation.

Seven golden hashes are unchanged. Hungaroring s13, Nuerburgring s19 and
Zandvoort s45 only change trajectories. Four-car Monaco s9 changes from 551 to
543 moves. Eight-car Monaco s16 changes from 1124 moves/seven finish events/no
crash to 1089/six/one; player 5 still ranks eighth. All twelve golden finishing
orders remain unchanged. The changed counts are recorded, not described as
mere hash differences.

Nine champion scripts have measured-data updates with reasons beside their
constants. Le Mans s29 and Zandvoort s34/s44/s115 regain a finisher. Le Mans
s14/s3/s11, Hungaroring s12/s40/s4/s10/s25 and Spa s83/s27 lose a finisher.
Hungaroring s25 now records five finishers and two crashes. Remaining changed
cases retain their terminal counts but move trajectories or finishing times.
Whole-log, controller-identity, explicit decision, complete-log and physical
correctness checks remain in place. No case is skipped for differing output.

The historical Zandvoort s115 pace comparison used to sum six finishers on both
sides. With seven now finishing, summing seven against six is invalid. It now
compares the same first six finishing positions and retains a no-loss-of-
reference-finishers check. This is a historical diagnostic, not the promotion
criterion. Staged-pace terminal counts and bounds are pinned to measured
outcomes, not silently defaulted to seven finishers when cars actually crash.

Detailed old/new pin constants are in
`experiments/simulation-integration/corpus-changes.json`. Field crash counts and
summed moves remain descriptive: the acceptance criterion is each cohort's
finishing places in the same mirrored races.

## Staging boundary

This source snapshot stages the measured corpus and correctness fixes for final
strict validation. It does not authorize publication of an unfinished campaign.
The final integration record must include completed full-fleet results and the
strict final-suite outcomes before master is advanced. No test/deployment gate
or production workflow has been weakened.
