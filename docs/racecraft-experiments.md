# Traffic racecraft laboratory (research branch, 2026-09-16)

Base: `614fef76564b3e6d4fcdd78a7d378483c5fa61f0` (round-255 ledger;
round-254 champion). Four proposals are executable here. **None is promoted.**
No golden expectations, tracks, saved user settings or champion constants change.
Finishing place is primary; own time breaks ties. No field-slowdown reward,
cooperation, yielding rule, crash-count acceptance gate or opponent coalition.

## Activation and isolation

Both `candidateSlots` and `racecraft.experiments` are required. With either
unset, all cars follow the existing champion. The flags are independent:

| Flag | Experiment |
| --- | --- |
| `interaction` | Spend the existing faithful-rival cap on direct/indirect interactions rather than just nearest cars. |
| `refresh` | Interaction ranking, refreshed at each projected round rather than fixed at rollout start. Implies `interaction`. |
| `opportunity` | Compare the champion with a small shortlist even when the ordinary chosen move survives. |
| `encounter` | Extend unresolved landing contests at the ordinary rollout cutoff, within a deterministic extra-work budget. Also extends opportunity forecasts. |
| `learned` | Use an explicitly supplied trained linear comparative ranker. Without `opportunity`, rank the shortlist directly; with it, break equal predicted place/time ties. |

Only a selected **real focal decision** activates experiments. A labelled rival
installed temporarily by a nested scorer cannot activate its experiments inside
a control car's forecast. Experiment context and live player/clock/frame state
are restored on return or exception. Existing proven tactics, terminal finishes,
checkpoint precedence and survival fallbacks return before opportunity ranking.
All-car faithful forecasts retain their all-car membership; the interaction
experiment changes only capped selections, not the cap itself.

Optional profile controls:

```
racecraft.rounds=2
racecraft.extraRounds=1
racecraft.policyBudget=96
racecraft.extensionBudget=64
racecraft.alternatives=2
racecraft.audit=false
```

`rounds` is the opportunity forecast's base horizon (1–4 complete cycles starting
after the candidate). `extraRounds` is 0–3. `policyBudget` bounds total additional
scorer calls across **all** opportunity alternatives per real decision (0–512).
`extensionBudget` independently bounds additional live move slots in existing
rollouts (0–512). No branch is selected by elapsed wall time. The unchanged
champion's internal search costs are not part of these additional-call budgets.
Audit mode prints `RACECRAFT` lines to stderr: focal slot, selected move,
attention-graph selections, extension rounds, opportunity-hook entries, switches,
forecast policy calls and elapsed nanoseconds. Timing is diagnostic only.

## 1. Interaction-ranked faithful rivals

`RacecraftTraffic` propagates independent physical legal landing sets for two
own moves per car, in real cyclic slot order. Cars that have not moved retain
their old cell; movers' arrivals are compared with the others' holdings at that
slot. Lap and gate progress travel with each state. Actual finishes vanish;
ordinary laps do not. Opponent speeds are not clipped to the AI's map indices.

Shared landings define direct edges. Neighbours of direct competitors provide
indirect-influence priority. The cap is filled by direct edge weight, indirect
weight, distance and slot number, deterministically. Non-interacting cars only
fill remaining attention slots inside the caller's old radius. Every unselected
car remains present and follows the existing inexpensive model.

These independent reachable sets **ignore mutual occupancy** and are not a
joint-game proof. Their role is allocation of prediction effort, not a danger
penalty, move veto, or licence to remove a third party. A 2,048-transition graph
budget bounds work; an incomplete graph cannot claim independence.

## 2. Opportunity search and its offline counterfactual counterpart

At the end of the ordinary scored path, the selected car considers the champion
and up to `alternatives` physically legal moves, ranked by the existing candidate
scores. It first requires an actual short-range interaction. Predictions start
from a detached board **after each candidate**, so the rivals respond to that
candidate's obstruction, not to a cached pre-candidate world.

All cars in these small forecasts use the existing recursion-guarded scorer.
This is not an unbounded call to each car's full real decision tree. The same
referee transition handles checkpoint credit, finishes, crashes, mover-first
timeouts and last-survivor classification. A legal map-dead blockade remains a
real move. An unavailable policy action, missing comparable route potential, or
exhausted comparison budget causes abstention: keep the champion.

Terminal classifications are exact for the simulated sequence. Nonterminal
place is an **estimate**, ordering each car's own remaining potential with slot
order to resolve simultaneous-arrival estimates; own remaining time is secondary.
An unreachable solo map is unknown, not an automatic crash. Multi-lap leaves
without a complete remaining-route potential abstain rather than compare
incommensurate next-gate distances. Query sentinel markers without a consistent
classification ledger also cannot be used for opportunity place predictions.

For stronger evidence, `racecraft_lab.py collect` uses the existing V2 Java
oracle to play **complete counterfactual races** under a frozen champion. It
first verifies exact replay of the source log. Each legal alternative then gets
its own first move, followed by recomputed champion decisions through terminal
classification. Source selection is a deterministic stride or explicit move
indices, not a crash-only filter. No-legal-alternative states are retained.

The collector retains the source log/profile/course, complete action traces,
per-car classifications, own committed moves, Java version, explicit heap, and
hashes of the JAR, course, profile and Python tooling. A dataset is published only
after unchanged-input verification. Interrupted or failed collection leaves
`*.pending.*` diagnostics, not an acceptable dataset. A bounded continuation
that does not finish is censored; **the whole decision is excluded from training
if any alternative is censored**, rather than selecting only easy outcomes.

## 3. Bounded encounter extensions

An outer rollout can extend its cutoff only while the focal car still has a
shared physical landing interaction. It stops on resolution, actual terminal
classification, the extra-round limit or the remaining per-decision slot budget.
Quiet open running receives no extension. The opportunity forecast uses the
same encounter test and its separate shared prediction budget. Budget exhaustion
never produces a universal win certificate. This implements the small selective
rollout experiment, **not** a new adversarial multi-player minimax solver.

## 4. Trainable comparative ranker

The `lab2` diagnostic command shares the exact V2 board validation and emits
12 bounded Java features for each legal candidate. The Python collector consumes
those values, avoiding a second implementation of the feature extraction:

```
speed_inf,speed_squared,acceleration,legal_exits,map_alive,remaining_events,
solo_turns,direct_rivals,indirect_rivals,contested_exits,nearest_distance,terminal
```

There are no track names, seed IDs, fixture IDs, player IDs or absolute positions
in the learned vector. Track/race/family identities remain metadata for splitting.
Deterministic batch pairwise logistic training learns which action has the lower
lexicographic `(final place, own future moves)` outcome. Equal labels add no
pair. The linear score is lower-is-better. A margin applies relative to the
champion's score, not successive arbitrary shortlist neighbours.

Training requires explicit validation data. Whole races, declared geometry
families **and exact course hashes** must be disjoint. Evaluation refuses data
from either training or validation populations. Declare families consistently:
hashes cannot identify two differently encoded variants of the same family.
There is no automatic hyperparameter search over validation outcomes. A final
untouched family/race split and deployed mixed-field evaluation remain necessary.

Models include the feature schema, finite weights, training digest, split
identities and validation report. `profile` embeds model parameters directly in
the generated profile, so the existing fleet manifest binds the model bytes as
well as the experimental configuration. There is no mutable external model file
loaded midway through a race. Missing, malformed, incompatible or non-finite
models fail at setup. **No fake or production-trained model ships by default.**
The real-JVM regression trains a tiny pilot solely to test the complete plumbing.
Its counterfactual metrics are not deployment performance evidence.

## Reproducible commands

Use JDK 25+, build with `sh build_main.sh`. Never edit `user.properties`.
Generate a normal champion log with a dedicated profile matching its roster,
then collect each family to its own NEW directory:

```sh
python tracks/racecraft_lab.py collect \
  --log results/hairpin.log --props results/champion.properties \
  --track hairpin --family open-u --seed 1 --stride 25 --limit 20 \
  --heap=-Xmx8g --out results/data-open-u
# Repeat on genuinely distinct course families for validation and final test.
python tracks/racecraft_lab.py train \
  --train results/data-open-u --validation results/data-other-family \
  --out results/ranker.json
python tracks/racecraft_lab.py evaluate \
  --model results/ranker.json --data results/data-untouched-family \
  --out results/ranker-test.json
```

Generate an isolated profile for each arm, or a combined profile after training:

```sh
python tracks/racecraft_lab.py profile --experiments interaction \
  --out results/interaction.properties
python tracks/racecraft_lab.py profile \
  --experiments interaction,refresh,opportunity,encounter,learned \
  --model results/ranker.json --out results/all.properties
python tracks/promotion_pair.py --players 8 --start-mode legacy \
  --seeds 31-40 --props results/interaction.properties \
  --heap=-Xmx8g --out results/interaction-legacy-31-40
```

`profile` leaves candidate slots empty. `promotion_pair.py` supplies complementary
odd/even cohorts and checks both. Use a seed window only after confirming it has
not informed prior development; **31–40 above is illustrative, not certified
untouched**. Run each arm separately before the combination, all start modes,
and two-/four-/eight-car fields. Full fleet results, runtime tails and fixture
review are required before any default-policy promotion. Do not re-freeze golden
expectations just to make an experiment's changed trace pass.

## Tests

```
sh run_tests.sh
python -m unittest discover -s tests -p 'test_*.py'
python tests/racecraft_lab_regression.py --heap=-Xmx8g --out results/lab-contracts
python tests/golden_races.py
for p in tests/ai1_*_regression.py; do python "$p" || exit; done
```

`RacecraftLabTests` covers flag/model validation, direct/indirect ranking,
slot ordering, high physical speeds, graph bounds, refresh, terminal/solo/timeout
semantics, the legal blockade, non-final lap progress, place-before-time,
unknown budgets, real-decision/control isolation and feature immutability.
The 17 Python unit contracts cover exact classification bookkeeping, censoring,
learning direction, finite schemas, dataset hashes, duplicate decisions,
family/race/geometry leakage, validation/test separation and no-overwrite exports.
The production CLI regression collects actual counterfactuals, trains a pilot,
embeds it, races each flag with mirrored assignments, tests an eight-car combined
arm, and verifies default/zero-budget control identity. Its optional
`--reference-jar` checks the pristine base on the identical runtime/heap.

Local supplementary JDK 21 testing reproduces the same Hairpin-s10 golden
mismatch in pristine master and the experimental build; the other eleven golden
cases match. This is not silently re-frozen. Supported-JDK validation and retained
logs distinguish environment behavior from an experiment leaking into controls.

## Second research batch

See [racecraft-next.md](racecraft-next.md) for the independently gated `diverse`,
`progressive` and `lexicographic` modes, policy-state collection, focal-replacement
opponent leagues, and decision-regret reports. The original schema-1 commands
and flags remain supported. These additions are not policy promotions.
