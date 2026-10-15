from pathlib import Path
import re
import subprocess

conflicts = subprocess.check_output(['git','diff','--name-only','--diff-filter=U'], text=True).splitlines()
for name in conflicts:
    text = Path(name).read_text()
    def resolve(match):
        ours, theirs = match.group(1), match.group(2)
        if name == 'racing-memory.md': return theirs + '\n' + ours
        if name != 'src/tr/logic/RaceAi.java': raise RuntimeError('Unreviewed conflict '+name)
        if 'final boolean root = simDepth' in ours:
            return ('        final boolean memoOwner = simDepth == 0;\n'
                    '        if (memoOwner) { suppressedMoves.clear(); suppressedMovesOwned = true; }\n'
                    '        try {\n' + ours + '\n'
                    '        } finally { if (memoOwner) suppressedMovesOwned = false; }\n')
        if 'inScorerSim = suppress || creativeModel;' in ours:
            return theirs.replace('suppress || awarePolicyDepth > 0', 'suppress || awarePolicyDepth > 0 || creativeModel')
        if 'workspace.researchOwnMoves == 2' in ours:
            return ours.replace('} else if (i == myIdx)', '} else '+theirs.lstrip())
        if 'Compatibility test/query seam' in ours:
            text = ours.replace('        Direction pick = null;',
                '        if (real && trueConfirmDepth == 0) trafficFronts.clear();\n        Direction pick = null;')
            text = text.replace('            placeKeyDepth = simDepth + 1;',
                '            final int outerAwareDepth = awareDepth, outerAwareRival = awareRival;\n'
                '            if (real && trueConfirmDepth == 0 && !creativeModel) {\n'
                '                awareDepth = simDepth + 1;\n'
                '                awareRival = relevantRival(playerNum, pos, nx, ny, nvx, nvy);\n'
                '            } else awareDepth = -1;\n'
                '            placeKeyDepth = simDepth + 1;')
            text = text.replace('} finally { placeKeyDepth = outerKeyDepth; allScorerRolloutDepth = outerScorerDepth; }',
                '} finally { placeKeyDepth = outerKeyDepth; allScorerRolloutDepth = outerScorerDepth; awareDepth = outerAwareDepth; awareRival = outerAwareRival; }')
            return text
        if 'private RacecraftOutcome researchForecast' in ours and 'awareMoveOverState' in theirs:
            return ours + '\n' + theirs
        raise RuntimeError('Unreviewed RaceAi conflict: '+ours[:150])
    text, n = re.subn(r'^<<<<<<<[^\n]*\n(.*?)^=======\n(.*?)^>>>>>>>[^\n]*\n', resolve, text, flags=re.M|re.S)
    if not n or '<<<<<<<' in text: raise RuntimeError('Unresolved '+name)
    Path(name).write_text(text)
    subprocess.run(['git','add',name], check=True)
print('Reviewed integration conflicts resolved; current aware and memo policies retained')
