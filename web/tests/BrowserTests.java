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
        final BrowserBridge custom = new BrowserBridge();
        custom.create("", "nPlayers=1\nplayer1Kind=HUMAN\n", "");
        custom.ok(); custom.undo(); custom.click(5, 5); custom.click(15, 5); custom.undo();
        final RaceGame drawing = (RaceGame) get(custom, "game");
        check(drawing.track.getLeft().size() == 1, "drawing undo differs");
        custom.ok();
        check(drawing.subgamestate == 0, "short border accepted");
        testStartingZoneDeltas();
        testOneAiMovePerStep();
        System.out.println("BrowserTests: previews, consent, original rules, one AI move per Step, undo, drawing and validation OK");
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
