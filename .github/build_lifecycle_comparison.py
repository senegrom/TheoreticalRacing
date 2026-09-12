#!/usr/bin/env python3
"""Validation-only dispatch: fixed versus byte-derived base scorer, in one JAR.
Run only in a disposable checkout after applying the production patch.
"""
import hashlib
from pathlib import Path
import re
import subprocess
import sys
root = Path.cwd()
base = sys.argv[1]
for name in ('RaceAi', 'RaceAiPrivateLane'):
    path = 'src/tr/logic/' + name + '.java'
    original = subprocess.check_output(['git', 'show', base + ':' + path]).decode('utf-8')
    replaced = re.sub(r'\bRaceAiPrivateLane\b', 'RaceAiPrivateLaneBaseline', original)
    replaced = re.sub(r'\bRaceAi\b', 'RaceAiBaseline', replaced)
    restored = replaced.replace('RaceAiPrivateLaneBaseline', 'RaceAiPrivateLane').replace('RaceAiBaseline', 'RaceAi')
    assert restored == original, 'baseline renaming changed non-identifier content'
    (root / 'src/tr/logic' / (name + 'Baseline.java')).write_text(replaced)
    print(name, 'base source SHA256', hashlib.sha256(original.encode()).hexdigest())
path = root / 'src/tr/logic/RaceAiTactics.java'
s = path.read_text()
old = '        if (realDecision && game.candidatePolicy(playerNumber))\n            return RaceAiDuelSearch.winWithinThreeMoves(game, playerNumber);\n'
assert s.count(old) == 1
path.write_text(s.replace(old, '        // Measurement only: third-move experiment is OFF for both cohorts.\n'))
path = root / 'src/tr/logic/RaceGame.java'
s = path.read_text()
old = 'executeMove(ai.computeAiMove());'
assert s.count(old) == 1
s = s.replace(old, 'executeMove(reviewComparisonMove());')
old = '\tfinal RaceAi ai = new RaceAi(this);'
assert s.count(old) == 1
s = s.replace(old, old + '''
    private final RaceAiBaseline reviewBaseline = new RaceAiBaseline(this);
    private int reviewCandidateMoves, reviewBaselineMoves;
    private Direction reviewComparisonMove() {
        if (candidatePolicy(players[subgamestate].getNumber())) {
            reviewCandidateMoves++;
            return ai.computeAiMove();
        }
        reviewBaselineMoves++;
        return reviewBaseline.computeAiMove();
    }
''')
old = '\t\t\tgameLog.append("# results\\n");'
assert s.count(old) == 1
s = s.replace(old, '''            gameLog.append("# reviewPolicyMoves candidate=").append(reviewCandidateMoves)
                    .append(" baseline=").append(reviewBaselineMoves).append('\\n');
''' + old)
path.write_text(s)
print('Comparison dispatch: fixed candidate / unchanged base control; third move disabled for BOTH')
