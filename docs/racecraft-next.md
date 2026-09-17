# Racecraft research: second batch (2026-09-17)

This extends `work/racecraft-experiments-20260916` from `bd02b56f`. It does
not change master, the champion constants, tracks, user.properties, or frozen
expectations. The research branch remains on its original round-254 champion;
results against this baseline are not comparisons with a later master policy.
Every new policy still requires selected `candidateSlots` AND explicit flags.
Nothing here is promoted, and no trained production model is bundled.

## Search arms

`diverse` implies `opportunity`. It reserves the last alternative slot for a
physically legal move whose tactical signature differs most from the champion
and retained alternatives. The other alternative slots retain the old score
ranking. The signature describes legal responses of each car on the candidate
board, own exits and exit velocity. It is only candidate allocation, not a
simultaneous-move prediction, obstruction bonus or universal safety proof.
The shortlist size and scorer-call budget are unchanged. Equivalent diversity
uses the original score/ordinal tie-break. Terminal tactics and precedence
paths still return before this hook.

`progressive` also implies `opportunity`. Each alternative has a persistent
private simulation cursor. All alternatives advance to a common cycle horizon
before their values are compared. A completed comparable stage is retained if
the next stage exhausts the shared budget or cannot obtain a policy action.
Partial stages never replace it. Terminal values stay fixed and consume no
phantom moves. Unknown route potentials do not become predicted crashes or
ties. A first-stage failure retains the champion. When `encounter` is also set,
a shared unresolved interaction in any remaining alternative permits a bounded
additional common stage; this does not create a minimax solver. Work never
uses elapsed wall time to choose actions. Diagnostics record completed stages,
rank changes, budget exhaustion, compared values and the chosen shortlist.

Examples, always writing NEW profiles:

```sh
python tracks/racecraft_next.py profile --experiments diverse \
  --out results/diverse.properties
python tracks/racecraft_next.py profile --experiments progressive \
  --out results/progressive.properties
python tracks/racecraft_next.py profile --experiments diverse,progressive,encounter \
  --rounds 2 --budget 96 --alternatives 2 --out results/search.properties
```

Profiles deliberately leave candidateSlots empty. The existing
`promotion_pair.py` supplies complementary cohorts for ordinary arm screening.
Set slots explicitly in a disposable profile for a generating-policy race.

## Place-first learning and relative features

Schema 1 and `learned` remain available unchanged. The new `lexicographic`
flag requires a schema-2 model and implies learning (not opportunity search).
It can rank the shortlist by itself or break equal forecast place/time values
when combined with `opportunity`/`progressive`.

Schema 2 retains the original 12 Java features and adds seven bounded values:
closing motion, comparable remaining-route difference, route-known indicator,
rival slot timing before our next move, change in the rival's legal responses,
rival legal-exit count, and field size. The relevant rival is selected by the
existing interaction ranking. There are no track names, seeds, player IDs or
absolute coordinates in the model. Missing route data has an explicit indicator.

The place head fits normalized final place, independently of time. The time
head learns only from action pairs with equal actual finishing places. A time
advantage cannot compensate for a worse predicted place. The maximum normalized
place residual on the explicit validation population supplies an *empirical*
radius. Only an interval contained in one rounded place category is resolved;
an out-of-range prediction or interval spanning categories abstains, rather than pretending the uncertain
places tie. Time is consulted only when both resolved predicted places match.
This interval is not a statistical confidence interval, a calibrated probability
or a guarantee on new populations. It may cause a small pilot to abstain almost
everywhere; tests of the plumbing must not be presented as a trained racecraft
gain. Zero equal-place time examples produce a zero time head, not fake labels.

```sh
python tracks/racecraft_next.py train --train results/train \
  --validation results/validation --out results/place-model.json
python tracks/racecraft_next.py evaluate --model results/place-model.json \
  --data results/untouched --out results/heldout.json
python tracks/racecraft_next.py profile --experiments lexicographic \
  --model results/place-model.json --out results/place-policy.properties
```

The new model and both heads are embedded in the output profile; there is no
mutable external model loaded during a race. Whole races, explicitly declared
families and exact course hashes must be disjoint between training and
validation, and final evaluation rejects overlap with either population.
Validation is used for the declared empirical radius, so is not a final test.

## Candidate-state collection with declared continuations

The original `racecraft_lab.py collect` remains champion-only. The new collector
accepts either champion or explicitly experimental source races. It verifies
exact replay under the generating policy and separately declares the policy
that continues each counterfactual. Source slots, experiment flags, roster and
lap count must match the supplied profile. All selected first-action alternatives
receive complete recomputed continuations; any unfinished alternative censors
the whole decision for both training heads. No crash-only sampling is used.

```sh
python tracks/racecraft_next.py collect --log results/candidate.log \
  --props results/candidate.properties --jar theoreticRacing.jar \
  --track hairpin --family open-u --state-policy experimental \
  --continuation source --moves 1,8 --heap=-Xmx8g --out results/train
# Same kind of source state, but revert to the champion AFTER the first action:
python tracks/racecraft_next.py collect --log results/candidate.log \
  --props results/candidate.properties --jar theoreticRacing.jar \
  --track hairpin --family open-u --state-policy experimental \
  --continuation champion --stride 25 --limit 20 \
  --heap=-Xmx8g --out results/champion-continuations
```

`--continuation specified` additionally requires `--continuation-jar` and
`--continuation-props`. The exact course, roster and laps must agree.
`--continuation-protocol v2` supports non-experimental historical policies;
experimental policies require v3. Datasets bind generating and continuation
JAR/profile identities separately, plus geometry, tooling, source log, runtime,
heap, selection and raw traces. Effective profiles are retained. A missing,
changed or interrupted input leaves pending diagnostics, never a successful
dataset marker. Old datasets are never overwritten. Models update between
experiments, not silently during collection. Do not combine two copies of the
same source decision with different continuations as independent examples;
the duplicate-decision guard deliberately rejects that operation.

### Classification-aware diagnostics

`v3,mover,turns,laps,finishedFirst,finishedLast;...` extends the query header and
uses actual finishing places for retired player markers. The entire ledger
is checked for consistency before mutation. Each request replaces the ledger;
a later legacy/V2 query cannot inherit it. Responses retain the V2 transition
format. `lab3` emits the shared 19 features; `audit3` emits actual search choices,
shortlists, values and budget diagnostics. These commands use the same board
validation and referee as V2; they do not define alternative racing rules.
The full ledger matters when collecting experimental states after retirements:
a sentinel alone cannot tell a place-first predictor who has already won.

## Opponent league and policy density

`racecraft_next.py league` runs complete oracle-driven races with a separately
chosen policy implementation for each car and a single authoritative referee.
All policies must use exactly the same course geometry, roster and lap rules.
Their transition responses are checked against the referee at every queried
move; a rules mismatch aborts instead of mixing incompatible games. Each car
chooses for itself. There is no coordinated opponent team and no cooperative
yielding rule.

A spec names a baseline, candidate, referee and one or more background policies.
For candidate density d, the d-1 candidate opponents stay fixed while the focal
car is replaced once with the baseline and once with the candidate. All other
opponents and the initial board stay identical. The focal rotates through every
slot by default. Densities 1,4,7 test different adoption levels in an eight-car
field; reports retain each background/density slice. Homogeneous mean place is
not used as a metric. Incomplete arms exclude their paired replacement case.

Example JSON (paths relative to the spec file, or absolute):

```json
{
  "version": 1,
  "referee": "current",
  "baseline": "current",
  "candidate": "research",
  "backgrounds": ["current", "historical"],
  "densities": [1, 4, 7],
  "policies": [
    {"name":"current", "jar":"../theoreticRacing.jar", "props":"eight-champion.properties", "protocol":"v3"},
    {"name":"research", "jar":"../theoreticRacing.jar", "props":"eight-candidate.properties", "protocol":"v3"},
    {"name":"historical", "jar":"historical/theoreticRacing.jar", "props":"eight-champion.properties", "protocol":"v2"}
  ]
}
```

Every JAR needs its matching `tracks/<track>.track` beside it. An experimental
actor's profile must select every slot to which it is assigned; for an eight-car
league normally set candidateSlots=1,2,3,4,5,6,7,8 in its own disposable profile.
Otherwise the tool rejects the mapping rather than labelling a disabled car as
experimental. The controller for each slot is selected by the league lineup,
not by changing other players into a team. Historical jars are supplied explicitly;
no arbitrary binary is downloaded or historical policy invented.

```sh
python tracks/racecraft_next.py league --spec results/league.json \
  --logs results/start-seed-a.log results/start-seed-b.log --track hairpin \
  --heap=-Xmx8g --out results/league-run
```

Generate starts separately under each requested start mode and repeat across
courses. `--focals 0,1` is a bounded diagnostic, not full slot-rotation evidence.
These are full referee-backed oracle races, not a single executable containing
all historical versions. Runtime measurements of this process-oracle harness
are not production decision latencies.

## Decision-regret report

```sh
python tracks/racecraft_next.py regret --data results/train \
  --out results/regret.json
```

The report joins each decision's actual search audit with retained complete
counterfactual outcomes. It reports the gap to the best evaluated action, whether
that action was absent from the shortlist, regret within an observed shortlist,
time regret at equal place, forecast values, exhaustion and completed horizons.
An unobserved/bypassed hook is not counted as a shortlist-generation failure.
The optimum is only among the evaluated first actions under the declared
continuation policies. Repeated-policy deployment effects and matchup failures
cannot be inferred from one-action data; use the separate league evidence.

## Validation and release boundary

Run the existing full suites, plus:

```sh
python tests/racecraft_next_regression.py --heap=-Xmx8g --out results/next-contracts
```

The new Java suite checks shortlist diversity/caps, common-horizon budget
behavior, action-order equivalence, terminal and unknown controls, model priority,
feature compatibility, and V3 ledger restoration. Python tests cover independent
place/time labels, censoring, finite schemas, split separation, evidence hashes,
profile export, regret attribution and fixed-opponent density rotations.
The real-JVM test collects actual experimental states, changes continuation
policies, trains/exports a tiny model, validates inactive and zero-budget controls,
and runs 12 complete eight-car focal-replacement races over three densities.
Its historical-interface control uses the same frozen binary in V2 mode: that
is compatibility coverage, NOT evidence of generalization to historical rivals.

The branch-specific workflow now repeats supported-JDK correctness, both real
laboratory regressions and the unchanged champion corpus on subsequent pushes.
No master deployment is attached to it. All experiment arms still require a full
mirrored place battery, runtime-tail analysis, genuinely untouched evaluations,
and integration with the intended current champion before promotion. The small
functional samples and fitted pilot are never substituted for that evidence.
