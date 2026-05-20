package tr.gui;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.Dimension;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.event.ActionListener;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.util.Properties;
import java.util.Scanner;
import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JColorChooser;
import javax.swing.JComboBox;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JTextField;
import javax.swing.SwingConstants;
import javax.swing.WindowConstants;
import tr.logic.Player;
import tr.logic.RaceGame;

/**
 * Start dialog: name/colour/AI per player, dimensions, then go.
 *
 * @author CGH
 */
public class StartDialog extends JFrame {
	private final static String	defTextFiller		= "00000";
	private static final long	serialVersionUID	= -5996002806608660877L;

	private final JButton		btnExit;
	private final JButton		btnMinus;
	private final JButton		btnOK;
	private final JButton[]			btnPlayer;
	private final JButton[]			btnPlayerCol;
	private final JComboBox<String>[]	cmbKind;
	private final JButton			btnPlus;
	private final JCheckBox			chkUseLastTrack;
	private final GridBagLayout	gridBag;
	private final JPanel		gridContainer;
	private final JLabel[]		lblPlayerCol;
	private final int			maxPlayers;
	private int					nPlayers;
	private final JPanel		pnlSize;
	private final Properties	prop;
	private final JTextField[]	txtSize;

	private Runnable			onConfirm, onCancel, onSave;

	public StartDialog(final String title, final Properties prop) {
		super(title);
		this.prop = prop;
		maxPlayers = Integer.parseInt(prop.getProperty("maxPlayers"));
		nPlayers = Integer.parseInt(prop.getProperty("nPlayers"));
		btnOK = new JButton("OK");
		btnExit = new JButton("Exit");
		btnPlus = new JButton("+");
		btnMinus = new JButton("-");
		btnPlayer = new JButton[maxPlayers];
		btnPlayerCol = new JButton[maxPlayers];
		@SuppressWarnings("unchecked")
		final JComboBox<String>[] cmbs = new JComboBox[maxPlayers];
		cmbKind = cmbs;
		lblPlayerCol = new JLabel[maxPlayers];
		for (int i = 0; i < maxPlayers; i++) {
			btnPlayer[i] = new JButton(prop.getProperty("player" + (i + 1) + "Name"));
			btnPlayer[i].setHorizontalAlignment(SwingConstants.LEFT);
			btnPlayerCol[i] = new JButton();
			cmbKind[i] = new JComboBox<>(new String[]{"Human", "AI1", "AI2" });
			cmbKind[i].setSelectedItem(Player.Kind.parse(prop.getProperty("player" + (i + 1) + "Kind")).name().equals("HUMAN") ? "Human"
					: Player.Kind.parse(prop.getProperty("player" + (i + 1) + "Kind")).name());
			lblPlayerCol[i] = new JLabel(" ");
		}
		gridContainer = new JPanel();
		gridBag = new GridBagLayout();
		txtSize = new JTextField[4];
		pnlSize = new JPanel();
		chkUseLastTrack = new JCheckBox("Use last track", Boolean.parseBoolean(prop.getProperty("useLastTrack", "false")));
		chkUseLastTrack.setEnabled(RaceGame.hasLastTrack(prop));
		if (!RaceGame.hasLastTrack(prop))
			chkUseLastTrack.setSelected(false);
	}

	public void setOnConfirm(final Runnable r) {
		onConfirm = r;
	}

	public void setOnCancel(final Runnable r) {
		onCancel = r;
	}

	public void setOnSave(final Runnable r) {
		onSave = r;
	}

	private void chooseColor(final int i) {
		final Color c = JColorChooser.showDialog(this, RaceGame.NAME, lblPlayerCol[i].getBackground());
		if (c == null)
			return;
		lblPlayerCol[i].setBackground(c);
		prop.put("player" + (i + 1) + "Color", c.getRed() + " " + c.getGreen() + " " + c.getBlue());
		repaint();
	}

	private void chooseName(final int i) {
		final String sTemp = prop.getProperty("player" + (i + 1) + "Name", "Player " + (i + 1));
		final String s = JOptionPane.showInputDialog(this, "Enter a name for Player " + (i + 1), sTemp);
		if (s == null || s.isEmpty())
			return;
		btnPlayer[i].setText(s);
		prop.put("player" + (i + 1) + "Name", s);
	}

	private void minusPlayer() {
		nPlayers = Math.max(nPlayers - 1, 1);
		prop.put("nPlayers", String.valueOf(nPlayers));
		setupGridBag();
	}

	private void plusPlayer() {
		nPlayers = Math.min(nPlayers + 1, maxPlayers);
		prop.put("nPlayers", String.valueOf(nPlayers));
		setupGridBag();
	}

	private void refreshSizeValues() {
		final String[] propNames = {"windowX", "windowY", "gameX", "gameY" };
		final int[] mins = {200, 200, 2, 2 };
		final int[] maxs = {10000, 10000, 500, 500 };
		for (int i = 0; i < 4; i++) {
			int val;
			try {
				val = Integer.parseInt(txtSize[i].getText());
				if (val < mins[i] || val > maxs[i])
					throw new NumberFormatException();
			} catch (final NumberFormatException e) {
				txtSize[i].setText(prop.getProperty(propNames[i]));
				continue;
			}
			prop.put(propNames[i], String.valueOf(val));
		}
	}

	private void commitKindSelections() {
		for (int i = 0; i < maxPlayers; i++) {
			final String sel = String.valueOf(cmbKind[i].getSelectedItem());
			prop.put("player" + (i + 1) + "Kind", "Human".equals(sel) ? "HUMAN" : sel);
		}
		prop.put("useLastTrack", String.valueOf(chkUseLastTrack.isSelected()));
	}

	/** Redraw the player rows. */
	private void setupGridBag() {
		gridContainer.removeAll();

		final GridBagConstraints c = new GridBagConstraints();
		c.fill = GridBagConstraints.BOTH;

		for (int i = 0; i < nPlayers; i++) {
			c.weightx = 4.0;
			c.gridwidth = 1;
			gridBag.setConstraints(btnPlayer[i], c);
			gridContainer.add(btnPlayer[i]);
			Component fill = Box.createRigidArea(new Dimension(5, 0));
			c.gridwidth = 1;
			c.weightx = 0.1;
			gridBag.setConstraints(fill, c);
			gridContainer.add(fill);
			c.weightx = 1.0;
			c.gridwidth = 1;
			gridBag.setConstraints(btnPlayerCol[i], c);
			gridContainer.add(btnPlayerCol[i]);
			fill = Box.createRigidArea(new Dimension(5, 0));
			c.gridwidth = 1;
			gridBag.setConstraints(fill, c);
			gridContainer.add(fill);
			c.weightx = 0.8;
			c.gridwidth = GridBagConstraints.REMAINDER;
			gridBag.setConstraints(cmbKind[i], c);
			gridContainer.add(cmbKind[i]);
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
		setSize(500, 450);
		setLocationRelativeTo(null);
		setResizable(false);
		setDefaultCloseOperation(WindowConstants.DISPOSE_ON_CLOSE);

		setLayout(new BorderLayout());
		final JPanel southContainer = new JPanel();

		final JLabel[] lblSize = new JLabel[4];
		lblSize[0] = new JLabel("Window X:");
		lblSize[1] = new JLabel("Window Y:");
		lblSize[2] = new JLabel("Game X:");
		lblSize[3] = new JLabel("Game Y:");
		for (int i = 0; i < 4; i++)
			txtSize[i] = new JTextField(defTextFiller);

		pnlSize.setLayout(new GridLayout(2, 4, 10, 5));
		for (int i = 0; i < 4; i++) {
			pnlSize.add(lblSize[i]);
			pnlSize.add(txtSize[i]);
		}

		gridContainer.setLayout(gridBag);
		gridContainer.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
		setupGridBag();
		for (int i = 0; i < maxPlayers; i++) {
			try (Scanner sc = new Scanner(prop.getProperty("player" + (i + 1) + "Color"))) {
				lblPlayerCol[i].setBackground(new Color(sc.nextInt(), sc.nextInt(), sc.nextInt()));
			}
			btnPlayerCol[i].add(lblPlayerCol[i]);
			lblPlayerCol[i].setOpaque(true);
			btnPlayerCol[i].setLayout(new GridLayout(1, 1));
		}

		southContainer.setLayout(new BoxLayout(southContainer, BoxLayout.X_AXIS));
		southContainer.setBorder(BorderFactory.createEmptyBorder(0, 10, 10, 10));
		southContainer.add(chkUseLastTrack);
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

		addWindowListener(new WindowAdapter() {
			@Override
			public void windowClosing(final WindowEvent e) {
				doCancel();
			}
		});

		final ActionListener btnListener = arg0 -> {
			final Object source = arg0.getSource();
			if (source == btnPlus)
				plusPlayer();
			else if (source == btnMinus)
				minusPlayer();
			else if (source == btnOK)
				doConfirm();
			else if (source == btnExit)
				doCancel();
			else
				for (int i = 0; i < nPlayers; i++)
					if (source == btnPlayer[i])
						chooseName(i);
					else if (source == btnPlayerCol[i])
						chooseColor(i);
		};

		btnPlus.addActionListener(btnListener);
		btnMinus.addActionListener(btnListener);
		btnOK.addActionListener(btnListener);
		btnExit.addActionListener(btnListener);
		for (int i = 0; i < maxPlayers; i++) {
			btnPlayer[i].addActionListener(btnListener);
			btnPlayerCol[i].addActionListener(btnListener);
		}
	}

	private void doConfirm() {
		refreshSizeValues();
		commitKindSelections();
		dispose();
		if (onSave != null)
			onSave.run();
		if (onConfirm != null)
			onConfirm.run();
	}

	private void doCancel() {
		refreshSizeValues();
		commitKindSelections();
		dispose();
		if (onCancel != null)
			onCancel.run();
	}
}
