package tr.logic;

import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.BitSet;

/**
 * Track reachability solver extracted from {@link RaceGame}: the reverse-BFS
 * turnsToFinish map, the roomy / shed / certified-speed precompute, the
 * distance-to-finish map, and their async lifecycle. Reads its host's geometry
 * predicates (finish crossing, edge legality, track area) through a back-ref;
 * the AI reads the resulting arrays directly.
 */
final class Reachability {
	private final RaceGame game;

	Reachability(final RaceGame game) {
		this.game = game;
	}

	private volatile boolean reachabilityReady;
	private Thread reachabilityThread;
	int[][] distToFinish;

	BitSet	aliveStates;
	int[]	turnsArr;
	int		aliveW, aliveH, aliveVMAX;
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
		final int span = 2 * aliveVMAX + 1;
		return ((x * aliveH + y) * span + (vx + aliveVMAX)) * span + (vy + aliveVMAX);
	}

	/** True iff (x,y,vx,vy) can reach the finish via some legal sequence of moves. */
	boolean isAlive(final int x, final int y, final int vx, final int vy) {
		if (aliveStates == null)
			return true; // not yet computed — be permissive
		if (Math.abs(vx) > aliveVMAX || Math.abs(vy) > aliveVMAX)
			return false;
		if (x < 0 || y < 0 || x >= aliveW || y >= aliveH)
			return false;
		return aliveStates.get(aliveIdx(x, y, vx, vy));
	}

	/** Minimum number of turns from (x,y,vx,vy) to crossing the finish, or MAX_VALUE if unreachable. */
	int turnsToFinish(final int x, final int y, final int vx, final int vy) {
		if (turnsArr == null)
			return Integer.MAX_VALUE;
		if (Math.abs(vx) > aliveVMAX || Math.abs(vy) > aliveVMAX)
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
		final int span = 2 * aliveVMAX + 1;
		final int total = aliveW * aliveH * span * span;
		aliveStates = new BitSet(total);
		turnsArr = new int[total];
		Arrays.fill(turnsArr, Integer.MAX_VALUE);
		final ArrayDeque<int[]> queue = new ArrayDeque<>();

		for (int x = 0; x < aliveW; x++) {
			for (int y = 0; y < aliveH; y++) {
				if (distAt(x, y) == Integer.MAX_VALUE)
					continue;
				if (distAt(x, y) > 2 * aliveVMAX + 5)
					continue; // optimization: too far for direct finish-cross
				for (int vx = -aliveVMAX; vx <= aliveVMAX; vx++) {
					for (int vy = -aliveVMAX; vy <= aliveVMAX; vy++) {
						for (final Direction d : Direction.values()) {
							final int nvx = vx + d.dx;
							final int nvy = vy + d.dy;
							if (Math.abs(nvx) > aliveVMAX || Math.abs(nvy) > aliveVMAX)
								continue;
							if (game.crossesFinish(x, y, x + nvx, y + nvy)) {
								final int idx = aliveIdx(x, y, vx, vy);
								if (!aliveStates.get(idx)) {
									aliveStates.set(idx);
									turnsArr[idx] = 1;
									queue.offer(new int[]{x, y, vx, vy });
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
			final int[] cur = queue.poll();
			final int xp = cur[0], yp = cur[1], vxp = cur[2], vyp = cur[3];
			final int turns = turnsArr[aliveIdx(xp, yp, vxp, vyp)];
			final int x = xp - vxp;
			final int y = yp - vyp;
			if (x < 0 || y < 0 || x >= aliveW || y >= aliveH)
				continue;
			if (distAt(x, y) == Integer.MAX_VALUE)
				continue;
			if (!game.isMoveLegalGeometryCached(x, y, xp, yp))
				continue;
			for (final Direction d : Direction.values()) {
				final int vx = vxp - d.dx;
				final int vy = vyp - d.dy;
				if (Math.abs(vx) > aliveVMAX || Math.abs(vy) > aliveVMAX)
					continue;
				final int idx = aliveIdx(x, y, vx, vy);
				if (!aliveStates.get(idx)) {
					aliveStates.set(idx);
					turnsArr[idx] = turns + 1;
					queue.offer(new int[]{x, y, vx, vy });
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
		final BitSet r0 = new BitSet(total);
		sweepRoomy(legalAlive, null, r0);
		final long tRoomy0 = System.nanoTime();
		final BitSet r1 = new BitSet(total);
		sweepRoomy(legalAlive, r0, r1);
		final long tRoomy1 = System.nanoTime();
		final byte[] shed0 = initMinShed(total);
		final byte[] shed = relaxMinShed(relaxMinShed(shed0, legalAlive, null), legalAlive, null);
		final long tShed = System.nanoTime();
		final byte[] shedRoomy = relaxMinShed(relaxMinShed(shed0, legalAlive, r1), legalAlive, r1);
		final long tShedRoomy = System.nanoTime();
		final byte[] cert = sweepCertSq(legalAlive, shed);
		final long tCert = System.nanoTime();
		roomy0 = r0;
		roomy1 = r1;
		minShed2 = shed;
		minShed2Roomy = shedRoomy;
		certSq = cert;
		if (game.autoMode)
			System.out.printf(
					"[reachability] init=%.0fms bfs=%.0fms mask=%.0fms roomy0=%.0fms roomy1=%.0fms shed=%.0fms shedRoomy=%.0fms cert=%.0fms total=%.0fms alive=%d%n",
					(tInit - t0) / 1e6, (tBfs - tInit) / 1e6, (tMask - tBfs) / 1e6, (tRoomy0 - tMask) / 1e6,
					(tRoomy1 - tRoomy0) / 1e6, (tShed - tRoomy1) / 1e6, (tShedRoomy - tShed) / 1e6, (tCert - tShedRoomy) / 1e6,
					(tCert - t0) / 1e6, aliveStates.cardinality());
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
		final Direction[] dirs = Direction.values();
		final int span = 2 * aliveVMAX + 1;
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
			for (int di = 0; di < dirs.length; di++) {
				final int nvx = vx + dirs[di].dx;
				final int nvy = vy + dirs[di].dy;
				if (Math.abs(nvx) > aliveVMAX || Math.abs(nvy) > aliveVMAX)
					continue;
				final int nx = x + nvx;
				final int ny = y + nvy;
				// Alive-first equals legal-first in result (both pure
				// predicates); alive-first keeps the HashMap lookups to alive
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
		final Direction[] dirs = Direction.values();
		final int span = 2 * aliveVMAX + 1;
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
			for (int di = 0; di < dirs.length; di++) {
				final int nvx = vx + dirs[di].dx;
				final int nvy = vy + dirs[di].dy;
				if (Math.abs(nvx) > aliveVMAX || Math.abs(nvy) > aliveVMAX)
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
		final int span = 2 * aliveVMAX + 1;
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
		final Direction[] dirs = Direction.values();
		final int span = 2 * aliveVMAX + 1;
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
			for (int di = 0; di < dirs.length; di++) {
				if ((mask & 1 << di) == 0)
					continue;
				final int nvx = vx + dirs[di].dx;
				final int nvy = vy + dirs[di].dy;
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
		final Direction[] dirs = Direction.values();
		final int span = 2 * aliveVMAX + 1;
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
			for (int di = 0; di < dirs.length; di++) {
				if ((mask & 1 << di) == 0)
					continue;
				final int nvx = vx + dirs[di].dx;
				final int nvy = vy + dirs[di].dy;
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
		if (Math.abs(vx) > aliveVMAX || Math.abs(vy) > aliveVMAX)
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

		final ArrayDeque<int[]> queue = new ArrayDeque<>();
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
			queue.add(new int[]{x, y });
		}

		while (!queue.isEmpty()) {
			final int[] cell = queue.poll();
			final int d = distToFinish[cell[0]][cell[1]];
			for (int dx = -1; dx <= 1; dx++)
				for (int dy = -1; dy <= 1; dy++) {
					if (dx == 0 && dy == 0)
						continue;
					final int nx = cell[0] + dx, ny = cell[1] + dy;
					if (nx < 0 || nx >= w || ny < 0 || ny >= h)
						continue;
					if (distToFinish[nx][ny] != Integer.MAX_VALUE)
						continue;
					if (!game.trackA.contains(nx, ny) && !game.startZoneA.contains(nx, ny))
						continue;
					distToFinish[nx][ny] = d + 1;
					queue.add(new int[]{nx, ny });
				}
		}
	}

	/** Dump the turnsToFinish reachability map for the loaded track: a little-
	 *  endian binary of [aliveW, aliveH, aliveVMAX] then turnsArr (int32 each,
	 *  Integer.MAX_VALUE = unreachable). Python decodes with the same aliveIdx
	 *  formula: ((x*aliveH+y)*span + (vx+VMAX))*span + (vy+VMAX), span=2*VMAX+1. */
	void writeReachability(final String path) {
		try (java.io.OutputStream out = new java.io.BufferedOutputStream(new java.io.FileOutputStream(path))) {
			final java.nio.ByteBuffer buf = java.nio.ByteBuffer
					.allocate((3 + turnsArr.length) * 4).order(java.nio.ByteOrder.LITTLE_ENDIAN);
			buf.putInt(aliveW).putInt(aliveH).putInt(aliveVMAX);
			for (final int v : turnsArr)
				buf.putInt(v);
			out.write(buf.array());
		} catch (final java.io.IOException e) {
			e.printStackTrace();
			System.exit(3);
		}
		System.out.println("dumped reachability " + aliveW + "x" + aliveH + " vmax=" + aliveVMAX
				+ " (" + turnsArr.length + " states) -> " + path);
	}

	/** Kick off reverse-BFS reachability on a daemon thread so it doesn't block the UI. */
	void startReachabilityCompute() {
		reachabilityReady = false;
		final Thread t = new Thread(() -> {
			computeReachability();
			reachabilityReady = true;
		}, "reachability-compute");
		t.setDaemon(true);
		reachabilityThread = t;
		t.start();
	}

	/** Wait for reachability if the background BFS hasn't finished yet. */
	void ensureReachabilityReady() {
		if (reachabilityReady)
			return;
		final Thread t = reachabilityThread;
		if (t == null)
			return;
		try {
			t.join();
		} catch (final InterruptedException e) {
			Thread.currentThread().interrupt();
		}
	}

}
