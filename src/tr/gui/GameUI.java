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
import java.util.Arrays;
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

/** Main game-window facade. Swing controls are allocated only for GUI games. */
public final class GameUI {
	@FunctionalInterface
	public interface EnabledControl {
		void setEnabled(boolean enabled);
	}

	private static final JButton[] NO_DIRECTION_BUTTONS = new JButton[0];
	private static final int RIGHT_SIZE = 170;

	private JButton[] btnDirections;
	private JButton btnExit;
	private JButton btnOK;
	private JButton btnRestart;
	private JButton btnUndo;
	private boolean directionsEnabled = true;
	private JFrame frame;
	private JLabel[] lblPlayerInfo;
	private JLabel lblStatus;
	private final int maxPlayers;
	private final EnabledControl okControl = this::setOkEnabled;
	private final EnabledControl undoControl = this::setUndoEnabled;
	private boolean okEnabled = true;
	private final String[] playerInfo;
	private String status = " ";
	private final String title;
	private boolean undoEnabled;

	public GameUI(final String title, final int maxPlayers) {
		this.title = title;
		this.maxPlayers = maxPlayers;
		playerInfo = new String[maxPlayers];
		Arrays.fill(playerInfo, "-");
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
		return btnDirections == null ? NO_DIRECTION_BUTTONS : btnDirections;
	}

	public EnabledControl getBtnOK() {
		return okControl;
	}

	public EnabledControl getBtnUndo() {
		return undoControl;
	}

	public void repaint() {
		if (frame != null)
			frame.repaint();
	}

	public void setDirectionsEnabled(final boolean enabled) {
		directionsEnabled = enabled;
		if (btnDirections != null)
			for (final JButton button : btnDirections)
				button.setEnabled(enabled);
	}

	public void setOkEnabled(final boolean enabled) {
		okEnabled = enabled;
		if (btnOK != null)
			btnOK.setEnabled(enabled);
	}

	public void setUndoEnabled(final boolean enabled) {
		undoEnabled = enabled;
		if (btnUndo != null)
			btnUndo.setEnabled(enabled);
	}

	public void setPlayerInfo(final String text, final int i) {
		playerInfo[i] = text;
		if (lblPlayerInfo != null)
			lblPlayerInfo[i].setText(text);
	}

	public void setStatus(final String text) {
		status = text;
		if (lblStatus != null)
			lblStatus.setText(text);
	}

	public void setupUI(final JPanel grid, final RaceGame game, final int windowX, final int windowY, final Player[] players) {
		if (frame != null)
			throw new IllegalStateException("game window already initialized");
		createControls();
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
		final JPanel buttonContainer = new JPanel();
		gridContainer.setLayout(null);
		rightContainer.setLayout(new BoxLayout(rightContainer, BoxLayout.Y_AXIS));
		directionContainer.setLayout(new GridLayout(3, 3, 1, 1));
		playerInfoContainer.setLayout(new GridLayout(players.length, 3, 5, 5));
		buttonContainer.setLayout(new GridLayout(0, 1, 1, 1));

		frame.add(gridContainer, BorderLayout.CENTER);
		frame.add(rightContainer, BorderLayout.EAST);
		frame.add(lblStatus, BorderLayout.SOUTH);
		lblStatus.setHorizontalAlignment(SwingConstants.CENTER);

		final ActionListener buttonListener = event -> {
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

		for (final JButton button : btnDirections) {
			directionContainer.add(button);
			button.addActionListener(buttonListener);
		}
		directionContainer.setMaximumSize(new Dimension(RIGHT_SIZE, RIGHT_SIZE));
		buttonContainer.setMaximumSize(new Dimension(RIGHT_SIZE, RIGHT_SIZE));
		playerInfoContainer.setMaximumSize(new Dimension(RIGHT_SIZE, players.length * 15));
		directionContainer.setAlignmentX(0f);
		buttonContainer.setAlignmentX(0f);
		playerInfoContainer.setAlignmentX(0f);

		buttonContainer.add(btnOK);
		buttonContainer.add(btnUndo);
		buttonContainer.add(btnRestart);
		buttonContainer.add(btnExit);
		for (int i = 0; i < players.length; i++) {
			final JLabel colorLabel = new JLabel();
			colorLabel.setOpaque(true);
			colorLabel.setMaximumSize(new Dimension(10, 10));
			colorLabel.setBackground(players[i].getColor());
			final JPanel colorPanel = new JPanel(new BorderLayout());
			colorPanel.add(colorLabel, BorderLayout.CENTER);
			playerInfoContainer.add(colorPanel);
			playerInfoContainer.add(new JLabel(players[i].getName() + players[i].getKind().label()));
			playerInfoContainer.add(lblPlayerInfo[i]);
		}

		rightContainer.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
		rightContainer.add(directionContainer);
		rightContainer.add(Box.createRigidArea(new Dimension(0, 10)));
		rightContainer.add(buttonContainer);
		rightContainer.add(Box.createRigidArea(new Dimension(0, 10)));
		rightContainer.add(playerInfoContainer);

		btnOK.addActionListener(buttonListener);
		btnUndo.addActionListener(buttonListener);
		btnRestart.addActionListener(buttonListener);
		btnExit.addActionListener(event -> game.exitMe());
		frame.addWindowListener(new WindowAdapter() {
			@Override
			public void windowClosing(final WindowEvent event) {
				game.exitMe();
			}
		});

		final Dimension minSize = grid.getPreferredSize();
		grid.setSize(minSize);
		grid.setMinimumSize(minSize);
		final Dimension containerSize = gridContainer.getSize();
		final JScrollPane scroller = new JScrollPane(grid);
		gridContainer.add(scroller);
		scroller.setBorder(new LineBorder(null, 0));
		scroller.setSize(
				Math.min(containerSize.width,
						minSize.width + (containerSize.height < minSize.height ? scroller.getVerticalScrollBar().getMinimumSize().width : 0)),
				Math.min(containerSize.height,
						minSize.height + (containerSize.width < minSize.width ? scroller.getHorizontalScrollBar().getMinimumSize().height : 0)));
		scroller.setLocation(Math.max((containerSize.width - minSize.width) / 2, 0), Math.max((containerSize.height - minSize.height) / 2, 0));
		grid.addMouseListener(new MouseAdapter() {
			@Override
			public void mousePressed(final MouseEvent event) {
				final int x = (int) Math.round(event.getX() / (double) RaceUI.GRID_DIST);
				final int y = (int) Math.round(event.getY() / (double) RaceUI.GRID_DIST);
				game.clickedGrid(x, y);
			}
		});

		frame.setVisible(true);
		frame.repaint();
		frame.validate();
	}

	private void createControls() {
		lblStatus = new JLabel(status);
		btnOK = new JButton("OK");
		btnOK.setEnabled(okEnabled);
		btnUndo = new JButton("Undo");
		btnUndo.setEnabled(undoEnabled);
		btnExit = new JButton("Exit");
		btnRestart = new JButton("Restart");
		btnDirections = new JButton[9];
		for (int i = 0; i < btnDirections.length; i++) {
			btnDirections[i] = new JButton(Direction.fromIndex(i).label());
			btnDirections[i].setEnabled(directionsEnabled);
		}
		lblPlayerInfo = new JLabel[maxPlayers];
		for (int i = 0; i < maxPlayers; i++)
			lblPlayerInfo[i] = new JLabel(playerInfo[i]);
	}
}
