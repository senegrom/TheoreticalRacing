# Racecraft review: fixes, experiments and research plan

Baseline: `31bf6b986b669831a4ebc0b9d87cac5adb711a96` (round 278).
Branch: `work/racecraft-review-20260926`.

This PR includes all five recommendations from the review. Concrete fixes and
bounded prototypes are implemented; the full contingent-prefix follow-up and
learned joint-endpoint evaluator are specified below, not represented as trained
or promoted systems. A passing contract suite is not evidence of better places.
Actual validation commands are recorded in `validation.json` and the PR checks.

## Controls and unchanged rules

Every behavior-changing arm requires BOTH an explicit `racecraftReview` flag
and membership in `candidateSlots`. Empty flags or no candidate slots retain the
control policy. AI labels do not select experiments. Unknown flags fail loudly.
The experiment settings are ordinary race properties, included in the existing
benchmark manifests, rather than hidden JVM switches.

| Flag | Implemented behavior |
| --- | --- |
| `crossing` | A nonterminal geometric S/F crossing cannot abort the shortlist comparison. Use the full referee result for finish precedence. |
| `duel-anytime` | Retain completed winning certificates when further search exhausts its budget. |
| `duel-cache` | Per-attempt memoization of complete joint-state/depth/clock subproblems. |
| `projected-place` | Re-test ordering unresolved horizons by projected place, then own time. Actual classified outcomes retain their authoritative values. |
| `diverse` | Add at most one kinematically distinct candidate within one extra score unit. |
| `selective` | On a nominal tie, compare one stronger first response of one directly involved rival. |

`all` enables all six for interaction testing, not for attribution of gains.
`racecraftReviewAudit=true` emits diagnostics without enabling a policy arm.
The owner rules are unchanged: own finishing place first, own time second;
blocking and forcing a rival's crash are legitimate; no yielding or cooperation.
The canonical 20-cell boundary also gates the new duel options. The chooser
remains restricted to traffic within that same boundary. The existing referee,
starting-grid approximation, physics, maps, tracks, `user.properties`, golden
expectations and default-policy promotion status are not changed.

A bounded screen, using a new profile and fresh output directory:

```sh
sh build_main.sh
mkdir -p results
cp tracks/lap_bench.properties results/review-crossing.properties
printf '\nracecraftReview=crossing\n' >> results/review-crossing.properties
python3 tracks/promotion_pair.py \
  --props results/review-crossing.properties --players 2 --start-mode legacy \
  --seeds 1-2 --heap=-Xmx8g --tracks hairpin circle \
  --out results/review-crossing-2p-legacy-s1-2
```

The production runner supplies complementary candidate slots, preserves source
profiles, and validates the results. Repeat separately for each arm; do not call
these two tracks a full fleet. Never use the small-heap, silently demoted policy
as the champion. Unset hidden Java option variables before screening.

## 1. Finish geometry must not cancel a traffic comparison

The reviewed chooser returned the scorer's original choice as soon as any
shortlisted action crossed the S/F line geometrically. That could discard an
already-better evaluated candidate and skip remaining candidates even when a
checkpoint or lap was still owed. The `crossing` arm asks `evaluateMove` instead:
a genuine finish wins immediately, an illegal action is excluded, and a legal
nonterminal crossing is simulated with the successor's updated progress.

The contract constructs a real geometric crossing with CP1 owed, checks a
nonfinal lap crossing and a genuine final finish, and verifies that the candidate
actually evaluates both supplied actions where the control aborts after one.
It also checks live-state isolation. The defect's occurrence rate and place
cost in natural races remain to be measured. Do not replace this with a blanket
ban on S/F crossings or weaken checkpoint legality to satisfy the test.

Follow-up coverage should include the simultaneous final-checkpoint/finish case
in the chooser, both player orders, and naturally occurring counterexamples
harvested from the audit. Existing referee tests already cover combined events;
that does not make every chooser-specific path covered.

## 2. Keep completed duel proofs; use the same work budget better

The reviewed root discarded `best` when any later sibling exhausted the budget.
The new anytime arm returns only a fully completed certificate, never an
unfinished search. Universal opponent nodes still require every physical reply
to lose; a single unproved response is enough to withhold a certificate. Own
moves retain the planning cap; rival replies include all nine physical
accelerations, including map-dead and above-planning-cap continuations.

Memo keys contain both cars' position, velocity, lap/gate state, exact projected
clock, side to move and remaining own depth. Each table belongs to one horizon
attempt in one fixed game/grid-rule world and is never reused across decisions,
geometry, roster or rule changes. Budget-exhausted subproblems are not cached.
A completed `UNKNOWN` means only no certificate at this depth, not a proven loss.

Cache savings can finance extra nodes and therefore expose additional proofs.
`duel-cache` is accordingly a separately measured policy arm, not claimed to be
decision-invisible under a fixed physical-work budget. Shorter certificates
retain precedence; a fifth own move is not added.

The low-budget test finds nonvacuous witnesses where the control discards a
completed proof, verifies retained actions with the existing independent
physical-reply verifier, checks generous-budget cached/uncached agreement at
depths two through four, and checks zero-budget abstention and state isolation.
Audit counters separately report exhaustions, completed proofs discarded,
retained proofs, searched nodes and cache hits. First measure their frequency
in real races, then measure finishing places.

## 3. Re-test chooser variants after round 278, and measure returned actions

Round 278 stopped the round-49 tie-break from reversing many chooser proposals.
That changed the effective decision pipeline. Earlier width and ranking results
remain evidence about the older pipeline; they are not conclusive for this one.

`projected-place` is distinct from the already-promoted mandatory correction
that counts rivals actually finishing ahead. On unresolved full-round endpoints,
it estimates remaining order from each live car's own whole-race route value,
using the next round's slot order to break equal-time arrivals. It abstains when
a live route value is missing or a lap course lacks its whole-race potential.
Resolved outcomes remain exact. The estimate is not a proof that a rival will
follow its solo line, and there are no fitted probabilities.

`diverse` retains the ordinary stable shortlist and adds at most one candidate
within one extra score unit. The extra direction maximizes minimum Manhattan
separation from the selected accelerations, with deterministic score/enum ties.
This is a bounded proposal heuristic, not a claim that acceleration distance
always identifies tactical diversity. Compare it with the baseline directly and
then with the crossing fix; do not conflate wider proposals with better values.

The root audit records scorer, chooser, tie-break, initial pace, private/staged/
field-pace decisions, forecast evaluations, and the final returned action after
all remaining guards. Early tactical/solo/checkpoint returns have no fabricated
chooser event. Later-guard changes are grouped rather than individually attributed.
Forecast arrays are copied into immutable JSON strings before workspace reuse.
The trace does not call policies, reset a candidate workspace, or change scores.

```sh
# Add racecraftReviewAudit=true to a separate profile used for one race.
java -Xmx8g -Djava.awt.headless=true -jar theoreticRacing.jar \
  --auto --track circle --props results/review-audit.properties \
  --seed 2 --log results/circle.log 2> results/circle.stderr
python3 docs/experiments/racecraft-review/audit.py results/circle.stderr
```

Use one race per input file; duplicated root keys are rejected rather than
silently aggregating concatenated batches. The summarizer separates proposals
from executed changes and counts final overrides. It never claims these counters
are place gains. Twelve complete-race control checks exercise flags without
slots, slots without flags, and audit-on/off identity for control and all-arms
candidate on Hairpin and Circle. These bounded checks do not replace the fleet.

## 4. Selectively model the rival that can change the contest

The production rollout does not reproduce every car's entire recursive decision
process. Its selected nearby rivals and own continuation use suppressed policies;
other rivals use cheaper proxies. Paying for an entirely stronger world at every
move is not justified merely because the approximation exists.

The implemented `selective` prototype is narrower: require nominally tied
choices and intersecting next-landing envelopes, fix one directly involved rival
for the comparison, and run at most two additional forecasts in which only that
rival's first response uses its stronger chooser and downstream guards. All cars
remain present. A required response that is not reached is unknown, not success.
Only a strict stronger-world improvement with no nominal worsening can switch
the proposal. Subsequent moves replan normally; no second-action commitment or
opponent coalition is manufactured. This is model-conditional, not a universal
proof or a calibrated human-response model.

### Full contingent-prefix continuation: research follow-up, not yet ported

Existing implementation reference:
`d3f699c7d68da4444a1af2294e974f644c956155`, `docs/contingent-prefix.md` and the
chooser laboratory on `work/contingent-prefix-prepared-20260921`. Reuse that
machinery rather than write a second unbounded planner. Do not merge its older
rule/baseline changes wholesale into the current champion.

1. Capture the nominal and stronger first reply of the same contesting rival;
   deduplicate identical replies. Report response disagreement and whether it
   actually changes a legal continuation or relative-order forecast.
2. Within each resulting world, search the baseline second focal action plus
   a bounded number of alternatives on that world's own board. Require a
   strict improvement in one declared world and no worsening in either;
   unknown or incomparable plans keep the incumbent. Each rival pursues its
   own place and time, never a coordinated anti-mover objective.
3. Reuse exact prefixes only when every car, roster identity, progress ledger,
   classification, alive/occupancy state, next slot/round, clock, game geometry,
   grid-rule context, policy mode, horizon and first-response choice match.
   Deep-copy mutable arrays and replay the original ordered logical budget
   charges so a performance-only cache does not secretly enlarge the search.
4. Verify full-versus-resumed traces, budget frontiers, slot orders and referee
   transitions before measuring speed. Keep additional search financed by saved
   work as a separate arm. Measure returned first actions and observed second
   actions, not just internally proposed plans.

The campaign's existing contingent-search results did not justify its CPU cost.
The specific new question is whether a narrower activation condition and the
post-278 pipeline change that trade-off. No renewed benefit is assumed.

## 5. Learn joint rollout-endpoint value: explicit research specification

**Not implemented or trained in this PR.** No learned weights, inference model,
fake training set, or claimed win-rate improvement is shipped. The audit provides
forecast observations for investigating the question, not training labels.

Two endpoints with the same solo distance can differ materially because one car
controls an exit and the other can be repeatedly denied it. The proposed target
is the eventual own result conditional on the whole endpoint and specified
continuation policy, not imitation of the current chooser's forecasts or direct
unconstrained action replacement.

### Data and labels

Replay each sampled root and each candidate through the full referee, then run
complete counterfactual tails with pinned policies to obtain own finishing place
and own move count. Save losing actions and crashes as well as selected moves;
otherwise the labels are selected-policy biased. Carry all live and retired cars,
positions, velocities, full progress/grid flags, classification/finish history,
turn cursor and clock, geometry and rule identity. Bind samples to baseline,
JAR, profile, track, seed, roster/seat, root identity and action hashes.

Current exported endpoints say `replayReady:false`: they omit parts of the full
classification/cursor ledger and must NOT be fed directly to a referee or used
as completed labels. A full-state exporter and independent replay checks are a
prerequisite. Actual scored finishes outrank model estimates; no model may
reinterpret a crash as a legal finish.

### Model and evaluation

Start with a small, inspectable residual endpoint model on top of the exact solo
value, using relative position/velocity, turn order, progress, contested landing
access and exit multiplicity. Use separate place and conditional-time outputs
with a lexicographic comparison, not a weighted sum that can exchange a place
for speed. Detect unavailable/out-of-domain inputs and fall back to the existing
chooser. Do not replace physical legality, certified wins or existing safety
checks with a learned prediction.

Split by track family and entire race/root before tuning; sibling actions and
mirror assignments from the same root must not leak into held-out data. Keep
synthetic track families and a fresh seed window for final evaluation. First
report shadow prediction error and decision disagreement; then run a separately
gated on-policy candidate. Prediction accuracy alone does not clear a promotion.
After every promotion collect fresh on-policy counterexamples rather than
assuming the old continuation distribution still holds.

## Promotion and measurement checklist

Run each independent arm against the same pinned post-278 control, then the
selected combinations against the new corrected baseline. Record hashes and
actual completed evidence, not only the proposed run plan.

- Supported JDK build with warnings as errors; every Java contract; replay,
  headless and owner-rule tests; all goldens and every `ai1_*_regression.py`.
  Never re-freeze expectations merely to conceal a control regression.
- Mirrored two-, four- and eight-car fields on legacy, informed and scattered
  starts, using the reference `-Xmx8g`, fresh seed windows and all fleet courses.
  Use a fresh manifest-bound directory for every changed experiment.
- One candidate against the champion field, rotated through every seat and
  paired with the same-seed all-champion race (`run_1vfield.py`), plus the required
  homogeneous fleet grids. Report per-track and aggregate own place, own time,
  candidate versus champion crashes, CPU per decision and memory.
- Evaluate own place first and own time second. Field moves and field crashes
  are descriptive, not independent vetoes. A rival crash caused by a faster,
  better-placed candidate is legitimate racecraft. Report uncertainty and
  held-out results; do not reject or promote from a few attractive examples.

Suggested order: crossing continuity, retained proof frequency, cache/anytime
ablation, final-action audit, post-278 rank/diversity re-tests, selective-response
activation, full contingent-prefix experiment, and finally endpoint learning.
This PR preserves that entire plan without pretending all research has been run.
