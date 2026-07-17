package tr.gui;

import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import tr.logic.RaceGame;

/**
 * Funnels Exit button clicks and window-close events into {@code game.exitMe()}.
 *
 * @author CGH
 */
public class ExitListener extends WindowAdapter implements ActionListener {

	private final RaceGame game;

	public ExitListener(final RaceGame game) {
		this.game = game;
	}

	@Override
	public void actionPerformed(final ActionEvent arg0) {
		game.exitMe();
	}

	@Override
	public void windowClosing(final WindowEvent arg0) {
		game.exitMe();
	}
}
