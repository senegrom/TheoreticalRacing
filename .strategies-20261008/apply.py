#!/usr/bin/env python3
"""Materialize reviewed strategy experiments; refuse unmatched source anchors."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
STAGE = Path(__file__).resolve().parent

def edit(path, old, new, count=1):
    p=ROOT/path; text=p.read_text()
    found=text.count(old)
    if found != count: raise RuntimeError(f'{path}: expected {count} anchors, got {found}: {old[:120]}')
    p.write_text(text.replace(old,new))

for name in ('StrategyState','ResponseStrategies','PlaceCertificates','OrderedBlockade','SuffixManoeuvres','ContinuationPortfolio'):
    shutil.copyfile(STAGE/(name+'.java'), ROOT/'src/tr/logic'/(name+'.java'))
# Forced means physically forced, not merely unique inside the preferred planning domain.
p=ROOT/'src/tr/logic/PlaceCertificates.java'
p.write_text(p.read_text().replace('forced && legal.size() == 1','forced && state.legal(game, false).size() == 1'))

if 'SUFFIX_MANOEUVRES' not in (ROOT/'src/tr/logic/RacecraftNext.java').read_text():
    edit('src/tr/logic/RacecraftNext.java','SHORT_TRANSITIONS("short-transitions");',
         'SHORT_TRANSITIONS("short-transitions"), SUFFIX_MANOEUVRES("suffix-manoeuvres"),\n        RESPONSE_STRATEGY("response-strategy"), PLACE_CERTIFICATES("place-certificates"),\n        FORCED_SEQUENCE("forced-sequence"), CONTINUATION_POLICIES("continuation-policies"),\n        ORDERED_BLOCKADE("ordered-blockade");')
    edit('src/tr/logic/RacecraftNext.java','final int manoeuvreNodes, manoeuvreDepth;',
         'final int manoeuvreNodes, manoeuvreDepth;\n    final int strategyNodes, forcedMoveCap;')
    edit('src/tr/logic/RacecraftNext.java','manoeuvreNodes = bounded(props,',
         'strategyNodes = bounded(props, "racecraftStrategyNodes", 12000, 0, 40000);\n        forcedMoveCap = bounded(props, "racecraftForcedMoveCap", 16, 4, 24);\n        manoeuvreNodes = bounded(props,')
    edit('src/tr/logic/RacecraftNext.java','return game.candidatePolicy(player) && features.contains(feature)',
         'return game.candidatePolicy(player) && configured(feature)\n                && (feature.ordinal() < Feature.SUFFIX_MANOEUVRES.ordinal() || strategyNodes > 0)\n                && (feature != Feature.SUFFIX_MANOEUVRES || manoeuvreNodes > 0)')
    edit('src/tr/logic/RacecraftNext.java','features.contains(Feature.OPENING)', 'features.contains(Feature.OPENING)', 1)
    edit('src/tr/logic/RacecraftNext.java','boolean configured(final Feature feature) { return features.contains(feature); }',
         'boolean configured(final Feature feature) { return features.contains(feature)\n            || feature == Feature.MANOEUVRE && features.contains(Feature.SUFFIX_MANOEUVRES)\n                    && strategyNodes > 0; }')
    edit('src/tr/logic/RacecraftNext.java','+ ":" + manoeuvreNodes + ":" + manoeuvreDepth;',
         '+ ":" + manoeuvreNodes + ":" + manoeuvreDepth + ":" + strategyNodes + ":" + forcedMoveCap;')

    edit('src/tr/logic/FollowupPlans.java',
         'record Entry(java.util.List<Direction> actions, String expectedKey, boolean traffic) {',
         'record Entry(java.util.List<Direction> actions, String expectedKey, boolean traffic, ResponseStrategies.Tree responses) {')
    edit('src/tr/logic/FollowupPlans.java',
         'Entry(final Direction action, final String expectedKey) { this(java.util.List.of(action), expectedKey, false); }',
         'Entry(final java.util.List<Direction> actions, final String expectedKey, final boolean traffic) { this(actions, expectedKey, traffic, null); }\n        Entry(final Direction action, final String expectedKey) { this(java.util.List.of(action), expectedKey, false); }\n        boolean response() { return responses != null; }\n        static Entry response(final ResponseStrategies.Tree tree, final String key) {\n            if (tree == null || tree.empty()) throw new IllegalArgumentException("empty response plan");\n            return new Entry(java.util.List.of(Direction.NONE), key, false, tree);\n        }')
    edit('src/tr/logic/FollowupPlans.java',
         'return entry != null && entry.expectedKey().equals(key(game)) ? entry : null;',
         'return entry != null && (entry.response() ? entry.responses().at(key(game)) != null\n                : entry.expectedKey().equals(key(game))) ? entry : null;')
    edit('src/tr/logic/FollowupPlans.java','if(e.traffic()) out.append("M_");',
         'if(e.response()) { out.append("R_").append(e.responses().encode()).append(\'~\').append(e.expectedKey()); continue; }\n            if(e.traffic()) out.append("M_");')
    edit('src/tr/logic/FollowupPlans.java','final boolean traffic=fields[0].startsWith("M_");',
         'if(fields[0].startsWith("R_")) { result.entries[i]=Entry.response(ResponseStrategies.Tree.parse(fields[0].substring(2)),fields[1]); continue; }\n            final boolean traffic=fields[0].startsWith("M_");')
    edit('src/tr/logic/RacecraftReplay.java','plans.equals("-") ? "rc3," : plans.contains("M_") ? "rc5," : "rc4,"',
         'plans.equals("-") ? "rc3," : plans.contains("R_") ? "rc6," : plans.contains("M_") ? "rc5," : "rc4,"')
    edit('src/tr/logic/RacecraftReplay.java','text.length() > 16384','text.length() > 131072')
    edit('src/tr/logic/RacecraftReplay.java','h[0].equals("rc4") || h[0].equals("rc5")',
         'h[0].equals("rc4") || h[0].equals("rc5") || h[0].equals("rc6")')
    edit('src/tr/logic/RacecraftReplay.java','if (plans.contains("M_") != h[0].equals("rc5")) throw new IllegalArgumentException("noncanonical plan version");',
         'final String version = plans.equals("-") ? "rc3" : plans.contains("R_") ? "rc6" : plans.contains("M_") ? "rc5" : "rc4";\n        if (!h[0].equals(version)) throw new IllegalArgumentException("noncanonical plan version");')
    p=ROOT/'src/tr/logic/RacecraftReplay.java';t=p.read_text();t=t.replace(
         'game.racecraftNext.configured(RacecraftNext.Feature.MANOEUVRE)',
         '(game.racecraftNext.configured(RacecraftNext.Feature.MANOEUVRE)\n                    || game.racecraftNext.configured(RacecraftNext.Feature.RESPONSE_STRATEGY)\n                    || game.racecraftNext.configured(RacecraftNext.Feature.CONTINUATION_POLICIES))');p.write_text(t)

    edit('src/tr/logic/TrafficManoeuvres.java',
         'if (budget <= 0 || schedule.size() < depth) return new Search(List.of(), 0);',
         'if (game.racecraftNext.enabled(game, game.players[game.subgamestate].getNumber(), RacecraftNext.Feature.SUFFIX_MANOEUVRES))\n            return SuffixManoeuvres.propose(game, schedule, nominal, depth, budget);\n        if (budget <= 0 || schedule.size() < depth) return new Search(List.of(), 0);')

    p=ROOT/'src/tr/logic/RaceAi.java';t=p.read_text()
    def rep(old,new,count=1):
        global t
        if t.count(old)!=count: raise RuntimeError(f'RaceAi anchor {t.count(old)} != {count}: {old[:110]}')
        t=t.replace(old,new)
    rep('private Direction inheritedFollowup, pendingFirst;',
        'private Direction inheritedFollowup, pendingFirst;\n    private final java.util.Map<Direction, ResponseStrategies.Tree> responseProofs = new java.util.EnumMap<>(Direction.class);\n    private StrategyState.Budget responseBudget, blockadeBudget;\n    private int strategyPlaceNodes, strategyForcedNodes, strategyPolicyForecasts, strategyResponses;')
    rep('inheritedFollowup = null; inheritedTraffic = null; pendingFollowup = null; pendingFirst = null; decisionRootKey = null;',
        'inheritedFollowup = null; inheritedTraffic = null; pendingFollowup = null; pendingFirst = null; decisionRootKey = null;\n            responseProofs.clear(); responseBudget = null; blockadeBudget = null;\n            strategyPlaceNodes = strategyForcedNodes = strategyPolicyForecasts = strategyResponses = 0;')
    rep('|| game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.MANOEUVRE)) {',
        '|| game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.MANOEUVRE)\n                    || game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.CONTINUATION_POLICIES)\n                    || game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.RESPONSE_STRATEGY)) {')
    rep('if (entry != null && entry.traffic() && game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.MANOEUVRE)) inheritedTraffic = entry;',
        'if (entry != null && entry.traffic() && (game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.MANOEUVRE)\n                        || game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.CONTINUATION_POLICIES))) inheritedTraffic = entry;')
    rep('if (entry != null && !entry.traffic() && game.racecraftNext.enabled',
        'if (entry != null && !entry.traffic() && !entry.response() && game.racecraftNext.enabled')
    rep('final Direction decision = optimalMoveAI1(pos, vel, playerNum);',
        'Direction decision = optimalMoveAI1(pos, vel, playerNum);\n        if (root && trafficFeature(playerNum, RacecraftNext.Feature.RESPONSE_STRATEGY))\n            decision = responseDecision(decision);')
    rep('if (capture) System.err.println("RACECRAFT_TRAFFIC p="',
        'if (capture) System.err.println("RACECRAFT_STRATEGIES p=" + playerNum + " placeNodes=" + strategyPlaceNodes\n                + " forcedNodes=" + strategyForcedNodes + " policyForecasts=" + strategyPolicyForecasts\n                + " responseSelections=" + strategyResponses);\n        if (capture) System.err.println("RACECRAFT_TRAFFIC p="')
    rep('&& !game.racecraftNext.configured(RacecraftNext.Feature.MANOEUVRE)) return;',
        '&& !game.racecraftNext.configured(RacecraftNext.Feature.MANOEUVRE)\n                && !game.racecraftNext.configured(RacecraftNext.Feature.RESPONSE_STRATEGY)\n                && !game.racecraftNext.configured(RacecraftNext.Feature.CONTINUATION_POLICIES)) return;')
    rep('&& game.racecraftNext.enabled(game, game.players[game.subgamestate].getNumber(),\n                        pendingFollowup.traffic() ? RacecraftNext.Feature.MANOEUVRE : RacecraftNext.Feature.FOLLOWUP)',
        '&& pendingPlanEnabled(pendingFollowup, game.players[game.subgamestate].getNumber())')
    rep('if (tacticalWin != null)\n\t\t\treturn tacticalWin;',
        'if (tacticalWin != null)\n\t\t\treturn tacticalWin;\n        if (trafficFeature(playerNum, RacecraftNext.Feature.FORCED_SEQUENCE)) {\n            final Direction forced = forcedSequenceNominee();\n            if (forced != null) return forced;\n        }')
    rep('&& nextEnabled(playerNum, RacecraftNext.Feature.ADAPTIVE_ESCAPE)) {',
        '&& (nextEnabled(playerNum, RacecraftNext.Feature.ADAPTIVE_ESCAPE)\n                        || nextEnabled(playerNum, RacecraftNext.Feature.RESPONSE_STRATEGY))) {')
    rep('certified = privateProof.certifiesAdaptive(nx, ny, nvx, nvy,\n                        game.racecraftNext.adaptiveCycles, escapes, game.racecraftNext.adaptiveNodes);',
        'certified = nextEnabled(playerNum, RacecraftNext.Feature.RESPONSE_STRATEGY)\n                        ? responseCertificate(d, escapes)\n                        : privateProof.certifiesAdaptive(nx, ny, nvx, nvy,\n                                game.racecraftNext.adaptiveCycles, escapes, game.racecraftNext.adaptiveNodes);')
    rep('chosen = guardedFieldPaceOverride(pos, vel, playerNum, chosen, trapByDir, poTByDir);',
        'chosen = guardedFieldPaceOverride(pos, vel, playerNum, chosen, trapByDir, poTByDir);\n            if (trafficFeature(playerNum, RacecraftNext.Feature.CONTINUATION_POLICIES)\n                    && auditChooser != null && (chosen != auditChooser || inheritedTraffic != null)) {\n                final ContinuationPortfolio.Choice portfolio = ContinuationPortfolio.choose(game, chosen, auditChooser, inheritedTraffic);\n                strategyPolicyForecasts += portfolio.forecasts();\n                if (portfolio.tail() != null) { pendingFirst = portfolio.action(); pendingFollowup = portfolio.tail(); }\n                chosen = portfolio.action();\n            }')
    rep('if (addPace) cands.add(pace);',
        'if (addPace) cands.add(pace);\n        if (trafficFeature(playerNum, RacecraftNext.Feature.PLACE_CERTIFICATES)) {\n            final Direction extra = placeCertificateNominee();\n            if (extra != null && !cands.contains(extra)) cands.add(extra);\n        }')
    rep('return hasDistinctCover(sealCover, escapeCount, opponentCount, sealMatch);',
        'final boolean covered = hasDistinctCover(sealCover, escapeCount, opponentCount, sealMatch);\n        if (covered && escapeCount > 0 && trafficFeature(playerNum, RacecraftNext.Feature.ORDERED_BLOCKADE)) {\n            final Player me = game.players[game.subgamestate];\n            for (final Direction first : DIRECTIONS) if (me.getVelocity()[0] + first.dx == vx\n                    && me.getVelocity()[1] + first.dy == vy && me.getPosition()[0] + vx == x && me.getPosition()[1] + vy == y) {\n                if (blockadeBudget == null) blockadeBudget = new StrategyState.Budget(game.racecraftNext.strategyNodes);\n                if (OrderedBlockade.check(game, first, sealEscapes, escapeCount, blockadeBudget)\n                        == OrderedBlockade.Verdict.IMPOSSIBLE) return false;\n            }\n        }\n        return covered;')
    helpers=(STAGE/'hooks.txt').read_text()
    t=t[:t.rfind('}')]+helpers+'\n}\n';p.write_text(t)

    # Canonical response-memory protocol, bounded independently in Python.
    p=ROOT/'tools/racecraft_validation.py';t=p.read_text()
    t=t.replace('len(text) > 16384','len(text) > 131072').replace("('rc4', 'rc5')","('rc4', 'rc5', 'rc6')")
    a=t.index("        if ('M_' in header[7])")
    b=t.index('    if not 1 <= n <= 9',a)
    t=t[:a]+'''        version = 'rc6' if 'R_' in header[7] else 'rc5' if 'M_' in header[7] else 'rc4'
        if header[0] != version or len(plans) != n:
            raise ValueError('noncanonical plan version or roster')
        for plan in plans:
            if plan == '-': continue
            if not plan.startswith('R_'):
                if not re.fullmatch(pattern, plan): raise ValueError('invalid follow-up policy memory')
                continue
            fields = plan[2:].split('~')
            if len(fields) != 2 or not re.fullmatch(r'[0-9a-f]{64}', fields[1]):
                raise ValueError('invalid response memory')
            nodes = fields[0].split('!')
            if not 1 <= len(nodes) <= 128: raise ValueError('response table over budget')
            keys = []
            for node in nodes:
                f = node.split('_')
                if len(f) != 4 or not re.fullmatch(r'[0-9a-f]{64}', f[0]):
                    raise ValueError('invalid response key')
                mask, cycles, escapes = map(int, f[1:])
                integer(mask, 1, 511); integer(cycles, 1, 3); integer(escapes, 1, 9)
                if '_'.join((f[0],str(mask),str(cycles),str(escapes))) != node:
                    raise ValueError('noncanonical response node')
                keys.append(f[0])
            if keys != sorted(set(keys)): raise ValueError('duplicate or unordered response keys')
''' + t[b:];p.write_text(t)
    p=ROOT/'tools/racecraft_corpus.py';t=p.read_text()
    t=t.replace("'rc5,'", "'rc5,', 'rc6,'").replace('"rc5,"','"rc5,", "rc6,"')
    p.write_text(t)

if (STAGE/'StrategyResearchTests.java').exists():
    shutil.copyfile(STAGE/'StrategyResearchTests.java',ROOT/'tests/tr/logic/StrategyResearchTests.java')
    p=ROOT/'run_tests.sh';t=p.read_text()
    if 'tr.logic.StrategyResearchTests' not in t:
        p.write_text(t+'\njava -ea -Djava.awt.headless=true -cp test-bin tr.logic.StrategyResearchTests\n')
for name in ('test_strategy_protocol.py','racecraft_strategies_cli.py'):
    if (STAGE/name).exists(): shutil.copyfile(STAGE/name,ROOT/'tests'/name)
p=ROOT/'docs/experiments/strategy-research';p.mkdir(parents=True,exist_ok=True)
if (STAGE/'README.md').exists(): shutil.copyfile(STAGE/'README.md',p/'README.md')
p=ROOT/'racing-memory.md';t=p.read_text()
if '## Executable strategy research (2026-10-08' not in t:
    title,rest=t.split('\n',1)
    t=title+'\n\n## Executable strategy research (2026-10-08, branch only)\n\nSix independent arms: suffix-manoeuvres, response-strategy, place-certificates,\nforced-sequence, continuation-policies, ordered-blockade. Recover the earlier\nresearch foundation while preserving current master b907126 and the 301a/301c\npromotions. All extra policy changes require explicit candidate slots and flags.\nResponses carry finite clock-keyed trees; suffixes remain fresh proposals; three-car\nbounds nominate, never equate unknown with loss; forced search counts physical\nalternatives; ordered blockade clears only exhaustive impossibility. No promotion\nor performance gain claimed. Executed validation is recorded separately.\n'+rest
    p.write_text(t)
print('Materialized six executable strategy experiments and protocol contracts')
