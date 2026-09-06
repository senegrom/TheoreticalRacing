package tr.logic;

import java.awt.geom.PathIterator;
import java.io.IOException;
import java.io.StringReader;
import java.lang.reflect.Field;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import tr.browser.Json;
import tr.browser.JOptionPane;
import tr.browser.SwingUtilities;
import tr.gui.GameUI;
import tr.gui.RaceUI;

/**
 * Transport/presentation adapter only. All actions enter RaceGame's existing
 * public UI methods; all move previews use its side-effect-free live referee.
 * No physics, turn ordering, placement RNG or AI policy is implemented here.
 */
public final class BrowserBridge {
    private RaceGame game;
    private GameUI ui;
    private RaceUI scene;
    private int selected = -1;
    private java.awt.geom.Area shownArea;
    private List<double[]> shownShape = List.of();
    private final Map<Integer, String> outcomes = new LinkedHashMap<>();
    private int scannedLogLength;
    private void readOutcomes() {
        final StringBuilder log = (StringBuilder) field("gameLog");
        if (log.length() < scannedLogLength) { outcomes.clear(); scannedLogLength = 0; }
        // Records are append-only between undo operations. Names are never parsed.
        if (log.length() != scannedLogLength) {
            for (final String line : log.substring(scannedLogLength).split("\n")) {
                final String[] words = line.split(" ");
                if (words.length > 3 && words[0].matches("[0-9]+") && words[1].matches("p[1-9]")) {
                    for (final String outcome : new String[]{"CRASH", "FINISH", "TIMEOUT"}) {
                        if (line.contains(" " + outcome + " place="))
                            outcomes.put(Integer.parseInt(words[1].substring(1)), outcome);
                    }
                }
            }
            scannedLogLength = log.length();
        }
    }
    private static final Map<String, Field> FIELDS = new LinkedHashMap<>();

    private Object field(final String name) {
        try {
            Field f = FIELDS.get(name);
            if (f == null) {
                f = RaceGame.class.getDeclaredField(name);
                f.setAccessible(true);
                FIELDS.put(name, f);
            }
            return f.get(game);
        } catch (final ReflectiveOperationException ex) {
            throw new IllegalStateException("Engine API changed: " + name, ex);
        }
    }

    public String create(final String track, final String configuration, final String seed) throws IOException {
        // One JVM/iframe per session. Refuse to orphan a live reachability worker.
        if (game != null) throw new IllegalStateException("Create a fresh engine for a new race");
        if (configuration.length() > 100_000) throw new IllegalArgumentException("Configuration is too large");
        final Properties props = new Properties();
        props.load(new StringReader(configuration));
        props.setProperty("maxPlayers", "9");
        if (!track.isEmpty()) {
            if (!TrackIO.loadTrack(props, track)) throw new IllegalArgumentException("Cannot load track: " + track);
        } else {
            props.setProperty("useLastTrack", "false");
            props.setProperty("lapClosable", "false");
            props.remove("lastTrackLeft");
            props.remove("lastTrackRight");
        }
        SwingUtilities.clear();
        JOptionPane.drain();
        game = new RaceGame(props);
        if (!seed.isBlank()) game.setStartSeed(Long.parseLong(seed));
        final Path home = Path.of(System.getProperty("user.home"), "theoretical-racing");
        game.setGameLogPath(home.resolve("last_game.log").toString());
        game.setPropertiesPath(home.resolve("user.properties").toString());
        game.start();
        ui = (GameUI) field("gameFrame");
        scene = (RaceUI) field("rui");
        return snapshot();
    }

    private GameState phase() { return (GameState) field("gamestate"); }
    public String tick() {
        requireGame();
        // The real Java background worker does the work, unchanged. Never block
        // the browser transport by joining it, and never substitute a weaker AI.
        if (game.trackA == null || game.reach.isReady()) SwingUtilities.tick();
        return snapshot();
    }
    public String click(final int x, final int y) {
        requireGame();
        if (x < 0 || y < 0 || x > game.gameCols || y > game.gameRows)
            throw new IllegalArgumentException("Click is outside the grid");
        game.clickedGrid(x, y);
        return snapshot();
    }
    public String ok() {
        requireGame();
        game.clickedOK();
        return snapshot();
    }
    public String undo() {
        requireGame();
        // Match the enabled desktop control; a queued AI reply must not race Undo.
        if (phase() == GameState.DRAWTRACK || ui.undoEnabled) {
            game.clickedUndo();
            selected = -1;
        }
        return snapshot();
    }
    public String preview(final int index) {
        requireHumanTurn();
        if (index < 0 || index >= 9) throw new IllegalArgumentException("Invalid direction");
        // A repeated UI preview must not commit the engine's double-click action.
        if ((Integer) field("isShowingPrePath") != index) game.clickedDirection(Direction.fromIndex(index));
        selected = index;
        return snapshot();
    }
    public String move(final int index, final boolean crashConfirmed) {
        requireHumanTurn();
        if (index < 0 || index >= 9) throw new IllegalArgumentException("Invalid direction");
        if ((Integer) field("isShowingPrePath") != index) game.clickedDirection(Direction.fromIndex(index));
        final int before = (Integer) field("turnCounter");
        JOptionPane.confirmCrash(crashConfirmed);
        try { game.clickedDirection(Direction.fromIndex(index)); }
        finally { JOptionPane.confirmCrash(false); }
        if ((Integer) field("turnCounter") != before) selected = -1;
        return snapshot();
    }
    public String log() { requireGame(); return field("gameLog").toString(); }
    public void awaitReady() { requireGame(); game.reach.ensureReachabilityReady(); }
    private void requireGame() {
        if (game == null) throw new IllegalStateException("No race has been created");
    }
    private void requireHumanTurn() {
        requireGame();
        if (phase() != GameState.PLAY || game.players[game.subgamestate].isAi())
            throw new IllegalStateException("It is not a human turn");
    }
    public String snapshot() {
        requireGame();
        final GameState phase = phase();
        final Map<String, Object> out = new LinkedHashMap<>();
        out.put("phase", phase.name());
        out.put("status", ui.status);
        out.put("cols", game.gameCols); out.put("rows", game.gameRows);
        out.put("current", game.subgamestate); out.put("turn", field("turnCounter"));
        out.put("laps", game.totalLaps); out.put("selected", selected);
        out.put("ok", ui.okEnabled); out.put("undo", ui.undoEnabled);
        out.put("ready", game.trackA == null || game.reach.isReady());
        if (game.track != null && game.reach.isReady()) {
            try { game.reach.ensureReachabilityReady(); }
            catch (final RuntimeException | Error error) { out.put("failure", error.toString()); }
        }
        out.put("messages", JOptionPane.drain());
        out.put("left", game.track == null ? List.of() : game.track.getLeft());
        out.put("right", game.track == null ? List.of() : game.track.getRight());
        out.put("startZone", scene.startZone); out.put("checkpoints", scene.checkpoints);
        out.put("closures", scene.closures);
        out.put("finish", scene.finishLine == null ? null : new double[][]{
                {scene.finishLine.getX1(), scene.finishLine.getY1()},
                {scene.finishLine.getX2(), scene.finishLine.getY2()}});
        out.put("prePath", scene.prePath);
        // Export the actual Java Area once per geometry, including tolerance and
        // multi-lap closures. Canvas is only a renderer, never a geometry oracle.
        if (game.trackA != null && shownArea != game.trackA) {
            final List<double[]> shape = new ArrayList<>();
            final PathIterator it = game.trackA.getPathIterator(null, 0.1);
            final double[] coords = new double[6];
            while (!it.isDone()) {
                final int kind = it.currentSegment(coords);
                shape.add(kind == PathIterator.SEG_CLOSE ? new double[]{kind}
                        : new double[]{kind, coords[0], coords[1]});
                it.next();
            }
            shownArea = game.trackA;
            shownShape = shape;
        }
        out.put("shape", shownShape);
        readOutcomes();
        final List<Object> players = new ArrayList<>();
        for (final Player p : game.players) {
            final Map<String, Object> item = new LinkedHashMap<>();
            item.put("name", p.getName()); item.put("number", p.getNumber());
            item.put("kind", p.getKind().name()); item.put("position", p.getPosition());
            item.put("velocity", p.getVelocity()); item.put("place", p.getFinishedPlace());
            item.put("outcome", outcomes.getOrDefault(p.getNumber(), ""));
            item.put("lap", p.getLap()); item.put("nextGate", p.getNextGate());
            item.put("traceStart", p.getTraceStart()); item.put("history", p.getHistory());
            item.put("color", String.format("#%02x%02x%02x", p.getColor().getRed(), p.getColor().getGreen(), p.getColor().getBlue()));
            players.add(item);
        }
        out.put("players", players);
        final List<Object> moves = new ArrayList<>();
        if (phase == GameState.PLAY) {
            final Player player = game.players[game.subgamestate];
            if (!player.isAi()) {
                for (final Direction d : Direction.values()) {
                    final int[] pos = player.getPosition(), vel = player.getVelocity();
                    final int[] nextVel = {vel[0] + d.dx, vel[1] + d.dy};
                    final int[] end = {pos[0] + nextVel[0], pos[1] + nextVel[1]};
                    final RaceGame.MoveResult result = game.evaluateMove(player, pos, end);
                    moves.add(Map.of("index", d.ordinal(), "position", end, "velocity", nextVel,
                            "legal", result.legal(), "finishes", result.finishes(),
                            "lap", result.lapCross(), "timeout", game.raceTurnLimitReached()));
                }
            }
        }
        out.put("moves", moves);
        final List<int[]> starts = new ArrayList<>();
        if (phase == GameState.PLACEPLAYERS && game.subgamestate < game.players.length) {
            for (int x = 0; x <= game.gameCols; x++) for (int y = 0; y <= game.gameRows; y++) {
                if (game.startZoneA.contains(x, y) && !game.isCrashingPlayer(x, y, game.players[game.subgamestate].getNumber()))
                    starts.add(new int[]{x, y});
            }
        }
        out.put("starts", starts);
        return Json.encode(out);
    }

    /** Java-side catalogue uses the original parser, never a second .track parser. */
    public static String catalogue() {
        final List<Object> tracks = new ArrayList<>();
        for (final String id : TrackIO.listTracks()) {
            final TrackIO.TrackData t = TrackIO.loadTrackData(id);
            if (t == null) throw new IllegalStateException("Invalid bundled track " + id);
            tracks.add(Map.of("id", id, "name", t.name(), "cols", t.gameX(), "rows", t.gameY(),
                    "left", t.left(), "right", t.right(), "lapClosable", TrackIO.trackDeclaresClosable(id)));
        }
        return Json.encode(tracks);
    }

    /** Dependency-free development harness and differential-test transport. */
    public static void main(final String[] args) throws Exception {
        if (args.length == 1 && args[0].equals("catalogue")) { System.out.println(catalogue()); return; }
        if (args.length < 5) throw new IllegalArgumentException("track players laps seed output-log [kind]");
        final int count = Integer.parseInt(args[1]);
        final String kind = args.length > 5 ? args[5] : "AI2";
        final StringBuilder config = new StringBuilder("nPlayers=" + count + "\nlaps=" + args[2] + "\n");
        for (int i = 1; i <= count; i++) config.append("player").append(i).append("Kind=").append(kind.split(",")[(i - 1) % kind.split(",").length])
                .append("\nplayer").append(i).append("Name=").append((char) ('A' + i - 1)).append('\n');
        final BrowserBridge bridge = new BrowserBridge();
        bridge.create(args[0], config.toString(), args[3]);
        bridge.awaitReady();
        bridge.ok();
        int steps = 0;
        while (bridge.phase() != GameState.FINISHED) {
            SwingUtilities.tick();
            if (++steps > 100_000) throw new IllegalStateException("Race did not terminate");
        }
        java.nio.file.Files.writeString(Path.of(args[4]), bridge.log());
    }
}
