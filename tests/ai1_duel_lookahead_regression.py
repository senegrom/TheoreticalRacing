#!/usr/bin/env python3
"""Two-move blockade certificates through the real AI and V2 referee.

These are constructed positions discovered with seed 20260911, not claims of
naturally occurring race wins. Enumerate every physical rival reply, ask the
actual policy for its follow-up, then check every final reply. Both AI labels,
array-wrap orders and retired-slot rosters must carry out the promised win.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracks.forensics_common import DIRS, parse_v2_answer  # noqa: E402

CASES = [
    ((10, 14, 4, 0), (12, 15, 5, 0), (0, -1)),
    ((14, 15, 3, -1), (11, 16, 6, -1), (0, -1)),
    ((11, 18, 3, 1), (9, 23, 5, -3), (-1, 0)),
    ((9, 21, 5, -1), (15, 23, 2, -3), (-1, 1)),
    ((15, 8, 2, 1), (10, 13, 6, 1), (0, 1)),
    ((10, 9, 4, 1), (13, 14, 5, 0), (1, 0)),
    ((9, 22, 6, 1), (11, 26, 5, -1), (-1, 1)),
    ((8, 23, 6, -1), (8, 21, 6, 0), (-1, 1)),
]


def request(mover, cars, turn):
    return f'v2,{mover},{turn},1;' + ';'.join(','.join(map(str, c)) for c in cars)


def advance(cars, mover, direction, transition):
    result = list(cars)
    x, y, vx, vy, _, _, _ = cars[mover]
    dx, dy = direction
    result[mover] = (x+vx+dx, y+vy+dy, vx+dx, vy+dy, 0, transition.lap, transition.gate)
    return result


def query(install, lines, stage):
    source, destination = install / f'{stage}.requests', install / f'{stage}.answers'
    source.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    run = subprocess.run([
        'java', '-Xmx256m', '-Djava.awt.headless=true', '-jar', str(install/'theoreticRacing.jar'),
        '--auto', '--track', 'hairpin', '--props', str(install/'profile.properties'),
        '--query-moves', str(source), str(destination),
    ], capture_output=True, text=True, timeout=120)
    if run.returncode:
        raise AssertionError(run.stdout+'\n'+run.stderr)
    answers = destination.read_text(encoding='utf-8').splitlines()
    assert len(answers) == len(lines), 'incomplete oracle output'
    return [parse_v2_answer(line, 1) for line in answers]


def main():
    jar = ROOT/'theoreticRacing.jar'
    if not jar.is_file():
        raise SystemExit('Build theoreticRacing.jar before running this test')
    setups = continuations = 0
    with tempfile.TemporaryDirectory(prefix='racing-duel-proof-') as tmp:
        install = Path(tmp)
        shutil.copyfile(jar, install/'theoreticRacing.jar')
        (install/'tracks').mkdir()
        shutil.copyfile(ROOT/'tests/fixtures/racecraft_hairpin.track', install/'tracks/hairpin.track')
        for kind in ('AI1', 'AI2'):
            for players in (2, 8):
                (install/'profile.properties').write_text(
                    f'nPlayers={players}\nlaps=1\ncandidateSlots=1,{players}\n'+''.join(
                        f'player{i}Kind={kind}\n' for i in range(1, players+1)), encoding='utf-8')
                boards = []
                for mine, other, expected in CASES:
                    for mover, rival in ((0, players-1), (players-1, 0)):
                        cars = [(-100000, -100000, 0, 0, 99, 0, 0)]*players
                        cars[mover], cars[rival] = (*mine, 0, 0, 0), (*other, 0, 0, 0)
                        boards.append((cars, mover, rival, expected))
                roots = query(install, [request(m, c, 100) for c, m, _, _ in boards], 'roots')
                replies = []
                for (cars, mover, rival, expected), (dx, dy, mask) in zip(boards, roots):
                    assert (dx, dy) == expected, (kind, players, cars, (dx, dy), expected)
                    transition = mask.transitions[DIRS.index((dx, dy))]
                    assert transition.status == 'OK', transition
                    replies.append((advance(cars, mover, (dx, dy), transition), mover, rival))
                    setups += 1
                masks = query(install, [request(r, c, 101) for c, _, r in replies], 'rival')
                followups = []
                for (cars, mover, rival), (_, _, mask) in zip(replies, masks):
                    for direction, transition in zip(DIRS, mask.transitions):
                        assert transition.status != 'FINISH', 'rival can beat the promised setup'
                        if transition.status in ('OK', 'LAP'):
                            followups.append((advance(cars, rival, direction, transition), mover, rival))
                assert followups, 'no legal opposing continuations were exercised'
                choices = query(install, [request(m, c, 102) for c, m, _ in followups], 'followups')
                terminal = []
                for (cars, mover, rival), (dx, dy, mask) in zip(followups, choices):
                    transition = mask.transitions[DIRS.index((dx, dy))]
                    assert transition.status in ('OK', 'LAP', 'FINISH'), 'policy failed its proof'
                    if transition.status != 'FINISH':
                        terminal.append(request(rival, advance(cars, mover, (dx, dy), transition), 103))
                    continuations += 1
                if terminal:
                    for _, _, mask in query(install, terminal, 'terminal'):
                        assert all(t.status == 'CRASH' for t in mask.transitions), mask.transitions
    print(f'Duel lookahead: OK ({setups} setups; {continuations} legal rival continuations; '
          'actual AI follow-ups and all final physical replies checked)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
