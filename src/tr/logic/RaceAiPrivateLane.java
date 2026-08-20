package tr.logic;

/**
 * Adversarial private-lane proof used by {@link RaceAi}'s pace overrides.
 *
 * <p>The API surface is deliberately narrow: one proof session owns the
 * conservative rival rectangles plus the lazily-created exact fallback. A
 * session must span the complete candidate loop so its cache and fail-closed
 * node budget retain the champion's ordering semantics.</p>
 */
final class RaceAiPrivateLane {
	private static final Direction[] DIRECTIONS = Direction.values();

	private final RaceGame game;
	private final Reachability reach;

	RaceAiPrivateLane(final RaceGame game) {
		this.game = game;
		reach = game.reach;
	}

	final class ProofSession {
		private final int playerNum;
		private final RivalReach rectangles;
		private final int exactNodeBudget;
		private ExactRivalReach exact;

		private ProofSession(final int playerNum, final RivalReach rectangles,
				final int exactNodeBudget) {
			this.playerNum = playerNum;
			this.rectangles = rectangles;
			this.exactNodeBudget = exactNodeBudget;
		}

		boolean certifiesApproximate(final int x, final int y, final int vx, final int vy,
				final int turns, final int horizon, final int requiredEscapes) {
			return privatePaceCertificate(x, y, vx, vy, turns, rectangles, 0, horizon,
					requiredEscapes);
		}

		boolean certifiesExact(final int x, final int y, final int vx, final int vy,
				final int turns, final int horizon, final int requiredEscapes) {
			if (exact == null)
				exact = new ExactRivalReach(game, reach, playerNum, rectangles, exactNodeBudget);
			return privatePaceCertificate(x, y, vx, vy, turns, exact, 0, horizon,
					requiredEscapes);
		}
	}

	ProofSession begin(final int playerNum, final int horizon, final int exactNodeBudget) {
		return new ProofSession(playerNum, rivalReach(playerNum, horizon), exactNodeBudget);
	}

	/** Occupancy oracle used by the private-lane pace proof. */
	private interface RivalOccupancy {
		boolean mayOccupy(int ply, int x, int y);
	}

	/** Kinematic over-approximation of every cell any live rival can occupy
	 * after each of its next moves. Per axis, after {@code ply} moves the
	 * acceleration contribution is bounded by +/-ply*(ply+1)/2. Geometry,
	 * velocity caps, finishes and collisions are intentionally ignored, making
	 * each rectangle a superset of the rival's real reachable cells. A cell
	 * outside every rectangle is therefore physically unreachable under any
	 * rival policy. */
	private static final class RivalReach implements RivalOccupancy {
		final int[][] minX;
		final int[][] maxX;
		final int[][] minY;
		final int[][] maxY;
		final int rivals;

		RivalReach(final int horizon, final int rivals) {
			minX = new int[horizon + 1][rivals];
			maxX = new int[horizon + 1][rivals];
			minY = new int[horizon + 1][rivals];
			maxY = new int[horizon + 1][rivals];
			this.rivals = rivals;
		}

		@Override
		public boolean mayOccupy(final int ply, final int x, final int y) {
			for (int rival = 0; rival < rivals; rival++) {
				if (x >= minX[ply][rival] && x <= maxX[ply][rival]
						&& y >= minY[ply][rival] && y <= maxY[ply][rival])
					return true;
			}
			return false;
		}
	}

	private RivalReach rivalReach(final int playerNum, final int horizon) {
		int rivalCount = 0;
		for (final Player p : game.players)
			if (p.getNumber() != playerNum && !p.isFinished())
				rivalCount++;
		final RivalReach result = new RivalReach(horizon, rivalCount);
		int rival = 0;
		for (final Player p : game.players) {
			if (p.getNumber() == playerNum || p.isFinished())
				continue;
			final int[] pp = p.getPosition();
			final int[] pv = p.getVelocity();
			for (int ply = 1; ply <= horizon; ply++) {
				final int accelerationReach = ply * (ply + 1) / 2;
				final long projectedX = (long) pp[0] + (long) ply * pv[0];
				final long projectedY = (long) pp[1] + (long) ply * pv[1];
				result.minX[ply][rival] = saturatingInt(projectedX - accelerationReach);
				result.maxX[ply][rival] = saturatingInt(projectedX + accelerationReach);
				result.minY[ply][rival] = saturatingInt(projectedY - accelerationReach);
				result.maxY[ply][rival] = saturatingInt(projectedY + accelerationReach);
			}
			rival++;
		}
		return result;
	}

	/** Tiny primitive int-to-byte map for targeted occupancy answers. Unlike a
	 * board-sized array, its cost scales with the handful of cells the bounded
	 * certificate actually asks about. */
	private static final class IntByteCache {
		private int[] keys = new int[128];
		private byte[] values = new byte[128];
		private int size;

		byte get(final int key) {
			int slot = IntFrontier.mix(key) & (keys.length - 1);
			final int stored = key + 1;
			while (keys[slot] != 0) {
				if (keys[slot] == stored)
					return values[slot];
				slot = slot + 1 & (keys.length - 1);
			}
			return 0;
		}

		void put(final int key, final byte value) {
			if ((size + 1) * 2 >= keys.length)
				rehash(keys.length << 1);
			int slot = IntFrontier.mix(key) & (keys.length - 1);
			final int stored = key + 1;
			while (keys[slot] != 0) {
				if (keys[slot] == stored) {
					values[slot] = value;
					return;
				}
				slot = slot + 1 & (keys.length - 1);
			}
			keys[slot] = stored;
			values[slot] = value;
			size++;
		}

		private void rehash(final int capacity) {
			final int[] oldKeys = keys;
			final byte[] oldValues = values;
			keys = new int[capacity];
			values = new byte[capacity];
			size = 0;
			for (int i = 0; i < oldKeys.length; i++)
				if (oldKeys[i] != 0)
					put(oldKeys[i] - 1, oldValues[i]);
		}
	}

	/** Small primitive set/list used by the bounded targeted occupancy search.
	 * The exact fallback explores at most a few thousand states, so avoiding
	 * boxed Integer nodes keeps its fail-closed budget cheap and predictable. */
	private static final class IntFrontier {
		private int[] values = new int[64];
		private int[] table = new int[128];
		private int size;

		void clear() {
			java.util.Arrays.fill(table, 0);
			size = 0;
		}

		int size() {
			return size;
		}

		int get(final int index) {
			return values[index];
		}

		void add(final int value) {
			if ((size + 1) * 2 >= table.length)
				rehash(table.length << 1);
			int slot = mix(value) & (table.length - 1);
			final int stored = value + 1;
			while (table[slot] != 0) {
				if (table[slot] == stored)
					return;
				slot = slot + 1 & (table.length - 1);
			}
			table[slot] = stored;
			if (size == values.length)
				values = java.util.Arrays.copyOf(values, values.length << 1);
			values[size++] = value;
		}

		private void rehash(final int capacity) {
			table = new int[capacity];
			for (int i = 0; i < size; i++) {
				final int value = values[i];
				int slot = mix(value) & (capacity - 1);
				while (table[slot] != 0)
					slot = slot + 1 & (capacity - 1);
				table[slot] = value + 1;
			}
		}

		static int mix(final int value) {
			int mixed = value * 0x9E3779B9;
			mixed ^= mixed >>> 16;
			return mixed;
		}
	}

	/** Geometry-clipped targeted fallback for rectangular false positives.
	 * For each queried cell it expands every speed-valid, geometry-valid rival
	 * acceleration sequence that can still kinematically reach that cell.
	 * Collisions are deliberately ignored, which can only add rival paths.
	 * Exhausting the shared node budget reports "may occupy", so the proof
	 * remains conservative and the runtime cost is hard-bounded per real move. */
	private static final class ExactRivalReach implements RivalOccupancy {
		private final RaceGame game;
		private final Reachability reach;
		private final RivalReach rectangle;
		private final int[] starts;
		private final int span;
		private final int vmax;
		private final int height;
		private final int width;
		private final int cells;
		private final IntByteCache cache = new IntByteCache();
		private IntFrontier current = new IntFrontier();
		private IntFrontier next = new IntFrontier();
		private int nodesLeft;

		ExactRivalReach(final RaceGame game, final Reachability reach,
				final int playerNum, final RivalReach rectangle, final int nodesLeft) {
			this.game = game;
			this.reach = reach;
			this.rectangle = rectangle;
			this.nodesLeft = nodesLeft;
			span = reach.aliveSpan;
			vmax = reach.aliveVMAX;
			height = reach.aliveH;
			width = reach.aliveW;
			cells = width * height;
			starts = new int[rectangle.rivals];
			int index = 0;
			for (final Player p : game.players) {
				if (p.getNumber() == playerNum || p.isFinished())
					continue;
				final int[] position = p.getPosition();
				final int[] velocity = p.getVelocity();
				starts[index++] = reach.aliveIdx(position[0], position[1], velocity[0], velocity[1]);
			}
		}

		@Override
		public boolean mayOccupy(final int ply, final int targetX, final int targetY) {
			if (!rectangle.mayOccupy(ply, targetX, targetY))
				return false;
			if (targetX < 0 || targetX >= width || targetY < 0 || targetY >= height)
				return false;
			final int key = ply * cells + targetX * height + targetY;
			final byte cached = cache.get(key);
			if (cached != 0)
				return cached == 2;
			final boolean occupied = search(ply, targetX, targetY);
			cache.put(key, (byte) (occupied ? 2 : 1));
			return occupied;
		}

		private boolean search(final int ply, final int targetX, final int targetY) {
			if (nodesLeft <= 0)
				return true;
			current.clear();
			next.clear();
			for (final int packed : starts)
				if (packedEnvelopeContains(packed, ply, targetX, targetY))
					current.add(packed);
			for (int step = 1; step <= ply && current.size() != 0; step++) {
				next.clear();
				final int remaining = ply - step;
				for (int i = 0; i < current.size(); i++) {
					if (--nodesLeft < 0)
						return true;
					int state = current.get(i);
					final int vy = state % span - vmax;
					state /= span;
					final int vx = state % span - vmax;
					state /= span;
					final int y = state % height;
					final int x = state / height;
					for (final Direction d : DIRECTIONS) {
						final int nvx = vx + d.dx, nvy = vy + d.dy;
						if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
							continue;
						final int nx = x + nvx, ny = y + nvy;
						if (game.crossesFinish(x, y, nx, ny))
							continue;
						if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
							continue;
						if (remaining == 0) {
							if (nx == targetX && ny == targetY)
								return true;
						} else if (envelopeContains(nx, ny, nvx, nvy, remaining, targetX, targetY)) {
							next.add(reach.aliveIdx(nx, ny, nvx, nvy));
						}
					}
				}
				final IntFrontier swap = current;
				current = next;
				next = swap;
			}
			return false;
		}

		private boolean packedEnvelopeContains(final int packed, final int steps,
				final int targetX, final int targetY) {
			int state = packed;
			final int vy = state % span - vmax;
			state /= span;
			final int vx = state % span - vmax;
			state /= span;
			final int y = state % height;
			final int x = state / height;
			return envelopeContains(x, y, vx, vy, steps, targetX, targetY);
		}

		private static boolean envelopeContains(final int x, final int y, final int vx, final int vy,
				final int steps, final int targetX, final int targetY) {
			final int accelerationReach = steps * (steps + 1) / 2;
			return Math.abs((long) targetX - ((long) x + (long) steps * vx)) <= accelerationReach
					&& Math.abs((long) targetY - ((long) y + (long) steps * vy)) <= accelerationReach;
		}
	}

	/** Count distinct private, alive one-move exits; crossing the finish is terminal success. */
	private int countPrivateEscapes(final int x, final int y, final int vx, final int vy,
			final RivalOccupancy rivals, final int rivalPly, final int requiredEscapes) {
		int count = 0;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return requiredEscapes;
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			if (rivals.mayOccupy(rivalPly, nx, ny))
				continue;
			if (reach.isAlive(nx, ny, nvx, nvy) && ++count >= requiredEscapes)
				return requiredEscapes;
		}
		return count;
	}

	private boolean privatePaceCertificate(final int x, final int y, final int vx, final int vy,
			final int turns, final RivalOccupancy rivals, final int ply, final int horizon,
			final int requiredEscapes) {
		if (countPrivateEscapes(x, y, vx, vy, rivals, ply + 1, requiredEscapes) >= requiredEscapes)
			return true;
		if (ply >= horizon)
			return false;
		for (final Direction d : DIRECTIONS) {
			final int nvx = vx + d.dx, nvy = vy + d.dy;
			if (RaceGame.aiVelocityOutOfRange(nvx, nvy))
				continue;
			final int nx = x + nvx, ny = y + nvy;
			if (game.crossesFinish(x, y, nx, ny))
				return true;
			if (!game.isMoveLegalGeometryCached(x, y, nx, ny))
				continue;
			if (rivals.mayOccupy(ply + 1, nx, ny))
				continue;
			if (!reach.isAlive(nx, ny, nvx, nvy))
				continue;
			final int nextTurns = reach.turnsToFinish(nx, ny, nvx, nvy);
			if (nextTurns >= turns)
				continue;
			if (privatePaceCertificate(nx, ny, nvx, nvy, nextTurns, rivals, ply + 1, horizon,
					requiredEscapes))
				return true;
		}
		return false;
	}

	private static int saturatingInt(final long value) {
		return value < Integer.MIN_VALUE ? Integer.MIN_VALUE
				: value > Integer.MAX_VALUE ? Integer.MAX_VALUE : (int) value;
	}
}
