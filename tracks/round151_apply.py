#!/usr/bin/env python3
"""Materialize an exact integer finish-line intersection predicate.

Every production caller supplies integer grid coordinates.  Java's
Line2D.linesIntersect is two relativeCCW tests; with the game's <=500 grid,
all differences, products and sums are exact in both double and long arithmetic.
This transcription preserves its collinear and degenerate-segment semantics,
then retains the existing forward-direction dot test unchanged.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old = """\tLine2D\t\t\t\tfinishLine;
\t/** Unit vector of the racing direction at the finish line. A move only
"""
new = """\tLine2D\t\t\t\tfinishLine;
\tprivate int finishX1, finishY1, finishX2, finishY2;
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
\t\tif (!linesIntersectInt(finishX1, finishY1, finishX2, finishY2,
\t\t\t\tx1, y1, x2, y2))
\t\t\treturn false;
\t\t// Only a forward crossing counts (move heads in the racing direction).
\t\t// A zero-length or backward move across the line is not a finish.
\t\treturn (x2 - x1) * finishFwdX + (y2 - y1) * finishFwdY > 0;
\t}

\t/** Exact integer transcription of Line2D.relativeCCW. */
\tstatic int relativeCCWInt(final int x1, final int y1, final int x2,
\t\t\tfinal int y2, final int px, final int py) {
\t\tfinal long dx1 = (long) x2 - x1, dy1 = (long) y2 - y1;
\t\tlong dx2 = (long) px - x1, dy2 = (long) py - y1;
\t\tlong ccw = dx2 * dy1 - dy2 * dx1;
\t\tif (ccw == 0) {
\t\t\tccw = dx2 * dx1 + dy2 * dy1;
\t\t\tif (ccw > 0) {
\t\t\t\tdx2 -= dx1;
\t\t\t\tdy2 -= dy1;
\t\t\t\tccw = dx2 * dx1 + dy2 * dy1;
\t\t\t\tif (ccw < 0)
\t\t\t\t\tccw = 0;
\t\t\t}
\t\t}
\t\treturn ccw < 0 ? -1 : ccw > 0 ? 1 : 0;
\t}

\tstatic boolean linesIntersectInt(final int x1, final int y1,
\t\t\tfinal int x2, final int y2, final int x3, final int y3,
\t\t\tfinal int x4, final int y4) {
\t\treturn relativeCCWInt(x1, y1, x2, y2, x3, y3)
\t\t\t\t* relativeCCWInt(x1, y1, x2, y2, x4, y4) <= 0
\t\t\t\t&& relativeCCWInt(x3, y3, x4, y4, x1, y1)
\t\t\t\t* relativeCCWInt(x3, y3, x4, y4, x2, y2) <= 0;
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
        testIntegerLineIntersection();
        testStartZone();
"""
assert tests.count(old) == 1, tests.count(old)
tests = tests.replace(old, new, 1)

anchor = """    private static void testStartZone() {
"""
method = """    private static void testIntegerLineIntersection() {
        for (int x1 = -2; x1 <= 2; x1++)
            for (int y1 = -2; y1 <= 2; y1++)
                for (int x2 = -2; x2 <= 2; x2++)
                    for (int y2 = -2; y2 <= 2; y2++)
                        for (int x3 = -2; x3 <= 2; x3++)
                            for (int y3 = -2; y3 <= 2; y3++)
                                for (int x4 = -2; x4 <= 2; x4++)
                                    for (int y4 = -2; y4 <= 2; y4++) {
                                        final boolean expected = java.awt.geom.Line2D.linesIntersect(
                                                x1, y1, x2, y2, x3, y3, x4, y4);
                                        final boolean actual = RaceGame.linesIntersectInt(
                                                x1, y1, x2, y2, x3, y3, x4, y4);
                                        check(actual == expected,
                                                "integer segment predicate mismatch: "
                                                + x1 + "," + y1 + " -> " + x2 + "," + y2
                                                + " vs " + x3 + "," + y3 + " -> " + x4 + "," + y4);
                                    }
    }

    private static void testStartZone() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, method, 1)
core.write_text(tests)
print("materialized exact integer finish intersection and exhaustive test")
