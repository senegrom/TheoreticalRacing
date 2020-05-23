package tr.logic;

import java.awt.Color;
import java.util.LinkedList;

/**
 * Represents a player, its position and velocity and additional infos (color,
 * player track...)
 *
 * @author CGH
 */
public class Player {
	public final static int	INIT_POS	= -100000;

	public final static Color brighterCol(final Color c) {
		return new Color(c.getRed() + (255 - c.getRed()) / 2, c.getGreen() + (255 - c.getGreen()) / 2, c.getBlue() + (255 - c.getBlue())
				/ 2);
	}

	private final Color				brightColor;
	private final Color				color;
	private int						finishedPlace;
	private final LinkedList<int[]>	history;
	private final String			name;
	private final int				number;
	private int[]					position;

	private int[]					velocity;

	public Player(final String name, final int number, final Color color) {
		this.name = name;
		this.number = number;
		this.color = color;
		brightColor = brighterCol(color);
		position = new int[]{INIT_POS, INIT_POS };
		velocity = new int[]{0, 0 };
		finishedPlace = 0;
		history = new LinkedList<int[]>();
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
