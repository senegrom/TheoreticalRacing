#!/usr/bin/env python3
"""Bench AI1 vs AI2 head-to-head across all bundled tracks.

Sets all 8 player slots to AI1, runs each track with --auto, then repeats
with all 8 set to AI2. Compares finishes/crashes/avg-moves per finish.

Usage:
  python bench_ai.py [track1 track2 ...]   # explicit tracks
  python bench_ai.py                        # regular fast bench (DEFAULT_TRACKS)
  python bench_ai.py --slow                 # second bench: the slow synthetic tracks
  python bench_ai.py --h2h [...]            # mixed 4v4 head-to-head (8-car)
  python bench_ai.py --4p [...]             # 2v2 head-to-head (4-car)
  python bench_ai.py --2v2 [...]            # alias for --4p
  python bench_ai.py --1v1 [...]            # 1v1 head-to-head (2-car endgame)
  python bench_ai.py --seeds 5 --seed-start 6 [...]  # seeds 6-10

The h2h/4p/1v1 modes all measure mean finishing place (lower=better) per kind
plus crashes; the smaller fields isolate the endgame where forcing the sole/
few remaining rivals to crash wins the race.

If no track args are given, runs DEFAULT_TRACKS (or SLOW_TRACKS with --slow).
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

if __package__:
    from .benchmark_io import configured_players, read_race
    from .fleet_grid import atomic_text, digest, json_text
else:
    # bench_iso loads this file by path rather than as a package.
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    from benchmark_io import configured_players, read_race
    from fleet_grid import atomic_text, digest, json_text

# lemans is back now that build_lemans.py uses angular ordering (clean loop,
# honest ~72-84 move laps) instead of the old greedy stitch that tangled.
# nurburgring is honest since the directional-finish fix. circle is a 1-move
# synthetic ring (tiny S/F gap, can't be made lap-honest without the checkpoint
# system) but harmless to the bench (always a tie).
# interlagos/zandvoort/hungaroring added 2026-07: real circuits (bacinger
# GeoJSON) that race a full 8-AI field to completion with fast reachability
# (2-5s). The other new tracks (serpentine/spiral/cog) are left out -- their
# wide corridors make reachability slow (37-57s), too heavy for every run.
DEFAULT_TRACKS = [
    'silverstone', 'monza', 'spa', 'monaco', 'spielberg', 'nurburgring', 'lemans',
    'interlagos', 'zandvoort', 'hungaroring',
    'circle', 'ugly_bump', 'hairpin', 'triangle', 'chicane', 'bigoval',
    # Fast synthetic geometric patterns (build_synthetic.py, small grids ->
    # reachability 1-6s): a serpentine zig-zag, an inward spiral, a flowing
    # slalom, and a scalloped closed ring (gear). The open ones are honest by
    # construction; the closed ring is made honest by orienting its start zone
    # OUTWARD so a forward finish crossing needs a full lap (build_synthetic
    # does this) -- else it darts across the S/F gap like the `circle` track.
    'zigzag', 'coil', 'slalom', 'gear',
]

# SECOND BENCH (run with --slow): the wide/large synthetic tracks whose
# reachability is too heavy (serpentine ~37s, spiral ~57s, cog ~27s) for every
# regular run. Use this as a regression guard on the slow tracks before
# promoting a new frozen standard -- confirm the new AI is >= the old one here.
SLOW_TRACKS = ['serpentine', 'serpentine2', 'spiral', 'cog']

ROOT = Path(__file__).resolve().parents[1]
JAR = str(ROOT / 'theoreticRacing.jar')
LOG = ''
PROPS = ''


def configure_runtime(directory):
    """Point mutable benchmark files at an isolated runtime directory."""
    global LOG, PROPS
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    LOG = str(directory / 'last_game.log')
    PROPS = str(directory / 'bench.properties')
    shutil.copyfile(ROOT / 'tracks' / 'bench.properties', PROPS)


def require_runtime():
    if not PROPS or not LOG:
        raise RuntimeError('benchmark runtime is not configured')


def set_all_to(kind):
    require_runtime()
    with open(PROPS, encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'^(player[1-8]Kind=).*$', r'\1' + kind, text, flags=re.MULTILINE)
    with open(PROPS, 'w', encoding='utf-8') as f:
        f.write(text)


def set_kinds(kinds):
    """kinds: list of 8 'AI1'/'AI2' strings for slots 1..8."""
    require_runtime()
    with open(PROPS, encoding='utf-8') as f:
        text = f.read()
    for i, k in enumerate(kinds, start=1):
        text = re.sub(r'^(player%dKind=).*$' % i, r'\g<1>' + k, text, flags=re.MULTILINE)
    with open(PROPS, 'w', encoding='utf-8') as f:
        f.write(text)


def set_nplayers(n):
    """Set the active field size (players 1..n race)."""
    require_runtime()
    with open(PROPS, encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'nPlayers=\d+', 'nPlayers=%d' % n, text)
    with open(PROPS, 'w', encoding='utf-8') as f:
        f.write(text)


SEEDS = [None]   # --seeds N -> [1..N]: randomized start grids (statistical bench)


def parse_race_log(path, expected_players=None):
    """Return finishes/crashes/finisher moves only for a complete classification."""
    try:
        return read_race(path, expected_players).self_play()
    except (OSError, ValueError):
        return None


def run_track(track, timeout=240, seed=None):
    require_runtime()
    cmd = ['java', '-Djava.awt.headless=true', '-jar', JAR, '--auto', '--track', track, '--props', PROPS, '--log', LOG]
    if seed is not None:
        cmd += ['--seed', str(seed)]
    if os.path.exists(LOG):
        os.remove(LOG)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or 'Aborting' in r.stdout:
        if r.stderr.strip():
            print(r.stderr.rstrip(), file=sys.stderr)
        return None
    return parse_race_log(LOG, configured_players(PROPS))


def run_track_batch(track, seeds, timeout=None):
    """One JVM for a CONTIGUOUS seed range via --seed A-B (reachability
    memoized in-process; ~35-45%% faster than singles). The game writes one
    log per seed with _sN inserted before the extension. Returns a list of
    per-seed parse_race_log results, or None if the JVM or any race failed."""
    require_runtime()
    base, ext = os.path.splitext(LOG)
    per_seed = ['%s_s%d%s' % (base, s, ext) for s in seeds]
    for p in per_seed:
        if os.path.exists(p):
            os.remove(p)
    cmd = ['java', '-Djava.awt.headless=true', '-jar', JAR, '--auto', '--track', track,
           '--props', PROPS, '--log', LOG, '--seed', '%d-%d' % (seeds[0], seeds[-1])]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       timeout=timeout or (180 + 60 * len(seeds)))
    if r.returncode != 0 or 'Aborting' in r.stdout:
        if r.stderr.strip():
            print(r.stderr.rstrip(), file=sys.stderr)
        return None
    out = []
    for p in per_seed:
        parsed = parse_race_log(p, configured_players(PROPS))
        if parsed is None:
            return None
        out.append(parsed)
    return out


def baseline_manifest(tracks, champion_jar, candidate_jar):
    """Bind a baseline to its actual frozen binary, not the candidate build."""
    java = shutil.which('java')
    if java is None:
        raise ValueError('Java executable not found')
    version = subprocess.run([java, '-version'], capture_output=True, text=True, check=True, timeout=15)
    track_hashes = {}
    for track in tracks:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', track):
            raise ValueError('invalid track name: ' + track)
        champion_track = Path(champion_jar).parent / 'tracks' / (track + '.track')
        candidate_track = Path(candidate_jar).parent / 'tracks' / (track + '.track')
        track_hashes[track] = digest(champion_track)
        if digest(candidate_track) != track_hashes[track]:
            raise ValueError('candidate/champion track data differ: ' + track)
    return {
        'schema': 1, 'champion_jar': digest(champion_jar),
        'seeds': list(SEEDS), 'properties': digest(PROPS), 'tracks': track_hashes,
        'runner': digest(Path(__file__)),
        'parsers': {name: digest(Path(__file__).with_name(name))
                    for name in ('benchmark_io.py', 'forensics_common.py')},
        'java': str(Path(java).resolve()), 'java_sha256': digest(java),
        'java_version_sha256': hashlib.sha256((version.stdout + version.stderr).encode()).hexdigest(),
        'java_environment': {key: hashlib.sha256(os.environ.get(key, '').encode()).hexdigest() for key in
                             ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS')},
    }


def load_baseline(path, manifest):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('manifest') != manifest:
        raise ValueError('baseline manifest differs or is missing; use a new BENCH_BASELINE file')
    rows = data.get('rows')
    if not isinstance(rows, dict) or set(rows) != set(manifest['tracks']):
        raise ValueError('baseline has incomplete track results')
    if data.get('rows_sha256') != hashlib.sha256(json_text(rows).encode()).hexdigest():
        raise ValueError('baseline results checksum mismatch')
    for row in rows.values():
        if (not isinstance(row, list) or len(row) != 3
                or any(type(v) is not int or v < 0 for v in row[:2])
                or type(row[2]) not in (int, float) or not math.isfinite(row[2]) or row[2] < 0
                or row[0] + row[1] > 7 * len(SEEDS)):
            raise ValueError('invalid baseline result row')
    return rows


def bench(tracks):
    global JAR
    require_runtime()
    backup = Path(PROPS).read_text(encoding='utf-8')
    candidate_jar = JAR
    champion_jar = str(Path(os.environ.get('BENCH_CHAMPION_JAR', JAR)).resolve())
    baseline_path = os.environ.get('BENCH_BASELINE')
    baseline = manifest = None
    valid = True
    try:
        set_nplayers(8)   # canonical full field; robust to a prior killed bench
        if not tracks or len(set(tracks)) != len(tracks) or not SEEDS:
            raise ValueError('benchmark requires unique tracks and a nonempty seed set')
        set_all_to('AI2')
        if baseline_path:
            candidate_digest = digest(candidate_jar)
            manifest = baseline_manifest(tracks, champion_jar, candidate_jar)
            if Path(baseline_path).exists():
                baseline = load_baseline(baseline_path, manifest)
        kinds = ('AI1',) if baseline is not None else ('AI1', 'AI2')
        results = {}
        for kind in kinds:
            JAR = champion_jar if kind == 'AI2' else candidate_jar
            set_all_to(kind)
            rows = {}
            tf = tc = 0
            tm = 0.0
            nt = 0
            # Contiguous seed windows run as ONE JVM per track (--seed A-B);
            # anything else (default [None], custom lists) keeps singles.
            batched = (len(SEEDS) > 1 and SEEDS[0] is not None
                       and list(SEEDS) == list(range(SEEDS[0], SEEDS[0] + len(SEEDS))))
            for t in tracks:
                sf = sc = 0
                sm = []
                bad = False
                if batched:
                    try:
                        rs = run_track_batch(t, list(SEEDS))
                    except subprocess.TimeoutExpired:
                        rs = None
                    if rs is None:
                        bad = True
                    else:
                        for f, c, mvs in rs:
                            sf += f
                            sc += c
                            if mvs:
                                sm.append(sum(mvs) / len(mvs))
                else:
                    for seed in SEEDS:
                        try:
                            r = run_track(t, seed=seed)
                        except subprocess.TimeoutExpired:
                            r = None
                        if r is None:
                            bad = True
                            break
                        f, c, mvs = r
                        sf += f
                        sc += c
                        if mvs:   # a zero-finisher race (2-car ends at first crash) must not drag mv to 0
                            sm.append(sum(mvs) / len(mvs))
                if bad:
                    rows[t] = None
                    valid = False
                    print(f'  [{kind}] {t:18}: TIMEOUT/INVALID')
                    continue
                avg = sum(sm) / len(sm) if sm else 0.0
                rows[t] = (sf, sc, avg)
                tf += sf
                tc += sc
                tm += avg
                nt += 1
            results[kind] = (tf, tc, tm / max(1, nt), rows)
        if baseline_path:
            set_all_to('AI2')
            if (digest(candidate_jar) != candidate_digest
                    or baseline_manifest(tracks, champion_jar, candidate_jar) != manifest):
                raise ValueError('benchmark inputs changed during the run')
            if baseline is None and valid:
                rows = results['AI2'][3]
                atomic_text(baseline_path, json_text({
                    'manifest': manifest, 'rows': rows,
                    'rows_sha256': hashlib.sha256(json_text(rows).encode()).hexdigest(),
                }))
                print(f'# seeded champion baseline -> {os.path.basename(baseline_path)}')
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('benchmark: ' + str(error), file=sys.stderr)
        return False
    finally:
        JAR = candidate_jar
        Path(PROPS).write_text(backup, encoding='utf-8')

    if baseline is not None:
        rows = {t: baseline[t] for t in tracks}
        results['AI2'] = (sum(v[0] for v in rows.values()), sum(v[1] for v in rows.values()),
                          sum(v[2] for v in rows.values()) / len(rows), rows)

    # Report
    print()
    print(f'{"track":18} | {"AI1 f/c mv":>15} | {"AI2 f/c mv":>15} | diff')
    print('-' * 70)
    for t in tracks:
        r1 = results['AI1'][3].get(t)
        r2 = results['AI2'][3].get(t)
        if r1 is None or r2 is None:
            print(f'{t:18} | {"INVALID":>15} | {"INVALID":>15} |')
            continue
        f1, c1, m1 = r1
        f2, c2, m2 = r2
        diff = m1 - m2
        print(f'{t:18} | {f1}/{c1} mv={m1:7.3f} | {f2}/{c2} mv={m2:7.3f} | {diff:+.3f}')
    print('-' * 70)
    if not valid:
        print('TOTAL: INVALID (incomplete experiment)')
        return False
    f1, c1, m1, _ = results['AI1']
    f2, c2, m2, _ = results['AI2']
    print(f'{"TOTAL":18} | f={f1} c={c1} mv={m1:.3f} | f={f2} c={c2} mv={m2:.3f} | {m1-m2:+.3f}')
    return valid


def run_track_h2h(track, timeout=240, seed=None):
    """Run one race with the current PROPS kinds. Returns
    {kind: (sum_places, count, crashes)} or None if invalid."""
    require_runtime()
    cmd = ['java', '-Djava.awt.headless=true', '-jar', JAR, '--auto', '--track', track, '--props', PROPS, '--log', LOG]
    if seed is not None:
        cmd += ['--seed', str(seed)]
    if os.path.exists(LOG):
        os.remove(LOG)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or 'Aborting' in r.stdout or not os.path.exists(LOG):
        if r.stderr.strip():
            print(r.stderr.rstrip(), file=sys.stderr)
        return None
    try:
        race = read_race(LOG, configured_players(PROPS))
        out = {}
        for kind in ('AI1', 'AI2'):
            numbers = [n for n, (_, k) in race.players.items() if k == kind]
            if not numbers:
                raise ValueError('mixed benchmark requires both AI cohorts')
            out[kind] = (sum(race.places[n] for n in numbers), len(numbers),
                         sum(n in race.crashed for n in numbers))
        return out
    except (OSError, ValueError) as error:
        print('benchmark log: ' + str(error), file=sys.stderr)
        return None


def bench_field(tracks, nplayers=8, ai1n=4, label='h2h'):
    """Mixed-field head-to-head: ai1n x AI1 vs (nplayers-ai1n) x AI2 in one
    race, run in both grid orderings to cancel start-position bias. Metric:
    mean finishing place per kind (lower better; the two means sum to
    nplayers+1) + crashes. nplayers=2 is the 1v1 endgame (forcing the sole
    rival to crash = a win), 4 is 2v2, 8 is 4v4."""
    require_runtime()
    if not tracks or not SEEDS or not 0 < ai1n < nplayers <= 9:
        raise ValueError('mixed benchmark requires tracks, seeds and two nonempty cohorts')
    valid = True
    with open(PROPS, encoding='utf-8') as f:
        backup = f.read()
    try:
        set_nplayers(nplayers)
        front = ['AI1'] * ai1n + ['AI2'] * (nplayers - ai1n)
        rows = {}
        tot = {'AI1': [0, 0, 0], 'AI2': [0, 0, 0]}
        for t in tracks:
            agg = {'AI1': [0, 0, 0], 'AI2': [0, 0, 0]}
            ok = True
            for seed in SEEDS:
                for kinds in (front, list(reversed(front))):
                    set_kinds(kinds)
                    try:
                        r = run_track_h2h(t, seed=seed)
                    except subprocess.TimeoutExpired:
                        r = None
                    if (r is None or r['AI1'][1] != ai1n
                            or r['AI2'][1] != nplayers - ai1n):
                        ok = False
                        break
                    for kind in ('AI1', 'AI2'):
                        s, n, c = r[kind]
                        agg[kind][0] += s
                        agg[kind][1] += n
                        agg[kind][2] += c
                if not ok:
                    break
            if not ok:
                rows[t] = None
                valid = False
                print(f'  [{label}] {t:18}: INVALID')
                continue
            rows[t] = agg
            for kind in ('AI1', 'AI2'):
                for i in range(3):
                    tot[kind][i] += agg[kind][i]
    finally:
        with open(PROPS, 'w', encoding='utf-8') as f:
            f.write(backup)

    print()
    print(f'# {label}: {ai1n}x AI1 vs {nplayers - ai1n}x AI2 ({nplayers}-car field), mean place lower=better')
    print(f'{"track":18} | {"AI1 place/cr":>14} | {"AI2 place/cr":>14}')
    print('-' * 56)
    for t in tracks:
        agg = rows.get(t)
        if agg is None:
            print(f'{t:18} | {"INVALID":>14} | {"INVALID":>14}')
            continue
        p1 = agg['AI1'][0] / agg['AI1'][1]
        p2 = agg['AI2'][0] / agg['AI2'][1]
        print(f'{t:18} | {p1:6.2f} c={agg["AI1"][2]}    | {p2:6.2f} c={agg["AI2"][2]}')
    print('-' * 56)
    if not valid:
        print('TOTAL mean place: INVALID (incomplete experiment)')
        return False
    p1 = tot['AI1'][0] / tot['AI1'][1]
    p2 = tot['AI2'][0] / tot['AI2'][1]
    print(f'{"TOTAL mean place":18} | {p1:6.3f} c={tot["AI1"][2]}   | {p2:6.3f} c={tot["AI2"][2]}')
    return valid


def positive_integer(value):
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError('must be an integer') from error
    if number < 1:
        raise argparse.ArgumentTypeError('must be positive')
    return number


def build_parser():
    parser = argparse.ArgumentParser(
        description='Benchmark the candidate AI1 controller against frozen AI2.'
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--h2h', dest='mode', action='store_const', const='h2h',
                       help='run a mixed 4v4 eight-car field')
    modes.add_argument('--4p', '--2v2', dest='mode', action='store_const', const='4p',
                       help='run a mixed 2v2 four-car field')
    modes.add_argument('--1v1', dest='mode', action='store_const', const='1v1',
                       help='run a two-car endgame')
    parser.set_defaults(mode='self-play')
    parser.add_argument('--slow', action='store_true',
                        help='use the slow-track suite when no tracks are listed')
    parser.add_argument('--seeds', type=positive_integer, metavar='COUNT',
                        help='run COUNT consecutive randomized grids')
    parser.add_argument('--seed-start', type=positive_integer, metavar='SEED',
                        help='first seed (requires --seeds)')
    parser.add_argument('tracks', nargs='*', help='track names (default: regular suite)')
    return parser


def parse_cli(argv):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.seed_start is not None and args.seeds is None:
        parser.error('--seed-start requires --seeds')

    seed_start = args.seed_start if args.seed_start is not None else 1
    args.seed_values = (
        list(range(seed_start, seed_start + args.seeds))
        if args.seeds is not None else [None]
    )
    if not args.tracks:
        args.tracks = list(SLOW_TRACKS if args.slow else DEFAULT_TRACKS)
    return args


def main(argv):
    global SEEDS
    args = parse_cli(argv)
    SEEDS = args.seed_values
    if args.seeds is not None:
        print(f'# statistical bench: seeds {SEEDS[0]}-{SEEDS[-1]} ({len(SEEDS)} grids per track)')

    if args.mode == '1v1':
        return bench_field(args.tracks, 2, 1, '1v1')
    if args.mode == '4p':
        return bench_field(args.tracks, 4, 2, '4p')
    if args.mode == 'h2h':
        return bench_field(args.tracks, 8, 4, 'h2h')
    return bench(args.tracks)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='theoretical-racing-bench-') as directory:
        configure_runtime(directory)
        raise SystemExit(0 if main(sys.argv[1:]) else 1)
