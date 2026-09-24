#!/usr/bin/env python3
"""One candidate car against a field of champions: the invasion check.

The mirrored screen (run_screen.py) races half a field of candidates against
half a field of champions. A promotion must also survive the opposite regime,
ONE candidate car entering a field of n-1 champions -- a policy can win the
mixed field and still lose places as a lone entrant, or the reverse. The
candidate is rotated through every seat (candidateSlots=k, k = 1..n), and each
race is paired with the all-champion race of the same track, seed and seat:
the same jar with no candidateSlots, which the arm's identity check has
already shown to race exactly as the champion. The reading is the candidate's
place minus the champion's place in that seat of that race -- negative means
the lone candidate gains places on the current champion. Seat and seed
effects cancel in the pairing.

    run_1vfield.py --jar ARM.jar --out DIR [--seeds 1-5] [--jobs 3]
                   [--heap=-Xmx8g] [--players 8] [--mode legacy] [--tracks ALL]
"""
from __future__ import annotations

import argparse
import collections
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
from fleet_grid import seed_range  # noqa: E402


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
    subprocess.run([sys.executable, str(ROOT / 'tracks/fleet_grid.py'), args.seeds,
                    str(args.jobs), str(grid)], cwd=ROOT, env=env, check=True)


def report(control: Path, seats: dict[int, Path], seeds: range) -> str:
    tracks = sorted(json.loads((control / 'manifest.json').read_text(encoding='utf-8'))['tracks'])
    units, per_track = [], collections.defaultdict(list)
    cand_places, cand_crash, champ_crash = [], 0, 0
    for track in tracks:
        for seed in seeds:
            base = read_race(control / f'{track}_s{seed}.log')
            if base.slots:
                raise ValueError(f'control race has candidates: {track} s{seed}')
            diffs = []
            for seat, grid in seats.items():
                race = read_race(grid / f'{track}_s{seed}.log')
                if race.slots != {seat}:
                    raise ValueError(f'seat {seat} race has candidates {sorted(race.slots)}: {track} s{seed}')
                diffs.append(race.places[seat] - base.places[seat])
                cand_places.append(race.places[seat])
                cand_crash += seat in race.crashed
                champ_crash += seat in base.crashed
            units.append(statistics.mean(diffs))
            per_track[track].append(statistics.mean(diffs))
    n = len(units)
    mean = statistics.mean(units)
    se = statistics.stdev(units) / math.sqrt(n) if n > 1 else float('nan')
    lines = [
        '%d races per seat, %d seats, %d paired track-seeds' % (n, len(seats), n),
        'lone candidate mean place %.3f  (the champion in the same seats: %.3f)'
        % (statistics.mean(cand_places), statistics.mean(cand_places) - mean),
        'crashes      lone candidate %d   champion in the same seat %d' % (cand_crash, champ_crash),
        'paired track-seeds %d: candidate minus champion place %+.3f  (standard error %.3f; negative favours the candidate)'
        % (n, mean, se),
    ]
    rows = sorted((statistics.mean(v), t) for t, v in per_track.items())
    lines.append('\ntracks where the lone candidate gains most (mean place difference):')
    lines += ['    %-14s %+.3f' % (t, d) for d, t in rows[:8]]
    lines.append('tracks where it loses most:')
    lines += ['    %-14s %+.3f' % (t, d) for d, t in rows[-8:]]
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
        props = out / f'{name}-control.properties'
        write_once(props, base)
        control = out / f'{name}-control'
        run_grid(args, jar, props, control)
        seats = {}
        for seat in range(1, args.players + 1):
            props = out / f'{name}-seat{seat}.properties'
            write_once(props, base + f'candidateSlots={seat}\n')
            seats[seat] = out / f'{name}-seat{seat}'
            run_grid(args, jar, props, seats[seat])
        lo, hi = seed_range(args.seeds)
        text = report(control, seats, range(lo, hi + 1))
        (out / f'{name}-1vfield.txt').write_text(text, encoding='utf-8')
        print(text, end='', flush=True)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'one-versus-field check failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
