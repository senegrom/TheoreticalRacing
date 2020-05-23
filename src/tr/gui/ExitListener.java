package tr.gui;

import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.WindowEvent;
import java.awt.event.WindowListener;
import tr.logic.RaceGame;

/**
 * Listen to all exit buttons
 *
 * @author CGH
 */
public class ExitListener implements ActionListener, WindowListener {

	private final RaceGame	game;

	public ExitListener(final RaceGame game) {
		super();
		this.game = game;
	}

	@Override
	public void actionPerformed(final ActionEvent arg0) {
		game.exitMe();
	}

	@Override
	public void windowActivated(final WindowEvent arg0) {}

	@Override
	public void windowClosed(final WindowEvent arg0) {}

	@Override
	public void windowClosing(final WindowEvent arg0) {
		game.exitMe();
		// arg0.getWindow().
	}

	@Override
	public void windowDeactivated(final WindowEvent arg0) {}

	@Override
	public void windowDeiconified(final WindowEvent arg0) {}

	@Override
	public void windowIconified(final WindowEvent arg0) {}

	@Override
	public void windowOpened(final WindowEvent arg0) {}

}
