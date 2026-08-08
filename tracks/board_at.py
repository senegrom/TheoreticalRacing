"""Reconstruct the board at one global move index of a game log.

Prints the mover's state, every live car, and the mover's 9 candidate
landings classified: BODY (live rival on the cell), DEAD-STATE (reach
says the landing state cannot finish / off-board), or OPEN. Segment-level
wall legality is NOT checkable offline -- an OPEN cell may still be an
illegal cut (use oracle_roll.py's mask for exact classification); a
DEAD-STATE/BODY verdict is definitive.

Usage: board_at.py <log> <reach.bin> <moveIndex>
"""
import re
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
INF = 2147483647
LINE = re.compile(
    r'^(\d+) p(\d+) \S+ (\S+) v\((-?\d+),(-?\d+)\)\S\((-?\d+),(-?\d+)\) '
    r'\((-?\d+),(-?\d+)\)\S\((-?\d+),(-?\d+)\) (ok|CRASH|FINISH)')
START = re.compile(r'^player(\d+) name=\S+ kind=\S+ start=(\d+),(\d+)')


class Reach:
    def __init__(self, path):
        d = open(path, 'rb').read()
        self.w, self.h, self.vmax = struct.unpack_from('<iii', d, 0)
        self.span = 2 * self.vmax + 1
        self.arr = memoryview(d)[12:].cast('i')

    def t(self, x, y, vx, vy):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return None
        if abs(vx) > self.vmax or abs(vy) > self.vmax:
            return None
        i = ((x * self.h + y) * self.span + (vx + self.vmax)) * self.span + (vy + self.vmax)
        v = self.arr[i]
        return None if v == INF else v


log, reachbin, target = sys.argv[1], sys.argv[2], int(sys.argv[3])
reach = Reach(reachbin)

pos = {}
vel = {}
dead = set()
fin = set()
for line in open(log, encoding='utf-8', errors='replace'):
    sm = START.match(line)
    if sm:
        pos[int(sm.group(1))] = (int(sm.group(2)), int(sm.group(3)))
        vel[int(sm.group(1))] = (0, 0)
        continue
    m = LINE.match(line)
    if not m:
        continue
    t, p = int(m.group(1)), int(m.group(2))
    nvx, nvy = int(m.group(6)), int(m.group(7))
    x, y = int(m.group(8)), int(m.group(9))
    nx, ny = int(m.group(10)), int(m.group(11))
    st = m.group(12)
    if t == target:
        print('move %d: p%d at (%d,%d) v(%d,%d) -> chose %s land (%d,%d) v(%d,%d) [%s]'
              % (t, p, x, y, int(m.group(4)), int(m.group(5)), m.group(3), nx, ny, nvx, nvy, st))
        cvx, cvy = int(m.group(4)), int(m.group(5))
        print('\nlive cars (post their last move):')
        for q in sorted(pos):
            if q == p or q in dead or q in fin:
                continue
            qx, qy = pos[q]
            print('  p%d (%d,%d) v(%d,%d)  dist=%d'
                  % (q, qx, qy, vel[q][0], vel[q][1], max(abs(qx - x), abs(qy - y))))
        bodies = {pos[q] for q in pos if q != p and q not in dead and q not in fin}
        print('\ncandidates from (%d,%d) v(%d,%d):' % (x, y, cvx, cvy))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                wvx, wvy = cvx + dx, cvy + dy
                wx, wy = x + wvx, y + wvy
                tt = reach.t(wx, wy, wvx, wvy) if abs(wvx) <= 12 and abs(wvy) <= 12 else None
                cls = ('BODY' if (wx, wy) in bodies else
                       'DEAD-STATE' if tt is None else 'open t=%d' % tt)
                mark = ' <== chosen' if (wx, wy) == (nx, ny) else ''
                print('  d(%+d,%+d) land (%d,%d) v(%d,%d): %s%s'
                      % (dx, dy, wx, wy, wvx, wvy, cls, mark))
        break
    if st == 'CRASH':
        dead.add(p)
    elif st == 'FINISH':
        fin.add(p)
    else:
        pos[p] = (nx, ny)
        vel[p] = (nvx, nvy)
