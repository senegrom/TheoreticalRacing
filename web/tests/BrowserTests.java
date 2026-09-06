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
        final BrowserBridge b = new BrowserBridge();
        b.create("hairpin", "nPlayers=2\nplayer1Kind=HUMAN\nplayer2Kind=AI1\nlaps=1\n", "1");
        final RaceGame g = (RaceGame) get(b, "game");
        b.awaitReady();
        int[] start = null;
        outer: for (int x = 0; x <= g.gameCols; x++) for (int y = 0; y <= g.gameRows; y++) {
            if (g.startZoneA.contains(x, y)) { start = new int[]{x, y}; break outer; }
        }
        check(start != null, "human start missing");
        b.click(start[0], start[1]);
        check(g.players[1].getPosition()[0] != Player.INIT_POS, "AI not auto-placed after human");
        b.ok();
        final String originalLog = b.log();
        final int[][] originalPositions = {g.players[0].getPosition().clone(), g.players[1].getPosition().clone()};
        Direction legal = null;
        for (final Direction d : Direction.values()) {
            if (d != Direction.NONE && g.evaluateMove(g.players[0], start, new int[]{start[0] + d.dx, start[1] + d.dy}).legal()) { legal = d; break; }
        }
        check(legal != null, "no legal first move");
        b.preview(legal.ordinal()); b.preview(legal.ordinal());
        check(Arrays.equals(g.players[0].getPosition(), start), "repeated preview moved the car");
        check(originalLog.equals(b.log()), "preview changed race log");
        b.move(legal.ordinal(), false);
        check(!Arrays.equals(g.players[0].getPosition(), start), "confirm did not execute move");
        int ticks = 0;
        while (g.players[g.subgamestate].isAi() && ++ticks < 10) b.tick();
        check(!g.players[g.subgamestate].isAi(), "AI replies did not return human turn");
        b.undo();
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
        b.move(Direction.NW.ordinal(), true);
        check(g.players[0].getFinishedPlace() == 2 && b.log().contains(" CRASH place=2"), "confirmed crash did not use referee");
        final BrowserBridge custom = new BrowserBridge();
        custom.create("", "nPlayers=1\nplayer1Kind=HUMAN\n", "");
        custom.ok(); custom.undo(); custom.click(5, 5); custom.click(15, 5); custom.undo();
        final RaceGame drawing = (RaceGame) get(custom, "game");
        check(drawing.track.getLeft().size() == 1, "drawing undo differs");
        custom.ok();
        check(drawing.subgamestate == 0, "short border accepted");
        System.out.println("BrowserTests: previews, consent, original rules, AI replies, undo, drawing and validation OK");
    }
}
