package tr.logic;

import java.awt.Color;
import java.nio.file.Files;
import java.util.Arrays;
import static tr.logic.LifecycleTestSupport.*;

/** Shared engine tested with the repository's non-modal browser dialog transport. */
public final class TimeoutUndoTests {
    private TimeoutUndoTests() {}

    private static RaceGame humans(final int count) throws Exception {
        final Player[] players=new Player[count];
        for (int i=0;i<count;i++) {
            players[i]=new Player("P"+(i+1),i+1,Color.BLUE,Player.Kind.HUMAN);
            players[i].setPosition(new int[]{10+10*i,10}); players[i].setVelocity(new int[]{0,0});
        }
        final RaceGame game=straight(80,players); laps(game,1);
        return game;
    }

    private static String state(final RaceGame game) throws Exception {
        final StringBuilder b=new StringBuilder(game.subgamestate+":"+game.turnCount()+":"+get(game,"gameLog"));
        b.append(get(game,"finishedFirst")).append(get(game,"finishedLast"));
        for (final Player p : game.players) b.append(Arrays.toString(p.getPosition()))
                .append(Arrays.toString(p.getVelocity())).append(p.getFinishedPlace())
                .append(Arrays.toString(p.lapState())).append(p.getHistory().size());
        return b.toString();
    }

    public static void main(final String[] args) throws Exception {
        // Fail rather than silently switch to headless Swing and miss the interactive path.
        Class.forName("tr.browser.JOptionPane");
        final RaceGame game=humans(3); game.setQueryTurnCounter(2249);
        final String p1=state(game); commit(game,Direction.NONE);
        final String p2=state(game); commit(game,Direction.NONE);
        final String p3=state(game); commit(game,Direction.NONE);
        check(game.turnCount()==2252 && game.players[2].getFinishedPlace()==3,"timeout fixture failed");
        game.clickedUndo(); check(p3.equals(state(game)),"Undo skipped the timeout turn");
        commit(game,Direction.NONE); game.clickedUndo(); check(p3.equals(state(game)),"repeat timeout/Undo drift");
        game.clickedUndo(); check(p2.equals(state(game)),"preceding player move not preserved");
        game.clickedUndo(); check(p1.equals(state(game)),"earliest player move not preserved");

        final RaceGame mixed=humans(4); mixed.players[1]=car(2,20,10,0,0);
        mixed.setQueryTurnCounter(3000);
        final String beforeHuman=state(mixed);
        commit(mixed,Direction.NONE); commit(mixed,Direction.NONE); // AI retirement
        mixed.clickedUndo(); check(beforeHuman.equals(state(mixed)),"Undo did not cross the AI timeout correctly");

        final RaceGame declined=humans(3);
        declined.players[0].setPosition(new int[]{10,2}); declined.players[0].setVelocity(new int[]{0,-4});
        final String beforeDecline=state(declined);
        commit(declined,Direction.NONE); // default non-modal consent is NO
        check(beforeDecline.equals(state(declined)),"declining crash committed state");
        check(((java.util.Deque<?>) get(declined,"moveHistory")).isEmpty(),"decline created Undo history");

        final RaceGame terminal=humans(2); terminal.setQueryTurnCounter(1501);
        final var log=Files.createTempFile("timeout-undo-", ".log");
        try {
            terminal.setGameLogPath(log.toString()); commit(terminal,Direction.NONE);
            check(get(terminal,"gamestate")==GameState.FINISHED,"last-rival timeout did not finish");
            final String finished=state(terminal); terminal.clickedUndo();
            check(finished.equals(state(terminal)),"Undo re-opened a finished race");
        } finally { Files.deleteIfExists(log); }

        final RaceGame auto=humans(3); auto.setAutoMode(true); auto.setQueryTurnCounter(2251);
        commit(auto,Direction.NONE);
        check(((java.util.Deque<?>) get(auto,"moveHistory")).isEmpty(),"auto mode retains Undo snapshots");
        System.out.println("TimeoutUndoTests: exact timeout restoration, AI skipping, declined consent, terminal and auto-mode histories OK");
    }
}
