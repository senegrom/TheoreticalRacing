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
		for (final String a : args) {
			if ("--auto".equals(a))
				auto = true;
		}

		final Properties prop = loadProperties();
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
