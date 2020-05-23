package tr.main;

import java.awt.EventQueue;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.Properties;
import javax.swing.UIManager;
import tr.logic.RaceGame;

/**
 * Starts the game
 *
 * @author CGH
 */
public class Main {

	static {
		try {
			// Set System L&F
			UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
		} catch (final Exception e) {
			e.printStackTrace();
		}
	}

	public static void main(final String[] args) {
		System.out.println(RaceGame.NAME + " " + RaceGame.VERSION);
		System.out.println("=================================\n");

		final Properties prop = new Properties();
		FileInputStream input = null;

		try {
			input = new FileInputStream(RaceGame.userProperties);
			prop.load(input);
		} catch (final IOException e1) {
			try {
				input = new FileInputStream(RaceGame.defProperties);
				prop.load(input);
			} catch (final IOException e2) {
				e2.printStackTrace();
			}
		}
		try {
			input.close();
		} catch (final IOException e1) {
			e1.printStackTrace();
		}

		EventQueue.invokeLater(() -> new RaceGame(prop).start());
	}
}
