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
import java.util.List;
import java.util.Properties;
import java.util.Scanner;
import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JButton;
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
import tr.logic.TrackIO;
import tr.logic.TrackIO.TrackData;

/**
 * Start dialog: name/colour/AI per player, dimensions, track chooser, then go.
 *
 * @author CGH
 */
public final class StartDialog extends JFrame {
	private final static String	defTextFiller		= "00000";
	private static final long	serialVersionUID	= -5996002806608660877L;

	private static final String	TRACK_DRAW_NEW		= "<Draw new>";
	private static final String	TRACK_LAST			= "<Last>";

	private final JButton				btnExit;
	private final JButton				btnMinus;
	private final JButton				btnOK;
	private final JButton[]				btnPlayer;
	private final JButton[]				btnPlayerCol;
	private final JComboBox<String>[]	cmbKind;
	private final JButton				btnPlus;
	private final JComboBox<String>		cmbTrack;
	private final TrackPreviewPanel		previewPanel;
	private final GridBagLayout			gridBag;
	private final JPanel				gridContainer;
	private final JLabel[]				lblPlayerCol;
	private final int					maxPlayers;
	private int							nPlayers;
	private final JPanel				pnlSize;
	private final Properties			prop;
	private final JTextField[]			txtSize;

	private transient Runnable			onConfirm, onCancel, onSave;

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
		final JComboBox<String>[] cmbs = (JComboBox<String>[]) new JComboBox<?>[maxPlayers];
		cmbKind = cmbs;
		lblPlayerCol = new JLabel[maxPlayers];
		for (int i = 0; i < maxPlayers; i++) {
			btnPlayer[i] = new JButton(prop.getProperty("player" + (i + 1) + "Name"));
			btnPlayer[i].setHorizontalAlignment(SwingConstants.LEFT);
			btnPlayerCol[i] = new JButton();
			cmbKind[i] = new JComboBox<>(new String[]{"Human", "AI1", "AI2" });
			final Player.Kind kind = Player.Kind.parse(prop.getProperty("player" + (i + 1) + "Kind"));
			cmbKind[i].setSelectedItem(kind == Player.Kind.HUMAN ? "Human" : kind.name());
			lblPlayerCol[i] = new JLabel(" ");
		}
		gridContainer = new JPanel();
		gridBag = new GridBagLayout();
		txtSize = new JTextField[4];
		pnlSize = new JPanel();
		cmbTrack = new JComboBox<>();
		previewPanel = new TrackPreviewPanel();
		populateTrackCombo();
	}

	private void populateTrackCombo() {
		cmbTrack.removeAllItems();
		cmbTrack.addItem(TRACK_DRAW_NEW);
		final boolean hasLastTrack = TrackIO.hasLastTrack(prop);
		if (hasLastTrack)
			cmbTrack.addItem(TRACK_LAST);
		final List<String> names = TrackIO.listTracks();
		for (final String n : names)
			cmbTrack.addItem(n);

		final boolean useLast = Boolean.parseBoolean(prop.getProperty("useLastTrack", "false")) && hasLastTrack;
		if (useLast)
			cmbTrack.setSelectedItem(TRACK_LAST);
		else
			cmbTrack.setSelectedItem(TRACK_DRAW_NEW);
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

	/** Settings that Cancel keeps too: closing the dialog should not discard a
	 *  kind the user changed, but it must not commit a track either -- browsing
	 *  the combo to look at a circuit is not choosing it. */
	private void commitPlayerKinds() {
		for (int i = 0; i < maxPlayers; i++) {
			final String sel = String.valueOf(cmbKind[i].getSelectedItem());
			prop.put("player" + (i + 1) + "Kind", "Human".equals(sel) ? "HUMAN" : sel);
		}
	}

	/** Confirm only: loading a track rewrites the stored track, the grid size
	 *  and lapClosable, so it must follow an actual OK. */
	private void commitTrackSelection() {
		final String trackSel = (String) cmbTrack.getSelectedItem();
		if (trackSel == null || TRACK_DRAW_NEW.equals(trackSel)) {
			prop.put("useLastTrack", "false");
			// lapClosable describes the LOADED track. A track about to be drawn
			// has declared nothing, and inheriting a real circuit's waiver would
			// skip the loop-closure clamp on an open drawing.
			prop.put("lapClosable", "false");
		} else if (TRACK_LAST.equals(trackSel)) {
			prop.put("useLastTrack", "true");
		} else if (!TrackIO.loadTrack(prop, trackSel)) {
			prop.put("useLastTrack", "false");
		}
	}

	private void updateTrackPreview() {
		final String sel = (String) cmbTrack.getSelectedItem();
		if (sel == null || TRACK_DRAW_NEW.equals(sel)) {
			previewPanel.clearTrack("Draw a new track");
			return;
		}
		final TrackData td;
		if (TRACK_LAST.equals(sel))
			td = TrackIO.loadLastTrackData(prop);
		else
			td = TrackIO.loadTrackData(sel);
		if (td == null)
			previewPanel.clearTrack("Track unavailable");
		else
			previewPanel.setTrack(td.gameX(), td.gameY(), td.left(), td.right(), td.name());
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
		setSize(820, 480);
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

		final JPanel trackPanel = new JPanel(new BorderLayout(6, 6));
		trackPanel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
		final JPanel trackHeader = new JPanel(new BorderLayout(6, 0));
		trackHeader.add(new JLabel("Track:"), BorderLayout.WEST);
		trackHeader.add(cmbTrack, BorderLayout.CENTER);
		trackPanel.add(trackHeader, BorderLayout.NORTH);
		previewPanel.setPreferredSize(new Dimension(280, 200));
		previewPanel.setBorder(BorderFactory.createLineBorder(new Color(180, 180, 180)));
		trackPanel.add(previewPanel, BorderLayout.CENTER);

		southContainer.setLayout(new BoxLayout(southContainer, BoxLayout.X_AXIS));
		southContainer.setBorder(BorderFactory.createEmptyBorder(0, 10, 10, 10));
		southContainer.add(Box.createHorizontalGlue());
		southContainer.add(btnMinus);
		southContainer.add(btnPlus);
		southContainer.add(Box.createHorizontalGlue());
		southContainer.add(btnExit);
		southContainer.add(btnOK);

		add(gridContainer, BorderLayout.CENTER);
		add(trackPanel, BorderLayout.EAST);
		add(southContainer, BorderLayout.SOUTH);

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

		cmbTrack.addActionListener(e -> updateTrackPreview());
		updateTrackPreview();

		setVisible(true);
		// Same foreground nudge as the game frame: launched from a terminal,
		// the dialog otherwise opens behind it.
		toFront();
		requestFocus();
	}

	private void doConfirm() {
		refreshSizeValues();
		commitPlayerKinds();
		commitTrackSelection();
		dispose();
		if (onSave != null)
			onSave.run();
		if (onConfirm != null)
			onConfirm.run();
	}

	private void doCancel() {
		refreshSizeValues();
		commitPlayerKinds();
		dispose();
		if (onCancel != null)
			onCancel.run();
	}
}
