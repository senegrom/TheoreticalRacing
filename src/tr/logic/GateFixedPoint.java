package tr.logic;

import java.util.function.BiFunction;
import java.util.function.BiPredicate;

/** Ordered three-gate product iteration. A pass count is a safety limit,
 * never evidence of convergence. No partial result is accepted at the cap. */
final class GateFixedPoint {
	private GateFixedPoint() {}

	static <T> int converge(final T[] maps, final BiFunction<Integer, T, T> compute,
			final BiPredicate<T, T> equal, final int maxPasses) {
		if (maps.length != 3 || maxPasses < 3)
			throw new IllegalArgumentException("Expected three gates and at least three passes");
		for (int pass = 1; pass <= maxPasses; pass++) {
			boolean unchanged = true;
			for (int gate = 2; gate >= 0; gate--) {
				final T before = maps[gate];
				final T after = compute.apply(gate, maps[(gate + 1) % 3]);
				if (after == null)
					throw new IllegalStateException("Gate computation returned no map");
				maps[gate] = after;
				unchanged &= before != null && equal.test(before, after);
			}
			// Retain the previous minimum work/order, but actually check the
			// product equations before using the maps as a coherent cycle.
			if (pass >= 3 && unchanged)
				return pass;
		}
		throw new IllegalStateException("Lap gate maps did not converge after " + maxPasses
				+ " passes; refusing an unverified reachability map");
	}
}
