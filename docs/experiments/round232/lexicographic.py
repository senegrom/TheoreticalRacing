#!/usr/bin/env python3
"""Audit paired fleet grids and compare times in finishing order.

Usage: lexicographic.py OUTPUT.json BASE_GRID CANDIDATE_GRID [...]
Each later grid is compared with BASE_GRID on exactly the same track/seeds.
Use own moves, not global move indices (retirements change the latter).
The game stops with one car still active: that unobserved finish, crashes,
and timeouts are all missing finishes, never artificially quick results.
"""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
import statistics
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'tracks'))
import fleet_grid as fleet
from forensics_common import parse_move, normalized_sha256


def vector(row):
    times = [row['moves'][n - 1] for n in row['finish_order']]
    return tuple(times + [float('inf')] * (len(row['moves']) - len(times)))


def compare(candidate, baseline):
    """Return (sign, decisive place); negative means the candidate improves."""
    if len(candidate) != len(baseline):
        raise ValueError('different field sizes')
    for place, (c, b) in enumerate(zip(candidate, baseline), 1):
        if c != b:
            return (-1 if c < b else 1), place
    return 0, None


def read_grid(grid):
    grid = Path(grid)
    manifest = json.loads((grid / 'manifest.json').read_text())
    assert manifest['runner'] == fleet.digest(REPO / 'tracks/fleet_grid.py')
    assert manifest['log_parser'] == fleet.digest(REPO / 'tracks/forensics_common.py')
    for track, digest in manifest['tracks'].items():
        assert digest == fleet.digest(REPO / 'tracks' / (track + '.track'))
    run_id = hashlib.sha256(fleet.json_text(manifest).encode()).hexdigest()
    lo, hi = manifest['seeds']
    rows = {}
    assert len(list(grid.glob('*_s*.log'))) == len(manifest['tracks']) * (hi - lo + 1)
    for track in sorted(manifest['tracks']):
        completed = fleet.completed(grid, track, run_id, range(lo, hi + 1))
        assert completed is not None, (grid, track)
        for seed, saved in zip(range(lo, hi + 1), completed['logs']):
            log = grid / f'{track}_s{seed}.log'
            text = log.read_text()
            players = [line for line in text.splitlines() if line.startswith('player')]
            moves = [0] * len(players)
            status = ['unfinished'] * len(players)
            finish_order = []
            for line in text.splitlines():
                move = parse_move(line)
                if move:
                    moves[move.player - 1] += 1
                    if move.status in ('FINISH', 'CRASH', 'TIMEOUT'):
                        status[move.player - 1] = move.status
                    if move.status == 'FINISH':
                        finish_order.append(move.player)
            assert sum(moves) == saved['counts']['moves']
            rows[track, seed] = dict(track=track, seed=seed, laps=not completed['no_loop'],
                moves=moves, statuses=status, finish_order=finish_order,
                starts=players, counts=saved['counts'], sha256=saved['sha256'],
                normalized_sha256=normalized_sha256(text))
    return rows, dict(grid=str(grid), run_id=run_id, manifest=manifest)


def score(candidate, baseline):
    assert candidate.keys() == baseline.keys(), 'unpaired corpus'
    by_place = collections.defaultdict(lambda: dict(better=0, worse=0))
    decisive = []
    winner_delta = []
    prefix = [dict(pairs=0, better=0, worse=0, tied=0) for _ in range(8)]
    for key in sorted(baseline):
        c, b = candidate[key], baseline[key]
        assert c['starts'] == b['starts'], ('different starts', key)
        cv, bv = vector(c), vector(b)
        sign, place = compare(cv, bv)
        if sign:
            by_place[place]['better' if sign < 0 else 'worse'] += 1
        decisive.append(dict(track=key[0], seed=key[1], sign=sign, place=place,
                             candidate=[None if x == float('inf') else x for x in cv],
                             baseline=[None if x == float('inf') else x for x in bv]))
        if cv[0] != float('inf') and bv[0] != float('inf'):
            winner_delta.append(cv[0] - bv[0])
        for i, (ct, bt) in enumerate(zip(cv, bv)):
            p = prefix[i]
            p['pairs'] += 1
            p['better' if ct < bt else 'worse' if ct > bt else 'tied'] += 1
            if ct != bt:
                break
    return dict(pairs=len(baseline), better=sum(r['sign'] < 0 for r in decisive),
        worse=sum(r['sign'] > 0 for r in decisive), tied=sum(r['sign'] == 0 for r in decisive),
        first_difference=dict(sorted(by_place.items())), equal_prefix=prefix,
        winner_mean_delta=statistics.mean(winner_delta), winner_move_delta=sum(winner_delta),
        winner_finite_pairs=len(winner_delta),
        candidate_counts={k: sum(r['counts'][k] for r in candidate.values()) for k in ('fin','crash','timeout','moves')},
        baseline_counts={k: sum(r['counts'][k] for r in baseline.values()) for k in ('fin','crash','timeout','moves')},
        comparisons=decisive)


def main():
    output, *grids = sys.argv[1:]
    assert len(grids) >= 2
    baseline, base_source = read_grid(grids[0])
    result = dict(baseline_source=base_source, baseline=list(baseline.values()), candidates=[])
    for path in grids[1:]:
        candidate, source = read_grid(path)
        metrics = score(candidate, baseline)
        result['candidates'].append(dict(source=source, rows=list(candidate.values()), metrics=metrics))
        print(json.dumps(dict(grid=path, **{k:v for k,v in metrics.items() if k not in ('comparisons','equal_prefix')})), flush=True)
    Path(output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
