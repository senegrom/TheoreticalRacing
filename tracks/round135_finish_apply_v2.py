#!/usr/bin/env python3
"""Materialize Round 135 and replace the generic predicate with exact JDK semantics."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("round135_finish_apply.py")), run_name="__main__")

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()
old = """\tstatic boolean segmentsIntersectInt(final int ax, final int ay,
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
new = """\tstatic boolean segmentsIntersectInt(final int ax, final int ay,
\t\t\tfinal int bx, final int by, final int cx, final int cy,
\t\t\tfinal int dx, final int dy) {
\t\treturn relativeCCWInt(ax, ay, bx, by, cx, cy)
\t\t\t\t* relativeCCWInt(ax, ay, bx, by, dx, dy) <= 0
\t\t\t\t&& relativeCCWInt(cx, cy, dx, dy, ax, ay)
\t\t\t\t* relativeCCWInt(cx, cy, dx, dy, bx, by) <= 0;
\t}

\t/** Integer transcription of Line2D.relativeCCW, including its deliberately
\t * unusual degenerate-line behaviour.  Long products are exact for board
\t * coordinates and preserve every branch of the JDK predicate. */
\tprivate static int relativeCCWInt(final int x1, final int y1,
\t\t\tfinal int x2, final int y2, final int px0, final int py0) {
\t\tfinal long dx = (long) x2 - x1;
\t\tfinal long dy = (long) y2 - y1;
\t\tlong px = (long) px0 - x1;
\t\tlong py = (long) py0 - y1;
\t\tlong ccw = px * dy - py * dx;
\t\tif (ccw == 0) {
\t\t\tccw = px * dx + py * dy;
\t\t\tif (ccw > 0) {
\t\t\t\tpx -= dx;
\t\t\t\tpy -= dy;
\t\t\t\tccw = px * dx + py * dy;
\t\t\t\tif (ccw < 0)
\t\t\t\t\tccw = 0;
\t\t\t}
\t\t}
\t\treturn ccw < 0 ? -1 : ccw > 0 ? 1 : 0;
\t}
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)
race.write_text(source)
print("materialized exact Line2D-compatible integer finish intersection")
