from pathlib import Path
import re
p=Path('src/tr/logic/RacecraftReplay.java'); s=p.read_text()
if 'static List<String> expire(' not in s:
    s=s.replace('racecraft-rc3-v1;', 'racecraft-rc3-v2-progress-timeout;')
    idx=s.index('    private static boolean classifyLast(')
    s=s[:idx]+'''    /** Atomic timeout event. Rank first, then log/retire worst-first exactly as the referee. */
    static List<String> expire(final RaceGame game) {
        if (!game.raceTurnLimitReached()) throw new IllegalStateException("race has not timed out");
        final int[] order = RaceTimeout.order(game);
        final List<String> trace = new ArrayList<>();
        int last = game.researchFinishedLast();
        final int survivors = game.players.length == 1 ? 0 : 1;
        for (int k = order.length - 1; k >= survivors; k--) {
            final int slot = order[k]; final Player p = game.players[slot];
            final int[] x = p.getPosition(), v = p.getVelocity();
            p.setFinishedPlace(game.players.length - last++);
            game.setQueryTurnCounter(game.turnCount() + 1);
            trace.add(slot + ":NONE:" + x[0] + ":" + x[1] + ":" + v[0] + ":" + v[1]
                    + ":TIMEOUT:" + p.getFinishedPlace() + ":" + p.getLap() + ":" + p.getNextGate()
                    + ":" + (p.hasLeftGrid() ? 1 : 0) + ":" + game.turnCount());
            p.logPosition(x); p.setPosition(new int[]{Player.INIT_POS, Player.INIT_POS});
            p.setVelocity(new int[]{0, 0});
        }
        game.researchClassification(game.researchFinishedFirst(), last);
        classifyLast(game);
        return trace;
    }

    static List<Direction> legalActions(final RaceGame game) {
        final List<Direction> legal = new ArrayList<>();
        if (game.raceTurnLimitReached()) return legal;
        final Player p = game.players[game.subgamestate];
        final int[] x = p.getPosition(), v = p.getVelocity();
        for (final Direction d : Direction.values()) {
            if (!RaceGame.aiVelocityOutOfRange(v[0] + d.dx, v[1] + d.dy)
                    && game.evaluateMove(p, x, new int[]{x[0]+v[0]+d.dx, x[1]+v[1]+d.dy}).legal()) legal.add(d);
        }
        return List.copyOf(legal);
    }

    static String legalActionText(final RaceGame game) {
        return String.join(",", legalActions(game).stream().map(Enum::name).toList());
    }

'''+s[idx:]
    s=s.replace('        final boolean timeout = game.raceTurnLimitReached();', '''        if (game.raceTurnLimitReached()) throw new IllegalStateException("use atomic expire for timeout");
        final boolean timeout = false;''')
    old='''                final Direction action = game.raceTurnLimitReached() ? Direction.NONE
                        : firstAction && first != null ? first'''
    new='''                if (game.raceTurnLimitReached()) {
                    int live = 0;
                    for (final Player p : game.players) if (!p.isFinished()) live++;
                    final int events = live - (game.players.length == 1 ? 0 : 1);
                    if (events > maxMoves - step) break; // never partially apply an atomic classification
                    final List<String> expired = expire(game);
                    for (final String row : expired) if (row.startsWith(self + ":")) {
                        own++; focalStatus = RacecraftOutcome.Status.TIMED_OUT;
                    }
                    if (focalStatus == RacecraftOutcome.Status.RUNNING) focalStatus = RacecraftOutcome.Status.CLASSIFIED;
                    trace.addAll(expired); complete = true; break;
                }
                final Direction action = firstAction && first != null ? first'''
    assert old in s; s=s.replace(old,new)
    s=s.replace('/** cf3,', '/** cf4,').replace('cf3 request','cf4 request').replace('cf3 requires','cf4 requires').replace('cf3 bound','cf4 bound')
    s=s.replace('if (h.length != 3)', 'if (h.length != 3 || !h[0].equals("cf4"))')
    old='''        final StringBuilder json = new StringBuilder("{\\"schema\\":3,\\"baseline\\":\\"").append(actual)'''
    new='''        final List<Direction> legal;
        try (Scope ignored = new Scope(game, root)) { legal = legalActions(game); }
        final StringBuilder json = new StringBuilder("{\\"schema\\":4,\\"requestSha256\\":\\"")
                .append(sha(line)).append("\\",\\"maxMoves\\":").append(bound)
                .append(",\\"legalActions\\":[");
        for (int k = 0; k < legal.size(); k++) {
            if (k > 0) json.append(','); json.append('"').append(legal.get(k)).append('"');
        }
        json.append("],\\"baseline\\":\\"").append(actual)'''
    assert old in s; s=s.replace(old,new)
    a=s.index('            final boolean legal;'); b=s.index('            final Tail result =',a)
    s=s[:a]+'''            final boolean isLegal = legal.contains(d);
            if (!isLegal && d != actual) continue;
'''+s[b:]
    s=s.replace('.append(legal)\n', '.append(isLegal)\n')
    p.write_text(s)
    p=Path('src/tr/logic/MoveQueries.java'); p.write_text(p.read_text().replace('line.startsWith("cf3,")','line.startsWith("cf4,")'))
    p=Path('tests/tr/logic/RacecraftNextTests.java'); p.write_text(p.read_text().replace('cf3,','cf4,'))
    p=Path('src/tr/logic/RaceAi.java'); s=p.read_text()
    s=s.replace('final String snapshot = capture ? RacecraftReplay.snapshot(game) : null;', '''final String snapshot = capture ? RacecraftReplay.snapshot(game) : null;
        final String legalActions = capture ? RacecraftReplay.legalActionText(game) : null;''')
    s=s.replace('+ "|" + auditScorer + "|" + auditChooser + "|" + auditOpening + "|" + auditShortlist);', '+ "|" + auditScorer + "|" + auditChooser + "|" + auditOpening + "|" + auditShortlist + "|" + legalActions);')
    p.write_text(s)
p=Path('src/tr/logic/RaceAi.java'); s=p.read_text()
if 'private java.util.List<Direction> openingFollowups' not in s:
    s=s.replace('    private int researchOpeningTrials;', '''    private int researchOpeningTrials;
    private java.util.List<Direction> openingFollowups = java.util.List.of();''')
    s=s.replace('        researchOpeningTrials++;', '        researchOpeningTrials++;\n        openingFollowups = java.util.List.of();')
    a=s.index('    private Direction openingSearch('); b=s.index('\n\t/** Round 262:',a)
    s=s[:a]+'''    private Direction openingSearch(final int[] pos, final int[] vel, final int player,
            final Direction nominal, final Direction[] order, final int width) {
        researchOpeningTrials = 0;
        final OpeningPlans.Selection result = OpeningPlans.choose(nominal,
                java.util.Arrays.copyOf(order, width), game.racecraftNext.openingTrials,
                nextEnabled(player, RacecraftNext.Feature.CRASH_RANK), (first, second) -> {
                    final RacecraftOutcome value = researchForecast(pos, vel, player, first,
                            game.racecraftNext.openingRounds, second);
                    return new OpeningPlans.Trial(value, openingFollowups);
                });
        return result.move();
    }

    /** Legal second actions, priced in the successor's progress frame. */
    private java.util.List<Direction> openingSecondActions(final RolloutWorkspace w, final int i) {
        final int[] turns = new int[DIRECTIONS.length];
        java.util.Arrays.fill(turns, -1);
        for (final Direction d : DIRECTIONS) {
            final int vx = w.vx[i] + d.dx, vy = w.vy[i] + d.dy;
            if (RaceGame.aiVelocityOutOfRange(vx, vy)) continue;
            final int x = w.px[i] + vx, y = w.py[i] + vy;
            final RaceGame.MoveResult next = game.evaluateMove(w.laps[i], w.gates[i], w.px[i], w.py[i],
                    x, y, occupiedByOther(x, y, i, w.px, w.py, w.alive));
            if (!next.legal()) continue;
            turns[d.ordinal()] = next.finishes() ? 0 : exactPot != null
                    ? exactPot.movesToFinish(OptimalPotential.remainingEvents(next.gateAfter(), next.lapAfter(),
                            game.totalLaps), x, y, vx, vy)
                    : game.lapGates == null ? reach.turnsToFinish(x,y,vx,vy)
                    : reach.turnsToGate(next.gateAfter(),x,y,vx,vy);
        }
        return OpeningPlans.ordered(turns, w.vx[i], w.vy[i]);
    }
'''+s[b:]
    needle='''				boolean moved;
                if (i == myIdx && simDepth == forcedSecondDepth'''
    assert needle in s
    s=s.replace(needle,'''                if (i == myIdx && simDepth == forcedSecondDepth && forcedSecond == null
                        && workspace.researchOwnMoves == 2) openingFollowups = openingSecondActions(workspace, i);
				boolean moved;
                if (i == myIdx && simDepth == forcedSecondDepth''')
    # Old deep solver does not carry progress in its key; abstention is the only sound timeout verdict.
    s=re.sub(r'if \(endgameTimedOut\(depth\)\)\s*return true;', 'if (endgameTimedOut(depth))\n            return false; // no progress frame: abstain, never claim a timeout win',s)
    p.write_text(s)
# Retain all existing non-timeout regressions; replace the now-obsolete mover-first timeout expectations.
p=Path('tests/tr/logic/SimulationBoundaryTests.java'); s=p.read_text()
if 'progressTimeout' not in s:
    s=s.replace('''                // Round 274, rank first: a survivor''','''                final boolean progressTimeout = kind == 2;
                if (progressTimeout) {
                    // Every next-gate value is unknown on this fixture. Cyclic order starts
                    // AFTER the installed mover, so that mover is third, not the survivor.
                    check(value == 2 * RaceAi.VERDICT_PLACE_STRIDE && tier[0] == 3,
                            "timeout did not use projected cyclic progress order");
                    check(projectedClock(g) == g.turnCount() && field[0] == 0,
                            "timeout invented a racing move or future field cost");
                    continue;
                }
                // Round 274, rank first: a survivor''')
    s=s.replace('''null, null, null) == -1,
                "candidate finish overrode mover-first timeout"''','''null, null, null) == 0,
                "timeout did not classify the current cyclic-first car without moving"''')
    p.write_text(s)
p=Path('tests/tr/logic/EndgamePhysicalTests.java'); s=p.read_text()
s=s.replace('''check((boolean) rivalNode.invoke(ai, 61, 7, 11, 0, 60, 13, 12, 0, 19),
                "rival timeout must precede its otherwise finishing acceleration");''','''check(!(boolean) rivalNode.invoke(ai, 61, 7, 11, 0, 60, 13, 12, 0, 19),
                "progress-blind deep solver fabricated a timeout win");'''); p.write_text(s)
