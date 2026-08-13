package tr.logic;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.BitSet;
import java.util.zip.CheckedInputStream;
import java.util.zip.CheckedOutputStream;
import java.util.zip.CRC32;

/**
 * Track reachability solver extracted from {@link RaceGame}: the reverse-BFS
 * turnsToFinish map, the roomy / shed / certified-speed precompute, the
 * distance-to-finish map, and their async lifecycle. Reads its host's geometry
 * predicates (finish crossing, edge legality, track area) through a back-ref;
 * the AI reads the resulting arrays directly.
 */
final class Reachability {
	private static final Direction[] DIRECTIONS = Direction.values();
	private final RaceGame game;

	Reachability(final RaceGame game) {
		this.game = game;
	}

	/** Allocation-free FIFO for the large solver traversals. */
	private static final class IntQueue {
		private int[] data = new int[1024];
		private int head;
		private int size;

		boolean isEmpty() {
			return size == 0;
		}

		void add(final int value) {
			if (size == data.length)
				grow();
			int tail = head + size;
			if (tail >= data.length)
				tail -= data.length;
			data[tail] = value;
			size++;
		}

		int remove() {
			final int value = data[head];
			head++;
			if (head == data.length)
				head = 0;
			size--;
			return value;
		}

		private void grow() {
			final int[] larger = new int[data.length << 1];
			final int first = Math.min(size, data.length - head);
			System.arraycopy(data, head, larger, 0, first);
			System.arraycopy(data, 0, larger, first, size - first);
			data = larger;
			head = 0;
		}
	}

	private volatile Throwable reachabilityFailure;
	private volatile boolean reachabilityReady;
	private Thread reachabilityThread;
	int[][] distToFinish;

	BitSet	aliveStates;
	int[]	turnsArr;
	int		aliveW, aliveH, aliveVMAX, aliveSpan;
	/** Precomputed {@link #isRoomy} (depth 0 / depth 1) over all alive states;
	 *  non-alive states stay unset (isRoomy is false there — they can have
	 *  neither legal alive successors nor finish crossings). */
	BitSet	roomy0, roomy1;
	/** Precomputed minimum |v|^2 over all states reachable in <= 2 braking
	 *  moves (legal edges, alive landings; the Roomy variant additionally
	 *  requires roomy1 landings). Unsigned bytes, clamped to 255. Together
	 *  they answer {@link #canShedSpeed}(..., depth=2, ...) in O(1). */
	byte[]	minShed2, minShed2Roomy;
	/** Per-state certified speed budget, squared (unsigned bytes; 255 =
	 *  uncertified / non-alive): the SECOND-smallest entry of the multiset
	 *  {state's own |v|^2} plus {minShed2 of every qualifying braking
	 *  successor} -- i.e. the minimal T^2 such that at least two independent
	 *  blind braking descents reach |v| <= T within the
	 *  {@link #countBrakeProofs} horizon. Built by {@link #sweepCertSq};
	 *  consumed via {@link #certBudget} by AI2 only. */
	byte[]	certSq;

	int aliveIdx(final int x, final int y, final int vx, final int vy) {
		return ((x * aliveH + y) * aliveSpan + (vx + aliveVMAX)) * aliveSpan + (vy + aliveVMAX);
	}

	boolean velocityOutOfRange(final int vx, final int vy) {
		return vx < -aliveVMAX || vx > aliveVMAX || vy < -aliveVMAX || vy > aliveVMAX;
	}

	/** True iff (x,y,vx,vy) can reach the finish via some legal sequence of moves. */
	boolean isAlive(final int x, final int y, final int vx, final int vy) {
		if (aliveStates == null)
			return true; // not yet computed — be permissive
		if (velocityOutOfRange(vx, vy))
			return false;
		if (x < 0 || y < 0 || x >= aliveW || y >= aliveH)
			return false;
		return aliveStates.get(aliveIdx(x, y, vx, vy));
	}

	/** Minimum number of turns from (x,y,vx,vy) to crossing the finish, or MAX_VALUE if unreachable. */
	int turnsToFinish(final int x, final int y, final int vx, final int vy) {
		if (turnsArr == null)
			return Integer.MAX_VALUE;
		if (velocityOutOfRange(vx, vy))
			return Integer.MAX_VALUE;
		if (x < 0 || y < 0 || x >= aliveW || y >= aliveH)
			return Integer.MAX_VALUE;
		return turnsArr[aliveIdx(x, y, vx, vy)];
	}

	/**
	 * Reverse-BFS from finish-line-crossing states: computes both the alive set
	 * AND the exact minimum number of turns from each state to crossing the finish.
	 * Run once per track build.
	 */
	void computeReachability() {
		final long t0 = System.nanoTime();
		aliveW = game.gameCols + 1;
		aliveH = game.gameRows + 1;
		aliveVMAX = RaceGame.AI_MAX_SPEED;
		aliveSpan = 2 * aliveVMAX + 1;
		final long stateCount = (long) aliveW * aliveH * aliveSpan * aliveSpan;
		if (stateCount > Integer.MAX_VALUE)
			throw new IllegalStateException("Reachability state space is too large: " + stateCount);
		final long estimatedBytes = stateCount * 12L;
		final Runtime runtime = Runtime.getRuntime();
		final long availableBytes = runtime.maxMemory() - (runtime.totalMemory() - runtime.freeMemory());
		if (estimatedBytes > availableBytes * 3 / 4)
			throw new IllegalStateException("Reachability needs roughly " + (estimatedBytes >> 20)
					+ " MiB but the JVM has only " + (availableBytes >> 20) + " MiB available");
		final int total = (int) stateCount;
		aliveStates = new BitSet(total);
		turnsArr = new int[total];
		Arrays.fill(turnsArr, Integer.MAX_VALUE);
		final IntQueue queue = new IntQueue();
		for (int x = 0; x < aliveW; x++) {
			for (int y = 0; y < aliveH; y++) {
				final int dist = distAt(x, y);
				if (dist == Integer.MAX_VALUE)
					continue;
				if (dist > 2 * aliveVMAX + 5)
					continue; // optimization: too far for direct finish-cross
				for (int vx = -aliveVMAX; vx <= aliveVMAX; vx++) {
					for (int vy = -aliveVMAX; vy <= aliveVMAX; vy++) {
						for (final Direction d : DIRECTIONS) {
							final int nvx = vx + d.dx;
							final int nvy = vy + d.dy;
							if (velocityOutOfRange(nvx, nvy))
								continue;
							if (game.crossesFinish(x, y, x + nvx, y + nvy)) {
								final int idx = aliveIdx(x, y, vx, vy);
								if (!aliveStates.get(idx)) {
									aliveStates.set(idx);
									turnsArr[idx] = 1;
									queue.add(idx);
								}
								break;
							}
						}
					}
				}
			}
		}

		final long tInit = System.nanoTime();

		while (!queue.isEmpty()) {
			int rest = queue.remove();
			final int curIdx = rest;
			final int vyp = rest % aliveSpan - aliveVMAX;
			rest /= aliveSpan;
			final int vxp = rest % aliveSpan - aliveVMAX;
			rest /= aliveSpan;
			final int yp = rest % aliveH;
			final int xp = rest / aliveH;
			final int turns = turnsArr[curIdx];
			final int x = xp - vxp;
			final int y = yp - vyp;
			if (x < 0 || y < 0 || x >= aliveW || y >= aliveH)
				continue;
			if (distAt(x, y) == Integer.MAX_VALUE)
				continue;
			if (!game.isMoveLegalGeometryCached(x, y, xp, yp))
				continue;
			for (final Direction d : DIRECTIONS) {
				final int vx = vxp - d.dx;
				final int vy = vyp - d.dy;
				if (velocityOutOfRange(vx, vy))
					continue;
				final int idx = aliveIdx(x, y, vx, vy);
				if (!aliveStates.get(idx)) {
					aliveStates.set(idx);
					turnsArr[idx] = turns + 1;
					queue.add(idx);
				}
			}
		}
		final long tBfs = System.nanoTime();

		// --- Precomputed AI maps ------------------------------------------
		// One-time sweeps over the alive states turn the runtime questions
		// isRoomy(depth <= 1) and canShedSpeed(depth == 2) into O(1) lookups
		// with exactly the original semantics (see those methods). Non-alive
		// states keep unset/255 entries: they can have neither legal alive
		// successors (alive-closure of the BFS above) nor finish crossings
		// (those are seeded with turns == 1), so isRoomy is false there, and
		// the shed maps are only ever consulted behind an isAlive check.
		final short[] legalAlive = buildLegalAliveMask(total);
		final long tMask = System.nanoTime();
		derivePrecomputes(legalAlive);
		final long tDerive = System.nanoTime();
		writeReachabilityCache(legalAlive);
		final long tCache = System.nanoTime();
		if (game.autoMode)
			System.out.printf(
					"[reachability] init=%.0fms bfs=%.0fms mask=%.0fms derive=%.0fms cacheWrite=%.0fms total=%.0fms alive=%d%n",
					(tInit - t0) / 1e6, (tBfs - tInit) / 1e6, (tMask - tBfs) / 1e6, (tDerive - tMask) / 1e6,
					(tCache - tDerive) / 1e6, (tCache - t0) / 1e6, aliveStates.cardinality());
	}

	/** Roomy / shed / certified-speed sweeps over the alive set: pure array
	 *  passes shared by the compute and cache-load paths. */
	private void derivePrecomputes(final short[] legalAlive) {
		final int total = turnsArr.length;
		final BitSet r0 = new BitSet(total);
		sweepRoomy(legalAlive, null, r0);
		final BitSet r1 = new BitSet(total);
		sweepRoomy(legalAlive, r0, r1);
		final byte[] shed0 = initMinShed(total);
		final byte[] shed = relaxMinShed(relaxMinShed(shed0, legalAlive, null), legalAlive, null);
		final byte[] shedRoomy = relaxMinShed(relaxMinShed(shed0, legalAlive, r1), legalAlive, r1);
		final byte[] cert = sweepCertSq(legalAlive, shed);
		roomy0 = r0;
		roomy1 = r1;
		minShed2 = shed;
		minShed2Roomy = shedRoomy;
		certSq = cert;
	}

	/** Sweep helper for {@link #computeReachability}: per-alive-state bitmask
	 *  over {@link Direction} ordinals — bit d set iff the successor under d
	 *  stays in the velocity range, its edge is geometry-legal and its landing
	 *  is alive (the shared non-crossing qualifying conditions of
	 *  {@link #isRoomy} and {@link #canShedSpeed}). Every legality query here
	 *  hits {@code edgeLegalCache}: when the BFS popped an alive landing it
	 *  already checked the edge from the landing's unique cell-predecessor,
	 *  which is exactly the source cell used here. */
	short[] buildLegalAliveMask(final int total) {
		final int span = aliveSpan;
		final short[] mask = new short[total];
		for (int idx = aliveStates.nextSetBit(0); idx >= 0; idx = aliveStates.nextSetBit(idx + 1)) {
			int rest = idx;
			final int vy = rest % span - aliveVMAX;
			rest /= span;
			final int vx = rest % span - aliveVMAX;
			rest /= span;
			final int y = rest % aliveH;
			final int x = rest / aliveH;
			short m = 0;
			for (int di = 0; di < DIRECTIONS.length; di++) {
				final int nvx = vx + DIRECTIONS[di].dx;
				final int nvy = vy + DIRECTIONS[di].dy;
				if (velocityOutOfRange(nvx, nvy))
					continue;
				final int nx = x + nvx;
				final int ny = y + nvy;
				// Alive-first equals legal-first in result (both pure
				// predicates); alive-first keeps the edge-cache probes to alive
				// landings only (all of which are cache hits, see above).
				if (isAlive(nx, ny, nvx, nvy) && game.isMoveLegalGeometryCached(x, y, nx, ny))
					m = (short) (m | 1 << di);
			}
			mask[idx] = m;
		}
		return mask;
	}

	/** Sweep helper for {@link #computeReachability}: sets in {@code out} every
	 *  alive state with >= 2 qualifying continuations per the {@link #isRoomy}
	 *  rule. A successor qualifies if it crosses the finish, or its
	 *  {@code legalAlive} bit is set and (when {@code req != null}) its state
	 *  bit is set in {@code req}. {@code req == null} computes depth 0;
	 *  {@code req == roomy0} computes depth 1. */
	void sweepRoomy(final short[] legalAlive, final BitSet req, final BitSet out) {
		final int span = aliveSpan;
		for (int idx = aliveStates.nextSetBit(0); idx >= 0; idx = aliveStates.nextSetBit(idx + 1)) {
			int rest = idx;
			final int vy = rest % span - aliveVMAX;
			rest /= span;
			final int vx = rest % span - aliveVMAX;
			rest /= span;
			final int y = rest % aliveH;
			final int x = rest / aliveH;
			final int mask = legalAlive[idx];
			int count = 0;
			for (int di = 0; di < DIRECTIONS.length; di++) {
				final int nvx = vx + DIRECTIONS[di].dx;
				final int nvy = vy + DIRECTIONS[di].dy;
				if (velocityOutOfRange(nvx, nvy))
					continue;
				final int nx = x + nvx;
				final int ny = y + nvy;
				if (game.crossesFinish(x, y, nx, ny)) {
					count++;
				} else {
					if ((mask & 1 << di) == 0)
						continue;
					if (req != null && !req.get(aliveIdx(nx, ny, nvx, nvy)))
						continue;
					count++;
				}
				if (count >= 2) {
					out.set(idx);
					break;
				}
			}
		}
	}

	/** Sweep helper for {@link #computeReachability}: |v|^2 (clamped to 255)
	 *  for every alive state, 255 for non-alive states (never read — the
	 *  runtime consults the shed maps only behind an isAlive check). */
	byte[] initMinShed(final int total) {
		final int span = aliveSpan;
		final byte[] arr = new byte[total];
		Arrays.fill(arr, (byte) 0xFF);
		for (int idx = aliveStates.nextSetBit(0); idx >= 0; idx = aliveStates.nextSetBit(idx + 1)) {
			final int vy = idx % span - aliveVMAX;
			final int vx = idx / span % span - aliveVMAX;
			arr[idx] = (byte) Math.min(vx * vx + vy * vy, 255);
		}
		return arr;
	}

	/** Sweep helper for {@link #computeReachability}: one Jacobi relaxation of
	 *  the min-|v|^2-reachable-by-braking map (unsigned bytes): out[s] =
	 *  min(in[s], min in[succ]) over successors in the braking cone (|v|
	 *  non-increasing — the integer-square compare is exactly the runtime's
	 *  hypot compare) whose {@code legalAlive} bit is set and (when
	 *  {@code roomyReq != null}) whose state bit is set in {@code roomyReq} —
	 *  exactly the per-step conditions of {@link #canShedSpeed}. */
	byte[] relaxMinShed(final byte[] in, final short[] legalAlive, final BitSet roomyReq) {
		final int span = aliveSpan;
		final byte[] out = new byte[in.length];
		Arrays.fill(out, (byte) 0xFF);
		for (int idx = aliveStates.nextSetBit(0); idx >= 0; idx = aliveStates.nextSetBit(idx + 1)) {
			int rest = idx;
			final int vy = rest % span - aliveVMAX;
			rest /= span;
			final int vx = rest % span - aliveVMAX;
			rest /= span;
			final int y = rest % aliveH;
			final int x = rest / aliveH;
			final int mask = legalAlive[idx];
			final int v2 = vx * vx + vy * vy;
			int best = in[idx] & 0xFF;
			for (int di = 0; di < DIRECTIONS.length; di++) {
				if ((mask & 1 << di) == 0)
					continue;
				final int nvx = vx + DIRECTIONS[di].dx;
				final int nvy = vy + DIRECTIONS[di].dy;
				if (nvx * nvx + nvy * nvy > v2)
					continue; // braking cone only
				final int succ = aliveIdx(x + nvx, y + nvy, nvx, nvy);
				if (roomyReq != null && !roomyReq.get(succ))
					continue;
				final int cand = in[succ] & 0xFF;
				if (cand < best)
					best = cand;
			}
			out[idx] = (byte) best;
		}
		return out;
	}

	/** Sweep helper for {@link #computeReachability}: per-state certified speed
	 *  budget, squared (unsigned bytes, 255 = uncertified). For every alive
	 *  state the sweep collects {@code shed[succ]} (= minShed2, the min |v|^2
	 *  shed-able in <= 2 further braking moves) of each qualifying braking
	 *  successor -- braking cone by |v|^2, legal edge, alive landing: exactly
	 *  the first-move semantics of {@link #countBrakeProofs} minus the runtime
	 *  opponent-prediction filter -- plus the state's own |v|^2 (the zero-move
	 *  descent: the state is already at that speed). The entry written is the
	 *  SECOND-smallest of that multiset: the minimal target T^2 such that at
	 *  least two independent blind braking descents reach |v| <= T within the
	 *  proof horizon; 255 if fewer than two entries qualify. Non-alive states
	 *  keep 255 (only ever consulted behind an alive candidate). */
	byte[] sweepCertSq(final short[] legalAlive, final byte[] shed) {
		final int span = aliveSpan;
		final byte[] arr = new byte[shed.length];
		Arrays.fill(arr, (byte) 0xFF);
		for (int idx = aliveStates.nextSetBit(0); idx >= 0; idx = aliveStates.nextSetBit(idx + 1)) {
			int rest = idx;
			final int vy = rest % span - aliveVMAX;
			rest /= span;
			final int vx = rest % span - aliveVMAX;
			rest /= span;
			final int y = rest % aliveH;
			final int x = rest / aliveH;
			final int mask = legalAlive[idx];
			final int v2 = vx * vx + vy * vy;
			// Two smallest entries of the witness multiset, seeded with the
			// state's own |v|^2 (the zero-move descent).
			int min1 = Math.min(v2, 255);
			int min2 = 256; // sentinel: fewer than two entries so far
			for (int di = 0; di < DIRECTIONS.length; di++) {
				if ((mask & 1 << di) == 0)
					continue;
				final int nvx = vx + DIRECTIONS[di].dx;
				final int nvy = vy + DIRECTIONS[di].dy;
				if (nvx * nvx + nvy * nvy > v2)
					continue; // braking cone only
				final int cand = shed[aliveIdx(x + nvx, y + nvy, nvx, nvy)] & 0xFF;
				if (cand < min1) {
					min2 = min1;
					min1 = cand;
				} else if (cand < min2)
					min2 = cand;
			}
			arr[idx] = (byte) Math.min(min2, 255);
		}
		return arr;
	}

	/** Certified per-state speed budget for AI2's pace discipline: the minimal
	 *  integer target T such that at least two independent blind braking
	 *  descents from (x,y,vx,vy) reach |v| <= T within the
	 *  {@link #countBrakeProofs} horizon -- {@code ceil(sqrt(certSq))} over
	 *  the precomputed map (the uncertified 255 maps to 16, an effectively
	 *  unbounded budget). Replaces the global constant base 5 of the
	 *  pre-certification widthBudget with local, heading- and speed-exact map
	 *  truth. Conservative 0 for states outside the precomputed space or
	 *  before the map exists (never the case after ensureReachabilityReady). */
	int certBudget(final int x, final int y, final int vx, final int vy) {
		if (certSq == null)
			return 0;
		if (velocityOutOfRange(vx, vy))
			return 0;
		if (x < 0 || y < 0 || x >= aliveW || y >= aliveH)
			return 0;
		return (int) Math.ceil(Math.sqrt(certSq[aliveIdx(x, y, vx, vy)] & 0xFF));
	}

	double scorePos(final int x, final int y, final int vx, final int vy) {
		final int dist = distAt(x, y);
		double score = dist == Integer.MAX_VALUE ? 1e6 : dist;
		final double speed = Math.sqrt(vx * vx + vy * vy);
		if (speed > 5)
			score += 2 * (speed - 5);
		return score;
	}

	int distAt(final int x, final int y) {
		if (distToFinish == null)
			return Integer.MAX_VALUE;
		if (x < 0 || y < 0 || x >= distToFinish.length || y >= distToFinish[0].length)
			return Integer.MAX_VALUE;
		return distToFinish[x][y];
	}

	/**
	 * 8-connected BFS from the finish line through track cells. Used as the AI's
	 * "distance to finish along the track" heuristic.
	 */
	void computeDistMap() {
		final int w = game.gameCols + 1;
		final int h = game.gameRows + 1;
		distToFinish = new int[w][h];
		for (final int[] col : distToFinish)
			Arrays.fill(col, Integer.MAX_VALUE);

		final IntQueue queue = new IntQueue();
		final double fx1 = game.finishLine.getX1(), fy1 = game.finishLine.getY1();
		final double fx2 = game.finishLine.getX2(), fy2 = game.finishLine.getY2();
		final int samples = (int) Math.ceil(Math.hypot(fx2 - fx1, fy2 - fy1) * 2) + 1;
		for (int i = 0; i <= samples; i++) {
			final double t = (double) i / samples;
			final int x = (int) Math.round(fx1 + t * (fx2 - fx1));
			final int y = (int) Math.round(fy1 + t * (fy2 - fy1));
			if (x < 0 || x >= w || y < 0 || y >= h)
				continue;
			if (distToFinish[x][y] != Integer.MAX_VALUE)
				continue;
			distToFinish[x][y] = 0;
			queue.add(x * h + y);
		}

		while (!queue.isEmpty()) {
			final int cell = queue.remove();
			final int cx = cell / h;
			final int cy = cell % h;
			final int d = distToFinish[cx][cy];
			for (int dx = -1; dx <= 1; dx++)
				for (int dy = -1; dy <= 1; dy++) {
					if (dx == 0 && dy == 0)
						continue;
					final int nx = cx + dx, ny = cy + dy;
					if (nx < 0 || nx >= w || ny < 0 || ny >= h)
						continue;
					if (distToFinish[nx][ny] != Integer.MAX_VALUE)
						continue;
					if (!game.trackA.contains(nx, ny) && !game.startZoneA.contains(nx, ny))
						continue;
					distToFinish[nx][ny] = d + 1;
					queue.add(nx * h + ny);
				}
		}
		buildRingWidths(w, h);
	}

	/** Round 83: per-progress-ring corridor widths. ringWidth[d] counts the
	 *  track cells at distance-to-finish d -- a narrowing corridor is a
	 *  STATIC property of the distance map, visible without any rollout
	 *  (the deep-horizon commitment class: both members hold speed into a
	 *  monotonically narrowing ring sequence). */
	private int[] ringWidth;

	private void buildRingWidths(final int w, final int h) {
		int maxDist = 0;
		for (int x = 0; x < w; x++)
			for (int y = 0; y < h; y++) {
				final int d = distToFinish[x][y];
				if (d != Integer.MAX_VALUE && d > maxDist)
					maxDist = d;
			}
		final int[] widths = new int[maxDist + 1];
		for (int x = 0; x < w; x++)
			for (int y = 0; y < h; y++) {
				final int d = distToFinish[x][y];
				if (d != Integer.MAX_VALUE)
					widths[d]++;
			}
		ringWidth = widths;
	}

	/** Minimum ring width over the next {@code span} progress rings ahead of
	 *  (x,y); MAX_VALUE off-track. Rings 0-2 (the finish mouth) never count:
	 *  a corridor that ends at the flag is victory, not doom. */
	int minRingWidthAhead(final int x, final int y, final int span) {
		final int d = distAt(x, y);
		if (d == Integer.MAX_VALUE || ringWidth == null)
			return Integer.MAX_VALUE;
		int min = Integer.MAX_VALUE;
		for (int k = 1; k <= span; k++) {
			final int rd = d - k;
			if (rd < 3)
				break;
			if (rd < ringWidth.length && ringWidth[rd] > 0 && ringWidth[rd] < min)
				min = ringWidth[rd];
		}
		return min;
	}

	/** Longest consecutive run of rings with width <= {@code width} within the
	 *  next {@code span} rings ahead of (x,y). A short narrow GATE (lemans
	 *  chicane, 1-3 rings) is passable at speed; a SUSTAINED narrow corridor
	 *  (the zandvoort funnels) is where overcommitment kills. */
	int narrowRunAhead(final int x, final int y, final int span, final int width) {
		final int d = distAt(x, y);
		if (d == Integer.MAX_VALUE || ringWidth == null)
			return 0;
		int run = 0, best = 0;
		for (int k = 1; k <= span; k++) {
			final int rd = d - k;
			if (rd < 3)
				break;
			if (rd < ringWidth.length && ringWidth[rd] > 0 && ringWidth[rd] <= width) {
				run++;
				if (run > best)
					best = run;
			} else
				run = 0;
		}
		return best;
	}

	/** Dump the turnsToFinish reachability map for the loaded track: a little-
	 *  endian binary of [aliveW, aliveH, aliveVMAX] then turnsArr (int32 each,
	 *  Integer.MAX_VALUE = unreachable). Python decodes with the same aliveIdx
	 *  formula: ((x*aliveH+y)*span + (vx+VMAX))*span + (vy+VMAX), span=2*VMAX+1. */
	void writeReachability(final String path) {
		try {
			TrackIO.writeAtomically(Path.of(path), out -> {
				final ByteBuffer buffer = ByteBuffer.allocate(CACHE_IO_BYTES).order(ByteOrder.LITTLE_ENDIAN);
				buffer.putInt(aliveW).putInt(aliveH).putInt(aliveVMAX);
				writeLittleEndian(out, buffer, turnsArr);
				flush(out, buffer);
			});
		} catch (final IOException e) {
			e.printStackTrace();
			System.exit(3);
		}
		System.out.println("dumped reachability " + aliveW + "x" + aliveH + " vmax=" + aliveVMAX
				+ " (" + turnsArr.length + " states) -> " + path);
	}

	/** Kick off reverse-BFS reachability on a daemon thread so it doesn't block the UI. */
	void startReachabilityCompute() {
		reachabilityFailure = null;
		final Thread t = new Thread(() -> {
			try {
				if (!tryLoadReachabilityCache())
					computeReachability();
			} catch (final RuntimeException | Error failure) {
				reachabilityFailure = failure;
			} finally {
				reachabilityReady = true;
			}
		}, "reachability-compute");
		t.setDaemon(true);
		reachabilityThread = t;
		reachabilityReady = false; // volatile publication of the new thread/failure state
		t.start();
	}

	/** Non-blocking completion probe (ensureReachabilityReady joins and rethrows failures). */
	boolean isReady() {
		return reachabilityReady;
	}

	/** Wait for reachability and never expose a partial map after interruption or
	 *  background failure. */
	void ensureReachabilityReady() {
		if (!reachabilityReady) {
			final Thread t = reachabilityThread;
			if (t != null) {
				try {
					t.join();
				} catch (final InterruptedException e) {
					Thread.currentThread().interrupt();
					throw new IllegalStateException("Interrupted while computing track reachability", e);
				}
			}
		}
		final Throwable failure = reachabilityFailure;
		if (failure instanceof RuntimeException runtimeFailure)
			throw runtimeFailure;
		if (failure instanceof Error errorFailure)
			throw errorFailure;
	}

	// --- Reachability disk cache -----------------------------------------
	// The turns map and the legal-alive mask are pure functions of the track
	// geometry (seeds only move start placements), yet the BFS that builds
	// them dominates race startup. Both arrays are cached keyed by a geometry
	// hash; the cheap roomy/shed/cert sweeps are re-derived on load. Files
	// live outside the install dir (TrackIO.reachCacheDir) so multi-MB caches
	// never land in cloud-synced folders.

	// TRC2 appends a CRC32 so valid-looking, same-size corruption cannot alter AI decisions.
	private static final int CACHE_MAGIC = 0x54524332; // "TRC2"
	private static final int CACHE_HEADER_BYTES = 4 * Integer.BYTES;
	private static final int CACHE_CHECKSUM_BYTES = Integer.BYTES;
	private static final int CACHE_IO_BYTES = 64 * 1024;
	private static final int CACHE_DIRECTION_MASK = (1 << DIRECTIONS.length) - 1;

	private java.nio.file.Path reachCachePath() {
		final Track track = game.track;
		if (track == null)
			return null;
		try {
			final java.security.MessageDigest md = java.security.MessageDigest.getInstance("SHA-256");
			final java.nio.ByteBuffer header = java.nio.ByteBuffer.allocate(4 * Integer.BYTES)
					.order(java.nio.ByteOrder.LITTLE_ENDIAN);
			header.putInt(CACHE_MAGIC).putInt(game.gameCols).putInt(game.gameRows).putInt(RaceGame.AI_MAX_SPEED);
			md.update(header.array());
			final java.nio.ByteBuffer point = java.nio.ByteBuffer.allocate(2 * Integer.BYTES)
					.order(java.nio.ByteOrder.LITTLE_ENDIAN);
			for (final java.util.List<int[]> side : java.util.List.of(track.getLeft(), track.getRight())) {
				for (final int[] p : side) {
					point.clear();
					point.putInt(p[0]).putInt(p[1]);
					md.update(point.array());
				}
				md.update((byte) ';');
			}
			final StringBuilder hex = new StringBuilder(64);
			for (final byte b : md.digest())
				hex.append(Character.forDigit((b >> 4) & 0xF, 16)).append(Character.forDigit(b & 0xF, 16));
			return TrackIO.reachCacheDir().resolve("reach-" + hex + ".bin");
		} catch (final java.security.NoSuchAlgorithmException e) {
			return null;
		}
	}

	/** Load turns + legal-alive from the geometry-keyed cache and re-derive
	 *  the sweeps. Any validation or IO failure returns false and leaves the
	 *  compute path to run from scratch. */
	boolean tryLoadReachabilityCache() {
		final Path path = reachCachePath();
		if (path == null || !Files.isRegularFile(path))
			return false;
		final long t0 = System.nanoTime();
		final int w = game.gameCols + 1;
		final int h = game.gameRows + 1;
		final int vmax = RaceGame.AI_MAX_SPEED;
		final int span = 2 * vmax + 1;
		final long stateCount = (long) w * h * span * span;
		if (stateCount > Integer.MAX_VALUE)
			return false;
		final long expectedBytes = CACHE_HEADER_BYTES
				+ stateCount * (Integer.BYTES + Short.BYTES) + CACHE_CHECKSUM_BYTES;
		try {
			if (Files.size(path) != expectedBytes)
				return false;
		} catch (final IOException e) {
			return false;
		}
		final Runtime runtime = Runtime.getRuntime();
		final long availableBytes = runtime.maxMemory() - (runtime.totalMemory() - runtime.freeMemory());
		if (stateCount * 12L > availableBytes * 3 / 4)
			return false; // let computeReachability raise its descriptive error
		final int total = (int) stateCount;
		final int[] turns = new int[total];
		final short[] legalAlive = new short[total];
		try (InputStream in = new java.io.BufferedInputStream(Files.newInputStream(path), CACHE_IO_BYTES)) {
			if (!readCacheData(in, w, h, vmax, turns, legalAlive))
				return false;
		} catch (final IOException e) {
			return false;
		}
		final BitSet alive = new BitSet(total);
		if (!validateCacheArrays(turns, legalAlive, alive))
			return false;
		aliveW = w;
		aliveH = h;
		aliveVMAX = vmax;
		aliveSpan = span;
		turnsArr = turns;
		aliveStates = alive;
		final long tLoad = System.nanoTime();
		derivePrecomputes(legalAlive);
		final long tDerive = System.nanoTime();
		if (game.autoMode)
			System.out.printf("[reachability] cache-hit load=%.0fms derive=%.0fms total=%.0fms alive=%d%n",
					(tLoad - t0) / 1e6, (tDerive - tLoad) / 1e6, (tDerive - t0) / 1e6, aliveStates.cardinality());
		return true;
	}

	/** Best-effort atomic cache write; failures only cost the speedup. */
	private void writeReachabilityCache(final short[] legalAlive) {
		final Path path = reachCachePath();
		if (path == null)
			return;
		try {
			TrackIO.writeAtomically(path, out ->
					writeCacheData(out, aliveW, aliveH, aliveVMAX, turnsArr, legalAlive));
		} catch (final IOException e) {
			System.err.println("[reachability] cache write failed: " + e);
		}
	}

	static boolean readCacheData(final InputStream in, final int w, final int h, final int vmax,
			final int[] turns, final short[] legalAlive) throws IOException {
		if (turns.length != legalAlive.length)
			return false;
		final CRC32 checksum = new CRC32();
		final CheckedInputStream checked = new CheckedInputStream(in, checksum);
		final byte[] ioBuffer = new byte[CACHE_IO_BYTES];
		if (checked.readNBytes(ioBuffer, 0, CACHE_HEADER_BYTES) != CACHE_HEADER_BYTES)
			return false;
		final ByteBuffer header = ByteBuffer.wrap(ioBuffer, 0, CACHE_HEADER_BYTES).order(ByteOrder.LITTLE_ENDIAN);
		if (header.getInt() != CACHE_MAGIC || header.getInt() != w || header.getInt() != h || header.getInt() != vmax)
			return false;
		if (!readLittleEndian(checked, turns, ioBuffer) || !readLittleEndian(checked, legalAlive, ioBuffer))
			return false;
		if (in.readNBytes(ioBuffer, 0, CACHE_CHECKSUM_BYTES) != CACHE_CHECKSUM_BYTES || in.read() != -1)
			return false;
		final int stored = ByteBuffer.wrap(ioBuffer, 0, CACHE_CHECKSUM_BYTES)
				.order(ByteOrder.LITTLE_ENDIAN).getInt();
		return Integer.toUnsignedLong(stored) == checksum.getValue();
	}

	static void writeCacheData(final OutputStream out, final int w, final int h, final int vmax,
			final int[] turns, final short[] legalAlive) throws IOException {
		if (turns.length != legalAlive.length)
			throw new IllegalArgumentException("cache array lengths differ");
		final CRC32 checksum = new CRC32();
		final CheckedOutputStream checked = new CheckedOutputStream(out, checksum);
		final ByteBuffer buffer = ByteBuffer.allocate(CACHE_IO_BYTES).order(ByteOrder.LITTLE_ENDIAN);
		buffer.putInt(CACHE_MAGIC).putInt(w).putInt(h).putInt(vmax);
		writeLittleEndian(checked, buffer, turns);
		writeLittleEndian(checked, buffer, legalAlive);
		flush(checked, buffer);
		buffer.putInt((int) checksum.getValue());
		flush(out, buffer);
	}

	static boolean readLittleEndian(final InputStream in, final int[] values, final byte[] buffer) throws IOException {
		if (buffer.length < Integer.BYTES)
			throw new IllegalArgumentException("integer IO buffer is too small");
		final ByteBuffer bytes = ByteBuffer.wrap(buffer).order(ByteOrder.LITTLE_ENDIAN);
		int offset = 0;
		while (offset < values.length) {
			final int count = Math.min(values.length - offset, buffer.length / Integer.BYTES);
			final int byteCount = count * Integer.BYTES;
			if (in.readNBytes(buffer, 0, byteCount) != byteCount)
				return false;
			bytes.clear();
			bytes.limit(byteCount);
			bytes.asIntBuffer().get(values, offset, count);
			offset += count;
		}
		return true;
	}

	static boolean readLittleEndian(final InputStream in, final short[] values, final byte[] buffer) throws IOException {
		if (buffer.length < Short.BYTES)
			throw new IllegalArgumentException("short IO buffer is too small");
		final ByteBuffer bytes = ByteBuffer.wrap(buffer).order(ByteOrder.LITTLE_ENDIAN);
		int offset = 0;
		while (offset < values.length) {
			final int count = Math.min(values.length - offset, buffer.length / Short.BYTES);
			final int byteCount = count * Short.BYTES;
			if (in.readNBytes(buffer, 0, byteCount) != byteCount)
				return false;
			bytes.clear();
			bytes.limit(byteCount);
			bytes.asShortBuffer().get(values, offset, count);
			offset += count;
		}
		return true;
	}

	static boolean validateCacheArrays(final int[] turns, final short[] legalAlive, final BitSet alive) {
		if (turns.length != legalAlive.length)
			return false;
		for (int i = 0; i < turns.length; i++) {
			final int mask = Short.toUnsignedInt(legalAlive[i]);
			if ((mask & ~CACHE_DIRECTION_MASK) != 0)
				return false;
			if (turns[i] == Integer.MAX_VALUE) {
				if (mask != 0)
					return false;
			} else {
				if (turns[i] < 1)
					return false;
				alive.set(i);
			}
		}
		return true;
	}

	private static void writeLittleEndian(final OutputStream out, final ByteBuffer buffer, final int[] values)
			throws IOException {
		for (final int value : values) {
			if (buffer.remaining() < Integer.BYTES)
				flush(out, buffer);
			buffer.putInt(value);
		}
	}

	private static void writeLittleEndian(final OutputStream out, final ByteBuffer buffer, final short[] values)
			throws IOException {
		for (final short value : values) {
			if (buffer.remaining() < Short.BYTES)
				flush(out, buffer);
			buffer.putShort(value);
		}
	}

	private static void flush(final OutputStream out, final ByteBuffer buffer) throws IOException {
		out.write(buffer.array(), 0, buffer.position());
		buffer.clear();
	}

}
