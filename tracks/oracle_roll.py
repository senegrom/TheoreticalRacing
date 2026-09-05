#!/usr/bin/env python3
"""Referee-backed replay and counterfactuals, including multi-lap progress.

Usage:
  oracle_roll.py verify <log> <track> <moveIdx> [rounds]
  oracle_roll.py cand   <log> <track> <moveIdx> [rounds]

RACING_PROPS must match the recorded roster, kinds and lap count. V2 checks
lap-count mismatches. A round is one cycle of player slots, starting at the
specified mover; already-retired slots are skipped and the live referee's
last-survivor rule ends the race. RACING_WORK_DIR locates reach_<track>.bin
for candidate diagnostics (default: tracks/).
"""
from pathlib import Path
import os
import sys

if __package__:
    from .forensics_common import (
        CandidateMask, DIRNAMES, DIRS, Oracle, Reach, ReplayBoard, configure_console,
        log_player_count, reconstruct_board,
    )
else:
    from forensics_common import (
        CandidateMask, DIRNAMES, DIRS, Oracle, Reach, ReplayBoard, configure_console,
        log_player_count, reconstruct_board,
    )

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORK = Path(os.environ.get('RACING_WORK_DIR', HERE))
JAR = ROOT / 'theoreticRacing.jar'
PROPS = Path(os.environ.get('RACING_PROPS', HERE / 'bench.properties'))
TERMINAL = ('FINISH', 'CRASH', 'TIMEOUT')


def copy_board(cars):
    return cars.copy() if isinstance(cars, ReplayBoard) else list(cars)


def race_finished(cars):
    live = sum(car[4] == 0 for car in cars)
    return live == 0 if len(cars) == 1 else live <= 1


def apply_move(cars, index, dx, dy, mask):
    x, y, vx, vy, _ = cars[index][:5]
    direction = DIRS.index((dx, dy))
    symbol = mask[direction]
    cars = copy_board(cars)
    nvx, nvy = vx + dx, vy + dy
    progress = []
    if isinstance(mask, CandidateMask):
        transition = mask.transitions[direction]
        status = transition.status
        fate = ('LAP %d/%d' % (transition.lap, mask.laps) if status == 'LAP'
                else 'ok' if status == 'OK' else status)
        progress = [transition.lap, transition.gate]
    else:
        if isinstance(cars, ReplayBoard) and cars.complete:
            raise ValueError('complete replay requires V2 transitions, not a legacy mask')
        fate = 'FINISH' if symbol == 'F' else 'CRASH' if symbol in 'XB' else 'ok'
    if fate in TERMINAL:
        marker = 99 if fate == 'CRASH' else 90
        # Match the live engine's retired position/velocity, not an active
        # body at the old or attempted destination. Verification below uses
        # the attempted move's coordinates, as the race log does.
        cars[index] = tuple([-100000, -100000, 0, 0, marker] + progress)
    else:
        cars[index] = tuple([x + nvx, y + nvy, nvx, nvy, 0] + progress)
    if isinstance(cars, ReplayBoard):
        cars.turns += 1
    return cars, fate


def roll(oracle, cars, first_mover, rounds, watch):
    if rounds < 1:
        raise ValueError('rounds must be positive')
    cars = copy_board(cars)
    count = len(cars)
    for slot in range(rounds * count):
        if race_finished(cars):
            return 'RACE_END', slot // count, cars
        index = (first_mover + slot) % count
        if cars[index][4] == 0:
            dx, dy, mask = oracle.ask(index, cars)
            cars, fate = apply_move(cars, index, dx, dy, mask)
            if index == watch and fate in TERMINAL:
                return fate, slot // count, cars
    return 'alive', rounds, cars


def verify(oracle, cars, mover, real, rounds):
    if rounds < 1:
        raise ValueError('rounds must be positive')
    current = copy_board(cars)
    count = len(current)
    checked = 0
    first_turn = current.turns + 1 if isinstance(current, ReplayBoard) else real[0].index if real else 1
    ok = True
    for slot in range(rounds * count):
        if race_finished(current):
            break
        index = (mover + slot) % count
        if current[index][4] != 0:
            continue
        if checked >= len(real):
            ok = False  # the observed window is incomplete, not a shorter match
            break
        x, y, vx, vy, _ = current[index][:5]
        dx, dy, mask = oracle.ask(index, current)
        nvx, nvy = vx + dx, vy + dy
        nx, ny = x + nvx, y + nvy
        current, fate = apply_move(current, index, dx, dy, mask)
        observed = real[checked]
        direction = DIRNAMES[DIRS.index((dx, dy))]
        match = (
            observed.index == first_turn + checked
            and index + 1 == observed.player
            and direction == observed.direction
            and fate == observed.status
            and (x, y, vx, vy, nx, ny, nvx, nvy) == (
                observed.x, observed.y, observed.old_vx, observed.old_vy,
                observed.new_x, observed.new_y, observed.new_vx, observed.new_vy,
            )
        )
        if isinstance(mask, CandidateMask) and fate == 'ok':
            expected_cp = mask.transitions[DIRS.index((dx, dy))].checkpoints
            observed_cp = (1 if 'cp1' in observed.detail.split() else 0) | (
                2 if 'cp2' in observed.detail.split() else 0)
            match &= expected_cp == observed_cp
        print('  %s sim p%d %-4s ->(%d,%d) %s | real t=%d p%d %-4s ->(%d,%d) %s' % (
            'OK ' if match else 'DIFF', index + 1, direction, nx, ny, fate,
            observed.index, observed.player, observed.direction,
            observed.new_x, observed.new_y, observed.status,
        ))
        checked += 1
        ok &= match
        if not match:
            break
    # A simulated early ending is not an exact match to a continuing race.
    if race_finished(current) and checked < len(real):
        ok = False
    ok = bool(ok and checked > 0)
    print('VERIFY: %s' % ('EXACT MATCH (%d moves)' % checked if ok else 'DIVERGED'))
    return ok


def candidates(oracle, reach, cars, mover, rounds):
    x, y, vx, vy, _ = cars[mover][:5]
    _, _, mask = oracle.ask(mover, cars)
    print('mover p%d candidates (mask %s):' % (mover + 1, mask))
    for i, (dx, dy) in enumerate(DIRS):
        next_cars, immediate = apply_move(cars, mover, dx, dy, mask)
        if immediate in TERMINAL:
            print('  %-4s %s' % (DIRNAMES[i], immediate))
            continue
        nvx, nvy = vx + dx, vy + dy
        fate, round_no, final = roll(oracle, next_cars, mover + 1, rounds, mover)
        fx, fy, fvx, fvy, _ = final[mover][:5]
        suffix = ''
        if fate == 'alive':
            turns = reach.turns(fx, fy, fvx, fvy)
            suffix = ' (final t=%s)' % ('DOOMED' if turns is None else turns)
        else:
            fate = '%s @round %d' % (fate, round_no)
        print('  %-4s %s land=(%d,%d) v(%d,%d): %s%s' % (
            DIRNAMES[i], immediate, x + nvx, y + nvy, nvx, nvy, fate, suffix))


def main(argv):
    configure_console()
    if len(argv) not in (4, 5) or argv[0] not in ('verify', 'cand'):
        raise SystemExit(__doc__)
    mode, log, track = argv[:3]
    target = int(argv[3])
    rounds = int(argv[4]) if len(argv) == 5 else 3
    cars, mover, real = reconstruct_board(log, target, log_player_count(log), complete=True)
    print('board before move %d (mover p%d):' % (target, mover + 1))
    for index, car in enumerate(cars):
        print('  p%d (%d,%d) v(%d,%d) fin=%d lap=%d gate=%d' % (index + 1, *car))
    with Oracle(track, JAR, PROPS) as oracle:
        if mode == 'verify':
            return 0 if verify(oracle, cars, mover, real, rounds) else 1
        candidates(oracle, Reach(WORK / ('reach_%s.bin' % track)), cars, mover, rounds)
        return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
