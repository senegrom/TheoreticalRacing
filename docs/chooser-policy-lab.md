# Chooser-policy laboratory (research only, 2026-09-19)

Base: `720f421fc5c93795f9f0d4f14249b0c6898af7b8`, the promoted round-260
12-round chooser with the finish-target reach-cache key correction. This is a
new research branch, not a replacement with the archived round-254 laboratory.
No champion constants, golden expectations, saved settings, bundled courses or
master publication workflows are changed. None of these experiments is promoted.
Each driver still optimizes its own race; there is no cooperation, yielding
reward, coalition of opponents, or aggregate-crash acceptance gate.

## Opt-in controls and comparison boundary

A real focal decision requires BOTH selected `candidateSlots` and explicit
`chooser.experiments`. Audit-only mode is observational and does not require
selected slots. Flags, models and bounds are validated at game setup.

| Flag | Additional question |
| --- | --- |
| `aware` | What if our next projected decision and one directly interacting rival's decision use the stronger chooser policy? |
| `setup` | What if a shortlisted first move is followed by a different deliberate second focal action? |
| `terminal` | Among candidates with resolved simulated classifications, which actual place and own completion time is better? |
| `student` | Can a trained approximation of the chooser replace those bounded upgraded continuation decisions? |
| `assist` | Can a trained model suggest one extra legal candidate which the real forecast then evaluates? |
| `legacy-guarded` | Controlled insertion test of an explicit original 12-feature ranker, before downstream guards. |
| `legacy-unchecked` | Diagnostic-only unchecked insertion of that same ranker's proposal after downstream guards. |

`aware` and `student` are mutually exclusive. Each legacy control must run alone;
there is no implicit historical model and no production-trained model is bundled.
The unchecked control deliberately recreates a dangerous experimental insertion
point. It is NOT a suggested deployment policy. It must not be used to bypass
correctness gates or presented as a repair.

```
chooser.experiments=aware,setup,terminal
chooser.rounds=12
chooser.policyBudget=4096
chooser.moveBudget=8192
chooser.setupWidth=2
chooser.audit=false
chooser.auditEvery=1
candidateSlots=1,3,5,7
```

`rounds` is 1–24, using the production simulator's convention: the first round
contains only remaining higher-numbered slots; subsequent rounds contain the
full roster. It is NOT 12 complete focal-to-focal cycles. Policy/move budgets
bound ADDITIONAL scorer invocations (including nested scorers) and simulated
live move slots, respectively, across the entire real decision. Their ranges
are 0–65536 and 0–131072. Exhaustion retains the ordinary chooser; a partial
comparison never becomes a predicted death or win. Zero in either budget is an
identity control. These are not CPU-time limits: the unchanged champion's work,
fixed-size feature calculations and bounded 2048-transition interaction graphs
are separate costs. Runtime tails still require measurement. `setupWidth` is
1–3, including the original continuation, and audit sampling is deterministic.

All genuine proposals are made at the existing chooser's position BEFORE the
ordinary pace overrides, danger checks and confirmations. Later stages may
legitimately replace them. Proven tactics, terminal/checkpoint precedence and
other earlier returns are untouched. The default path calls the original
chooser implementation verbatim. No flag can activate itself merely because a
candidate-labelled rival is temporarily installed inside a control's simulation.

## Bounded chooser-aware and two-action forecasts

The ordinary root chooser is evaluated first. For an `aware` arm, at most the
first projected decision of the focal driver and of one directly interacting
rival is upgraded. That driver uses an unsuppressed decision, including the
current chooser and downstream pace/guard processing. Inside that upgraded
call, all subordinate simulated driver calls are suppressed. Thus there is one
additional policy-improvement level, not recursive unbounded chooser expansion.
The original cap/distance selection and proxies remain for all other decisions.
The recovered interaction graph allocates effort, never adds a danger penalty
or removes an unselected car. An incomplete graph cannot certify independence.

For `setup`, each original first-action candidate has an ordinary continuation
plus up to `setupWidth-1` different legal second focal actions. Those alternatives
are considered only AFTER intervening drivers have responded to the first move.
The actual continuation is always retained; other second actions are ordered by
complete route potential when available, then deterministically by direction.
Each first/second pair gets a fresh forecast. Only the first action is committed;
there is no persistent forced plan. The execution audit records whether the
justifying second action is selected again when its state is actually reached.

The `counterfactual` command performs the stronger offline experiment: full
oracle-driven races after one or two substituted actions. Intervening replies
and second-action legality are recomputed by the supplied frozen real policy,
not copied from the short forecast. It reports the best single-action and
best evaluated two-action result. Any incomplete alternative censors the whole
comparison; no easy subset is labelled a complete comparison.

## Resolved outcomes are not heuristic distances

The existing simulator still supplies the same integer verdict to existing
callers. A parallel detached ledger receives every actual selected acceleration
and applies the same referee with lap/checkpoint credit, occupied landings,
finish-before-occupancy exemption, timeout precedence, retirement order and
last-survivor classification. A solo time trial retains its exception.

The laboratory additionally records terminal status, actual simulated place and
own committed moves. `terminal` first finds the ordinary verdict winner. ONLY
when that winner has a known terminal classification does it compare the other
resolved candidates by place, then own moves. Unresolved estimates are not
promoted to facts or mixed into a non-transitive terminal/heuristic ranking.
A dead-vs-live distinction remains the old rule unless both are resolved.
These are exact classifications for the SIMULATED sequence, not guarantees
about what real opponents will choose. Legacy query sentinel markers do not
supply a classification ledger and cannot activate this ranking.

## Teacher collection and distillation

`chooser3,mover,turns,laps,finishedFirst,finishedLast;...` queries restore full
seven-field car states and real retired-place markers, validate the entire
ledger before mutation, and return the ordinary decision plus chooser audit.
`v3` returns the existing V2 transition response. V2/legacy requests clear the
classification counters rather than inheriting a previous V3 request.

The teacher is the CURRENT 12-round chooser on states from a supplied current
or experimental race. `collect` first replays every source move under its source
profile. It then clears experimental flags/slots in a separate teacher profile.
Source policy and teacher identities are retained separately. The teacher gives
its actual candidate verdicts, not invented completion labels. The 19 bounded
relative features are recovered from `f03922e` and computed only in Java; the
first 12 retain the original ranker's feature semantics. No absolute position,
track name, seed, player identity or fixture identity enters a weight vector.

```
python tracks/chooser_lab.py collect --log results/race.log \
  --props results/source.properties --track hairpin --family open-u \
  --stride 25 --limit 20 --heap=-Xmx8g --out results/teacher-open-u
# Collect genuinely distinct validation and untouched final-test families too.
python tracks/chooser_lab.py train --train results/teacher-open-u \
  --validation results/teacher-validation --out results/chooser-student.json
python tracks/chooser_lab.py evaluate --model results/chooser-student.json \
  --data results/teacher-untouched --out results/student-heldout.json
```

Deterministic pairwise training ranks the teacher's values: any finite surviving
verdict beats death; unknown route values and equal pairs provide no labels.
It learns the chooser's comparative forecast, NOT final race places. Reports
separate teacher-value agreement, teacher-death errors, switches from the
score-only policy and teacher time regret. Whole races, declared geometry
families and exact course hashes must be disjoint across train/validation/test.
The teacher implementation must agree. A held-out teacher-regret improvement is
not a deployed-policy improvement. Models must be updated between experiments.

Inputs bind the JAR, course, source log, source/teacher profiles, Java executable
and version, explicit heap, seed, selection and Python tooling. Retained copied
profiles are also checked for changes, and copied evidence hashes are verified
when loading a dataset. Missing/changed input or interrupted work leaves a
pending marker, not a publishable dataset. Output files are never overwritten.

`student` uses the explicit model ONLY in those bounded upgraded simulated
decisions, before their own downstream guards. `assist` asks the model for one
extra scored/legal first action, then includes it in the real forecast
comparison; it does not grant a direct learned override. Neither path promises
saved time or better places. Feature costs and tail latency must be measured.
Models are embedded in generated profiles, never loaded from a mutable external
file halfway through a race.

```
python tracks/chooser_lab.py profile --experiments aware,setup,terminal \
  --out results/aware-setup.properties
python tracks/chooser_lab.py profile --experiments student \
  --model results/chooser-student.json --out results/student.properties
python tracks/chooser_lab.py profile --experiments assist \
  --model results/chooser-student.json --out results/assistant.properties
```

Generated profiles leave slots empty; `promotion_pair.py` supplies complementary
cohorts. For each native diagnostic race explicitly select slots in a DISPOSABLE
profile, never `user.properties`. The two legacy control profiles accept an
explicit `--legacy-model` in the archived original v1 format. Comparing them
isolates insertion point with the SAME frozen weights and shortlist; it does
not claim to reproduce the historical round-258 population or old policy.

## Decision-path and forecast/execution audits

With `chooser.audit=true`, stderr gets one `CHOOSER_AUDIT` JSON record per
sampled real decision: original score selection, chooser candidates and verdicts,
research proposals, stage replacements, final action, work counts, modelled
steps, forced follow-up, geometry/finish/gate metadata and cache key. Timing
never selects an action. Known bypasses include tactical proofs, solo precedence,
singleton shortlists and geometric crossing precedence; other early returns are
reported as before-chooser, not mislabeled as evaluated.

```
python tracks/chooser_lab.py audit --log results/race.log \
  --audit results/race.stderr --out results/forecast-audit.json
python tracks/chooser_lab.py counterfactual --log results/race.log \
  --props results/source.properties --track hairpin --move 1 --depth 2 \
  --second-width 2 --heap=-Xmx8g --out results/two-action-deviations
```

The audit checks alignment with the committed race, compares a forecast only
when its first action was actually committed, and stops at the FIRST divergent
state/action. Later predictions are not independent errors. Where an audit for
the diverging real decision exists, its policy stages are attached; this is
observed correspondence, not a causal claim about which layer improved place.
Follow-up results distinguish a matching prefix from a different state where
the planned action would no longer be justified. Bypassed hooks and final
unforecast actions remain explicit missing evidence.

## Fixed-opponent league

`chooser_lab.py league` reuses the archived laboratory's focal-replacement
method, not its old runtime hook. Supply version-1 JSON with `referee`, `baseline`,
`candidate`, `backgrounds`, `densities` and a `policies` list. Each policy names
`name`, `jar`, `props`, and `protocol` (`v3`, or `v2` for a non-experimental
historical implementation). Paths are relative to the spec. Every JAR has its
matching `tracks/<track>.track` beside it. Geometry/roster/laps must agree.

For each source start, density and focal slot, all opponents remain identical
while the focal is replaced baseline/candidate. Experimental actors must select
their assigned slots. Every queried transition is checked against the single
referee; disagreement aborts rather than mixing games. No rival coalition is
created. Each driver's continuation comes from its individually assigned policy.
Defaults rotate every slot; densities 1,4,7 apply to an eight-car field.

```
python tracks/chooser_lab.py league --spec results/league.json \
  --logs results/starts-1.log results/starts-2.log --track hairpin \
  --heap=-Xmx8g --out results/league
```

Reports retain each opponent/density population, complete and censored pairs,
place differences and time differences at equal place. Homogeneous mean place
is not treated as a performance metric. The process-oracle harness's runtime
is not native decision latency. Historical binaries must be supplied explicitly;
using one binary through V2 is only an interface compatibility control.

## Cache-history protection and validation

```
sh build_main.sh                         # supported JDK 25+
sh run_tests.sh
python -m unittest discover -s tests -p 'test_*.py'
python tests/chooser_lab_regression.py --heap=-Xmx8g --out results/lab-contracts
python tests/chooser_cache_regression.py --heap=-Xmx8g --out results/cache-contracts
python tests/golden_races.py
for test in tests/ai1_*_regression.py; do python "$test" || exit; done
```

The cache test checks two complete races against isolated cold, warm and
post-Java-suite cache histories. It does not mutate courses, keys or goldens.
`--skip-suite` is explicitly diagnostic and cannot claim post-suite invariance.
Use isolated cache directories for every campaign and retain input manifests.

Local supplementary JDK 21 testing passed the default 12 goldens, Java contracts,
18 new tooling tests and the native end-to-end laboratory run (14 native races,
three teacher datasets, trained pilot, complete two-action deviations and eight
focal-replacement races). These are bounded functional samples; the pilot is not
a production-trained model and protocol controls are not historical performance.
Supported-JDK CI results are recorded separately with their exact tested tree.
No full mirrored fleet, chooser-aware gain, two-action gain, real browser-JVM
execution of experimental flags, or production latency-tail result is claimed.
Promotion still requires all-course mirrored places against round 260 or the
then-current champion, legacy/informed/scatter starts, genuinely untouched data,
individual-arm and combined-arm tests, fixture review and runtime-tail checks.
