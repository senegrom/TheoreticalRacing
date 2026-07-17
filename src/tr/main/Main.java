package tr.main;

import java.awt.EventQueue;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;
import javax.swing.UIManager;
import tr.logic.RaceGame;
import tr.logic.TrackIO;

/**
 * Starts the game.
 *
 * @author CGH
 */
public class Main {

	static {
		try {
			UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
		} catch (final Exception e) {
			e.printStackTrace();
		}
	}

	public static void main(final String[] args) {
		System.out.println(RaceGame.NAME + " " + RaceGame.VERSION);
		System.out.println("=================================\n");

		boolean auto = false;
		String trackName = null;
		boolean listTracks = false;
		String dumpReach = null;
		String queryIn = null, queryOut = null;
		Long seed = null;
		String logPath = null, propsPath = null;
		for (int i = 0; i < args.length; i++) {
			final String a = args[i];
			if ("--auto".equals(a))
				auto = true;
			else if ("--track".equals(a) && i + 1 < args.length)
				trackName = args[++i];
			else if ("--list-tracks".equals(a))
				listTracks = true;
			else if ("--dump-reach".equals(a) && i + 1 < args.length)
				dumpReach = args[++i];
			else if ("--log".equals(a) && i + 1 < args.length)
				logPath = args[++i];
			else if ("--props".equals(a) && i + 1 < args.length)
				propsPath = args[++i];
			else if ("--seed".equals(a) && i + 1 < args.length)
				seed = Long.parseLong(args[++i]);
			else if ("--query-moves".equals(a) && i + 2 < args.length) {
				queryIn = args[++i];
				queryOut = args[++i];
			}
		}

		if (listTracks) {
			for (final String name : TrackIO.listTracks())
				System.out.println(name);
			return;
		}

		final Properties prop = loadProperties(propsPath);
		if (trackName != null && !TrackIO.loadTrack(prop, trackName)) {
			System.err.println("Track not found: " + trackName);
			System.err.println("Available: " + TrackIO.listTracks());
			System.exit(2);
		}

		final boolean autoMode = auto || dumpReach != null || queryIn != null;
		final String dumpReachPath = dumpReach;
		final String qIn = queryIn, qOut = queryOut;
		final Long startSeed = seed;
		final String gameLogPath = logPath;
		EventQueue.invokeLater(() -> {
			final RaceGame game = new RaceGame(prop);
			game.setAutoMode(autoMode);
			if (dumpReachPath != null)
				game.setDumpReachPath(dumpReachPath);
			if (qIn != null)
				game.setQueryPaths(qIn, qOut);
			if (startSeed != null)
				game.setStartSeed(startSeed);
			if (gameLogPath != null)
				game.setGameLogPath(gameLogPath);
			game.start();
		});
	}

	private static Properties loadProperties(final String override) {
		final Properties prop = new Properties();
		if (override != null) {
			try (InputStream in = Files.newInputStream(Path.of(override))) {
				prop.load(in);
			} catch (final IOException e) {
				e.printStackTrace();
			}
			return prop;
		}
		// 1. User properties from user-home dir (preferred)
		final Path userProp = TrackIO.userPropertiesPath();
		if (Files.isRegularFile(userProp)) {
			try (InputStream in = Files.newInputStream(userProp)) {
				prop.load(in);
				return prop;
			} catch (final IOException e) {
				e.printStackTrace();
			}
		}
		// 2. CWD-relative default.properties (backwards compat)
		final Path defProp = Path.of(RaceGame.defProperties);
		if (Files.isRegularFile(defProp)) {
			try (InputStream in = Files.newInputStream(defProp)) {
				prop.load(in);
				return prop;
			} catch (final IOException e) {
				e.printStackTrace();
			}
		}
		// 3. Bundled default.properties resource
		try (InputStream in = Main.class.getResourceAsStream("/default.properties")) {
			if (in != null)
				prop.load(in);
		} catch (final IOException e) {
			e.printStackTrace();
		}
		// 4. Any missing keys are filled in by RaceGame's constructor defaults
		return prop;
	}
}
