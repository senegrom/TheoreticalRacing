package tr.logic;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedList;
import java.util.Properties;

/**
 * Static track file/properties IO extracted from {@link RaceGame}: locating the
 * install dir and its files, listing/parsing .track files, and (de)serialising
 * point lists. Pure IO/parse helpers — no game state.
 */
public final class TrackIO {
	private TrackIO() {}

	/** Directory containing the JAR (or the classes dir in dev runs). */
	private static Path installDir() {
		try {
			final Path codeSource = Path.of(RaceGame.class.getProtectionDomain().getCodeSource().getLocation().toURI());
			return Files.isDirectory(codeSource) ? codeSource : codeSource.getParent();
		} catch (final Exception e) {
			return Path.of(".");
		}
	}

	/** Path to the user's saved properties (next to the JAR). */
	public static Path userPropertiesPath() {
		return installDir().resolve("user.properties");
	}

	/** Path to the per-session game log (next to the JAR). */
	public static Path gameLogPath() {
		return installDir().resolve("last_game.log");
	}

	/** Directory containing .track files. */
	public static Path tracksDir() {
		return installDir().resolve("tracks");
	}

	/** List names of available tracks (file stem, without .track suffix). */
	public static java.util.List<String> listTracks() {
		final Path dir = tracksDir();
		if (!Files.isDirectory(dir))
			return java.util.List.of();
		try (java.util.stream.Stream<Path> s = Files.list(dir)) {
			return s.filter(p -> p.toString().endsWith(".track"))
					.map(p -> p.getFileName().toString().replaceFirst("\\.track$", ""))
					.sorted()
					.toList();
		} catch (final IOException e) {
			return java.util.List.of();
		}
	}

	/** Parsed track data — used by the chooser for previews and by loadTrack to update props. */
	public static record TrackData(String name, int gameX, int gameY, LinkedList<int[]> left, LinkedList<int[]> right) {}

	/** Parse a named .track file. Returns null on miss / parse failure. */
	public static TrackData loadTrackData(final String name) {
		final Path file = tracksDir().resolve(name + ".track");
		if (!Files.isRegularFile(file))
			return null;
		final Properties tp = new Properties();
		try (java.io.InputStream in = Files.newInputStream(file)) {
			tp.load(in);
		} catch (final IOException e) {
			return null;
		}
		final LinkedList<int[]> left = parsePointList(tp.getProperty("trackLeft"));
		final LinkedList<int[]> right = parsePointList(tp.getProperty("trackRight"));
		if (left.size() < 2 || right.size() < 2)
			return null;
		int gx;
		int gy;
		try {
			gx = Integer.parseInt(tp.getProperty("gameX", String.valueOf(RaceGame.defCols)));
			gy = Integer.parseInt(tp.getProperty("gameY", String.valueOf(RaceGame.defRows)));
		} catch (final NumberFormatException e) {
			gx = RaceGame.defCols;
			gy = RaceGame.defRows;
		}
		return new TrackData(tp.getProperty("name", name), gx, gy, left, right);
	}

	/** Parse the "last track" data straight out of a Properties bundle. Null if missing/invalid. */
	public static TrackData loadLastTrackData(final Properties prop) {
		final String left = prop.getProperty("lastTrackLeft");
		final String right = prop.getProperty("lastTrackRight");
		if (left == null || right == null || left.isEmpty() || right.isEmpty())
			return null;
		final LinkedList<int[]> l = parsePointList(left);
		final LinkedList<int[]> r = parsePointList(right);
		if (l.size() < 2 || r.size() < 2)
			return null;
		int gx;
		int gy;
		try {
			gx = Integer.parseInt(prop.getProperty("gameX", String.valueOf(RaceGame.defCols)));
			gy = Integer.parseInt(prop.getProperty("gameY", String.valueOf(RaceGame.defRows)));
		} catch (final NumberFormatException e) {
			gx = RaceGame.defCols;
			gy = RaceGame.defRows;
		}
		return new TrackData("Last", gx, gy, l, r);
	}

	/** Load a named track into {@code prop}, replacing lastTrack* + gameX/gameY. */
	public static boolean loadTrack(final Properties prop, final String name) {
		final TrackData td = loadTrackData(name);
		if (td == null)
			return false;
		prop.put("lastTrackLeft", pointListToString(td.left()));
		prop.put("lastTrackRight", pointListToString(td.right()));
		prop.put("gameX", String.valueOf(td.gameX()));
		prop.put("gameY", String.valueOf(td.gameY()));
		prop.put("useLastTrack", "true");
		return true;
	}

	public static boolean hasLastTrack(final Properties prop) {
		final String left = prop.getProperty("lastTrackLeft");
		final String right = prop.getProperty("lastTrackRight");
		return left != null && right != null && !left.isEmpty() && !right.isEmpty();
	}

	static String pointListToString(final LinkedList<int[]> list) {
		final StringBuilder sb = new StringBuilder();
		boolean first = true;
		for (final int[] p : list) {
			if (!first)
				sb.append(";");
			sb.append(p[0]).append(",").append(p[1]);
			first = false;
		}
		return sb.toString();
	}

	static LinkedList<int[]> parsePointList(final String s) {
		final LinkedList<int[]> result = new LinkedList<>();
		if (s == null || s.isEmpty())
			return result;
		for (final String pair : s.split(";")) {
			final String[] xy = pair.split(",");
			if (xy.length != 2)
				continue;
			try {
				result.add(new int[]{Integer.parseInt(xy[0].trim()), Integer.parseInt(xy[1].trim()) });
			} catch (final NumberFormatException ignored) {
			}
		}
		return result;
	}

}
