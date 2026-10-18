package tr.logic;

/** perf_aware (exact): the moves of suppressed scorer decisions, shared within one
 *  top-level decision (or one standalone rollout).
 *
 *  A suppressed decision -- computeAiMove under inScorerSim, the move of every scorer
 *  car in a rollout -- starts no rollout and no nested decision. It reads the board
 *  RaceAi.scorerMoveOverState installs (every car's position, velocity, finished flag,
 *  lap and next gate, the mover's slot and the turn counter), the decider's grid world
 *  (RaceGame.aiGridLegal) and the race's fixed course and maps; every other field it
 *  reads it rewrites first or holds as a pure cache. Its direction is therefore a
 *  function of this key, and a stored direction replays exactly.
 *
 *  Keys are compared in full; the hash only finds them. RaceAi clears the memo before
 *  every top-level decision and every standalone rollout. A full memo stops storing,
 *  which only recomputes.
 *
 *  perf (upmemo): RaceAi also keeps two smaller instances for the moves of upgraded
 *  (aware) forecast decisions over a whole race -- the same key, in one fixed context
 *  and a validated race world (RaceAi.upgradedMemoOn). */
final class RaceAiMoveMemo {
	static final int MISS = -2;
	private static final int NO_MOVE = -1;
	private static final Direction[] DIRECTIONS = Direction.values();
	/** The caps: a memo holding maxEntries keys, or whose next key would take its pool
	 *  past maxPoolInts ints, stops storing. */
	private final int maxPoolInts;
	private final int maxEntries;
	private int[] pool = new int[1 << 12];
	private int top;
	private int[] offsets = new int[1 << 8];
	private long[] hashes = new long[1 << 8];
	private byte[] moves = new byte[1 << 8];
	private int count;
	private int[] table = new int[1 << 9];
	/** Bumped by every lookup, store and clear: a store commits the key its own lookup
	 *  left at the pool's free end only while nothing else has run since. */
	private long stamp;
	private long pendingStamp = -1;
	private long pendingHash;
	private int pendingLength;

	/** The suppressed-move memo: 1 << 16 entries, 1 << 21 pool ints. */
	RaceAiMoveMemo() {
		this(1 << 16, 1 << 21);
	}

	RaceAiMoveMemo(final int maxEntries, final int maxPoolInts) {
		this.maxEntries = maxEntries;
		this.maxPoolInts = maxPoolInts;
	}

	/** The entries stored since the last clear. */
	int size() {
		return count;
	}

	/** The stored code of a decision: its direction's ordinal, or NO_MOVE for none. */
	static int code(final Direction move) {
		return move == null ? NO_MOVE : move.ordinal();
	}

	void clear() {
		stamp++;
		if (count > 0)
			java.util.Arrays.fill(table, 0);
		count = 0;
		top = 0;
	}

	/** The decision a stored code stands for: a direction, or null. */
	static Direction move(final int code) {
		return code == NO_MOVE ? null : DIRECTIONS[code];
	}

	/** The stored move code for this board, or MISS; a miss leaves its key pending
	 *  for {@link #store}. */
	int find(final int mover, final int turns, final boolean gridLegal, final int[] px, final int[] py,
			final int[] vx, final int[] vy, final boolean[] alive, final int[] laps, final int[] gates) {
		stamp++;
		final int length = build(mover, turns, gridLegal, px, py, vx, vy, alive, laps, gates);
		if (length < 0)
			return MISS;
		final long hash = hash(length);
		final int entry = locate(hash, length);
		if (entry >= 0)
			return moves[entry];
		pendingStamp = stamp;
		pendingHash = hash;
		pendingLength = length;
		return MISS;
	}

	/** Record the decision taken on the board of the last lookup, which missed. It is
	 *  dropped -- only a later recomputation -- when any lookup, store or clear ran in
	 *  between (which may have overwritten that key), or when the memo is full. */
	void store(final Direction move) {
		if (pendingStamp != stamp)
			return;
		stamp++;
		if (count >= maxEntries)
			return;
		final long hash = pendingHash;
		final int length = pendingLength;
		if (count == offsets.length) {
			final int capacity = 2 * offsets.length;
			offsets = java.util.Arrays.copyOf(offsets, capacity);
			hashes = java.util.Arrays.copyOf(hashes, capacity);
			moves = java.util.Arrays.copyOf(moves, capacity);
		}
		if (2 * (count + 1) > table.length) {
			table = new int[2 * table.length];
			for (int e = 0; e < count; e++)
				insert(e);
		}
		final int entry = count++;
		offsets[entry] = top;
		hashes[entry] = hash;
		moves[entry] = (byte) (move == null ? NO_MOVE : move.ordinal());
		top += length;
		insert(entry);
	}

	/** Write the key at the pool's free end; its length, or -1 when the pool is full. */
	private int build(final int mover, final int turns, final boolean gridLegal, final int[] px,
			final int[] py, final int[] vx, final int[] vy, final boolean[] alive, final int[] laps,
			final int[] gates) {
		final int n = px.length;
		final int length = 4 + 7 * n;
		if (length > maxPoolInts - top)
			return -1;
		if (top + length > pool.length)
			pool = java.util.Arrays.copyOf(pool, Math.min(maxPoolInts, Math.max(2 * pool.length, top + length)));
		int at = top;
		pool[at++] = mover;
		pool[at++] = n;
		pool[at++] = turns;
		pool[at++] = gridLegal ? 1 : 0;
		for (int j = 0; j < n; j++) {
			pool[at++] = px[j];
			pool[at++] = py[j];
			pool[at++] = vx[j];
			pool[at++] = vy[j];
			pool[at++] = alive[j] ? 1 : 0;
			pool[at++] = laps[j];
			pool[at++] = gates[j];
		}
		return length;
	}

	private long hash(final int length) {
		long h = 0xCBF29CE484222325L;
		for (int k = top, end = top + length; k < end; k++) {
			h ^= pool[k];
			h *= 0x100000001B3L;
		}
		h ^= h >>> 33;
		h *= 0xFF51AFD7ED558CCDL;
		h ^= h >>> 33;
		h *= 0xC4CEB9FE1A85EC53L;
		return h ^ h >>> 33;
	}

	/** The entry holding the key just built at the pool's free end, or -1. */
	private int locate(final long hash, final int length) {
		final int mask = table.length - 1;
		for (int slot = (int) hash & mask; table[slot] != 0; slot = slot + 1 & mask) {
			final int entry = table[slot] - 1;
			if (hashes[entry] == hash && sameKey(offsets[entry], length))
				return entry;
		}
		return -1;
	}

	/** Every key holds its car count second, so equal keys have equal lengths; an
	 *  entry of another length differs by then and is never read past its end. */
	private boolean sameKey(final int offset, final int length) {
		for (int k = 0; k < length; k++) {
			if (pool[offset + k] != pool[top + k])
				return false;
		}
		return true;
	}

	private void insert(final int entry) {
		final int mask = table.length - 1;
		int slot = (int) hashes[entry] & mask;
		while (table[slot] != 0)
			slot = slot + 1 & mask;
		table[slot] = entry + 1;
	}
}
