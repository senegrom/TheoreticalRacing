#!/usr/bin/env python3
"""One candidate car against a field of champions: the invasion check.

The mirrored screen (run_screen.py) races half a field of candidates against
half a field of champions. A promotion must also survive the opposite regime,
ONE candidate car entering a field of n-1 champions -- a policy can win the
mixed field and still lose places as a lone entrant, or the reverse. The
candidate is rotated through every seat (candidateSlots=k, k = 1..n). The
reading is the candidate's mean place over the seats of one track and seed
minus (n+1)/2, the mean place of any car in an n-car race -- negative means
the lone candidate gains places on the champions. Each race used to be paired
with the all-champion race of the same track, seed and seat; with every seat
raced that race's places are a permutation of 1..n, so it contributed exactly
(n+1)/2 per track and seed, and the owner dropped it (2026-09-29).

    run_1vfield.py --jar ARM.jar --out DIR [--seeds 1-5] [--jobs 3]
                   [--heap=-Xmx8g] [--players 8] [--mode legacy] [--tracks ALL]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tracks'))
from benchmark_io import read_race  # noqa: E402
from fleet_grid import completed, json_text, run_grid_process, seed_range  # noqa: E402


def write_once(path: Path, content: str) -> None:
    """Never silently replace the profile of an existing measured grid."""
    try:
        with path.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(content)
    except FileExistsError:
        if path.read_text(encoding='utf-8') != content:
            raise ValueError(f'Existing profile differs: {path}; use a fresh output directory')


def run_grid(args, jar: Path, props: Path, grid: Path) -> None:
    env = dict(os.environ, RACING_JAR=str(jar), RACING_PROPS=str(props), RACING_HEAP=args.heap,
               RACING_TRACKS='' if args.tracks == ['ALL'] else ','.join(args.tracks))
    print(f'==> {grid.name}, seeds {args.seeds}', flush=True)
    run_grid_process([sys.executable, str(ROOT / 'tracks/fleet_grid.py'), args.seeds,
                      str(args.jobs), str(grid)], cwd=ROOT, env=env)


def validated_grid(grid: Path, seeds: range) -> dict:
    """The grid's manifest, once every track in it is a validated completion;
    its build, runtime, seeds, courses and race profile (all but the candidate
    slot), which every seat's grid must share."""
    manifest = json.loads((grid / 'manifest.json').read_text(encoding='utf-8'))
    run_id = hashlib.sha256(json_text(manifest).encode('utf-8')).hexdigest()
    for track in manifest['tracks']:
        if completed(grid, track, run_id, seeds) is None:
            raise ValueError(f'{grid.name}: {track} is missing, incomplete or corrupt')
    shared = {k: v for k, v in manifest.items() if k not in ('properties', 'comparison')}
    shared['profile'] = manifest['comparison']['properties']
    return shared


def report(seats: dict[int, Path], seeds: range) -> str:
    # One build, runtime, seed window, course set and profile across the seats
    # (review, 2026-09-28): the first seat's grid is the reference.
    first = min(seats)
    common = validated_grid(seats[first], seeds)
    for seat, grid in seats.items():
        if validated_grid(grid, seeds) != common:
            raise ValueError(f'seat {seat} was raced by another build, runtime, seed window, course set or profile')
    tracks = sorted(common['tracks'])
    units, per_track = [], collections.defaultdict(list)
    cand_places, cand_crash, champ_crash, champ_races = [], 0, 0, 0
    players = None
    for track in tracks:
        for seed in seeds:
            places = []
            for seat, grid in seats.items():
                race = read_race(grid / f'{track}_s{seed}.log')
                if race.slots != {seat}:
                    raise ValueError(f'seat {seat} race has candidates {sorted(race.slots)}: {track} s{seed}')
                players = players or len(race.places)
                if len(race.places) != players:
                    raise ValueError(f'seat {seat} raced another field size: {track} s{seed}')
                places.append(race.places[seat])
                cand_crash += seat in race.crashed
                champ_crash += len(race.crashed - {seat})
                champ_races += players - 1
            # (n+1)/2 is the mean place only when every seat is raced.
            if set(seats) != set(range(1, players + 1)):
                raise ValueError('the lone check needs every seat raced: seats %s of %d' % (sorted(seats), players))
            cand_places += places
            units.append(statistics.mean(places) - (players + 1) / 2)
            per_track[track].append(units[-1])
    n = len(units)
    mean = statistics.mean(units)
    se = statistics.stdev(units) / math.sqrt(n) if n > 1 else float('nan')
    races = len(cand_places)
    lines = [
        '%d races per seat, %d seats, %d track-seeds' % (n, len(seats), n),
        'lone candidate mean place %.3f  (a car in a %d-car race: %.3f)'
        % (statistics.mean(cand_places), players, (players + 1) / 2),
        'crashes      lone candidate %d in %d races (%.1f%%)   champions beside it %d in %d (%.1f%%)'
        % (cand_crash, races, 100 * cand_crash / races, champ_crash, champ_races,
           100 * champ_crash / champ_races if champ_races else 0.0),
        'track-seeds %d: candidate place minus the mean place %+.3f  (standard error %.3f; negative favours the candidate)'
        % (n, mean, se),
        # One candidate car's shift; head_to_head's mirrored difference is twice
        # this unit and prints it as its per-car line (review, 2026-09-27).
        "(one candidate car's shift in its seat: the unit of the mirrored screen's per-car line)",
    ]
    rows = sorted((statistics.mean(v), t) for t, v in per_track.items())
    lines.append('\ntracks where the lone candidate gains most (mean place difference):')
    lines += ['    %-14s %+.3f' % (t, d) for d, t in [r for r in rows if r[0] < 0][:8]]
    lines.append('tracks where it loses most:')
    lines += ['    %-14s %+.3f' % (t, d) for d, t in [r for r in rows if r[0] > 0][-8:]]
    lines.append('\n%d tracks favour the candidate, %d the champion, %d tied'
                 % (sum(d < 0 for d, _ in rows), sum(d > 0 for d, _ in rows), sum(d == 0 for d, _ in rows)))
    return '\n'.join(lines) + '\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--jar', required=True, type=Path)
    parser.add_argument('--seeds', default='1-5')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--heap', default='-Xmx8g')
    parser.add_argument('--players', type=int, default=8)
    parser.add_argument('--mode', choices=('legacy', 'informed', 'scatter'), default='legacy')
    parser.add_argument('--tracks', nargs='+', default=['ALL'])
    args = parser.parse_args(argv)
    if args.jobs < 1 or not 2 <= args.players <= 9:
        parser.error('--jobs must be positive and --players 2-9')
    jar, out = args.jar.resolve(), args.out.resolve()
    if not jar.is_file():
        parser.error('Build the candidate JAR first')
    base = (ROOT / 'tracks/lap_bench.properties').read_text(encoding='utf-8')
    overrides = {'nPlayers', 'candidateSlots', 'aiStartPlacement'}
    base = '\n'.join(line for line in base.splitlines()
                     if line.partition('=')[0].strip() not in overrides) + '\n'
    base += f'nPlayers={args.players}\naiStartPlacement={args.mode}\n'
    name = f'{args.players}p-{args.mode}'
    out.mkdir(parents=True, exist_ok=True)
    try:
        seats = {}
        for seat in range(1, args.players + 1):
            props = out / f'{name}-seat{seat}.properties'
            write_once(props, base + f'candidateSlots={seat}\n')
            seats[seat] = out / f'{name}-seat{seat}'
            run_grid(args, jar, props, seats[seat])
        lo, hi = seed_range(args.seeds)
        text = report(seats, range(lo, hi + 1))
        (out / f'{name}-1vfield.txt').write_text(text, encoding='utf-8')
        print(text, end='', flush=True)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'one-versus-field check failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
