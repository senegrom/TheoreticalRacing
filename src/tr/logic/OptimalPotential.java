package tr.logic;

import java.awt.geom.Line2D;

/**
 * Exact distance-to-finish for a car alone on the track: for every
 * (position, velocity) and every count of gate events still owed, the fewest
 * moves in which the race can still be completed.
 *
 * <p>The gate maps answer "how far to the NEXT gate", which is not the same
 * question: the state you arrive at a gate in shapes the segment after it, so
 * descending them one at a time is not the shortest race. This potential folds
 * the gates remaining into the state, so its greedy descent is optimal by
 * construction -- and safe, because a state with a finite value always has a
 * successor one closer.
 *
 * <p>Every move costs one turn and every seed costs one turn, so this is a
 * plain breadth-first search backward from the finish rather than a weighted
 * one. It obeys the referee: a non-final gate passage must be an ordinarily
 * legal move, only the post-line part of a race-ending crossing is exempt. Rivals are not
 * modelled at all, which is exactly why the policy that uses it must first
 * check that none is near.
 */
final class OptimalPotential {

	/** Gate order within a lap: CP1, CP2, then the S/F crossing that scores it. */
	private static final int[] ORDER = {1, 2, 0 };
	/** Unreachable; distances are stored as moves + 1 so zero means "no value". */
	private static final short NONE = 0;

	private final int w, h, vmax, span, stages;
	private final short[] dist;

	private OptimalPotential(final int w, final int h, final int vmax, final int stages,
			final short[] dist) {
		this.w = w;
		this.h = h;
		this.vmax = vmax;
		this.span = 2 * vmax + 1;
		this.stages = stages;
		this.dist = dist;
	}

	/** Gate events still owed by a car on {@code lapsDone} laps whose next gate
	 *  is {@code nextGate}: the rest of this lap plus three per lap after it. */
	static int remainingEvents(final int nextGate, final int lapsDone, final int totalLaps) {
		final int inLap = nextGate == 1 ? 3 : nextGate == 2 ? 2 : 1;
		return inLap + 3 * (totalLaps - lapsDone - 1);
	}

	/** @return moves to finish, or {@link Integer#MAX_VALUE} if the race cannot
	 *  be completed from here. {@code remaining == 0} means already finished. */
	int movesToFinish(final int remaining, final int x, final int y, final int vx, final int vy) {
		if (remaining <= 0)
			return 0;
		if (remaining > stages || x < 0 || y < 0 || x >= w || y >= h
				|| vx < -vmax || vx > vmax || vy < -vmax || vy > vmax)
			return Integer.MAX_VALUE;
		final short d = dist[key(x, y, vx, vy, remaining)];
		return d == NONE ? Integer.MAX_VALUE : Short.toUnsignedInt(d) - 1;
	}

	private int key(final int x, final int y, final int vx, final int vy, final int remaining) {
		return (((x * h + y) * span + vx + vmax) * span + vy + vmax) * stages + remaining - 1;
	}


	/**
	 * Build the potential, or return null when the board is too large for the
	 * byte budget (the Nordschleife's 89M states would need 1.6 GB, and it is
	 * already within about a percent of optimal).
	 */
	static OptimalPotential build(final RaceGame game, final int totalLaps, final long budgetBytes) {
		if (game.lapGates == null)
			return null;
		final int w = game.gameCols + 1, h = game.gameRows + 1;
		final int vmax = RaceGame.AI_MAX_SPEED, span = 2 * vmax + 1;
		final int stages = 3 * totalLaps;
		final long states = (long) w * h * span * span;
		final long entries = states * stages;
		if (entries > Integer.MAX_VALUE || entries * Short.BYTES > budgetBytes)
			return null;
		final short[] dist = new short[(int) entries];
		final OptimalPotential map = new OptimalPotential(w, h, vmax, stages, dist);
		final IntList frontier = new IntList();

		// Seed every terminal predecessor, including a move that collects
		// CP2 (or CP1 and CP2) before the finish and lands beyond the grid.
		final Line2D sf = game.lapGates[0];
		for (int x = 0; x < w; x++)
			for (int y = 0; y < h; y++) {
				if (!Reachability.cellNearSegment(sf, x, y, 2 * vmax + 5))
					continue;
				for (int vx = -vmax; vx <= vmax; vx++)
					for (int vy = -vmax; vy <= vmax; vy++)
						for (int dvx = -1; dvx <= 1; dvx++)
							for (int dvy = -1; dvy <= 1; dvy++) {
								final int nvx = vx + dvx, nvy = vy + dvy;
								if (nvx < -vmax || nvx > vmax || nvy < -vmax || nvy > vmax)
									continue;
								final int nx = x + nvx, ny = y + nvy;
								if (!game.crossesFinish(x, y, nx, ny)
										|| !game.finishRunUpLegal(x, y, nx, ny))
									continue;
								for (int remaining = 1; remaining <= 3; remaining++) {
									final int pending = ORDER[(stages - remaining) % 3];
									if (game.gateEventsOnMove(pending, x, y, nx, ny) != remaining)
										continue;
									final int k = map.key(x, y, vx, vy, remaining);
									if (dist[k] == NONE) {
										dist[k] = 2; // one move, stored as moves + 1
										frontier.add(k);
									}
								}
							}
			}

		// Backward breadth-first search: every edge and every seed costs one
		// move, so a plain queue keeps the values exact.
		for (int read = 0; read < frontier.size; read++) {
			final int cur = frontier.data[read];
			final int next = Short.toUnsignedInt(dist[cur]) + 1;
			int rest = cur / stages;
			final int rNow = cur % stages + 1;
			final int nvy = rest % span - vmax;
			rest /= span;
			final int nvx = rest % span - vmax;
			rest /= span;
			final int ny = rest % h;
			final int nx = rest / h;
			final int x = nx - nvx, y = ny - nvy;
			if (x < 0 || y < 0 || x >= w || y >= h)
				continue;
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			for (int extra = 0; extra <= 3; extra++) {
				final int rPred = rNow + extra;
				if (rPred > stages)
					break;
				final int pending = ORDER[(stages - rPred) % 3];
				if (game.gateEventsOnMove(pending, x, y, nx, ny) != extra)
					continue;
				for (int dvx = -1; dvx <= 1; dvx++)
					for (int dvy = -1; dvy <= 1; dvy++) {
						final int vx = nvx - dvx, vy = nvy - dvy;
						if (vx < -vmax || vx > vmax || vy < -vmax || vy > vmax)
							continue;
						final int k = map.key(x, y, vx, vy, rPred);
						if (dist[k] == NONE) {
							if (next > 0xffff)
								throw new IllegalStateException("optimal potential distance exceeds storage range");
							dist[k] = (short) next;
							frontier.add(k);
						}
					}
			}
		}
		return map;
	}

	/**
	 * The move a car alone on the track should make: the successor with the
	 * lowest distance-to-finish. Ties go to the first direction in enum order,
	 * so the choice is reproducible. Returns null when no successor has a
	 * value, which leaves the caller on its ordinary policy.
	 */
	Direction bestMove(final RaceGame game, final int x, final int y, final int vx, final int vy,
			final int remaining) {
		if (remaining <= 0 || remaining > stages)
			return null;
		final int pending = ORDER[(stages - remaining) % 3];
		Direction best = null;
		int bestValue = Integer.MAX_VALUE;
		for (final Direction d : Direction.values()) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (nvx < -vmax || nvx > vmax || nvy < -vmax || nvy > vmax)
				continue;
			final int nx = x + nvx, ny = y + nvy;
			final int events = game.gateEventsOnMove(pending, x, y, nx, ny);
			final int after = remaining - events;
			if (after == 0) {
				if (game.finishRunUpLegal(x, y, nx, ny))
					return d;
				continue;
			}
			if (nx < 0 || ny < 0 || nx >= w || ny >= h
					|| !game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			final int value = movesToFinish(after, nx, ny, nvx, nvy);
			if (value < bestValue) {
				bestValue = value;
				best = d;
			}
		}
		return best;
	}

	/** Growable int list: the search queue, read once in order. */
	private static final class IntList {
		private int[] data = new int[1 << 16];
		private int size;

		void add(final int value) {
			if (size == data.length)
				data = java.util.Arrays.copyOf(data, data.length * 2);
			data[size++] = value;
		}
	}
}
