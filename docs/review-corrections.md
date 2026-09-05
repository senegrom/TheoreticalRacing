# Review corrections after round 223

These are rule/instrument corrections, not a new tuning or promotion of the
champion's scoring heuristics.

* The referee awards a finish only when the pre-line approach is legal.
  An illegal finishing attempt no longer bypasses the crash branch.
* Finish approaches test wall-segment intersections before the exact finish
  parameter, including collinear overlap and border vertices. Existing
  containment checks remain; post-line wall contact is still exempt.
* AI terminal shortcuts use the same legal-finish predicate. This prevents
  the chooser from repeatedly selecting a crossing the corrected referee
  would now reject. Reachability cache semantics advance from 14 to 15.
* The move oracle uses the referee's transition and V2 complete board state.
  Queries do not inherit lap/gate/clock state. Standalone simulation queries
  initialize their own frame. Full replay tracks non-final laps and verifies
  exact outcomes and kinematics rather than merely terminal/nonterminal.
* Fleet runs are manifest-bound, locked, attempt-isolated and validated.
  Only complete successful logs publish resumable markers. Failed/missing
  work returns nonzero, remains retryable, and cannot consume stale logs.
* Gate and robust map cycles now check full-array/set convergence, retaining
  a minimum of three passes. Failure to converge within 128 passes is an
  explicit error, not an accepted provisional map. The existing robust
  passage rule is unchanged. Tests include a cycle needing more than three
  passes and a deliberately oscillating one.

## Why two golden logs change

The old and corrected builds were compared on the same Java 21 runtime.
On `zigzag` seed 4, old finishing moves 530 (p8 SW) and 532 (p6 NW) run
collinearly along a wall before the finish. Seed 22 has the same defect at
moves 521 (p2 SW) and 523 (p5 NW). Ordinary geometry already rejects such
wall overlap, but the sampled finish approach missed it. The corrected
oracle classifies these four old moves as illegal and the AI selects legal
interior alternatives instead.

Only those two golden digests are updated. Total race moves, finishing order,
finishes and crashes are unchanged: seed 4 has 532 moves and seed 22 has 528,
each with seven successful finishers and zero crashes. The other ten golden
fixtures remain unchanged. The thin-notch unit fixtures additionally cover
an illegal approach that falls between containment samples and one that is
already detected but was incorrectly awarded a finish.

Three trajectories within the private-slack pin have corresponding updates.
On frozen Monza seed 30, turn 647 p5 changes NW to N; on seed 145, turn 640
p4 makes exactly the same correction. Each Monza log differs in that single
finishing move only. On Serpentine seed 38, p3 avoids its illegal wall-overlap
finish at turn 819 by changing its two preceding approach moves; nearby p6's
last approach responds. The corrected oracle rejects each old illegal finish.
All three races retain seven finishes, zero crashes, every player's move
count and the same finishing order. Their digests are updated; all remaining
private-slack trajectories and summary/identity assertions stay pinned.

## Validation commands

```
sh run_tests.sh
sh build_main.sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/headless_smoke.py
python3 tests/query_replay_regression.py
python3 tests/golden_races.py
for test in tests/ai1_*_regression.py; do python3 "$test" || exit; done
sh tracks/verify_reach_cache.sh circle 1
```

The new end-to-end replay test records an actual 163-move two-lap race and
verifies its complete transition sequence, final/non-final crossing semantics,
legacy/V2 query-order isolation and standalone simulation isolation. Small
regressions and golden tests do not replace the full expensive promotion
battery; no full-fleet pace improvement is claimed by these corrections.
