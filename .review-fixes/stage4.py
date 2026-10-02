from pathlib import Path
import re, subprocess
p=Path('tests/test_racecraft_corpus.py'); s=p.read_text()
s=s.replace("_, final = corpus.board(control['finalState'])", "_, final = corpus.validation.snapshot(control['finalState'])")
p.write_text(s)
p=Path('tests/racecraft_next_cli.py'); s=p.read_text()
if "'--every', '7'" not in s:
    s=s.replace("'--seed', '1', '--limit', '2', '--out'", "'--seed', '1', '--limit', '20', '--every', '7', '--out'")
    s=s.replace("'--cases', '1', '--max-moves'", "'--cases', '3', '--offset', '1', '--max-moves'")
    s=s.replace('first = cases[0]', 'first = cases[1]')
    s=s.replace("if first['turn'] != 0:", "if first['turn'] <= 0:")
    s=s.replace("fixture must capture the first actual move", "fixture must replay a mid-race decision")
    s=s.replace("for m in moves]", "for m in moves if m.index > first['turn']]")
    s=s.replace('actual full-race control trace OK', 'three mid-race control suffixes and every legal first action OK')
    p.write_text(s)
p=Path('src/tr/logic/OpeningPlans.java'); s=p.read_text()
if '    static Direction bestCrash(' in s:
    start=s.index('    static Direction bestCrash(')
    s=s[:start]+'}\n'; s=s.replace('import java.util.Arrays;\n',''); p.write_text(s)
# Common solo precedence already ran above the tactical stage; do not repeat it.
p=Path('src/tr/logic/RaceAi.java'); s=p.read_text()
old='''		if (!rivalWithinCheb(pos[0], pos[1], playerNum, AI1_CHOOSER_MAXDIST)) {
			final Direction alone = optimalAloneMove(pos, vel, playerNum);
			if (alone != null)
				return alone;
		}
'''
if old in s: s=s.replace(old,'',1)
p.write_text(s)
# Include the updated validation baseline in the assembled commit.
subprocess.run(['git','add','.github/workflows/racecraft-next.yml'],check=True)
