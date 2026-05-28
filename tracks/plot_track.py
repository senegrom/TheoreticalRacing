#!/usr/bin/env python3
"""Quick ASCII visualizer for a .track file."""
import sys


def main():
    path = sys.argv[1]
    cols = 80
    with open(path) as f:
        text = f.read()
    grid_x = grid_y = None
    left = []
    right = []
    for line in text.splitlines():
        if line.startswith('gameX='):
            grid_x = int(line.split('=')[1])
        elif line.startswith('gameY='):
            grid_y = int(line.split('=')[1])
        elif line.startswith('trackLeft='):
            data = line.split('=', 1)[1]
            left = [tuple(map(int, p.split(','))) for p in data.split(';')]
        elif line.startswith('trackRight='):
            data = line.split('=', 1)[1]
            right = [tuple(map(int, p.split(','))) for p in data.split(';')]

    if not grid_x or not grid_y:
        sys.exit('no grid dims')

    sx = cols / grid_x
    sy = (cols // 2) / grid_y
    rows = int(grid_y * sy) + 1
    cols = int(grid_x * sx) + 1

    canvas = [[' '] * cols for _ in range(rows)]

    def plot_polyline(pts, ch):
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            r0 = round(y0 * sy)
            c0 = round(x0 * sx)
            r1 = round(y1 * sy)
            c1 = round(x1 * sx)
            steps = max(abs(r1 - r0), abs(c1 - c0)) + 1
            for s in range(steps):
                t = s / max(1, steps - 1)
                r = round(r0 + (r1 - r0) * t)
                c = round(c0 + (c1 - c0) * t)
                if 0 <= r < rows and 0 <= c < cols:
                    canvas[r][c] = ch

    plot_polyline(left, 'L')
    plot_polyline(right, 'R')

    # mark start (first points) and finish (last points)
    if left:
        r = round(left[0][1] * sy)
        c = round(left[0][0] * sx)
        if 0 <= r < rows and 0 <= c < cols:
            canvas[r][c] = 'S'
        r = round(left[-1][1] * sy)
        c = round(left[-1][0] * sx)
        if 0 <= r < rows and 0 <= c < cols:
            canvas[r][c] = 'F'
    if right:
        r = round(right[0][1] * sy)
        c = round(right[0][0] * sx)
        if 0 <= r < rows and 0 <= c < cols:
            canvas[r][c] = 's'
        r = round(right[-1][1] * sy)
        c = round(right[-1][0] * sx)
        if 0 <= r < rows and 0 <= c < cols:
            canvas[r][c] = 'f'

    for row in canvas:
        print(''.join(row))


if __name__ == '__main__':
    main()
