"""One-shot, exact-context source integration on the pinned review baseline.
Used only to assemble this branch through the authorized GitHub connection.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def edit(path, old, new):
    file = ROOT / path
    text = file.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one integration anchor, found {count}: {old[:90]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")

edit("src/tr/logic/RaceGame.java", "\tprivate final Properties\tprop;",
     "\tprivate final Properties\tprop;\n\tfinal RacecraftReview.Config racecraftReview;")
edit("src/tr/logic/RaceGame.java", "\t\tthis.prop = prop;",
     "\t\tthis.prop = prop;\n\t\tracecraftReview = RacecraftReview.Config.from(prop);")
edit("src/tr/logic/RaceAiTactics.java", "        if (realDecision)\n            return RaceAiDuelSearch.winWithinFourMoves(game, playerNumber);",
'''        if (realDecision) {
            final boolean retain = RacecraftReview.enabled(game, playerNumber, RacecraftReview.Feature.DUEL_ANYTIME);
            final boolean cache = RacecraftReview.enabled(game, playerNumber, RacecraftReview.Feature.DUEL_CACHE);
            if (retain || cache || game.racecraftReview.audit)
                return RaceAiDuelSearch.winWithinFourMoves(game, playerNumber, retain, cache, game.racecraftReview.audit);
            return RaceAiDuelSearch.winWithinFourMoves(game, playerNumber);
        }''')
edit("src/tr/logic/RaceAi.java", "\tprivate final RaceAiPrivateLane privateLane;",
'''\tprivate final RaceAiPrivateLane privateLane;
\tprivate RacecraftReview.Trace reviewTrace;
\tprivate int reviewProjectedDepth = -1;
\tprivate int reviewReplyDepth = -1;
\tprivate int reviewReplyRival = -1;
\tprivate boolean reviewReplyUsed;

\tprivate void reviewStage(final String name, final Direction action) {
\t\tif (reviewTrace != null && simDepth == 0 && !inScorerSim) reviewTrace.stage(name, action);
\t}
''')
edit("src/tr/logic/RaceAi.java", "\t\treturn optimalMoveAI1(pos, vel, playerNum);",
'''\t\tfinal boolean root = simDepth == 0 && !inScorerSim;
\t\tfinal RacecraftReview.Trace previousTrace = reviewTrace;
\t\tif (root) reviewTrace = game.racecraftReview.audit ? new RacecraftReview.Trace(game, playerNum) : null;
\t\ttry {
\t\t\tfinal Direction action = optimalMoveAI1(pos, vel, playerNum);
\t\t\tif (root && reviewTrace != null) reviewTrace.emit(action);
\t\t\treturn action;
\t\t} finally {
\t\t\tif (root) reviewTrace = previousTrace;
\t\t}''')
edit("src/tr/logic/RaceAi.java", "\t\tboolean chooserConsulted = false;",
     '\t\treviewStage("scorer", best);\n\t\tboolean chooserConsulted = false;')
edit("src/tr/logic/RaceAi.java", "\t\t\tchooserConsulted = true;",
     '\t\t\tchooserConsulted = true;\n\t\t\treviewStage("chooser", best);')
edit("src/tr/logic/RaceAi.java", "\t\tDirection chosen = (poDir != null && poBestT < poScorerT) ? poDir : best;",
'''\t\treviewStage("tie-break", best);
\t\tDirection chosen = (poDir != null && poBestT < poScorerT) ? poDir : best;
\t\treviewStage("pace", chosen);''')
for method, label in [("privatePaceOverride", "private-pace"), ("stagedPaceOverride", "staged-pace"), ("guardedFieldPaceOverride", "field-pace")]:
    file = ROOT / "src/tr/logic/RaceAi.java"
    text = file.read_text(encoding="utf-8")
    start = text.index("\t\t\tchosen = " + method + "(")
    end = text.index(";", start) + 1
    text = text[:end] + f'\n\t\t\treviewStage("{label}", chosen);' + text[end:]
    file.write_text(text, encoding="utf-8")
file = ROOT / "src/tr/logic/RaceAi.java"
text = file.read_text(encoding="utf-8")
method_start = text.index("\tprivate Direction jointChooser(")
start = text.rfind("\t/** Round 256: among the landings", 0, method_start)
if start < 0:
    raise RuntimeError("missing chooser documentation anchor")
end = text.index("\t/** Round 262: Chebyshev distance", method_start)
text = text[:start] + (ROOT / ".review-build/chooser.java.inc").read_text(encoding="utf-8") + text[end:]
file.write_text(text, encoding="utf-8")
edit("src/tr/logic/RaceAi.java", "\t\t\t\telse if (scorerSet[i])\n\t\t\t\t\tmoved = scorerMoveOverState",
'''\t\t\t\telse if (simDepth == reviewReplyDepth && i == reviewReplyRival && !reviewReplyUsed) {
\t\t\t\t\treviewReplyUsed = true;
\t\t\t\t\tmoved = scorerMoveOverState(i, px, py, vx, vy, alive, move, workspace, false);
\t\t\t\t} else if (scorerSet[i])
\t\t\t\t\tmoved = scorerMoveOverState''')
edit("src/tr/logic/RaceAi.java", "\t\treturn rankVerdict(myFinished ? aheadAtMyFinish : rivalsFinished, myTime);",
'''\t\tif (simDepth == reviewProjectedDepth && !myFinished && !raceOver
\t\t\t\t&& (exactPot != null || game.lapGates == null)) {
\t\t\tfinal int[] remainingTimes = new int[game.players.length];
\t\t\tfor (int i = 0; i < remainingTimes.length; i++)
\t\t\t\tremainingTimes[i] = alive[i] ? ttfFor(i, px[i], py[i], vx[i], vy[i]) : Integer.MAX_VALUE;
\t\t\tfinal int projectedAhead = RacecraftReview.projectedAhead(myIdx, rivalsFinished, remainingTimes, alive);
\t\t\tif (projectedAhead >= 0 && simDepth == placeKeyDepth)
\t\t\t\tplaceKey = projectedAhead * PLACE_KEY_STRIDE + (rounds - 1) + Math.min(myTime, PLACE_KEY_STRIDE / 2);
\t\t}
\t\treturn rankVerdict(myFinished ? aheadAtMyFinish : rivalsFinished, myTime);''')
edit("src/tr/logic/RaceAi.java", "\t\t\treturn simOutcomeCore(myX, myY, myVx, myVy, playerNum, rounds, simFinishVanish,",
     "\t\t\tfinal int result = simOutcomeCore(myX, myY, myVx, myVy, playerNum, rounds, simFinishVanish,")
edit("src/tr/logic/RaceAi.java", "\t\t\t\t\toutRivalCost, candidatePending);\n\t\t} finally {",
'''\t\t\t\t\toutRivalCost, candidatePending);
\t\t\tif (reviewTrace != null && simDepth == 1 && simDepth == placeKeyDepth)
\t\t\t\treviewTrace.endpoint(workspace.turns, game.aiGridLegal, workspace.px, workspace.py,
\t\t\t\t\t\tworkspace.vx, workspace.vy, workspace.laps, workspace.gates, workspace.alive);
\t\t\treturn result;
\t\t} finally {''')
edit("run_tests.sh", "java -ea -Djava.awt.headless=true -cp test-bin tr.logic.RaceAiDuelSearchTests",
     "java -ea -Djava.awt.headless=true -cp test-bin tr.logic.RaceAiDuelSearchTests\njava -ea -Djava.awt.headless=true -cp test-bin tr.logic.RacecraftReviewTests")
file = ROOT / "racing-memory.md"
text = file.read_text(encoding="utf-8")
first, rest = text.split("\n", 1)
entry = (ROOT / ".review-build/journal.md").read_text(encoding="utf-8")
file.write_text(first + "\n\n" + entry + "\n" + rest, encoding="utf-8")
