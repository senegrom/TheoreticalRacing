package tr.logic;

import java.awt.geom.Area;
import java.awt.geom.PathIterator;
import java.awt.geom.Rectangle2D;

/**
 * perf_pocket: the starting-grid pocket test {@code zone.contains(x, y) &&
 * !track.contains(x, y)} ({@code RaceGame.inPocket}) answered for whole
 * subcells of the start zone's bounds. Same verdicts, far fewer walks of the
 * corridor's Area (that walk was 11-16% of all CPU on Hungaroring).
 *
 * <p>Why a verdict is exact. {@link Area#contains(double, double)} is a
 * half-open bounds test followed by the parity of the crossings of the
 * rightward ray from the point with the Area's y-monotone pieces, each counted
 * on [ytop, ybot). Take a point at least MARGIN from every line piece of the
 * Area's outline (its path iterator, junction and closing segments included)
 * and from the control-point box of every curved piece. A line piece's count
 * is then decided exactly (its XforY errs by about 1e-12), a curved piece's by
 * its box alone; the pieces meet only at shared points and horizontal
 * junctions, so the count changes parity only across the outline, and the
 * bounds test agrees with the parity. Area.contains is therefore constant on
 * any connected set of such points. A subcell is clean when no piece comes
 * within 2 * MARGIN of its closed square (conservative marking); the MARGIN
 * neighbourhoods of two 4-adjacent clean subcells overlap, so one exact
 * Area.contains in a 4-connected clean component holds at every point indexed
 * into it (the index arithmetic errs by about 1e-13). Every other subcell keeps
 * the exact tests, with the corridor's memoised per thread on the exact
 * coordinates. Each build checks every lattice point of its region and two
 * points per unit cell against the exact tests; a disagreement disables it.
 */
final class PocketCells {
	/** Nothing proven: both exact tests. */
	static final byte UNKNOWN = 0;
	/** Out of the pocket everywhere: outside the zone or inside the corridor. */
	static final byte OUT = 1;
	/** In the pocket everywhere. */
	static final byte IN = 2;
	/** Inside the zone everywhere; the corridor test remains. */
	static final byte ZONE_IN = 3;
	/** Outside the corridor everywhere; the zone test remains. */
	static final byte TRACK_OUT = 4;

	/** Larger regions (a start line hundreds of cells long) keep the exact tests. */
	private static final long MAX_UNITS = 4096;
	private static final int MAX_SUBCELLS = 1 << 18;
	private static final int MAX_RES = 64;
	private static final double MARGIN = 1.0 / 512;
	private static final double MAX_COORD = 1 << 20;
	private static final byte FALSE = 1;
	private static final byte TRUE = 2;
	private static final byte DIRTY = 3;

	/** The pair this table answers for; the caller rebuilds on any other pair. */
	final Area zone;
	final Area track;
	private final double ox;
	private final double oy;
	private final int res;
	private final int w;
	private final int h;
	private final byte[] states;
	private final ThreadLocal<RaceGame.PointContainmentCache> trackMemo =
			ThreadLocal.withInitial(() -> new RaceGame.PointContainmentCache(1 << 10));

	private PocketCells(final Area zone, final Area track, final double ox, final double oy,
			final int res, final int w, final int h, final byte[] states) {
		this.zone = zone;
		this.track = track;
		this.ox = ox;
		this.oy = oy;
		this.res = res;
		this.w = w;
		this.h = h;
		this.states = states;
	}

	/** The verdict for the subcell holding (x, y); UNKNOWN off the table. */
	byte state(final double x, final double y) {
		final double fx = (x - ox) * res, fy = (y - oy) * res;
		if (fx >= 0 && fy >= 0 && fx < w && fy < h)
			return states[(int) fx * h + (int) fy];
		return UNKNOWN;
	}

	/** {@code track.contains(x, y)}, memoised per thread on the exact coordinates. */
	boolean trackContains(final double x, final double y) {
		final long xBits = Double.doubleToRawLongBits(x);
		final long yBits = Double.doubleToRawLongBits(y);
		final RaceGame.PointContainmentCache memo = trackMemo.get();
		final byte cached = memo.get(xBits, yBits);
		if (cached != 0)
			return cached == RaceGame.PointContainmentCache.TRUE;
		final boolean inside = track.contains(x, y);
		memo.put(xBits, yBits, inside);
		return inside;
	}

	void clearMemoForCurrentThread() {
		trackMemo.remove();
	}

	/** A table for this pair; one that proves nothing when it cannot be built. */
	static PocketCells build(final Area zone, final Area track) {
		PocketCells cells = null;
		try {
			cells = tryBuild(zone, track);
		} catch (final RuntimeException e) {
			cells = null; // the exact tests everywhere
		}
		return cells != null ? cells : new PocketCells(zone, track, 0, 0, 1, 0, 0, new byte[0]);
	}

	private static PocketCells tryBuild(final Area zone, final Area track) {
		if (zone.isEmpty())
			return null;
		final Rectangle2D b = zone.getBounds2D();
		final double minX = Math.floor(b.getMinX()) - 1, minY = Math.floor(b.getMinY()) - 1;
		final double maxX = Math.ceil(b.getMaxX()) + 1, maxY = Math.ceil(b.getMaxY()) + 1;
		if (!(minX >= -MAX_COORD && minY >= -MAX_COORD && maxX <= MAX_COORD && maxY <= MAX_COORD))
			return null;
		final long unitsW = (long) (maxX - minX), unitsH = (long) (maxY - minY);
		if (unitsW * unitsH > MAX_UNITS)
			return null;
		int res = MAX_RES;
		while (res > 1 && unitsW * unitsH * res * res > MAX_SUBCELLS)
			res >>= 1;
		if (unitsW * unitsH * res * res > MAX_SUBCELLS)
			return null;
		final Grid grid = new Grid(minX, minY, res, (int) (unitsW * res), (int) (unitsH * res));
		final byte[] zoneValues = grid.values(zone);
		final byte[] trackValues = grid.values(track);
		if (zoneValues == null || trackValues == null
				|| !grid.verify(zone, zoneValues, unitsW, unitsH)
				|| !grid.verify(track, trackValues, unitsW, unitsH))
			return null;
		final byte[] states = new byte[zoneValues.length];
		for (int k = 0; k < states.length; k++)
			states[k] = combine(zoneValues[k], trackValues[k]);
		return new PocketCells(zone, track, minX, minY, res, grid.w, grid.h, states);
	}

	private static byte combine(final byte zone, final byte track) {
		if (zone == FALSE || track == TRUE)
			return OUT;
		if (zone == TRUE)
			return track == FALSE ? IN : ZONE_IN;
		return track == FALSE ? TRACK_OUT : UNKNOWN;
	}

	/** One Area's verdicts on the table's subcells: TRUE/FALSE where proven, 0 elsewhere. */
	private static final class Grid {
		final double ox;
		final double oy;
		final int res;
		final int w;
		final int h;
		/** The region's far edges. */
		final double x1;
		final double y1;
		/** Sample spacing along a line piece, per axis. */
		final double step;
		/** Marking reach: 2 * MARGIN plus the sampling slack. */
		final double pad;

		Grid(final double ox, final double oy, final int res, final int w, final int h) {
			this.ox = ox;
			this.oy = oy;
			this.res = res;
			this.w = w;
			this.h = h;
			x1 = ox + (double) w / res;
			y1 = oy + (double) h / res;
			step = 0.25 / res;
			pad = 2 * MARGIN + step;
		}

		/** The same arithmetic as {@link PocketCells#state}. */
		int index(final double x, final double y) {
			final double fx = (x - ox) * res, fy = (y - oy) * res;
			if (fx >= 0 && fy >= 0 && fx < w && fy < h)
				return (int) fx * h + (int) fy;
			return -1;
		}

		/** Null when the outline cannot be read. */
		byte[] values(final Area area) {
			final byte[] val = new byte[w * h];
			if (!markOutline(area, val))
				return null;
			final int[] queue = new int[val.length];
			for (int seed = 0; seed < val.length; seed++) {
				if (val[seed] != 0)
					continue;
				final byte v = area.contains(ox + (seed / h + 0.5) / res, oy + (seed % h + 0.5) / res)
						? TRUE : FALSE;
				val[seed] = v;
				int head = 0, tail = 0;
				queue[tail++] = seed;
				while (head < tail) {
					final int k = queue[head++];
					final int j = k % h;
					if (k >= h && val[k - h] == 0) {
						val[k - h] = v;
						queue[tail++] = k - h;
					}
					if (k + h < val.length && val[k + h] == 0) {
						val[k + h] = v;
						queue[tail++] = k + h;
					}
					if (j > 0 && val[k - 1] == 0) {
						val[k - 1] = v;
						queue[tail++] = k - 1;
					}
					if (j + 1 < h && val[k + 1] == 0) {
						val[k + 1] = v;
						queue[tail++] = k + 1;
					}
				}
			}
			for (int k = 0; k < val.length; k++)
				if (val[k] == DIRTY)
					val[k] = 0;
			return val;
		}

		/** Marks every subcell near the outline DIRTY: lines by their points, curves by their boxes. */
		private boolean markOutline(final Area area, final byte[] val) {
			final double[] c = new double[6];
			double sx = 0, sy = 0, px = 0, py = 0;
			boolean open = false;
			for (final PathIterator it = area.getPathIterator(null); !it.isDone(); it.next()) {
				switch (it.currentSegment(c)) {
					case PathIterator.SEG_MOVETO:
						if (!finite(c, 2))
							return false;
						sx = px = c[0];
						sy = py = c[1];
						open = true;
						box(px, py, px, py, val);
						break;
					case PathIterator.SEG_LINETO:
						if (!open || !finite(c, 2))
							return false;
						line(px, py, c[0], c[1], val);
						px = c[0];
						py = c[1];
						break;
					case PathIterator.SEG_QUADTO:
						if (!open || !finite(c, 4))
							return false;
						box(Math.min(px, Math.min(c[0], c[2])), Math.min(py, Math.min(c[1], c[3])),
								Math.max(px, Math.max(c[0], c[2])), Math.max(py, Math.max(c[1], c[3])), val);
						px = c[2];
						py = c[3];
						break;
					case PathIterator.SEG_CUBICTO:
						if (!open || !finite(c, 6))
							return false;
						box(Math.min(Math.min(px, c[0]), Math.min(c[2], c[4])),
								Math.min(Math.min(py, c[1]), Math.min(c[3], c[5])),
								Math.max(Math.max(px, c[0]), Math.max(c[2], c[4])),
								Math.max(Math.max(py, c[1]), Math.max(c[3], c[5])), val);
						px = c[4];
						py = c[5];
						break;
					case PathIterator.SEG_CLOSE:
						if (!open)
							return false;
						line(px, py, sx, sy, val);
						px = sx;
						py = sy;
						break;
					default:
						return false;
				}
			}
			return true;
		}

		/** Samples at most {@code step} apart along the part within one unit of the region. */
		private void line(final double ax, final double ay, final double bx, final double by,
				final byte[] val) {
			final double dx = bx - ax, dy = by - ay;
			final double[] p = {-dx, dx, -dy, dy };
			final double[] q = {ax - (ox - 1), x1 + 1 - ax, ay - (oy - 1), y1 + 1 - ay };
			double t0 = 0, t1 = 1;
			for (int e = 0; e < 4; e++) {
				if (p[e] == 0) {
					if (q[e] < 0)
						return;
				} else {
					final double r = q[e] / p[e];
					if (p[e] < 0) {
						if (r > t0)
							t0 = r;
					} else if (r < t1)
						t1 = r;
				}
			}
			if (t0 > t1)
				return;
			final double span = (t1 - t0) * Math.max(Math.abs(dx), Math.abs(dy));
			final long n = (long) Math.ceil(span / step) + 1;
			for (long k = 0; k <= n; k++) {
				final double t = t0 + (t1 - t0) * k / n;
				final double qx = ax + t * dx, qy = ay + t * dy;
				box(qx, qy, qx, qy, val);
			}
		}

		/** Every subcell whose closed square comes within {@code pad} of the box. */
		private void box(final double minX, final double minY, final double maxX, final double maxY,
				final byte[] val) {
			final double fi0 = Math.floor((minX - pad - ox) * res), fi1 = Math.floor((maxX + pad - ox) * res);
			final double fj0 = Math.floor((minY - pad - oy) * res), fj1 = Math.floor((maxY + pad - oy) * res);
			if (fi1 < 0 || fj1 < 0 || fi0 >= w || fj0 >= h)
				return;
			final int i0 = (int) Math.max(0, fi0), i1 = (int) Math.min(w - 1, fi1);
			final int j0 = (int) Math.max(0, fj0), j1 = (int) Math.min(h - 1, fj1);
			for (int i = i0; i <= i1; i++)
				for (int j = j0; j <= j1; j++)
					val[i * h + j] = DIRTY;
		}

		/** Every lattice point of the region and two points per unit cell, against the exact test. */
		boolean verify(final Area area, final byte[] val, final long unitsW, final long unitsH) {
			for (long ux = 0; ux <= unitsW; ux++)
				for (long uy = 0; uy <= unitsH; uy++) {
					final double x = ox + ux, y = oy + uy;
					if (!agrees(area, val, x, y))
						return false;
					if (ux < unitsW && uy < unitsH && (!agrees(area, val, x + 0.5, y + 0.5)
							|| !agrees(area, val, x + 1.0 / 3, y + 2.0 / 3)))
						return false;
				}
			return true;
		}

		private boolean agrees(final Area area, final byte[] val, final double x, final double y) {
			final int k = index(x, y);
			return k < 0 || val[k] == 0 || (val[k] == TRUE) == area.contains(x, y);
		}

		private static boolean finite(final double[] c, final int count) {
			for (int i = 0; i < count; i++)
				if (!(Math.abs(c[i]) <= MAX_COORD))
					return false;
			return true;
		}
	}
}
