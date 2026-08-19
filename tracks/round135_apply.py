#!/usr/bin/env python3
"""Materialize Round 135's exact fixed-finish supporting-line reject."""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old = """\tfinal Reachability reach = new Reachability(this);
\tboolean crossesFinish(final double x1, final double y1, final double x2, final double y2) {
\t\tif (!Line2D.linesIntersect(finishLine.getX1(), finishLine.getY1(), finishLine.getX2(), finishLine.getY2(), x1, y1, x2, y2))
\t\t\treturn false;
\t\t// Only a forward crossing counts (move heads in the racing direction).
\t\t// A zero-length or backward move across the line is not a finish.
\t\treturn (x2 - x1) * finishFwdX + (y2 - y1) * finishFwdY > 0;
\t}
"""
new = """\tfinal Reachability reach = new Reachability(this);
\tboolean crossesFinish(final double x1, final double y1, final double x2, final double y2) {
\t\t// Round 135: almost every simulated move lies strictly on one side of
\t\t// the fixed finish line. Two same-sign oriented areas prove that the
\t\t// move segment cannot intersect the finish segment, avoiding the general
\t\t// Line2D relative-CCW machinery. Zero, opposite-sign, NaN and degenerate
\t\t// cases retain the exact original predicate, so this is a one-sided
\t\t// rejection only and cannot alter a finish verdict.
\t\tfinal double fx1 = finishLine.getX1(), fy1 = finishLine.getY1();
\t\tfinal double fdx = finishLine.getX2() - fx1, fdy = finishLine.getY2() - fy1;
\t\tfinal double side1 = fdx * (y1 - fy1) - fdy * (x1 - fx1);
\t\tfinal double side2 = fdx * (y2 - fy1) - fdy * (x2 - fx1);
\t\tif ((side1 > 0.0 && side2 > 0.0) || (side1 < 0.0 && side2 < 0.0))
\t\t\treturn false;
\t\tif (!Line2D.linesIntersect(fx1, fy1, finishLine.getX2(), finishLine.getY2(), x1, y1, x2, y2))
\t\t\treturn false;
\t\t// Only a forward crossing counts (move heads in the racing direction).
\t\t// A zero-length or backward move across the line is not a finish.
\t\treturn (x2 - x1) * finishFwdX + (y2 - y1) * finishFwdY > 0;
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
race.write_text(source)
print("materialized Round 135 fixed-finish supporting-line reject")
