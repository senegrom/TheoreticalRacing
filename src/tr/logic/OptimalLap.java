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

	/** Growable int list: a BFS level is filled once and then read once. */
	private static final class IntList {
		private int[] data = new int[1024];
		private int size;

		void add(final int value) {
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
		final int stages = 3 * laps;
		final long cells = (long) w * h * span * span;
		if (cells * stages > Integer.MAX_VALUE)
			throw new IllegalStateException("optimal-lap state space too large: " + cells * stages);
		final int total = (int) cells;
		final BitSet seen = new BitSet(total * stages);
		IntList frontier = new IntList();
		IntList next = new IntList();
		final int start = (((startX * h + startY) * span + vmax) * span + vmax) * stages;
		seen.set(start);
		frontier.add(start);
		int level = 0;
		long visited = 1;
		while (frontier.size > 0) {
			level++;
			for (int i = 0; i < frontier.size; i++) {
				final int key = frontier.data[i];
				final int stage = key % stages;
				int rest = key / stages;
				final int vy = rest % span - vmax;
				rest /= span;
				final int vx = rest % span - vmax;
				rest /= span;
				final int y = rest % h;
				final int x = rest / h;
				final int pending = ORDER[stage % 3];
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
							if (game.crossesFinish(x, y, nx, ny))
								ns++;
						} else if (game.touchesGate(pending, x, y, nx, ny)) {
							ns++;
							// the referee tests CP1 then CP2 within one move, so a
							// single move can take both
							if (pending == 1 && game.touchesGate(2, x, y, nx, ny))
								ns++;
						}
						final boolean finishes = ns == stages;
						if (!finishes && !game.isMoveLegalGeometryCached(x, y, nx, ny))
							continue;
						if (finishes) {
							System.out.println("[optimal] states=" + visited
									+ " frontier-levels=" + level);
							return level;
						}
						final int nkey = (((nx * h + ny) * span + nvx + vmax) * span + nvy + vmax)
								* stages + ns;
						if (!seen.get(nkey)) {
							seen.set(nkey);
							visited++;
							next.add(nkey);
						}
					}
				}
			}
			final IntList swap = frontier;
			frontier = next;
			next = swap;
			next.size = 0;
		}
		System.out.println("[optimal] states=" + visited + " -- no completion found");
		return -1;
	}
}
