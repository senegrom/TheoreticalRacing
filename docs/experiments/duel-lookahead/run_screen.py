#!/usr/bin/env python3
"""Run mirrored candidate/champion grids without changing user.properties.

Defaults are a bounded regression screen, NOT the full promotion battery.
Each grid and comparison uses the repository's existing provenance validation.
Use --tracks ALL --seeds 1-10 for a full track/seed slice in every start mode.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRACKS = ['hairpin', 'chicane', 'bigoval', 'circle', 'gear', 'monaco', 'silverstone', 'zigzag']


def write_once(path: Path, content: str) -> None:
    """Never silently replace the profile of an existing measured grid."""
    try:
        with path.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(content)
    except FileExistsError:
        if path.read_text(encoding='utf-8') != content:
            raise ValueError(f'Existing profile differs: {path}; use a fresh output directory')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--jar', type=Path, default=ROOT/'theoreticRacing.jar')
    parser.add_argument('--seeds', default='1-2')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--heap', default='-Xmx2g')
    parser.add_argument('--players', nargs='+', type=int, choices=(2, 8), default=[2, 8])
    parser.add_argument('--modes', nargs='+', choices=('legacy', 'informed', 'scatter'),
                        default=['legacy', 'informed', 'scatter'])
    parser.add_argument('--tracks', nargs='+', default=DEFAULT_TRACKS)
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    jar, out = args.jar.resolve(), args.out.resolve()
    if not jar.is_file():
        parser.error('Build the candidate JAR before running the screen')
    if 'ALL' in args.tracks and args.tracks != ['ALL']:
        parser.error('Use --tracks ALL by itself')
    base = (ROOT/'tracks/lap_bench.properties').read_text(encoding='utf-8')
    overrides = {'nPlayers', 'candidateSlots', 'aiStartPlacement'}
    base = '\n'.join(line for line in base.splitlines()
                     if line.partition('=')[0].strip() not in overrides)+'\n'
    out.mkdir(parents=True, exist_ok=True)
    try:
        for players in dict.fromkeys(args.players):
            for mode in dict.fromkeys(args.modes):
                grids = []
                for parity, label in ((1, 'odd'), (2, 'even')):
                    name = f'{players}p-{mode}-{label}'
                    props = out/f'{name}.properties'
                    slots = ','.join(map(str, range(parity, players+1, 2)))
                    write_once(props, base+f'nPlayers={players}\naiStartPlacement={mode}\n'
                               f'candidateSlots={slots}\n')
                    grid = out/name
                    env = dict(os.environ, RACING_JAR=str(jar), RACING_PROPS=str(props),
                               RACING_HEAP=args.heap,
                               RACING_TRACKS='' if args.tracks == ['ALL'] else ','.join(args.tracks))
                    print(f'==> {name}, seeds {args.seeds}', flush=True)
                    subprocess.run([sys.executable, str(ROOT/'tracks/fleet_grid.py'), args.seeds,
                                    str(args.jobs), str(grid)], cwd=ROOT, env=env, check=True)
                    grids.append(str(grid))
                report = subprocess.run([sys.executable, str(ROOT/'tracks/head_to_head.py'), *grids],
                                        cwd=ROOT, check=True, capture_output=True, text=True)
                (out/f'{players}p-{mode}-head-to-head.txt').write_text(report.stdout, encoding='utf-8')
                print(report.stdout, end='', flush=True)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'duel screen failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
