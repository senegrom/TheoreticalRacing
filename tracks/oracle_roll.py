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
import sys

if __package__:
    from .forensics_common import DIRNAMES, DIRS, Oracle, Reach, reconstruct_board
else:
    from forensics_common import DIRNAMES, DIRS, Oracle, Reach, reconstruct_board


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORK = Path(os.environ.get('RACING_WORK_DIR', HERE))
JAR = ROOT / 'theoreticRacing.jar'
PROPS = HERE / 'bench.properties'


def apply_move(cars, index, dx, dy, mask):
    x, y, vx, vy, _ = cars[index]
    outcome = mask[DIRS.index((dx, dy))]
    cars = list(cars)
    if outcome == 'F':
        cars[index] = (x, y, vx, vy, 90)
        return cars, 'FINISH'
    if outcome in 'XB':
        cars[index] = (x, y, vx, vy, 99)
        return cars, 'CRASH'
    nvx, nvy = vx + dx, vy + dy
    cars[index] = (x + nvx, y + nvy, nvx, nvy, 0)
    return cars, 'ok'


def roll(oracle, cars, first_mover, rounds, watch):
    cars = list(cars)
    index = first_mover % 8
    completed = 0
    while completed < rounds:
        if cars[index][4] == 0:
            dx, dy, mask = oracle.ask(index, cars)
            cars, fate = apply_move(cars, index, dx, dy, mask)
            if index == watch and fate != 'ok':
                return fate, completed, cars
        index = (index + 1) % 8
        if index == 0:
            completed += 1
        if all(car[4] != 0 for car in cars):
            break
    return 'alive', rounds, cars


def verify(oracle, cars, mover, real, rounds):
    simulated = []
    current = list(cars)
    index = mover
    while len(simulated) < rounds * 8 and not all(car[4] != 0 for car in current):
        if current[index][4] == 0:
            dx, dy, mask = oracle.ask(index, current)
            current, fate = apply_move(current, index, dx, dy, mask)
            simulated.append((
                index + 1,
                DIRNAMES[DIRS.index((dx, dy))],
                current[index][0],
                current[index][1],
                fate,
            ))
        index = (index + 1) % 8

    ok = len(real) >= len(simulated)
    for sim, observed in zip(simulated, real):
        sim_status = 'ok' if sim[4] == 'ok' else sim[4]
        match = (
            sim[0] == observed.player
            and sim[1] == observed.direction
            and (sim_status != 'ok') == (observed.status != 'ok')
        )
        ok &= match
        print(
            '  %s sim p%d %-4s ->(%d,%d) %s | real t=%d p%d %-4s '
            '->(%d,%d) %s'
            % (
                'OK ' if match else 'DIFF',
                sim[0], sim[1], sim[2], sim[3], sim[4],
                observed.index, observed.player, observed.direction,
                observed.new_x, observed.new_y, observed.status,
            )
        )
        if not match:
            break
    print('VERIFY: %s' % ('EXACT MATCH (%d moves)' % len(simulated) if ok else 'DIVERGED'))
    return ok


def candidates(oracle, reach, cars, mover, rounds):
    x, y, vx, vy, _ = cars[mover]
    _, _, mask = oracle.ask(mover, cars)
    print('mover p%d candidates (mask %s):' % (mover + 1, mask))
    for direction_index, (dx, dy) in enumerate(DIRS):
        outcome = mask[direction_index]
        if outcome in 'XB':
            print('  %-4s %s -- fatal immediately' % (DIRNAMES[direction_index], outcome))
            continue
        if outcome == 'F':
            print('  %-4s F -- finishes' % DIRNAMES[direction_index])
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
        print(
            '  %-4s %s land=(%d,%d) v(%d,%d): %s%s'
            % (
                DIRNAMES[direction_index], outcome,
                x + nvx, y + nvy, nvx, nvy, fate, suffix,
            )
        )


def configure_console():
    reconfigure = getattr(sys.stdout, 'reconfigure', None)
    if reconfigure is not None:
        reconfigure(encoding='utf-8', errors='replace')


def main(argv):
    configure_console()
    if len(argv) not in (4, 5) or argv[0] not in ('verify', 'cand'):
        raise SystemExit(__doc__)
    mode, log, track = argv[:3]
    target = int(argv[3])
    rounds = int(argv[4]) if len(argv) == 5 else 3
    cars, mover, real = reconstruct_board(log, target)
    print('board before move %d (mover p%d):' % (target, mover + 1))
    for index, car in enumerate(cars):
        print('  p%d (%d,%d) v(%d,%d) fin=%d' % (index + 1, *car))

    with Oracle(track, JAR, PROPS) as oracle:
        if mode == 'verify':
            return 0 if verify(oracle, cars, mover, real, rounds) else 1
        reach = Reach(WORK / ('reach_%s.bin' % track))
        candidates(oracle, reach, cars, mover, rounds)
        return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
