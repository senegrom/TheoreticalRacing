package tr.logic;

import java.awt.Color;
import java.awt.geom.Path2D;
import java.awt.geom.Line2D;
import java.lang.reflect.Field;
import java.util.Arrays;
import java.util.Properties;
import java.util.Random;

/** Physical reply checks for the promoted two-move and opt-in three-move proofs. */
public final class RaceAiDuelSearchTests {
    private static final Direction[] DIRECTIONS = Direction.values();
    private static final int[][] SETUPS = {
        {10,14,4,0,12,15,5,0}, {14,15,3,-1,11,16,6,-1},
        {11,18,3,1,9,23,5,-3}, {9,21,5,-1,15,23,2,-3},
        {15,8,2,1,10,13,6,1}, {10,9,4,1,13,14,5,0},
        {9,22,6,1,11,26,5,-1}, {8,23,6,-1,8,21,6,0}
    };
    private static final Direction[] SETUP_MOVES = {
        Direction.N, Direction.N, Direction.W, Direction.SW,
        Direction.S, Direction.E, Direction.SW, Direction.SW
    };

    private RaceAiDuelSearchTests() {}

    public static void main(final String[] args) {
        testSetupProofsAndIsolation();
        testFinishSetupAndRefutation();
        testProgressAndTurnLimit();
        testPhysicalReplies();
        testRandomSoundness();
        testThreeMoveSoundness();
        System.out.println("RaceAiDuelSearchTests: OK (64 setup variants; 12,000 sampled positions)");
    }

    private static RaceGame game(final String candidates) {
        final Properties props = new Properties();
        if (candidates != null)
            props.setProperty("candidateSlots", candidates);
        final RaceGame g = new RaceGame(props);
        g.gameCols = 80;
        g.gameRows = 30;
        g.track = new Track();
        for (final int[] p : new int[][]{{5,27},{3,14},{6,3},{74,3},{77,14},{75,27}})
            g.track.addLeft(p[0], p[1]);
        for (final int[] p : new int[][]{{18,27},{15,16},{19,12},{61,12},{65,16},{62,27}})
            g.track.addRight(p[0], p[1]);
        g.trackA = TrackGeometry.getToleranceExpandedShape(
                TrackGeometry.newPrefilledPath(g.track.getLeft(), g.track.getRight()));
        final float[][] zone = TrackGeometry.makeStartZone(g.track.getLeft().getFirst(),
                g.track.getRight().getFirst());
        final Path2D.Float start = new Path2D.Float();
        start.moveTo(zone[0][0],zone[1][0]);
        for (int i = 1; i < 4; i++) start.lineTo(zone[0][i],zone[1][i]);
        start.closePath();
        g.startZoneA = TrackGeometry.getToleranceExpandedShape(start);
        g.finishLine = new Line2D.Double(75,27,62,27);
        set(g, "finishFwdY", 1.0);
        g.players = new Player[]{car(1, 70,24,0,1), car(2, 40,8,0,0)};
        return g;
    }

    private static Player car(final int number, final int x, final int y, final int vx, final int vy) {
        final Player p = new Player("P" + number, number, Color.BLUE, Player.Kind.AI1);
        p.setPosition(new int[]{x,y});
        p.setVelocity(new int[]{vx,vy});
        return p;
    }

    private static void testSetupProofsAndIsolation() {
        for (int fixture = 0; fixture < SETUPS.length; fixture++) {
            for (final int mover : new int[]{0,1}) {
                for (final int roster : new int[]{2,8}) {
                    for (final Player.Kind kind : new Player.Kind[]{Player.Kind.AI1,Player.Kind.AI2}) {
                        final RaceGame baseline = game(null), candidate = game("" + (mover + 1));
                        final int[] s = SETUPS[fixture];
                        for (final RaceGame g : new RaceGame[]{baseline,candidate}) {
                            g.players = new Player[roster];
                            final Player me = new Player("Me", mover + 1, Color.BLUE, kind);
                            me.setPosition(new int[]{s[0],s[1]});
                            me.setVelocity(new int[]{s[2],s[3]});
                            g.players[mover] = me;
                            g.players[1-mover] = car(2-mover,s[4],s[5],s[6],s[7]);
                            for (int i = 2; i < roster; i++) {
                                g.players[i] = car(i+1,40+i,8,0,0);
                                g.players[i].setFinishedPlace(i+1);
                            }
                            g.subgamestate = mover;
                        }
                        final String before = snapshot(candidate);
                        final Direction selected = RaceAiTactics.winNow(candidate,mover+1);
                        check(selected == SETUP_MOVES[fixture], "setup/slot/kind determinism changed");
                        check(RaceAiTactics.winNow(candidate,mover+1,false)
                                == RaceAiTactics.winNow(baseline,mover+1),
                                "experimental horizon changed a hypothetical champion decision");
                        check(RaceAiTactics.winNow(baseline,mover+1) == selected,
                                "merge removed the promoted two-move tactic");
                        check(winsAfter(candidate,candidate.players[mover],candidate.players[1-mover],
                                selected,0,2), "setup has a refuting reply");
                        // Round 237: these fixtures are TWO-move setups, and that used
                        // to be shown by the gated champion finding nothing here. With
                        // the gate gone, say it directly instead: one own move is not
                        // enough, two are. A fixture that decays into a one-move
                        // knockout would stop testing what it was built to test.
                        check(!winsAfter(candidate,candidate.players[mover],
                                candidate.players[1-mover],selected,0,1),
                                "fixture decayed into a one-move proof");
                        check(before.equals(snapshot(candidate)), "proof mutated live state");
                        // The unselected rival retains the promoted two-move champion;
                        // only a selected real decision may try the extra horizon.
                        check(RaceAiTactics.winNow(candidate,2-mover)
                                == RaceAiTactics.winNow(baseline,2-mover),
                                "three-move candidate leaked to an unselected rival");
                    }
                }
            }
        }
        final RaceGame g = game("1");
        final Player extra = car(3,35,8,0,0);
        g.players = new Player[]{g.players[0],g.players[1],extra};
        check(RaceAiDuelSearch.winWithinTwoMoves(g,1) == null, "proof used with a third live car");
        extra.setFinishedPlace(3);
        check(RaceAiDuelSearch.winWithinTwoMoves(g,1) != null, "retired slot hid a valid duel");
        g.players[0].setFinishedPlace(2);
        check(RaceAiDuelSearch.winWithinTwoMoves(g,1) == null, "retired mover allowed to race");
        check(RaceAiDuelSearch.winWithinTwoMoves(g,9) == null, "absent mover allowed to race");
    }

    private static void testFinishSetupAndRefutation() {
        final RaceGame g = game("1");
        final Direction setup = RaceAiTactics.winNow(g,1);
        check(setup != null && winsAfter(g,g.players[0],g.players[1],setup,0,2),
                "missed a guaranteed second-move finish");
        // Round 237: the gated champion used to stand in for "this is not already
        // an immediate win". State the property itself now that both run the proof.
        check(!winsAfter(g,g.players[0],g.players[1],setup,0,1),
                "finish setup is already immediate");
        // One opponent reply that reaches the flag refutes the whole setup.
        g.players[1] = car(2,66,26,0,0);
        check(RaceAiDuelSearch.winWithinTwoMoves(g,1) == null, "ignored a rival finishing reply");
        // An immediate flag always takes precedence over setting up another move.
        g.players[0] = car(1,70,26,0,4);
        final Direction immediate = RaceAiTactics.winNow(g,1);
        check(immediate != null && move(g,g.players[0],g.players[1],immediate).finishes(),
                "setup stole an immediate win");
    }

    private static void testProgressAndTurnLimit() {
        final RaceGame g = game("1");
        g.lapGates = new Line2D[]{g.finishLine,
                new Line2D.Double(25,3,25,12),new Line2D.Double(65,25,75,25)};
        set(g,"lapCrossGate",g.finishLine);
        set(g,"lapFwdY",1.0);
        g.players[0].setNextGate(2);
        final Direction setup = RaceAiTactics.winNow(g,1);
        check(setup != null && winsAfter(g,g.players[0],g.players[1],setup,0,2),
                "lost checkpoint credit between projected moves");
        g.totalLaps = 2;
        check(RaceAiDuelSearch.winWithinTwoMoves(g,1) == null, "non-final crossing called a win");
        g.totalLaps = 1;
        final int limit = 750*g.players.length;
        g.setQueryTurnCounter(limit-2);
        final Direction atBoundary = RaceAiTactics.winNow(g,1);
        check(atBoundary != null && winsAfter(g,g.players[0],g.players[1],atBoundary,limit-2,2),
                "legal move at the exact turn boundary was rejected");
        g.setQueryTurnCounter(limit-1);
        check(RaceAiDuelSearch.winWithinTwoMoves(g,1) == null,
                "promised a second move after our own timeout");
        g.setQueryTurnCounter(limit);
        final Direction last = RaceAiTactics.winNow(g,1);
        check(last != null && winsAfter(g,g.players[0],g.players[1],last,limit,2),
                "missed rival retirement on the next turn");
        g.setQueryTurnCounter(limit+1);
        check(RaceAiDuelSearch.winWithinTwoMoves(g,1) == null, "current timeout ignored");
        g.setQueryTurnCounter(Integer.MAX_VALUE);
        check(RaceAiDuelSearch.winWithinTwoMoves(g,1) == null, "query clock overflowed");
    }

    private static void testPhysicalReplies() {
        final RaceGame g = game("1");
        g.players[0] = car(1,64,6,-3,5);
        final Player human = new Player("Human",2,Color.RED,Player.Kind.HUMAN);
        human.setPosition(new int[]{72,23});
        human.setVelocity(new int[]{-12,-12});
        g.players[1] = human;
        int physical = 0, bounded = 0;
        for (final Direction d : DIRECTIONS) {
            if (move(g,human,g.players[0],d).legal()) {
                physical++;
                if (!RaceGame.aiVelocityOutOfRange(-12+d.dx,-12+d.dy))
                    bounded++;
            }
        }
        check(physical == 3 && bounded == 1, "physical-reply boundary fixture changed");
        final Direction selected = RaceAiTactics.winNow(g,1);
        check(selected == null || winsAfter(g,g.players[0],human,selected,0,2),
                "human reply beyond the planning cap refutes the proof");
    }

    private static void testRandomSoundness() {
        final RaceGame g = game("1");
        final Random random = new Random(20260911);
        int proofs = 0, setups = 0, valid = 0;
        for (int trial = 0; trial < 12000; trial++) {
            final int x = 4+random.nextInt(73), y = 4+random.nextInt(23);
            g.players[0] = car(1,x,y,random.nextInt(27)-13,random.nextInt(27)-13);
            g.players[1] = car(2,x+random.nextInt(13)-6,y+random.nextInt(13)-6,
                    random.nextInt(27)-13,random.nextInt(27)-13);
            if (!onTrack(g,g.players[0]) || !onTrack(g,g.players[1])
                    || Arrays.equals(g.players[0].getPosition(),g.players[1].getPosition()))
                continue;
            valid++;
            final String before = snapshot(g);
            final Direction selected = RaceAiDuelSearch.winWithinTwoMoves(g,1);
            check(before.equals(snapshot(g)), "random probe mutated its board");
            if (selected != null) {
                check(winsAfter(g,g.players[0],g.players[1],selected,g.turnCount(),2),
                        "random proof has a physical counterexample at trial " + trial);
                proofs++;
                if (!winsAfter(g,g.players[0],g.players[1],selected,g.turnCount(),1))
                    setups++;
            }
        }
        check(proofs > 20 && setups > 0, "random soundness checks were vacuous");
        System.out.println("Random duel checks: " + valid + " valid boards, " + proofs
                + " certificates, " + setups + " requiring a second own move");
    }

    private static void testThreeMoveSoundness() {
        final RaceGame g = game("1");
        final Random random = new Random(20260912);
        int valid = 0, proofs = 0, additional = 0;
        for (int trial = 0; trial < 2500; trial++) {
            final int x = 4 + random.nextInt(73), y = 4 + random.nextInt(23);
            g.players[0] = car(1,x,y,random.nextInt(27)-13,random.nextInt(27)-13);
            g.players[1] = car(2,x+random.nextInt(13)-6,y+random.nextInt(13)-6,
                    random.nextInt(27)-13,random.nextInt(27)-13);
            if (!onTrack(g,g.players[0]) || !onTrack(g,g.players[1])
                    || Arrays.equals(g.players[0].getPosition(),g.players[1].getPosition())) continue;
            valid++;
            final String before = snapshot(g);
            final Direction old = RaceAiDuelSearch.winWithinTwoMoves(g,1);
            final Direction selected = RaceAiDuelSearch.winWithinThreeMoves(g,1);
            check(before.equals(snapshot(g)), "three-move proof mutated its board");
            if (old != null) check(selected == old, "deeper search changed an earlier certificate");
            if (selected == null) continue;
            check(winsAfter(g,g.players[0],g.players[1],selected,0,3),
                    "three-move certificate has a physical refutation at trial " + trial);
            proofs++;
            if (old == null) {
                check(RaceAiTactics.winNow(g,1) == selected,
                        "additional certificate not reachable from the production tactic");
                check(RaceAiTactics.winNow(g,1,false) == null,
                        "three-move-only certificate leaked into a nested decision");
                final RaceGame champion = game(null);
                champion.players = g.players;
                check(RaceAiTactics.winNow(champion,1) != null,
                        "round 239: the default champion must take the three-move certificate too");
                additional++;
                if (additional <= 3) System.out.println("Additional three-move witness: "
                        + snapshot(g) + " via " + selected);
            }
        }
        check(additional > 0, "three-move search adds no verified certificates");
        System.out.println("Three-move checks: " + valid + " valid, " + proofs
                + " certificates, " + additional + " beyond two moves");
    }

    /** Slow independent verifier: replay each branch into detached PLAYERS,
     * advancing the referee's complete lap ledger, with no solver calls.
     */
    private static boolean winsAfter(final RaceGame g, final Player me, final Player rival,
            final Direction d, final long turn, final int ownMoves) {
        if (timeout(g,turn) || RaceGame.aiVelocityOutOfRange(
                me.getVelocity()[0]+d.dx,me.getVelocity()[1]+d.dy))
            return false;
        final RaceGame.MoveResult ours = move(g,me,rival,d);
        if (!ours.legal()) return false;
        if (ours.finishes() || timeout(g,turn+1)) return true;
        final Player after = advance(me,d,ours);
        for (final Direction reply : DIRECTIONS) {
            final RaceGame.MoveResult theirs = move(g,rival,after,reply);
            if (theirs.finishes()) return false;
            if (!theirs.legal()) continue;
            if (ownMoves == 1) return false;
            final Player opponent = advance(rival,reply,theirs);
            boolean answered = false;
            for (final Direction follow : DIRECTIONS) {
                if (winsAfter(g,after,opponent,follow,turn+2,ownMoves-1)) {
                    answered = true;
                    break;
                }
            }
            if (!answered) return false;
        }
        return true;
    }

    private static boolean timeout(final RaceGame g, final long turn) {
        return g.lapGates != null && turn > (long) g.totalLaps*750*g.players.length;
    }

    private static RaceGame.MoveResult move(final RaceGame g, final Player p,
            final Player blocker, final Direction d) {
        final int[] pos = p.getPosition(), vel = p.getVelocity(), other = blocker.getPosition();
        final int x = pos[0]+vel[0]+d.dx, y = pos[1]+vel[1]+d.dy;
        return g.evaluateMove(p.getLap(),p.getNextGate(),pos[0],pos[1],x,y,
                x == other[0] && y == other[1]);
    }

    private static Player advance(final Player p, final Direction d, final RaceGame.MoveResult move) {
        final int[] v = p.getVelocity(), pos = p.getPosition();
        final Player copy = car(p.getNumber(),pos[0]+v[0]+d.dx,pos[1]+v[1]+d.dy,
                v[0]+d.dx,v[1]+d.dy);
        final int[] ledger = p.lapState();
        ledger[0] = move.lapAfter();
        ledger[1] = move.gateAfter();
        copy.restoreLapState(ledger);
        return copy;
    }

    private static boolean onTrack(final RaceGame g, final Player p) {
        final int[] pos = p.getPosition();
        return g.isMoveLegalGeometry(pos[0],pos[1],pos[0],pos[1]);
    }

    private static String snapshot(final RaceGame g) {
        final StringBuilder s = new StringBuilder().append(g.turnCount()).append('/').append(g.subgamestate);
        for (final Player p : g.players)
            s.append(Arrays.toString(p.getPosition())).append(Arrays.toString(p.getVelocity()))
                    .append(Arrays.toString(p.lapState())).append(p.getFinishedPlace())
                    .append(Arrays.deepToString(p.getHistory().toArray()));
        return s.toString();
    }

    private static void set(final RaceGame g, final String name, final Object value) {
        try {
            final Field field = RaceGame.class.getDeclaredField(name);
            field.setAccessible(true);
            field.set(g,value);
        } catch (final ReflectiveOperationException e) {
            throw new AssertionError(e);
        }
    }

    private static void check(final boolean condition, final String message) {
        if (!condition) throw new AssertionError(message);
    }
}
