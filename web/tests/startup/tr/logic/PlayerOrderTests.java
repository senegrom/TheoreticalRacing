package tr.logic;

import java.lang.reflect.Field;
import java.util.Arrays;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import tr.browser.Progress;

/** Explicit AI-first/interleaved ordering and shared-analysis completion barriers. */
public final class PlayerOrderTests {
    private PlayerOrderTests() {}
    private static void check(final boolean ok, final String message) {
        if (!ok) throw new AssertionError(message);
    }
    private static boolean placed(final Player p) { return p.getPosition()[0] != Player.INIT_POS; }
    private static int[] free(final RaceGame g, final int[] exclude) {
        for (int x=0; x<=g.gameCols; x++) for (int y=0; y<=g.gameRows; y++) {
            if (g.startZoneA.contains(x,y) && !g.isCrashingPlayer(x,y,g.players[g.subgamestate].getNumber())
                    && (exclude == null || x != exclude[0] || y != exclude[1])) return new int[]{x,y};
        }
        throw new AssertionError("No free start");
    }
    private static void prefix(final RaceGame g) {
        for (int i=0; i<g.players.length; i++)
            check(placed(g.players[i]) == (i < g.subgamestate), "Placement skipped roster slot " + i);
    }
    private static void blockedAi(final BrowserBridge b, final RaceGame g, final int expected) {
        check(g.players[expected].isAi(), "Expected an AI turn");
        final int[] p = free(g,null);
        b.click(p[0],p[1]); b.ok(); b.tick();
        check(g.subgamestate == expected && !g.reach.isReady(), "Input bypassed a pending AI or analysis barrier");
        prefix(g);
        try { StartPlacement.choose(g,g.players[expected],1L); throw new AssertionError("Partial analysis admitted"); }
        catch (final IllegalStateException correct) { /* It must not choose a fallback. */ }
    }
    private static void drain(final BrowserBridge b, final RaceGame g) {
        for (int i=0; i<20 && g.subgamestate<g.players.length && g.players[g.subgamestate].isAi(); i++) b.tick();
        check(g.subgamestate == g.players.length || !g.players[g.subgamestate].isAi(), "Ready AI never placed");
        prefix(g);
    }
    public static void main(final String[] args) throws Exception {
        final String roster = args[0];
        final String track = args.length>1 ? args[1] : "hairpin";
        final int laps = args.length>2 ? Integer.parseInt(args[2]) : 1;
        final StringBuilder config = new StringBuilder("aiStartPlacement=informed\nnPlayers=" + roster.length() + "\nlaps=" + laps + "\n");
        for (int i=0; i<roster.length(); i++) config.append("player").append(i+1).append("Kind=")
                .append(roster.charAt(i)=='H' ? "HUMAN" : i%2==0 ? "AI1" : "AI2").append('\n');
        Progress.holdAlternatives = true;
        final var commands = Executors.newSingleThreadExecutor();
        final BrowserBridge bridge = new BrowserBridge();
        try {
            final var created = commands.submit(() -> bridge.create(track,config.toString(),"1"));
            check(Progress.ENTERED.await(10,TimeUnit.SECONDS), "Distance scan never started");
            created.get(5,TimeUnit.SECONDS);
            final Field field = BrowserBridge.class.getDeclaredField("game"); field.setAccessible(true);
            final RaceGame g = (RaceGame) field.get(bridge);
            prefix(g);
            while (!g.players[g.subgamestate].isAi()) {
                final int[] p = free(g,null); bridge.click(p[0],p[1]); prefix(g);
            }
            final int waiting = g.subgamestate;
            blockedAi(bridge,g,waiting);
            check(g.preparedStartAnalysis()==null && Progress.ALTERNATIVES.get()==0, "Alternatives built before complete maps");
            Progress.RELEASE.countDown();
            if (g.lapGates != null) {
                check(Progress.OPTIMAL_ENTERED.await(25,TimeUnit.SECONDS), "Exact-race barrier missing");
                blockedAi(bridge,g,waiting);
                check(g.preparedStartAnalysis()==null, "Alternatives built before exact-race map");
            }
            Progress.OPTIMAL_RELEASE.countDown();
            check(Progress.ALTERNATIVES_ENTERED.await(25,TimeUnit.SECONDS), "Shared alternative scan missing");
            blockedAi(bridge,g,waiting);
            Progress.ALTERNATIVES_RELEASE.countDown();
            bridge.awaitReady();
            final StartPlacement.Analysis shared = g.preparedStartAnalysis();
            check(shared != null && Progress.ALTERNATIVES.get()==1, "Missing/duplicated shared scan");
            drain(bridge,g);
            while (g.subgamestate < g.players.length) {
                // A later human stays unplaced until every earlier AI has chosen.
                final int index=g.subgamestate; check(!g.players[index].isAi(), "Human not next");
                for (int i=0;i<3;i++) bridge.tick();
                check(g.subgamestate==index, "AI jumped across an intervening human");
                final int[] p=free(g,null); bridge.click(p[0],p[1]); drain(bridge,g);
                check(g.preparedStartAnalysis()==shared, "New analysis for another AI");
            }
            final int[][] positions=Arrays.stream(g.players).map(p->p.getPosition().clone()).toArray(int[][]::new);
            for (final Player p:g.players) p.setPosition(new int[]{Player.INIT_POS,Player.INIT_POS});
            for (int i=0;i<g.players.length;i++) {
                if (g.players[i].isAi()) check(Arrays.equals(positions[i],StartPlacement.choose(g,g.players[i],1L)),
                        "Choice did not use exactly earlier committed placements");
                g.players[i].setPosition(positions[i]);
            }
            final int lastHuman=roster.lastIndexOf('H');
            if (lastHuman>=0) {
                g.clickedUndo(); prefix(g);
                check(g.subgamestate==lastHuman, "Undo retained dependent choices");
                final int[] replacement=free(g,positions[lastHuman]);
                bridge.click(replacement[0],replacement[1]); drain(bridge,g);
                check(g.preparedStartAnalysis()==shared, "Undo rebuilt base analysis");
            }
            check(Progress.BUILDS.get()==1 && Progress.DISTANCES.get()==1 && Progress.ALTERNATIVES.get()==1,
                    "Preparation repeated for each AI or after Undo");
            check(Progress.OPTIMAL.get()==(g.lapGates==null?0:1), "Exact potential duplicated");
            System.out.println("PlayerOrderTests: " + roster + ", " + laps + " laps; strict roster order, three preparation barriers, one shared analysis, live occupancy and Undo OK");
        } finally {
            Progress.RELEASE.countDown(); Progress.OPTIMAL_RELEASE.countDown(); Progress.ALTERNATIVES_RELEASE.countDown();
            commands.shutdownNow();
        }
    }
}
