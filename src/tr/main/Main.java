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

/** Starts the game. */
public final class Main {
	private Main() {}

	static record Options(boolean auto, String trackName, boolean listTracks,
			String dumpReach, String queryIn, String queryOut, String optimalStart, Long seed, Long seedEnd,
			String logPath, String propsPath) {
		boolean headless() {
			return auto || dumpReach != null || queryIn != null || optimalStart != null;
		}
	}

	public static void main(final String[] args) {
		System.out.println(RaceGame.NAME + " " + RaceGame.VERSION);
		System.out.println("=================================\n");

		final Options options;
		try {
			options = parseArgs(args);
		} catch (final IllegalArgumentException error) {
			System.err.println(error.getMessage());
			System.err.println(usage());
			System.exit(2);
			return;
		}

		if (options.listTracks()) {
			for (final String name : TrackIO.listTracks())
				System.out.println(name);
			return;
		}

		final Properties prop;
		try {
			prop = loadProperties(options.propsPath());
		} catch (final RuntimeException error) {
			System.err.println(error.getMessage());
			System.exit(2);
			return;
		}
		if (options.trackName() != null && !TrackIO.loadTrack(prop, options.trackName())) {
			System.err.println("Track not found: " + options.trackName());
			System.err.println("Available: " + TrackIO.listTracks());
			System.exit(2);
			return;
		}

		if (options.headless()) {
			System.setProperty("java.awt.headless", "true");
			Thread.setDefaultUncaughtExceptionHandler((thread, error) -> {
				System.err.println("Uncaught exception on " + thread.getName());
				error.printStackTrace();
				System.exit(1);
			});
		} else {
			installLookAndFeel();
		}
		if (options.seedEnd() != null && options.auto()) {
			runBatch(options, prop);
			return;
		}
		EventQueue.invokeLater(() -> {
			final RaceGame game = new RaceGame(prop);
			game.setAutoMode(options.headless());
			if (options.dumpReach() != null)
				game.setDumpReachPath(options.dumpReach());
			if (options.queryIn() != null)
				game.setQueryPaths(options.queryIn(), options.queryOut());
			if (options.optimalStart() != null)
				game.setOptimalStart(options.optimalStart());
			if (options.seed() != null)
				game.setStartSeed(options.seed());
			if (options.logPath() != null)
				game.setGameLogPath(options.logPath());
			game.start();
		});
	}

	/** Batch mode: race every seed of the range in this one JVM. Each seed
	 *  gets a fresh RaceGame over a fresh Properties copy; the reachability
	 *  arrays are built once per track and reused in-process (read-only after
	 *  build), which removes the per-race JVM boot and cache-load overhead
	 *  that dominates battery wall time. */
	private static void runBatch(final Options options, final Properties baseProp) {
		final String logPattern = options.logPath() != null
				? options.logPath() : TrackIO.gameLogPath().toString();
		long s = options.seed();
		while (true) {
			final long thisSeed = s;
			final java.util.concurrent.CountDownLatch done = new java.util.concurrent.CountDownLatch(1);
			EventQueue.invokeLater(() -> {
				final Properties raceProp = new Properties();
				raceProp.putAll(baseProp);
				final RaceGame game = new RaceGame(raceProp);
				game.setAutoMode(true);
				game.setAutoRaceEndHook(done::countDown);
				game.setStartSeed(thisSeed);
				game.setGameLogPath(batchLogPath(logPattern, thisSeed));
				game.start();
			});
			try {
				done.await();
			} catch (final InterruptedException e) {
				Thread.currentThread().interrupt();
				System.exit(1);
				return;
			}
			if (s == options.seedEnd())
				break;
			s++;
		}
		System.exit(0);
	}

	/** Insert _sN before the extension: races/x.log + 7 -> races/x_s7.log. */
	private static String batchLogPath(final String pattern, final long seed) {
		final int dot = pattern.lastIndexOf('.');
		final int sep = Math.max(pattern.lastIndexOf('/'), pattern.lastIndexOf('\\'));
		if (dot > sep)
			return pattern.substring(0, dot) + "_s" + seed + pattern.substring(dot);
		return pattern + "_s" + seed;
	}

	static Options parseArgs(final String[] args) {
		boolean auto = false;
		String trackName = null;
		boolean listTracks = false;
		String dumpReach = null;
		String queryIn = null;
		String queryOut = null;
		String optimalStart = null;
		Long seed = null;
		Long seedEnd = null;
		String logPath = null;
		String propsPath = null;

		for (int i = 0; i < args.length; i++) {
			final String option = args[i];
			switch (option) {
				case "--auto" -> auto = true;
				case "--list-tracks" -> listTracks = true;
				case "--track" -> trackName = value(args, ++i, option);
				case "--dump-reach" -> dumpReach = value(args, ++i, option);
				// Exact shortest solo race from the given start cell: "x,y".
				case "--optimal-laps" -> optimalStart = value(args, ++i, option);
				case "--log" -> logPath = value(args, ++i, option);
				case "--props" -> propsPath = value(args, ++i, option);
				case "--seed" -> {
					final String raw = value(args, ++i, option);
					try {
						final int dash = raw.indexOf('-', 1);
						if (dash > 0) {
							seed = Long.valueOf(raw.substring(0, dash));
							seedEnd = Long.valueOf(raw.substring(dash + 1));
							if (seedEnd < seed)
								throw new IllegalArgumentException("--seed range end before start: " + raw);
						} else {
							seed = Long.valueOf(raw);
							seedEnd = null;
						}
					} catch (final NumberFormatException error) {
						throw new IllegalArgumentException("--seed requires an integer or A-B range: " + raw, error);
					}
				}
				case "--query-moves" -> {
					queryIn = value(args, ++i, option);
					queryOut = value(args, ++i, option);
				}
				case "--help", "-h" -> throw new IllegalArgumentException(usage());
				default -> throw new IllegalArgumentException("Unknown option: " + option);
			}
		}
		if (seedEnd != null && !auto)
			throw new IllegalArgumentException("--seed range requires --auto");
		if (seedEnd != null && (dumpReach != null || queryIn != null))
			throw new IllegalArgumentException("--seed range cannot be combined with reach/query modes");
		return new Options(auto, trackName, listTracks, dumpReach, queryIn, queryOut,
				optimalStart, seed, seedEnd, logPath, propsPath);
	}

	private static String value(final String[] args, final int index, final String option) {
		if (index >= args.length || args[index].startsWith("--"))
			throw new IllegalArgumentException(option + " requires a value");
		return args[index];
	}

	private static String usage() {
		return "Usage: java -jar theoreticRacing.jar [--auto] [--track NAME] "
				+ "[--props FILE] [--log FILE] [--seed N|A-B] [--dump-reach FILE] "
				+ "[--query-moves INPUT OUTPUT] [--optimal-laps X,Y] [--list-tracks]";
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
