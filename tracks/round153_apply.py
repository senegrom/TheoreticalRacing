#!/usr/bin/env python3
"""Materialize an exact fixed-finish supporting-line rejection.

For integer game moves, two endpoints strictly on the same side of the fixed
finish line cannot intersect its segment.  That one-sided test rejects the vast
majority of simulated moves before Java's general Line2D predicate.  Zero,
opposite-side, collinear and degenerate cases retain the original predicate and
forward-direction check unchanged.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old = """\tLine2D\t\t\t\tfinishLine;
\t/** Unit vector of the racing direction at the finish line. A move only
"""
new = """\tLine2D\t\t\t\tfinishLine;
\tprivate int finishX1, finishY1, finishX2, finishY2;
\tprivate long finishDx, finishDy;
\t/** Unit vector of the racing direction at the finish line. A move only
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\tboolean crossesFinish(final double x1, final double y1, final double x2, final double y2) {
\t\tif (!Line2D.linesIntersect(finishLine.getX1(), finishLine.getY1(), finishLine.getX2(), finishLine.getY2(), x1, y1, x2, y2))
\t\t\treturn false;
\t\t// Only a forward crossing counts (move heads in the racing direction).
\t\t// A zero-length or backward move across the line is not a finish.
\t\treturn (x2 - x1) * finishFwdX + (y2 - y1) * finishFwdY > 0;
\t}
"""
new = """\tboolean crossesFinish(final int x1, final int y1, final int x2, final int y2) {
\t\tfinal long side1 = finishDx * ((long) y1 - finishY1)
\t\t\t\t- finishDy * ((long) x1 - finishX1);
\t\tfinal long side2 = finishDx * ((long) y2 - finishY1)
\t\t\t\t- finishDy * ((long) x2 - finishX1);
\t\tif (side1 > 0 && side2 > 0 || side1 < 0 && side2 < 0)
\t\t\treturn false;
\t\tif (!Line2D.linesIntersect(finishX1, finishY1, finishX2, finishY2,
\t\t\t\tx1, y1, x2, y2))
\t\t\treturn false;
\t\t// Only a forward crossing counts (move heads in the racing direction).
\t\t// A zero-length or backward move across the line is not a finish.
\t\treturn (x2 - x1) * finishFwdX + (y2 - y1) * finishFwdY > 0;
\t}

\tstatic boolean sameStrictFinishSide(final int fx1, final int fy1,
\t\t\tfinal int fx2, final int fy2, final int x1, final int y1,
\t\t\tfinal int x2, final int y2) {
\t\tfinal long fdx = (long) fx2 - fx1, fdy = (long) fy2 - fy1;
\t\tfinal long side1 = fdx * ((long) y1 - fy1) - fdy * ((long) x1 - fx1);
\t\tfinal long side2 = fdx * ((long) y2 - fy1) - fdy * ((long) x2 - fx1);
\t\treturn side1 > 0 && side2 > 0 || side1 < 0 && side2 < 0;
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\tfinal int[] fL = track.getLeft().getLast();
\t\tfinal int[] fR = track.getRight().getLast();
\t\tfinishLine = new Line2D.Double(fL[0], fL[1], fR[0], fR[1]);
"""
new = """\t\tfinal int[] fL = track.getLeft().getLast();
\t\tfinal int[] fR = track.getRight().getLast();
\t\tfinishX1 = fL[0];
\t\tfinishY1 = fL[1];
\t\tfinishX2 = fR[0];
\t\tfinishY2 = fR[1];
\t\tfinishDx = (long) finishX2 - finishX1;
\t\tfinishDy = (long) finishY2 - finishY1;
\t\tfinishLine = new Line2D.Double(finishX1, finishY1, finishX2, finishY2);
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
race.write_text(source)

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
old = """        testSegmentIntersection();
        testStartZone();
"""
new = """        testSegmentIntersection();
        testFinishSideReject();
        testStartZone();
"""
assert tests.count(old) == 1, tests.count(old)
tests = tests.replace(old, new, 1)

anchor = """    private static void testStartZone() {
"""
method = """    private static void testFinishSideReject() {
        for (int fx1 = -2; fx1 <= 2; fx1++)
            for (int fy1 = -2; fy1 <= 2; fy1++)
                for (int fx2 = -2; fx2 <= 2; fx2++)
                    for (int fy2 = -2; fy2 <= 2; fy2++)
                        for (int x1 = -2; x1 <= 2; x1++)
                            for (int y1 = -2; y1 <= 2; y1++)
                                for (int x2 = -2; x2 <= 2; x2++)
                                    for (int y2 = -2; y2 <= 2; y2++)
                                        if (RaceGame.sameStrictFinishSide(
                                                fx1, fy1, fx2, fy2, x1, y1, x2, y2))
                                            check(!java.awt.geom.Line2D.linesIntersect(
                                                    fx1, fy1, fx2, fy2,
                                                    x1, y1, x2, y2),
                                                    "same-side finish reject hid an intersection");
    }

    private static void testStartZone() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, method, 1)
core.write_text(tests)
print("materialized exact supporting-line finish reject")
