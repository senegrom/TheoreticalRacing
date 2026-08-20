#!/usr/bin/env python3
"""Materialize allocation-free boundary segment intersection queries.

The residual exact legality path creates two int[2] query endpoints, then calls
the generic five-array intersection routine with seq=3.  The seq=3 branch never
uses endpoint identity rules, so an arithmetic-identical primitive overload can
consume the four query coordinates directly and avoid both arrays and generic
branching.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()
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
\t *  inclusion are an exact transcription of checkIntersect(..., seq=3). */
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
text = text.replace(anchor, method, 1)
geom.write_text(text)

print("materialized primitive boundary intersection query")
