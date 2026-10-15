# Learning racecraft experiments

Branch: `work/racecraft-strategies-20261008`.
Reviewed champion: `71fdb12363f021ccc1036f8276041897cdbb0504`.
All additions are unpromoted, independently opt-in experiments. The current
aware policy and its exact geometry/search optimisations are retained. None of
the new arms claims the measured gains of the separate round-305/309 work.

## Configuration

Use a separate properties file, never edit `user.properties`:

```properties
candidateSlots=1,3,5,7
racecraftNext=forecast-repair,corner-memory,time-investment,event-aware,proof-number
racecraftLearningNodes=12000
racecraftLearningTrials=16
racecraftRepairAttempts=3
racecraftRepairRewind=2
racecraftEventUpgrades=1
racecraftProofMoves=7
```

Either learning budget set to zero disables these additions. With no candidate
slots, they are inactive. Computed placement, the twenty-cell solo rule, track
files and map construction are unchanged. Earlier experimental flags remain
available; measure them separately before stacking. `proof-number` does not
activate the new forecast comparison by itself.

`learning-control` runs the same new comparison without any repair, memory,
extra event upgrade or attack nomination. Use it alongside the flags-off aware
champion as an attribution control. The detached comparison uses twelve OWN
moves and the final response cycle, rather than the champion's roster-round
cutoff, and exact referee transitions. Therefore an arm's difference from the
champion is not automatically caused only by the feature named in its flag.

## Forecast repair and rewind

`LearningForecast` checkpoints a forecast logically by recording its exact
state keys. A policy-selected physical crash nominates that car's failed cheap
decision for a stronger, bounded full-policy compute. A rerun starts at the
original board, keeps the root action fixed, and recomputes EVERY intervening
car's move. If needed, refinement goes back at most two earlier decisions of
the failed car. It does not splice an escape into an unchanged opponent trace.

Refinements are selected by a fixed rule, not whichever outcome favours the
root car. The same eligibility rule covers self and rivals. At most the
configured number of refinements is performed per candidate/profile, and a
strong call's own descendants remain suppressed. A null policy result is
unknown. A failed explicit planned action is an inadmissible plan, not evidence
of a retirement. A remaining model crash is still a conditional prediction,
never a universal forced-win certificate.

The first future own action and one selected rival's first move keep the
bounded full-policy model. This is a targeted response to model failure, not
a promotion of symmetric full-policy recursion or the no-phantom-win arm.

## Cross-lap corner memory

`LearningMemory` records only real committed, legal own moves, after the Undo
snapshot is taken. A complete counterfactual race teaches only its detached
copy, as it must to reproduce the stateful policy. Hypothetical forecasts do
not teach. Repeated hints and query calls neither add nor consume experience.

The archive stores at most 64 four-action, turning, progress-making segments
per slot, with exact entry and exit states. A stable spatial sample retains
entries instead of a FIFO that would forget lap one before lap two starts.
Identical entries/action sequences retain the earliest observed lap. A segment
crossing the start/finish line, ending in classification or changing grid
entitlement is not recorded. Recent one-move observations are separately
bounded to four per slot.

Retrieval initially requires exact own position, velocity, next gate and grid
entitlement, from an EARLIER lap. Stored paths are proposals, not instructions
or traffic guarantees. Both ordinary and memory-assisted profiles receive
matched reactive forecasts; the latter rechecks each recorded action against
the actual projected board. Remaining race distance is recomputed for today's
lap. A useful concrete suffix uses the existing commit-only, exact-board plan
memory and remains subject to subsequent guards.

## One-move time investments

`TimeInvestment` activates only with two live cars and finite mapped distances
no greater than fourteen moves. It nominates an immediate route-denial action
or a backward-planned interception whose own mapped cost is at most one move
above the solo minimum. The existing ambush generator's zero-debt mode stays
unchanged. Incomplete rival graph layers do not establish mandatory cells.

These are mapped, model-conditional proposals. The bounded speed map is NOT
advertised as a universal lower bound on an unrestricted human opponent.
No opponent-delay bonus is used. Fresh forecasts choose by our place, then
our own total time. A one-turn expenditure is permitted, not automatically
rewarded. Actual finishing precedence remains authoritative.

## Event-triggered stronger own decisions

`event-aware` retains the first stronger own continuation and spends a bounded
additional allowance at later choice points. The cheap trigger requires more
than one physical in-domain legal move and either a unique minimum-time
continuation or a landing competing with a rival's next acceleration band.
A physically forced move does not consume an extra upgrade. Triggers are not
proofs of danger and add no avoidance penalty.

Compare against `learning-control`, with equal node/trial settings, and report
both total strong calls and where they were spent. Default one extra event call
is a starting experimental setting, not a tuned optimum. The race audit logs
forecast, refinement, event, memory and nomination counts.

## Proof-number tactics

`ProofNumberSearch` is a best-first AND/OR tree, not another fixed-depth
uniform expansion. Own nodes need one winning action; rival nodes cover ALL
nine physical accelerations, including out-of-AI-domain replies and illegal
moves that retire the rival. The complete expansion's transition allowance is
reserved before any child is admitted, so an omitted response cannot become
a proof. The shared progress-based timeout transition remains authoritative.

The existing shorter tactics run first. The fallback searches win-by-deadline
goals from five through the configured own-move cap, advancing a deadline only
when the preceding bounded goal is refuted. Refuting that goal does not prove
the whole position lost; exhausting work proves neither win nor loss.

A completed result retains up to 512 clock-keyed own responses. Commitment
installs the strategy; subsequent matching states retrieve its response.
Immediate shorter wins and the outer solo rule retain precedence. An independent
verifier in the test suite follows only recorded own actions and enumerates
all rival replies. Strategy tables are internal policy state, not externally
authenticated proof objects.

## Snapshot and replay contract

`rc7` adds bounded per-slot corner archives, recent committed observations and
proof responses to the complete snapshot. Old rc3--rc6 snapshots remain
readable. Settings, executable and input manifests remain pinned; changing the
policy build requires recapturing performance data. The cf4 request digest
binds the complete learning state, not merely the physical positions.

Undo, race reset and detached scopes preserve or reset learning state at the
same point as follow-up memory. Java and Python reject malformed kinematics,
discontinuous observation trails, invalid proof depths and noncanonical tables.
Full control continuations must still match the captured race suffix exactly.

## Competitive opponent league (offline)

`tools/racecraft_league.py` runs the new `league1` engine protocol, with
complete referee continuations and reacting per-actor policies. The initial
pool supports the current champion, suppressed scorer, pure solo-pace variant,
and bounded genomes `g_SPEED_RADIUS_HORIZON`. It does not yet run mixed historical
JARs inside one game; historical executable adapters are not claimed.

A genome changes the conditions under which its actor compares a few own
continuations. Its fitness is its OWN mean finishing place, then own time,
using exact rational comparison. Opponent profile names are not exposed to the
actor. No reward is given for hurting a named candidate, self-sacrifice,
cooperation or field-wide crashes. Every slot rotation is measured.

The runner first verifies an all-champion full-trace continuation against each
captured generating race. It then produces cross-play, searches counterpolicies
against the current candidate and improves the candidate against the retained
pool. A separate held-out capture is evaluated only after selection. Cycles
are reported only for two-live-car cross-play. Incomplete tails never enter
fitness, and no profile is automatically installed or promoted.

Example, from an existing capture made with this exact build:

```sh
python3 tools/racecraft_league.py \
  --capture /tmp/racing-capture --out /tmp/racing-league \
  --pool champion,scorer,pace --cases 2 --generations 1 --mutations 4
```

Use a NEW output directory. The default work bounds are intentionally finite;
start with `--generations 0 --cases 1 --pool champion,scorer` for a smoke check.
The manifest records executable, configuration, geometry, Java runtime, tools,
seed, every request and complete trace. Output is research evidence, not a
replacement for mirrored fleet and lone-entrant promotion batteries.

## Validation

`LearningRacecraftTests` covers a repaired phantom rival retirement, bounded
rewind, committed corner learning and later-lap use, Undo and rc7 round trips,
one-move-debt interception, event activation, independent proof verification
and deterministic league continuations. Python tests cover malformed learning
memory, complete-request binding, genome validity and own-place-first fitness.

`tests/racecraft_learning_cli.py` compares default identity against pinned
master, independent arms, combination, no-slot and zero-budget controls,
audit-on/off identity, complete cf4 control suffixes with memory, and the league
runner end to end. Golden races, champion pins and browser parity remain separate.
Only executed results belong in validation.json. No fleet gain is asserted by
constructed witnesses, successful compilation or functional race controls.
