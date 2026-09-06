#!/usr/bin/env python3
"""Exact last-rival blocks, including array wrap, retired slots and both AI labels.

These are constructed tactical boards, not claimed naturally occurring races.
The old 8db66b3 policy missed these blocks; its ordinary continuation lost the
seven original-slot cases. A blocked opponent has NO legal acceleration, independently
of how clever its policy is. The full referee mask checks all nine replies.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracks.forensics_common import DIRS, parse_v2_answer  # noqa: E402

# mover (x,y,vx,vy), rival (x,y,vx,vy), one physically identical board per slot order
CASES = [
    ((14,16,2,4), (16,23,1,-4)),
    ((73,27,3,-7), (76,15,1,6)),
    ((15,22,2,2), (17,25,1,-2)),
    # Independent same-heading discovery seed 20260906: an actual positional
    # fight, rather than an opposing-heading interception.
    ((7,11,-2,-4), (5,10,-1,-4)),
    ((16,12,1,2), (14,16,4,-1)),
    ((73,12,3,-1), (75,7,2,3)),
    ((18,6,-1,7), (22,9,-4,5)),
]


def query(mover, cars, turn=100):
    return f'v2,{mover},{turn},1;' + ';'.join(','.join(map(str, c)) for c in cars)


def requests(players):
    lines = []
    for mine, other in CASES:
        for mover, rival in ((0, players-1), (players-1, 0)):
            cars = [(-100000,-100000,0,0,99,0,0)] * players
            cars[mover] = (*mine,0,0,0)
            cars[rival] = (*other,0,0,0)
            lines.append(query(mover,cars))
            # The exact winning move is NONE (coast onto the sole rival exit).
            x,y,vx,vy = mine
            cars[mover] = (x+vx,y+vy,vx,vy,0,0,0)
            lines.append(query(rival,cars,101))
    return lines


def main():
    jar = ROOT / 'theoreticRacing.jar'
    if not jar.is_file():
        raise SystemExit('Build theoreticRacing.jar before running this test')
    tested = 0
    with tempfile.TemporaryDirectory(prefix='racing-racecraft-') as tmp:
        install = Path(tmp)
        shutil.copyfile(jar, install/'theoreticRacing.jar')
        (install/'tracks').mkdir()
        shutil.copyfile(ROOT/'tests/fixtures/racecraft_hairpin.track', install/'tracks/hairpin.track')
        for kind in ('AI1','AI2'):
            for players in (2,8):
                props = install/'profile.properties'
                props.write_text(f'nPlayers={players}\nlaps=1\n'+''.join(
                    f'player{i}Kind={kind}\n' for i in range(1,players+1)),encoding='utf-8')
                source, destination = install/'requests.txt', install/'answers.txt'
                lines = requests(players)
                source.write_text('\n'.join(lines)+'\n',encoding='utf-8')
                run = subprocess.run(['java','-Xmx256m','-Djava.awt.headless=true','-jar',
                    str(install/'theoreticRacing.jar'),'--auto','--track','hairpin','--props',str(props),
                    '--query-moves',str(source),str(destination)],capture_output=True,text=True,timeout=120)
                if run.returncode:
                    raise AssertionError(run.stdout+'\n'+run.stderr)
                answers = destination.read_text(encoding='utf-8').splitlines()
                assert len(answers) == len(lines), 'missing query result'
                for index in range(0,len(answers),2):
                    dx,dy,mask = parse_v2_answer(answers[index],1)
                    assert (dx,dy) == (0,0), (kind,players,lines[index],answers[index])
                    assert mask.transitions[DIRS.index((dx,dy))].status == 'OK', answers[index]
                    _,_,reply = parse_v2_answer(answers[index+1],1)
                    assert all(t.status == 'CRASH' for t in reply.transitions), (lines[index+1],reply)
                    tested += 1
    print(f'Racecraft: OK ({tested} winning boards; every rival reply checked; both kinds and slot orders)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
