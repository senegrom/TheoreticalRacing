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
		return build(game, totalLaps, budgetBytes, budgetBytes);
	}

	/** The retained-distance limit and total construction limit are separate:
	 * production keeps the historical distance-map eligibility while reserving
	 * additional, bounded room for the pending FIFO. Tests may pass one shared
	 * limit through the three-argument overload above. */
	static OptimalPotential build(final RaceGame game, final int totalLaps,
			final long distanceBudgetBytes, final long totalBudgetBytes) {
		if (game.lapGates == null)
			return null;
		final int w = game.gameCols + 1, h = game.gameRows + 1;
		final int vmax = RaceGame.AI_MAX_SPEED, span = 2 * vmax + 1;
		final int stages = 3 * totalLaps;
		final long states = (long) w * h * span * span;
		final long entries = states * stages;
		final long distanceBytes = entries * Short.BYTES;
		if (entries > Integer.MAX_VALUE || distanceBytes > distanceBudgetBytes)
			return null;
		// The total budget also covers the live frontier. The circular queue
		// retains only pending states and refuses to grow past this allowance.
		final long queueBytes = totalBudgetBytes - distanceBytes;
		if (queueBytes < 1024L * Integer.BYTES)
			return null;
		final short[] dist = new short[(int) entries];
		final OptimalPotential map = new OptimalPotential(w, h, vmax, stages, dist);
		final IntQueue frontier = new IntQueue((int) Math.min(Integer.MAX_VALUE, queueBytes / Integer.BYTES));
		try {

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
		// move, so FIFO order keeps the values exact.
		while (!frontier.isEmpty()) {
			final int cur = frontier.remove();
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
		} catch (final FrontierBudgetExceeded ignored) {
			return null;
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

	long retainedBytes() { return (long) dist.length * Short.BYTES; }

	private static final class FrontierBudgetExceeded extends RuntimeException {
		private static final long serialVersionUID = 1L;
	}

	/** Circular FIFO: processed states are released immediately. The capacity
	 * is bounded by the caller's construction-memory budget. */
	private static final class IntQueue {
		private int[] data;
		private int head, size;
		private final int maxCapacity;

		IntQueue(final int maxCapacity) {
			this.maxCapacity = Math.max(1024, maxCapacity);
			data = new int[Math.min(1 << 16, this.maxCapacity)];
		}

		boolean isEmpty() { return size == 0; }

		void add(final int value) {
			if (size == data.length) grow();
			int tail = head + size;
			if (tail >= data.length) tail -= data.length;
			data[tail] = value; size++;
		}

		int remove() {
			final int value = data[head];
			if (++head == data.length) head = 0;
			size--; return value;
		}

		private void grow() {
			if (data.length >= maxCapacity)
				throw new FrontierBudgetExceeded();
			final int next = data.length <= maxCapacity / 2 ? data.length << 1 : maxCapacity;
			final int[] larger = new int[next];
			final int first = Math.min(size, data.length - head);
			System.arraycopy(data, head, larger, 0, first);
			System.arraycopy(data, 0, larger, first, size - first);
			data = larger; head = 0;
		}
	}
}
