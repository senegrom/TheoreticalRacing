package tr.main;

import java.awt.EventQueue;
import java.awt.GraphicsEnvironment;
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
		if (autoMode) {
			System.setProperty("java.awt.headless", "true");
			Thread.setDefaultUncaughtExceptionHandler((thread, error) -> {
				System.err.println("Uncaught exception on " + thread.getName());
				error.printStackTrace();
				System.exit(1);
			});
		} else {
			installLookAndFeel();
		}
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

	private static void installLookAndFeel() {
		if (GraphicsEnvironment.isHeadless())
			return;
		try {
			UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
		} catch (final Exception e) {
			e.printStackTrace();
		}
	}

	private static Properties loadProperties(final String override) {
		final Properties prop = new Properties();
		final Path path = override == null ? TrackIO.userPropertiesPath() : Path.of(override);
		if (!Files.isRegularFile(path)) {
			if (override != null)
				throw new IllegalArgumentException("Properties file not found: " + path);
			return prop;
		}
		try (InputStream in = Files.newInputStream(path)) {
			prop.load(in);
		} catch (final IOException e) {
			throw new IllegalStateException("Could not read properties: " + path, e);
		}
		return prop;
	}
}
