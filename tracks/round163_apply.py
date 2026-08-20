#!/usr/bin/env python3
"""Materialize exact finish-side and primitive boundary fast paths.

Two residual geometry costs remain after the direct edge cache:
* nearly every simulated move calls the general finish-segment predicate even
  when both integer endpoints are strictly on one side of its supporting line;
* residual boundary checks allocate two tiny endpoint arrays before walking the
  fixed border path.

Both transformations preserve the original fallback arithmetic and endpoint
rules exactly.  The same-side test only rejects a mathematically impossible
intersection; all zero/opposite/collinear cases retain Line2D.  The primitive
boundary overload is an allocation-free spelling of checkIntersect(...,seq=3).
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

old = """\t\tfinal int[] from = {x1, y1 };
\t\tfinal int[] to = {x2, y2 };
\t\treturn !TrackGeometry.segmentCrossesPath(from, to, track.getLeft()) && !TrackGeometry.segmentCrossesPath(from, to, track.getRight());
"""
new = """\t\treturn !TrackGeometry.segmentCrossesPath(x1, y1, x2, y2, track.getLeft())
\t\t\t\t&& !TrackGeometry.segmentCrossesPath(x1, y1, x2, y2, track.getRight());
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
race.write_text(source)

geom = Path("src/tr/logic/TrackGeometry.java")
text = geom.read_text()
anchor = """\tstatic boolean segmentCrossesPath(final int[] from, final int[] to, final List<int[]> path) {
"""
method = """\t/** Allocation-free seq=3 boundary check. Arithmetic and endpoint
\t * inclusion exactly match checkIntersect(..., seq=3). */
\tprivate static boolean checkIntersectSeq3(final int[] p11, final int[] p12,
\t\t\tfinal int x21, final int y21, final int x22, final int y22) {
\t\tfinal double x1 = p11[0], y1 = p11[1], x2 = x21, y2 = y21;
\t\tfinal double dx1 = p12[0] - p11[0], dy1 = p12[1] - p11[1];
\t\tfinal double dx2 = x22 - x21, dy2 = y22 - y21;
\t\tfinal double d = dx2 * dy1 - dx1 * dy2;
\t\tif (d == 0) {
\t\t\tif ((x2 - x1) * dy1 - (y2 - y1) * dx1 != 0)
\t\t\t\treturn false;
\t\t\tfinal double len1Sq = dx1 * dx1 + dy1 * dy1;
\t\t\tif (len1Sq == 0)
\t\t\t\treturn false;
\t\t\tfinal double s1 = ((x2 - x1) * dx1 + (y2 - y1) * dy1) / len1Sq;
\t\t\tfinal double s2 = ((x22 - x1) * dx1 + (y22 - y1) * dy1) / len1Sq;
\t\t\treturn Math.max(0, Math.min(s1, s2)) < Math.min(1, Math.max(s1, s2));
\t\t}
\t\tfinal double s = (dy1 * x1 - dy1 * x2 - dx1 * y1 + dx1 * y2) / d;
\t\tfinal double t = (dy2 * x1 - dy2 * x2 - dx2 * y1 + dx2 * y2) / d;
\t\tif (s > 0 && s < 1 && t > 0 && t < 1)
\t\t\treturn true;
\t\treturn s > 0 && s < 1 && (t == 0 || t == 1);
\t}

\tstatic boolean segmentCrossesPath(final int x1, final int y1, final int x2,
\t\t\tfinal int y2, final List<int[]> path) {
\t\tint[] prev = null;
\t\tfor (final int[] cur : path) {
\t\t\tif (prev != null && checkIntersectSeq3(prev, cur, x1, y1, x2, y2))
\t\t\t\treturn true;
\t\t\tprev = cur;
\t\t}
\t\treturn false;
\t}

\tstatic boolean segmentCrossesPath(final int[] from, final int[] to, final List<int[]> path) {
"""
assert text.count(anchor) == 1, text.count(anchor)
geom.write_text(text.replace(anchor, method, 1))

core = Path("tests/tr/logic/CoreTests.java")
tests = core.read_text()
old_calls = """        testSegmentIntersection();
        testStartZone();
"""
new_calls = """        testSegmentIntersection();
        testFinishSideReject();
        testPrimitiveBoundaryIntersection();
        testStartZone();
"""
assert tests.count(old_calls) == 1, tests.count(old_calls)
tests = tests.replace(old_calls, new_calls, 1)

anchor = """    private static void testStartZone() {
"""
methods = """    private static void testFinishSideReject() {
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

    private static void testPrimitiveBoundaryIntersection() {
        final List<List<int[]>> paths = List.of(
                List.of(new int[]{0, 0}, new int[]{3, 0}, new int[]{3, 3}),
                List.of(new int[]{-1, -1}, new int[]{2, 2}, new int[]{4, -1}),
                List.of(new int[]{0, 2}, new int[]{2, 2}, new int[]{4, 2}));
        for (final List<int[]> path : paths)
            for (int x1 = -2; x1 <= 5; x1++)
                for (int y1 = -2; y1 <= 5; y1++)
                    for (int x2 = -2; x2 <= 5; x2++)
                        for (int y2 = -2; y2 <= 5; y2++) {
                            final boolean legacy = TrackGeometry.segmentCrossesPath(
                                    new int[]{x1, y1}, new int[]{x2, y2}, path);
                            final boolean primitive = TrackGeometry.segmentCrossesPath(
                                    x1, y1, x2, y2, path);
                            check(legacy == primitive,
                                    "primitive seq=3 boundary check diverged");
                        }
    }

    private static void testStartZone() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, methods, 1)
core.write_text(tests)

assert race.read_text().count("sameStrictFinishSide") == 1
assert geom.read_text().count("checkIntersectSeq3") == 2
assert tests.count("private static void testPrimitiveBoundaryIntersection()") == 1
print("materialized exact finish-side and primitive boundary fast paths")
