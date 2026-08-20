#!/usr/bin/env python3
"""Materialize an exact integer finish-line intersection kernel.

Every production caller supplies integer board coordinates, but crossesFinish
currently routes each probe through java.awt.geom.Line2D's double-precision
relative-CCW implementation.  This experiment keeps the public semantics and
forward-direction test while using overflow-safe long cross products and an
inclusive integer segment predicate.  CoreTests exhaustively compare the new
predicate with Line2D over a dense small grid plus deterministic wide samples.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old = """\tprivate double\t\t\t\tfinishFwdX, finishFwdY;
"""
new = """\tprivate double\t\t\t\tfinishFwdX, finishFwdY;
\tprivate int\t\t\t\t\tfinishX1, finishY1, finishX2, finishY2;
\tprivate int\t\t\t\t\tfinishHeadingX, finishHeadingY;
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

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
\tboolean crossesFinish(final int x1, final int y1, final int x2, final int y2) {
\t\t// The unnormalised heading has exactly the same sign as the old unit
\t\t// vector dot product, but stays in integer arithmetic.  Rejecting the
\t\t// overwhelmingly common non-forward probes before intersection is safe:
\t\t// such a move could never count as a finish under the existing rule.
\t\tfinal long forward = (long) (x2 - x1) * finishHeadingX
\t\t\t\t+ (long) (y2 - y1) * finishHeadingY;
\t\treturn forward > 0 && segmentsIntersectInt(
\t\t\t\tfinishX1, finishY1, finishX2, finishY2, x1, y1, x2, y2);
\t}

\t/** Inclusive integer segment intersection, equivalent to
\t *  {@link Line2D#linesIntersect(double, double, double, double, double,
\t *  double, double, double)} for integer coordinates. Board bounds make the
\t *  long cross products many orders of magnitude smaller than overflow. */
\tstatic boolean segmentsIntersectInt(final int ax, final int ay,
\t\t\tfinal int bx, final int by, final int cx, final int cy,
\t\t\tfinal int dx, final int dy) {
\t\tif (Math.max(ax, bx) < Math.min(cx, dx)
\t\t\t\t|| Math.max(cx, dx) < Math.min(ax, bx)
\t\t\t\t|| Math.max(ay, by) < Math.min(cy, dy)
\t\t\t\t|| Math.max(cy, dy) < Math.min(ay, by))
\t\t\treturn false;
\t\tfinal long o1 = orient(ax, ay, bx, by, cx, cy);
\t\tfinal long o2 = orient(ax, ay, bx, by, dx, dy);
\t\tfinal long o3 = orient(cx, cy, dx, dy, ax, ay);
\t\tfinal long o4 = orient(cx, cy, dx, dy, bx, by);
\t\tif (o1 == 0 && onSegment(ax, ay, bx, by, cx, cy))
\t\t\treturn true;
\t\tif (o2 == 0 && onSegment(ax, ay, bx, by, dx, dy))
\t\t\treturn true;
\t\tif (o3 == 0 && onSegment(cx, cy, dx, dy, ax, ay))
\t\t\treturn true;
\t\tif (o4 == 0 && onSegment(cx, cy, dx, dy, bx, by))
\t\t\treturn true;
\t\treturn (o1 > 0) != (o2 > 0) && (o3 > 0) != (o4 > 0);
\t}

\tprivate static long orient(final int ax, final int ay, final int bx,
\t\t\tfinal int by, final int cx, final int cy) {
\t\treturn (long) (bx - ax) * (cy - ay) - (long) (by - ay) * (cx - ax);
\t}

\tprivate static boolean onSegment(final int ax, final int ay, final int bx,
\t\t\tfinal int by, final int px, final int py) {
\t\treturn px >= Math.min(ax, bx) && px <= Math.max(ax, bx)
\t\t\t\t&& py >= Math.min(ay, by) && py <= Math.max(ay, by);
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\tfinal int[] fL = left.getLast(), fR = right.getLast();
\t\tdouble hx = 0, hy = 0;
"""
new = """\t\tfinal int[] fL = left.getLast(), fR = right.getLast();
\t\tfinishX1 = fL[0];
\t\tfinishY1 = fL[1];
\t\tfinishX2 = fR[0];
\t\tfinishY2 = fR[1];
\t\tdouble hx = 0, hy = 0;
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\tif (hx == 0 && hy == 0) {
\t\t\thx = -(fR[1] - fL[1]);
\t\t\thy = fR[0] - fL[0];
\t\t}
\t\tfinal double len = Math.hypot(hx, hy);
"""
new = """\t\tif (hx == 0 && hy == 0) {
\t\t\thx = -(fR[1] - fL[1]);
\t\t\thy = fR[0] - fL[0];
\t\t}
\t\tfinishHeadingX = (int) hx;
\t\tfinishHeadingY = (int) hy;
\t\tfinal double len = Math.hypot(hx, hy);
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
race.write_text(source)

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
old = """        testPointContainmentCache();
        testEndgameMemoKey();
"""
new = """        testPointContainmentCache();
        testIntegerSegmentIntersection();
        testEndgameMemoKey();
"""
assert tests.count(old) == 1, tests.count(old)
tests = tests.replace(old, new, 1)

anchor = """    private static void testDistinctCoverMatching() {
"""
method = """    private static void testIntegerSegmentIntersection() {
        for (int ax = -2; ax <= 2; ax++)
            for (int ay = -2; ay <= 2; ay++)
                for (int bx = -2; bx <= 2; bx++)
                    for (int by = -2; by <= 2; by++)
                        for (int cx = -2; cx <= 2; cx++)
                            for (int cy = -2; cy <= 2; cy++)
                                for (int dx = -2; dx <= 2; dx++)
                                    for (int dy = -2; dy <= 2; dy++) {
                                        final boolean expected = java.awt.geom.Line2D.linesIntersect(
                                                ax, ay, bx, by, cx, cy, dx, dy);
                                        final boolean actual = RaceGame.segmentsIntersectInt(
                                                ax, ay, bx, by, cx, cy, dx, dy);
                                        check(actual == expected,
                                                "integer segment predicate mismatch: "
                                                + ax + "," + ay + " -> " + bx + "," + by
                                                + " vs " + cx + "," + cy + " -> " + dx + "," + dy);
                                    }

        long state = 0x6a09e667f3bcc909L;
        for (int i = 0; i < 100_000; i++) {
            final int[] p = new int[8];
            for (int j = 0; j < p.length; j++) {
                state = state * 6364136223846793005L + 1442695040888963407L;
                p[j] = (int) ((state >>> 32) % 4001) - 2000;
            }
            final boolean expected = java.awt.geom.Line2D.linesIntersect(
                    p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7]);
            final boolean actual = RaceGame.segmentsIntersectInt(
                    p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7]);
            check(actual == expected, "wide integer segment predicate mismatch at sample " + i);
        }
    }

    private static void testDistinctCoverMatching() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, method, 1)
core.write_text(tests)

print("materialized exact integer finish intersection")
