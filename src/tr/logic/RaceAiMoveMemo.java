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
 *  perf_packkey (exact): a key is one header word and one word per car, each value in
 *  bits of its own, so two boards have equal keys exactly when they are equal. A board
 *  with a value outside its bits (build) is neither looked up nor stored, which only
 *  recomputes; no board of a race has one.
 *
 *  perf (upmemo): RaceAi also keeps two smaller instances for the moves of upgraded
 *  (aware) forecast decisions over a whole race -- the same key, in one fixed context,
 *  a validated race world and one chooser horizon (RaceAi.upgradedMemoOn,
 *  maintainUpgradedMemo). */
final class RaceAiMoveMemo {
	static final int MISS = -2;
	private static final int NO_MOVE = -1;
	private static final Direction[] DIRECTIONS = Direction.values();
	/** perf_packkey: a car's word holds x, vx and lap in its low half, y, vy, gate and the
	 *  alive bit in its high half (build). A position counts POS_BITS from Player.INIT_POS,
	 *  -100000 to 31071; a velocity SMALL_BITS from -64, to 63; a lap or a gate SMALL_BITS
	 *  from 0, to 127. The header holds the whole turn counter in its high half, and the
	 *  mover and the car count in HEAD_BITS each above the grid world's bit. A race stays
	 *  inside them: at most nine cars, 500 cells a side, 99 laps and three gates; a dead car
	 *  stands at INIT_POS or, in a rollout, on its last cell or its finishing move's
	 *  landing; a velocity changes by one a move, so 64 would take a run-up of 2,000 cells.
	 *  Only a query can place a finished car elsewhere (it checks live cars' positions). */
	private static final int POS_BITS = 17, POS_BIAS = -Player.INIT_POS;
	private static final int SMALL_BITS = 7, VEL_BIAS = 64;
	private static final int HEAD_BITS = 15;
	/** The caps: a memo holding maxEntries keys, or whose next key would take its pool
	 *  past maxPoolLongs words, stops storing. A key is at most ten words (nine cars), so
	 *  RaceAi's instances reach maxEntries first; the pool's cap bounds their bytes. */
	private final int maxPoolLongs;
	private final int maxEntries;
	private long[] pool = new long[1 << 11];
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

	/** The suppressed-move memo: 1 << 16 entries, 1 << 20 pool words. */
	RaceAiMoveMemo() {
		this(1 << 16, 1 << 21);
	}

	/** maxPoolInts is the pool's memory in ints, two to a word. */
	RaceAiMoveMemo(final int maxEntries, final int maxPoolInts) {
		this.maxEntries = maxEntries;
		this.maxPoolLongs = maxPoolInts / 2;
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
	 *  for {@link #store}, unless the pool is full or a value does not fit (build). */
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

	/** Write the key at the pool's free end; its length in words, or -1 when the pool is
	 *  full or a value does not fit its bits. Every value is checked, so a key stands for
	 *  one board. The fields go together in int arithmetic and each car's two halves into
	 *  one long: shifts and ors, no multiplication, for CheerpJ's long arithmetic too. */
	private int build(final int mover, final int turns, final boolean gridLegal, final int[] px,
			final int[] py, final int[] vx, final int[] vy, final boolean[] alive, final int[] laps,
			final int[] gates) {
		final int n = px.length;
		final int length = 1 + n;
		if (length > maxPoolLongs - top)
			return -1;
		if (top + length > pool.length)
			pool = java.util.Arrays.copyOf(pool, Math.min(maxPoolLongs, Math.max(2 * pool.length, top + length)));
		int over = (mover | n) >>> HEAD_BITS;
		int at = top;
		pool[at++] = (long) turns << 32 | (mover << HEAD_BITS + 1 | n << 1 | (gridLegal ? 1 : 0));
		for (int j = 0; j < n; j++) {
			final int x = px[j] + POS_BIAS, y = py[j] + POS_BIAS;
			final int dx = vx[j] + VEL_BIAS, dy = vy[j] + VEL_BIAS;
			final int lap = laps[j], gate = gates[j];
			over |= (x | y) >>> POS_BITS | (dx | dy | lap | gate) >>> SMALL_BITS;
			final int low = x | dx << POS_BITS | lap << POS_BITS + SMALL_BITS;
			final int high = y | dy << POS_BITS | gate << POS_BITS + SMALL_BITS | (alive[j] ? 1 << 31 : 0);
			pool[at++] = (long) high << 32 | low;
		}
		return over == 0 ? length : -1;
	}

	/** Each word's multiplication stands off the chain, so they overlap; h ^ h >>> 7 brings
	 *  a word's high bits down before the next one is added, and keeps them apart over ten
	 *  words: a shift of 32 undoes itself every second word, so two alternate cars' high
	 *  bits (an alive flag, a gate, vy) could cancel to one hash. */
	private long hash(final int length) {
		long h = 0xCBF29CE484222325L;
		for (int k = top, end = top + length; k < end; k++)
			h = (h ^ h >>> 7) + pool[k] * 0x9E3779B97F4A7C15L;
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

	/** Every key's header holds its car count, so equal keys have equal lengths; an
	 *  entry of another length differs there and is never read past its end. */
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
