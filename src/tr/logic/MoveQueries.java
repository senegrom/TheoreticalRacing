package tr.logic;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/** Independent board queries. V2 carries laps, gates and the race turn count;
 * replies include the live referee's transition for EACH candidate. */
final class MoveQueries {
	private MoveQueries() {}

	static record Header(int mover, boolean complete, int turns, boolean simulation,
			int rounds, String world, int cap) {}
	private static record Car(int x, int y, int vx, int vy, int finished, int lap, int gate) {}

	static Header restoreBoard(final RaceGame game, final String line) {
		if (line.length() > 8192)
			throw new IllegalArgumentException("Query line is too long");
		final String[] parts = line.split(";", -1);
		if (parts.length != game.players.length + 1)
			throw new IllegalArgumentException("Query must contain exactly " + game.players.length + " player groups");
		final String[] h = parts[0].split(",", -1);
		final boolean simulation = h[0].equals("sim") || h[0].equals("sim2");
		final boolean complete = h[0].equals("v2") || h[0].equals("sim2");
		final int count = simulation ? (complete ? 7 : 5) : complete ? 4 : 1;
		if (h.length != count)
			throw new IllegalArgumentException("Malformed query header");
		final int mover = integer(h[simulation || complete ? 1 : 0]);
		final int turns = complete ? integer(h[simulation ? 5 : 2]) : 0;
		if (mover < 0 || mover >= game.players.length || turns < 0)
			throw new IllegalArgumentException("Mover or turn count out of range");
		if (complete && integer(h[simulation ? 6 : 3]) != game.totalLaps)
			throw new IllegalArgumentException("Query lap count does not match the loaded race profile");
		final int rounds = simulation ? integer(h[2]) : 0;
		final String world = simulation ? h[3].trim() : "";
		final int cap = simulation ? integer(h[4]) : 0;
		if (simulation && (rounds < 1 || rounds > 10000 || cap < 0 || cap > game.players.length
				|| !(world.equals("smom") || world.equals("scorer") || world.equals("true"))))
			throw new IllegalArgumentException("Invalid simulation rounds, world or rival cap");
		final Car[] cars = new Car[game.players.length];
		for (int i = 0; i < cars.length; i++) {
			final String[] f = parts[i + 1].split(",", -1);
			if (complete ? f.length != 7 : f.length != 5 && f.length != 6)
				throw new IllegalArgumentException(complete
						? "V2 player group must be x,y,vx,vy,finished,lap,gate"
						: "Player query group must be x,y,vx,vy,finished[,gate]");
			final int x = integer(f[0]), y = integer(f[1]);
			final int vx = integer(f[2]), vy = integer(f[3]), finished = integer(f[4]);
			final int lap = complete ? integer(f[5]) : 0;
			final int gate = complete ? integer(f[6]) : f.length == 6 ? integer(f[5])
					: game.lapGates == null ? 0 : 1;
			if (finished < 0 || RaceGame.aiVelocityOutOfRange(vx, vy) || gate < 0 || gate > 2
					|| lap < 0 || lap > game.totalLaps || finished == 0 && lap == game.totalLaps)
				throw new IllegalArgumentException("Query velocity, finished marker or lap/gate out of range");
			if (finished == 0) {
				if (x < 0 || y < 0 || x > game.gameCols || y > game.gameRows)
					throw new IllegalArgumentException("Live player position outside grid");
				for (int j = 0; j < i; j++)
					if (cars[j].finished() == 0 && cars[j].x() == x && cars[j].y() == y)
						throw new IllegalArgumentException("Two live players occupy the same cell");
			}
			cars[i] = new Car(x, y, vx, vy, finished, lap, gate);
		}
		if (cars[mover].finished() != 0)
			throw new IllegalArgumentException("Mover is already finished");
		// Validate the WHOLE request before mutating any player. Missing legacy
		// fields have explicit defaults, never state inherited from a prior query.
		for (int i = 0; i < cars.length; i++) {
			final Car c = cars[i];
			final Player player = game.players[i];
			player.setPosition(new int[]{c.x(), c.y()});
			player.setVelocity(new int[]{c.vx(), c.vy()});
			player.setFinishedPlace(c.finished());
			player.restoreLapState(new int[]{c.lap(), c.gate(), 0, 0, 0, 0});
			player.getHistory().clear();
		}
		game.subgamestate = mover;
		game.setQueryTurnCounter(turns);
		return new Header(mover, complete, turns, simulation, rounds, world, cap);
	}

	private static int integer(final String value) {
		return Integer.parseInt(value.trim());
	}

	/** Mask + transition tokens in Direction.values() order. F means an ACTUAL
	 * terminal finish, not merely a geometric crossing. Non-final laps are A/D
	 * with an explicit LAP transition in V2. T is a referee timeout (V2 only). */
	static String candidates(final RaceGame game, final int mover, final boolean complete) {
		final Player player = game.players[mover];
		final int[] p = player.getPosition(), v = player.getVelocity();
		final StringBuilder mask = new StringBuilder(9), transitions = new StringBuilder();
		for (final Direction d : Direction.values()) {
			final int vx = v[0] + d.dx, vy = v[1] + d.dy;
			final int[] destination = {p[0] + vx, p[1] + vy};
			char c;
			String status;
			int lap = player.getLap(), gate = player.getNextGate(), cp = 0;
			if (complete && game.raceTurnLimitReached()) {
				c = 'T';
				status = "TIMEOUT";
			} else if (RaceGame.aiVelocityOutOfRange(vx, vy)) {
				c = 'X';
				status = "CRASH";
			} else {
				final RaceGame.MoveResult result = game.evaluateMove(player, p, destination);
				c = result.finishes() ? 'F' : !result.geometryLegal() ? 'X' : !result.legal() ? 'B'
						: !game.reach.isAlive(destination[0], destination[1], vx, vy) ? 'D' : 'A';
				status = result.finishes() ? "FINISH" : !result.legal() ? "CRASH"
						: result.lapCross() ? "LAP" : "OK";
				lap = result.lapAfter();
				gate = result.gateAfter();
				cp = (result.passCp1() ? 1 : 0) | (result.passCp2() ? 2 : 0);
			}
			mask.append(c);
			if (transitions.length() > 0)
				transitions.append('|');
			transitions.append(status).append(',').append(lap).append(',').append(gate).append(',').append(cp);
		}
		return mask + (complete ? ";" + transitions : "");
	}

	static String answer(final RaceGame game, final String line) {
		final Header header = restoreBoard(game, line);
		if (header.simulation()) {
			final int[] audit = new int[3];
			final int verdict;
			game.ai.simTrace = true;
			try {
				verdict = game.ai.querySimOutcome(header.mover(), header.rounds(),
						!header.world().equals("smom"), header.world().equals("true"),
						false, header.cap(), audit);
			} finally {
				game.ai.simTrace = false;
			}
			System.err.flush();
			return "V=" + verdict + ";tier=" + audit[0] + ";thread=" + audit[1] + ";snug=" + audit[2];
		}
		final Direction move = game.ai.computeAiMove();
		return (header.complete() ? "v2;" : "") + move.dx + "," + move.dy + ";"
				+ candidates(game, header.mover(), header.complete());
	}

	static void process(final RaceGame game, final String inPath, final String outPath) {
		final boolean interactive = inPath.equals("-");
		try (BufferedReader reader = interactive
				? new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))
				: Files.newBufferedReader(Path.of(inPath));
				BufferedWriter writer = interactive
						? new BufferedWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8))
						: Files.newBufferedWriter(Path.of(outPath))) {
			String line;
			while ((line = reader.readLine()) != null) {
				line = line.trim();
				if (line.equals("quit"))
					break;
				if (line.isEmpty())
					continue;
				writer.write(answer(game, line));
				writer.newLine();
				writer.flush();
			}
		} catch (final IOException error) {
			error.printStackTrace();
			System.exit(3);
		}
		if (!interactive)
			System.out.println("answered queries -> " + outPath);
	}
}
