package tr.gui;

import java.awt.BorderLayout;
import java.awt.Component;
import java.awt.Dimension;
import java.awt.GridLayout;
import java.awt.event.ActionListener;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.SwingConstants;
import javax.swing.WindowConstants;
import javax.swing.border.LineBorder;
import tr.logic.Direction;
import tr.logic.Player;
import tr.logic.RaceGame;

/**
 * Main game-window facade.
 *
 * <p>The Swing frame is created lazily in {@link #setupUI}. Headless auto-play
 * still uses the lightweight button/label objects expected by {@link RaceGame},
 * but never constructs a top-level AWT window.</p>
 *
 * @author CGH
 */
public final class GameUI {
	private final static int	rightSize	= 170;

	private final JButton[]	btnDirections;
	private final JButton	btnExit;
	private final JButton	btnOK;
	private final JButton	btnRestart;
	private final JButton	btnUndo;
	private JFrame			frame;
	private final JLabel[]	lblPlayerInfo;
	private final JLabel	lblStatus;
	private final String	title;

	public GameUI(final String title, final int maxPlayers) {
		this.title = title;
		lblStatus = new JLabel(" ");
		btnOK = new JButton("OK");
		btnUndo = new JButton("Undo");
		btnUndo.setEnabled(false);
		btnExit = new JButton("Exit");
		btnRestart = new JButton("Restart");
		btnDirections = new JButton[Direction.values().length];
		for (int i = 0; i < btnDirections.length; i++)
			btnDirections[i] = new JButton(Direction.fromIndex(i).label());
		lblPlayerInfo = new JLabel[maxPlayers];
		for (int i = 0; i < maxPlayers; i++)
			lblPlayerInfo[i] = new JLabel("-");
	}

	public void dispose() {
		if (frame != null)
			frame.dispose();
	}

	/** Parent component for dialogs, or {@code null} in headless mode. */
	public Component getDialogParent() {
		return frame;
	}

	public JButton[] getBtnDirections() {
		return btnDirections;
	}

	public JButton getBtnOK() {
		return btnOK;
	}

	public JButton getBtnUndo() {
		return btnUndo;
	}

	public void repaint() {
		if (frame != null)
			frame.repaint();
	}

	public void setPlayerInfo(final String s, final int i) {
		lblPlayerInfo[i].setText(s);
	}

	public void setStatus(final String s) {
		lblStatus.setText(s);
	}

	public void setupUI(final Grid g, final RaceGame game, final int windowX, final int windowY, final Player[] players) {
		if (frame != null)
			throw new IllegalStateException("game window already initialized");
		frame = new JFrame(title);
		frame.setSize(windowX, windowY);
		frame.setLocationRelativeTo(null);
		frame.setResizable(false);
		frame.setDefaultCloseOperation(WindowConstants.DO_NOTHING_ON_CLOSE);

		frame.setLayout(new BorderLayout());
		final JPanel gridContainer = new JPanel();
		final JPanel rightContainer = new JPanel();
		final JPanel directionContainer = new JPanel();
		final JPanel playerInfoContainer = new JPanel();
		final JPanel btnContainer = new JPanel();

		gridContainer.setLayout(null);
		rightContainer.setLayout(new BoxLayout(rightContainer, BoxLayout.Y_AXIS));
		directionContainer.setLayout(new GridLayout(3, 3, 1, 1));
		playerInfoContainer.setLayout(new GridLayout(players.length, 3, 5, 5));
		btnContainer.setLayout(new GridLayout(0, 1, 1, 1));

		frame.add(gridContainer, BorderLayout.CENTER);
		frame.add(rightContainer, BorderLayout.EAST);
		frame.add(lblStatus, BorderLayout.SOUTH);
		lblStatus.setHorizontalAlignment(SwingConstants.CENTER);

		final ActionListener lstnButton = event -> {
			final Object source = event.getSource();
			if (source == btnOK)
				game.clickedOK();
			else if (source == btnUndo)
				game.clickedUndo();
			else if (source == btnRestart)
				game.restartMe();
			else
				for (int i = 0; i < btnDirections.length; i++)
					if (source == btnDirections[i]) {
						game.clickedDirection(Direction.fromIndex(i));
						break;
					}
		};

		for (final JButton b : btnDirections) {
			directionContainer.add(b);
			b.addActionListener(lstnButton);
		}
		directionContainer.setMaximumSize(new Dimension(rightSize, rightSize));
		btnContainer.setMaximumSize(new Dimension(rightSize, rightSize));
		playerInfoContainer.setMaximumSize(new Dimension(rightSize, players.length * 15));
		directionContainer.setAlignmentX(0f);
		btnContainer.setAlignmentX(0f);
		playerInfoContainer.setAlignmentX(0f);

		btnContainer.add(btnOK);
		btnContainer.add(btnUndo);
		btnContainer.add(btnRestart);
		btnContainer.add(btnExit);

		for (int i = 0; i < players.length; i++) {
			final JLabel colorLbl = new JLabel();
			colorLbl.setOpaque(true);
			colorLbl.setMaximumSize(new Dimension(10, 10));
			colorLbl.setBackground(players[i].getColor());
			final JPanel colorPanel = new JPanel(new BorderLayout());
			colorPanel.add(colorLbl, BorderLayout.CENTER);
			playerInfoContainer.add(colorPanel);
			playerInfoContainer.add(new JLabel(players[i].getName() + players[i].getKind().label()));
			lblPlayerInfo[i] = new JLabel("-");
			playerInfoContainer.add(lblPlayerInfo[i]);
		}

		rightContainer.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
		rightContainer.add(directionContainer);
		rightContainer.add(Box.createRigidArea(new Dimension(0, 10)));
		rightContainer.add(btnContainer);
		rightContainer.add(Box.createRigidArea(new Dimension(0, 10)));
		rightContainer.add(playerInfoContainer);

		btnOK.addActionListener(lstnButton);
		btnUndo.addActionListener(lstnButton);
		btnRestart.addActionListener(lstnButton);
		btnExit.addActionListener(event -> game.exitMe());
		frame.addWindowListener(new WindowAdapter() {
			@Override
			public void windowClosing(final WindowEvent event) {
				game.exitMe();
			}
		});

		frame.setVisible(true);

		final Dimension minSize = new Dimension(g.cols * RaceUI.GRID_DIST + 1, g.rows * RaceUI.GRID_DIST + 1);
		g.setSize(minSize);
		g.setMinimumSize(minSize);
		g.setPreferredSize(minSize);

		final Dimension contSize = gridContainer.getSize();
		final JScrollPane scroller = new JScrollPane(g);
		gridContainer.add(scroller);
		scroller.setBorder(new LineBorder(null, 0));
		scroller.setSize(
				Math.min(contSize.width,
						minSize.width + (contSize.height < minSize.height ? scroller.getVerticalScrollBar().getMinimumSize().width : 0)),
				Math.min(contSize.height,
						minSize.height + (contSize.width < minSize.width ? scroller.getHorizontalScrollBar().getMinimumSize().height : 0)));
		scroller.setLocation(Math.max((contSize.width - minSize.width) / 2, 0), Math.max((contSize.height - minSize.height) / 2, 0));

		g.addMouseListener(new MouseAdapter() {
			@Override
			public void mousePressed(final MouseEvent event) {
				final int x = (int) Math.round(event.getX() / (double) RaceUI.GRID_DIST);
				final int y = (int) Math.round(event.getY() / (double) RaceUI.GRID_DIST);
				game.clickedGrid(x, y);
			}
		});

		frame.repaint();
		frame.validate();
	}
}
