package tr.logic;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;

/** Malformed user track properties must fail without losing the saved circuit. */
public final class TrackImportTests {
    private TrackImportTests() {}

    public static void main(final String[] args) throws IOException {
        final Path directory = TrackIO.tracksDir();
        final boolean existed = Files.exists(directory);
        Files.createDirectories(directory);
        final Path file = Files.createTempFile(directory, "import-regression-", ".track");
        final String name = file.getFileName().toString().replaceFirst("\\.track$", "");
        final String valid = "gameX=20\ngameY=20\ntrackLeft=2,2;18,2\n"
                + "trackRight=2,6;18,6\nlapClosable=true\n";
        try {
            final Properties saved = new Properties();
            saved.setProperty("personal", "unchanged");
            Files.writeString(file, valid, StandardCharsets.US_ASCII);
            check(TrackIO.loadTrack(saved, name), "valid track rejected");
            final Properties before = new Properties();
            before.putAll(saved);
            for (final String key : new String[]{"name", "trackLeft", "lapClosable"}) {
                Files.writeString(file, valid + key + "=" + "\\" + "u12x4\n", StandardCharsets.US_ASCII);
                check(TrackIO.loadTrackData(name) == null, "invalid escape accepted by preview parser");
                check(!TrackIO.loadTrack(saved, name), "invalid escape accepted by track loader");
                check(!TrackIO.trackDeclaresClosable(name), "invalid escape granted lap closure");
                check(before.equals(saved), "failed load changed the previous track/settings");
            }
            Files.writeString(file, valid + "name=Caf" + "\\" + "u00e9\n", StandardCharsets.US_ASCII);
            check("Caf\u00e9".equals(TrackIO.loadTrackData(name).name()), "valid Unicode escape rejected");
            check(TrackIO.trackDeclaresClosable(name), "valid closure declaration lost");
            check(TrackIO.loadTrack(saved, name), "recovery after repairing track failed");
            System.out.println("TrackImportTests: malformed escapes rejected; saved settings and valid Unicode preserved");
        } finally {
            Files.deleteIfExists(file);
            if (!existed) Files.deleteIfExists(directory);
        }
    }

    private static void check(final boolean condition, final String message) {
        if (!condition) throw new AssertionError(message);
    }
}
