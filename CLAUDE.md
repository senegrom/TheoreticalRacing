# theoreticRacing — instructions for Claude Code

The live authority for the racing AI campaign is `racing-memory.md` (newest
entry first). Read its top entries before changing `src/tr/logic/RaceAi*.java`
or the maps in `Reachability.java` / `OptimalPotential.java`.

## Racecraft evaluation rule (decided by the owner, 2026-09-07)

We care about **lexicographic performance**: every car races for its own
finishing position first and its own time second. Judge a policy by how the
cars running it finish, not by the field's summed moves.

- Every agent tries to be as fast as possible. A move by the winner that slows
  the second car is **not** to be punished.
- Forcing a rival into a crash is legitimate racecraft and is **not** to be
  punished. A car that can be forced out has itself to blame for being there:
  the burden is on every car never to enter a state a rival can close.
- **No active cooperation.** The car behind must never let the car ahead win;
  no yielding, no waiting, no team play of any kind.

Consequences for measurement. Where a change touches how cars interact, the
criterion is the head-to-head place comparison: run candidate cars and champion
cars in the SAME races, mirror the slot assignment so grid advantage cancels,
and compare their finishing places (`tracks/head_to_head.py`). A car that
crashes already scores as that car's last place, so mean place prices safety
correctly and needs no separate gate.

The fleet's summed-moves and crash counters are FIELD metrics. They never
veto a candidate. In particular a faster leading car whose pace costs the
second car a crash is an improvement, and a field made entirely of the
candidate is allowed to crash more often than the champion's field. Report
those numbers as description, never as a rejection.

## Measurement discipline (unchanged)

- Any change that can alter a decision gets its own fleet grid before it
  ships (`tracks/fleet_grid.sh` on the AWS box), on random starts
  (`aiStartPlacement=legacy`, the headless default), computed starts
  (`aiStartPlacement=informed`) and scattered starts (`aiStartPlacement=scatter`).
- Correctness fixes that the fleet clears ship even at noise cost; pinned
  artifacts are re-frozen from measurement, with the reason beside the number.
- Never edit `user.properties`; never regenerate fleet tracks in place.
