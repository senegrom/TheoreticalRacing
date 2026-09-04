#!/usr/bin/env python3
"""Needle audit: walk a crashed car back to the move that actually killed it.

Most crashes in traffic are decided several moves before the wall: the car
enters a landing with a single alive continuation and a rival then occupies
that one cell. board_at.py classifies landings against an offline finish map
that is blind to lap gates, so in a lap race it calls live states dead. This
asks the game itself through the --query-moves oracle, which reports every
candidate as F (finish), X (illegal), B (body), D (dead in the coherent alive
set) or A (alive), and answers two questions per step of the car's last moves:

  open    how many of its nine landings were A -- its real choice set
  thread  how many continuations the landing it CHOSE had, with the rivals
          where they actually stood -- the width of the lane it entered

plus the nearest live rival to that landing and its speed, which is the radius
any contestability guard would have needed to see it. Round 219 was aimed with
exactly this: across five audited deaths the closing rival stood one to three
cells from the landing at the decisive move.

Usage: needle_audit.py <log> <track> <player> [steps]
Requires theoreticRacing.jar in the repo root and tracks/lap_bench.properties
(override with RACING_PROPS).
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

if __package__:
    from .forensics_common import DIRNAMES, DIRS, Oracle, log_player_count, reconstruct_board
else:
    from forensics_common import DIRNAMES, DIRS, Oracle, log_player_count, reconstruct_board

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
JAR = ROOT / 'theoreticRacing.jar'
PROPS = pathlib.Path(os.environ.get('RACING_PROPS', HERE / 'lap_bench.properties'))

MOVE = re.compile(r'^(\d+) p(\d+) \S+ (\S+) v\((-?\d+),(-?\d+)\)\D+\((-?\d+),(-?\d+)\) '
                  r'\((\d+),(\d+)\)\D+\((\d+),(\d+)\) (\S+)')


def car_moves(log, player):
    out = []
    for line in pathlib.Path(log).read_text(encoding='utf-8', errors='replace').splitlines():
        m = MOVE.match(line)
        if m and int(m.group(2)) == player:
            out.append((int(m.group(1)), m.group(3), int(m.group(4)), int(m.group(5)),
                        int(m.group(6)), int(m.group(7)), int(m.group(8)), int(m.group(9)),
                        int(m.group(10)), int(m.group(11)), m.group(12)))
    return out


def configure_console():
    reconfigure = getattr(sys.stdout, 'reconfigure', None)
    if reconfigure is not None:
        reconfigure(encoding='utf-8', errors='replace')


def main(argv=None) -> int:
    configure_console()
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 3:
        print(__doc__)
        return 2
    log, track, player = argv[0], argv[1], int(argv[2])
    steps = int(argv[3]) if len(argv) > 3 else 8
    if not JAR.is_file():
        raise SystemExit('theoreticRacing.jar not found; run build_main.sh first')
    n = log_player_count(log)
    moves = car_moves(log, player)
    crash = next((i for i, mv in enumerate(moves) if 'CRASH' in mv[10]), None)
    if crash is None:
        print(f'p{player} never crashed in {log}')
        return 1
    window = moves[max(0, crash - steps + 1):crash + 1]
    oracle = Oracle(track, JAR, PROPS)
    try:
        print(f'{pathlib.Path(log).name}: p{player} crashed at move {moves[crash][0]}; '
              f'walking back {len(window)} of its moves\n')
        print(f"{'move':>5s} {'state':22s} {'chose':6s} {'open':>4s} {'thread':>6s}  "
              f"mask       nearest rival      note")
        first_narrow = None
        for gm, _, ovx, ovy, nvx, nvy, x, y, nx, ny, status in window:
            cars, mover, _ = reconstruct_board(log, gm, n)
            _, _, mask = oracle.ask(mover, cars)
            open_ = mask.count('A')
            chosen_i = DIRS.index((nvx - ovx, nvy - ovy))
            chosen_cls = mask[chosen_i]
            thread = '-'
            if chosen_cls in 'AD':
                hyp = list(cars)
                hyp[mover] = (nx, ny, nvx, nvy, 0)
                _, _, mask2 = oracle.ask(mover, hyp)
                thread = str(mask2.count('A'))
                if first_narrow is None and mask2.count('A') <= 1:
                    first_narrow = gm
            near = None
            for j, c in enumerate(cars):
                if j == mover or c[4] != 0:
                    continue
                dcheb = max(abs(c[0] - nx), abs(c[1] - ny))
                if near is None or dcheb < near[0]:
                    near = (dcheb, max(abs(c[2]), abs(c[3])), j + 1)
            rival = f'p{near[2]} at {near[0]:2d} |v|={near[1]}' if near else 'no rival'
            note = {'D': 'entered a DEAD state', 'B': 'drove into a body',
                    'X': 'illegal move'}.get(chosen_cls, '')
            if not note and thread == '1':
                note = 'single-lane landing'
            elif not note and thread == '0':
                note = 'landing has NO continuation'
            if 'CRASH' in status:
                note = (note + '  <- CRASH').strip()
            print(f'{gm:5d} ({x:3d},{y:3d}) v({ovx:2d},{ovy:2d})  {DIRNAMES[chosen_i]:6s} '
                  f'{open_:4d} {thread:>6s}  {mask}  {rival:18s} {note}')
        if first_narrow is not None:
            print(f'\nthread first narrowed to <=1 at move {first_narrow}')
    finally:
        oracle.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
