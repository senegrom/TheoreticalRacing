#!/usr/bin/env python3
"""Pin round 348's margin by a decision specimen.

Round 348: where the deciding car races a small group -- more than two cars
live, at most three live rivals within twenty cells of it -- chooser landings
whose forecast verdicts are equal go to the larger margin (RaceAi.ppMargin: how
far the forecast leaves the rivals behind the mover, or the mover behind them),
and only equal margins to the score's order. The goldens and the outcome pins
hold races the rule changes; this pin holds one real decision in which the
margin takes the tie (MARGIN_SPECIMEN below), as tests/decision_specimen.py
describes: the race's summary, its trajectory digest and the decision's line.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
import decision_specimen  # noqa: E402

# Zandvoort s1, the live track, eight AI2 cars, one lap: at turn 390 p6, on its 49th move, stands at (82,75) with
# v(9,1) and three live rivals within twenty cells of it: p8 beside it on (83,75), p7 on (89,76) and p4 on (100,76).
# Two of its landings carry the same verdict, six rivals projected to finish before it and its own finish projected
# in round 89: NONE, to (91,76) at v(9,1), which the score puts first (88.67 against 88.69), and W, to (90,76) at
# v(8,1). In NONE's forecast p8, the one car projected behind p6, finishes in round 89 too; in W's it finishes in
# round 90. The margins are -23 and -21, and the chooser takes W: p6 lifts where it would have held its speed, and
# the car behind it loses a round in the forecast. A print build of the promoted round (2026-11-22) races the
# promoted jar's race and prints the decision, NONE to W, margin -23 to -21, the only one of its kind in the race;
# its twin, the margin off in top-level decisions only (forecasts keep it), races that race through turn 389 and
# plays NONE at turn 390. The race has seven finishers and no crash: p2 wins on its 135th move, p3 and p4 follow on
# their 136th and 137th, p5 and p6 on their 138th and p7 and p8 on their 139th, and p1 is the car still running at
# the end, after 139 moves (1,101 turns). The twin's race ends in the same classification on the same moves: the
# specimen shows that the margin acts, not that it pays.
MARGIN_SPECIMEN = decision_specimen.Specimen(
    "zandvoort", 1, (7, 0, [135, 136, 137, 138, 138, 139, 139]),
    "1e3ccce1d1fd013a77653692d47db163885e30307607c10f7b95273d69f7d648",
    "390 p6 AI W v(9,1)→(8,1) (82,75)→(90,76) ok",
)


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    decision_specimen.check("margin", MARGIN_SPECIMEN)
    print("AI1MarginRegression: OK (decision specimen pinned on Zandvoort s1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
