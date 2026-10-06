# Traffic opportunities (research only)

Based on master `82d259a217c23991cec7adc164c81f48e575c88c`, integrated into
`work/racecraft-outcomes-opening-20260928`. All prior branch experiments remain.
No policy is promoted; defaults, the 20-cell solo rule, computed starts, maps,
tracks and user.properties are unchanged. Use a private properties file:

```properties
candidateSlots=1,3,5,7
racecraftNext=denial,manoeuvre,checkpoint-traffic,decision-endpoint,staged-order,short-transitions
racecraftManoeuvreNodes=192
racecraftManoeuvreDepth=4
```

Every flag is independent. Zero manoeuvre nodes is inert. New arms run only at
real traffic decisions, not nested chooser/scorer calls or the solo path.

## Denial

Near the finish (at most 12 own solo moves remaining), propose one pace-neutral
landing that increases the next live rival's best immediately legal reply plus
post-transition solo distance. Cyclic move order and all existing bodies count.
Finishes are terminal. Unpriced replies and forced-crash positions are not
invented as numerical delay certificates. No blocking bonus is applied: the
nomination competes in the current all-rival chooser. Round 292b's pace nominee
and conditional authority are retained exactly.

## Multi-move manoeuvres

A nominal suppressed-scorer trajectory supplies occupancy at own decision
points. A bounded graph retains position, velocity, lap/gate progress, grid
entitlement, own move index and first action. It generates at most two distinct
first-action proposals, up to four actual accelerations long. There is no
instantaneous stopping or artificial wait. Completed paths are proposals only,
not certificates of optimality or safety; no complete path means no proposal.

Each proposal and the incumbent are then evaluated independently in the SAME
reactive all-car suppressed-scorer model for 12 own moves, ending before the
next own decision. These forecasts use the detached referee and exact per-car
grid entitlement (rather than assuming the nominal occupancy schedule remains
valid). This is a deliberately explicit separate proposal-validation model,
not a reuse of a shorter native-chooser score. Unknown/illegal forced prefixes
do not win a comparison. Human-roster and unavailable full-lap-potential cases
abstain rather than invent a human policy. Extra work is bounded by graph nodes,
two new proposals, one inherited suffix and one incumbent forecast.

The winning suffix is stored ONLY if its first action is actually committed.
At the next exact matching board it is re-evaluated against fresh alternatives;
it is never blindly executed. Traffic entries carry up to three future actions
and use rc5 snapshot headers with `M_E+N+NE~<physical-state-key>` per slot. Old
opening entries retain rc4. Empty memory remains rc3. The cf4 request digest
binds the complete memory. Undo and detached scopes copy/restore immutable
entries. Queries do not install/consume committed memory. Guards and later pace
overrides remain authoritative and replacement invalidates the pending suffix.

## Checkpoint traffic tie-break

Retain every existing eligibility test and collect the equal minimum solo
plateau. Compare the incumbent and up to two equal-best alternatives in the
all-rival joint model. No non-touching move, deferred checkpoint, worse solo
value or placement lookahead is introduced. Actual finishes retain precedence.

## Decision-aligned endpoint

Only chooser comparisons complete the last missing roster prefix, stopping
immediately before the mover's next action. Own move count is unchanged. This
adds at most n-1 live rival actions, not another own-move layer. Proof search
horizons and real cyclic advantage are unchanged. All candidates use the same
phase; the existing event-triggered extension can still add common full rounds.

## Staged ordering

Staged pace alternatives still require the incumbent improvement and existing
admission checks. Detailed outcomes retain elapsed own moves. Among improving
alternatives compare place/time before the heuristic score concession. Unknown
incumbent or alternative time is not accepted as favourable evidence.

## Short transitions

The scorer's top-level one-cycle projection removes a finisher at its actual
turn and never reinstalls its old or post-finish body. Ordinary lap crossings
and legal map-dead positions remain live. When its preference search abstains,
a physical legal reply is sought before calling the car stuck. Nested reference
projections remain untouched in this first isolated arm.

## Evidence

Constructed behavioural tests and complete-race controls are functional checks,
not place-gain measurements. Run each arm alone, then combinations against the
current champion using mirrored random/computed/scattered fields and held-out
seeds plus the lone-candidate/control check. Report own place, own time and CPU;
field crashes and summed time do not veto a policy. See validation.json for
executed results, revisions and explicit outstanding work.
