from pathlib import Path
import shutil

ROOT = Path('.')
STAGE = ROOT / '.creative-20261011'

def replace(text, old, new, count=1):
    found = text.count(old)
    if found != count:
        raise RuntimeError(f'patch context mismatch ({found} != {count}): {old[:100]}')
    return text.replace(old, new)

for source in STAGE.glob('*.java'):
    folder = 'tests/tr/logic' if source.stem.endswith('Tests') else 'src/tr/logic'
    shutil.copyfile(source, ROOT / folder / source.name)
for source in STAGE.glob('*.py'):
    if source.name == 'apply.py': continue
    folder = 'tests' if source.name.startswith('test_') or source.name.endswith('_cli.py') else 'tools'
    shutil.copyfile(source, ROOT / folder / source.name)

p = ROOT / 'src/tr/logic/RacecraftNext.java'
s = p.read_text()
if 'PACE_FEINTS' not in s:
    s = replace(s, 'ORDERED_BLOCKADE("ordered-blockade");', '''ORDERED_BLOCKADE("ordered-blockade"), PACE_FEINTS("pace-feints"), AMBUSH("ambush"),
        TRAFFIC_JUDO("traffic-judo"), SELFISH_SEARCH("selfish-search"), TWO_JUDGE("two-judge");''')
    s = replace(s, 'final int strategyNodes, forcedMoveCap;', 'final int strategyNodes, forcedMoveCap;\n    final int creativeNodes, creativeTrials, selfishPlies;')
    s = replace(s, '        strategyNodes = bounded(', '''        creativeNodes = bounded(props, "racecraftCreativeNodes", 2048, 0, 20000);
        creativeTrials = bounded(props, "racecraftCreativeTrials", 6, 0, 12);
        selfishPlies = bounded(props, "racecraftSelfishPlies", 6, 2, 9);
        strategyNodes = bounded(''')
    s = replace(s, '&& (feature.ordinal() < Feature.SUFFIX_MANOEUVRES.ordinal() || strategyNodes > 0)', '''&& (feature.ordinal() < Feature.SUFFIX_MANOEUVRES.ordinal()
                        || feature.ordinal() > Feature.ORDERED_BLOCKADE.ordinal() || strategyNodes > 0)
                && (!creative(feature) || creativeNodes > 0 && creativeTrials > 0)''')
    s = replace(s, '+ ":" + strategyNodes + ":" + forcedMoveCap;', '+ ":" + strategyNodes + ":" + forcedMoveCap\n            + ":" + creativeNodes + ":" + creativeTrials + ":" + selfishPlies;')
    s = replace(s, '    boolean any(final RaceGame game, final int player) {', '''    static boolean creative(final Feature feature) { return feature.ordinal() >= Feature.PACE_FEINTS.ordinal(); }
    boolean creativeConfigured() {
        for (final Feature feature : features) if (creative(feature)) return true;
        return false;
    }
    boolean creativeEnabled(final RaceGame game, final int player) {
        return game.candidatePolicy(player) && creativeConfigured() && creativeNodes > 0 && creativeTrials > 0;
    }

    boolean any(final RaceGame game, final int player) {''')
    p.write_text(s)

p = ROOT / 'src/tr/logic/RaceAi.java'
s = p.read_text()
if 'private boolean creativeModel;' not in s:
    s = replace(s, 'private final RaceGame game;', 'private final RaceGame game;\n    private boolean creativeModel;')
    s = replace(s, 'final boolean root = simDepth == 0 && !inScorerSim;', 'final boolean root = simDepth == 0 && !inScorerSim && !creativeModel;')
    s = replace(s, 'inScorerSim = suppress;', 'inScorerSim = suppress || creativeModel;')
    s = replace(s, 'return game.racecraftNext.enabled(game, player, feature);', 'return !creativeModel && game.racecraftNext.enabled(game, player, feature);')
    s = replace(s, 'return simDepth == 0 && !inScorerSim && game.racecraftNext.enabled(game, player, feature)', 'return !creativeModel && simDepth == 0 && !inScorerSim && game.racecraftNext.enabled(game, player, feature)')
    s = replace(s, '|| game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.RESPONSE_STRATEGY)) {', '|| game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.RESPONSE_STRATEGY)\n                    || game.racecraftNext.creativeEnabled(game, playerNum)) {')
    s = replace(s, '|| game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.CONTINUATION_POLICIES))) inheritedTraffic = entry;', '|| game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.CONTINUATION_POLICIES)\n                        || game.racecraftNext.creativeEnabled(game, playerNum))) inheritedTraffic = entry;')
    s = replace(s, '&& !game.racecraftNext.configured(RacecraftNext.Feature.CONTINUATION_POLICIES)) return;', '&& !game.racecraftNext.configured(RacecraftNext.Feature.CONTINUATION_POLICIES)\n                && !game.racecraftNext.creativeConfigured()) return;')
    s = replace(s, '|| nextEnabled(player, RacecraftNext.Feature.CONTINUATION_POLICIES);', '|| nextEnabled(player, RacecraftNext.Feature.CONTINUATION_POLICIES) || creativeRoot(player);')
    s = replace(s, 'cands.size() < 2 && !tactical && !manoeuvre)', 'cands.size() < 2 && !tactical && !manoeuvre && !creativeRoot(playerNum))')
    s = replace(s, '        if (real) auditOpening = planned;', '''        if (real && creativeRoot(playerNum)) {
            final java.util.List<Direction> incumbentPlan = new java.util.ArrayList<>();
            incumbentPlan.add(planned);
            if (pendingFirst == planned && pendingFollowup != null && !pendingFollowup.response())
                incumbentPlan.addAll(pendingFollowup.actions());
            final CreativeTactics.Choice choice = CreativeTactics.choose(game, incumbentPlan, inheritedTraffic);
            if (choice.accepted()) {
                pendingFirst = choice.action(); pendingFollowup = choice.tail(); planned = choice.action();
            }
            if (game.racecraftNext.capture && !game.racecraftReplay)
                System.err.println("RACECRAFT_CREATIVE p=" + playerNum + " proposals=" + choice.proposals()
                        + " forecasts=" + choice.forecasts() + " accepted=" + choice.accepted() + " checked=" + choice.checked());
        }
        if (real) auditOpening = planned;''')
    s = replace(s, '    Direction researchScorer() {', '''    /** Complete top-level champion decision, with lower-level calls suppressed.
     * No experimental feature may recursively invoke this model. */
    Direction researchFullFirst() {
        final boolean old = creativeModel, oldScorer = inScorerSim;
        creativeModel = true; inScorerSim = false;
        try { return computeAiMove(); }
        finally { creativeModel = old; inScorerSim = oldScorer; }
    }

    private boolean creativeRoot(final int player) {
        return !creativeModel && simDepth == 0 && !inScorerSim && game.racecraftNext.creativeEnabled(game, player)
                && nearestLiveRival(game.players[player - 1].getPosition(), player) <= AI1_CHOOSER_MAXDIST;
    }

    Direction researchScorer() {''')
    p.write_text(s)

p = ROOT / 'src/tr/logic/RacecraftReplay.java'
s = p.read_text()
if 'game.racecraftNext.creativeConfigured()' not in s:
    s = replace(s, '|| game.racecraftNext.configured(RacecraftNext.Feature.CONTINUATION_POLICIES)))',
                '|| game.racecraftNext.configured(RacecraftNext.Feature.CONTINUATION_POLICIES)\n                    || game.racecraftNext.creativeConfigured()))')
    p.write_text(s)
p = ROOT / 'src/tr/logic/MoveQueries.java'
s = p.read_text()
if 'TacticBreeder.answer' not in s:
    s = replace(s, '        if (line.startsWith("cf4,"))', '        if (line.startsWith("breed1,")) return TacticBreeder.answer(game, line);\n        if (line.startsWith("cf4,"))')
    p.write_text(s)

# These new comparisons always use known place first, then own time; unknown
# checker results are rejected, never improved by merely changing model tier.
p = ROOT / 'src/tr/logic/CreativeTactics.java'; s = p.read_text()
s = s.replace('candidate.outcome().betterThan(base.outcome(), false)', 'better(candidate.outcome(), base.outcome())')
s = s.replace('trial.outcome().betterThan(value.outcome(), false)', 'better(trial.outcome(), value.outcome())')
s = replace(s, '    static Judgement check(', '''    static boolean better(final RacecraftOutcome candidate, final RacecraftOutcome incumbent) {
        return candidate != null && incumbent != null && candidate.known() && incumbent.known()
                && (candidate.ahead() < incumbent.ahead() || candidate.ahead() == incumbent.ahead()
                        && candidate.time() < incumbent.time());
    }
    static Judgement check(''')
p.write_text(s)
p = ROOT / 'src/tr/logic/SelfishSearch.java'; s = p.read_text()
s = s.replace('row[1] == Player.Kind.HUMAN.ordinal()', '(row[1] != Player.Kind.AI1.ordinal() && row[1] != Player.Kind.AI2.ordinal())')
p.write_text(s)

p = ROOT / 'run_tests.sh'; s = p.read_text()
if 'tr.logic.CreativeRacecraftTests' not in s:
    s += '\njava -ea -Djava.awt.headless=true -cp test-bin tr.logic.CreativeRacecraftTests\n'
    p.write_text(s)
p = ROOT / 'racing-memory.md'; s = p.read_text()
heading = '## Creative racecraft branch (2026-10-11, not promoted)'
if heading not in s:
    title, rest = s.split('\n', 1)
    s = title + '\n\n' + heading + '''

Opt-in endpoint-preserving feints, complete-layer ambush proposals, poisoned gaps
and three-car traffic judo, terminal self-interested search, and a separate
full-first-response acceptance check. Offline breed1 tails mutate legal own
prefixes while opponents recompute; no learned policy is installed. New queries
and hints are read-only, stored suffixes are commit-only, all defaults and the
computed-start/20-cell rules are retained. Implementation is under validation;
no fleet gain or promotion is claimed. See docs/experiments/creative-racecraft.
''' + rest
    p.write_text(s)
print('Applied six isolated creative racecraft experiments; promotion disabled')
