#!/usr/bin/env python3
"""Run one candidateSlots mirror pair and publish only validated place evidence.

Both cohorts use AI1; candidateSlots alone selects the experimental policy.
Defaults cover every bundled course at the reference -Xmx8g heap. Use a fresh
output directory. Successful execution measures a candidate; it never promotes it.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

if __package__:
    from . import head_to_head
    from .benchmark_io import candidate_slots, configured_players, read_properties, update_properties
    from .fleet_grid import atomic_text, digest, directory_lock, json_text, manifest_for, seed_range
else:
    import head_to_head
    from benchmark_io import candidate_slots, configured_players, read_properties, update_properties
    from fleet_grid import atomic_text, digest, directory_lock, json_text, manifest_for, seed_range

ROOT = Path(__file__).resolve().parents[1]
JAVA_OPTIONS = ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')
SOURCES = ('promotion_pair.py', 'head_to_head.py', 'fleet_grid.py',
           'benchmark_io.py', 'forensics_common.py')


def require_plain_java_environment():
    # _JAVA_OPTIONS can override a command-line -Xmx. Never silently compare a
    # different, memory-demoted policy because of a developer/runner environment.
    if any(os.environ.get(key, '').strip() for key in JAVA_OPTIONS):
        raise ValueError('unset JAVA_TOOL_OPTIONS, JDK_JAVA_OPTIONS and _JAVA_OPTIONS; '
                         'select the comparison heap explicitly with --heap')


def write_profile(path, original, players, mode, slots):
    path.write_bytes(original)
    values = {'nPlayers': str(players), 'aiStartPlacement': mode,
              'candidateSlots': ','.join(map(str, slots)), 'useLastTrack': 'false'}
    values.update({'player%dKind' % n: 'AI1' for n in range(1, players + 1)})
    update_properties(path, values)
    roster = configured_players(path)
    if len(roster) != players or any(kind != 'AI1' for _, kind in roster.values()):
        raise ValueError('profile cannot configure the requested all-AI1 field (check maxPlayers)')
    names = [name for name, _ in roster.values()]
    if len(set(names)) != players or any('\n' in name or '\r' in name for name in names):
        raise ValueError('promotion profiles require unique, single-line player names')
    if candidate_slots(read_properties(path).get('candidateSlots', '')) != set(slots):
        raise ValueError('profile does not enable the requested candidate cohort')
    return roster


def validate_grid(grid, expected_manifest, roster, slots):
    """Do not let two mutually consistent but wrongly configured grids pass."""
    with directory_lock(grid):
        manifest, races = head_to_head.load_grid(grid)
        if manifest != expected_manifest:
            raise ValueError('grid manifest differs from the requested experiment')
        for race in races.values():
            if race.players != roster or race.slots != set(slots):
                raise ValueError('race did not run the requested candidate/champion cohorts')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--jar', type=Path, default=ROOT / 'theoreticRacing.jar')
    parser.add_argument('--props', type=Path, default=ROOT / 'tracks/lap_bench.properties')
    parser.add_argument('--java', default='java')
    parser.add_argument('--heap', default='-Xmx8g')
    parser.add_argument('--players', type=int, choices=(2, 4, 8), required=True)
    parser.add_argument('--start-mode', choices=('legacy', 'informed', 'scatter'), required=True)
    parser.add_argument('--seeds', default='1-10')
    parser.add_argument('--tracks', nargs='+', help='default: every course beside the selected JAR')
    args = parser.parse_args(argv)
    try:
        require_plain_java_environment()
        lo, hi = seed_range(args.seeds)
        if not re.fullmatch(r'-Xmx[1-9][0-9]*[kKmMgG]', args.heap):
            raise ValueError('--heap must be one explicit -Xmx memory limit, e.g. --heap=-Xmx8g')
        executable = shutil.which(args.java)
        if executable is None:
            raise ValueError('Java executable not found: ' + args.java)
        java, jar, source = Path(executable).resolve(), args.jar.resolve(), args.props.resolve()
        tracks = args.tracks if args.tracks is not None else sorted(
            p.stem for p in (jar.parent / 'tracks').glob('*.track'))
        if (not tracks or len(set(tracks)) != len(tracks)
                or any(not re.fullmatch(r'[A-Za-z0-9_-]+', t) for t in tracks)):
            raise ValueError('select a nonempty set of unique valid track names')
        tracks = sorted(tracks)
        original = source.read_bytes()
        source_hash = hashlib.sha256(original).hexdigest()
        code_hashes = {name: digest(ROOT / 'tracks' / name) for name in SOURCES}
        # Parse before creating any runtime files; malformed source input is not
        # repaired or overwritten. The caller-owned source profile is never edited.
        read_properties(source)
        out = args.out.resolve()
        out.mkdir(parents=True, exist_ok=False)
        report_path = out / 'head-to-head.txt'
        published = False
        try:
            with directory_lock(out):
                mirrors = []
                for parity, label in ((1, 'odd'), (2, 'even')):
                    profile, grid = out / (label + '.properties'), out / label
                    slots = list(range(parity, args.players + 1, 2))
                    roster = write_profile(profile, original, args.players, args.start_mode, slots)
                    manifest = manifest_for(jar, profile, java, [args.heap], tracks, lo, hi)
                    mirrors.append((profile, grid, slots, roster, manifest))

                def unchanged():
                    require_plain_java_environment()
                    if (digest(source) != source_hash
                            or any(digest(ROOT / 'tracks' / name) != value
                                   for name, value in code_hashes.items())
                            or any(manifest_for(jar, p, java, [args.heap], tracks, lo, hi) != m
                                   for p, _, _, _, m in mirrors)):
                        raise ValueError('promotion inputs changed; no comparison is valid')

                identity = {'schema': 1, 'players': args.players, 'start_mode': args.start_mode,
                            'seeds': [lo, hi], 'heap': args.heap, 'source_profile': source_hash,
                            'tooling': code_hashes, 'mirrors': [m for *_, m in mirrors]}
                atomic_text(out / 'pair-manifest.json', json_text(identity))
                unchanged()
                for profile, grid, slots, roster, manifest in mirrors:
                    env = dict(os.environ, RACING_JAR=str(jar), RACING_PROPS=str(profile),
                               RACING_JAVA=str(java), RACING_HEAP=args.heap,
                               RACING_TRACKS=','.join(tracks), RACING_TIMEOUT='3600')
                    print('==> %s: %d cars, %s starts, seeds %d-%d, %s, candidate slots %s' %
                          (grid.name, args.players, args.start_mode, lo, hi, args.heap, slots), flush=True)
                    # One JVM at a time: the reference heap is per process.
                    subprocess.run([sys.executable, str(ROOT / 'tracks/fleet_grid.py'),
                                    '%d-%d' % (lo, hi), '1', str(grid)], cwd=ROOT, env=env, check=True)
                    unchanged()
                    validate_grid(grid, manifest, roster, slots)
                # Existing scorer independently checks completion, geometry,
                # complementary assignments, mirrored seeds and finishing places.
                report = io.StringIO()
                with contextlib.redirect_stdout(report):
                    status = head_to_head.main([str(grid) for _, grid, *_ in mirrors])
                if status:
                    raise ValueError('head-to-head validation failed')
                unchanged()
                atomic_text(report_path, report.getvalue())
                published = True
                print(report.getvalue(), end='')
        finally:
            if not published:
                report_path.unlink(missing_ok=True)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('promotion pair: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
