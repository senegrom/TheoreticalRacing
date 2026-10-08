# Adaptive racecraft experiments

Research branch: `work/racecraft-outcomes-opening-20260928`.
Starting revision: `1c50a5cb740c2deb9bd8bf8a588c8693e4335aae`.
No champion promotion or performance improvement is implied by these implementations.

Use a private properties file; never edit user.properties:

```properties
candidateSlots=1,3,5,7
racecraftNext=opening,adaptive-escape,followup,recovery,tactical-extension
racecraftAdaptiveNodes=2048
racecraftAdaptiveCycles=2
racecraftRecoveryTrials=9
racecraftTacticalExtraRounds=2
```

The new four flags each require candidate slots. `followup` refines the existing
`opening` experiment and requires it explicitly; followup alone is inert. The
other flags are independent of opening, rank-time and crash-rank. Zero adaptive,
recovery or extension budgets disable their respective extra work. Existing
opening budgets and its four-roster-round/CP1 phase remain unchanged. The solo
20-cell rule and computed-start policy are not modified.

## Adaptive escape certificates

The private-lane override first tries its existing approximate and exact fixed
route certificates. On failure, adaptive-escape may try a bounded AND/OR proof.
For each physical rival reply there must be enough different legal own responses;
responses can depend on the observed reply. The original two/three-escape count
is retained, and each nonterminal own response must decrease the exact solo
remaining distance. Terminal own finishes and last-survivor classification end a
branch. A rival finish rejects the certificate. Timeouts, unknown distances,
unavailable full-lap potential, exhausted work, or anything other than exactly
two live cars provide no extra permission. Retired roster entries remain in the
clock limit. Human replies are not clipped to the AI speed cap.

The node budget is shared across candidate attempts in a private-proof session.
This is a finite-horizon response certificate, not a whole-race guarantee or a
claim that the production policy will execute its witness. Existing candidate
admission, cross-model checks, pace ordering and downstream safety guards remain.

## Inherited follow-ups

The opening planner retains the particular second action that made a first
action better. A detached ledger follows the exact first-cycle actions selected
by the same rollout model and records the anticipated next decision state.
Only committing the actual planned first action installs the proposal. If a
later guard replaces that first action, no plan is installed. Repeated hint or
query evaluations do not consume or install plans.

At the next own decision an exact state match admits the inherited action to the
chooser even outside its cheap shortlist. Its old forecast is not reused: it is
compared freshly at the ordinary common horizon. It can lose that comparison.
Positions, velocities, progress, grid departure, classification, cyclic order,
clock and rule/profile identity must match. UI trail-pruning marks and other
players' stored suggestions are not physical-state identity; the suggestion is
never a proof or forced move. The opening phase still expires normally.

Pending plans belong to game state. Human Undo snapshots copy them. Detached
counterfactual scopes save/restore them. Snapshots with pending plans use `rc4`
(an `rc3` header plus a bounded per-slot action/hash field); empty-memory snapshots
remain `rc3`. The existing `cf4` complete-request digest binds either form,
including policy memory. Its replay recomputes the root policy before committing
a forced action when follow-up memory is enabled, so the control follows the
same state transitions as the real race. All normal full-suffix validation stays
required. Old captures remain tied to their original JAR and cannot be relabelled
with a different build.

## Failure-triggered candidate expansion

When every currently compared original action is a known predicted crash,
recovery evaluates additional physically legal first actions, even outside the
score window and even without a finite solo-route potential. The default budget
of nine additional trials covers the remaining legal acceleration set. Every
new forecast uses the same twelve-round suppressed-scorer model. Unknown does
not activate the trigger. Unknown results supply no crash or survival evidence;
crash-rank refinement requires an all-known-crash comparison, while a known
survivor may still replace a known crash. Ties retain the incumbent. This is not
a global widening of the chooser and does not bypass later guards.

## Endpoint-triggered extension

The initial trigger is an immediate physical finishing continuation for a live
rival at a nonterminal forecast endpoint. It does not assume that the rival
waits. If any compared action has that unresolved event, all compared actions
(including admitted inherited/recovery actions) are reforecast at the same
original horizon plus one or two complete roster rounds. Opponent selection and
policies stay the same. Terminal results remain terminal; no shorter-horizon
value is mixed into the extended selection. Unknown incumbent extensions retain
the preceding decision. This is intentionally not a general quiescence solver.

## Validation and promotion

RacecraftAdaptiveTests includes independent physical enumeration of a position
where every exit is individually contestable but conditional responses work,
a private-pace integration witness, escape-count and budget refutations,
query/memory/replay isolation, actual failure-triggered recovery, and a forecast
with an imminent finisher just beyond its horizon. Scheduling tests separately
pin fresh inherited evaluation, lexicographic outcome ordering, common horizons,
unknown handling and phase isolation. Existing racecraft CLI controls run the
combined configuration, default/empty-slot identity, capture-on/off identity and
complete counterfactual tails. These are functional tests, not promotion data.

Measure each arm independently, then combinations. Report candidate place first,
own time second and CPU cost. Use mirrored races and the lone-entrant/control
battery across legacy, informed and scattered starts and held-out tracks/seeds.
The promising all-rival-scorer arm remains a separate measured comparator. No
cooperative yielding, field-cost veto or start-placement lookahead is added.
