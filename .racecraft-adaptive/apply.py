from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / '.racecraft-adaptive'

def read(name): return (ROOT / name).read_text(encoding='utf-8')
def write(name, text):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
def rep(text, old, new, count=1):
    actual = text.count(old)
    if actual != count: raise RuntimeError(f'anchor count {actual}, expected {count}: {old[:160]!r}')
    return text.replace(old, new)

for source in STAGE.glob('*.java'):
    dest = 'tests/tr/logic/' if source.name.endswith('Tests.java') else 'src/tr/logic/'
    write(dest + source.name, source.read_text())

name = 'src/tr/logic/RacecraftNext.java'
s = read(name)
s = rep(s, 'OPENING("opening");', 'OPENING("opening"), ADAPTIVE_ESCAPE("adaptive-escape"),\n        FOLLOWUP("followup"), RECOVERY("recovery"), TACTICAL_EXTENSION("tactical-extension");')
s = rep(s, '    final int captureLimit;', '    final int captureLimit;\n    final int adaptiveNodes, adaptiveCycles, recoveryTrials, tacticalExtraRounds;')
s = rep(s, '        capture = Boolean.parseBoolean(audit);', '''        capture = Boolean.parseBoolean(audit);
        adaptiveNodes = bounded(props, "racecraftAdaptiveNodes", 2048, 0, 20000);
        adaptiveCycles = bounded(props, "racecraftAdaptiveCycles", 2, 1, 3);
        recoveryTrials = bounded(props, "racecraftRecoveryTrials", 9, 0, 9);
        tacticalExtraRounds = bounded(props, "racecraftTacticalExtraRounds", 2, 0, 2);''')
s = rep(s, '&& (feature != Feature.OPENING || openingTrials > 0 && opening(game, player));', '''&& (feature != Feature.OPENING || openingTrials > 0 && opening(game, player))
                && (feature != Feature.FOLLOWUP || features.contains(Feature.OPENING)
                        && openingTrials > 0 && opening(game, player))
                && (feature != Feature.ADAPTIVE_ESCAPE || adaptiveNodes > 0)
                && (feature != Feature.RECOVERY || recoveryTrials > 0)
                && (feature != Feature.TACTICAL_EXTENSION || tacticalExtraRounds > 0);''')
s = rep(s, 'String signature() { return features.toString() + ":" + openingRounds + ":" + openingTrials; }', '''boolean configured(final Feature feature) { return features.contains(feature); }
    String signature() { return features.toString() + ":" + openingRounds + ":" + openingTrials
            + ":" + adaptiveNodes + ":" + adaptiveCycles + ":" + recoveryTrials + ":" + tacticalExtraRounds; }''')
write(name, s)

name = 'src/tr/logic/OpeningPlans.java'
s = read(name)
s = rep(s, 'record Trial(RacecraftOutcome outcome, List<Direction> followups) {\n        Trial { followups = List.copyOf(followups); }', '''record Trial(RacecraftOutcome outcome, List<Direction> followups, String expectedKey) {
        Trial(RacecraftOutcome outcome, List<Direction> followups) { this(outcome, followups, null); }
        Trial { followups = List.copyOf(followups); }''')
s = rep(s, 'record Selection(Direction move, int trials) {}', '''record Selection(Direction move, int trials, Direction followup, String expectedKey) {
        Selection(Direction move, int trials) { this(move, trials, null, null); }
    }''')
s = rep(s, '        Direction best = nominal;', '        Direction best = nominal, followup = null;\n        String expectedKey = null;')
s = rep(s, '                    value = result.outcome(); best = order.get(k);', '''                    value = result.outcome(); best = order.get(k);
                    followup = followups.get(next); expectedKey = result.expectedKey();''')
s = rep(s, 'return new Selection(best, used);', 'return new Selection(best, used, followup, expectedKey);')
write(name,s)

name = 'src/tr/logic/RaceGame.java'
s = read(name)
s = rep(s, 'public final class RaceGame {', 'public final class RaceGame {\n    FollowupPlans followups = new FollowupPlans();')
s = rep(s, '\tprivate static final class MoveSnapshot {', '\tprivate static final class MoveSnapshot {\n        final FollowupPlans followups;')
s = rep(s, '\t\tMoveSnapshot(final RaceGame game) {', '\t\tMoveSnapshot(final RaceGame game) {\n            followups = game.followups.copy();')
s = rep(s, '\t\tvoid restore(final RaceGame game) {', '\t\tvoid restore(final RaceGame game) {\n            game.followups = followups.copy();')
s = rep(s, '\t\t// The gate credit belongs to a move that actually happens:', '''        if (ai != null) ai.commitResearchPlan(d);
        else followups.put(subgamestate, null);
\t\t// The gate credit belongs to a move that actually happens:''')
write(name,s)

name = 'src/tr/logic/RacecraftReplay.java'
s = read(name)
s = rep(s, '        final String identity;', '        final String identity, plans;')
s = rep(s, '''                final String identity, final int[][] cars) {
            this.turn = turn;''', '''                final String identity, final int[][] cars) {
            this(turn, laps, slot, first, last, identity, cars, "-");
        }
        Board(final int turn, final int laps, final int slot, final int first, final int last,
                final String identity, final int[][] cars, final String plans) {
            this.plans = plans;
            this.turn = turn;''')
s = rep(s, 'new StringBuilder("rc3,")', 'new StringBuilder(plans.equals("-") ? "rc3," : "rc4,")')
s = rep(s, '                    .append(\',\').append(identity);', '''                    .append(',').append(identity);
            if (!plans.equals("-")) out.append(',').append(plans);''')
s = rep(s, 'game.researchFinishedFirst(), game.researchFinishedLast(), identity(game), cars);', 'game.researchFinishedFirst(), game.researchFinishedLast(), identity(game), cars, game.followups.encode(cars.length));')
s = rep(s, 'h.length != 7 || !h[0].equals("rc3")', '!((h.length == 7 && h[0].equals("rc3")) || (h.length == 8 && h[0].equals("rc4")))')
s = rep(s, 'return new Board(turn, laps, slot, first, last, h[6], rows);', '''final String plans = h.length == 8 ? h[7] : "-";
        FollowupPlans.parse(plans, n);
        return new Board(turn, laps, slot, first, last, h[6], rows, plans);''')
s = rep(s, '        final boolean grid, replay;', '        final boolean grid, replay;\n        final FollowupPlans followups;')
s = rep(s, '            grid = game.aiGridLegal; replay = game.racecraftReplay;', '''            grid = game.aiGridLegal; replay = game.racecraftReplay;
            followups = game.followups;''')
s = rep(s, '            game.players = detached; game.subgamestate = board.slot;', '''            game.followups = FollowupPlans.parse(board.plans, detached.length);
            game.players = detached; game.subgamestate = board.slot;''')
s = rep(s, '            game.players = players; game.subgamestate = slot;', '''            game.followups = followups;
            game.players = players; game.subgamestate = slot;''')
s = rep(s, '''                final Direction action = firstAction && first != null ? first
                        : scorerOnly ? policy.researchScorer() : policy.computeAiMove();''', '''                // A forced first action must still preserve the policy's plan when
                // it equals the actual proposal; a different action invalidates it.
                final boolean remember = game.racecraftNext.configured(RacecraftNext.Feature.FOLLOWUP);
                final Direction proposed = firstAction && first != null && !remember ? first
                        : scorerOnly ? policy.researchScorer() : policy.computeAiMove();
                final Direction action = firstAction && first != null ? first : proposed;''')
s = rep(s, '                final String transition = advance(game, action);', '                policy.commitResearchPlan(action);\n                final String transition = advance(game, action);')
write(name,s)

name = 'src/tr/logic/RaceAiPrivateLane.java'
s = read(name)
s = rep(s, '\t\tprivate ExactRivalReach exact;', '\t\tprivate ExactRivalReach exact;\n        private AdaptiveEscape.Session adaptive;')
anchor = '\t\t/** The candidate\'s own progress in the proof\'s currency. */'
s = rep(s, anchor, '''        /** Extra proof only; callers retain their original candidate and rollout gates. */
        boolean certifiesAdaptive(final int x, final int y, final int vx, final int vy,
                final int cycles, final int escapes, final int budget) {
            if (adaptive == null) adaptive = new AdaptiveEscape.Session(game, playerNum, budget);
            return adaptive.certifies(x, y, vx, vy, cycles, escapes);
        }

''' + anchor)
write(name,s)

name = 'src/tr/logic/RaceAi.java'
s = read(name)
s = rep(s, '\tprivate final RaceGame game;', '''\tprivate final RaceGame game;
    private Direction inheritedFollowup, pendingFirst;
    private FollowupPlans.Entry pendingFollowup;
    private String decisionRootKey, openingExpectedKey;
    private int tacticalProbeDepth = -1;
    private boolean tacticalEndpoint;''')
s = rep(s, '        RacecraftOutcome researchOutcome;', '        RacecraftOutcome researchOutcome;\n        FollowupPlans.Projection followupProjection;')
s = rep(s, '        final Direction decision = optimalMoveAI1(pos, vel, playerNum);', '''        if (root) {
            inheritedFollowup = null; pendingFollowup = null; pendingFirst = null; decisionRootKey = null;
            if (game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.FOLLOWUP)) {
                decisionRootKey = FollowupPlans.key(game);
                final FollowupPlans.Entry entry = game.followups.find(game);
                inheritedFollowup = entry == null ? null : entry.action();
            }
        }
        final Direction decision = optimalMoveAI1(pos, vel, playerNum);
        if (root && pendingFirst != decision) pendingFollowup = null;''')
s = rep(s, '\t/**\n\t * Pure min-turns lookup, no opponent reasoning.', '''    /** Called only once an action is committed. Hint/oracle queries are read-only. */
    void commitResearchPlan(final Direction action) {
        if (!game.racecraftNext.configured(RacecraftNext.Feature.FOLLOWUP)) return;
        FollowupPlans.Entry entry = null;
        if (pendingFollowup != null && action == pendingFirst && decisionRootKey != null
                && game.racecraftNext.enabled(game, game.players[game.subgamestate].getNumber(),
                        RacecraftNext.Feature.FOLLOWUP)
                && decisionRootKey.equals(FollowupPlans.key(game))) entry = pendingFollowup;
        game.followups.put(game.subgamestate, entry);
        decisionRootKey = null; pendingFollowup = null; pendingFirst = null;
    }

\t/**
\t * Pure min-turns lookup, no opponent reasoning.''')
s = rep(s, '        final boolean rankTime = nextEnabled(playerNum, RacecraftNext.Feature.RANK_TIME);', '''        final boolean rankTime = nextEnabled(playerNum, RacecraftNext.Feature.RANK_TIME);
        final boolean real = simDepth == 0 && !inScorerSim;
        final boolean recovery = real && nextEnabled(playerNum, RacecraftNext.Feature.RECOVERY);
        final boolean extension = real && nextEnabled(playerNum, RacecraftNext.Feature.TACTICAL_EXTENSION);
        final Direction inherited = real ? inheritedFollowup : null;
        final boolean tactical = recovery || extension || inherited != null;
        final java.util.Map<Direction, TacticalComparison.Evaluation> sampled = tactical
                ? new java.util.LinkedHashMap<>() : null;''')
s = rep(s, '\t\tif (n < 2)\n\t\t\treturn best;', '\t\tif (n == 0 || n < 2 && !tactical)\n\t\t\treturn best;')
s = rep(s, '''\t\t\tfinal int outcome = simOutcome(nx, ny, nvx, nvy, playerNum, AI1_CHOOSER_ROUNDS,
\t\t\t\t\ttrue, true, true, true, true, AI1_SCORER_MAXRIVALS, null);''', '''            final TacticalComparison.Evaluation evaluation = tactical
                    ? tacticalForecast(pos, vel, playerNum, d, AI1_CHOOSER_ROUNDS) : null;
            final int outcome = tactical ? evaluation.outcome().liveVerdict()
                    : simOutcome(nx, ny, nvx, nvy, playerNum, AI1_CHOOSER_ROUNDS,
                            true, true, true, true, true, AI1_SCORER_MAXRIVALS, null);
            if (tactical) sampled.put(d, evaluation);''')
s = rep(s, '        final Direction nominal = pick == null ? best : pick;', '''        Direction nominal = pick == null ? best : pick;
        if (tactical) {
            final TacticalComparison.Selection selection = TacticalComparison.choose(nominal, sampled,
                    RacecraftReplay.legalActions(game), inherited, AI1_CHOOSER_ROUNDS,
                    recovery ? game.racecraftNext.recoveryTrials : 0,
                    extension ? game.racecraftNext.tacticalExtraRounds : 0,
                    (d, horizon) -> tacticalForecast(pos, vel, playerNum, d, horizon));
            nominal = selection.move();
            if (game.racecraftNext.capture && !game.racecraftReplay)
                System.err.println("RACECRAFT_TACTICAL p=" + playerNum + " trials=" + selection.trials()
                        + " extension=" + selection.extensionRounds() + " inherited=" + selection.inheritedOffered()
                        + " recovery=" + selection.recoveryExpanded());
        }''')
s = rep(s, '        openingFollowups = java.util.List.of();', '        openingFollowups = java.util.List.of();\n        openingExpectedKey = null;')
s = rep(s, 'return new OpeningPlans.Trial(value, openingFollowups);', 'return new OpeningPlans.Trial(value, openingFollowups, openingExpectedKey);')
s = rep(s, '''        return result.move();
    }

    /** Legal second actions''', '''        if (simDepth == 0 && !inScorerSim && result.followup() != null && result.expectedKey() != null
                && nextEnabled(player, RacecraftNext.Feature.FOLLOWUP)) {
            pendingFirst = result.move();
            pendingFollowup = new FollowupPlans.Entry(result.followup(), result.expectedKey());
        }
        return result.move();
    }

    /** Legal second actions''')
s = rep(s, '        workspace.researchOutcome = null;', '''        workspace.researchOutcome = null;
        workspace.followupProjection = candidatePending && simDepth == forcedSecondDepth
                && nextEnabled(playerNum, RacecraftNext.Feature.FOLLOWUP)
                ? new FollowupPlans.Projection(game) : null;''')
s = rep(s, '\t\t\tworkspace.laps[myIdx] = candidate.lapAfter();', '''            if (workspace.followupProjection != null)
                workspace.followupProjection.step(myIdx, candidate, myX, myY, myVx, myVy);
\t\t\tworkspace.laps[myIdx] = candidate.lapAfter();''')
s = rep(s, '''                if (i == myIdx && simDepth == forcedSecondDepth && forcedSecond == null
                        && workspace.researchOwnMoves == 2) openingFollowups = openingSecondActions(workspace, i);''', '''                if (i == myIdx && simDepth == forcedSecondDepth && workspace.researchOwnMoves == 2) {
                    if (workspace.followupProjection != null) {
                        openingExpectedKey = workspace.followupProjection.key(workspace.turns, i);
                        workspace.followupProjection = null;
                    }
                    if (forcedSecond == null) openingFollowups = openingSecondActions(workspace, i);
                }''')
s = rep(s, '''\t\t\t\tfinal boolean timedOut = game.lapGates != null
\t\t\t\t\t\t&& workspace.turns > (long) game.totalLaps * 750 * game.players.length;''', '''                if (workspace.followupProjection != null)
                    workspace.followupProjection.step(i, transition, move[0], move[1], move[2], move[3]);
\t\t\t\tfinal boolean timedOut = game.lapGates != null
\t\t\t\t\t\t&& workspace.turns > (long) game.totalLaps * 750 * game.players.length;''')
s = rep(s, '\t\treturn rankVerdict(myFinished ? aheadAtMyFinish : rivalsFinished, myTime);', '''        if (simDepth == tacticalProbeDepth && !myFinished) tacticalEndpoint = imminentRivalFinish(workspace, myIdx);
\t\treturn rankVerdict(myFinished ? aheadAtMyFinish : rivalsFinished, myTime);''')
s = rep(s, '\t\t\tif (!certified)\n\t\t\t\tcontinue;', '''            if (!certified && simDepth == 0 && !inScorerSim
                    && nextEnabled(playerNum, RacecraftNext.Feature.ADAPTIVE_ESCAPE)) {
                final int escapes = speedSquared(nvx, nvy) < AI1_DJS_SPD2 || homogeneousFrontier
                        ? AI1_PRIVATE_EXACT_ESCAPES : AI1_PRIVATE_BASE_ESCAPES;
                certified = privateProof.certifiesAdaptive(nx, ny, nvx, nvy,
                        game.racecraftNext.adaptiveCycles, escapes, game.racecraftNext.adaptiveNodes);
            }
\t\t\tif (!certified)
\t\t\t\tcontinue;''')
anchor = '    /** Legal second actions, priced in the successor\'s progress frame. */'
s = rep(s, anchor, '''    private TacticalComparison.Evaluation tacticalForecast(final int[] pos, final int[] vel,
            final int player, final Direction action, final int rounds) {
        final int demand = researchDemandDepth, probe = tacticalProbeDepth;
        final boolean oldEndpoint = tacticalEndpoint;
        researchDemandDepth = tacticalProbeDepth = simDepth + 1;
        tacticalEndpoint = false;
        try {
            final int vx = vel[0] + action.dx, vy = vel[1] + action.dy;
            simOutcome(pos[0] + vx, pos[1] + vy, vx, vy, player, rounds,
                    true, true, true, true, true, AI1_SCORER_MAXRIVALS, null);
            return new TacticalComparison.Evaluation(lastResearchOutcome == null
                    ? RacecraftOutcome.unknown() : lastResearchOutcome, tacticalEndpoint);
        } finally {
            researchDemandDepth = demand; tacticalProbeDepth = probe; tacticalEndpoint = oldEndpoint;
        }
    }

    /** Trigger only. Continue the same policies in actual cyclic order; never
     * assume an opponent will wait, or grant a finishing place from this predicate. */
    private boolean imminentRivalFinish(final RolloutWorkspace w, final int self) {
        for (int i = 0; i < w.alive.length; i++) if (i != self && w.alive[i]) {
            for (final Direction d : DIRECTIONS) {
                final int x = w.px[i] + w.vx[i] + d.dx, y = w.py[i] + w.vy[i] + d.dy;
                if (game.evaluateMove(w.laps[i], w.gates[i], w.px[i], w.py[i], x, y,
                        occupiedByOther(x, y, i, w.px, w.py, w.alive)).finishes()) return true;
            }
        }
        return false;
    }

''' + anchor)
write(name,s)

name = 'tools/racecraft_validation.py'
s=read(name)
s=rep(s, "if len(header) != 7 or header[0] != 'rc3' or not re.fullmatch(r'[0-9a-f]{64}', header[6]):", "if not ((len(header) == 7 and header[0] == 'rc3') or (len(header) == 8 and header[0] == 'rc4')) or not re.fullmatch(r'[0-9a-f]{64}', header[6]):")
s=rep(s, '    n = len(rows)\n', '''    n = len(rows)
    if len(header) == 8:
        plans = header[7].split('.')
        if len(plans) != n or any(p != '-' and not re.fullmatch(r'(?:NW|N|NE|W|NONE|E|SW|S|SE)~[0-9a-f]{64}', p) for p in plans):
            raise ValueError('invalid follow-up policy memory')
''')
write(name,s)
name='tools/racecraft_corpus.py'
s=read(name)
s=rep(s, "if len(h) != 7 or h[0] != 'rc3' or not 1 <= len(cars) <= 9 or any(len(c) != 14 for c in cars):", "if not ((len(h) == 7 and h[0] == 'rc3') or (len(h) == 8 and h[0] == 'rc4')) or not 1 <= len(cars) <= 9 or any(len(c) != 14 for c in cars):")
s=rep(s, '    slot = int(h[3])\n', '    validation.snapshot(snapshot)\n    slot = int(h[3])\n')
write(name,s)

name='tests/racecraft_next_cli.py'
s=read(name)
s=rep(s,"FLAGS = 'crash-rank,rank-time,opening'", "FLAGS = 'crash-rank,rank-time,opening,adaptive-escape,followup,recovery,tactical-extension'")
write(name,s)
name='run_tests.sh'
s=read(name)
s+='\njava -ea -Djava.awt.headless=true -cp test-bin tr.logic.RacecraftAdaptiveTests\n'
write(name,s)

name='racing-memory.md'
s=read(name)
heading=s.index('\n')+1
entry='''

## Adaptive response research (2026-10-03, branch only)

Owner request: implement adaptive escapes, inherited opening follow-ups,
failure-triggered candidate expansion and endpoint-triggered extension.
Base: 1c50a5c on work/racecraft-outcomes-opening-20260928; master remains
b54e9bb. New opt-in racecraftNext flags: adaptive-escape, followup, recovery,
tactical-extension. All require candidateSlots. Followup refines opening and
requires that flag too. No start-placement changes, no yielding, no promotion.
Adaptive certificates cover exactly two live cars, finite horizon, all physical
rival accelerations, unchanged escape-count requirements and decreasing exact
solo distance. Budget exhaustion and absent exact lap potentials abstain.
Follow-up proposals are saved only when their first action is committed, expire
on board/clock/rule mismatch or end of opening, and are candidates, never forced
moves. Undo and rc4 snapshots preserve pending plans; cf4 request hashing also
binds this optional policy state. UI path-pruning marks are not plan identity.
Recovery admits every remaining physical legal action within its explicit trial
budget only after all compared originals predict known crashes. Extended
comparisons repeat every considered action at one common horizon (+1/+2 roster
cycles), keeping the same opponent model. Neither feature treats unknown as a
crash or a proof. Existing pace and danger guards remain downstream.
Validation outcomes are recorded separately after execution. Earlier round-298
screens do not evaluate these implementations. No fleet/lone-entrant gain claimed.
'''
s=s[:heading]+entry+s[heading:]
write(name,s)
print('Applied adaptive response, follow-up state, recovery, and tactical-horizon experiments')
