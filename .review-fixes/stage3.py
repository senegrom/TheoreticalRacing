from pathlib import Path
import re
p=Path('src/tr/logic/RaceAi.java'); s=p.read_text()
if 'private Direction rankedRescue(' not in s:
    anchor='''		if (trueDead && best != null) {
'''
    assert anchor in s
    s=s.replace(anchor,'''        if (trueDead && best != null && nextEnabled(playerNum, RacecraftNext.Feature.RANK_TIME))
            return rankedRescue(pos, vel, playerNum, chosen, simFinishVanish, exactSelf, exactRivals,
                    scorerRivals, scorerSelf, rounds, scorerCap);
'''+anchor,1)
    s=s.replace('''            final boolean rankRescue = nextEnabled(playerNum, RacecraftNext.Feature.RANK_TIME);
            int confirmedKey = Integer.MAX_VALUE;
''','')
    s=s.replace('(rankRescue || confirmed == null)', 'confirmed == null')
    s=s.replace('''t >= 0 && (!rankRescue || t != Integer.MAX_VALUE) && (rankRescue
                            ? t < candT || t == candT && spd < candSpd
                            : spd < candSpd || spd == candSpd && t < candT)''','''t >= 0 && (spd < candSpd || spd == candSpd && t < candT)''')
    a=s.index('                if (rankRescue) {'); b=s.index('\n\t\t\t}',a)
    s=s[:a]+'''                if (survives) confirmed = cand;
                else rejected[cand.ordinal()] = true;'''+s[b:]
    idx=s.index('\n\tprivate final static double\tAI2_MOMENTUM_TIEBREAK')
    s=s[:idx]+'''
    /** All admitted alternatives pass both existing confirmation worlds before selection. */
    private Direction rankedRescue(final int[] pos, final int[] vel, final int playerNum,
            final Direction chosen, final boolean vanish, final boolean exactSelf, final boolean exactRivals,
            final boolean scorerRivals, final boolean scorerSelf, final int rounds, final int cap) {
        final Direction selected = ConfirmedMoves.choose(DIRECTIONS, d -> {
            if (d == chosen) return RacecraftOutcome.unknown();
            final int vx = vel[0]+d.dx, vy = vel[1]+d.dy, x = pos[0]+vx, y = pos[1]+vy;
            if (RaceGame.aiVelocityOutOfRange(vx,vy) || !game.aiMoveLegal(pos[0],pos[1],x,y)
                    || game.isCrashingPlayer(x,y,playerNum) || !reach.isAlive(x,y,vx,vy))
                return RacecraftOutcome.unknown();
            final int proposal = simOutcome(x,y,vx,vy,playerNum,rounds,vanish,exactSelf,exactRivals,
                    scorerRivals,scorerSelf,cap,null);
            if (!researchSurvives(proposal)) return RacecraftOutcome.unknown();
            trueConfirmDepth++;
            try {
                if (!researchSurvives(simOutcome(x,y,vx,vy,playerNum,AI1_DEEP_HORIZON,
                        vanish,exactSelf,exactRivals,true,scorerSelf,false,
                        Math.max(cap,AI1_DEEP_CERT_RIVALS),null,null,null))) return RacecraftOutcome.unknown();
                if (!researchSurvives(simOutcome(x,y,vx,vy,playerNum,AI1_TRUE_CONFIRM_ROUNDS,
                        vanish,exactSelf,exactRivals,true,scorerSelf,true,
                        Math.max(cap,AI1_DEEP_CERT_RIVALS),null,null,null))) return RacecraftOutcome.unknown();
                return lastResearchOutcome;
            } finally { trueConfirmDepth--; }
        });
        return selected == null ? chosen : selected;
    }
'''+s[idx:]
    # Keep the projected log clock consistent with the atomic real timeout event.
    s=s.replace('''        if (rank > 0 || game.players.length == 1) w.researchOwnMoves++;''','''        w.turns += order.length - (game.players.length == 1 ? 0 : 1);
        if (rank > 0 || game.players.length == 1) w.researchOwnMoves++;''')
    p.write_text(s)
p=Path('tests/tr/logic/SimulationBoundaryTests.java'); s=p.read_text()
s=s.replace('projectedClock(g) == g.turnCount() && field[0] == 0', 'projectedClock(g) == g.turnCount() + 2L && field[0] == 0')
p.write_text(s)
p=Path('tests/tr/logic/RaceAiDuelSearchTests.java'); s=p.read_text()
if 'timeoutProgressWin' not in s:
    s=s.replace('''        if (timeout(g,turn) || RaceGame.aiVelocityOutOfRange(''','''        if (timeout(g,turn)) return timeoutProgressWin(g,me,rival,true);
        if (RaceGame.aiVelocityOutOfRange(''')
    s=s.replace('''        if (ours.finishes() || timeout(g,turn+1)) return true;
        final Player after = advance(me,d,ours);''','''        if (ours.finishes()) return true;
        final Player after = advance(me,d,ours);
        if (timeout(g,turn+1)) return timeoutProgressWin(g,after,rival,false);''')
    idx=s.index('    private static boolean timeout(')
    s=s[:idx]+'''    private static boolean timeoutProgressWin(final RaceGame g, final Player me, final Player rival,
            final boolean ownTurn) {
        return RaceTimeout.progress(g,me,ownTurn?0:1).compareTo(RaceTimeout.progress(g,rival,ownTurn?1:0))<0;
    }

'''+s[idx:]
    s=s.replace('''        check(RaceAiDuelSearch.winWithinTwoMoves(g,1) == null,
                "promised a second move after our own timeout");''','''        final Direction progressWin=RaceAiDuelSearch.winWithinTwoMoves(g,1);
        check(progressWin != null && winsAfter(g,g.players[0],g.players[1],progressWin,limit-1,2),
                "lost a progress-classified win without promising another move");''')
    p.write_text(s)
p=Path('tests/tr/logic/RacecraftFixTests.java'); s=p.read_text()
if 'confirmationSelection();' not in s:
    s=s.replace('        openingCoverage();','        openingCoverage();\n        confirmationSelection();')
    idx=s.index('    private static Direction chooser(')
    s=s[:idx]+'''    private static void confirmationSelection() {
        final List<Direction> visited=new ArrayList<>();
        final Direction result=ConfirmedMoves.choose(new Direction[]{Direction.N,Direction.SE,Direction.W},d->{
            visited.add(d);
            if(d==Direction.W)return RacecraftOutcome.unknown();
            return new RacecraftOutcome(RacecraftOutcome.Status.FINISHED,d==Direction.N?1:0,
                    d==Direction.N?1:9,0);
        });
        check(result==Direction.SE && visited.size()==3,"first slower survivor outranked a later winning confirmation");
        check(ConfirmedMoves.choose(new Direction[]{Direction.N,Direction.SE},d->
                new RacecraftOutcome(RacecraftOutcome.Status.FINISHED,0,d==Direction.N?5:2,0))==Direction.SE,
                "same-place confirmed finishes lost their elapsed time");
        check(ConfirmedMoves.choose(new Direction[]{Direction.N},d->RacecraftOutcome.unknown())==null,
                "unknown confirmation selected an action");
    }

'''+s[idx:]; p.write_text(s)
p=Path('run_tests.sh'); s=p.read_text()
if 'tr.logic.RacecraftFixTests' not in s:
    p.write_text(s+'\njava -ea -Djava.awt.headless=true -cp test-bin tr.logic.RacecraftFixTests\n')
