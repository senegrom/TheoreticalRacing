# Racing strategy experiments

Research branch: `work/racecraft-strategies-20261008`.
Base champion: `b907126230b0c5a71c91b62430fa32469e58b895`.
Recovered experimental foundation: `6ec439ae29ca037b013451c368c3d23799e834e5`.
These are game-playing experiments, not promoted policy or performance results.

Use a private properties file:

```properties
candidateSlots=1,3,5,7
racecraftNext=suffix-manoeuvres,response-strategy,place-certificates,forced-sequence,continuation-policies,ordered-blockade
racecraftStrategyNodes=12000
racecraftForcedMoveCap=16
racecraftManoeuvreNodes=192
racecraftManoeuvreDepth=4
```

All additions require candidate slots and real root decisions within the existing
20-cell traffic boundary. Zero strategy nodes disables the six additions. The
suffix flag enables the previous manoeuvre backbone; the response flag enables
its adaptive fallback. Other earlier flags remain available independently.
Computed starts, maps, tracks and user.properties are unchanged. The current
301a pace-tie rule and 301c danger-search changes are preserved.

## Same-first-action suffixes

The graph retains different intermediate histories, including two continuations
that start with the nominal move. Root expansion is round-robin within the graph
budget. At most three completed paths are offered, not unfinished paths. Each is
re-evaluated with reacting opponents under the same model. A better suffix can be
installed even when the immediate action does not change. Stored suffixes still
require an exact observed-state match and a fresh evaluation at the next turn.

## Executable response strategies

The adaptive search returns a bounded table of verified response masks. Each
opponent reply has the existing required number of progress-making answers.
Incomplete branches do not enter the table. Committing the proved first action
installs its table; a query alone does not. At the next matching state the normal
action is retained when it is certified. Otherwise a fresh proof may admit it
without increasing the remaining horizon; failing that, a certified alternative
is selected. These are finite-horizon guarantees, not whole-race guarantees.
Immediate finishes and the outer solo rule retain precedence.

Trees contain at most 256 clock-keyed decision states. The rc6 snapshot format
adds response tables to the existing per-slot memory. Java and Python validate
lengths, masks, horizons, escape counts and sorted unique keys. The complete cf4
request digest includes this memory. Undo and detached simulations copy immutable
tables. Earlier rc3/rc4/rc5 snapshots remain supported, but captures remain tied
to their original executable. Strategy records are internal game policy state,
not independently authenticated proof objects.

## Three-car finishing-place search

The bounded solver considers complete referee transitions in actual turn order,
including existing classifications and progress. Each opponent's physical moves
are considered, including legal moves that the solo map cannot price. Unknown
search results do not imply losses. A completed result is retained when later
exploration runs out of budget. The initial three-car experiment activates near
the finish and nominates one useful action to the ordinary chooser. A guaranteed
second does not automatically outrank an unproved opportunity to win. Bounds are
conditional on executing the strategy found by the search.

## Forced-sequence extensions

After established shorter tactics fail, the two-car experiment distinguishes
branching decisions from physically forced moves. Only a unique physically legal
action counts as forced, never merely a unique preferred action. All physical
moves still count toward elapsed time and a separate move cap. The node budget
remains bounded. Shared progress-based timeout classification is used.

## Own-continuation portfolio

A chooser/pace disagreement activates comparison under two controllable own
prefixes: ordinary scorer and solo pace. Both candidate first actions receive
both profiles. Opponents use the same reactive scorer throughout. Completed
prefixes are compared at one common twelve-own-move horizon and final response
cycle. The winner retains its concrete suffix as policy memory. Human-roster or
unavailable-map cases abstain. Subsequent danger checks still apply.

## Ordered blockade feasibility

The existing matching test remains first. With three or four live cars, a
bounded one-cycle search checks whether the proposed covering moves are jointly
possible in actual turn order, including occupied cells and retired cars. Only a
completed impossibility result clears the old objection. Incomplete work leaves
it unchanged. This is not a new general avoidance penalty.

## Tests and evaluation

StrategyResearchTests covers referee parity, nominal-first suffixes, response
execution and memory, absolute place bounds, a seven-own-move forced-line witness,
reversed-order blockade fixtures, portfolio restoration and flag controls.
Python checks response-memory structure and request binding. Complete-race
controls and exact counterfactual control suffixes are functional checks, not
performance measurements. Executed results belong in validation.json.

Evaluate each arm separately before combinations, using mirrored fields,
random/computed/scattered starts, held-out seeds and the lone-entrant comparison.
Own finishing place is primary, own time secondary; report computation cost.
No improvement or promotion is claimed without those measurements.
