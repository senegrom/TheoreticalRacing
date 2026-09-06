package tr.logic;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import tr.browser.Progress;

/** Real engine + a blocking telemetry observer: placement must not wait for BFS. */
public final class StartupTests {
    private StartupTests() {}
    private static void check(final boolean ok, final String message) {
        if (!ok) throw new AssertionError(message);
    }
    public static void main(final String[] args) throws Exception {
        final int count = Integer.parseInt(args[0]);
        final String track = args.length > 1 ? args[1] : "hairpin";
        final int laps = args.length > 2 ? Integer.parseInt(args[2]) : 1;
        final StringBuilder props = new StringBuilder("nPlayers=" + count + "\nlaps=" + laps + "\nplayer1Kind=HUMAN\n");
        for (int i = 2; i <= count; i++) props.append("player").append(i).append("Kind=AI").append(i % 2 + 1).append('\n');
        final var commands = Executors.newSingleThreadExecutor();
        final BrowserBridge bridge = new BrowserBridge();
        try {
            final var created = commands.submit(() -> bridge.create(track, props.toString(), "1"));
            check(Progress.ENTERED.await(10, TimeUnit.SECONDS), "Distance preparation did not start");
            check(created.get(5, TimeUnit.SECONDS).contains("\"phase\":\"PLACEPLAYERS\""), "Placement not available during distance calculation");
            check(!bridge.readiness().contains("\"ready\":true"), "Incomplete maps reported ready");
            final Field field = BrowserBridge.class.getDeclaredField("game");
            field.setAccessible(true);
            final RaceGame game = (RaceGame) field.get(bridge);
            final List<int[]> allCells = new ArrayList<>();
            for (int x = 0; x <= game.gameCols; x++) for (int y = 0; y <= game.gameRows; y++) {
                if (game.startZoneA.contains(x, y)) allCells.add(new int[]{x, y});
            }
            final Field cells = BrowserBridge.class.getDeclaredField("startCells");
            cells.setAccessible(true);
            final List<?> cached = (List<?>) cells.get(bridge);
            check(cached.size() == allCells.size(), "Cached start scan lost cells");
            for (int i = 0; i < cached.size(); i++) check(Arrays.equals((int[]) cached.get(i), allCells.get(i)), "Start enumeration order changed");
            int[] start = null;
            outer: for (int x = 0; x <= game.gameCols; x++) for (int y = 0; y <= game.gameRows; y++) {
                if (game.startZoneA.contains(x, y)) { start = new int[]{x, y}; break outer; }
            }
            check(start != null, "No start cell");
            final int[] cell = start;
            commands.submit(() -> bridge.click(cell[0], cell[1])).get(5, TimeUnit.SECONDS);
            for (final Player player : game.players) check(player.getPosition()[0] != Player.INIT_POS, "A driver was not placed");
            check(Progress.BUILDS.get() == 1 && Progress.DISTANCES.get() == 1,
                    "Placing multiple drivers repeated preparation");
            check(!game.reach.isReady(), "Observer stopped blocking unexpectedly");
            Progress.RELEASE.countDown();
            bridge.awaitReady();
            check(Progress.BUILDS.get() == 1 && Progress.DISTANCES.get() == 1, "Preparation ran twice");
            check(Progress.FINISHES.get() <= 1, "Finish map recomputed per driver");
            System.out.println("StartupTests: " + count + " drivers, " + laps + " laps; placement overlaps distance BFS; one shared map build");
        } finally {
            Progress.RELEASE.countDown();
            commands.shutdownNow();
        }
    }
}
