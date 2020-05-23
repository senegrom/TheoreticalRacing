package tr.gui;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.Dimension;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.event.ActionListener;
import java.util.Properties;
import java.util.Scanner;
import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JButton;
import javax.swing.JColorChooser;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JTextField;
import javax.swing.SwingConstants;
import tr.logic.RaceGame;

/**
 * Start dialog of the game
 *
 * @author CGH
 */

public class StartDialog extends JFrame {
	private final static String	defTextFiller		= "00000";
	private static final long	serialVersionUID	= -5996002806608660877L;

	private final JButton		btnExit;
	private final JButton		btnMinus;
	private final JButton		btnOK;
	private final JButton[]		btnPlayer;
	private final JButton[]		btnPlayerCol;
	private final JButton		btnPlus;
	private final GridBagLayout	gridBag;
	private final JPanel		gridContainer;
	private boolean				isActive			= true;
	private final JLabel[]		lblPlayerCol;
	private final int			maxPlayers;
	private int					nPlayers;
	private final JPanel		pnlSize;
	private final Properties	prop;
	private final JTextField[]	txtSize;

	public StartDialog(final String s, final Properties prop) {
		super(s);
		this.prop = prop;
		maxPlayers = Integer.valueOf(prop.getProperty("maxPlayers"));
		nPlayers = Integer.valueOf(prop.getProperty("nPlayers"));
		btnOK = new JButton("OK");
		btnExit = new JButton("Exit");
		btnPlus = new JButton("+");
		btnMinus = new JButton("-");
		btnPlayer = new JButton[maxPlayers];
		btnPlayerCol = new JButton[maxPlayers];
		lblPlayerCol = new JLabel[maxPlayers];
		for (int i = 0; i < maxPlayers; i++) {
			btnPlayer[i] = new JButton(prop.getProperty("player" + (i + 1) + "Name"));
			btnPlayer[i].setHorizontalAlignment(SwingConstants.LEFT);
			btnPlayerCol[i] = new JButton();
			lblPlayerCol[i] = new JLabel(" ");
		}
		gridContainer = new JPanel();
		gridBag = new GridBagLayout();
		txtSize = new JTextField[4];
		pnlSize = new JPanel();
	}

	private final void chooseColor(final int i) {
		final Color c = JColorChooser.showDialog(this, RaceGame.NAME, lblPlayerCol[i].getBackground());
		if (c == null)
			return;
		lblPlayerCol[i].setBackground(c);
		prop.put("player" + (i + 1) + "Color", c.getRed() + " " + c.getGreen() + " " + c.getBlue());
		repaint();
	}

	private final void chooseName(final int i) {
		boolean notFirstRun = false;
		String s, sTemp;
		do {
			if (notFirstRun)
				JOptionPane.showMessageDialog(this, "Not a valid name.", RaceGame.NAME, JOptionPane.OK_OPTION);
			try {
				sTemp = prop.getProperty("player" + (i + 1) + "Name");
			} catch (final Exception e) {
				sTemp = "Player " + (i + 1);
			}
			s = JOptionPane.showInputDialog(this, "Enter a name for Player " + (i + 1), sTemp);
			notFirstRun = true;
		} while (s == null);
		btnPlayer[i].setText(s);
		prop.put("player" + (i + 1) + "Name", s);
	}

	@Override
	public boolean isActive() {
		return isActive;
	}

	private final void minusPlayer() {
		nPlayers = Math.max(nPlayers - 1, 1);
		prop.put("nPlayers", String.valueOf(nPlayers));
		setupGridBag();
	}

	private final void plusPlayer() {
		nPlayers = Math.min(nPlayers + 1, maxPlayers);
		prop.put("nPlayers", String.valueOf(nPlayers));
		setupGridBag();
	}

	private final void refreshSizeValues() {
		String propName = null;
		for (int i = 0; i < 4; i++) {
			if (i == 0)
				propName = "windowX";
			else if (i == 1)
				propName = "windowY";
			else if (i == 2)
				propName = "gameX";
			else if (i == 3)
				propName = "gameY";
			try {
				Integer.valueOf(txtSize[i].getText());
			} catch (final Exception e) {
				txtSize[i].setText(prop.getProperty(propName));
			}
			prop.put(propName, txtSize[i].getText());
		}
	}

	/**
	 * Redraw the buttons for players
	 */
	private final void setupGridBag() {
		gridContainer.removeAll();

		final GridBagConstraints c = new GridBagConstraints();
		c.fill = GridBagConstraints.BOTH;

		Component fill;
		int i;
		for (i = 0; i < nPlayers; i++) {
			c.weightx = 4.0;
			c.gridwidth = 1;
			gridBag.setConstraints(btnPlayer[i], c);
			gridContainer.add(btnPlayer[i]);
			fill = Box.createRigidArea(new Dimension(5, 0));
			c.gridwidth = 1;
			c.weightx = 0.1;
			gridBag.setConstraints(fill, c);
			gridContainer.add(fill);
			c.weightx = 1.0;
			c.gridwidth = GridBagConstraints.REMAINDER;
			gridBag.setConstraints(btnPlayerCol[i], c);
			gridContainer.add(btnPlayerCol[i]);
			fill = Box.createRigidArea(new Dimension(0, 5));
			gridBag.setConstraints(fill, c);
			gridContainer.add(fill);
		}

		gridBag.setConstraints(pnlSize, c);
		gridContainer.add(pnlSize);

		validate();
		repaint();
	}

	public void setupUI() {
		final StartDialog me = this;
		int i;
		setSize(400, 400);
		setLocationRelativeTo(null);
		setResizable(false);
		setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);

		setLayout(new BorderLayout());
		final JPanel southContainer = new JPanel();

		final JLabel[] lblSize = new JLabel[4];
		lblSize[0] = new JLabel("Window X:");
		lblSize[1] = new JLabel("Window Y:");
		lblSize[2] = new JLabel("Game X:");
		lblSize[3] = new JLabel("Game Y:");
		txtSize[0] = new JTextField(defTextFiller);
		txtSize[1] = new JTextField(defTextFiller);
		txtSize[2] = new JTextField(defTextFiller);
		txtSize[3] = new JTextField(defTextFiller);

		pnlSize.setLayout(new GridLayout(2, 4, 10, 5));
		for (i = 0; i < 4; i++) {
			pnlSize.add(lblSize[i]);
			pnlSize.add(txtSize[i]);
		}

		gridContainer.setLayout(gridBag);
		gridContainer.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
		setupGridBag();
		for (i = 0; i < maxPlayers; i++) {
			final Scanner sc = new Scanner(prop.getProperty("player" + (i + 1) + "Color"));
			lblPlayerCol[i].setBackground(new Color(sc.nextInt(), sc.nextInt(), sc.nextInt()));
			btnPlayerCol[i].add(lblPlayerCol[i]);
			lblPlayerCol[i].setOpaque(true);
			btnPlayerCol[i].setLayout(new GridLayout(1, 1));
			sc.close();
		}

		southContainer.setLayout(new BoxLayout(southContainer, BoxLayout.X_AXIS));
		southContainer.setBorder(BorderFactory.createEmptyBorder(0, 10, 10, 10));
		southContainer.add(Box.createHorizontalGlue());
		southContainer.add(btnMinus);
		southContainer.add(btnPlus);
		southContainer.add(Box.createHorizontalGlue());
		southContainer.add(btnExit);
		southContainer.add(btnOK);

		add(gridContainer, BorderLayout.CENTER);
		add(southContainer, BorderLayout.SOUTH);

		setVisible(true);

		txtSize[0].setText(prop.getProperty("windowX"));
		txtSize[1].setText(prop.getProperty("windowY"));
		txtSize[2].setText(prop.getProperty("gameX"));
		txtSize[3].setText(prop.getProperty("gameY"));

		final ActionListener btnListener = arg0 -> {
			final Object source = arg0.getSource();
			if (source == btnPlus)
				me.plusPlayer();
			else if (source == btnMinus)
				me.minusPlayer();
			else if (source == btnOK) {
				refreshSizeValues();
				isActive = false;
				me.dispose();
			} else if (source == btnExit)
				System.exit(0);
			else
				for (int i1 = 0; i1 < nPlayers; i1++)
					if (source == btnPlayer[i1])
						chooseName(i1);
					else if (source == btnPlayerCol[i1])
						chooseColor(i1);
		};

		btnPlus.addActionListener(btnListener);
		btnMinus.addActionListener(btnListener);
		btnOK.addActionListener(btnListener);
		btnExit.addActionListener(btnListener);
		for (i = 0; i < maxPlayers; i++) {
			btnPlayer[i].addActionListener(btnListener);
			btnPlayerCol[i].addActionListener(btnListener);
		}
	}
}
