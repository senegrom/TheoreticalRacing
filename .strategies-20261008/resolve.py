from pathlib import Path
import re
import subprocess

p=Path('src/tr/logic/RaceAi.java')
text=p.read_text()
conflicts=list(re.finditer(r'^<<<<<<< .*?\n(.*?)^=======\n(.*?)^>>>>>>> .*?\n',text,re.M|re.S))
if conflicts:
    if len(conflicts)!=1 or 'private Direction jointChooser' not in conflicts[0].group(1):
        raise RuntimeError('unreviewed master/research conflict')
    text=text[:conflicts[0].start()]+conflicts[0].group(2)+text[conflicts[0].end():]
    for old,new in [
        ('final boolean addPace = pace != null && !cands.contains(pace);',
         'final boolean paceInSet = pace != null && cands.contains(pace);\n        final boolean addPace = pace != null && !paceInSet;'),
        ('long pickVerdict = -1;', 'long pickVerdict = -1;\n        long paceVerdict = Long.MIN_VALUE;'),
        ('if (pick == null || verdict >= 0 && (pickVerdict < 0 || verdict < pickVerdict)) { pick = d; pickVerdict = verdict; }',
         'if (d == pace) paceVerdict = verdict;\n            if (pick == null || verdict >= 0 && (pickVerdict < 0 || verdict < pickVerdict)) { pick = d; pickVerdict = verdict; }'),
        ('// Preserve round 292b exactly: existing in-window pace swaps remain authoritative.\n        chooserJudgedPace = addPace;',
         '// Preserve current master 301a: only exact faithful ties permit the map-time swap.\n        chooserJudgedPace = addPace || paceInSet && paceVerdict != pickVerdict;')]:
        if text.count(old)!=1: raise RuntimeError('missing reviewed chooser merge anchor: '+old)
        text=text.replace(old,new)
    p.write_text(text)
    subprocess.run(['git','add',str(p)],check=True)
    print('Resolved chooser conflict, retaining 301a tie-only pace authority and research candidates')
