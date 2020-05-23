package tr.gui;

import java.awt.BorderLayout;
import java.awt.Dimension;
import java.awt.GridLayout;
import java.awt.event.ActionListener;
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
import tr.logic.Player;
import tr.logic.RaceGame;

/**
 * JFrame extension containing the main game
 *
 * @author CGH
 */
public class GameUI extends JFrame {
	private final static int	rightSize			= 170;
	private static final long	serialVersionUID	= -8111395739974463615L;

	private final JButton[]		btnDirections;
	private final JButton		btnExit;
	private final JButton		btnOK;
	private final JButton		btnRestart;
	private final JButton		btnUndo;
	private final JLabel[]		lblPlayerInfo;
	private final JLabel		lblStatus;

	public GameUI(final String s, final int maxPlayers) {
		super(s);
		lblStatus = new JLabel(" ");
		btnOK = new JButton("OK");
		btnUndo = new JButton("Undo");
		btnUndo.setEnabled(false);
		btnExit = new JButton("Exit");
		btnRestart = new JButton("Restart");
		btnDirections = new JButton[9];
		for (int i = 0; i < 9; i++)
			btnDirections[i] = new JButton();
		btnDirections[0].setText("NW");
		btnDirections[1].setText("N");
		btnDirections[2].setText("NE");
		btnDirections[3].setText("W");
		btnDirections[4].setText("-");
		btnDirections[5].setText("E");
		btnDirections[6].setText("SW");
		btnDirections[7].setText("S");
		btnDirections[8].setText("SE");

		lblPlayerInfo = new JLabel[maxPlayers];
	}

	public JButton[] getBtnDirections() {
		return btnDirections;
	}

	public JButton getBtnExit() {
		return btnExit;
	}

	public JButton getBtnOK() {
		return btnOK;
	}

	public JButton getBtnUndo() {
		return btnUndo;
	}

	public void setOKText(final String s) {
		btnOK.setText(s);
	}

	public void setPlayerInfo(final String s, final int i) {
		lblPlayerInfo[i].setText(s);
	}

	public void setStatus(final String s) {
		lblStatus.setText(s);
	}

	public void setUndoText(final String s) {
		btnUndo.setText(s);
	}

	public void setupUI(final Grid g, final RaceGame game, final int windowX, final int windowY, final Player[] players) {
		setSize(windowX, windowY);
		setLocationRelativeTo(null);
		setResizable(false);
		setDefaultCloseOperation(WindowConstants.DO_NOTHING_ON_CLOSE);

		setLayout(new BorderLayout());
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

		add(gridContainer, BorderLayout.CENTER);
		add(rightContainer, BorderLayout.EAST);

		add(lblStatus, BorderLayout.SOUTH);
		lblStatus.setHorizontalAlignment(SwingConstants.CENTER);

		final ExitListener lstnExit = new ExitListener(game);
		final ActionListener lstnButton = arg0 -> {
			final Object source = arg0.getSource();
			if (source == btnOK)
				game.clickedOK();
			else if (source == btnUndo)
				game.clickedUndo();
			else if (source == btnRestart)
				game.restartMe();
			else
				for (int i = 0; i < 9; i++)
					if (source == btnDirections[i])
						game.clickedDirection(i);
		};

		for (int i = 0; i < 9; i++) {
			directionContainer.add(btnDirections[i]);
			btnDirections[i].addActionListener(lstnButton);
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

		JLabel temp;
		JPanel tempP;
		for (int i = 0; i < players.length; i++) {
			temp = new JLabel();
			tempP = new JPanel();
			tempP.setLayout(new BorderLayout());
			temp.setOpaque(true);
			temp.setMaximumSize(new Dimension(10, 10));
			temp.setBackground(players[i].getColor());
			tempP.add(temp, BorderLayout.CENTER);
			playerInfoContainer.add(tempP);
			playerInfoContainer.add(new JLabel(players[i].getName()));
			lblPlayerInfo[i] = new JLabel("-");
			playerInfoContainer.add(lblPlayerInfo[i]);
		}

		rightContainer.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
		rightContainer.add(directionContainer);
		rightContainer.add(Box.createRigidArea(new Dimension(0, 10)));
		rightContainer.add(btnContainer);
		rightContainer.add(Box.createRigidArea(new Dimension(0, 10)));
		rightContainer.add(playerInfoContainer);

		// Listeners
		btnOK.addActionListener(lstnButton);
		btnUndo.addActionListener(lstnButton);
		btnRestart.addActionListener(lstnButton);
		btnExit.addActionListener(lstnExit);
		addWindowListener(lstnExit);

		setVisible(true);

		// Adapt size
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

		g.addMouseListener(new GridListener(game));

		repaint();
		validate();
	}
}
