#!/usr/bin/env python3
"""Materialize a contiguous Path2D mirror for exact point containment.

Area.contains walks the Area's internal curve vector for every residual legality
sample.  Path2D.Double copies the Area's exact PathIterator (same winding rule,
line/cubic coordinates and boundary convention) into contiguous primitive
arrays, whose contains implementation evaluates the same path with less object
indirection.  The original Areas remain authoritative for rectangle proofs and
start placement; only cached point probes use their exact path mirrors.
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
        for (int ix = -100; ix <= 1100; ix++) {
            final double x = ix / 37.0;
            for (int iy = -100; iy <= 900; iy++) {
                final double y = iy / 41.0;
                check(area.contains(x, y) == mirror.contains(x, y),
                        "Area/Path2D point containment diverged at " + x + "," + y);
            }
        }
        final java.awt.geom.PathIterator iterator = area.getPathIterator(null);
        final double[] coordinates = new double[6];
        while (!iterator.isDone()) {
            final int type = iterator.currentSegment(coordinates);
            if (type != java.awt.geom.PathIterator.SEG_CLOSE) {
                final double x = coordinates[0], y = coordinates[1];
                check(area.contains(x, y) == mirror.contains(x, y),
                        "Area/Path2D boundary convention diverged");
                check(area.contains(Math.nextUp(x), y) == mirror.contains(Math.nextUp(x), y),
                        "Area/Path2D nextUp boundary convention diverged");
                check(area.contains(Math.nextDown(x), y) == mirror.contains(Math.nextDown(x), y),
                        "Area/Path2D nextDown boundary convention diverged");
            }
            iterator.next();
        }
    }

    private static void testDistinctCoverMatching() {
"""
assert tests.count(anchor) == 1, tests.count(anchor)
tests = tests.replace(anchor, method, 1)
core.write_text(tests)
print("materialized exact Path2D containment mirrors and differential unit test")
