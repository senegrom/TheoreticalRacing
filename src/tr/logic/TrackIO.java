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
					.map(p -> {
					final String fileName = p.getFileName().toString();
					return fileName.substring(0, fileName.length() - ".track".length());
				})
					.sorted()
					.toList();
		} catch (final IOException e) {
			return java.util.List.of();
		}
	}

	/** Parsed track data — used by the chooser for previews and by loadTrack to update props. */
	public static record TrackData(String name, int gameX, int gameY, LinkedList<int[]> left, LinkedList<int[]> right) {}

	static boolean validTrackName(final String name) {
		if (name == null || name.isEmpty())
			return false;
		for (int i = 0; i < name.length(); i++) {
			final char c = name.charAt(i);
			if (!Character.isLetterOrDigit(c) && c != '_' && c != '-')
				return false;
		}
		return true;
	}

	/** Parse a named .track file. Returns null on miss / parse failure. */
	public static TrackData loadTrackData(final String name) {
		if (!validTrackName(name))
			return null;
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
		int gx;
		int gy;
		try {
			gx = Integer.parseInt(tp.getProperty("gameX", String.valueOf(RaceGame.defCols)));
			gy = Integer.parseInt(tp.getProperty("gameY", String.valueOf(RaceGame.defRows)));
		} catch (final NumberFormatException e) {
			return null;
		}
		if (gx < 2 || gy < 2 || gx > 500 || gy > 500 || !validBorders(left, right)
				|| !pointsWithinGrid(left, gx, gy) || !pointsWithinGrid(right, gx, gy))
			return null;
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
		int gx;
		int gy;
		try {
			gx = Integer.parseInt(prop.getProperty("gameX", String.valueOf(RaceGame.defCols)));
			gy = Integer.parseInt(prop.getProperty("gameY", String.valueOf(RaceGame.defRows)));
		} catch (final NumberFormatException e) {
			return null;
		}
		if (gx < 2 || gy < 2 || gx > 500 || gy > 500 || !validBorders(l, r)
				|| !pointsWithinGrid(l, gx, gy) || !pointsWithinGrid(r, gx, gy))
			return null;
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
		return loadLastTrackData(prop) != null;
	}

	/** Basic structural validity shared by file loading and drawn-track checks. */
	static boolean validBorders(final LinkedList<int[]> left, final LinkedList<int[]> right) {
		if (left == null || right == null || left.size() < 2 || right.size() < 2)
			return false;
		if (samePoint(left.getFirst(), right.getFirst()) || samePoint(left.getLast(), right.getLast()))
			return false;
		return noConsecutiveDuplicates(left) && noConsecutiveDuplicates(right);
	}

	private static boolean noConsecutiveDuplicates(final LinkedList<int[]> points) {
		int[] previous = null;
		for (final int[] point : points) {
			if (previous != null && samePoint(previous, point))
				return false;
			previous = point;
		}
		return true;
	}

	private static boolean pointsWithinGrid(final LinkedList<int[]> points, final int gameX, final int gameY) {
		for (final int[] point : points)
			if (point[0] < 0 || point[0] > gameX || point[1] < 0 || point[1] > gameY)
				return false;
		return true;
	}

	private static boolean samePoint(final int[] a, final int[] b) {
		return a[0] == b[0] && a[1] == b[1];
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
		if (s == null || s.isBlank())
			return result;
		for (final String pair : s.split(";", -1)) {
			final String[] xy = pair.split(",", -1);
			if (xy.length != 2) {
				result.clear();
				return result;
			}
			try {
				result.add(new int[]{Integer.parseInt(xy[0].trim()), Integer.parseInt(xy[1].trim()) });
			} catch (final NumberFormatException e) {
				result.clear();
				return result;
			}
		}
		return result;
	}

}
