#!/usr/bin/env python3
"""Materialize behavior-exact forward-first finish testing.

A finish requires both segment intersection and a positive heading dot product.
The old order always paid for Line2D.linesIntersect first.  Because all inputs
are finite board coordinates, rejecting a non-positive dot product before the
intersection is logically identical and can skip the sampled hotspot.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()
old = """\tboolean crossesFinish(final double x1, final double y1, final double x2, final double y2) {
\t\tif (!Line2D.linesIntersect(finishLine.getX1(), finishLine.getY1(), finishLine.getX2(), finishLine.getY2(), x1, y1, x2, y2))
\t\t\treturn false;
\t\t// Only a forward crossing counts (move heads in the racing direction).
\t\t// A zero-length or backward move across the line is not a finish.
\t\treturn (x2 - x1) * finishFwdX + (y2 - y1) * finishFwdY > 0;
\t}
"""
new = """\tboolean crossesFinish(final double x1, final double y1, final double x2, final double y2) {
\t\t// Only a forward crossing counts.  Test this cheap necessary condition
\t\t// before the substantially dearer Line2D predicate; conjunction order
\t\t// cannot change the result for finite board coordinates.
\t\tif ((x2 - x1) * finishFwdX + (y2 - y1) * finishFwdY <= 0)
\t\t\treturn false;
\t\treturn Line2D.linesIntersect(finishLine.getX1(), finishLine.getY1(),
\t\t\t\tfinishLine.getX2(), finishLine.getY2(), x1, y1, x2, y2);
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
race.write_text(source)
print("materialized forward-first finish test")
