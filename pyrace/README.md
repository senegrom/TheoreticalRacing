# pyrace — learned racing AI for theoreticRacing

All Python bits for training a neural network to drive the vector-racing game
live here. The Java game remains the UI / reference engine; Python is headless.

## Goal

The hand-crafted champion **AI2.9** drives the reachability-optimal racing line,
so it is at the *pace floor* — a network will not out-drive it on empty-track lap
time. The value of learning is in **multi-agent racecraft** (traffic, blocking,
opponent interaction), the exact frontier the hand-crafted scoring terms handle
crudely. A transformer with **attention over the 8 cars** is the natural fit:
permutation-invariant, variable car count, and attention *is* the "which
opponents matter" computation the heuristics approximate.

## Plan / milestones

1. **Engine** (`engine.py`, `track.py`) — a headless Python port of the game
   physics (step, legality, finish crossing, crash), matching the Java engine.
   Validated by replaying a Java game log and confirming identical trajectories.
   *(this commit — first cut + validation harness)*
2. **Reachability features** (`reachability.py` or a Java export) — the exact
   `turnsToFinish(x,y,vx,vy)` map. Either re-port the reverse-BFS or export it
   from Java for guaranteed match. This is the key per-state feature (frees the
   net from learning basic navigation).
3. **Data pipeline** — harvest `(full board state, AI2.9 move, track)` tuples by
   running the Java game with richer logging; a Python loader yields training
   pairs for behavior cloning.
4. **Model** (`model.py`) — a set-attention transformer: ego features + one token
   per opponent → 9-way move logits (+ a value head later for RL).
5. **Behavior cloning** (`train_bc.py`) — clone AI2.9; validate the clone reaches
   ~AI2.9 strength on the existing `tracks/bench_ai.py` harness (export weights to
   Java, or evaluate in this engine).
6. **RL self-play** (`train_rl.py`) — fine-tune the clone to *exceed* AI2.9. This
   is where the novel upside lives (learned traffic/racecraft).

## Layout

- `track.py` — parse `.track` files, derive finish line / forward direction /
  start zone / corridor polygon.
- `engine.py` — `RaceState` + move resolution (faithful to Java `commitMove`:
  finish checked first and unblockable, else crash if illegal, else move;
  game ends when N-1 of N cars are done).
- `validate_engine.py` — replay `last_game.log` moves through the engine and
  assert the per-move legal/crash/finish verdicts match Java.

Note: the track-generation tooling in `../tracks/*.py` stays there (it is
track authoring, a separate concern from AI training).

## Engine facts (ported from `src/tr/logic/RaceGame.java`)

- State per car: `(x, y, vx, vy)`; 9 accelerations `(dx,dy) in {-1,0,1}^2`;
  a valid move keeps `|vx|,|vy| <= AI_MAX_SPEED = 12`. `newVel = vel + accel`,
  `newPos = pos + newVel`.
- Track = two border polylines (left, right). Finish line = `(left[-1],
  right[-1])`; a crossing counts only if the move heads in the racing direction
  (`finishFwd` = normalized average of the last border segments). Start line =
  `(left[0], right[0])`; the start zone is a `startZoneWidth = 2` deep band off it.
- Corridor polygon = `left + reversed(right)`, closed. Legality: destination and
  ~2-per-unit interior samples must be inside `corridor ∪ startZone`, AND the
  move segment must not cross either border polyline.
- Move resolution (`commitMove`): if it crosses the finish → finish (unblockable);
  else if illegal (outside corridor / crosses border / lands on another car) →
  crash, placed `N - finishedLast`; else normal move. Game ends when
  `finishedFirst + finishedLast >= N - 1`; the last car gets `finishedFirst + 1`.
