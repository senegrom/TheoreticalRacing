#!/usr/bin/env python3
"""Crop the surrounding whitespace from every .track file.

Translates all border points so the track's bounding box hugs a small margin,
and sets gameX/gameY to the bounding box + margin on each side. The track shape
is unchanged (pure translate + grid crop), so races stay equivalent; the smaller
grid also speeds up the reachability BFS.

Usage: python tighten_tracks.py [--apply]   (default: dry-run preview)
"""

import glob
import os
import sys

MARGIN = 3
TRACK_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_points(s):
    pts = []
    for pair in s.split(';'):
        pair = pair.strip()
        if not pair:
            continue
        x, y = pair.split(',')
        pts.append((int(x), int(y)))
    return pts


def fmt_points(pts):
    return ';'.join(f'{x},{y}' for x, y in pts)


def tighten(path, apply):
    with open(path, encoding='utf-8') as f:
        lines = f.read().splitlines()

    left = right = None
    for ln in lines:
        if ln.startswith('trackLeft='):
            left = parse_points(ln[len('trackLeft='):])
        elif ln.startswith('trackRight='):
            right = parse_points(ln[len('trackRight='):])
    if not left or not right:
        return None

    allpts = left + right
    minx = min(p[0] for p in allpts)
    miny = min(p[1] for p in allpts)
    maxx = max(p[0] for p in allpts)
    maxy = max(p[1] for p in allpts)

    dx = MARGIN - minx
    dy = MARGIN - miny
    new_gx = (maxx - minx) + 2 * MARGIN
    new_gy = (maxy - miny) + 2 * MARGIN

    left = [(x + dx, y + dy) for x, y in left]
    right = [(x + dx, y + dy) for x, y in right]

    out = []
    for ln in lines:
        if ln.startswith('gameX='):
            out.append(f'gameX={new_gx}')
        elif ln.startswith('gameY='):
            out.append(f'gameY={new_gy}')
        elif ln.startswith('trackLeft='):
            out.append('trackLeft=' + fmt_points(left))
        elif ln.startswith('trackRight='):
            out.append('trackRight=' + fmt_points(right))
        else:
            out.append(ln)

    name = os.path.basename(path).replace('.track', '')
    if apply:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out) + '\n')
    return name, new_gx, new_gy, dx, dy


def main():
    apply = '--apply' in sys.argv
    print('APPLYING' if apply else 'DRY RUN (pass --apply to write)')
    for f in sorted(glob.glob(os.path.join(TRACK_DIR, '*.track'))):
        r = tighten(f, apply)
        if r:
            name, gx, gy, dx, dy = r
            print(f'  {name:16}: new grid {gx}x{gy}  (shift {dx:+d},{dy:+d})')


if __name__ == '__main__':
    main()
