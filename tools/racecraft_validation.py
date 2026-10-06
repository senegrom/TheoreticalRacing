"""Strict acceptance boundary for cf4 counterfactual evidence.

Checks protocol/state consistency independently of Java; geometry remains the
pinned Java referee's responsibility. No label is accepted without matching the
entire control suffix of the captured real race, including terminal places.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tracks'))
from forensics_common import parse_move

DIRECTIONS = dict(zip(('NW', 'N', 'NE', 'W', 'NONE', 'E', 'SW', 'S', 'SE'),
                      ((-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1))))
STATUSES = {'RUNNING', 'FINISHED', 'CLASSIFIED', 'CRASHED', 'TIMED_OUT', 'UNKNOWN'}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def integer(value, minimum=0, maximum=2_147_483_647):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('invalid integer in counterfactual result')
    return value


def snapshot(text: str):
    if not isinstance(text, str) or len(text) > 16384:
        raise ValueError('missing or oversized snapshot')
    try:
        groups = text.split(';')
        header = groups[0].split(',')
        if not ((len(header) == 7 and header[0] == 'rc3') or (len(header) == 8 and header[0] in ('rc4', 'rc5'))) or not re.fullmatch(r'[0-9a-f]{64}', header[6]):
            raise ValueError('invalid snapshot header')
        turn, laps, slot, first, last = map(int, header[1:6])
        rows = [list(map(int, group.split(','))) for group in groups[1:]]
    except (TypeError, ValueError) as error:
        raise ValueError('invalid snapshot encoding') from error
    n = len(rows)
    if len(header) == 8:
        plans = header[7].split('.')
        atom = r'(?:NW|N|NE|W|NONE|E|SW|S|SE)'
        pattern = rf'(?:{atom}|M_{atom}(?:\+{atom}){{0,2}})~[0-9a-f]{{64}}'
        if ('M_' in header[7]) != (header[0] == 'rc5'):
            raise ValueError('noncanonical plan version')
        if len(plans) != n or any(p != '-' and not re.fullmatch(pattern, p) for p in plans):
            raise ValueError('invalid follow-up policy memory')
    if not 1 <= n <= 9 or any(len(row) != 14 for row in rows):
        raise ValueError('invalid snapshot roster')
    integer(turn); integer(laps, 1); integer(slot, 0, n - 1)
    integer(first, 0, n); integer(last, 0, n)
    if first + last > n: raise ValueError('impossible classification counters')
    ranks = []
    occupied = set()
    for index, row in enumerate(rows):
        if row[0] != index + 1 or row[1] not in (1, 2):
            raise ValueError('unsupported snapshot player identity')
        integer(row[6], 0, n); integer(row[7], 0, laps); integer(row[8], 0, 2)
        for value in row[9:13]: integer(value)
        integer(row[13], 0, 1)
        if row[6]: ranks.append(row[6])
        else:
            if row[2] < 0 or row[3] < 0 or row[7] == laps or tuple(row[2:4]) in occupied:
                raise ValueError('invalid live snapshot player')
            occupied.add(tuple(row[2:4]))
    if len(set(ranks)) != len(ranks): raise ValueError('duplicate finishing places')
    return (turn, laps, slot, first, last, header[6]), rows


def query(case: dict, max_moves: int) -> str:
    integer(max_moves, 1, 100000)
    if case.get('actual') not in DIRECTIONS: raise ValueError('invalid observed action')
    snapshot(case['snapshot'])
    return f"cf4,{max_moves},{case['actual']}|{case['snapshot']}"


def action_list(value):
    if not isinstance(value, list) or any(type(a) is not str or a not in DIRECTIONS for a in value):
        raise ValueError('invalid legal-action set')
    if len(set(value)) != len(value): raise ValueError('duplicate legal actions')
    return value


def validate_trial(case: dict, trial: dict, max_moves: int):
    header, rows = snapshot(case['snapshot'])
    turn, laps, slot, first, last, identity = header
    n, self = len(rows), slot
    if n > 1 and sum(row[6] == 0 for row in rows) < 2:
        raise ValueError('captured decision is already classified')
    trace = trial.get('trace')
    if not isinstance(trace, list) or len(trace) > max_moves or not all(type(s) is str for s in trace):
        raise ValueError('invalid or oversized referee trace')
    if sha('\n'.join(trace)) != trial.get('traceSha256'): raise ValueError('trace checksum mismatch')
    if type(trial.get('complete')) is not bool or type(trial.get('legal')) is not bool:
        raise ValueError('missing boolean result fields')
    integer(trial.get('place'), 0, n); integer(trial.get('ownMoves'), 0, max_moves)
    if trial.get('status') not in STATUSES: raise ValueError('invalid terminal status')
    own, status, timeout_origin = 0, 'RUNNING', None
    done = False
    for index, line in enumerate(trace):
        f = line.split(':')
        if len(f) != 12 or f[1] not in DIRECTIONS or f[6] not in ('OK', 'LAP', 'FINISH', 'CRASH', 'TIMEOUT'):
            raise ValueError('malformed referee transition')
        try:
            actor = int(f[0]); x, y, vx, vy = map(int, f[2:6])
            place, lap, gate, left, clock = map(int, f[7:12])
        except ValueError as error: raise ValueError('malformed transition integer') from error
        integer(actor, 0, n - 1); integer(place, 0, n); integer(lap, 0, laps)
        integer(gate, 0, 2); integer(left, 0, 1)
        row = rows[actor]
        if done or row[6] or clock != turn + 1: raise ValueError('trace continues a retired state or has wrong clock')
        if index == 0 and f[6] != 'TIMEOUT' and f[1] != trial['action']:
            raise ValueError('trial did not execute its declared first action')
        if f[6] == 'TIMEOUT':
            if turn <= 750 * laps * n or f[1] != 'NONE' or [x, y, vx, vy] != row[2:6]:
                raise ValueError('timeout moved a car or preceded the limit')
            if timeout_origin is None: timeout_origin = slot
        else:
            if timeout_origin is not None or actor != slot: raise ValueError('wrong cyclic turn order')
            dx, dy = DIRECTIONS[f[1]]
            if (vx, vy, x, y) != (row[4] + dx, row[5] + dy, row[2] + row[4] + dx, row[3] + row[5] + dy):
                raise ValueError('invalid acceleration or destination')
        if left < row[13]: raise ValueError('leftGrid was reset')
        if f[6] == 'LAP':
            if lap != row[7] + 1 or gate != 1: raise ValueError('invalid lap transition')
        elif lap != row[7]: raise ValueError('unexpected lap credit')
        if actor == self: own += 1
        if f[6] == 'FINISH':
            first += 1
            if place != first: raise ValueError('finish rank out of order')
            row[2:7] = [-100000, -100000, 0, 0, place]
            if actor == self: status = 'FINISHED'
        elif f[6] in ('CRASH', 'TIMEOUT'):
            if place != n - last: raise ValueError('retirement rank out of order')
            last += 1
            row[2:7] = [-100000, -100000, 0, 0, place]
            if actor == self: status = 'TIMED_OUT' if f[6] == 'TIMEOUT' else 'CRASHED'
        else:
            if place != 0: raise ValueError('live car has a finishing place')
            row[2:6] = [x, y, vx, vy]
        row[7], row[8], row[13] = lap, gate, left
        turn = clock
        live = [i for i, r in enumerate(rows) if r[6] == 0]
        if len(live) == 1 and n > 1:
            survivor = live[0]; rows[survivor][6] = first + 1
            if survivor == self: status = 'CLASSIFIED'
            done = True
        elif not live: done = True
        if done:
            slot = timeout_origin if timeout_origin is not None else actor
        elif timeout_origin is None:
            slot = next((actor + k) % n for k in range(1, n + 1) if rows[(actor + k) % n][6] == 0)
    if timeout_origin is not None and not done: raise ValueError('partial atomic timeout classification')
    if trial['complete'] != done: raise ValueError('completion flag disagrees with classification')
    if trial['ownMoves'] != own or trial['place'] != rows[self][6]: raise ValueError('own result disagrees with trace')
    if trial['status'] != status and not (not done and trial['status'] == 'UNKNOWN'):
        raise ValueError('outcome status disagrees with referee transitions')
    final_h, final_rows = snapshot(trial.get('finalState'))
    if final_h != (turn, laps, slot, first, last, identity): raise ValueError('final header disagrees with trace')
    if len(final_rows) != n: raise ValueError('final roster changed')
    # UI pruning/history marks are not decision inputs and detached replay omits old histories.
    for expected, actual in zip(rows, final_rows):
        if expected[:9] != actual[:9] or expected[13] != actual[13]:
            raise ValueError('final player state disagrees with trace')
    if done and sorted(row[6] for row in final_rows) != list(range(1, n + 1)):
        raise ValueError('final classifications are not a permutation')
    return done


def validate_response(case: dict, answer: dict, max_moves: int):
    if answer.get('schema') != 4 or answer.get('baseline') != case['actual']:
        raise ValueError('wrong response version or observed action')
    if answer.get('requestSha256') != sha(query(case, max_moves)) or answer.get('maxMoves') != max_moves:
        raise ValueError('response is not bound to this complete request')
    if answer.get('rootIdentity') != snapshot(case['snapshot'])[0][5]: raise ValueError('wrong geometry/policy identity')
    legal = action_list(case.get('legalActions'))
    if action_list(answer.get('legalActions')) != legal: raise ValueError('capture/replay legality differs')
    trials = answer.get('trials')
    if not isinstance(trials, list) or any(not isinstance(t, dict) for t in trials):
        raise ValueError('missing action trials')
    actions = [t.get('action') for t in trials]
    if len(set(actions)) != len(actions) or set(actions) != set(legal) | {case['actual']}:
        raise ValueError('missing, duplicate or extraneous action trials')
    complete = True
    for trial in trials:
        if trial.get('legal') is not (trial['action'] in legal): raise ValueError('inconsistent legality flag')
        complete = validate_trial(case, trial, max_moves) and complete
    return next(t for t in trials if t['action'] == case['actual']), complete


def validate_control(case: dict, control: dict, race_text: str, roster: dict):
    """Every case, including mid-race captures, must reproduce the original suffix."""
    header, rows = snapshot(case['snapshot'])
    turn = header[0]
    if '# results\n' not in race_text: raise ValueError('original race has no final classification')
    actual = []
    for line in race_text.splitlines():
        move = parse_move(line)
        if move is not None and move.index > turn:
            status = 'OK' if move.status == 'ok' else 'LAP' if move.status.startswith('LAP') else move.status
            actual.append((move.player - 1, move.direction, move.new_x, move.new_y,
                           move.new_vx, move.new_vy, status, move.index))
    predicted = []
    for line in control['trace']:
        f = line.split(':')
        predicted.append((int(f[0]), f[1], *map(int, f[2:6]), f[6], int(f[11])))
    if not control['complete'] or actual != predicted:
        raise ValueError('control continuation does not reproduce the full captured race suffix')
    by_name = {name: number for number, (name, _) in roster.items()}
    if len(by_name) != len(rows): raise ValueError('ambiguous captured player names')
    places = {}
    for line in race_text.split('# results\n', 1)[1].splitlines():
        m = re.fullmatch(r'(\d+)\. (.*)', line)
        if m:
            if m[2] not in by_name or by_name[m[2]] in places: raise ValueError('unknown or duplicate result player')
            places[by_name[m[2]]] = int(m[1])
    _, final = snapshot(control['finalState'])
    if sorted(places.values()) != list(range(1, len(rows) + 1)) or any(places.get(r[0]) != r[6] for r in final):
        raise ValueError('control final places disagree with captured race')
