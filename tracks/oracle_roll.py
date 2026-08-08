#!/usr/bin/env python3
"""Perfect-fidelity joint rollout through the game's interactive move oracle.

Usage:
  oracle_roll.py verify <log> <track> <moveIdx> [rounds]
  oracle_roll.py cand   <log> <track> <moveIdx> [rounds]

Requires theoreticRacing.jar in the repo root, tracks/bench.properties, and
reach_<track>.bin in RACING_WORK_DIR (default: tracks/).
"""
from pathlib import Path
import os
import re
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORK = Path(os.environ.get('RACING_WORK_DIR', HERE))
JAR = ROOT / 'theoreticRacing.jar'
PROPS = HERE / 'bench.properties'
DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
DIRNAMES = ['NW', 'N', 'NE', 'W', 'NONE', 'E', 'SW', 'S', 'SE']
INF = 2_147_483_647

MOVE = re.compile(
    r'^(?P<t>\d+) p(?P<p>\d+) \S+ (?P<dir>\S+) '
    r'v\((?P<vx0>-?\d+),(?P<vy0>-?\d+)\)→\((?P<vx1>-?\d+),(?P<vy1>-?\d+)\) '
    r'\((?P<x0>-?\d+),(?P<y0>-?\d+)\)→\((?P<x1>-?\d+),(?P<y1>-?\d+)\) '
    r'(?P<status>ok|CRASH|FINISH)')
START = re.compile(r'^player(?P<p>\d+) name=.*? kind=\S+ start=(?P<x>-?\d+),(?P<y>-?\d+)')
ANSWER = re.compile(r'^(-?\d+),(-?\d+);([FXBDA]{9})$')


class Reach:
    def __init__(self, path):
        data = Path(path).read_bytes()
        self.w, self.h, self.vmax = struct.unpack_from('<iii', data, 0)
        self.span = 2 * self.vmax + 1
        self.arr = memoryview(data)[12:].cast('i')

    def turns(self, x, y, vx, vy):
        if not (0 <= x < self.w and 0 <= y < self.h) or abs(vx) > self.vmax or abs(vy) > self.vmax:
            return None
        idx = ((x * self.h + y) * self.span + vx + self.vmax) * self.span + vy + self.vmax
        value = self.arr[idx]
        return None if value == INF else value


class Oracle:
    def __init__(self, track):
        self.proc = subprocess.Popen(
            ['java', '-jar', str(JAR), '--auto', '--track', track, '--props', str(PROPS),
             '--seed', '1', '--query-moves', '-', '-'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8', bufsize=1)

    def ask(self, mover, cars):
        query = str(mover) + ';' + ';'.join('%d,%d,%d,%d,%d' % tuple(car) for car in cars)
        self.proc.stdin.write(query + '\n')
        self.proc.stdin.flush()
        for line in self.proc.stdout:
            match = ANSWER.match(line.strip())
            if match:
                return int(match.group(1)), int(match.group(2)), match.group(3)
        raise RuntimeError('oracle died')

    def close(self):
        try:
            self.proc.stdin.write('quit\n')
            self.proc.stdin.flush()
        except OSError:
            pass
        self.proc.terminate()


def board_at(log, target):
    """Return the board just before global move target, its mover, and later real moves."""
    cars = [None] * 8
    mover = None
    real = []
    for line in Path(log).read_text(encoding='utf-8', errors='replace').splitlines():
        start = START.match(line)
        if start:
            i = int(start['p']) - 1
            cars[i] = [int(start['x']), int(start['y']), 0, 0, 0]
            continue
        move = MOVE.match(line)
        if not move:
            continue
        t = int(move['t'])
        i = int(move['p']) - 1
        if t < target:
            status = move['status']
            if status == 'CRASH':
                cars[i][4] = 99
            elif status == 'FINISH':
                cars[i][4] = 90
            else:
                cars[i] = [int(move['x1']), int(move['y1']), int(move['vx1']), int(move['vy1']), 0]
            continue
        if t == target and mover is None:
            mover = i
        real.append((t, i + 1, move['dir'], int(move['x1']), int(move['y1']), move['status']))

    if mover is None or any(car is None for car in cars):
        raise ValueError('log does not contain a complete board at the requested move')
    return [tuple(car) for car in cars], mover, real


def apply_move(cars, i, dx, dy, mask):
    x, y, vx, vy, _ = cars[i]
    outcome = mask[DIRS.index((dx, dy))]
    cars = list(cars)
    if outcome == 'F':
        cars[i] = (x, y, vx, vy, 90)
        return cars, 'FINISH'
    if outcome in 'XB':
        cars[i] = (x, y, vx, vy, 99)
        return cars, 'CRASH'
    nvx, nvy = vx + dx, vy + dy
    cars[i] = (x + nvx, y + nvy, nvx, nvy, 0)
    return cars, 'ok'


def roll(oracle, cars, first_mover, rounds, watch):
    cars = list(cars)
    i = first_mover % 8
    completed = 0
    while completed < rounds:
        if cars[i][4] == 0:
            dx, dy, mask = oracle.ask(i, cars)
            cars, fate = apply_move(cars, i, dx, dy, mask)
            if i == watch and fate != 'ok':
                return fate, completed, cars
        i = (i + 1) % 8
        if i == 0:
            completed += 1
        if all(car[4] != 0 for car in cars):
            break
    return 'alive', rounds, cars


def verify(oracle, cars, mover, real, rounds):
    simulated = []
    current = list(cars)
    i = mover
    while len(simulated) < rounds * 8 and not all(car[4] != 0 for car in current):
        if current[i][4] == 0:
            dx, dy, mask = oracle.ask(i, current)
            current, fate = apply_move(current, i, dx, dy, mask)
            simulated.append((i + 1, DIRNAMES[DIRS.index((dx, dy))], current[i][0], current[i][1], fate))
        i = (i + 1) % 8

    ok = True
    for sim, observed in zip(simulated, real):
        t, player, direction, x, y, status = observed
        sim_status = 'ok' if sim[4] == 'ok' else sim[4]
        match = sim[0] == player and sim[1] == direction and (sim_status != 'ok') == (status != 'ok')
        ok &= match
        print('  %s sim p%d %-4s ->(%d,%d) %s | real t=%d p%d %-4s ->(%d,%d) %s'
              % ('OK ' if match else 'DIFF', sim[0], sim[1], sim[2], sim[3], sim[4],
                 t, player, direction, x, y, status))
        if not match:
            break
    print('VERIFY: %s' % ('EXACT MATCH (%d moves)' % len(simulated) if ok else 'DIVERGED'))


def candidates(oracle, reach, cars, mover, rounds):
    x, y, vx, vy, _ = cars[mover]
    _, _, mask = oracle.ask(mover, cars)
    print('mover p%d candidates (mask %s):' % (mover + 1, mask))
    for ci, (dx, dy) in enumerate(DIRS):
        outcome = mask[ci]
        if outcome in 'XB':
            print('  %-4s %s -- fatal immediately' % (DIRNAMES[ci], outcome))
            continue
        if outcome == 'F':
            print('  %-4s F -- finishes' % DIRNAMES[ci])
            continue
        nvx, nvy = vx + dx, vy + dy
        next_cars = list(cars)
        next_cars[mover] = (x + nvx, y + nvy, nvx, nvy, 0)
        fate, round_no, final = roll(oracle, next_cars, mover + 1, rounds, mover)
        fx, fy, fvx, fvy, _ = final[mover]
        suffix = ''
        if fate == 'alive':
            turns = reach.turns(fx, fy, fvx, fvy)
            suffix = ' (final t=%s)' % ('DOOMED' if turns is None else turns)
        else:
            fate = '%s @round %d' % (fate, round_no)
        print('  %-4s %s land=(%d,%d) v(%d,%d): %s%s'
              % (DIRNAMES[ci], outcome, x + nvx, y + nvy, nvx, nvy, fate, suffix))


def main(argv):
    if len(argv) not in (4, 5) or argv[0] not in ('verify', 'cand'):
        raise SystemExit(__doc__)
    mode, log, track = argv[:3]
    target = int(argv[3])
    rounds = int(argv[4]) if len(argv) == 5 else 3
    cars, mover, real = board_at(log, target)
    print('board before move %d (mover p%d):' % (target, mover + 1))
    for i, car in enumerate(cars):
        print('  p%d (%d,%d) v(%d,%d) fin=%d' % (i + 1, *car))

    oracle = Oracle(track)
    try:
        if mode == 'verify':
            verify(oracle, cars, mover, real, rounds)
        else:
            candidates(oracle, Reach(WORK / ('reach_%s.bin' % track)), cars, mover, rounds)
    finally:
        oracle.close()


if __name__ == '__main__':
    main(sys.argv[1:])
