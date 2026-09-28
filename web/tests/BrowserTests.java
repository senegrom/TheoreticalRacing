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
        testCoarseLoopRefused();
        testDrawnCheckpointsByLength();
        testPlacementFailureRecovery();
        testStartingZoneDeltas();
        testOneAiMovePerStep();
        testTimeoutUndo();
        testReachCachePruned();
        check(b.build().matches("[0-9a-f]{64}"), "the jar carries no engine build identity: " + b.build());
        testExactMapBesideTheMaps();
        System.out.println("BrowserTests: previews, consent, original rules, one AI move per Step, undo, duplicate drawing points, coarse loops refused, drawn checkpoints by length and placement recovery OK");
    }

    /** Review, 2026-09-28: with computed starts the exact race map builds beside
     *  the reachability maps; its stage must not mark theirs complete. */
    private static void testExactMapBesideTheMaps() {
        tr.browser.Progress.geometry();
        tr.browser.Progress.plan(true, true, true);
        tr.browser.Progress.begin("Scanning finish approaches", 4);
        tr.browser.Progress.begin("Exact full-race map", 9);
        check(tr.browser.Progress.stage() == 4, "the exact map jumped the checklist to " + tr.browser.Progress.stage());
        tr.browser.Progress.begin("Resolving lap checkpoints", 6);
        tr.browser.Progress.begin("Lap safety", 7);
        tr.browser.Progress.begin("Computing braking maps", 5);
        check(tr.browser.Progress.stage() == 8, "the lap-driving sweeps did not show as stage 8");
        tr.browser.Progress.begin("Exact full-race map", 9);
        check(tr.browser.Progress.stage() == 9, "the exact map did not follow the lap maps");
    }

    /** Review, 2026-09-28: the browser's map caches never shrank. Pruning keeps
     *  this race's maps and the newest others within the budget, drops stale
     *  temporary files and the retired generation's files. */
    private static void testReachCachePruned() throws Exception {
        final java.nio.file.Path root = java.nio.file.Files.createTempDirectory("prune");
        final java.nio.file.Path live = java.nio.file.Files.createDirectory(root.resolve("maps-v2"));
        final long now = 10_000_000_000L;
        final java.util.function.BiConsumer<String, Long> file = (name, age) -> {
            try {
                final java.nio.file.Path p = live.resolve(name);
                java.nio.file.Files.write(p, new byte[100]);
                java.nio.file.Files.setLastModifiedTime(p, java.nio.file.attribute.FileTime.fromMillis(now - age));
            } catch (final java.io.IOException e) { throw new java.io.UncheckedIOException(e); }
        };
        java.nio.file.Files.write(root.resolve("reach-retired.bin"), new byte[100]);
        file.accept("reach-current.bin", 9_000_000L);          // oldest, but this race's
        file.accept("reach-current.bin.derived", 9_000_000L);
        file.accept("reach-new.bin", 1_000L);
        file.accept("reach-mid.bin", 5_000L);
        file.accept("reach-old.bin", 8_000L);
        file.accept(".reach-new.bin.tmp.1.tmp", 7_200_000L);   // abandoned two hours ago
        file.accept(".reach-mid.bin.tmp.2.tmp", 60_000L);      // perhaps still being written
        BrowserBridge.pruneReachCache(live, live.resolve("reach-current.bin").toString(), 400, now);
        final java.util.Set<String> left = new java.util.TreeSet<>();
        try (java.util.stream.Stream<java.nio.file.Path> s = java.nio.file.Files.list(live)) {
            s.forEach(p -> left.add(p.getFileName().toString()));
        }
        check(left.equals(new java.util.TreeSet<>(java.util.List.of("reach-current.bin", "reach-current.bin.derived",
                "reach-new.bin", "reach-mid.bin", ".reach-mid.bin.tmp.2.tmp"))), "pruned cache holds " + left);
        check(!java.nio.file.Files.exists(root.resolve("reach-retired.bin")), "a retired generation's file survived");
    }

    /** The owner's drawn-track rule (2026-09-27): a closed loop drawn with too
     *  few points for its checkpoints is refused at that border's OK, and the
     *  same border is accepted once it has eight points. */
    private static void testCoarseLoopRefused() throws Exception {
        final BrowserBridge bridge = new BrowserBridge();
        bridge.create("", "nPlayers=1\nplayer1Kind=HUMAN\ngameX=40\ngameY=30\n", "1");
        bridge.ok();
        for (final int[] p : new int[][]{{10, 5}, {30, 5}, {30, 25}, {5, 25}, {5, 7}})
            bridge.click(p[0], p[1]);
        bridge.ok();
        final RaceGame game = (RaceGame) get(bridge, "game");
        check(game.subgamestate == 0, "a closed loop too coarse for checkpoints was accepted");
        bridge.undo(); bridge.undo();
        for (final int[] p : new int[][]{{20, 25}, {5, 25}, {5, 15}, {5, 7}})
            bridge.click(p[0], p[1]);
        bridge.ok();
        check(game.track.getLeft().size() == 7 && game.subgamestate == 0,
                "a seven-point closed loop was accepted");
        bridge.undo();
        for (final int[] p : new int[][]{{5, 10}, {5, 7}})
            bridge.click(p[0], p[1]);
        bridge.ok();
        check(game.track.getLeft().size() == 8 && game.subgamestate == 1,
                "an eight-point closed loop was refused");
    }

    /** The owner's rule for drawings (2026-09-27): the checkpoints sit at a third
     *  and two thirds of the left border's LENGTH. Placed by index, this nine-point
     *  loop put both on its last side, and a 14-move backwards lap counted. */
    private static void testDrawnCheckpointsByLength() throws Exception {
        final BrowserBridge bridge = new BrowserBridge();
        bridge.create("", "nPlayers=1\nplayer1Kind=HUMAN\ngameX=45\ngameY=85\n", "1");
        bridge.ok();
        for (final int[] p : new int[][]{{5, 8}, {5, 75}, {35, 75}, {35, 8}, {35, 5}, {20, 5}, {15, 5}, {11, 5}, {8, 5}})
            bridge.click(p[0], p[1]);
        bridge.ok();
        for (final int[] p : new int[][]{{15, 16}, {15, 65}, {25, 65}, {25, 16}, {25, 15}, {22, 15}, {19, 15}, {17, 15}, {16, 15}})
            bridge.click(p[0], p[1]);
        bridge.ok();
        bridge.awaitReady();
        final RaceGame game = (RaceGame) get(bridge, "game");
        check(game.lapGates != null, "the drawn loop was not lapped");
        // The left border is 194 cells long: a third lies on its first side, two
        // thirds on its third; each checkpoint runs to the nearest inner point.
        check(game.lapGates[1].getX1() == 5 && Math.abs(game.lapGates[1].getY1() - 8 - 194 / 3.0) < 1e-9
                && game.lapGates[1].getX2() == 15 && game.lapGates[1].getY2() == 65,
                "CP1 is not at a third of the border's length: " + game.lapGates[1].getP1() + " " + game.lapGates[1].getP2());
        check(game.lapGates[2].getX1() == 35 && Math.abs(game.lapGates[2].getY1() - (75 - (2 * 194 / 3.0 - 97))) < 1e-9
                && game.lapGates[2].getX2() == 25,
                "CP2 is not at two thirds of the border's length: " + game.lapGates[2].getP1() + " " + game.lapGates[2].getP2());
        // The page draws the referee's segments, not rounded ones (review, 2026-09-28).
        final double[][] drawn = ((tr.gui.RaceUI) get(bridge, "scene")).checkpoints;
        check(drawn.length == 2 && drawn[0][1] == game.lapGates[1].getY1() && drawn[1][1] == game.lapGates[2].getY1(),
                "the page draws the checkpoints off the referee's: " + java.util.Arrays.deepToString(drawn));
        int[] start = null;
        outer: for (int x = 0; x <= game.gameCols; x++) for (int y = 0; y <= game.gameRows; y++)
            if (game.startZoneA.contains(x, y) && game.trackA.contains(x, y)) { start = new int[]{x, y}; break outer; }
        check(start != null, "no grid cell on the drawn loop");
        final int lap = OptimalLap.solve(game, start[0], start[1], 1);
        check(lap > 20, "a short lap still counts on the drawn loop: " + lap + " moves");
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
    /** The generated adapter only makes dialogs non-modal; commit/undo are the real engine. */
    private static void testTimeoutUndo() throws Exception {
        final RaceGame game = new RaceGame(new java.util.Properties());
        game.gameCols = 80; game.gameRows = 20; game.track = new Track();
        game.track.addLeft(0, 1); game.track.addLeft(73, 1);
        game.track.addRight(0, 19); game.track.addRight(73, 19);
        game.trackA = new java.awt.geom.Area(new java.awt.geom.Rectangle2D.Double(0, 1, 73, 18));
        game.startZoneA = new java.awt.geom.Area();
        game.finishLine = new java.awt.geom.Line2D.Double(72.5, 1, 72.5, 19);
        game.lapGates = new java.awt.geom.Line2D[]{game.finishLine,
                new java.awt.geom.Line2D.Double(50, 1, 50, 19),
                new java.awt.geom.Line2D.Double(60, 1, 60, 19)};
        set(game, "finishFwdX", 1.0); set(game, "lapFwdX", 1.0);
        set(game, "lapCrossGate", game.finishLine);
        set(game, "rui", new tr.gui.RaceUI(20, 80));
        set(game, "gamestate", GameState.PLAY); set(game, "startZoneGone", true);
        game.players = new Player[3];
        for (int i = 0; i < 3; i++) {
            game.players[i] = new Player("P" + (i + 1), i + 1, java.awt.Color.BLUE, Player.Kind.HUMAN);
            game.players[i].setPosition(new int[]{10 + 10 * i, 10});
            game.players[i].setVelocity(new int[]{0, 0});
        }
        final java.lang.reflect.Method commit = RaceGame.class.getDeclaredMethod("commitMove", int[].class, int[].class, int[].class);
        commit.setAccessible(true);
        game.setQueryTurnCounter(2249);
        for (int i = 0; i < 2; i++)
            commit.invoke(game, game.players[i].getPosition(), new int[]{0, 0}, game.players[i].getPosition().clone());
        final String savedLog = get(game, "gameLog").toString();
        final int[] savedLap = game.players[2].lapState();
        final int savedHistory = game.players[2].getHistory().size();
        commit.invoke(game, game.players[2].getPosition(), new int[]{1, 0}, new int[]{31, 10});
        check(game.turnCount() == 2252 && game.players[2].getFinishedPlace() == 3
                && get(game, "gamestate") == GameState.PLAY, "timeout fixture did not leave an ongoing race");
        check(get(game, "gameLog").toString().contains("TIMEOUT place=3"), "timeout was not committed");
        game.clickedUndo();
        check(game.turnCount() == 2251 && game.subgamestate == 2, "timeout undo consumed the preceding player's move");
        check(savedLog.equals(get(game, "gameLog").toString()), "timeout undo did not restore the exact log");
        check(game.players[2].getFinishedPlace() == 0 && (int) get(game, "finishedLast") == 0
                && Arrays.equals(game.players[2].getPosition(), new int[]{30, 10})
                && Arrays.equals(game.players[2].getVelocity(), new int[]{0, 0})
                && Arrays.equals(game.players[2].lapState(), savedLap)
                && game.players[2].getHistory().size() == savedHistory, "timeout undo did not restore all player state");
        // Repeating the action must be deterministic, not consume an extra snapshot.
        commit.invoke(game, game.players[2].getPosition(), new int[]{1, 0}, new int[]{31, 10});
        game.clickedUndo(); game.clickedUndo();
        check(game.turnCount() == 2250 && game.subgamestate == 1, "successive undo lost the earlier action boundary");
        // Declined crash consent still must not add a committed action.
        final int snapshots = ((java.util.Deque<?>) get(game, "moveHistory")).size();
        final String beforeDecline = get(game, "gameLog").toString();
        commit.invoke(game, game.players[1].getPosition(), new int[]{0, -20}, new int[]{20, -10});
        check(((java.util.Deque<?>) get(game, "moveHistory")).size() == snapshots
                && beforeDecline.equals(get(game, "gameLog").toString()), "declined crash recorded an Undo action");
        game.setAutoMode(true); game.setQueryTurnCounter(2251);
        commit.invoke(game, game.players[1].getPosition(), new int[]{0, 0}, game.players[1].getPosition().clone());
        check(((java.util.Deque<?>) get(game, "moveHistory")).size() == snapshots, "auto timeout allocated Undo history");
        System.out.println("Timeout Undo: mover, clock, classification, log, histories and lap state restored; consent preserved");
    }

    private static void set(final Object object, final String name, final Object value) throws Exception {
        final Field f = object.getClass().getDeclaredField(name);
        f.setAccessible(true); f.set(object, value);
    }

}
