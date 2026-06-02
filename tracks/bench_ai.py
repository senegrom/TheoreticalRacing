#!/usr/bin/env python3
"""Bench AI1 vs AI2 head-to-head across all bundled tracks.

Sets all 8 player slots to AI1, runs each track with --auto, then repeats
with all 8 set to AI2. Compares finishes/crashes/avg-moves per finish.

Usage:
  python bench_ai.py [track1 track2 ...]

If no track args are given, runs the full default bench set.
"""

import os
import re
import subprocess
import sys

# Skip lemans and nurburgring: both are degenerate benchmarks with an
# exploitable near-instant finish across the S/F gap (depth-4 search finishes
# nurburgring in ~4 moves), so their move counts are a tie-break artifact
# rather than a measure of racing quality.
DEFAULT_TRACKS = [
    'silverstone', 'monza', 'spa', 'monaco', 'spielberg',
    'circle', 'the_long_loop', 'sprint', 'hairpin', 'triangle',
    'chicane', 'bigoval', 'curve',
]

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


if __name__ == '__main__':
    tracks = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_TRACKS
    bench(tracks)
