package tr.logic;

import java.awt.Color;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.List;
import java.util.Properties;

/** Exact equivalence and partial-order contracts, not a performance campaign. */
public final class ContingentPrefixTests {
    private ContingentPrefixTests() {}
    private static void check(final boolean ok, final String why) { if (!ok) throw new AssertionError(why); }
    private static RaceGame game(final String course, final String flags) throws Exception {
        final Method fixture = ChooserResearchTests.class.getDeclaredMethod("game", String.class, Properties.class);
        fixture.setAccessible(true);
        final Properties p = new Properties(); p.setProperty("chooser.experiments", flags);
        p.setProperty("chooser.policyBudget", "16000"); p.setProperty("chooser.moveBudget", "32000");
        p.setProperty("chooser.setupWidth", "3"); p.setProperty("candidateSlots", "1,2");
        if (course.equals("circle")) p.setProperty("laps", "2");
        return (RaceGame) fixture.invoke(null, course, p);
    }
    private static Player car(final int slot, final int x, final int y, final int vx, final int vy, final int lap, final int gate) {
        final Player p = new Player("P" + slot, slot, Color.BLUE, Player.Kind.AI2);
        p.setPosition(new int[]{x,y}); p.setVelocity(new int[]{vx,vy});
        p.restoreLapState(new int[]{lap,gate,0,0,0,0}); return p;
    }
    private static String live(final RaceGame g) {
        final StringBuilder s = new StringBuilder().append(g.subgamestate).append('/').append(g.turnCount());
        for (final Player p : g.players) s.append(Arrays.toString(p.getPosition())).append(Arrays.toString(p.getVelocity()))
                .append(Arrays.toString(p.lapState())).append(p.getFinishedPlace());
        return s.toString();
    }
    private static void rule() throws Exception {
        final RaceGame g = game("circle", "contingent,prefix"); g.reach.computeDistMap();
        g.players = new Player[]{car(1,80,71,-1,-3,1,1),car(2,86,46,0,0,0,1),car(3,13,57,0,0,0,1)};
        g.subgamestate=0; g.setQueryTurnCounter(100);
        final String before=live(g);
        final int events=OptimalPotential.remainingEvents(1,1,2);
        final OptimalPotential pot=g.optimalPotential(); check(pot!=null,"fixture lacks exact map");
        final Direction expected=pot.bestMove(g,80,71,-1,-3,events);
        check(expected==Direction.SE,"solo witness changed");
        check(g.ai.computeAiMove()==expected,"20-cell rule still selects non-optimal checkpoint crossing");
        check(before.equals(live(g)),"quiet decision mutated state");
        final Method near=RaceAi.class.getDeclaredMethod("rivalWithinCheb",int.class,int.class,int.class,int.class);
        near.setAccessible(true);
        // Boundary predicate is independent of wall shape. Off-course synthetic
        // positions below are used ONLY to exercise the distance predicate.
        for (final int d : new int[]{19,20,21,39,40,41}) {
            g.players[1].setPosition(new int[]{80+d,71});
            check((boolean)near.invoke(g.ai,80,71,1,20)==(d<=20),"wrong boundary "+d);
        }
        // Exercise the complete policy, not just the predicate, on valid cells
        // at each boundary distance. Far cells must descend the exact potential.
        for (final int distance : new int[]{19,20,21,39,40,41}) {
            boolean found = false;
            for (int x=0;x<=g.gameCols&&!found;x++) for (int y=0;y<=g.gameRows&&!found;y++)
                if (Math.max(Math.abs(x-80),Math.abs(y-71))==distance && g.isMoveLegalGeometryCached(x,y,x,y)) {
                    g.players[1].setPosition(new int[]{x,y});
                    final String audit=g.ai.queryChooserAudit();
                    if(distance>20) check(audit.contains("solo-precedence")&&g.ai.computeAiMove()==expected,"valid far policy "+distance);
                    else check(!audit.contains("solo-precedence"),"near decision misclassified as solo");
                    found=true;
                }
            check(found,"no drivable boundary fixture "+distance);
        }
        g.players[1].setPosition(new int[]{86,46});
        g.players=new Player[]{g.players[0]};
        check(g.ai.computeAiMove()==expected,"same state differs from solo");
    }
    private static void compare() {
        final ChooserResearch.Outcome fast=new ChooserResearch.Outcome(5,false,0,3,"RUNNING");
        final ChooserResearch.Outcome slow=new ChooserResearch.Outcome(7,false,0,3,"RUNNING");
        final ChooserResearch.Outcome second=new ChooserResearch.Outcome(0,true,2,6,"FINISH");
        final ChooserResearch.Outcome third=new ChooserResearch.Outcome(0,true,3,2,"FINISH");
        check(ChooserResearch.dominates(List.of(fast,second),List.of(slow,third)),"dominance lost");
        check(!ChooserResearch.dominates(List.of(fast,slow),List.of(slow,fast)),"crossing models forced a choice");
        check(!ChooserResearch.dominates(List.of(second),List.of(fast)),"terminal mixed with estimate");
        check(!ChooserResearch.dominates(List.of(fast,fast),List.of(fast,fast)),"ties switch");
        final ChooserResearch.Outcome unknown=new ChooserResearch.Outcome(Integer.MAX_VALUE,false,0,3,"RUNNING");
        check(!ChooserResearch.dominates(List.of(fast),List.of(unknown)),"unknown priced as loss");
        final ChooserResearch.Budget b=new ChooserResearch.Budget(2,3); b.move();b.policy();b.policy();
        final List<Boolean> charges=b.since(0);
        final ChooserResearch.Budget cached=new ChooserResearch.Budget(1,3);
        try {cached.replay(charges);throw new AssertionError("replay ignored bound");}
        catch(final ChooserResearch.Limit expected) {check(cached.policies==1&&cached.moves==1,"charge ordering changed");}
    }
    private static void replay(final RaceGame g, final ChooserResearch.Run run) {
        final ChooserResearch.Board b=new ChooserResearch.Board(run.root);
        for(final Object step:run.steps) {
            final java.util.Map<?,?> m=(java.util.Map<?,?>)step;
            final int who=(int)m.get("mover"); final Direction d=Direction.valueOf((String)m.get("action"));
            check(((Number)m.get("turn")).longValue()==b.turns,"trace clock mismatch");
            check(b.step(g,who,d).equals(m.get("status")),"trace/referee mismatch");
        }
        check(b.cars().equals(run.state.cars())&&b.turns==run.state.turns,"trace did not reconstruct final state");
    }
    private static int prefixes() throws Exception {
        int cases=0,savings=0;
        for (final String course:List.of("hairpin","circle")) for(final boolean aware: new boolean[]{false,true}) {
            final RaceGame g=game(course,aware?"setup,aware,prefix":"contingent,prefix");
            if(course.equals("circle")) {
                g.players=new Player[]{car(1,50,8,1,0,0,0),car(2,55,8,1,0,0,1)};
                g.subgamestate=0;g.setQueryTurnCounter(100);
            }
            for(final int focal: new int[]{0,1}) {
                g.subgamestate=focal;
                final String before=live(g);
                final Direction first=g.ai.computeAiMove();
                final int rival=aware?-1:1-focal;
                for(final int horizon: new int[]{2,4}) {
                    final ChooserResearch.Budget originalBudget=new ChooserResearch.Budget(16000,32000);
                    final ChooserResearch.Run original=g.ai.chooserForecast(first,horizon,aware,false,null,true,originalBudget,rival,null,!aware,null);
                    if(original.secondPrefix==null) continue;
                    for(final Direction second:original.secondOptions) {
                        final ChooserResearch.Budget fullBudget=new ChooserResearch.Budget(16000,32000);
                        final ChooserResearch.Run full=g.ai.chooserForecast(first,horizon,aware,false,second,true,fullBudget,rival,null,!aware,null);
                        final ChooserResearch.Budget reusedBudget=new ChooserResearch.Budget(16000,32000);
                        final ChooserResearch.Run reused=g.ai.chooserForecast(first,horizon,aware,false,second,true,reusedBudget,rival,null,!aware,original.secondPrefix);
                        check(full.outcome.equals(reused.outcome),"cached outcome changed");
                        check(full.steps.equals(reused.steps),"cached trace changed");
                        check(full.state.cars().equals(reused.state.cars()),"cached state changed");
                        check(fullBudget.policies==reusedBudget.policies&&fullBudget.moves==reusedBudget.moves,"logical budget changed");
                        check(full.upgrades==reused.upgrades,"policy upgrade count changed");
                        savings+=reusedBudget.reusedPolicies;cases++;replay(g,reused);
                        check(before.equals(live(g)),"forecast polluted live state");
                    }
                    // Replayed charges fail at the same logical point as a full
                    // traversal, even when an upgraded nested policy exhausts it.
                    if (course.equals("hairpin") && focal==0 && horizon==2) {
                        for (final int limit : new int[]{0,1,2,8,32}) {
                            final ChooserResearch.Budget full=new ChooserResearch.Budget(limit,64);
                            final ChooserResearch.Budget cached=new ChooserResearch.Budget(limit,64);
                            boolean fa=false,ca=false;
                            try {g.ai.chooserForecast(first,horizon,aware,false,Direction.NONE,true,full,rival,null,!aware,null);}
                            catch(final ChooserResearch.Limit e){fa=true;}
                            try {g.ai.chooserForecast(first,horizon,aware,false,Direction.NONE,true,cached,rival,null,!aware,original.secondPrefix);}
                            catch(final ChooserResearch.Limit e){ca=true;}
                            check(fa==ca&&full.policies==cached.policies&&full.moves==cached.moves,"budget frontier changed");
                            check(before.equals(live(g)),"failure corrupted root");
                        }
                    }
                    // A prefix is tied to the full clock/board, not just focal position.
                    g.setQueryTurnCounter(g.turnCount()+1);
                    try {g.ai.chooserForecast(first,horizon,aware,false,Direction.NONE,true,new ChooserResearch.Budget(16000,32000),rival,null,!aware,original.secondPrefix);
                        throw new AssertionError("stale prefix accepted");}
                    catch(final IllegalArgumentException expected) { /* fail closed */ }
                    g.setQueryTurnCounter(g.turnCount()-1);
                    try {g.ai.chooserForecast(first,horizon,aware,false,Direction.NONE,true,new ChooserResearch.Budget(16000,32000),rival,Direction.S,!aware,original.secondPrefix);
                        throw new AssertionError("prefix crossed rival-response contexts");}
                    catch(final IllegalArgumentException expected) { /* fail closed */ }
                }
            }
        }
        check(cases>=12&&savings>0,"prefix test exercised no reuse");
        System.out.println("ContingentPrefixTests: "+cases+" full/resumed forecasts identical; "+savings+" scorer calls reused");
        return cases;
    }
    public static void main(final String[] args) throws Exception {
        rule();compare();prefixes();
        System.out.println("ContingentPrefixTests: quiet boundary, Pareto abstention, ledger replay and budget identity OK");
    }
}
