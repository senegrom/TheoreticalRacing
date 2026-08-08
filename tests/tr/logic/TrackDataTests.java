package tr.logic;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;
import java.util.Properties;
import java.util.stream.Stream;

/** Structural regression checks for every bundled .track file. */
final class TrackDataTests {
	private TrackDataTests() {}

	static void run() {
		final List<Path> files = new ArrayList<>();
		try (Stream<Path> stream = Files.list(Path.of("tracks"))) {
			stream.filter(path -> path.getFileName().toString().endsWith(".track"))
					.sorted()
					.forEach(files::add);
		} catch (final IOException e) {
			throw new AssertionError("could not list bundled tracks", e);
		}
		check(!files.isEmpty(), "no bundled tracks found");
		for (final Path file : files)
			validate(file);
		System.out.println("TrackDataTests: " + files.size() + " tracks OK");
	}

	private static void validate(final Path file) {
		final Properties prop = new Properties();
		try (InputStream in = Files.newInputStream(file)) {
			prop.load(in);
		} catch (final IOException e) {
			throw new AssertionError(file + ": unreadable", e);
		}
		final int width = intProperty(file, prop, "gameX");
		final int height = intProperty(file, prop, "gameY");
		check(width >= 2 && height >= 2, file + ": invalid grid size");
		final List<int[]> left = TrackIO.parsePointList(prop.getProperty("trackLeft"));
		final List<int[]> right = TrackIO.parsePointList(prop.getProperty("trackRight"));
		check(left.size() >= 2, file + ": left border too short");
		check(right.size() >= 2, file + ": right border too short");
		check(!same(left.getFirst(), right.getFirst()), file + ": degenerate start line");
		check(!same(left.getLast(), right.getLast()), file + ": degenerate finish line");
		validateSide(file, "left", left, width, height);
		validateSide(file, "right", right, width, height);

		final float[][] zone = TrackGeometry.makeStartZone(left.getFirst(), right.getFirst());
		for (final float[] axis : zone)
			for (final float value : axis)
				check(Float.isFinite(value), file + ": non-finite start zone");

		final LinkedList<int[]> closed = new LinkedList<>();
		closed.addAll(left);
		closed.addAll(right.reversed());
		closed.add(left.getFirst());
		check(!TrackGeometry.checkIntersect(closed, closed, false), file + ": self-intersecting corridor");
	}

	private static void validateSide(final Path file, final String sideName, final List<int[]> side,
			final int width, final int height) {
		int[] previous = null;
		for (final int[] point : side) {
			check(point[0] >= 0 && point[0] <= width && point[1] >= 0 && point[1] <= height,
					file + ": " + sideName + " point outside grid: " + point[0] + "," + point[1]);
			check(previous == null || !same(previous, point), file + ": duplicate consecutive " + sideName + " point");
			previous = point;
		}
	}

	private static int intProperty(final Path file, final Properties prop, final String key) {
		try {
			return Integer.parseInt(prop.getProperty(key));
		} catch (final RuntimeException e) {
			throw new AssertionError(file + ": invalid " + key, e);
		}
	}

	private static boolean same(final int[] a, final int[] b) {
		return a[0] == b[0] && a[1] == b[1];
	}

	private static void check(final boolean condition, final String message) {
		if (!condition)
			throw new AssertionError(message);
	}
}
