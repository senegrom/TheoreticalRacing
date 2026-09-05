# Move oracle, version 2

The headless oracle uses the same side-effect-free `RaceGame.evaluateMove`
transition as the live referee. Run with `--query-moves - -` for line-buffered
stdin/stdout. Startup diagnostics precede replies; `quit` closes the process.
Use the same track, roster, kinds and `laps` properties as the recorded race.

## Full board requests

```
v2,MOVER,TURN_COUNT,TOTAL_LAPS;x,y,vx,vy,finished,lap,gate;...
```

MOVER is the zero-based array index. TURN_COUNT is the number of already
committed global moves, not the mover's personal move count. TOTAL_LAPS must
match the loaded game (including the fallback to one lap on open tracks).
There must be exactly one seven-field group per configured player. `finished`
is zero for a live car and positive for a retired car; `lap` counts completed
laps, and `gate` is 1 for CP1, 2 for CP2, or 0 for S/F next. Live cars must
have distinct in-grid cells and velocities in the AI planning domain.

The entire request is validated before mutation. Each accepted request resets
all players' progress, positions, velocities and retired markers plus the race
clock; no omitted state is inherited from previous requests. Trace-only history
is cleared. Malformed requests terminate the headless process nonzero.

## Responses

```
v2;dx,dy;MASK;STATUS,lap,gate,checkpoints|... (nine transition tokens)
```

Both MASK and the transition tokens follow `NW,N,NE,W,NONE,E,SW,S,SE` order.
The mask is a quick classification: `F` is an actual terminal finish; `X` is
illegal geometry or an out-of-domain velocity; `B` is a live-body collision;
`D` is a legal move with a reachability-dead landing; `A` is a legal alive
landing; and `T` is the race-turn timeout. **D is not an immediate crash.**

Each candidate also has an authoritative STATUS (`OK`, `LAP`, `FINISH`,
`CRASH`, or `TIMEOUT`), resulting lap/gate, and checkpoint bit mask (1=CP1,
2=CP2). A non-final lap is not `F`. The run-up to an actual finish must be
legal; the intentional exemption for the part beyond the line remains.
Timeout precedence matches the live race, including its existing threshold.

The attempted destination is `(x+vx+dx,y+vy+dy)`, with resulting velocity
`(vx+dx,vy+dy)`. After a terminal event the live state retires the player at
`(-100000,-100000)` with zero velocity. Race logs record the attempted move,
not that retired sentinel. Full replay must preserve the clock, lap and gate
for all players after every transition and stop under the referee's
last-survivor rule (zero survivors for a solo race, at most one otherwise).

## Simulation requests

```
sim2,MOVER,ROUNDS,WORLD,RIVAL_CAP,TURN_COUNT,TOTAL_LAPS;...seven-field groups...
```

WORLD is `smom`, `scorer` or `true`. The mover is already at the queried
landing. These requests initialize their own decision frame and work before
any move query; they return `V=...;tier=...;thread=...;snug=...`.

## Legacy protocol

`MOVER;x,y,vx,vy,finished[,gate];...` and the original `sim,...` header remain
accepted. Omitted lap, gate and clock fields are explicitly reset to lap 0,
CP1 (or gate 0 without lap gates), and clock 0. Replies keep the old
`dx,dy;MASK` shape. Legacy `F` now means a legal actual finish, not every
geometric S/F crossing. Legacy responses have no checkpoint/lap transition
payload and must not be used for complete multi-lap reconstruction.

Python `ReplayBoard`, `CandidateMask`, `reconstruct_board(..., complete=True)`
and `Oracle.ask` implement V2. `oracle_roll.verify` compares global move
indices, player, acceleration, pre/post position and velocity, exact event
kind and checkpoint marks, and fails on incomplete or prematurely ended
windows. A replay round means one full cycle of player slots from the chosen
mover, skipping retired players.
