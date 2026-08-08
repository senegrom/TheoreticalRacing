"""Perfect-fidelity joint rollout via the game's interactive move oracle.

One JVM (--query-moves - -) answers "what does THE REAL SCORER do from this
exact board" per query line; this driver reconstructs a board from a race
log, then rolls the joint game forward with the real scorer as EVERY car's
policy -- the fidelity ceiling that the in-game rollouts (smom /
scorer-rival) approximate. Campaign provenance: rounds 55-65, where it
located every doom-entry move and validated each rescue candidate before
any Java was written (see racing-memory.md).

Modes:
  verify: roll N rounds from just before a log move and diff against the
          real race (must match move-for-move -- validates the pipeline).
  cand:   DJS question at a log move: for each of the mover's 9 candidate
          landings, roll N rounds and report the mover's fate. Round-0
          starts with the players after the mover (simOutcome semantics).

Usage:
  oracle_roll.py verify <log> <track> <moveIdx> [rounds]
  oracle_roll.py cand   <log> <track> <moveIdx> [rounds]

Requires: theoreticRacing.jar in the repo root, reach_<track>.bin in
RACING_WORK_DIR (produce via --dump-reach), and an all-AI properties file
inert_AI1.properties in RACING_WORK_DIR (inert_probe.py writes one).
RACING_WORK_DIR defaults to this script's directory.
"""
import os
import re
import struct
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WORK = os.environ.get('RACING_WORK_DIR', HERE)
JAR = os.path.join(REPO, 'theoreticRacing.jar')
PROPS = os.path.join(WORK, 'inert_AI1.properties')
DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
DIRNAMES = ['NW', 'N', 'NE', 'W', 'NONE', 'E', 'SW', 'S', 'SE']

LINE = re.compile(
    r'^(\d+) p(\d+) \S+ (\S+) v\((-?\d+),(-?\d+)\)\S\((-?\d+),(-?\d+)\) '
    r'\((-?\d+),(-?\d+)\)\S\((-?\d+),(-?\d+)\) (ok|CRASH|FINISH)')
START = re.compile(r'^player(\d+) name=\S+ kind=\S+ start=(\d+),(\d+)')
ANSWER = re.compile(r'^(-?\d+),(-?\d+);([FXBDA]{9})$')
INF = 2147483647


class Reach:
    def __init__(self, path):
        d = open(path, 'rb').read()
        self.w, self.h, self.vmax = struct.unpack_from('<iii', d, 0)
        self.span = 2 * self.vmax + 1
        self.arr = memoryview(d)[12:].cast('i')

    def t(self, x, y, vx, vy):
        if not (0 <= x < self.w and 0 <= y < self.h) or abs(vx) > self.vmax or abs(vy) > self.vmax:
            return None
        v = self.arr[((x * self.h + y) * self.span + (vx + self.vmax)) * self.span + (vy + self.vmax)]
        return None if v == INF else v


class Oracle:
    def __init__(self, track):
        self.proc = subprocess.Popen(
            ['java', '-jar', JAR, '--auto', '--track', track, '--props', PROPS,
             '--seed', '1', '--query-moves', '-', '-'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding='utf-8', bufsize=1)

    def ask(self, mover, cars):
        """cars: list of 8 tuples (x, y, vx, vy, fin). Returns (dx, dy, mask)."""
        q = str(mover) + ';' + ';'.join('%d,%d,%d,%d,%d' % tuple(c) for c in cars)
        self.proc.stdin.write(q + '\n')
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError('oracle died')
            m = ANSWER.match(line.strip())
            if m:
                return int(m.group(1)), int(m.group(2)), m.group(3)

    def close(self):
        try:
            self.proc.stdin.write('quit\n')
            self.proc.stdin.flush()
        except OSError:
            pass
        self.proc.terminate()


def board_at(log, target):
    """Board state just BEFORE global move `target`. Returns (cars, mover_idx,
    real_moves) with real_moves = the log's moves from target onward."""
    cars = [None] * 8
    mover = None
    for line in open(log, encoding='utf-8', errors='replace'):
        sm = START.match(line)
        if sm:
            cars[int(sm.group(1)) - 1] = [int(sm.group(2)), int(sm.group(3)), 0, 0, 0]
            continue
        m = LINE.match(line)
        if not m:
            continue
        t, p = int(m.group(1)), int(m.group(2))
        i = p - 1
        if t >= target:
            if t == target:
                mover = i
            break
        st = m.group(12)
        if st == 'CRASH':
            cars[i][4] = 99
        elif st == 'FINISH':
            cars[i][4] = 90
        else:
            cars[i] = [int(m.group(10)), int(m.group(11)), int(m.group(6)), int(m.group(7)), 0]
    real = []
    for line in open(log, encoding='utf-8', errors='replace'):
        m = LINE.match(line)
        if m and int(m.group(1)) >= target:
            real.append((int(m.group(1)), int(m.group(2)), m.group(3),
                         int(m.group(10)), int(m.group(11)), m.group(12)))
    return [tuple(c) for c in cars], mover, real


def apply_move(cars, i, dx, dy, mask):
    """Returns (new_cars, fate) with fate in {'ok','FINISH','CRASH'}."""
    x, y, vx, vy, fin = cars[i]
    ci = DIRS.index((dx, dy))
    c = mask[ci]
    cars = list(cars)
    if c == 'F':
        cars[i] = (x, y, vx, vy, 90)
        return cars, 'FINISH'
    if c in 'XB':
        cars[i] = (x, y, vx, vy, 99)
        return cars, 'CRASH'
    nvx, nvy = vx + dx, vy + dy
    cars[i] = (x + nvx, y + nvy, nvx, nvy, 0)
    return cars, 'ok'


def roll(oracle, cars, first_mover, rounds, watch, echo=False):
    """Roll `rounds` full rounds starting at index first_mover. Returns
    (fate, round_no, cars): fate of `watch` = 'CRASH'/'FINISH'/'alive'."""
    cars = list(cars)
    order = list(range(8))
    i = first_mover
    r = 0
    while r < rounds:
        idx = order[i]
        if cars[idx][4] == 0:
            dx, dy, mask = oracle.ask(idx, cars)
            cars, fate = apply_move(cars, idx, dx, dy, mask)
            if echo:
                print('    r%d p%d %s -> (%d,%d) v(%d,%d) %s'
                      % (r, idx + 1, DIRNAMES[DIRS.index((dx, dy))],
                         cars[idx][0], cars[idx][1], cars[idx][2], cars[idx][3],
                         fate if fate != 'ok' else ''))
            if idx == watch and fate != 'ok':
                return fate, r, cars
        i += 1
        if i == 8:
            i = 0
            r += 1
        if all(c[4] != 0 for c in cars):
            break
    return 'alive', rounds, cars


def main():
    mode, log, track, target = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    rounds = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    reach = Reach(os.path.join(WORK, 'reach_%s.bin' % track))
    cars, mover, real = board_at(log, target)
    print('board before move %d (mover p%d):' % (target, mover + 1))
    for i, c in enumerate(cars):
        print('  p%d (%d,%d) v(%d,%d) fin=%d' % (i + 1, c[0], c[1], c[2], c[3], c[4]))
    oracle = Oracle(track)
    try:
        if mode == 'verify':
            n_check = rounds * 8
            sim = []
            cc = list(cars)
            i = mover
            while len(sim) < n_check:
                idx = i % 8
                if cc[idx][4] == 0:
                    dx, dy, mask = oracle.ask(idx, cc)
                    cc, fate = apply_move(cc, idx, dx, dy, mask)
                    sim.append((idx + 1, DIRNAMES[DIRS.index((dx, dy))],
                                cc[idx][0], cc[idx][1], fate))
                i += 1
                if all(c[4] != 0 for c in cc):
                    break
            ok = True
            for k, s in enumerate(sim):
                if k >= len(real):
                    break
                rt, rp, rd, rx, ry, rst = real[k]
                st = 'ok' if s[4] == 'ok' else s[4]
                match = s[0] == rp and s[1] == rd and (st != 'ok') == (rst != 'ok')
                if not match:
                    ok = False
                print('  %s sim p%d %-4s ->(%d,%d) %s | real t=%d p%d %-4s ->(%d,%d) %s'
                      % ('OK ' if match else 'DIFF', s[0], s[1], s[2], s[3], s[4],
                         rt, rp, rd, rx, ry, rst))
                if not match:
                    break
            print('VERIFY: %s' % ('EXACT MATCH (%d moves)' % len(sim) if ok else 'DIVERGED'))
        elif mode == 'cand':
            x, y, vx, vy, fin = cars[mover]
            _, _, mask0 = oracle.ask(mover, cars)
            print('mover p%d candidates (mask %s):' % (mover + 1, mask0))
            for ci, (dx, dy) in enumerate(DIRS):
                c = mask0[ci]
                if c == 'X' or c == 'B':
                    print('  %-4s %s -- fatal immediately' % (DIRNAMES[ci], c))
                    continue
                if c == 'F':
                    print('  %-4s F -- finishes' % DIRNAMES[ci])
                    continue
                nvx, nvy = vx + dx, vy + dy
                cc = list(cars)
                cc[mover] = (x + nvx, y + nvy, nvx, nvy, 0)
                fate, r, fc = roll(oracle, cc, mover + 1 if mover < 7 else 0, rounds, mover)
                fx, fy, fvx, fvy, ffin = fc[mover]
                doom = ''
                if fate == 'alive':
                    tt = reach.t(fx, fy, fvx, fvy)
                    doom = ' (final t=%s)' % ('DOOMED' if tt is None else tt)
                print('  %-4s %s land=(%d,%d) v(%d,%d): %s%s'
                      % (DIRNAMES[ci], c, x + nvx, y + nvy, nvx, nvy,
                         fate if fate == 'alive' else '%s @round %d' % (fate, r), doom))
    finally:
        oracle.close()


main()
