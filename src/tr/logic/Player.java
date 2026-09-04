package tr.logic;

import java.awt.Color;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Position, velocity, identity and history of a single player.
 *
 * @author CGH
 */
public final class Player {
	public final static int INIT_POS = -100000;

	public enum Kind {
		HUMAN, AI1, AI2;

		public static Kind parse(final String value) {
			if (value == null)
				return HUMAN;
			try {
				return valueOf(value.trim().toUpperCase(Locale.ROOT));
			} catch (final IllegalArgumentException e) {
				return HUMAN;
			}
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
	private int						lap;
	private int						nextGate	= 1;
	private int						traceStart;
	private final int[]				gateMark	= new int[3];
	private final List<int[]>			history		= new ArrayList<>();
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

	public List<int[]> getHistory() {
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

	/** Completed S/F crossings this race (multi-lap mode). */
	public int getLap() {
		return lap;
	}

	/** Records one more completed crossing; returns the new count. */
	public int incrementLap() {
		return ++lap;
	}

	/** Multi-lap gate order: 1 = CP1 next, 2 = CP2 next, 0 = S/F next. */
	public int getNextGate() {
		return nextGate;
	}

	public void setNextGate(final int g) {
		nextGate = g;
	}

	/** Multi-lap trace pruning: first history index still drawn. */
	public int getTraceStart() {
		return traceStart;
	}

	/** Records passing gate g (0=S/F, 1=CP1, 2=CP2): the visible trace now
	 *  starts where the PREVIOUS gate was passed. */
	public void passGate(final int g) {
		traceStart = gateMark[(g + 2) % 3];
		gateMark[g] = Math.max(0, history.size() - 1);
	}

	/** Multi-lap progress, for the undo snapshot: lap, next gate, trace start
	 *  and the three gate marks. Undo rewinds position and velocity, so it has
	 *  to rewind the gate ledger with them or a rewound crossing stays banked. */
	int[] lapState() {
		return new int[] { lap, nextGate, traceStart, gateMark[0], gateMark[1], gateMark[2] };
	}

	void restoreLapState(final int[] state) {
		lap = state[0];
		nextGate = state[1];
		traceStart = state[2];
		gateMark[0] = state[3];
		gateMark[1] = state[4];
		gateMark[2] = state[5];
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
