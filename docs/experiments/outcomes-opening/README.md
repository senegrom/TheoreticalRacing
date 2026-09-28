# Outcome accounting, opening play, and counterfactual place loss

Research branch: `work/racecraft-outcomes-opening-20260928`.
Pinned starting revision: `955001104bbe315cf9b82a1cd2dfb447beddd211`.

This implements the owner's requested ideas 1, 2, 4 and 6. Idea 3 is evaluated
critically below and supplied as an offline diagnostic, not a driving change.
The unrequested learned opponent model (idea 5) is not implemented. None of
these policies is promoted. Existing queued master arms are not imported by
implication: rounds 291/293/294/295 have their own evidence.

## Controls

Use a new properties file, never change `user.properties` for experiments:

```properties
candidateSlots=1,3,5,7
racecraftNext=crash-rank,rank-time,opening,start-ties
racecraftOpeningRounds=6
racecraftOpeningTrials=18
```

Each flag is independent and requires the deciding car's candidate slot.
Empty flags or empty slots retain the control. Opening trials set to zero
completely disables that arm. `start-ties` changes placement only, not the
subsequent driving policy. Audit options are separate and do not select an arm.

## 1. Resolve different crash classifications

`RacecraftOutcome` distinguishes `UNKNOWN`, `RUNNING`, `FINISHED`, `CLASSIFIED`
and `CRASHED`. It carries the number ahead, own moves already taken, and route
moves still owed. Within a forecast the number ahead is relative to the cohort
live on entry; previously settled places are constant across alternatives.

At retirement, `ahead = currentLive + forecastFinishers - 1`. Earlier retirements
improve the mover's result; a rival merely finishing does not. The simulator
records that information without changing the negative survival sentinel used
by existing guards.

When **every action actually considered by the chooser is a known predicted
crash**, `crash-rank` selects by the mover's classification, then own time. It
does not treat unknown as a crash, claim a model prediction is forced, prefer
a crash over a surviving line, or claim to consider actions outside the shortlist.
Later pace and danger guards retain their established authority.

## 2. Place before speed, and elapsed time before a misleading zero

`rank-time` changes the scalar adapter for simulated comparisons to use actual
own moves plus remaining moves. Finishes one and five own moves away no longer
both read as zero. Finishing status and known survival have explicit predicates;
remaining-distance triggers retain their original units.

In the true-confirm rescue, slower-first can no longer select a worse-place
candidate simply because it passes first. All admitted alternatives are tested
through the existing cheap/deep and faithful confirmation legs. Selection
compares completed faithful outcomes by place/time; unknown confirmations are
not successes. Speed only orders exact value ties. This can cost additional
compute and requires measurement; it is not declared free or faster.

A `RUNNING` outcome still contains a finite-horizon forecast, not a certified
final place. This does not solve uncertainty beyond the horizon or replace
historical proxy models with a full game-theoretic solver.

## 3. Why not replace nearest-three with an interaction-selected three yet?

The attractive intuition is to spend accurate policy calls on relevant cars.
But a car can matter by occupying our possible landing, changing another car's
action that can affect it, or changing eventual classification without ever
approaching us. A short direct-contact graph cannot certify all three. Taking
the union across possible accelerations quickly includes most of a dense pack;
geometry-clipping and refreshing then add work without necessarily reducing
policy calls.

A second trap: different root actions must not receive incomparable model quality
because each selects its own convenient rival subset. A per-action cheap forecast
can make a candidate appear superior by predicting a different opponent badly.
Consistent union membership reduces that problem but further reduces possible
savings. Any cache must carry the relevant world, model, depth, slot and rules.

The newly measured all-nearby-scorer arm is therefore the appropriate comparison
baseline, not the old fixed-three arm alone. The ledger's reported 1.11x CPU
makes the overhead hurdle meaningful. No avoidance penalty, yielding rule,
worst-case coalition, or change to the canonical 20-cell solo gate is warranted.

The corpus tool implements a **shadow-only diagnostic**. It records potential
pre/post-action occupancy overlap at up to three own moves using conservative
unclipped acceleration envelopes, plus two-hop possible indirect blockers. It
uses velocities and adjacent cyclic move counts, not intersections of drawn
paths. Unclipped envelopes overinclude: these are neither probabilities nor
certified interaction-free separations. Two hops also do not capture every
possible longer dependency chain.

Next evaluation: compare direct/two-hop graph sizes with the fixed nearest set
and observed decision-sensitive opponents on the same counterfactual states.
Only then test live selection at a fixed policy-call budget against all-nearby
scorers, with held-out track families and the lone-entrant battery. Until it
earns places per compute, keep this diagnostic out of the driving path.

## 4. Two independent opening experiments

### Driving from a completed grid

`opening` is limited to the first four roster rounds and the mover before CP1.
It keeps the normal top-three roots. Over a common six-round horizon it evaluates
normal continuation plus explicit second actions, round-robin across roots,
with a maximum of 18 forecasts including the baseline by default. An illegal
forced second action is an unavailable plan, not a crash used to manufacture
a better classification. Completed results survive the trial-budget boundary;
unexamined branches remain unexamined.

Forecasts use the existing recursion-suppressed scorer policy and cyclic order.
Only the first action is returned. The next real turn replans from the observed
board: no hidden commitment or cooperation. Original pace overrides and later
guards remain in charge downstream. Audits distinguish the scorer, chooser,
opening proposal and final returned action.

This is bounded, not an exhaustive search over all roots or rival responses.
It does not establish that the proposed follow-up will actually be selected
later. The full real-policy counterfactual tail separately tests whether the
first-action proposal eventually earns places.

### Starting-cell choice

`start-ties` runs only for the final AI placer, with an AI-only stationary grid
and every other position observed. It compares the seeded stock choice and at
most three other **equally solo-optimal** cells supplied by the existing start
analysis, using three cyclic roster rounds of scorer-driven continuation.
Strict improvement changes the cell; exact ties retain the seeded stock choice.
Earlier placers and human-roster starts retain the existing policy.

No later placement, hidden seed result or human intention is guessed. The start
map, occupancy constraints and RNG stream are unchanged. Placement and driving
flags are independently measurable. This initial restriction trades scope for
a fully observed experiment.

## 6. Counterfactual corpus

Build on JDK 25 or later and select an AI-only profile:

```sh
sh build_main.sh
python3 tools/racecraft_corpus.py capture --track hairpin --seed 1 \
  --props /path/to/research.properties --heap=-Xmx8g \
  --limit 100 --every 1 --out /tmp/racecraft-capture
python3 tools/racecraft_corpus.py replay --capture /tmp/racecraft-capture \
  --cases 10 --max-moves 10000 --out /tmp/racecraft-tails
```

All output directories must be new. Caller-owned settings and track files are
not modified. Unset implicit JVM option environment variables. The manifest
binds the JAR, runtime version, explicit heap, track, profile, seed, tool, states,
original log and exact-potential mode. An under-provisioned map build is rejected
using the repository's existing potential-status check.

An `rc3` snapshot carries the turn, cyclic slot, lap count, existing finish and
retirement counters, identities/kinds, every car's position/velocity, settled
place, full lap/gate ledger and explicit `leftGrid` flag. Unlike V2, grid legality
is not guessed. This is complete for decision/rule replay; UI history lists are
not serialized because they are not policy inputs. Trace markers are carried,
but replay does not promise identical rendered history. V2 is unchanged.

Each `cf3` case recomputes and verifies the captured actual action, then runs
**every physically legal first action within the AI planning domain**, plus the
actual control even if illegal, through fresh real-policy continuation to
completion or an explicit work limit. Players are detached. The transition
logic is independently compared with actual `RaceGame.commitMove`. No heuristic
removes a car because a route map dislikes it. Classification, terminal landing
exceptions, checkpoints, grid state and turn limits follow the referee.
No continuation policy for human players is invented.

Every result stores its full transition trace and checksum. Truncated/unknown
tails are unlabelled; any incomplete alternative prevents claiming a best action.
No `COMPLETE` marker is written for an incomplete corpus. Input identity must
match capture throughout replay. An actual-action mismatch is rejected, not
silently converted into a training example.

The report compares own place first and own moves second. Diagnoses distinguish
shortlist exclusion, downstream replacement and pre-chooser/unobserved decisions.
When evidence cannot separate model, horizon and value-ranking errors it reports
a combined category rather than inventing causality. These are conditional
outcomes, not universal wins, independent statistical observations or promotion
evidence. Whole-race control checks compare every action and transition with
the original captured race, not just its first move.

## Validation and promotion

`RacecraftNextTests` covers typed ordering, simulated crash order, finish time,
opening budgets, control gating, placement isolation, snapshot validation,
bounded tails and independent live-referee replay. Python tests cover labels,
trace integrity, incomplete cases and the shadow diagnostic. The CLI regression
compares complete default/control/candidate races and actual capture/replay.

The branch workflow also runs the existing goldens and every champion pin without
rewriting expectations. Consult `validation.json` for completed, source-pinned
results: configuring a workflow is not a claim that its jobs passed.

Before promotion: each independent flag and their combination need two-, four-
and eight-car fields, random/computed/scattered starts, mirrored slots, held-out
seeds/track families, and a lone candidate rotated through every seat. Record
activation, proposed/executed switches and compute cost. Compare opening driving
on fixed grids before attributing gains to placement. Balanced cohort differences
are not lone-entrant effects. Field moves and crashes remain descriptive and
never independently veto a car gaining places.
