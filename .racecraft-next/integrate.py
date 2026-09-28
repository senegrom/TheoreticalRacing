"""One-shot integration on pinned master 9550011; removed after validation."""
from pathlib import Path


def once(text, before, after):
    assert text.count(before) == 1, (text.count(before), before[:140])
    return text.replace(before, after, 1)

p = Path('src/tr/logic/RaceGame.java')
s = p.read_text()
s = once(s, '\tprivate final boolean[] candidateSlots;', '''\tprivate final boolean[] candidateSlots;
    final RacecraftNext racecraftNext;
    boolean racecraftReplay;

    int researchFinishedFirst() { return finishedFirst; }
    int researchFinishedLast() { return finishedLast; }
    void researchClassification(final int first, final int last) {
        finishedFirst = first; finishedLast = last;
    }
    String researchFinishIdentity() { return finishFwdX + "," + finishFwdY + ":" + lapIdentity(); }
''')
s = once(s, '\t\tcandidateSlots = parseCandidateSlots(prop.getProperty("candidateSlots"), maxPlayers);', '\t\tcandidateSlots = parseCandidateSlots(prop.getProperty("candidateSlots"), maxPlayers);\n        racecraftNext = new RacecraftNext(prop);')
p.write_text(s)

p = Path('src/tr/logic/RaceAi.java')
s = p.read_text()
s = once(s, '\t\tint turns;\n', '\t\tint turns;\n        int researchOwnMoves;\n        boolean researchDetail;\n        RacecraftOutcome researchOutcome;\n')
s = once(s, '\tprivate int\t\t\t\t\t\tsimDepth;', '''\tprivate int\t\t\t\t\t\tsimDepth;
    private RacecraftOutcome lastResearchOutcome;
    private int researchDemandDepth = -1;
    private int forcedSecondDepth = -1;
    private Direction forcedSecond;
    private int capturedDecisions;
    private Direction auditScorer, auditChooser, auditOpening;
    private String auditShortlist = "";

    /** Isolated cheap continuation policy used by the placement experiment. */
    Direction researchScorer() {
        final boolean old = inScorerSim;
        inScorerSim = true;
        try { return computeAiMove(); }
        finally { inScorerSim = old; }
    }

    private boolean nextEnabled(final int player, final RacecraftNext.Feature feature) {
        return game.racecraftNext.enabled(game, player, feature);
    }

    private void recordResearch(final RolloutWorkspace w, final RacecraftOutcome.Status status,
            final int ahead, final int remaining) {
        if (w.researchDetail)
            w.researchOutcome = new RacecraftOutcome(status, ahead, w.researchOwnMoves, remaining);
    }

    private boolean researchFinishes(final int legacy) {
        return lastResearchOutcome == null ? legacy >= 0 && legacy % VERDICT_PLACE_STRIDE == 0
                : lastResearchOutcome.successful();
    }
''')
s = once(s, '\t\treturn optimalMoveAI1(pos, vel, playerNum);', '''        final boolean root = simDepth == 0 && !inScorerSim;
        final boolean capture = root && !game.racecraftReplay && game.racecraftNext.capture
                && capturedDecisions < game.racecraftNext.captureLimit
                && game.turnCount() % game.racecraftNext.captureEvery == 0;
        final String snapshot = capture ? RacecraftReplay.snapshot(game) : null;
        if (root) { auditScorer = null; auditChooser = null; auditOpening = null; auditShortlist = ""; }
        final Direction decision = optimalMoveAI1(pos, vel, playerNum);
        if (capture) {
            capturedDecisions++;
            System.err.println("RACECRAFT_STATE " + snapshot + "|" + decision
                    + "|" + auditScorer + "|" + auditChooser + "|" + auditOpening + "|" + auditShortlist);
        }
        return decision;''')
s = once(s, '\t\tprepareDecisionFrame(pos, vel, playerNum);\n\t\tfinal Direction tacticalWin', '''\t\tprepareDecisionFrame(pos, vel, playerNum);
        // Candidate experiments obey the literal solo rule even before a duel tactic.
        // The equivalent master rule correction is independently queued as round 294.
        if (game.racecraftNext.any(game, playerNum)
                && !rivalWithinCheb(pos[0], pos[1], playerNum, AI1_CHOOSER_MAXDIST)) {
            final Direction solo = optimalAloneMove(pos, vel, playerNum);
            if (solo != null) return solo;
        }
\t\tfinal Direction tacticalWin''')
# Convert the simulator's return only after its own depth-owned result is complete.
s = once(s, '\t\t\treturn simOutcomeCore(myX, myY, myVx, myVy, playerNum, rounds, simFinishVanish,', '\t\t\tfinal int legacy = simOutcomeCore(myX, myY, myVx, myVy, playerNum, rounds, simFinishVanish,')
s = once(s, '\t\t\t\t\toutRivalCost, candidatePending);\n\t\t} finally {', '''\t\t\t\t\toutRivalCost, candidatePending);
            lastResearchOutcome = workspace.researchOutcome;
            return nextEnabled(playerNum, RacecraftNext.Feature.RANK_TIME) && lastResearchOutcome != null
                    ? lastResearchOutcome.liveVerdict() : legacy;
\t\t} finally {''')
s = once(s, '\t\tworkspace.turns = game.turnCount();\n', '''\t\tworkspace.turns = game.turnCount();
        workspace.researchOutcome = null;
        workspace.researchOwnMoves = candidatePending ? 1 : 0;
        workspace.researchDetail = game.racecraftNext.any(game, playerNum)
                || game.racecraftNext.capture || simDepth == researchDemandDepth;
''')
# Candidate retirement and terminal finish.
s = once(s, '\t\t\tif (game.raceTurnLimitReached())\n\t\t\t\treturn -1;', '''\t\t\tif (game.raceTurnLimitReached()) {
                recordResearch(workspace, RacecraftOutcome.Status.CRASHED, liveCount - 1, 0);
                return -1;
            }''')
s = once(s, '\t\t\tif (!candidate.legal())\n\t\t\t\treturn -1;', '''\t\t\tif (!candidate.legal()) {
                recordResearch(workspace, RacecraftOutcome.Status.CRASHED, liveCount - 1, 0);
                return -1;
            }''')
s = once(s, '\t\t\tif (candidate.finishes() && simFinishVanish) {', '''\t\t\tif (candidate.finishes() && simFinishVanish) {
                recordResearch(workspace, RacecraftOutcome.Status.FINISHED, 0, 0);''')
s = once(s, '\t\t\t\tusePlayerFrame(i);\n\t\t\t\tif (outRivalCost', '\t\t\t\tusePlayerFrame(i);\n                if (i == myIdx) workspace.researchOwnMoves++;\n\t\t\t\tif (outRivalCost')
s = once(s, '\t\t\t\tboolean moved;\n\t\t\t\tif (i == myIdx)', '''\t\t\t\tboolean moved;
                if (i == myIdx && simDepth == forcedSecondDepth && forcedSecond != null
                        && workspace.researchOwnMoves == 2) {
                    final int nvx = vx[i] + forcedSecond.dx, nvy = vy[i] + forcedSecond.dy;
                    final int nx = px[i] + nvx, ny = py[i] + nvy;
                    final RaceGame.MoveResult trial = game.evaluateMove(workspace.laps[i], workspace.gates[i],
                            px[i], py[i], nx, ny, occupiedByOther(nx, ny, i, px, py, alive));
                    if (RaceGame.aiVelocityOutOfRange(nvx, nvy) || !trial.legal()) {
                        workspace.researchOutcome = RacecraftOutcome.unknown();
                        return -1; // an inadmissible forced continuation is not a forecasted retirement
                    }
                    moved = writeMove(move, nx, ny, nvx, nvy);
                } else if (i == myIdx)''')
s = once(s, '\t\t\t\t\t\tmyFinishRound = round;\n', '''\t\t\t\t\t\tmyFinishRound = round;
                        recordResearch(workspace, RacecraftOutcome.Status.FINISHED, rivalsFinished, 0);
''')
s = once(s, '\t\t\t\t\tif (i == myIdx)\n\t\t\t\t\t\treturn -1;', '''\t\t\t\t\tif (i == myIdx) {
                        recordResearch(workspace, RacecraftOutcome.Status.CRASHED,
                                RacecraftOutcome.retirementAhead(liveCount, rivalsFinished), 0);
                        return -1;
                    }''')
s = once(s, '\t\t\t\t\tmyFinishRound = endRound;\n', '''\t\t\t\t\tmyFinishRound = endRound;
                    recordResearch(workspace, RacecraftOutcome.Status.CLASSIFIED, rivalsFinished, 0);
''')
s = once(s, '\t\tfinal int myTime = myFinished ? 0 : ttf(px[myIdx], py[myIdx], vx[myIdx], vy[myIdx]);', '''\t\tfinal int myTime = myFinished ? 0 : ttf(px[myIdx], py[myIdx], vx[myIdx], vy[myIdx]);
        if (!myFinished) recordResearch(workspace, RacecraftOutcome.Status.RUNNING, rivalsFinished, myTime);''')
# Finish certificates must ask status, not infer it from a time digit.
suffix = ' % VERDICT_PLACE_STRIDE != 0'
assert s.count(suffix) == 2, s.count(suffix)
while suffix in s:
    end = s.index(suffix)
    start = s.rfind('simOutcome(', 0, end)
    assert start >= 0
    s = s[:start] + '!researchFinishes(' + s[start:end] + ')' + s[end + len(suffix):]
# Keep the fast/slow trigger's units as remaining distance.
needle = '\t\t\t\texactRivals, scorerRivals, scorerSelf, scorerCap, finalTier, null, threadRounds);\n\t\tif (chosenT >= 0) {'
s = once(s, needle, '''\t\t\t\texactRivals, scorerRivals, scorerSelf, scorerCap, finalTier, null, threadRounds);
        final int chosenRemaining = lastResearchOutcome == null ? chosenT % VERDICT_PLACE_STRIDE
                : lastResearchOutcome.remaining();
\t\tif (chosenT >= 0) {''')
s = once(s, 'chosenT % VERDICT_PLACE_STRIDE <= AI1_FASTSLOW_TTF', 'chosenRemaining <= AI1_FASTSLOW_TTF')
# Ranked rescue tries every admitted candidate; ordering is no longer selection.
s = once(s, '\t\t\tDirection confirmed = null;\n\t\t\tfor (int pass = 0; pass < DIRECTIONS.length && confirmed == null; pass++) {', '''\t\t\tDirection confirmed = null;
            final boolean rankRescue = nextEnabled(playerNum, RacecraftNext.Feature.RANK_TIME);
            int confirmedKey = Integer.MAX_VALUE;
\t\t\tfor (int pass = 0; pass < DIRECTIONS.length && (rankRescue || confirmed == null); pass++) {''')
s = once(s, 'if (t >= 0 && (spd < candSpd || spd == candSpd && t < candT)) {', '''if (t >= 0 && t != Integer.MAX_VALUE && (rankRescue
                            ? t < candT || t == candT && spd < candSpd
                            : spd < candSpd || spd == candSpd && t < candT)) {''')
s = once(s, '\t\t\t\tif (survives)\n\t\t\t\t\tconfirmed = cand;\n\t\t\t\telse\n\t\t\t\t\trejected[cand.ordinal()] = true;', '''                if (rankRescue) {
                    // Compare the completed faithful confirmation, not the proposal's speed.
                    final int key = lastResearchOutcome == null ? Integer.MAX_VALUE
                            : lastResearchOutcome.liveVerdict();
                    if (survives && key >= 0 && key < confirmedKey) {
                        confirmed = cand; confirmedKey = key;
                    }
                    rejected[cand.ordinal()] = true;
                } else if (survives) confirmed = cand;
                else rejected[cand.ordinal()] = true;''')
# Build the chooser change in isolation.
a = s.index('\tprivate Direction jointChooser(')
b = s.index('\n\t/** Round 262:', a)
c = s[a:b]
c = once(c, '\t\tfinal Direction[] order =', '''        final boolean rankTime = nextEnabled(playerNum, RacecraftNext.Feature.RANK_TIME);
        final boolean crashRank = nextEnabled(playerNum, RacecraftNext.Feature.CRASH_RANK);
        final boolean opening = nextEnabled(playerNum, RacecraftNext.Feature.OPENING)
                && RacecraftNext.opening(game, playerNum) && game.racecraftNext.openingTrials > 0;
        final boolean audit = simDepth == 0 && !inScorerSim;
        if (audit) auditScorer = best;
\t\tfinal Direction[] order =''')
c = once(c, '\t\tDirection pick = null;', '''        if (audit) {
            final StringBuilder row = new StringBuilder();
            for (int k = 0; k < n && k < AI1_CHOOSER_WIDTH; k++) {
                if (k > 0) row.append(','); row.append(order[k]);
            }
            auditShortlist = row.toString();
        }
        RacecraftOutcome bestCrash = null;
        Direction crashPick = null;
        boolean allCrash = true;
\t\tDirection pick = null;''')
c = once(c, '\t\t\tif (game.crossesFinishLegally(pos[0], pos[1], nx, ny))\n\t\t\t\treturn best;', '''            if (game.crossesFinishLegally(pos[0], pos[1], nx, ny)) {
                if (!game.racecraftNext.any(game, playerNum)) return best;
                final Player me = game.players[game.subgamestate];
                if (game.evaluateMove(me, pos, new int[]{nx, ny}).finishes()) return d;
                // Nonterminal crossings are ordinary candidates, never an abort.
            }''')
c = once(c, '\t\t\tfinal long verdict = outcome >= 0 && key >= 0 ? key : outcome;', '''            final RacecraftOutcome detail = lastResearchOutcome;
            if (detail == null || !detail.known() || !detail.crashed()) allCrash = false;
            else if (bestCrash == null || detail.betterThan(bestCrash, true)) {
                bestCrash = detail; crashPick = d;
            }
\t\t\tfinal long verdict = rankTime && detail != null ? detail.liveVerdict()
                    : outcome >= 0 && key >= 0 ? key : outcome;''')
c = once(c, '\t\treturn pick == null ? best : pick;', '''        if (crashRank && allCrash && crashPick != null) pick = crashPick;
        final Direction nominal = pick == null ? best : pick;
        if (audit) auditChooser = nominal;
        final Direction planned = opening ? openingSearch(pos, vel, playerNum, nominal, order,
                Math.min(n, AI1_CHOOSER_WIDTH)) : nominal;
        if (audit) auditOpening = planned;
        return planned;''')
s = s[:a] + c + s[b:]
# Add bounded explicit second-action planning. The plan is not a hidden commitment.
anchor = '\n\t/** Round 262:'
helpers = '''
    private RacecraftOutcome researchForecast(final int[] pos, final int[] vel,
            final int player, final Direction first, final int rounds, final Direction second) {
        final int oldDemand = researchDemandDepth, oldSecondDepth = forcedSecondDepth;
        final Direction oldSecond = forcedSecond;
        researchDemandDepth = forcedSecondDepth = simDepth + 1;
        forcedSecond = second;
        try {
            final int vx = vel[0] + first.dx, vy = vel[1] + first.dy;
            simOutcome(pos[0] + vx, pos[1] + vy, vx, vy, player, rounds,
                    true, true, true, true, true, AI1_SCORER_MAXRIVALS, null);
            return lastResearchOutcome == null ? RacecraftOutcome.unknown() : lastResearchOutcome;
        } finally {
            researchDemandDepth = oldDemand; forcedSecondDepth = oldSecondDepth; forcedSecond = oldSecond;
        }
    }

    private Direction openingSearch(final int[] pos, final int[] vel, final int player,
            final Direction nominal, final Direction[] order, final int width) {
        final int horizon = game.racecraftNext.openingRounds;
        RacecraftOutcome bestResult = researchForecast(pos, vel, player, nominal, horizon, null);
        if (!bestResult.known()) return nominal;
        Direction best = nominal;
        final boolean crashes = nextEnabled(player, RacecraftNext.Feature.CRASH_RANK);
        int used = 1;
        // Round-robin the root actions so a small budget does not fund only root 0.
        for (int follow = -1; follow < DIRECTIONS.length; follow++) {
            for (int k = 0; k < width; k++) {
                final Direction first = order[k];
                if (follow == -1 && first == nominal) continue;
                if (used >= game.racecraftNext.openingTrials) return best;
                used++;
                final RacecraftOutcome result = researchForecast(pos, vel, player, first, horizon,
                        follow < 0 ? null : DIRECTIONS[follow]);
                if (result.betterThan(bestResult, crashes)) { best = first; bestResult = result; }
            }
        }
        return best;
    }
'''
s = once(s, anchor, helpers + anchor)
p.write_text(s)

p = Path('src/tr/logic/StartPlacement.java')
s = p.read_text()
s = once(s, '        return new int[]{selected.x(), selected.y()};', '''        final int[] stock = {selected.x(), selected.y()};
        if (game.racecraftNext.enabled(game, player.getNumber(), RacecraftNext.Feature.START_TIES))
            return RacecraftReplay.chooseStart(game, player, stock,
                    bestCells.stream().map(c -> new int[]{c.x(), c.y()}).toArray(int[][]::new));
        return stock;''')
p.write_text(s)
p = Path('src/tr/logic/MoveQueries.java')
s = p.read_text()
s = once(s, '\tstatic String answer(final RaceGame game, final String line) {', '''\tstatic String answer(final RaceGame game, final String line) {
        if (line.startsWith("cf3,")) return RacecraftReplay.answer(game, line);''')
p.write_text(s)
p = Path('run_tests.sh')
s = p.read_text()
s += '\njava -ea -Djava.awt.headless=true -cp test-bin tr.logic.RacecraftNextTests\n'
p.write_text(s)
print('Integrated outcome, confirmation, opening, placement and corpus hooks')
