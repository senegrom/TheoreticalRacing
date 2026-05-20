package tr.logic;

import java.awt.Color;
import java.util.LinkedList;

/**
 * Position, velocity, identity and history of a single player.
 *
 * @author CGH
 */
public class Player {
	public final static int INIT_POS = -100000;

	public enum Kind {
		HUMAN, AI1, AI2;

		public static Kind parse(final String s) {
			if (s == null)
				return HUMAN;
			final String t = s.trim().toLowerCase();
			return switch (t) {
				case "ai1", "true" -> AI1;
				case "ai2" -> AI2;
				default -> HUMAN;
			};
		}

		public String label() {
			return this == HUMAN ? "" : " [" + name() + "]";
		}
	}

	private static Color brighterCol(final Color c) {
		return new Color(c.getRed() + (255 - c.getRed()) / 2, c.getGreen() + (255 - c.getGreen()) / 2,
				c.getBlue() + (255 - c.getBlue()) / 2);
	}

	private final Kind				kind;
	private final Color				brightColor;
	private final Color				color;
	private int						finishedPlace;
	private final LinkedList<int[]>	history		= new LinkedList<>();
	private final String			name;
	private final int				number;
	private int[]					position	= {INIT_POS, INIT_POS };
	private int[]					velocity	= {0, 0 };

	public Player(final String name, final int number, final Color color, final Kind kind) {
		this.name = name;
		this.number = number;
		this.color = color;
		this.kind = kind;
		this.brightColor = brighterCol(color);
	}

	public boolean isAi() {
		return kind != Kind.HUMAN;
	}

	public Kind getKind() {
		return kind;
	}

	public Color getBrightColor() {
		return brightColor;
	}

	public Color getColor() {
		return color;
	}

	public int getFinishedPlace() {
		return finishedPlace;
	}

	public LinkedList<int[]> getHistory() {
		return history;
	}

	public String getName() {
		return name;
	}

	public int getNumber() {
		return number;
	}

	public int[] getPosition() {
		return position;
	}

	public int[] getVelocity() {
		return velocity;
	}

	public boolean isFinished() {
		return finishedPlace != 0;
	}

	public String statusLabel() {
		return isFinished() ? finishedPlace + "." : velocity[0] + " " + (-velocity[1]);
	}

	public void logPosition(final int[] position) {
		history.add(position);
	}

	public void setFinishedPlace(final int p) {
		finishedPlace = p;
	}

	public void setPosition(final int[] position) {
		this.position = position;
	}

	public void setVelocity(final int[] velocity) {
		this.velocity = velocity;
	}
}
