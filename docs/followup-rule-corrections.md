# Follow-up: lap-aware search and exact geometry

These corrections follow the review of `a0710ff`. They change rule handling,
not scoring constants. Both AI kinds still run the same policy.

## Endgame search

The existing minimax has no checkpoint/lap fields in its state key. It now
runs only when both live competitors owe just their final S/F crossing.
Otherwise the normal lap-aware policy handles the position. This fixes the
Circle counterexample with 99 laps where the exact potential is over budget:
the old minimax chose NW into a wall while calling it a win; the corrected
choice is a legal non-final lap crossing.

## Detached rollouts

Each active rollout owns its positions, velocities, lap/gate ledger and clock.
A proposed initial move advances progress once, whereas a `sim2` query starts
from an already-applied landing. Every subsequent move uses the referee's
transition, and only a real terminal finish removes a car. Continuing lap
crossings still require legal, unoccupied landings.

Nested scorers temporarily install the complete projected board, including
lap/gate and clock state. Player state, scalar decision frames and per-player
frame arrays are restored in `finally` blocks. Per-depth workspaces keep
parent state and proof vectors isolated from nested simulations. Approximate
opponent policies remain approximate; no general claim of perfect prediction
is made. The regression compares each TRUE-model choice with a separate real
policy query on the exact projected board across CP1.

## Exact solo search

`RaceGame.gateEventsOnMove` is the shared allocation-free event specification:
CP1, then CP2, then a forward S/F crossing can all count on one move, matching
the referee's established order. Both exact solvers use it. The reverse BFS
seeds every terminal predecessor (one, two or three events still owed) and
allows up to three events on continuing edges. A final move may land beyond
the grid, but its pre-line approach must be legal. Continuing moves retain
their ordinary legality and bounded state-space checks.

Short distances in the potential are decoded unsigned, and overflow of that
storage is an explicit error rather than a negative distance or false zero.
Differential tests compare both solvers with forward BFS over referee results,
including a real automatically generated CP2/SF pair and two-lap cases.

## Rendering and builds

The race renderer receives a transformed copy of the referee's actual corridor
and finish segment. Lap holes, the closure band and fractional finish endpoints
are preserved; the renderer no longer independently constructs a single polygon
or uses the legacy border-tail finish in lap mode. Tests check every grid cell
of an automatically generated circuit against the painted shape.

The build checks the command exit status and parses an anchored `javac` or
`jar` version line. JVM option banners no longer masquerade as the JDK version;
malformed versions and failed probes fail closed. JVM options remain enabled
for compilation and packaging.

## Regression commands

```sh
sh run_tests.sh
JAVA_TOOL_OPTIONS=-Xmx2g sh build_main.sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/headless_smoke.py
python3 tests/query_replay_regression.py
python3 tests/lap_progress_regression.py
python3 tests/golden_races.py
for test in tests/ai1_*_regression.py; do python3 "$test" || exit; done
```

The golden and champion fixture expectations are not rewritten by these fixes.
Targeted rule contracts and the existing corpus do not replace the expensive
whole-fleet promotion battery. No fleet-wide pace improvement is claimed.
