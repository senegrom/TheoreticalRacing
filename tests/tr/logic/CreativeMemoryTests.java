package tr.logic;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
/** Commit-only creative suffixes and large existing response tables. */
public final class CreativeMemoryTests {
    private CreativeMemoryTests() {}
    private static RaceGame fixture() throws Exception {
        final Method method=RacecraftNextTests.class.getDeclaredMethod("straight",String.class,String.class);
        method.setAccessible(true);return (RaceGame)method.invoke(null,"pace-feints","1,2,3");
    }
    private static void set(final Object object,final String name,final Object value) throws Exception {
        final Field f=object.getClass().getDeclaredField(name);f.setAccessible(true);f.set(object,value);
    }
    private static void check(final boolean ok,final String message){if(!ok)throw new AssertionError(message);}
    public static void main(final String[] args) throws Exception {
        final RaceGame game=fixture();
        final FollowupPlans.Entry tail=FollowupPlans.Entry.traffic(List.of(Direction.N,Direction.E),"a".repeat(64));
        set(game.ai,"pendingFirst",Direction.E);set(game.ai,"pendingFollowup",tail);
        set(game.ai,"decisionRootKey",FollowupPlans.key(game));
        game.ai.commitResearchPlan(Direction.E);
        check(game.followups.encode(3).contains("M_N+E~"),"creative-only flag did not commit its suffix");
        final String before=RacecraftReplay.snapshot(game);
        game.ai.computeAiMove();game.ai.computeAiMove();
        check(before.equals(RacecraftReplay.snapshot(game)),"query consumed committed creative memory");
        final RaceGame large=fixture();
        final String original=RacecraftReplay.snapshot(large);final int divider=original.indexOf(';');
        final List<String> nodes=new ArrayList<>();
        for(int i=0;i<256;i++)nodes.add(String.format("%064x_1_1_1",i));
        final String state="rc6"+original.substring(3,divider)+",R_"+String.join("!",nodes)+"~"+"a".repeat(64)+".-.-"+original.substring(divider);
        check(state.length()>17000,"large response fixture too small");
        final String request="cf4,1000,-|"+state;
        final String response=MoveQueries.answer(large,request);
        check(response.contains(RacecraftReplay.sha(request)),"large request was not bound to its response");
        check(original.equals(RacecraftReplay.snapshot(large)),"large replay mutated real policy memory");
        System.out.println("CreativeMemoryTests: creative commit-only suffixes and full-size response-memory captures/replay OK");
    }
}
