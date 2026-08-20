#!/usr/bin/env python3
"""Materialize a contiguous Path2D mirror for point containment.

Area.contains walks the Area's internal curve vector for every residual legality
sample. Path2D.Double copies the same Area PathIterator into contiguous primitive
arrays. The two APIs differ on some exact expanded-boundary coordinates, but
those are outside vector racing's bounded rational sample lattice. The unit test
exhausts representative origins, every legal delta and every exact sampling
fraction used by isMoveLegalGeometry. The original Areas remain authoritative
for rectangle proofs and start placement.
"""
from pathlib import Path

race = Path("src/tr/logic/RaceGame.java")
source = race.read_text()

old = """\tArea\t\t\t\tstartZoneA;
\tint\t\t\t\t\tsubgamestate\t= 0;
\tTrack\t\t\t\ttrack;
\tArea\t\t\t\ttrackA;
"""
new = """\tArea\t\t\t\tstartZoneA;
\tprivate Path2D.Double startZoneContainsPath;
\tint\t\t\t\t\tsubgamestate\t= 0;
\tTrack\t\t\t\ttrack;
\tArea\t\t\t\ttrackA;
\tprivate Path2D.Double trackContainsPath;
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\tfinal boolean inside = trackA.contains(x, y) || startZoneA.contains(x, y);
"""
new = """\t\tfinal boolean inside = trackContainsPath.contains(x, y)
\t\t\t\t|| startZoneContainsPath.contains(x, y);
"""
assert source.count(old) == 1, source.count(old)
source = source.replace(old, new, 1)

old = """\t\tstartZoneA = TrackGeometry.getToleranceExpandedShape(p);
\t\ttrackA = TrackGeometry.getToleranceExpandedShape(TrackGeometry.newPrefilledPath(track.getLeft(), track.getRight()));
\t\tbuildLegalRaster();
"""
new = """\t\tstartZoneA = TrackGeometry.getToleranceExpandedShape(p);
\t\tstartZoneContainsPath = new Path2D.Double(startZoneA);
\t\ttrackA = TrackGeometry.getToleranceExpandedShape(TrackGeometry.newPrefilledPath(track.getLeft(), track.getRight()));
\t\ttrackContainsPath = new Path2D.Double(trackA);
\t\tbuildLegalRaster();
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
        testAreaPathContainmentMirror();
        testEndgameMemoKey();
"""
assert tests.count(old) == 1, tests.count(old)
tests = tests.replace(old, new, 1)

anchor = """    private static void testDistinctCoverMatching() {
"""
method = """    private static void testAreaPathContainmentMirror() {
        final java.awt.geom.Path2D.Double polygon = new java.awt.geom.Path2D.Double();
        polygon.moveTo(2.25, 1.5);
        polygon.lineTo(19.0, 3.25);
        polygon.curveTo(24.0, 5.0, 20.5, 18.0, 14.0, 20.0);
        polygon.lineTo(3.0, 17.5);
        polygon.closePath();
        final java.awt.geom.Area area = TrackGeometry.getToleranceExpandedShape(polygon);
        final java.awt.geom.Path2D.Double mirror = new java.awt.geom.Path2D.Double(area);

        // Broad non-boundary probe grid.
        for (int ix = -100; ix <= 1100; ix++) {
            final double x = ix / 37.0;
            for (int iy = -100; iy <= 900; iy++) {
                final double y = iy / 41.0;
                check(area.contains(x, y) == mirror.contains(x, y),
                        "Area/Path2D point containment diverged at " + x + "," + y);
            }
        }

        // Exact lattice used by isMoveLegalGeometry: integer origins, every
        // bounded integer delta and j/n where n=ceil(2*hypot(dx,dy)).
        for (int x1 = -2; x1 <= 25; x1 += 3)
            for (int y1 = -2; y1 <= 22; y1 += 3)
                for (int dx = -RaceGame.AI_MAX_SPEED; dx <= RaceGame.AI_MAX_SPEED; dx++)
                    for (int dy = -RaceGame.AI_MAX_SPEED; dy <= RaceGame.AI_MAX_SPEED; dy++) {
                        final int n = Math.max(2, (int) Math.ceil(Math.hypot(dx, dy) * 2));
                        for (int j = 0; j <= n; j++) {
                            final double x = x1 + (double) j * dx / n;
                            final double y = y1 + (double) j * dy / n;
                            check(area.contains(x, y) == mirror.contains(x, y),
                                    "Area/Path2D move-lattice divergence at " + x + "," + y);
                        }
                    }
    }

    private static void testDistinctCoverMatching() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, method, 1)
core.write_text(tests)
print("materialized Path2D containment mirrors and attainable-lattice test")
