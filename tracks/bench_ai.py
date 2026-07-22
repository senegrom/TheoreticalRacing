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
  python bench_ai.py --1v1 [...]            # 1v1 head-to-head (2-car endgame)

The h2h/4p/1v1 modes all measure mean finishing place (lower=better) per kind
plus crashes; the smaller fields isolate the endgame where forcing the sole/
few remaining rivals to crash wins the race.

If no track args are given, runs DEFAULT_TRACKS (or SLOW_TRACKS with --slow).
"""

import os
import re
import subprocess
import sys

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
    'circle', 'the_long_loop', 'sprint', 'hairpin', 'triangle',
    'chicane', 'bigoval', 'curve',
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

JAR = r'E:\OneDrive\Coding\Java\theoreticRacing\theoreticRacing.jar'
LOG = r'E:\OneDrive\Coding\Java\theoreticRacing\last_game.log'
PROPS = r'E:\OneDrive\Coding\Java\theoreticRacing\user.properties'
PROPS_BACKUP = PROPS + '.bench.bak'


def set_all_to(kind):
    with open(PROPS) as f:
        text = f.read()
    text = re.sub(r'(player[1-8]Kind=)AI[12]', r'\1' + kind, text)
    with open(PROPS, 'w') as f:
        f.write(text)


def set_kinds(kinds):
    """kinds: list of 8 'AI1'/'AI2' strings for slots 1..8."""
    with open(PROPS) as f:
        text = f.read()
    for i, k in enumerate(kinds, start=1):
        text = re.sub(r'(player%dKind=)AI[12]' % i, r'\g<1>' + k, text)
    with open(PROPS, 'w') as f:
        f.write(text)


def set_nplayers(n):
    """Set the active field size (players 1..n race)."""
    with open(PROPS) as f:
        text = f.read()
    text = re.sub(r'nPlayers=\d+', 'nPlayers=%d' % n, text)
    with open(PROPS, 'w') as f:
        f.write(text)


SEEDS = [None]   # --seeds N -> [1..N]: randomized start grids (statistical bench)


def run_track(track, timeout=240, seed=None):
    cmd = ['java', '-jar', JAR, '--auto', '--track', track, '--props', PROPS, '--log', LOG]
    if seed is not None:
        cmd += ['--seed', str(seed)]
    if os.path.exists(LOG):
        os.remove(LOG)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if 'Aborting' in r.stdout or not os.path.exists(LOG):
        return None
    moves, crashes, finishes = {}, set(), []
    with open(LOG, encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^(\d+) p(\d+) ', line)
            if not m:
                continue
            pn = int(m.group(2))
            moves[pn] = moves.get(pn, 0) + 1
            if 'CRASH' in line:
                crashes.add(pn)
            elif 'FINISH' in line:
                finishes.append((pn, moves[pn]))
    return len(finishes), len(crashes), [m for _, m in finishes]


def bench(tracks):
    # Backup props once before doing anything
    with open(PROPS) as f:
        backup = f.read()
    # Frozen-champion cache: AI2 is the promoted standard and is IDENTICAL on
    # every candidate run, so re-benching it doubles wall time for nothing. Set
    # BENCH_BASELINE=<file> to run only the AI1 (candidate) column and read AI2
    # from the cache; the first run with no cache seeds it. Delete the file when
    # the champion changes (a new promotion).
    baseline_path = os.environ.get('BENCH_BASELINE')
    baseline = None
    if baseline_path and os.path.exists(baseline_path):
        import json
        with open(baseline_path) as f:
            baseline = {k: tuple(v) if v else None for k, v in json.load(f).items()}
    kinds = ('AI1',) if baseline is not None else ('AI1', 'AI2')
    try:
        set_nplayers(8)   # canonical full field; robust to a prior killed bench
        results = {}
        for kind in kinds:
            set_all_to(kind)
            rows = {}
            tf = tc = 0
            tm = 0.0
            nt = 0
            for t in tracks:
                sf = sc = 0
                sm = []
                bad = False
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
                    print(f'  [{kind}] {t:18}: TIMEOUT/INVALID')
                    continue
                avg = sum(sm) / len(sm) if sm else 0.0
                rows[t] = (sf, sc, avg)
                tf += sf
                tc += sc
                tm += avg
                nt += 1
            results[kind] = (tf, tc, tm / max(1, nt), rows)
    finally:
        with open(PROPS, 'w') as f:
            f.write(backup)

    if baseline is not None:
        # Reconstruct the AI2 column from the cache (per-track rows + totals).
        r2rows = {t: baseline.get(t) for t in tracks}
        tf2 = sum(v[0] for v in r2rows.values() if v)
        tc2 = sum(v[1] for v in r2rows.values() if v)
        nt2 = sum(1 for v in r2rows.values() if v)
        tm2 = sum(v[2] for v in r2rows.values() if v) / max(1, nt2)
        results['AI2'] = (tf2, tc2, tm2, r2rows)
    elif baseline_path:
        import json
        with open(baseline_path, 'w') as f:
            json.dump(results['AI2'][3], f)
        print(f'# seeded champion baseline -> {os.path.basename(baseline_path)}')

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
        print(f'{t:18} | {f1}/{c1} mv={m1:5.1f}  | {f2}/{c2} mv={m2:5.1f}  | {diff:+.1f}')
    print('-' * 70)
    f1, c1, m1, _ = results['AI1']
    f2, c2, m2, _ = results['AI2']
    print(f'{"TOTAL":18} | f={f1} c={c1} mv={m1:.2f} | f={f2} c={c2} mv={m2:.2f} | {m1-m2:+.2f}')


def run_track_h2h(track, timeout=240, seed=None):
    """Run one race with the current PROPS kinds. Returns
    {kind: (sum_places, count, crashes)} or None if invalid."""
    cmd = ['java', '-jar', JAR, '--auto', '--track', track, '--props', PROPS, '--log', LOG]
    if seed is not None:
        cmd += ['--seed', str(seed)]
    if os.path.exists(LOG):
        os.remove(LOG)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if 'Aborting' in r.stdout or not os.path.exists(LOG):
        return None
    name_kind = {}
    place_name = {}
    crashes = {'AI1': 0, 'AI2': 0}
    in_results = False
    with open(LOG, encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^player\d+ name=(\S+) kind=(AI[12])', line)
            if m:
                name_kind[m.group(1)] = m.group(2)
                continue
            m = re.match(r'^\d+ p\d+ (AI[12]) .*CRASH', line)
            if m:
                crashes[m.group(1)] += 1
                continue
            if line.startswith('# results'):
                in_results = True
                continue
            if in_results:
                m = re.match(r'^(\d+)\. (\S+)', line)
                if m:
                    place_name[int(m.group(1))] = m.group(2)
    out = {}
    for kind in ('AI1', 'AI2'):
        places = [p for p, n in place_name.items() if name_kind.get(n) == kind]
        out[kind] = (sum(places), len(places), crashes[kind])
    return out


def bench_field(tracks, nplayers=8, ai1n=4, label='h2h'):
    """Mixed-field head-to-head: ai1n x AI1 vs (nplayers-ai1n) x AI2 in one
    race, run in both grid orderings to cancel start-position bias. Metric:
    mean finishing place per kind (lower better; the two means sum to
    nplayers+1) + crashes. nplayers=2 is the 1v1 endgame (forcing the sole
    rival to crash = a win), 4 is 2v2, 8 is 4v4."""
    with open(PROPS) as f:
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
                    if r is None:
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
                print(f'  [{label}] {t:18}: INVALID')
                continue
            rows[t] = agg
            for kind in ('AI1', 'AI2'):
                for i in range(3):
                    tot[kind][i] += agg[kind][i]
    finally:
        with open(PROPS, 'w') as f:
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
        p1 = agg['AI1'][0] / max(1, agg['AI1'][1])
        p2 = agg['AI2'][0] / max(1, agg['AI2'][1])
        print(f'{t:18} | {p1:6.2f} c={agg["AI1"][2]}    | {p2:6.2f} c={agg["AI2"][2]}')
    print('-' * 56)
    p1 = tot['AI1'][0] / max(1, tot['AI1'][1])
    p2 = tot['AI2'][0] / max(1, tot['AI2'][1])
    print(f'{"TOTAL mean place":18} | {p1:6.3f} c={tot["AI1"][2]}   | {p2:6.3f} c={tot["AI2"][2]}')


def bench_h2h(tracks):
    bench_field(tracks, 8, 4, 'h2h')


if __name__ == '__main__':
    args = sys.argv[1:]
    # --tag NAME: run fully isolated (own props copy + own log) so a second
    # bench can run simultaneously without colliding on user.properties/last_game.log
    if '--tag' in args:
        _i = args.index('--tag')
        _tag = args[_i + 1]
        args = args[:_i] + args[_i + 2:]
        import shutil
        import atexit
        _orig = PROPS
        PROPS = os.path.join(os.path.dirname(PROPS), 'user_%s.properties' % _tag)
        LOG = os.path.join(os.path.dirname(LOG), 'last_game_%s.log' % _tag)
        shutil.copy(_orig, PROPS)
        atexit.register(lambda: [os.remove(p) for p in (PROPS, LOG) if os.path.exists(p)])
        print('# isolated run: props=%s log=%s' % (os.path.basename(PROPS), os.path.basename(LOG)))
    h2h = '--h2h' in args
    one_v_one = '--1v1' in args
    four_p = '--4p' in args
    slow = '--slow' in args
    args = [a for a in args if a not in ('--h2h', '--1v1', '--4p', '--slow')]
    if '--seeds' in args:
        i = args.index('--seeds')
        SEEDS = list(range(1, int(args[i + 1]) + 1))
        args = args[:i] + args[i + 2:]
        print(f'# statistical bench: {len(SEEDS)} randomized start grids per track')
    tracks = args if args else (SLOW_TRACKS if slow else DEFAULT_TRACKS)
    if one_v_one:
        bench_field(tracks, 2, 1, '1v1')   # endgame: forcing the sole rival to crash = a win
    elif four_p:
        bench_field(tracks, 4, 2, '4p')     # 2v2
    elif h2h:
        bench_field(tracks, 8, 4, 'h2h')    # 4v4
    else:
        bench(tracks)
