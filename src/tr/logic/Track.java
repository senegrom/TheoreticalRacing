package tr.logic;

import java.util.LinkedList;

/**
 * Left and right border point lists of the track.
 *
 * @author CGH
 */
public final class Track {
	private final LinkedList<int[]>	lhs	= new LinkedList<>();
	private final LinkedList<int[]>	rhs	= new LinkedList<>();

	public void addLeft(final int x, final int y) {
		lhs.add(new int[]{x, y });
	}

	public void addRight(final int x, final int y) {
		rhs.add(new int[]{x, y });
	}

	public LinkedList<int[]> getLeft() {
		return lhs;
	}

	public LinkedList<int[]> getRight() {
		return rhs;
	}

	public void removeLastLeft() {
		if (!lhs.isEmpty())
			lhs.removeLast();
	}

	public void removeLastRight() {
		if (!rhs.isEmpty())
			rhs.removeLast();
	}
}
