#!/usr/bin/env python3
"""Validation-only before/after cohort shim. Never included in production."""
from pathlib import Path
import re
import os
import subprocess
BASE=os.environ.get('REVIEW_BASE', '9668703dc1489383bde78f2460476e9f6daa1da0')
def old(path):
    return subprocess.check_output(['git','show',BASE+':'+path],text=True)
p=Path('src/tr/logic/RaceAiPrivateLane.java')
before=old(str(p)).replace('RaceAiPrivateLane','RaceAiPrivateLaneBeforeReview')
p.with_name('RaceAiPrivateLaneBeforeReview.java').write_text(before)
s=p.read_text()
s=s.replace('private final int playerNum;', 'private final RaceAiPrivateLaneBeforeReview.ProofSession baseline;\n\t\tprivate final int playerNum;',1)
s=s.replace('this.playerNum = playerNum;', 'baseline = game.candidatePolicy(playerNum) ? null : new RaceAiPrivateLaneBeforeReview(game).begin(playerNum, rectangles.minX.length - 1, exactNodeBudget);\n\t\t\tthis.playerNum = playerNum;',1)
for name in ('certifiesApproximate','certifiesExact'):
    pos=s.index('boolean '+name+'('); brace=s.index('{',pos)
    delegate='\n\t\t\tif (baseline != null) return baseline.'+name+'(x, y, vx, vy, turns, horizon, requiredEscapes);'
    s=s[:brace+1]+delegate+s[brace+1:]
p.write_text(s)
p=Path('src/tr/logic/RaceAi.java');s=p.read_text();b=old(str(p))
start=s.index('\tprivate int simOutcomeCore(');end=s.index('\n\t/** Danger joint search',start)
bstart=b.index('\tprivate int simOutcomeCore(');bend=b.index('\n\t/** Danger joint search',bstart)
reviewed=s[start:end];original=b[bstart:bend]
signature=reviewed[:reviewed.index('{')+1]
args=re.findall(r'\bfinal\s+[\w\[\]]+\s+(\w+)',signature)
assert len(args)==19, args
args=', '.join(args)
wrapper=signature+'\n\t\treturn game.candidatePolicy(playerNum) ? simOutcomeCoreReviewed('+args+') : simOutcomeCoreBeforeReview('+args+');\n\t}\n\n'
s=s[:start]+wrapper+reviewed.replace('private int simOutcomeCore(', 'private int simOutcomeCoreReviewed(',1)+original.replace('private int simOutcomeCore(', 'private int simOutcomeCoreBeforeReview(',1)+s[end:]
p.write_text(s)
p=Path('src/tr/logic/RaceAiTactics.java');s=p.read_text()
needle='''        if (realDecision && game.candidatePolicy(playerNumber))
            return RaceAiDuelSearch.winWithinThreeMoves(game, playerNumber);
'''
assert s.count(needle)==1
p.write_text(s.replace(needle, '        // Cohort experiment: both sides retain the same two-move champion.\n'))
print('Measurement-only before/after shim installed; third-move candidate disabled on both sides.')
