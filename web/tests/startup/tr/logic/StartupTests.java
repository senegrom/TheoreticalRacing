package tr.logic;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import tr.browser.Progress;

/** Humans may place during map preparation; AI decisions must wait for ALL maps. */
public final class StartupTests {
    private StartupTests() {}
    private static void check(final boolean ok, final String message) {
        if (!ok) throw new AssertionError(message);
    }
    private static boolean placed(final Player player) { return player.getPosition()[0] != Player.INIT_POS; }
    private static int[] firstFree(final RaceGame g) {
        for (int x = 0; x <= g.gameCols; x++) for (int y = 0; y <= g.gameRows; y++) {
            if (g.startZoneA.contains(x, y) && !g.isCrashingPlayer(x, y, g.players[g.subgamestate].getNumber())) return new int[]{x,y};
        }
        throw new AssertionError("No start cell");
    }
    private static void drainAi(final BrowserBridge bridge, final RaceGame game) {
        for (int i = 0; i < 20 && game.subgamestate < game.players.length && game.players[game.subgamestate].isAi(); i++) bridge.tick();
        check(game.subgamestate == game.players.length || !game.players[game.subgamestate].isAi(), "AI placement callback was lost");
    }
    public static void main(final String[] args) throws Exception {
        final int count = Integer.parseInt(args[0]);
        final String track = args.length > 1 ? args[1] : "hairpin";
        final int laps = args.length > 2 ? Integer.parseInt(args[2]) : 1;
        final StringBuilder props = new StringBuilder("aiStartPlacement=informed\nnPlayers=" + count + "\nlaps=" + laps + "\nplayer1Kind=HUMAN\n");
        for (int i = 2; i <= count; i++) props.append("player").append(i).append("Kind=").append(count == 4 && i == 3 ? "HUMAN" : "AI" + (i % 2 + 1)).append('\n');
        final var commands = Executors.newSingleThreadExecutor();
        final BrowserBridge bridge = new BrowserBridge();
        try {
            final var created = commands.submit(() -> bridge.create(track, props.toString(), "1"));
            check(Progress.ENTERED.await(10, TimeUnit.SECONDS), "Distance preparation did not start");
            check(created.get(5, TimeUnit.SECONDS).contains("\"phase\":\"PLACEPLAYERS\""), "Human placement unavailable during distance calculation");
            check(!bridge.readiness().contains("\"ready\":true"), "Incomplete maps reported ready");
            final Field field = BrowserBridge.class.getDeclaredField("game"); field.setAccessible(true);
            final RaceGame game = (RaceGame) field.get(bridge);
            final List<int[]> allCells = new ArrayList<>();
            for (int x = 0; x <= game.gameCols; x++) for (int y = 0; y <= game.gameRows; y++)
                if (game.startZoneA.contains(x, y)) allCells.add(new int[]{x,y});
            final Field cells = BrowserBridge.class.getDeclaredField("startCells"); cells.setAccessible(true);
            final List<?> cached = (List<?>) cells.get(bridge);
            check(cached.size() == allCells.size(), "Cached start scan lost cells");
            for (int i = 0; i < cached.size(); i++) check(Arrays.equals((int[]) cached.get(i), allCells.get(i)), "Start enumeration changed");
            final int[] human = firstFree(game);
            commands.submit(() -> bridge.click(human[0], human[1])).get(5, TimeUnit.SECONDS);
            check(placed(game.players[0]), "Human placement waited for maps");
            for (int i = 1; i < count; i++) check(!placed(game.players[i]), "AI/later human placed before ready");
            if (count > 1) {
                final int[] free = firstFree(game);
                bridge.click(free[0], free[1]); bridge.ok(); bridge.tick();
                check(game.subgamestate == 1 && !placed(game.players[1]), "Manual input/tick bypassed the AI barrier");
                try { StartPlacement.choose(game, game.players[1], 1L); throw new AssertionError("Partial map accepted"); }
                catch (final IllegalStateException expected) { /* No fallback to a random start. */ }
            }
            check(Progress.BUILDS.get() == 1 && Progress.DISTANCES.get() == 1, "Map job duplicated per car");
            Progress.RELEASE.countDown();
            if (count > 1 && game.lapGates != null) {
                check(Progress.OPTIMAL_ENTERED.await(25, TimeUnit.SECONDS), "Exact race map not part of preparation");
                bridge.tick();
                check(!game.reach.isReady() && game.subgamestate == 1, "AI placed before exact race potential completed");
                for (int i = 1; i < count; i++) check(!placed(game.players[i]), "AI crossed optimality barrier early");
            }
            Progress.OPTIMAL_RELEASE.countDown();
            bridge.awaitReady();
            drainAi(bridge, game);
            if (count == 4) {
                check(game.subgamestate == 2 && !placed(game.players[3]), "AI preselected before intervening human");
                final int[] lateHuman = firstFree(game);
                bridge.click(lateHuman[0], lateHuman[1]);
                check(Arrays.equals(game.players[2].getPosition(), lateHuman), "Second human could not choose");
                drainAi(bridge, game);
            }
            for (final Player player : game.players) check(placed(player), "Ready AI was not placed");
            // Reconstruct each placement's information set from the final field.
            final int[][] positions = Arrays.stream(game.players).map(p -> p.getPosition().clone()).toArray(int[][]::new);
            for (final Player player : game.players) player.setPosition(new int[]{Player.INIT_POS, Player.INIT_POS});
            for (int i = 0; i < count; i++) {
                if (game.players[i].isAi()) check(Arrays.equals(positions[i], StartPlacement.choose(game, game.players[i], 1L)), "AI did not rescore current occupancy");
                game.players[i].setPosition(positions[i]);
            }
            check(Progress.OPTIMAL.get() == (count > 1 && game.lapGates != null ? 1 : 0), "Exact map repeated per AI");
            check(Progress.BUILDS.get() == 1 && Progress.DISTANCES.get() == 1 && Progress.FINISHES.get() <= 1, "Preparation repeated during placements");
            if (count == 4) {
                game.clickedUndo();
                check(game.subgamestate == 2 && !placed(game.players[2]) && !placed(game.players[3]), "Undo retained dependent AI placement");
                bridge.click(positions[2][0], positions[2][1]);
                check(Arrays.equals(game.players[3].getPosition(), positions[3]), "Undo changed deterministic tie breaking");
            }
            System.out.println("StartupTests: " + count + " drivers, " + laps + " laps; human placement overlaps BFS; AI waits for full maps and uses sequential occupancy; one shared build");
        } finally {
            Progress.RELEASE.countDown(); Progress.OPTIMAL_RELEASE.countDown(); commands.shutdownNow();
        }
    }
}
