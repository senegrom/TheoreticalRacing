package tr.logic;

import java.util.BitSet;

/**
 * Exact shortest solo race: the fewest moves in which one car, alone on the
 * track, can complete the configured laps.
 *
 * <p>Every move costs one turn, so a breadth-first search over
 * (position, velocity, gates completed) is exact rather than heuristic. The
 * search obeys the REFEREE's rules and none of the AI's self-imposed ones: a
 * non-final gate passage must be an ordinarily legal move, the race-ending
 * crossing is legality-waived, and nothing has to be shedable, certified or
 * reachability-alive. That is deliberate -- pruning to the AI's own alive set
 * would measure the AI against its own conservatism instead of against the
 * game. The one shared limit is the velocity domain (|v| <= AI_MAX_SPEED per
 * axis), which is the AI's movement vocabulary.
 */
final class OptimalLap {

	private OptimalLap() {}

	/** Growable long list: a BFS level is filled once and then read once. */
	private static final class LongList {
		private long[] data = new long[1024];
		private int size;

		void add(final long value) {
			if (size == data.length)
				data = java.util.Arrays.copyOf(data, data.length * 2);
			data[size++] = value;
		}
	}

	/** Gate order within a lap: CP1, CP2, then the S/F crossing that scores it. */
	private static final int[] ORDER = {1, 2, 0 };

	/** @return the minimum number of moves, or -1 if the race cannot be completed. */
	static int solve(final RaceGame game, final int startX, final int startY, final int laps) {
		final int w = game.gameCols + 1, h = game.gameRows + 1;
		final int vmax = RaceGame.AI_MAX_SPEED, span = 2 * vmax + 1;
		// A track whose boundary cannot close has no gates: the race is one
		// forward crossing of the finish, so there is a single stage and the
		// checkpoints never enter. Everything else below is unchanged.
		final boolean gated = game.lapGates != null;
		final int stages = gated ? 3 * laps : 1;
		final long cells = (long) w * h * span * span;
		if (cells > Integer.MAX_VALUE)
			throw new IllegalStateException("optimal-lap board too large: " + cells);
		final int total = (int) cells;
		// One visited set per stage rather than one over the product: ten laps
		// on a 500-cell board would overflow a single int-indexed BitSet.
		final BitSet[] seen = new BitSet[stages];
		for (int s = 0; s < stages; s++)
			seen[s] = new BitSet(total);
		LongList frontier = new LongList();
		LongList next = new LongList();
		final int startIdx = ((startX * h + startY) * span + vmax) * span + vmax;
		seen[0].set(startIdx);
		frontier.add((long) startIdx * stages);
		int level = 0;
		long visited = 1;
		while (frontier.size > 0) {
			level++;
			for (int i = 0; i < frontier.size; i++) {
				final long key = frontier.data[i];
				final int stage = (int) (key % stages);
				int rest = (int) (key / stages);
				final int vy = rest % span - vmax;
				rest /= span;
				final int vx = rest % span - vmax;
				rest /= span;
				final int y = rest % h;
				final int x = rest / h;
				final int pending = gated ? ORDER[stage % 3] : 0;
				for (int dvx = -1; dvx <= 1; dvx++) {
					for (int dvy = -1; dvy <= 1; dvy++) {
						final int nvx = vx + dvx, nvy = vy + dvy;
						if (nvx < -vmax || nvx > vmax || nvy < -vmax || nvy > vmax)
							continue;
						final int nx = x + nvx, ny = y + nvy;
						if (nx < 0 || ny < 0 || nx >= w || ny >= h)
							continue;
						int ns = stage;
						if (pending == 0) {
							if (game.crossesFinish(x, y, nx, ny)
									&& game.finishRunUpLegal(x, y, nx, ny))
								ns++;
						} else if (game.touchesGate(pending, x, y, nx, ny)) {
							ns++;
							// the referee tests CP1 then CP2 within one move, so a
							// single move can take both
							if (pending == 1 && game.touchesGate(2, x, y, nx, ny))
								ns++;
						}
						final boolean finishes = ns == stages;
						// The referee waives legality on the race-ending crossing, so a
						// car may finish THROUGH a wall from a neighbouring fold. Set
						// tr.strictFinish to require an ordinarily legal move there too
						// and measure what that permission is worth.
						if (!finishes && !game.isMoveLegalGeometryCached(x, y, nx, ny))
							continue;
						if (finishes) {
							System.out.println("[optimal] states=" + visited
									+ " frontier-levels=" + level);
							return level;
						}
						final int nidx = ((nx * h + ny) * span + nvx + vmax) * span + nvy + vmax;
						if (!seen[ns].get(nidx)) {
							seen[ns].set(nidx);
							visited++;
							next.add((long) nidx * stages + ns);
						}
					}
				}
			}
			final LongList swap = frontier;
			frontier = next;
			next = swap;
			next.size = 0;
		}
		System.out.println("[optimal] states=" + visited + " -- no completion found");
		return -1;
	}
}
