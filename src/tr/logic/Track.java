package tr.logic;

import java.util.LinkedList;

/**
 * Represents the track on which the game takes place
 *
 * @author CGH
 */
public class Track {
	private final LinkedList<int[]>	lhs;
	private final LinkedList<int[]>	rhs;

	public Track() {
		lhs = new LinkedList<>();
		rhs = new LinkedList<>();
	}

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
		if (lhs.size() > 0)
			lhs.removeLast();
	}

	public void removeLastRight() {
		if (rhs.size() > 0)
			rhs.removeLast();
	}

	public void removeLeft(final int i) {
		lhs.remove(i);
	}

	public void removeRight(final int i) {
		rhs.remove(i);
	}
}
