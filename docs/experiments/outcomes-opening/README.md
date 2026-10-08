# Outcome accounting, opening play, and counterfactual place loss

Branch: `work/racecraft-outcomes-opening-20260928`.
Integrated master: `b54e9bb05f91c0011e8d5e82178d1d13f3c1b494` (2026-10-02).
The original September 28 baseline and validation are historical, not evidence
for the repaired implementation. No experiment is promoted by this branch.

## Owner rules and scope

Every car pursues its own finishing place first and its own time second.
Forcing rival retirements is legitimate; field crashes or summed moves are not
independent vetoes. The canonical 20-cell solo boundary is unchanged.

The owner's October 2 computed-start rule explicitly rejects the old
`start-ties` multiplayer placement replay. That flag is now refused rather
than silently ignored; the replay implementation and placement hook are removed.
`StartPlacement.java` is the integrated master's implementation. Round 299's
separate pending start-rule work is not imported or re-screened here.

Common correctness fixes are independent of experimental flags: solo precedence
before tactics, current nonterminal-crossing behavior, modern grid-world cache
keys, and progress-based timeout classification. The standalone experimental
arms do not claim credit for those baseline changes.

## Opt-in controls

Use a separate profile; do not edit `user.properties`:

```properties
candidateSlots=1,3,5,7
racecraftNext=crash-rank,rank-time,opening
racecraftOpeningRounds=6
racecraftOpeningTrials=18
```

Each arm requires both its flag and the deciding car's candidate slot. Empty
flags or slots keep the repaired common control. `opening` is active only in
the first four roster rounds, before the mover passes its first checkpoint;
zero opening trials disable it completely. Capture settings do not select a
policy. The learned opponent model is not included.

## Crash classification and own time

`RacecraftOutcome` distinguishes unknown, running, finished, survivor-classified,
crashed and timed-out outcomes. It carries place information, own moves already
taken and remaining route moves. Rollout ranks are relative to the live cohort
at entry; already settled places are constant across that decision's alternatives.

An ordinary retirement has `ahead = currentLive + forecastFinishers - 1`.
Earlier crashes improve that rank; rivals merely finishing do not. If every
candidate actually considered by the chooser is a known forecast crash,
`crash-rank` selects the better classification, then own time. Unknown forecasts
are never labelled crashes; this refinement does not prefer a crash over a
surviving forecast or search beyond the existing root shortlist.

`rank-time` compares elapsed own moves plus remaining moves. A finish after one
own move and a finish after five no longer both carry zero time. Explicit
predicates distinguish completion, known survival and unavailable information.
The ranked rescue path checks each admitted action in both existing confirmation
worlds and uses `ConfirmedMoves` to select by place/time, not the first slower
survivor. Incomplete confirmations cannot qualify. The ordinary control retains
its prior rescue policy for isolated measurement.

A finite-horizon model prediction is not a forced outcome or a universal safety
certificate. Existing downstream pace and danger guards remain authoritative.

## One timeout rule across real and hypothetical games

`RaceTimeout` supplies the side-effect-free progress ordering used by the live
referee, projected rollouts, the bounded duel solver and offline replay:
fewer gate events owed, fewer moves to the next gate (unknown last), then the
actual cyclic next-mover order. The original roster determines the race limit,
including already retired slots.

Reaching the limit ends the race for all remaining cars atomically. Replay
uses the same worst-first timeout log order and survivor classification as the
live referee; it does not simulate another racing move. A trailing car cannot
be awarded a tactical win merely because the opponent's turn hits the limit.
The older deep solver lacks projected progress in its search state and therefore
abstains at a timeout rather than fabricating a certificate.

Timeout classification is distinct from a crash. The work budget is distinct
from both: an unfinished replay remains unlabelled and never partially applies
an atomic timeout event.

## Opening search without compass-prefix bias

The opening planner retains the normal root shortlist. Each root's baseline
forecast supplies legal second actions from that root's actual projected board,
after intervening rivals have moved. These follow-ups are ordered by continuation
value after collecting their gate/lap events, with momentum and limited diversity
on value ties. Enum order is only a final deterministic tie-break, not the rule
that determines which half of acceleration space is omitted.

`OpeningPlans` allocates the bounded forecast budget round-robin across the roots.
Illegal second actions are not offered by the baseline frontier. The common
horizon and the default 18-trial budget include baseline forecasts. Only the
first action is returned; the next real decision replans from observed state.
A forecast setup does not promise that the same follow-up will be executed later.

## Interaction selection stays offline

The influence diagnostic remains shadow-only. Direct contact does not capture
all strategically relevant cars: another car can change a blocker, or a distant
finisher can change place. Conservative acceleration envelopes and two-hop
closure may include most of a pack, leaving little computation to save. Giving
different root actions different-quality opponent models can also manufacture
an apparent advantage.

The diagnostic records unclipped pre/post-action occupancy envelopes and possible
two-hop dependencies. It does not establish threat probabilities, model a coalition,
penalize proximity, direct a car to yield, prune rivals or change the solo rule.
Any future live selector must be compared against the measured all-nearby/all-rival
scorer alternatives at a fixed compute budget and on held-out tracks.

## Counterfactual corpus: cf4 acceptance boundary

```sh
sh build_main.sh
python3 tools/racecraft_corpus.py capture --track hairpin --seed 1 \
  --props /path/to/research.properties --heap=-Xmx8g \
  --limit 100 --every 1 --out /tmp/racecraft-capture
python3 tools/racecraft_corpus.py replay --capture /tmp/racecraft-capture \
  --offset 1 --cases 3 --max-moves 10000 --out /tmp/racecraft-tails
```

Outputs must use new directories. Implicit JVM option environment variables are
refused. The schema-2 capture manifest binds the JAR, runtime version, explicit
heap, track, profile, seed, all relevant corpus/helper scripts, exact-potential
mode, captured states and original race log. Under-provisioned maps are refused.

An `rc3` snapshot includes the complete decision-relevant board: positions,
velocities, player identities, exact left-grid flags, laps/checkpoints, cyclic
slot, race clock and existing finish/retirement places. Capture also records the
referee-legal first-action set within the AI planning domain, along with scorer,
chooser, opening and final-action diagnostics.

The new `cf4` response has schema 4 and echoes the SHA-256 of the entire request,
including its dynamic snapshot, observed action and work bound. It must contain
exactly every captured legal first action plus the observed control, once each.
Old cf3 answers and old capture manifests are not accepted; capture again.

`racecraft_validation.py` independently checks transition structure, acceleration,
clock and cyclic order, retirement/finish ranks, terminal status, own move count,
final board consistency, legal-action coverage and full request identity. Trace
checksums alone are not acceptance evidence. The pinned Java referee remains the
authority for geometry and gate crossings; Python does not reimplement geometry.

For EVERY completed case, not merely turn-zero fixtures, the replayed control
must reproduce the entire original race-log suffix and final classification.
A matching first action is insufficient. Missing, inconsistent or truncated
answers never produce a labelled case or a `COMPLETE` marker. Counterfactual
labels are conditional on the pinned continuation policy, not fleet evidence or
game-theoretic guarantees.

## Regression witnesses and evaluation

`RacecraftFixTests` covers the previously false timeout certificate and live
referee agreement; actual chooser selection that salvages a better crash place;
confirmed-action selection by place/time; rotated unique opening setups under a
small budget; mid-race prior classifications, checkpoint/finish and exact grid
entitlement; phase and solo-control isolation. `RacecraftNextTests` retains
outcome, state-restoration and baseline contracts and rejects `start-ties`.

Python acceptance tests use complete coherent traces and attack request binding,
missing alternatives, impossible places/counts/status, malformed traces, final
states and later control-tail divergence. The complete-race CLI checks default,
no-slots, no-flags, zero-opening and audit identity against the integrated master,
and replays multiple mid-race decisions through the mandatory cf4 validator.

Completed runs and remaining limitations belong in `validation.json`; passing
unit tests is not a fleet promotion. Repaired variants need fresh independent
and combined screens, mirrored slots, all three start modes, held-out tracks,
compute measurements and lone-candidate checks. Old round-298 numbers do not
measure these repairs. No place gain or speedup is claimed here.
