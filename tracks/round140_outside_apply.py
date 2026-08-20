#!/usr/bin/env python3
"""Materialize a conservative outside-cell proof for exact point probes.

Round 134 proves some subcells wholly inside the track.  The exact fallback
still asks Area.contains for many points in unit cells whose entire interior is
disjoint from both track and start-zone Areas.  Area.intersects is evaluated
once while building the raster; a false result is a proof that every point the
runtime scan can classify into that cell is outside.  Boundary and ambiguous
cells retain the exact point cache and Area.contains path.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old = """\t/** Round 111: conservative legality raster over unit cells. Bit 0 = the
\t *  cell's (margin-padded) closed square is provably fully inside trackA
\t *  or startZoneA (exact Area.contains(rect)); bit 1 = the cell lies in
\t *  the one-cell dilation of a boundary polyline's sampled cover. See
"""
new = """\t/** Round 111: conservative legality raster over unit cells. Bit 0 = the
\t *  cell's (margin-padded) closed square is provably fully inside trackA
\t *  or startZoneA (exact Area.contains(rect)); bit 1 = the cell lies in
\t *  the one-cell dilation of a boundary polyline's sampled cover; bit 2 =
\t *  the unit-cell interior is provably disjoint from both Areas. See
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\t\t\tfinal double x = cx - 0.001, y = cy - 0.001, s = 1.002;
\t\t\t\tif (trackA.contains(x, y, s, s) || startZoneA.contains(x, y, s, s))
\t\t\t\t\tr[cx * rasterH + cy] = 1;
"""
new = """\t\t\t\tfinal double x = cx - 0.001, y = cy - 0.001, s = 1.002;
\t\t\t\tif (trackA.contains(x, y, s, s) || startZoneA.contains(x, y, s, s))
\t\t\t\t\tr[cx * rasterH + cy] = 1;
\t\t\t\telse if (!trackA.intersects(cx, cy, 1.0, 1.0)
\t\t\t\t\t\t&& !startZoneA.intersects(cx, cy, 1.0, 1.0))
\t\t\t\t\tr[cx * rasterH + cy] = 4;
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\tfinal long xBits = Double.doubleToRawLongBits(x);
"""
new = """\t\tfinal byte[] unit = legalRaster;
\t\tif (unit != null) {
\t\t\tfinal int ux = (int) Math.floor(x);
\t\t\tfinal int uy = (int) Math.floor(y);
\t\t\tfinal int unitW = unit.length / rasterH;
\t\t\tif (ux >= 0 && uy >= 0 && ux < unitW && uy < rasterH
\t\t\t\t\t&& (unit[ux * rasterH + uy] & 4) != 0)
\t\t\t\treturn false;
\t\t}
\t\tfinal long xBits = Double.doubleToRawLongBits(x);
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

race.write_text(source)
print("materialized conservative outside-cell raster proof")
