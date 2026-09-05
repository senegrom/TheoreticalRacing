"""Scan game move logs for crashed players.

Prefers the explicit CRASH outcome marker; additionally flags cars whose
moves stop well before the race's final move without a FINISH (a crashed
car is removed from the game). The boxed-out last survivor instead races
to within ~one round of the end. Note: a CRASH inside the final 8 moves is
caught only by the marker path (the heuristic has an end-of-race blind
window).

For each crash, print the last 3 moves with landing speed^2 -- the campaign
uses this to classify doom speed classes (wide trigger = spd^2 >= 49).

Usage: crash_scan.py <log-or-dir> [...]
"""
import os
import sys

if __package__:
    from .forensics_common import configure_console, parse_move
else:
    from forensics_common import configure_console, parse_move


def scan(path):
    moves = {}          # player -> list of (turn, dir, nvx, nvy, nx, ny, outcome)
    with open(path, encoding='utf-8', errors='replace') as f:
        for ln in f:
            mv = parse_move(ln)
            if mv is None:
                continue
            moves.setdefault(mv.player, []).append(
                (mv.index, mv.direction, mv.new_vx, mv.new_vy, mv.new_x, mv.new_y,
                 mv.status + mv.detail))
    if not moves:
        return None
    end = max(ms[-1][0] for ms in moves.values())
    crashed = []
    finished = 0
    for p, ms in sorted(moves.items()):
        last = ms[-1]
        if last[6].startswith('FINISH'):
            finished += 1
        elif last[6].startswith('CRASH') or last[0] < end - 8:
            crashed.append((p, ms))
    return finished, crashed, end


def main():
    configure_console()
    paths = []
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            paths += sorted(os.path.join(a, f) for f in os.listdir(a) if f.endswith('.log'))
        else:
            paths.append(a)
    total = 0
    for path in paths:
        r = scan(path)
        if r is None:
            continue
        finished, crashed, end = r
        name = os.path.basename(path)
        if not crashed:
            continue
        total += len(crashed)
        for p, ms in crashed:
            print('%-34s f=%d  p%d CRASHED at move %d/%d' % (name, finished, p, ms[-1][0], end))
            for t, d, nvx, nvy, nx, ny, out in ms[-3:]:
                print('    %4d %-4s v->(%d,%d) spd2=%-3d  ->(%d,%d) %s'
                      % (t, d, nvx, nvy, nvx * nvx + nvy * nvy, nx, ny, out))
    print('\n%d crashed player(s) across %d log(s)' % (total, len(paths)))


if __name__ == '__main__':
    main()
