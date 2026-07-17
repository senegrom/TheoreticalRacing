package tr.logic;

/**
 * One of the 9 directional adjustments to a player's velocity per turn.
 *
 * @author CGH
 */
public enum Direction {
	NW(-1, -1), N(0, -1), NE(1, -1),
	W(-1, 0), NONE(0, 0), E(1, 0),
	SW(-1, 1), S(0, 1), SE(1, 1);

	private final static Direction[] VALUES = values();

	public final int	dx, dy;

	Direction(final int dx, final int dy) {
		this.dx = dx;
		this.dy = dy;
	}

	public static Direction fromIndex(final int i) {
		return VALUES[i];
	}

	public String label() {
		return this == NONE ? "-" : name();
	}
}
