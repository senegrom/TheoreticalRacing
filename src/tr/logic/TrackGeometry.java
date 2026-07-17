package tr.logic;

import java.awt.BasicStroke;
import java.awt.Shape;
import java.awt.geom.Area;
import java.awt.geom.Path2D;
import java.util.Arrays;
import java.util.Iterator;
import java.util.LinkedList;

/**
 * Pure track-geometry helpers extracted from {@link RaceGame}: segment
 * intersection tests, incremental self-intersection, start-zone construction,
 * tolerance-expanded shapes and closed-path building. No game state.
 */
final class TrackGeometry {
	private TrackGeometry() {}

	private final static float			startZoneWidth	= 2f;
	private final static BasicStroke	strkTolerance	= new BasicStroke(.01f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND);

	/**
	 * @param seq 0: all endpoints checked; 1: p11==p22 allowed; 2: p12==p21
	 *            allowed; 3: equal endpoints always allowed.
	 * @return true iff the segments (p11,p12) and (p21,p22) intersect.
	 */
	final static boolean checkIntersect(final int[] p11, final int[] p12, final int[] p21, final int[] p22, final byte seq) {
		if (seq != 3 && (Arrays.equals(p11, p12) || Arrays.equals(p11, p21) || Arrays.equals(p12, p22) || Arrays.equals(p21, p22)))
			return true;
		if (seq != 1 && seq != 3 && Arrays.equals(p11, p22))
			return true;
		if (seq != 2 && seq != 3 && Arrays.equals(p12, p21))
			return true;

		final double x1 = p11[0], y1 = p11[1], x2 = p21[0], y2 = p21[1];
		final double dx1 = p12[0] - p11[0], dy1 = p12[1] - p11[1];
		final double dx2 = p22[0] - p21[0], dy2 = p22[1] - p21[1];
		final double d = dx2 * dy1 - dx1 * dy2;
		if (d == 0) {
			if (seq != 0 && seq != 3) {
				if (Math.signum(dx1) != Math.signum(dx2) || Math.signum(dy1) != Math.signum(dy2))
					return true;
				return false;
			}
			if ((x2 - x1) * dy1 - (y2 - y1) * dx1 != 0)
				return false;
			final double len1Sq = dx1 * dx1 + dy1 * dy1;
			if (len1Sq == 0)
				return false;
			final double s1 = ((x2 - x1) * dx1 + (y2 - y1) * dy1) / len1Sq;
			final double s2 = ((p22[0] - x1) * dx1 + (p22[1] - y1) * dy1) / len1Sq;
			return Math.max(0, Math.min(s1, s2)) < Math.min(1, Math.max(s1, s2));
		} else if (seq == 0 || seq == 3) {
			final double s = (dy1 * x1 - dy1 * x2 - dx1 * y1 + dx1 * y2) / d;
			final double t = (dy2 * x1 - dy2 * x2 - dx2 * y1 + dx2 * y2) / d;
			if (s > 0 && s < 1 && t > 0 && t < 1)
				return true;
			if (seq == 0 && (s == 0 || s == 1) && (t == 0 || t == 1))
				return true;
			// Corner-clip: AI line interior crosses through a border vertex
			// (s in code = AI line parameter, t in code = border parameter)
			if (seq == 3 && s > 0 && s < 1 && (t == 0 || t == 1))
				return true;
		}
		return false;
	}

	/**
	 * @return true iff the line paths p1, p2 intersect anywhere.
	 */
	final static boolean checkIntersect(final LinkedList<int[]> p1, final LinkedList<int[]> p2, final boolean allowEqual) {
		if (p1 == null || p2 == null || p1.size() < 2 || p2.size() < 2)
			return false;
		if (p1.size() == 2 && Arrays.equals(p1.getFirst(), p1.getLast()))
			return true;
		if (p2.size() == 2 && Arrays.equals(p2.getFirst(), p2.getLast()))
			return true;
		final Iterator<int[]> it1 = p1.iterator();
		int[] p11 = null, p12 = null;
		while (it1.hasNext()) {
			p12 = it1.next();
			if (p11 != null) {
				final Iterator<int[]> it2 = p2.iterator();
				int[] p21 = null, p22 = null;
				while (it2.hasNext()) {
					p22 = it2.next();
					if (p21 != null && (p11 != p21 || p12 != p22)) {
						final byte seq;
						if (allowEqual)
							seq = 3;
						else if (p11 == p22)
							seq = 1;
						else if (p12 == p21)
							seq = 2;
						else
							seq = 0;
						if (checkIntersect(p11, p12, p21, p22, seq))
							return true;
					}
					p21 = p22;
				}
			}
			p11 = p12;
		}
		return false;
	}

	/**
	 * Cheap incremental self-intersection check: tests segment (prevLast,last)
	 * of `active` against all earlier segments of `active` and all segments of
	 * `other`. O(n) per call instead of O(n²).
	 */
	final static boolean lastSegmentIntersects(final LinkedList<int[]> active, final LinkedList<int[]> other) {
		if (active.size() < 2)
			return false;
		final int[] a2 = active.getLast();
		final int[] a1 = active.get(active.size() - 2);
		// Against earlier segments of active itself (skip the adjacent one)
		int[] prev = null;
		final Iterator<int[]> it = active.iterator();
		int idx = 0;
		final int limit = active.size() - 2;
		while (it.hasNext() && idx <= limit) {
			final int[] cur = it.next();
			if (prev != null) {
				// segments (prev,cur) and (a1,a2); they're non-adjacent if idx < limit
				final boolean adjacent = idx == limit; // last segment before our new one
				if (!adjacent) {
					if (checkIntersect(prev, cur, a1, a2, (byte) 0))
						return true;
				} else {
					// adjacent: shared endpoint (cur == a1). Allowed.
					if (checkIntersect(prev, cur, a1, a2, (byte) 2))
						return true;
				}
			}
			prev = cur;
			idx++;
		}
		// Against all segments of the other side
		prev = null;
		final Iterator<int[]> it2 = other.iterator();
		while (it2.hasNext()) {
			final int[] cur = it2.next();
			if (prev != null && checkIntersect(prev, cur, a1, a2, (byte) 0))
				return true;
			prev = cur;
		}
		return false;
	}

	final static Area getToleranceExpandedShape(final Shape s) {
		final Area a = new Area(strkTolerance.createStrokedShape(s));
		a.add(new Area(s));
		return a;
	}

	final static float[][] makeStartZone(final int[] pL, final int[] pR) {
		final float len = (float) Math.sqrt((pR[0] - pL[0]) * (pR[0] - pL[0]) + (pR[1] - pL[1]) * (pR[1] - pL[1]));
		final float dirX = (pL[1] - pR[1]) * startZoneWidth / len;
		final float dirY = (pR[0] - pL[0]) * startZoneWidth / len;
		return new float[][]{{pL[0], pR[0], pR[0] + dirX, pL[0] + dirX }, {pL[1], pR[1], pR[1] + dirY, pL[1] + dirY } };
	}

	final static Path2D.Float newPrefilledPath(final LinkedList<int[]> left, final LinkedList<int[]> right) {
		if (left == null || left.isEmpty())
			return null;
		final Path2D.Float p = new Path2D.Float();
		int[] pos = left.getFirst();
		p.moveTo(pos[0], pos[1]);
		Iterator<int[]> it = left.iterator();
		while (it.hasNext()) {
			pos = it.next();
			p.lineTo(pos[0], pos[1]);
		}
		if (right == null || right.isEmpty())
			return p;
		it = right.descendingIterator();
		while (it.hasNext()) {
			pos = it.next();
			p.lineTo(pos[0], pos[1]);
		}
		p.closePath();
		return p;
	}

	static boolean segmentCrossesPath(final int[] from, final int[] to, final LinkedList<int[]> path) {
		int[] prev = null;
		for (final int[] cur : path) {
			if (prev != null && checkIntersect(prev, cur, from, to, (byte) 3))
				return true;
			prev = cur;
		}
		return false;
	}

}
