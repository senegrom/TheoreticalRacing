#!/usr/bin/env python3
"""Run mirrored candidate/champion grids without changing user.properties.

Defaults are a bounded regression screen, NOT the full promotion battery.
Each grid and comparison uses the repository's existing provenance validation.
Use --tracks ALL --seeds 1-10 for a full track/seed slice in every start mode.

--props names the base profile (default tracks/lap_bench.properties); its keys,
an arm's flags for instance, go into both cohorts' profiles, and nPlayers,
aiStartPlacement and candidateSlots are set here. Profiles are written as
canonical properties (racecraft_metrics.profile_text): the JVM reads the same
map as from the old verbatim profiles, but an output folder started with the
older tools refuses to resume -- use a fresh one.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tracks'))
from racecraft_metrics import profile_text  # noqa: E402
from fleet_grid import run_grid_process  # noqa: E402

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
    parser.add_argument('--props', type=Path, default=ROOT/'tracks/lap_bench.properties',
                        help='base profile; its keys go into both cohorts')
    parser.add_argument('--seeds', default='1-2')
    parser.add_argument('--jobs', type=int, default=1)
    # The Nordschleife's maps need 8 GiB; at 2 GiB a full slice never completed.
    parser.add_argument('--heap', default='-Xmx8g')
    parser.add_argument('--players', nargs='+', type=int, choices=(2, 4, 8), default=[2, 8])
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
    out.mkdir(parents=True, exist_ok=True)
    try:
        for players in dict.fromkeys(args.players):
            for mode in dict.fromkeys(args.modes):
                grids = []
                for parity, label in ((1, 'odd'), (2, 'even')):
                    name = f'{players}p-{mode}-{label}'
                    props = out/f'{name}.properties'
                    slots = ','.join(map(str, range(parity, players+1, 2)))
                    write_once(props, profile_text(args.props, {'nPlayers': str(players),
                               'aiStartPlacement': mode, 'candidateSlots': slots}))
                    grid = out/name
                    env = dict(os.environ, RACING_JAR=str(jar), RACING_PROPS=str(props),
                               RACING_HEAP=args.heap,
                               RACING_TRACKS='' if args.tracks == ['ALL'] else ','.join(args.tracks))
                    print(f'==> {name}, seeds {args.seeds}', flush=True)
                    run_grid_process([sys.executable, str(ROOT/'tracks/fleet_grid.py'), args.seeds,
                                      str(args.jobs), str(grid)], cwd=ROOT, env=env)
                    grids.append(str(grid))
                report = subprocess.run([sys.executable, str(ROOT/'tracks/head_to_head.py'), *grids],
                                        cwd=ROOT, check=True, capture_output=True, text=True)
                (out/f'{players}p-{mode}-head-to-head.txt').write_text(report.stdout, encoding='utf-8')
                print(report.stdout, end='', flush=True)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        # head_to_head says why it refused a pair on its stderr.
        detail = getattr(error, 'stderr', None)
        print(f'duel screen failed: {error}' + (f'\n{detail.rstrip()}' if detail else ''), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
