# theoreticRacing — instructions for coding agents

The live authority for the racing AI campaign is `racing-memory.md` (newest
entry first). Read its top entries before changing `src/tr/logic/RaceAi*.java`
or the maps in `Reachability.java` / `OptimalPotential.java`, and add an entry
there for every change you push: what it does, and what it measured.

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

Consequences for measurement: the fleet's summed-moves and crash counters are
field metrics and must not on their own reject a candidate whose winners cost
their followers time or crashes. Where a change touches how cars interact,
compare lexicographically -- finishing places of the cars that run the
candidate against cars that run the champion, in the same races -- and read
the field counters only as a safety instrument (a crash the candidate's own
car suffers is still a loss for that car).

## Measurement discipline

- Any change that can alter a decision gets a fleet grid before it ships
  (`tracks/fleet_grid.sh`; 730 races a seed slice), on random starts
  (`aiStartPlacement=legacy`, the headless default), computed starts
  (`aiStartPlacement=informed`) and scattered starts (`aiStartPlacement=scatter`).
  A few dozen races rank candidates; they do not clear them.
- Correctness fixes that the fleet clears ship even at noise cost; pinned
  artifacts are re-frozen from measurement, with the reason beside the number.
- Build with `sh build_main.sh` (JDK 25, warnings are errors); run
  `sh run_tests.sh`, `python tests/golden_races.py` and every
  `tests/ai1_*_regression.py` before publishing.
- Never edit `user.properties`; never regenerate fleet tracks in place; do not
  change tooling under `tracks/` while a fleet grid is running, the runner
  binds it into the grid's manifest.
