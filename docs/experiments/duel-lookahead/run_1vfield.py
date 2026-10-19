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
the lone candidate gains places on the current champion. With every seat
raced, the control's places in one track-seed are a permutation of 1..n, so
its mean is (n+1)/2 exactly: the pairing fixes the reading's zero, and the
control otherwise contributes only the descriptive crash count.

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
from racecraft_metrics import MatchedMetrics, profile_text, sensitivity
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
    slot), which every paired grid must share."""
    manifest = json.loads((grid / 'manifest.json').read_text(encoding='utf-8'))
    run_id = hashlib.sha256(json_text(manifest).encode('utf-8')).hexdigest()
    for track in manifest['tracks']:
        if completed(grid, track, run_id, seeds) is None:
            raise ValueError(f'{grid.name}: {track} is missing, incomplete or corrupt')
    shared = {k: v for k, v in manifest.items() if k not in ('properties', 'comparison')}
    shared['profile'] = manifest['comparison']['properties']
    return shared


def report(control: Path, seats: dict[int, Path], seeds: range, reverse: bool = False) -> str:
    # The pairing means something only between races of one build, runtime and
    # course set: every seat grid must match the control (review, 2026-09-28).
    common = validated_grid(control, seeds)
    for seat, grid in seats.items():
        if validated_grid(grid, seeds) != common:
            raise ValueError(f'seat {seat} was raced by another build, runtime, seed window, course set or profile')
    tracks = sorted(common['tracks'])
    units, per_track = [], collections.defaultdict(list)
    cand_places, cand_crash, champ_crash = [], 0, 0
    matched = MatchedMetrics()
    for track in tracks:
        for seed in seeds:
            base = read_race(control / f'{track}_s{seed}.log')
            roster = set(base.players)
            if set(seats) != roster:
                raise ValueError("entrant check requires every seat exactly once")
            if base.slots != (roster if reverse else set()):
                raise ValueError(f'control race has candidates: {track} s{seed}')
            diffs = []
            for seat, grid in seats.items():
                race = read_race(grid / f'{track}_s{seed}.log')
                if race.players != base.players or race.profile != base.profile:
                    raise ValueError('entrant race roster/geometry does not match control')
                if race.slots != (roster - {seat} if reverse else {seat}):
                    raise ValueError(f'seat {seat} race has candidates {sorted(race.slots)}: {track} s{seed}')
                diffs.append(race.places[seat] - base.places[seat])
                matched.add(race.places, base.places, race.moves, base.moves, race.outcomes, base.outcomes, seat)
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
    lines += matched.lines('old champion entrant' if reverse else 'candidate',
                           'candidate resident' if reverse else 'champion')
    lines += sensitivity(per_track)
    if reverse:
        lines = [line.replace('lone candidate', 'old champion entrant')
                 .replace('champion in the same seat', 'candidate resident in the same seat')
                 .replace('candidate minus champion place', 'old champion minus candidate place')
                 .replace('negative favours the candidate', 'negative means the old champion exploits the new field')
                 .replace("one candidate car's shift", "one old champion entrant's shift")
                 .replace('tracks favour the candidate', 'tracks favour the old champion entrant')
                 .replace('the champion,', 'the candidate resident,')
                 for line in lines]
        lines.insert(0, 'REVERSE ENTRY: one old champion against n-1 candidates; all-candidate paired control.')
    return '\n'.join(lines) + '\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--jar', required=True, type=Path)
    parser.add_argument('--props', type=Path, default=ROOT/'tracks/lap_bench.properties')
    parser.add_argument('--reverse', action='store_true', help='one old champion in a candidate field')
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
    if 'ALL' in args.tracks and args.tracks != ['ALL']:
        parser.error('Use --tracks ALL by itself')
    roster = set(range(1, args.players + 1))
    name = f'{args.players}p-{args.mode}' + ('-reverse' if args.reverse else '')
    def profile(slots):
        return profile_text(args.props, {'nPlayers': str(args.players), 'aiStartPlacement': args.mode,
                            'candidateSlots': ','.join(map(str, sorted(slots)))})
    out.mkdir(parents=True, exist_ok=True)
    try:
        props = out / f'{name}-control.properties'
        write_once(props, profile(roster if args.reverse else set()))
        control = out / f'{name}-control'
        run_grid(args, jar, props, control)
        seats = {}
        for seat in range(1, args.players + 1):
            props = out / f'{name}-seat{seat}.properties'
            write_once(props, profile(roster - {seat} if args.reverse else {seat}))
            seats[seat] = out / f'{name}-seat{seat}'
            run_grid(args, jar, props, seats[seat])
        lo, hi = seed_range(args.seeds)
        text = report(control, seats, range(lo, hi + 1), args.reverse)
        (out / f'{name}-1vfield.txt').write_text(text, encoding='utf-8')
        print(text, end='', flush=True)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'one-versus-field check failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
