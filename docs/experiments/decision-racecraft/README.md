# Decision-aligned racecraft research

Branch: `work/racecraft-improvements-20261019`.
Baseline: `e3cd7d2d4e12ef75e4a8df7c2d6b09769d047409` (the reviewed
`284c304` champion plus the first reporting change). **Nothing is promoted.**
No trained model is enabled by default, and no performance gain is asserted.

## Independent policy arms

Use a separate profile, never `user.properties`:

```properties
candidateSlots=1,3,5,7
racecraftFeatures=response-cycle,duel-ties,contingent
racecraftTrials=24
racecraftAudit=true
```

Prefer measuring one flag at a time before combinations. With no candidate
slots, no flags/capture, or `racecraftTrials=0`, the champion's decisions remain
unchanged. The literal twenty-cell solo rule, starting placement, the maps,
track files, and physical collision/finish rules are unchanged. Immediate and
certified tactical wins retain precedence over the research chooser and stored
responses. Nested champion forecasts do not activate the new chooser arms.

### `response-cycle`

The top-level candidate chooser still simulates twelve own moves, including
its candidate action. It additionally completes the preceding roster slots
in a final partial round, stopping immediately before the mover acts again.
Rivals later in the roster already responded in the last ordinary round.
This adds no own move and changes neither the five stronger own continuations
nor the selected rival's stronger first move. Normal terminal precedence is
retained. A model rival's crash still does not manufacture a chooser win.

### `duel-ties`

With exactly two live cars, reroll only the exact best primary-value ties
with one stronger own continuation, rather than five. A known, strictly
better secondary verdict wins; another tie keeps the incumbent. The later
map-only pace swap cannot undo a strict secondary judgement, including when
the incumbent stays selected but the pace alternative is strictly worse.
This is a new opt-in implementation of the round-314 idea, not a claim to
have completed the separate box's pending experiments or reproduced its gains.

### `contingent`

On a primary chooser tie, compare a bounded number of conditional plans in
two worlds. Both worlds select the SAME contesting rival: its nominal scorer
reply in one and its stronger first reply in the other. The mover's first
five later decisions use the full, recursion-suppressed champion policy.
Each trial starts at the original complete board and recomputes every
intervening action; there is no splicing an alternative into a frozen trace.

Each world's first subsequent own decision can use the ordinary second
acceleration or up to two other physical legal alternatives, ordered by mapped remaining
time and then stable direction order. An explicit
second action is injected through the very same response-table mechanism
used during actual play. If the policy's higher-precedence finish/proof/solo
rule chooses something else, that explicit plan is inadmissible. A null move,
unknown continuation or a predicted rival crash cannot justify acceptance.

Accept only no worsening in BOTH worlds and a strict own-place/own-time
improvement in at least one. Conflicting actions for an identical future
state are rejected. `racecraftTrials` is the maximum number of these forecast
trials per chooser, default 24, maximum 128; each admitted candidate reserves
both worlds. This is bounded model-conditional research, not a forced-win proof.

The actual first move, committed after the live Undo snapshot, installs at
most two next-decision responses for that seat. A hint/query never installs
or consumes them. They match the whole physical board, clock, progress,
classification, geometry, build/profile, grid entitlement and OTHER actors'
pending plans. The mover's own table is omitted from its lookup key to avoid
a self-referential key. Stale or newly illegal responses are ignored. Every
own committed move consumes the old table; Undo restores it; a race reset
clears it. Post-chooser overrides that change the proposed first action do
not install the abandoned plan.

### `paired-shadow` / `paired-value`

A small pairwise ridge model estimates differences in eventual own place and,
for equal-place actual finishers, an own-time residual above solo distance.
It is consulted ONLY among exact primary chooser ties. Thus a model cannot
erase a rival already finished ahead or overrule a distinct primary verdict.
`paired-shadow` records proposed disagreements without changing decisions;
`paired-value` applies supported predictions. Use one mode, not both.

```properties
racecraftFeatures=response-cycle,duel-ties,paired-shadow
racecraftModel=/absolute/path/rc-model/model.properties
```

The model must match the executable and policy profile and have finite,
well-shaped coefficients and positive scales. Missing/inapplicable models
or out-of-training-range features fall back to the existing chooser. Invalid
model files are rejected rather than silently loading corrupted coefficients.
The training profile permits switching shadow/application modes and changing
geometry; a complete replay snapshot separately binds the exact mode, actual
model, and geometry. AI1/AI2 labels are normalized in model applicability:
labels are not behavioural information. Coefficients are never distributed
as a promoted policy by this implementation.

The existing chooser branch-and-bound is disabled only for an active research
top-level comparison. This makes its primary values complete and avoids
assuming that the old bound is valid for an altered comparison. Nested
champion bounds and flags-off behaviour are retained. Account for the extra
CPU in experiments; a speed-only or promoted change is not being claimed.

## Complete replay and the data pipeline

The old V2 oracle remains readable, with its documented inference of grid
entitlement. It is NOT used for these labels. New `rp3` snapshots explicitly
carry each car's position, velocity, actual finishing place, lap/next gate,
grid entitlement, display gate indices, pending plans, global clock and
finisher/retirement ledgers. The snapshot is bound to geometry, model, flags,
roster and executable. Display trail coordinates are not policy input and are
not serialized; plan matching deliberately ignores display-only indices.

The query loop accepts:

```text
snapshot3
tail3|20000|-1|<rp3 snapshot>
tail3|20000|5|<rp3 snapshot>
```

`-1` follows the ordinary policy, and `0..8` forces only the first acceleration
in the existing `Direction` order. The ordinary first computation still runs
so a matching committed follow-up plan is retained. Later actors react with
the configured actual policies. Responses include a request SHA-256, complete
flag, each car's place and own move count, distinct FINISH/CRASH/TIMEOUT/
SURVIVOR/PRIOR fates, and the entire physical move trace plus its digest.
Timeouts use the live progress comparator. A budget stop is incomplete and
never enters training. AI-only profiles are required for complete tails.

A standalone workflow using only Python's standard library:

```sh
# Start with a separate 2-car AI-only profile, laps=1 or your target lap count.
# Keep the same policy flags/trial settings throughout capture and model use.
python3 tools/racecraft_pairs.py capture \
  --jar theoreticRacing.jar --props /tmp/study.properties \
  --tracks hairpin chicane circle --seeds 41-42 --limit 32 \
  --out /tmp/rc-capture

python3 tools/racecraft_pairs.py label \
  --capture /tmp/rc-capture --max-events 20000 --limit 32 \
  --out /tmp/rc-labels

python3 tools/racecraft_pairs.py train \
  --labels /tmp/rc-labels --holdout-families circle \
  --out /tmp/rc-model
```

Every stage requires a NEW output directory. Capture snapshots the JAR,
profiles and track files and pins the runtime and Java environment. It records
real committed disputed decisions, including the ultimately executed action
if later guards differ. The label stage first verifies the ordinary complete
continuation against the generating race suffix, move-for-move. Only then are
all available candidate continuations considered. Losing moves, crashes and
timeouts are retained; incomplete controls/tails are counted and excluded.
Duplicate states are explicit. Source/profiles/runtime changes fail validation.

Training requires separate whole races AND held-out track families; it refuses
cross-build/profile mixtures, duplicate/reversed pairs, malformed features and
unresolved labels. Synthetic families are grouped rather than randomly mixing
near-identical tracks. It reports supported-domain coverage, place regret and
conditional equal-place finishing-time regret, not an imitation accuracy that
can be dominated by easy routine moves. Standardization and feature ranges
use training data only. An out-of-domain validation row is reported as such,
not as a correct prediction. A successful tiny training smoke test is not
useful calibration or evidence that the learned policy wins races.

## Evaluation and reporting

The mirrored report now retains per-seat moves and terminal fates. It reports
same-seat place gains/losses/ties and time differences ONLY on equal-place pairs
where BOTH policies actually crossed the finish. A last survivor is not a
finisher, and its observed move count is not a finish time. Time is conditional
and descriptive, not a replacement for primary place comparison. Cars in one
race are not advertised as independent samples.

Both reports also show the result after dropping the strongest course and
strongest synthetic track family. This describes concentration; it does not
replace a prespecified held-out family evaluation.

`--props` preserves an arm's isolated settings in both existing screen tools.
The wrappers embed external model coefficients as `racecraftModel.*` properties
before launching a fleet, so the existing manifest pins the actual model,
not just a pathname. Direct fleet runs with an external `racecraftModel` path
are refused; use embedded properties or a wrapper. This avoids changing
`user.properties` or weakening existing manifest/completion checks.

```sh
# Explicit four-car coverage, alongside duels and eight-car fields.
python3 docs/experiments/duel-lookahead/run_screen.py \
  --jar theoreticRacing.jar --props /tmp/study.properties \
  --players 2 4 8 --modes legacy informed scatter --tracks ALL \
  --seeds 1-20 --out /tmp/rc-mirrored

# Lone candidate, rotated through every seat, versus an all-champion control.
python3 docs/experiments/duel-lookahead/run_1vfield.py \
  --jar theoreticRacing.jar --props /tmp/study.properties \
  --players 8 --tracks ALL --out /tmp/rc-lone

# Reverse entry: one old champion among seven candidates, every seat rotated,
# paired against an all-candidate control on the same track/seed/seat.
python3 docs/experiments/duel-lookahead/run_1vfield.py \
  --jar theoreticRacing.jar --props /tmp/study.properties \
  --players 8 --tracks ALL --reverse --out /tmp/rc-reverse
```

In the reverse report, NEGATIVE old-champion-minus-candidate place means the
old policy exploits a candidate-dominated field. Four-car reverse checks are
supported as well. Neither field crash totals nor summed field time veto a
candidate; own place first and own time second remain authoritative.

## Validation

`DecisionResearchTests` is included in `run_tests.sh`. It exercises the exact
final response cycle without adding an own move, explicit grid state,
canonical snapshot validation, side-effect isolation, committed response
execution, clock/opponent-memory invalidation, Undo, solo precedence,
shadow/application/OOD models, two-world non-regression and rejection of
unexecuted second actions, plus bounded complete referee tails.

`test_decision_research.py` covers reporting exclusions, family sensitivity,
model embedding, reverse-seat rotation and the strict paired training contract.
`tests/decision_research_cli.py` compares flags-off/no-slot/zero-budget controls
in all three start modes; tests individual arms and combinations with audit
on/off; verifies real control tails; and exercises label/train/model use end
to end. Supply `--baseline-jar` for an independently built pre-change champion.
Golden races, all existing AI pins and browser validation remain separate.
Only executed results belong in `validation.json`; no fleet promotion is
inferred from any of these functional checks.
