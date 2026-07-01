#!/usr/bin/env python3
"""Bench AI1 vs AI2 head-to-head across all bundled tracks.

Sets all 8 player slots to AI1, runs each track with --auto, then repeats
with all 8 set to AI2. Compares finishes/crashes/avg-moves per finish.

Usage:
  python bench_ai.py [track1 track2 ...]   # explicit tracks
  python bench_ai.py                        # regular fast bench (DEFAULT_TRACKS)
  python bench_ai.py --slow                 # second bench: the slow synthetic tracks
  python bench_ai.py --h2h [...]            # mixed 4v4 head-to-head instead

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
    # reachability 1-6s): a small serpentine zig-zag, an inward spiral, and a
    # flowing slalom. All OPEN (start != finish) so the race is honest; closed
    # synthetic loops dart across the S/F gap (the circle problem) and are left
    # out until a lap-checkpoint system exists.
    'zigzag', 'coil', 'slalom',
]

# SECOND BENCH (run with --slow): the wide/large synthetic tracks whose
# reachability is too heavy (serpentine ~37s, spiral ~57s) for every regular
# run. Use this as a regression guard on the slow tracks before promoting a new
# frozen standard -- confirm the new AI is at least as good as the old one here.
SLOW_TRACKS = ['serpentine', 'spiral']

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


def run_track(track, timeout=240):
    r = subprocess.run(['java', '-jar', JAR, '--auto', '--track', track],
                       capture_output=True, text=True, timeout=timeout)
    if 'Aborting' in r.stdout:
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
    try:
        results = {}
        for kind in ('AI1', 'AI2'):
            set_all_to(kind)
            rows = {}
            tf = tc = 0
            tm = 0.0
            nt = 0
            for t in tracks:
                try:
                    r = run_track(t)
                except subprocess.TimeoutExpired:
                    rows[t] = None
                    print(f'  [{kind}] {t:18}: TIMEOUT')
                    continue
                if r is None:
                    rows[t] = None
                    print(f'  [{kind}] {t:18}: INVALID')
                    continue
                f, c, mvs = r
                avg = sum(mvs) / len(mvs) if mvs else 0
                rows[t] = (f, c, avg)
                tf += f
                tc += c
                tm += avg
                nt += 1
            results[kind] = (tf, tc, tm / max(1, nt), rows)
    finally:
        with open(PROPS, 'w') as f:
            f.write(backup)

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


def run_track_h2h(track, timeout=240):
    """Run one race with the current PROPS kinds. Returns
    {kind: (sum_places, count, crashes)} or None if invalid."""
    r = subprocess.run(['java', '-jar', JAR, '--auto', '--track', track],
                       capture_output=True, text=True, timeout=timeout)
    if 'Aborting' in r.stdout:
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


def bench_h2h(tracks):
    """Mixed-field head-to-head: 4xAI1 vs 4xAI2 in one race, run in both
    grid orderings to cancel start-position bias. Metric: mean finishing
    place per kind (1-8; the two means sum to 9, lower is better)."""
    with open(PROPS) as f:
        backup = f.read()
    try:
        front = ['AI1'] * 4 + ['AI2'] * 4
        rows = {}
        tot = {'AI1': [0, 0, 0], 'AI2': [0, 0, 0]}
        for t in tracks:
            agg = {'AI1': [0, 0, 0], 'AI2': [0, 0, 0]}
            ok = True
            for kinds in (front, list(reversed(front))):
                set_kinds(kinds)
                try:
                    r = run_track_h2h(t)
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
                rows[t] = None
                print(f'  [h2h] {t:18}: INVALID')
                continue
            rows[t] = agg
            for kind in ('AI1', 'AI2'):
                for i in range(3):
                    tot[kind][i] += agg[kind][i]
    finally:
        with open(PROPS, 'w') as f:
            f.write(backup)

    print()
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


if __name__ == '__main__':
    args = sys.argv[1:]
    h2h = '--h2h' in args
    slow = '--slow' in args
    args = [a for a in args if a not in ('--h2h', '--slow')]
    tracks = args if args else (SLOW_TRACKS if slow else DEFAULT_TRACKS)
    if h2h:
        bench_h2h(tracks)
    else:
        bench(tracks)
