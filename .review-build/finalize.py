"""Final exact-context integration. Removed after the branch is assembled."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def edit(path, old, new):
    p = ROOT / path
    text = p.read_text(encoding='utf-8')
    if text.count(old) != 1:
        raise RuntimeError(f'{path}: integration anchor count {text.count(old)}: {old[:80]}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')

edit('src/tr/logic/RaceAi.java', '\tprivate void reviewStage(final String name, final Direction action) {', '''\t/** Use the owner's one authoritative radius for experimental duel activation. */
\tboolean reviewTrafficNearby(final int playerNum) {
\t\tfor (final Player p : game.players)
\t\t\tif (p.getNumber() == playerNum) {
\t\t\t\tfinal int[] pos = p.getPosition();
\t\t\t\treturn rivalWithinCheb(pos[0], pos[1], playerNum, AI1_CHOOSER_MAXDIST);
\t\t\t}
\t\treturn false;
\t}

\tprivate void reviewStage(final String name, final Direction action) {''')
for feature, variable in [('DUEL_ANYTIME', 'retain'), ('DUEL_CACHE', 'cache')]:
    edit('src/tr/logic/RaceAiTactics.java',
         f'final boolean {variable} = RacecraftReview.enabled(game, playerNumber, RacecraftReview.Feature.{feature});',
         f'final boolean {variable} = game.ai.reviewTrafficNearby(playerNumber)\n                    && RacecraftReview.enabled(game, playerNumber, RacecraftReview.Feature.{feature});')
edit('src/tr/logic/RaceAi.java',
     'RacecraftReview.shortlist(scoreByDir, bestScore, diverse)',
     'RacecraftReview.shortlist(scoreByDir, bestScore, AI1_CHOOSER_WIDTH, AI1_CHOOSER_WINDOW, diverse)')
edit('src/tr/logic/RacecraftReview.java',
     'static Direction[] shortlist(final double[] scores, final double bestScore, final boolean diverse) {',
     '''static Direction[] shortlist(final double[] scores, final double bestScore,
            final int width, final double window, final boolean diverse) {
        if (width < 1 || width > DIRECTIONS.length || !Double.isFinite(window) || window < 0)
            throw new IllegalArgumentException("invalid shortlist limits");''')
edit('src/tr/logic/RacecraftReview.java', 'score > bestScore + 1.0', 'score > bestScore + window')
edit('src/tr/logic/RacecraftReview.java', 'Math.min(3, sorted.size())', 'Math.min(width, sorted.size())')
edit('src/tr/logic/RacecraftReview.java', 'score > bestScore + 2.0', 'score > bestScore + window + 1.0')
p = ROOT / 'tests/tr/logic/RacecraftReviewTests.java'
s = p.read_text(encoding='utf-8').replace('shortlist(scores, 0, ', 'shortlist(scores, 0, 3, 1.0, ')
p.write_text(s, encoding='utf-8')
edit('tests/tr/logic/RacecraftReviewTests.java', '        testConfiguration();',
     '        testConfiguration();\n        testExperimentalSoloBoundary();')
edit('tests/tr/logic/RacecraftReviewTests.java', '    private static void expectInvalid(final Properties p) {', '''    private static void testExperimentalSoloBoundary() {
        final Properties p = new Properties();
        p.setProperty("candidateSlots", "1");
        p.setProperty("racecraftReview", "all");
        final RaceGame g = new RaceGame(p);
        g.players = new Player[]{car(1, 50, 10, 3, 0), car(2, 70, 10, 0, 0)};
        check(g.ai.reviewTrafficNearby(1), "twenty cells excluded from experiment boundary");
        g.players[1].setPosition(new int[]{71, 10});
        check(!g.ai.reviewTrafficNearby(1), "duel experiment can activate at twenty-one cells");
        g.players[1].setPosition(new int[]{51, 10});
        g.players[1].setFinishedPlace(1);
        check(!g.ai.reviewTrafficNearby(1), "retired rival activates duel experiment");
        check(!g.ai.reviewTrafficNearby(9), "missing mover activates duel experiment");
    }

    private static void expectInvalid(final Properties p) {''')
