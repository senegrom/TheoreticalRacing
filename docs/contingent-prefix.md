# Response-contingent plans and exact prefix reuse (research, 2026-09-21)

This branch combines the published chooser laboratory (`262649d`) with the
current master's owner rule (`3466471`). It implements two additional ideas:
response-contingent second actions and reuse of identical simulation prefixes.
It does not add the proposed learned rollout-endpoint evaluator. Nothing here
is a racecraft promotion or a replacement of master.

## Quiet-mode prerequisite

There is one authoritative 20-Chebyshev-cell boundary. Outside it, finite exact
solo descent runs **before** tactical/checkpoint/traffic precedence. Disabling
only the chooser had left the old 40-cell early return and admitted a three-turn
worse checkpoint touch on the unchanged two-lap Circle witness. The correction
uses the complete lap potential, or the point-to-point finish map; an unavailable
exact map remains unavailable, not a claimed proof. The chooser is still blocked
outside 20 even when exact preparation is unavailable. No distance constant is
tuned. Referee transitions, tracks, user settings, and golden expectations are
unchanged. This correctness correction can intentionally alter default traces;
experiment-off identity is measured against this **corrected** branch baseline,
not asserted against the buggy parent.

The regression exercises the Circle witness, valid road cells at distances
19/20/21/39/40/41, and the corresponding one-car control. The exact witness goes
from NE (one move plus remaining potential = 32) to SE (29, equal to the initial
potential). Choosing a move never changes live progress.

## Independent controls

Both `candidateSlots` and `chooser.experiments` are needed, as in the laboratory.

| Flag | Meaning |
| --- | --- |
| `contingent` | Compare two declared models of one rival's first reply, adapting the second focal action separately in each resulting world. Implies setup search. |
| `prefix` | Reuse complete prefix checkpoints before second-action branching. Requires `setup` or `contingent`. Does not change the search tree or logical budget. |
| `terminal` | Existing optional resolved place/time ranking within each world's plans. |

`contingent` is kept separate from `aware`, `student`, `assist`, and the legacy
insertion controls: otherwise several world-model changes would be confounded.
`setup,prefix` is the independent pure-optimisation arm for the existing setup
search; existing `setup,aware,prefix` also supports exact prefix replay.

```
python tracks/chooser_lab.py profile --experiments contingent \
  --rounds 12 --budget 16000 --move-budget 32000 --setup-width 3 \
  --out results/contingent.properties
python tracks/chooser_lab.py profile --experiments contingent,prefix \
  --rounds 12 --budget 16000 --move-budget 32000 --setup-width 3 \
  --out results/contingent-prefix.properties
python tracks/chooser_lab.py profile --experiments setup,prefix \
  --out results/setup-prefix.properties
```

Write new profiles, never `user.properties`. Generated slots are empty;
`tracks/promotion_pair.py` supplies the complementary assignments for screening.
The larger budgets above are illustrative research limits, not tuned defaults.
No model is trained or downloaded for these arms.

## A plan conditioned on responses, not an opponent coalition

The initial, bounded shortlist is retained. The root's physical interaction
graph selects one directly involved rival, fixed across initial candidates.
All other cars remain on the board with the existing forecast policies.

For each first move, the ordinary simulated reply is compared with the action
that this rival's own **bounded stronger chooser and downstream guards** select
on that same board. This is a declared policy contrast, not the worst legal
acceleration for our car, a human-response probability, or a universal proof.
Only that rival's first response changes. Identical replies share a scenario.
A missing/unreached required response remains unknown and prevents a switch.
Timeout/terminal scenarios use the same referee rules.

After each response and intervening moves, the focal car's original continuation
and up to `setupWidth-1` legal second actions are evaluated on that world's own
state. The two worlds do not share an assumed second action or cached opponent
trajectory. Illegal actions actually selected by a model retain their referee
consequences; a hypothetical car is not removed because a heuristic dislikes it.

Without justified probabilities, selection is a partial ordering: a candidate
must improve at least one declared world and worsen neither relative to the same
baseline first move. Competing/incomparable model outcomes keep the champion.
Resolved outcomes compare actual simulated place then own moves. Finite unresolved
forecasts compare at the same horizon; unresolved/terminal pairs or missing route
values are not silently declared equal. These are model-conditional comparisons,
not guarantees about real opponents. A more cautious partial ordering may itself
lose places and requires measurement like any other policy change.

Only the first move is proposed, at the existing chooser location **before**
pace/guard/confirmation stages. The next real decision replans using the observed
board. There is no hidden commitment, cooperation, or reward for delaying rivals.
Whether the conditional follow-up is actually executed remains an audit question.

## Exact reusable prefixes

Each scenario captures a private checkpoint immediately before the first second
focal-action trial. It stores every car's simulation position/velocity, lap/gate
state, alive state, fixed faithful-rival membership, clock and next slot/round,
plus the detached classification ledger, own-move counts, policy-upgrade flags,
reply observations and already-recorded trace. Mutable arrays are deeply copied.

Sibling second-action trials restore independent copies. Prefixes from different
rival-response scenarios are not interchanged. A checkpoint is bound to its exact
root board, player roster identities, game/configuration, geometry/cache identity,
lap rules, initial action, horizon, policy modes and reply choice. Changed root
state or mode is rejected. Nothing is persisted to disk, keyed only by our position,
or reused across live decisions. Scratch memo epochs may advance differently;
the invariant is semantic equivalence, not equality of incidental cache counters.

The budget records the ordered logical policy/move charges in the prefix. Reuse
replays those charges in order, including failure at the same limit. It therefore
saves physical calls without financing more branches or changing which comparison
completes. Reinvesting savings in extra search is deliberately NOT part of this
optimisation. `reusedPolicies`/`reusedMoves` and `physicalPolicies`/`physicalMoves`
are separate from the unchanged logical `policies`/`moves` audit counts. These are
call/slot counters, not wall-clock latency claims; copying/checking prefixes also
costs time and memory. Per-decision storage is bounded by the configured horizon,
shortlist and work limits.

## Diagnostics and tests

`CHOOSER_AUDIT` adds a `contingent` object with the fixed rival, declared models,
per-first-action plans, each observed reply and selected follow-up, and reasons
such as `models-agree`, `no-dominating-plan`, `unavailable-response` or `budget`.
The nominal plan remains in `selectedPlan` for compatibility with the existing
forecast/execution audit; the alternative scenario is not claimed to have happened.

```
sh run_tests.sh
sh build_main.sh
python -m unittest discover -s tests -p 'test_*.py'
python tests/contingent_prefix_regression.py --heap=-Xmx8g --out results/contingent-contracts
python tests/golden_races.py
for test in tests/ai1_*_regression.py; do python "$test" || exit; done
```

Java contracts compare full and resumed forecasts across both turn orders,
point-to-point and multi-lap courses, several horizons, chooser-aware upgrades,
forced follow-ups and budget frontiers. Complete traces are independently replayed
through the referee. CLI contracts compare nine complete races, including disabled,
zero-budget and exhausted controls; cached/uncached comparisons require equal
full traces, plans and logical counters. Eight Python contracts cover flag/profile
validation and source preservation.

Local supplementary OpenJDK 21 results and supported-JDK CI results must be reported
separately. The branch workflow preserves corpus failures rather than rewriting
expectations. The quiet-rule correction can change frozen trajectories even when
finishing results are unchanged; those differences and the complete mirrored
place battery remain release work. No full fleet, measured place improvement,
production speedup, endpoint-value learner or new default-policy promotion is
claimed by these bounded functional tests.
