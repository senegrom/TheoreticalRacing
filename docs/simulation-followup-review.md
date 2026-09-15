# Simulation branch follow-up (2026-09-14)

> Landed on master as round 248 (2026-09-15), measured together with the
> 2026-09-12 repairs it follows up; see racing-memory.md. The branch-status
> remarks below are historical.

This fixes the review of `55a63effcab7880fea38bc51b828fab861b319b8` on
`work/simulation-boundary-fixes-20260913`. It does not merge or rebase the branch
onto master, and it does not promote an AI policy or change golden expectations.
The prior four boundary repairs remain in place.

## A legal blockade is a move, not a retirement

`scorerMoveOverState` now returns the actual scorer-selected action, even when
the solo reachability map labels its landing dead. The surrounding rollout
applies the referee transition to that action. The map cannot veto a legal
blockade that wins before the moving car ever needs its next turn. Actual
illegal actions still crash; the repair does not replace them with safer moves.

When an approximate move model finds no preferred action, the rollout looks
for a deterministic physical legal continuation (finishing first, otherwise
first legal direction). All nine physical accelerations are considered. Only
an actual illegal selected action, a real timeout, or the absence of every
physical legal action can retire the projected car. This fallback is an
approximate continuation, not a claim that the rival's real policy was queried.

The unchanged Hairpin witness now predicts P1's loss, not immediate survivor
classification: P2 takes NONE from (15,22), velocity (2,2), to (17,24), boxing
P1 at (17,25), velocity (1,-2). The tests replay the actual referee and check
both slot orders, suppressed/full rival scorers, self models, and restoration
of the live state. A separate proxy witness has legal but no map-alive actions;
it must retain the body. High physical speeds and genuine retirement controls
are covered too.

## The private-lane mover has a progress ledger as well

A proof session snapshots the mover's pre-candidate position and lap/checkpoint
ledger. Each candidate applies its own referee transition from that snapshot;
trials cannot accumulate one another's gate credit. Illegal occupied candidates
are rejected. Terminal finishes preserve the referee's landing exemption.

All subsequent mover paths carry detached lap and gate state. Only a genuine
`MoveResult.finishes()` result bypasses the occupancy obligation. Non-final or
out-of-order crossings remain ordinary legal moves, with both occupancy and
continued-map-aliveness obligations. The existing pace-ordering heuristic,
search horizons, rival frontier cache and fail-closed node budget are unchanged.

The unchanged two-lap Circle example rejects both approximate and exact private
certificates: all nine next destinations geometrically cross the line, but none
finishes and every destination is reachable by the rival. Final-lap controls
remain terminal; owed checkpoints do not disappear. Additional tests cover
candidate gate credit, repeated trials, occupied candidates, recursive ordered
gate transitions, and 110 valid sampled candidates checked against independent
exhaustive short-horizon continuations (90 accepted certificates).

## Documentation and regression scope

`web/README.md` now describes every master push building a tested artifact and
CI calling the browser workflow, with PR-only path filtering and the existing
freshness/test gates. No workflow or publication permission is weakened.

`SimulationFollowupTests` is invoked by `run_tests.sh`. Its blockade, proxy and
mover-progress modes fail against the previous branch tip and pass with these
repairs. The previous `SimulationBoundaryTests`, timeout Undo checks and duel
contracts are retained. The supported-JDK validation workflow records actual
completed test outcomes separately; a successful transport step is not testing.

## Release boundary

The earlier branch has three documented frozen-trace differences. This change
leaves every golden expectation unchanged, and validation must report all
remaining/new mismatches rather than ignore or automatically re-freeze them.
Golden comparisons are diagnostic for this review branch, not a waived release
gate. Full mirrored-fleet evaluation and integration with the newer master
policy remain prerequisites for release. Finishing place remains the campaign
criterion; aggregate crash counts are descriptive, not a candidate veto.
