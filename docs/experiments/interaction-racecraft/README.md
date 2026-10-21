# Interaction-focused racecraft: research plan

Date: 2026-10-21. Branch: `work/racecraft-ideas-20261021`.

Reviewed baseline: [`b75ff732b7906fdc6cf5ce1c319b17f2e4a74f26`](https://github.com/senegrom/TheoreticalRacing/commit/b75ff732b7906fdc6cf5ce1c319b17f2e4a74f26), the round-327 champion.

**Status: proposals only.** This document preserves the six ideas from the latest racecraft review. None is implemented, enabled, benchmarked or promoted by this change. It changes no policy, map, rule, track, configuration or benchmark code. Experiment IDs IR1–IR6 below are local planning labels, not allocated campaign round numbers.

The central question is: **which sequence changes who can get through the next contest first, and which opponent decision determines whether it works?** The aim is better competitive reasoning, not more blanket caution or indiscriminate search depth.

## 1. Evidence that changes the priorities

The authoritative historical results are in the [baseline campaign ledger](https://github.com/senegrom/TheoreticalRacing/blob/b75ff732b7906fdc6cf5ce1c319b17f2e4a74f26/racing-memory.md). The following are recorded results from that ledger, not new measurements:

- Round 316 introduced projected-place ranking. Round 326 applied that objective inside nested choosers as well, aligning the model more closely with the policy it predicts. Round 327 uses sixteen-round forecasts for decisions with two live cars, rather than twelve.
- Response-cycle arm 323 was inert in duels and essentially neutral in four- and eight-car fields. Merely completing the roster cycle is therefore not a priority to repeat.
- The G1 exact-tie study on the round-316 champion tested 3,407 forced switches: 3,360 left the forced car's place unchanged, 22 improved it and 25 worsened it. This makes exact-tie-only action learning a sparse target. It does not establish that all alternative learning targets are unlearnable.
- Rival-fidelity arm 328 was screened on the round-326 base. Three stronger decisions for the relevant rival had promising initial readings, but its interaction with the promoted round-327 horizon is not established by those readings.
- The contingent arm ported to round 326 reported a four-car gain and substantial runtime cost; its eight-car screen was still in flight at the reviewed baseline. Selective planning deserves investigation, not an assumption that always-on planning pays.

Reported mirrored candidate-minus-champion place differences must retain their original units. They are not automatically the same quantity as a per-candidate shift from the balanced-field mean, or a lone-entrant comparison. Do not add gains measured on different champions and call the sum a stack result.

## 2. Priority and experiment map

| Priority | ID | Proposal | Smallest useful first result |
|---|---|---|---|
| 1 | IR1 | Select a simulated decision's horizon from its simulated field | Count finish-induced pack-to-duel transitions and resulting action disagreements |
| 2 | IR2 | Allocate a fixed stronger-rival budget to decisive rival–time pairs | Beat first-K scheduling with matched call budgets and reported runtime |
| 3 | IR5 | Measure single-action versus paired-action intervention headroom | Find held-out states where pairs help although no tested singleton helps |
| 4 | IR3 | Extend forecasts through unresolved interactions | Reduce finishing-order errors versus fixed horizons at comparable cost |
| 5 | IR4 | Generate multi-cell route-denial plans using exact time debt | Find naturally occurring useful plans that singleton bottlenecks miss |
| 6 | IR6 | Calibrate uncertainty in relative classification | Positive held-out value from evaluator disagreements, not just prediction fit |

Before interpreting IR2, run the horizon × rival-fidelity factorial in section 9. Develop arms separately; combining them is a subsequent experiment.

## 3. IR1 — Simulated-field horizon selection

### Mechanism

At the reviewed baseline, `RaceAi.computeAiMove()` selects `chooserDuel` from the real field at the top level. Recursive calls return before that selection is refreshed. An upgraded decision inside a forecast inherits the enclosing decision's horizon. The upgraded-memo documentation explicitly describes this scope.

Consider a decision with three live cars. A car finishes inside its forecast, leaving two cars contesting the remaining places. An upgraded decision on that board still inherits the twelve-round pack horizon, whereas a fresh real decision on the same physical field would select sixteen rounds.

This is a **candidate policy-model mismatch**, not a demonstrated cache defect. The current cache is designed for the current semantics. It is also not evidence that changing the scope necessarily improves play: bounded recursion is deliberately approximate.

### Proposed arm

When an upgraded simulated decision starts, derive its effective horizon from the installed simulated field, then restore the outer scope in `finally`. Keep the outer forecast's horizon, own-upgrade allowance and stopping convention unchanged. Do not silently turn this into extra full-policy recursion.

The first arm should cover pack-to-duel transitions caused by **finish crossings only**. Exclude transitions caused by hypothetical crashes or timeouts, separating this hypothesis from model-retirement semantics and the no-phantom-win rule. Keep the ordinary simulated terminal handling authoritative.

### Diagnostic and validation

Instrument eligible transitions, stronger decisions remaining after them, simulated actions changed and returned real actions changed. Construct a three-car witness and matching fresh-policy query; also test two-car, unchanged-pack, retirement-excluded and nested-scope restoration controls.

Initially bypass the affected upgraded-move memo on the experimental path. Re-enable it only after its effective-horizon dependencies and exactness are established. Compare cache-on/off decisions, cold/warm runs and query behaviour. A new context-sensitive setting must not reuse an entry from an incompatible context.

**Stop condition:** if eligible events or returned-action differences are negligible, record inactivity and stop before a large fleet run. If active, separate modelling fidelity from competitive benefit: only full-race comparisons establish the latter.

## 4. IR2 — Stronger rival decisions where they matter

### Mechanism

`ChooserTraffic` already selects a rival through two-cycle reachable-cell interactions, not simply proximity. The remaining opportunity is temporal and multi-car: one rival's first K decisions need not be the most informative K decisions for choosing our action.

A third car can determine whether our direct opponent's exit clears. A quiet initial approach can consume stronger calls before a later braking contest. A merge may require one stronger decision from each of several rivals rather than several from one rival.

### Proposed arm

Treat each eligible computation as a `(rival, decision event)` pair. Obtain preliminary reacting traces for shortlisted root actions, and nominate decisions that resolve concrete differences between those traces: whether a cell clears, which exit is taken, which car reaches a contested landing first, or whether a rival abandons its minimum-time route.

Allocate a fixed budget, initially three stronger rival decisions per root comparison profile. Derive scheduling criteria symmetrically from the competing forecasts rather than choosing refinements because they make the current favourite look good. Include a bounded third-car dependency path when that car controls the direct rival's options.

When a stronger call changes a move, replay from the appropriate common state and recompute all subsequent reacting moves. Do not splice the changed action into an unchanged opponent trace. If exact checkpoints are reused, bind the full state, clocks, grid world, policy context and budgets; account for the same logical work when testing speed-only reuse.

### Controls and cost accounting

Compare the fixed first-K relevant-rival schedule, the proposed schedule and a deterministic simple event-based schedule. Keep the own-upgrade allowance and root shortlist fixed. Count preliminary-trace work and schedule construction as well as stronger calls: equal call counts alone do not imply equal CPU.

Record calls by rival and event, changed replies, changed root actions, decision latency and complete-race place/time results. A trigger allocates computation; it neither vetoes an action nor adds a safety or cooperation reward.

**Stop condition:** no measurable action-value improvement at comparable total cost, or gains that disappear after preliminary-trace overhead is included. First-K=3 is an existing campaign experiment, not a new idea claimed by this plan.

## 5. IR3 — Interaction-triggered forecast extensions

### Mechanism

At a bounded endpoint, projected arrivals append solo remaining distances. That can misprice a contest still in progress: two individually fast routes may require incompatible timed occupancies, and neither independent solo distance prices the resulting detour.

This differs from response-cycle arm 323. Completing a turn-order cycle need not resolve the competitive interaction.

### Proposed arm

At the normal endpoint, inspect finalists for a specific unresolved dependency: competing low-debt routes, an imminent closure of an exit, or a projected order hinging on which car clears a contested landing. A nearby car alone is not sufficient.

If any finalist triggers, extend all finalists to a common additional decision clock, initially a small bounded number of own decisions and the required rival responses. Recompute reacting moves. Preserve terminal outcomes immediately, and retain a hard global cap. No extra own or rival upgrades should appear without being charged to the configured budget.

Use absolute, slot-aware timing. One candidate must not become artificially worse just because its longer evaluation records a rival actually finishing while another candidate retains only an optimistic projection at an earlier endpoint.

### Tests and limits

Compare against the normal horizon, a fixed longer horizon and a runtime-matched control. Use complete referee continuations to measure projected-order errors, root-action disagreement value and extension activation frequency. Test quiet nearby cars, unresolved merges, terminal crossings and repeated trigger/cap behaviour.

Apparent separation is not a certificate that cars will never interact again; they can meet at a later corner. A bounded extension improves an approximation, not a universal proof. Existing branch-and-bound shortcuts must remain admissible under the extended evaluation; bypass any whose validity is not established.

**Stop condition:** extensions mostly chase permanently unresolved interactions, or a fixed horizon at the same cost performs as well or better.

## 6. IR4 — Multi-cell denial with exact time-debt accounting

### Mechanism

The archived `AmbushPlans.mandatory()` finds singleton cells shared by every mapped minimum-time route at a layer, then seeks an interception. A rival can instead have several fast routes with no shared mandatory cell, yet a feasible sequence of our timed occupancies can deny all of them.

Example: the left route requires cell L on one response cycle, while the right route requires cell R on a later cycle. Occupying L at the first relevant time and R at the second can remove both routes without either cell being individually mandatory.

### Time-debt identity

Let `P(s)` be exact remaining solo moves, with the appropriate lap, gate and legal-world state. For a legal transition `s --a--> s'` with finite distances in the same model, define:

```
delta(s, a) = 1 + P(s') - P(s) >= 0
```

The inequality follows from the shortest-path property. For k own moves it telescopes:

```
k + P(s_k) = P(s_0) + sum_t delta(s_t, a_t)
```

A zero-debt action lies on a minimum-time continuation. Positive debt measures a time investment relative to that solo baseline, not a separate reward. The identity must not be applied across incompatible grid worlds, missing potentials, infinite map values or a domain that excludes the action under consideration.

For illustration only, projections `(ours, rival) = (40,39)` lose; spending one move to obtain `(41,40)` still loses and is slower; obtaining `(41,42)` changes the finishing order. Actual slot order and classification remain authoritative. Hurting a rival earns no bonus apart from its effect on our own place and time.

### Proposed generator

Build a bounded time-expanded rival graph containing routes with zero, one and two extra moves of debt. Track state, velocity, progress and timed occupancy, rather than collapsing distinct kinematics to a cell. Search feasible own manoeuvres whose occupancies cover the rival routes that would otherwise beat us. Keep a small number of genuinely distinct proposals for the normal reacting comparison.

Use the engine's actual endpoint-occupancy and crossing rules, not an assumed continuous-vehicle collision model. Apply roster order at each event. Do not infer mandatory cells or forced delay from an incomplete graph layer, or silently count a finish as an ordinary continuing state.

### Scope of evidence

Start as a **proposal generator**, not a forced-win certificate. Opponents can reroute, spend more debt or disrupt our plan. A bounded AI graph cannot prove a claim against unrestricted physical replies. Hypothetical rival crashes are not factual retirements.

Measure natural-state coverage, routes denied, own debt, proposal acceptance and realised classification. Compare with the singleton generator and a cost-matched generic widening control. An accepted multi-move proposal must use executable, conditional follow-up logic; a beneficial imaginary suffix is not enough.

**Stop condition:** no meaningful natural-state headroom beyond singleton proposals, or proposals repeatedly rely on opponents following a frozen trace.

## 7. IR5 — Paired-intervention headroom and selective planning

### Mechanism

A forced first action can be bad under the ordinary continuation yet useful with a different second action. The second action can itself depend on the setup. The negative G1 exact-tie singleton study does not directly measure this interaction.

### Offline study

Sample complete real decision snapshots across track families, field sizes and race phases. For each, compare:

1. The unchanged policy's complete reacting tail.
2. The best tested single own-action intervention in a bounded window.
3. The best tested pair of own-action interventions in the same window.

Include the unchanged action and singleton cases within the pair search so that headroom differences are interpretable. Cap and record enumeration budgets. Define later intervention times by the focal car's own decision count; terminal states or inadmissible second actions cannot supply a successful plan.

Every rival reacts afresh in every continuation. Record how often no tested singleton improves place but a tested pair does, and separately record equal-place own-time opportunities where terminal outcomes are comparable.

### Avoid an oracle-to-policy fallacy

Choosing the best pair after observing complete tails measures an offline opportunity bound under the pinned continuation policies. It is not proof that an online controller can identify the pair, nor that it will work against other opponents. More enumerated pairs also create more selection opportunities; report budgets and hold out whole races and track families.

Turn demonstrated opportunities into either a cheap search trigger or a small manoeuvre-proposal model. The learner nominates when or what to search; the reacting evaluator remains responsible for selection. Use the conditional-plan machinery for accepted continuations, including state matching, legality, replay and Undo semantics.

### Controls

Compare always-on contingent search, triggered contingent search and a budget-matched simple trigger. Include negative and quiet states when learning the trigger. Report precision, coverage, missed opportunities, full decision cost and race outcomes, not merely training accuracy.

**Stop condition:** pairs add little useful headroom over singletons, or the apparent opportunity cannot be predicted on held-out races without clairvoyant use of future replies.

## 8. IR6 — Uncertainty in relative classification

### Mechanism

Projected-place ranking turns approximate future arrivals into a hard order. Two plans can project the same place, but the faster one may depend on a poorly resolved traffic interaction. This is a broader target than exact primary-value ties.

For final place `R_i`, including the game's retirement and last-survivor rules:

```
R_i = 1 + sum_{j != i} 1[j is classified ahead of i]
E[R_i] = 1 + sum_{j != i} Pr(j is classified ahead of i)
```

This identity needs no independence assumption. Uncertainty is uncertainty in the forecast and opponent model, not invented randomness in deterministic physics.

### Proposed evaluator

Keep factual finishing precedence as the first comparison tier, as required by the owner. Within an equal factual tier of unresolved outcomes, estimate additional rivals likely to classify ahead; use own time only after the experimental place estimate. Keep completed outcomes and sound tactical certificates authoritative. Do not use predicted probabilities to erase a rival that actually finished ahead or to manufacture an achieved win from a model crash.

Learn pairwise classification or relative-arrival errors from joint, reacting continuations. A congestion event can delay both cars equally while leaving their order unchanged; independent own-time models miss that common cause. Do not multiply independent pairwise probabilities to claim a win probability: the expectation identity does not justify that step.

Use complete classified tails, including crashes and losing actions. Verify exact baseline control replays. Oversample informative forecast failures only with recorded inclusion probabilities or an appropriate representative calibration set. Split by whole race and track family, and test across retained opponent-policy variants where supported.

### Evaluation sequence

Begin in shadow mode. Measure calibration, held-out ranking quality, decision disagreement and realised value of those disagreements. Then test an explicitly candidate-gated evaluator with out-of-domain abstention and no hidden risk-aversion term. It may act outside exact ties, but only in its documented unresolved-outcome scope.

Do not mistake a frozen continuation label for a guaranteed outcome of the learned on-policy controller. A changed evaluator changes the state distribution and needs fresh on-policy evaluation. Re-establish branch-and-bound admissibility and model-version cache isolation before retaining those optimisations.

**Stop condition:** apparently good prediction metrics without positive held-out decision value, poor calibration across track families, or a policy that effectively recreates worst-case blanket caution.

## 9. Required interaction test: horizon × rival fidelity

Use one pinned common base and explicit arms; round-326 and round-327 headline gains cannot be added. First reproduce the intended controls on that base.

| Arm | Duel horizon | Stronger moves for the selected rival |
|---|---:|---:|
| H12/R1 | 12 | 1 |
| H16/R1 | 16 | 1 |
| H12/R3 | 12 | 3 |
| H16/R3 | 16 | 3 |

Keep shortlist construction, own upgrades, projected-place keys, tie rules, start modes and non-duel horizons fixed. Preserve the outer twenty-cell solo rule. Revisit memo keys for every effective policy setting.

Run matched and mirrored comparisons with common seed windows and seat assignments, plus the required lone-entrant checks. Report the four cells rather than only the winning configuration. For a common-baseline outcome metric M, the interaction contrast is:

```
[M(H16/R3) - M(H12/R3)] - [M(H16/R1) - M(H12/R1)]
```

Use matched sampling uncertainty; a contrast between different opponents or baselines is not automatically a factorial interaction. Lower place remains better. Follow the controlled comparison with direct competition between the promising configurations. In larger fields, separately report whether the real race ever entered the two-live-car regime and whether the arm changed any decisions there.

This is an experimental design, not an implemented command or claim that four such runs have occurred.

## 10. Shared constraints, artefacts and promotion requirements

All future arms must respect [AGENTS.md](../../../AGENTS.md): own finishing place first, own time second; no active cooperation, yielding or field-wide efficiency objective; unchanged computed starts and twenty-cell solo behaviour. Crashes are already priced by classification. Field crash totals and summed moves are descriptive, not additional vetoes or rewards.

Use explicit opt-in candidate gates and retain a frozen control. Never edit `user.properties` or regenerate fleet tracks in place. Keep diagnostics behaviour-invisible. Defaults, flags-off, no-slot and zero-budget controls must preserve champion actions where applicable.

Every executable result needs a manifest binding source/JAR, policy/model settings, runtime, track geometry, seed, roster, seat and protocol version. A replay snapshot must preserve grid entitlement, clocks, progress, classification and policy memory. Reject malformed or incomplete tails; ordinary control continuations must reproduce the captured race before their counterfactual labels are accepted.

Record activation, proposed and accepted alternatives, returned-action changes, logical work, elapsed runtime, own classification and comparable own time. Use race or track/seed pairing when reporting uncertainty; car outcomes in the same race are not independent samples. Report per-track results, strongest-course/family exclusions and held-out geometry separately from held-out starts.

Correctness witnesses, compilation and small race screens establish neither broad performance nor promotion. Before promotion, execute the repository's Java, Python, golden, replay, browser-parity and champion-regression requirements, then mirrored two-, four- and eight-car comparisons, relevant random/computed/scattered starts and held-out seeds, and the required all-seat lone-candidate battery. Reverse-entry fields are an additional diagnostic, not a substitute. Record actual executed results, failures and omissions; do not pre-populate a validation file with expected successes.

For each arm, the deliverables are a bounded opt-in implementation, source-level witness/control tests, an exact replay case or explicit inactivity report, an independently reproducible comparison and a campaign-ledger entry. Leave ineffective arms unpromoted and keep their negative results.

## 11. Source anchors and implementation surfaces

These links pin the source reviewed for the ideas; historical code is not claimed to be on current master.

- [Campaign evidence and owner decisions](https://github.com/senegrom/TheoreticalRacing/blob/b75ff732b7906fdc6cf5ce1c319b17f2e4a74f26/racing-memory.md): rounds 316, 323–328 and G1.
- [RaceAi.java](https://github.com/senegrom/TheoreticalRacing/blob/b75ff732b7906fdc6cf5ce1c319b17f2e4a74f26/src/tr/logic/RaceAi.java): `computeAiMove`, `chooserRounds`, `awareMoveOverState`, `maintainUpgradedMemo`, `upgradedMemoOn`, `jointChooser`, `simOutcomeCore`, `ppPlaceKey` and `bnbPotential`.
- [ChooserTraffic.java](https://github.com/senegrom/TheoreticalRacing/blob/b75ff732b7906fdc6cf5ce1c319b17f2e4a74f26/src/tr/logic/ChooserTraffic.java): two-cycle interaction selection and reusable fronts.
- [Archived AmbushPlans.java](https://github.com/senegrom/TheoreticalRacing/blob/4671caf2c054fed7081a36c59009ba917b868045/src/tr/logic/AmbushPlans.java): singleton mandatory layers and backward interception; a reference implementation to inspect, not a promoted feature.
- [Prior implementation commit](https://github.com/senegrom/TheoreticalRacing/commit/be4a8e98bc545003f762aad02dbbed29fc1d7aa3) and [its research documentation](https://github.com/senegrom/TheoreticalRacing/blob/006503a5363f3ddc0d68b72fc3502c3064b67593/docs/experiments/decision-racecraft/README.md): complete replay, paired counterfactual tooling and conditional-plan state. Reconcile interfaces and policy semantics with the new baseline before reuse.
- [Mirrored scorer](https://github.com/senegrom/TheoreticalRacing/blob/b75ff732b7906fdc6cf5ce1c319b17f2e4a74f26/tracks/head_to_head.py) and [lone-entrant runner](https://github.com/senegrom/TheoreticalRacing/blob/b75ff732b7906fdc6cf5ce1c319b17f2e4a74f26/docs/experiments/duel-lookahead/run_1vfield.py): retain metric units and manifest contracts.

## Validation of this documentation change

No new engine tests, simulations, model training or fleet experiments are claimed. The baseline and its latest ledger entries were read, the six proposals were separated from historical results, and the pushed file and branch diff are to be checked. This research plan is not a request to promote any arm or change the live champion.
