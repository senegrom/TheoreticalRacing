package tr.logic;

import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

/**
 * perf_legality: a track border that keeps an exact grid index of its own
 * segments, so the referee's wall scans ({@link TrackGeometry#segmentCrossesPath}
 * and {@link TrackGeometry#segmentCrossesPathBefore}) run their unchanged
 * per-segment test on the few segments near a move instead of on all of them.
 * Any structural change of the list (add, remove, clear) moves modCount and
 * retires the index; like every geometry cache, it assumes that border points
 * are never changed in place.
 */
final class BorderPoints extends LinkedList<int[]> {
	private static final long serialVersionUID = 1L;

	/** The index of the current contents, built on first use. Volatile: the
	 *  AI's thread and the map and potential threads share one border. */
	private transient volatile Grid grid;

	/** The index of the current contents; never null, perhaps unusable. */
	Grid grid() {
		final Grid current = grid;
		return current != null && current.modCount == modCount ? current : rebuild();
	}

	private synchronized Grid rebuild() {
		Grid current = grid;
		if (current == null || current.modCount != modCount) {
			current = Grid.of(this, modCount);
			grid = current;
		}
		return current;
	}

	/**
	 * Segment i (points i and i + 1) is listed in every 8x8 cell its bounding
	 * box touches. A query visits the cells of the move's bounding box and runs
	 * the scan's own test on every segment whose box overlaps the move's, once:
	 * in the first cell both boxes share.
	 *
	 * <p>Why every verdict is the full scan's. With every coordinate within
	 * LIMIT, each difference, product and sum the tests form is an integer below
	 * 2^52 in magnitude, so an exact double, and each quotient is the correctly
	 * rounded ratio of two such integers. Such a ratio is 0 or 1 exactly, or at
	 * least 2^-52 away from both, so it keeps its side of 0 and of 1 when
	 * rounded, and every comparison a test makes decides as on exact values:
	 * a test reports a hit only at a real common point of the move and the
	 * segment, which lies in both bounding boxes. A segment whose box misses
	 * the move's cannot report one, and the order of the tests is free -- each
	 * is a pure boolean, and the scan only asks whether any is true. Moves or
	 * borders beyond LIMIT, and outsized grids, keep the full scan.
	 */
	static final class Grid {
		private static final int SHIFT = 3;
		private static final int LIMIT = 1 << 24;
		private static final long MAX_CELLS = 1L << 20;
		private static final long MAX_ENTRIES = 1L << 22;

		final int modCount;
		private final int[][] points;
		private final int[] minX, minY, maxX, maxY;
		private final int cellX, cellY, cols, rows;
		private final int[] first, segments;

		private Grid(final int modCount, final int[][] points, final int[] minX, final int[] minY,
				final int[] maxX, final int[] maxY, final int cellX, final int cellY, final int cols,
				final int rows, final int[] first, final int[] segments) {
			this.modCount = modCount;
			this.points = points;
			this.minX = minX;
			this.minY = minY;
			this.maxX = maxX;
			this.maxY = maxY;
			this.cellX = cellX;
			this.cellY = cellY;
			this.cols = cols;
			this.rows = rows;
			this.first = first;
			this.segments = segments;
		}

		/** An index that answers for nothing: its callers scan. */
		private static Grid unusable(final int modCount) {
			return new Grid(modCount, null, null, null, null, null, 0, 0, 0, 0, null, null);
		}

		static Grid of(final List<int[]> border, final int modCount) {
			final int[][] points = border.toArray(new int[0][]);
			final int n = points.length - 1;
			if (n < 1)
				return unusable(modCount);
			for (final int[] p : points)
				if (p == null || p.length < 2 || p[0] < -LIMIT || p[0] > LIMIT || p[1] < -LIMIT || p[1] > LIMIT)
					return unusable(modCount);
			final int[] minX = new int[n], minY = new int[n], maxX = new int[n], maxY = new int[n];
			int x0 = Integer.MAX_VALUE, y0 = Integer.MAX_VALUE, x1 = Integer.MIN_VALUE, y1 = Integer.MIN_VALUE;
			for (int i = 0; i < n; i++) {
				final int[] a = points[i], b = points[i + 1];
				minX[i] = Math.min(a[0], b[0]);
				minY[i] = Math.min(a[1], b[1]);
				maxX[i] = Math.max(a[0], b[0]);
				maxY[i] = Math.max(a[1], b[1]);
				x0 = Math.min(x0, minX[i] >> SHIFT);
				y0 = Math.min(y0, minY[i] >> SHIFT);
				x1 = Math.max(x1, maxX[i] >> SHIFT);
				y1 = Math.max(y1, maxY[i] >> SHIFT);
			}
			final long cols = (long) x1 - x0 + 1, rows = (long) y1 - y0 + 1;
			long entries = 0;
			for (int i = 0; i < n; i++)
				entries += ((long) (maxX[i] >> SHIFT) - (minX[i] >> SHIFT) + 1)
						* ((long) (maxY[i] >> SHIFT) - (minY[i] >> SHIFT) + 1);
			if (cols * rows > MAX_CELLS || entries > MAX_ENTRIES)
				return unusable(modCount);
			final int height = (int) rows, cells = (int) (cols * rows);
			final int[] first = new int[cells + 1];
			for (int i = 0; i < n; i++)
				for (int gx = (minX[i] >> SHIFT) - x0; gx <= (maxX[i] >> SHIFT) - x0; gx++)
					for (int gy = (minY[i] >> SHIFT) - y0; gy <= (maxY[i] >> SHIFT) - y0; gy++)
						first[gx * height + gy + 1]++;
			for (int c = 0; c < cells; c++)
				first[c + 1] += first[c];
			final int[] next = Arrays.copyOf(first, cells);
			final int[] segments = new int[(int) entries];
			for (int i = 0; i < n; i++)
				for (int gx = (minX[i] >> SHIFT) - x0; gx <= (maxX[i] >> SHIFT) - x0; gx++)
					for (int gy = (minY[i] >> SHIFT) - y0; gy <= (maxY[i] >> SHIFT) - y0; gy++)
						segments[next[gx * height + gy]++] = i;
			return new Grid(modCount, points, minX, minY, maxX, maxY, x0, y0, (int) cols, height, first, segments);
		}

		/** Does the index answer for a move between these points? */
		boolean covers(final int x1, final int y1, final int x2, final int y2) {
			return points != null && x1 >= -LIMIT && x1 <= LIMIT && y1 >= -LIMIT && y1 <= LIMIT
					&& x2 >= -LIMIT && x2 <= LIMIT && y2 >= -LIMIT && y2 <= LIMIT;
		}

		/** {@link TrackGeometry#segmentCrossesPath} on this border. */
		boolean crossesPath(final int[] from, final int[] to) {
			return hits(from[0], from[1], to[0], to[1], from, to, 0, 0, 0, 0, false);
		}

		/** {@link TrackGeometry#segmentCrossesPathBefore} on this border, for a
		 *  move of positive length and a run-up within it (0 < until <= 1). */
		boolean crossesPathBefore(final int x1, final int y1, final int x2, final int y2, final double dx,
				final double dy, final double lengthSquared, final double until) {
			return hits(x1, y1, x2, y2, null, null, dx, dy, lengthSquared, until, true);
		}

		private boolean hits(final int x1, final int y1, final int x2, final int y2, final int[] from,
				final int[] to, final double dx, final double dy, final double lengthSquared,
				final double until, final boolean before) {
			final int loX = Math.min(x1, x2), hiX = Math.max(x1, x2);
			final int loY = Math.min(y1, y2), hiY = Math.max(y1, y2);
			final int gx0 = Math.max(loX >> SHIFT, cellX), gx1 = Math.min(hiX >> SHIFT, cellX + cols - 1);
			final int gy0 = Math.max(loY >> SHIFT, cellY), gy1 = Math.min(hiY >> SHIFT, cellY + rows - 1);
			for (int gx = gx0; gx <= gx1; gx++)
				for (int gy = gy0; gy <= gy1; gy++) {
					final int cell = (gx - cellX) * rows + gy - cellY;
					for (int k = first[cell], end = first[cell + 1]; k < end; k++) {
						final int s = segments[k];
						if (maxX[s] < loX || minX[s] > hiX || maxY[s] < loY || minY[s] > hiY
								|| Math.max(minX[s] >> SHIFT, gx0) != gx || Math.max(minY[s] >> SHIFT, gy0) != gy)
							continue;
						if (before
								? TrackGeometry.hitBefore(points[s], points[s + 1], x1, y1, dx, dy, lengthSquared, until)
								: TrackGeometry.checkIntersect(points[s], points[s + 1], from, to, (byte) 3))
							return true;
					}
				}
			return false;
		}
	}
}
