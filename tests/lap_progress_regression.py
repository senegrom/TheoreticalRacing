#!/usr/bin/env python3
"""Non-final endgame safety and internal rollout/authoritative oracle agreement."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracks.forensics_common import DIRS  # noqa: E402

TRACE = re.compile(
    r'^SIMTRACE r=(\d+) i=(\d+) (\w+) '
    r'\((-?\d+),(-?\d+)\)v\((-?\d+),(-?\d+)\) -> '
    r'\((-?\d+),(-?\d+)\)v\((-?\d+),(-?\d+)\)'
    r'(?: (FINISH|LAP|CRASH|TIMEOUT))? progress=(\d+),(\d+)$', re.MULTILINE)


def run_queries(directory, laps, requests):
    props = directory / 'profile.properties'
    props.write_text('nPlayers=2\nplayer1Kind=AI1\nplayer2Kind=AI2\nlaps=%d\n' % laps, encoding='utf-8')
    source, answers = directory / 'queries.txt', directory / 'answers.txt'
    source.write_text('\n'.join(requests) + '\n', encoding='utf-8')
    run = subprocess.run(['java', '-Xmx1200m', '-Djava.awt.headless=true', '-jar',
                          str(ROOT / 'theoreticRacing.jar'), '--auto', '--track', 'circle',
                          '--props', str(props), '--query-moves', str(source), str(answers)],
                         capture_output=True, text=True, timeout=240)
    if run.returncode:
        raise AssertionError('oracle process failed\n' + run.stdout + '\n' + run.stderr)
    return answers.read_text(encoding='utf-8').splitlines(), run.stderr


def board_query(mover, clock, laps, cars):
    return 'v2,%d,%d,%d;' % (mover, clock, laps) + ';'.join(','.join(map(str, car)) for car in cars)


def decode(line):
    version, direction, mask, tokens = line.split(';')
    assert version == 'v2' and len(mask) == 9
    dx, dy = map(int, direction.split(','))
    transitions = [token.split(',') for token in tokens.split('|')]
    assert len(transitions) == 9
    return (dx, dy), mask, transitions


def main():
    with tempfile.TemporaryDirectory(prefix='racing-lap-progress-') as temporary:
        directory = Path(temporary)
        # The exact potential is over budget. Near S/F must not mean near victory.
        dangerous = 'v2,0,200,99;50,5,4,-2,0,0,0;48,8,4,0,0,0,0'
        answers, _ = run_queries(directory, 99, [dangerous])
        move, mask, transitions = decode(answers[0])
        chosen = DIRS.index(move)
        assert mask[chosen] == 'A' and transitions[chosen][:3] == ['LAP', '1', '1'], answers[0]

        # Recorded Circle board immediately before p2 passes CP1. Compare every
        # projected edge with the referee and every TRUE choice with a fresh
        # policy query on that exact projected position, clock and gate ledger.
        initial = [[75, 72, -4, 5, 0, 0, 2], [80, 64, -2, 5, 0, 0, 1]]
        request = 'sim2,0,6,true,2,31,2;' + ';'.join(','.join(map(str, car)) for car in initial)
        before = board_query(0, 31, 2, initial)
        answers, trace = run_queries(directory, 2, [before, request, before, request, before])
        assert answers[0] == answers[2] == answers[4], 'nested simulation leaked into next query'
        assert answers[1] == answers[3], 'same simulation changed with query history'
        entries = list(TRACE.finditer(trace))
        assert len(entries) == 22, 'incomplete six-round traces\n' + trace
        entries = entries[:11]  # second identical simulation is the isolation check
        cars = [car[:] for car in initial]
        clock = 31
        queries, expected = [], []
        for entry in entries:
            _, index, model = int(entry[1]), int(entry[2]), entry[3]
            x, y, vx, vy, nx, ny, nvx, nvy = map(int, entry.group(*range(4, 12)))
            status, lap, gate = entry[12] or 'OK', int(entry[13]), int(entry[14])
            assert cars[index][:4] == [x, y, vx, vy], 'rollout lost its projected position'
            queries.append(board_query(index, clock, 2, cars))
            expected.append((model, (nvx - vx, nvy - vy), status, lap, gate))
            cars[index] = [nx, ny, nvx, nvy, 0, lap, gate]
            if status in ('FINISH', 'CRASH', 'TIMEOUT'):
                cars[index][:5] = [-100000, -100000, 0, 0, 77]
            clock += 1
        replies, _ = run_queries(directory, 2, queries)
        assert len(replies) == len(expected)
        true_count = 0
        for reply, (model, acceleration, status, lap, gate) in zip(replies, expected):
            policy, mask, transitions = decode(reply)
            chosen = DIRS.index(acceleration)
            assert transitions[chosen][:3] == [status, str(lap), str(gate)], (reply, acceleration)
            assert mask[chosen] not in 'XB', (model, reply)
            if model == 'TRUE':
                true_count += 1
                assert policy == acceleration, ('TRUE prediction differs from real policy', policy, acceleration)
        assert expected[0][4] == 2 and true_count == 6, 'checkpoint was not advanced'
    print('LapProgress: OK (non-final endgame; 11 projected transitions; 6 TRUE choices; query isolation)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
