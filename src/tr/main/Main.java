package tr.main;

import java.awt.EventQueue;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;
import javax.swing.UIManager;
import tr.logic.RaceGame;

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
		for (int i = 0; i < args.length; i++) {
			final String a = args[i];
			if ("--auto".equals(a))
				auto = true;
			else if ("--track".equals(a) && i + 1 < args.length)
				trackName = args[++i];
			else if ("--list-tracks".equals(a))
				listTracks = true;
		}

		if (listTracks) {
			for (final String name : RaceGame.listTracks())
				System.out.println(name);
			return;
		}

		final Properties prop = loadProperties();
		if (trackName != null && !RaceGame.loadTrack(prop, trackName)) {
			System.err.println("Track not found: " + trackName);
			System.err.println("Available: " + RaceGame.listTracks());
			System.exit(2);
		}

		final boolean autoMode = auto;
		EventQueue.invokeLater(() -> {
			final RaceGame game = new RaceGame(prop);
			game.setAutoMode(autoMode);
			game.start();
		});
	}

	private static Properties loadProperties() {
		final Properties prop = new Properties();
		// 1. User properties from user-home dir (preferred)
		final Path userProp = RaceGame.userPropertiesPath();
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
