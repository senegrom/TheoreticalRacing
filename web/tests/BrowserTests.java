package tr.logic;

import java.lang.reflect.Field;
import java.util.Arrays;

/** Exercise the same UI commands that the browser sends, without a JS mock. */
public final class BrowserTests {
    private BrowserTests() {}
    private static Object get(final Object object, final String name) throws Exception {
        final Field f = object.getClass().getDeclaredField(name);
        f.setAccessible(true);
        return f.get(object);
    }
    private static void check(final boolean value, final String message) {
        if (!value) throw new AssertionError(message);
    }
    public static void main(final String[] args) throws Exception {
        ReviewRuleTests.run();
        FollowupRuleTests.run();
        StartPlacementTests.run();
        final BrowserBridge b = new BrowserBridge();
        final String created = b.create("hairpin", "nPlayers=2\nplayer1Kind=HUMAN\nplayer2Kind=AI1\nlaps=1\n", "1");
        check(created.contains("\"_snapshot\":\"full\"") && created.contains("\"shape\":"),
                "initial browser state is not a complete resynchronization");
        final RaceGame g = (RaceGame) get(b, "game");
        b.awaitReady();
        check(b.snapshot().contains("\"undo\":false"), "placement undo enabled before any human placement");
        int[] start = null;
        outer: for (int x = 0; x <= g.gameCols; x++) for (int y = 0; y <= g.gameRows; y++) {
            if (g.startZoneA.contains(x, y)) { start = new int[]{x, y}; break outer; }
        }
        check(start != null, "human start missing");
        b.click(start[0], start[1]);
        check(g.players[1].getPosition()[0] != Player.INIT_POS, "AI not auto-placed after human");
        check(b.snapshot().contains("\"undo\":true"), "bundled-track human placement cannot be undone through the UI");
        b.undo();
        check(g.subgamestate == 0 && g.players[0].getPosition()[0] == Player.INIT_POS
                && g.players[1].getPosition()[0] == Player.INIT_POS,
                "browser placement undo did not remove the human and dependent AI placements");
        check(b.snapshot().contains("\"undo\":false"), "placement undo stayed enabled after restoring the first turn");
        b.click(start[0], start[1]);
        b.ok();
        final String originalLog = b.log();
        final int[][] originalPositions = {g.players[0].getPosition().clone(), g.players[1].getPosition().clone()};
        Direction legal = null;
        for (final Direction d : Direction.values()) {
            if (d != Direction.NONE && g.evaluateMove(g.players[0], start, new int[]{start[0] + d.dx, start[1] + d.dy}).legal()) { legal = d; break; }
        }
        check(legal != null, "no legal first move");
        final String previewDelta = b.preview(legal.ordinal());
        check(previewDelta.contains("\"_snapshot\":\"delta\"") && !previewDelta.contains("\"shape\":"),
                "unchanged geometry was resent in a normal action delta");
        b.preview(legal.ordinal());
        check(Arrays.equals(g.players[0].getPosition(), start), "repeated preview moved the car");
        check(originalLog.equals(b.log()), "preview changed race log");
        b.move(legal.ordinal(), false);
        check(!Arrays.equals(g.players[0].getPosition(), start), "confirm did not execute move");
        final int beforeReply = g.turnCount();
        b.tick();
        check(g.turnCount() == beforeReply + 1, "first Step consumed a viewport callback instead of an AI move");
        check(!g.players[g.subgamestate].isAi(), "one Step did not return the human turn");
        b.tick();
        check(g.turnCount() == beforeReply + 1, "idle Step advanced a human turn");
        final String undoDelta = b.undo();
        check(undoDelta.contains("\"history\":"), "undo did not send a history replacement delta");
        final String resync = b.snapshot();
        check(resync.contains("\"_snapshot\":\"full\"") && resync.contains("\"shape\":"),
                "explicit snapshot did not provide a full resynchronization");
        check(Arrays.deepEquals(originalPositions, new int[][]{g.players[0].getPosition(), g.players[1].getPosition()}), "undo failed to restore the complete field");
        check(originalLog.equals(b.log()), "undo failed to restore original log");
        check(g.players[0].getHistory().size() == 1 && g.players[1].getHistory().size() == 1, "undo retained replies in histories");
        try { b.preview(9); throw new AssertionError("invalid direction accepted"); }
        catch (final IllegalArgumentException expected) { /* Expected. */ }
        try { b.click(-1, 0); throw new AssertionError("off-grid click accepted"); }
        catch (final IllegalArgumentException expected) { /* Expected. */ }
        try { b.create("hairpin", "", ""); throw new AssertionError("second live engine accepted"); }
        catch (final IllegalStateException expected) { /* Expected. */ }
        // Deliberately place the test car outside the corridor to test the crash
        // consent transport, leaving the live referee (not a mock) to reject it.
        g.players[0].setPosition(new int[]{0, 0});
        g.players[0].setVelocity(new int[]{-1, -1});
        final String beforeCrash = b.log();
        b.move(Direction.NW.ordinal(), false);
        check(beforeCrash.equals(b.log()) && !g.players[0].isFinished(), "crash happened without consent");
        final String crashed = b.move(Direction.NW.ordinal(), true);
        check(crashed.contains("\"outcome\":\"CRASH\""), "snapshot loses recorded crash outcome");
        check(g.players[0].getFinishedPlace() == 2 && b.log().contains(" CRASH place=2"), "confirmed crash did not use referee");
        testCustomTrackDrawing();
        testPlacementFailureRecovery();
        testStartingZoneDeltas();
        testOneAiMovePerStep();
        testTimeoutUndo();
        System.out.println("BrowserTests: previews, consent, original rules, one AI move per Step, undo, duplicate drawing points and placement recovery OK");
    }

    /** A timeout is undoable while at least two cars remain in PLAY. This
     * uses the same commit/undo methods as desktop, with nonmodal browser UI. */
    private static void testTimeoutUndo() throws Exception {
        final RaceGame g = new RaceGame(new java.util.Properties());
        g.gameCols = 80; g.gameRows = 20; g.track = new Track();
        g.track.addLeft(0, 1); g.track.addLeft(73, 1);
        g.track.addRight(0, 19); g.track.addRight(73, 19);
        g.trackA = new java.awt.geom.Area(new java.awt.geom.Rectangle2D.Double(0, 1, 73, 18));
        g.startZoneA = new java.awt.geom.Area();
        g.finishLine = new java.awt.geom.Line2D.Double(72.5, 1, 72.5, 19);
        g.lapGates = new java.awt.geom.Line2D[]{g.finishLine,
                new java.awt.geom.Line2D.Double(50, 1, 50, 19),
                new java.awt.geom.Line2D.Double(60, 1, 60, 19)};
        set(g, "finishFwdX", 1.0); set(g, "lapCrossGate", g.finishLine); set(g, "lapFwdX", 1.0);
        set(g, "rui", new tr.gui.RaceUI(20, 80)); set(g, "gamestate", GameState.PLAY);
        set(g, "startZoneGone", true);
        g.players = new Player[3];
        for (int i = 0; i < 3; i++) {
            g.players[i] = new Player("P" + (i + 1), i + 1, java.awt.Color.BLUE, Player.Kind.HUMAN);
            g.players[i].setPosition(new int[]{10 + 10 * i, 10});
            g.players[i].setVelocity(new int[]{0, 0});
        }
        final java.lang.reflect.Method commit = RaceGame.class.getDeclaredMethod("commitMove",
                int[].class, int[].class, int[].class);
        commit.setAccessible(true);
        g.setQueryTurnCounter(2249);
        for (int i = 0; i < 2; i++)
            commit.invoke(g, g.players[i].getPosition(), new int[]{0, 0}, g.players[i].getPosition().clone());
        final String before = undoState(g);
        for (int repeat = 0; repeat < 2; repeat++) {
            commit.invoke(g, g.players[2].getPosition(), new int[]{1, 0}, new int[]{31, 10});
            check(g.players[2].getFinishedPlace() == 3 && g.turnCount() == 2252,
                    "timeout fixture did not retire P3");
            check(get(g, "gamestate") == GameState.PLAY, "timeout fixture should remain playable");
            check(((java.util.Deque<?>) get(g, "moveHistory")).size() == 3,
                    "timeout did not record exactly one snapshot");
            g.clickedUndo();
            check(before.equals(undoState(g)), "timeout Undo rewound an earlier move or lost state");
            check(g.subgamestate == 2 && g.turnCount() == 2251 && !g.players[2].isFinished(),
                    "timeout Undo did not return P3 to its own turn");
        }
        // No preceding human move: the timeout itself must enable Undo.
        ((java.util.Deque<?>) get(g, "moveHistory")).clear();
        final String first = undoState(g);
        commit.invoke(g, g.players[2].getPosition(), new int[]{0, 0}, g.players[2].getPosition().clone());
        g.clickedUndo();
        check(first.equals(undoState(g)), "first-action timeout could not be undone");
        System.out.println("TimeoutUndo: exact clock, slot, log, positions, history and progress restored; retry OK");
    }

    private static String undoState(final RaceGame g) throws Exception {
        final StringBuilder out = new StringBuilder().append(g.turnCount()).append('/').append(g.subgamestate)
                .append('/').append(get(g, "finishedFirst")).append('/').append(get(g, "finishedLast"))
                .append('/').append(get(g, "startZoneGone")).append('/').append(get(g, "gameLog"));
        for (final Player p : g.players) {
            out.append(Arrays.toString(p.getPosition())).append(Arrays.toString(p.getVelocity()))
                    .append(p.getFinishedPlace()).append(Arrays.toString(p.lapState()));
            for (final int[] point : p.getHistory()) out.append(Arrays.toString(point));
        }
        return out.toString();
    }

    private static void set(final Object object, final String name, final Object value) throws Exception {
        final Field field = object.getClass().getDeclaredField(name);
        field.setAccessible(true); field.set(object, value);
    }

    private static void testCustomTrackDrawing() throws Exception {
        final BrowserBridge bridge = new BrowserBridge();
        bridge.create("", "nPlayers=1\nplayer1Kind=HUMAN\ngameX=20\ngameY=20\n", "1");
        bridge.ok(); bridge.undo(); bridge.click(5, 5); bridge.click(5, 5);
        final RaceGame game = (RaceGame) get(bridge, "game");
        check(game.track.getLeft().size() == 1, "duplicate first left point accepted");
        bridge.ok();
        check(game.subgamestate == 0, "short left border accepted");
        bridge.click(15, 5); bridge.undo();
        check(game.track.getLeft().size() == 1, "drawing undo differs");
        bridge.click(15, 5); bridge.ok();
        check(game.subgamestate == 1, "valid left border rejected");
        bridge.click(5, 10); bridge.click(5, 10);
        check(game.track.getRight().size() == 1, "duplicate first right point accepted");
        bridge.ok();
        check(get(game, "gamestate") == GameState.DRAWTRACK, "short right border accepted");
        bridge.click(15, 10); bridge.ok(); bridge.awaitReady();
        check(get(game, "gamestate") == GameState.PLACEPLAYERS,
                "duplicate clicks prevented completion of a corrected custom circuit");
    }

    private static void testPlacementFailureRecovery() throws Exception {
        final BrowserBridge bridge = new BrowserBridge();
        bridge.create("", "nPlayers=2\nplayer1Kind=HUMAN\nplayer2Kind=AI2\naiStartPlacement=informed\ngameX=20\ngameY=20\n", "1");
        bridge.ok(); bridge.click(7, 10); bridge.click(6, 6); bridge.ok();
        bridge.click(6, 8); bridge.click(5, 7); bridge.ok(); bridge.awaitReady();
        final RaceGame game = (RaceGame) get(bridge, "game");
        // This valid small circuit has only one viable AI start. A human can
        // occupy it, then undo and leave it free by choosing another legal cell.
        final String blocked = bridge.click(6, 8);
        final String message = "Player 2 (AI) couldn't find a start position.";
        check(message.equals(get(game, "placementFailure")), "fixture did not block AI placement");
        check(blocked.contains("\"placementFailure\":\"" + message + "\"")
                        && blocked.contains("\"failure\":null") && blocked.contains("\"undo\":true"),
                "placement error was not recoverable in the action delta");
        final String full = bridge.snapshot();
        check(full.contains("\"placementFailure\":\"" + message + "\"") && !full.contains("\"failure\":"),
                "placement error became fatal in the full snapshot");
        final String undone = bridge.undo();
        check(undone.contains("\"placementFailure\":null") && game.subgamestate == 0,
                "undo did not explicitly clear the placement error at the same turn");
        bridge.click(7, 8);
        check(get(game, "placementFailure") == null && game.subgamestate == 2
                        && Arrays.equals(game.players[1].getPosition(), new int[]{6, 8}),
                "replacement human placement did not free the viable AI start");
        bridge.ok();
        check(get(game, "gamestate") == GameState.PLAY, "recovered race could not start");
        final Field failure = Reachability.class.getDeclaredField("reachabilityFailure");
        failure.setAccessible(true);
        failure.set(game.reach, new IllegalStateException("expected preparation failure"));
        check(bridge.snapshot().contains("\"failure\":\"java.lang.IllegalStateException: expected preparation failure\""),
                "actual preparation error was downgraded to a recoverable placement error");
    }

    private static void testOneAiMovePerStep() throws Exception {
        final BrowserBridge bridge = new BrowserBridge();
        bridge.create("hairpin", "nPlayers=3\nplayer1Kind=AI2\nplayer2Kind=AI2\nplayer3Kind=AI2\naiStartPlacement=legacy\nlaps=1\n", "1");
        bridge.awaitReady();
        final RaceGame game = (RaceGame) get(bridge, "game");
        for (int i = 0; i < 10 && game.subgamestate < game.players.length; i++) bridge.tick();
        check(game.subgamestate == game.players.length, "AI-only field did not finish placement");
        bridge.ok();
        for (int turn = 1; turn <= 6; turn++) {
            bridge.tick();
            check(game.turnCount() == turn, "Step ran more or less than one move in an AI-only field");
        }
    }

    private static void testStartingZoneDeltas() throws Exception {
        final BrowserBridge bridge = new BrowserBridge();
        bridge.create("hairpin", "nPlayers=1\nplayer1Kind=HUMAN\n", "1");
        bridge.awaitReady();
        final RaceGame game = (RaceGame) get(bridge, "game");
        // This border-adjacent start has a legal northward exit from the zone.
        bridge.click(5, 27);
        bridge.ok();
        final String moved = bridge.move(Direction.N.ordinal(), false);
        check((int) get(game, "turnCounter") == 1, "start-zone fixture did not move");
        check(get(get(bridge, "scene"), "startZone") == null, "referee did not hide the start zone");
        check(moved.contains("\"startZone\":null") && !moved.contains("\"shape\":"),
                "hiding the start zone was omitted from the ordinary action delta");
        final String undone = bridge.undo();
        check(get(get(bridge, "scene"), "startZone") != null, "undo did not restore the start zone");
        check(undone.contains("\"startZone\":[") && !undone.contains("\"shape\":"),
                "restoring the start zone was omitted from the undo delta");
    }
}
