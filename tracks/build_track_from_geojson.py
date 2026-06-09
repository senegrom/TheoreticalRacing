#!/usr/bin/env python3
"""Convert bacinger/f1-circuits GeoJSON centerlines into theoreticRacing .track files.

Strategy: buffer the centerline with round caps into a closed polygon, then split
its exterior at the cap-endpoints into two long sides (trackLeft/trackRight). This
handles tight features (Loews hairpin, etc) without self-intersecting offsets.

Usage: build_track_from_geojson.py <input.geojson> <output.track> <name>
                                   <gridX> <gridY> [target_points] [width_m]
"""

import json
import math
import sys
from shapely.geometry import LineString

EARTH_R = 6371000.0


def project(lon, lat, lat0):
    x = math.radians(lon) * math.cos(math.radians(lat0)) * EARTH_R
    y = math.radians(lat) * EARTH_R
    return x, y


def signed_area(pts):
    n = len(pts)
    a = 0.0
    for i in range(n):
        j = (i + 1) % n
        a += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
    return 0.5 * a


def smooth(pts, iterations=2):
    """Chaikin-style smoothing on an open polyline."""
    for _ in range(iterations):
        new = [pts[0]]
        for i in range(1, len(pts) - 1):
            new.append((
                (pts[i - 1][0] + 2 * pts[i][0] + pts[i + 1][0]) / 4,
                (pts[i - 1][1] + 2 * pts[i][1] + pts[i + 1][1]) / 4,
            ))
        new.append(pts[-1])
        pts = new
    return pts


def closest_idx(pts, target):
    best = 0
    best_d = float('inf')
    for i, p in enumerate(pts):
        d = (p[0] - target[0]) ** 2 + (p[1] - target[1]) ** 2
        if d < best_d:
            best_d = d
            best = i
    return best


def main():
    if len(sys.argv) < 6:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    geojson_path = sys.argv[1]
    output_path = sys.argv[2]
    name = sys.argv[3]
    grid_x = int(sys.argv[4])
    grid_y = int(sys.argv[5])
    target = int(sys.argv[6]) if len(sys.argv) >= 7 else 60
    width_m = float(sys.argv[7]) if len(sys.argv) >= 8 else 18.0

    with open(geojson_path) as f:
        data = json.load(f)
    coords = data['features'][0]['geometry']['coordinates']

    if coords[0] == coords[-1]:
        coords = coords[:-1]

    lat0 = sum(c[1] for c in coords) / len(coords)
    pts_m = [project(c[0], c[1], lat0) for c in coords]

    # Moderate smoothing so the buffer doesn't pinch through tight corners.
    pts_m = smooth(pts_m, iterations=6)

    # Densify so long straights get enough sample points; the buffer's outer/inner
    # rings inherit density from the input. Without this, the cut point near a
    # main-straight midpoint can land between two sparse ring points, creating a
    # multi-segment-long S/F gap.
    target_step = 15.0  # meters between samples
    densified = [pts_m[0]]
    for i in range(1, len(pts_m)):
        prev = pts_m[i - 1]
        cur = pts_m[i]
        dist = math.hypot(cur[0] - prev[0], cur[1] - prev[1])
        if dist > target_step:
            steps = int(math.ceil(dist / target_step))
            for j in range(1, steps):
                t = j / steps
                densified.append((prev[0] + (cur[0] - prev[0]) * t, prev[1] + (cur[1] - prev[1]) * t))
        densified.append(cur)
    pts_m = densified

    # Buffer the CLOSED centerline so we get a donut polygon (outer + interior hole).
    # The outer ring traces the outside of the corridor; the inner ring traces the
    # inside. Both will get a small S/F gap punched into them at the same angular
    # location so the result is a single open polyline pair the game can consume.
    center_closed = LineString(pts_m + [pts_m[0]])
    half_w = width_m / 2.0
    buffered = center_closed.buffer(half_w, cap_style=1, join_style=1, resolution=8)
    if buffered.is_empty:
        print("buffer empty", file=sys.stderr)
        sys.exit(1)
    if buffered.geom_type == 'MultiPolygon':
        buffered = max(buffered.geoms, key=lambda g: g.area)
    if not buffered.interiors:
        print("closed-loop buffer has no interior hole -- try smaller width", file=sys.stderr)
        sys.exit(1)

    outer = list(buffered.exterior.coords)
    if outer[0] == outer[-1]:
        outer = outer[:-1]
    # Pick the largest interior hole; tight curves can produce tiny artifact holes.
    largest_interior = max(buffered.interiors, key=lambda r: abs(0.5 * sum(
        r.coords[i][0] * r.coords[(i + 1) % len(r.coords)][1] -
        r.coords[(i + 1) % len(r.coords)][0] * r.coords[i][1]
        for i in range(len(r.coords)))))
    inner = list(largest_interior.coords)
    if inner[0] == inner[-1]:
        inner = inner[:-1]

    # Outer is CCW (Shapely convention); inner is CW for interior holes. For our
    # corridor polygon (trackLeft + reverse(trackRight) + close) to trace the
    # annular region cleanly, both rings need to run in the same direction along
    # the corridor. Reverse the inner ring so it is CCW too.
    inner = list(reversed(inner))

    # S/F cut: at the longest centerline segment within a small window around
    # coords[0] (the real start/finish, where the bacinger trace begins). This
    # puts the in-game S/F on the real pit straight (matching the original) while
    # snapping to the longest local straight so the ring-cut stays clean (cutting
    # at a point that sits on a curve self-intersects the corridor).
    n = len(pts_m)
    window = max(2, n // 12)
    long_i = 0
    long_d = -1.0
    for off in range(-window, window + 1):
        i = off % n
        j = (i + 1) % n
        dx = pts_m[j][0] - pts_m[i][0]
        dy = pts_m[j][1] - pts_m[i][1]
        d = dx * dx + dy * dy
        if d > long_d:
            long_d = d
            long_i = i
    next_i = (long_i + 1) % n
    cut_xy = ((pts_m[long_i][0] + pts_m[next_i][0]) / 2.0, (pts_m[long_i][1] + pts_m[next_i][1]) / 2.0)

    i_out = closest_idx(outer, cut_xy)
    i_in = closest_idx(inner, cut_xy)

    # Rotate each ring so the cut becomes the open end. We drop the closing
    # vertex and rotate so the polyline runs from "just after cut" to "just before cut".
    def open_ring_at(ring, cut_idx):
        return ring[cut_idx + 1:] + ring[:cut_idx + 1]

    left = open_ring_at(outer, i_out)
    right = open_ring_at(inner, i_in)

    cstart = pts_m[long_i]

    # Make sure both run in the same direction along the centerline. Compare the
    # second point of each ring against the tangent at the cut.
    def tangent_at_cut():
        a = pts_m[long_i]
        b = pts_m[next_i]
        tx = b[0] - a[0]
        ty = b[1] - a[1]
        tn = math.hypot(tx, ty)
        return (tx / tn, ty / tn) if tn else (1.0, 0.0)

    tcx, tcy = tangent_at_cut()

    def aligned(side):
        if len(side) < 2:
            return True
        dx = side[1][0] - side[0][0]
        dy = side[1][1] - side[0][1]
        return dx * tcx + dy * tcy > 0

    if not aligned(left):
        left = list(reversed(left))
    if not aligned(right):
        right = list(reversed(right))

    # Scale to grid
    all_pts = left + right
    minx = min(p[0] for p in all_pts)
    maxx = max(p[0] for p in all_pts)
    miny = min(p[1] for p in all_pts)
    maxy = max(p[1] for p in all_pts)
    spanx = maxx - minx
    spany = maxy - miny
    margin = 3
    scale = min((grid_x - 2 * margin) / spanx, (grid_y - 2 * margin) / spany)

    def to_grid(p):
        gx = round(margin + (p[0] - minx) * scale)
        gy = round(margin + (maxy - p[1]) * scale)
        return (gx, gy)

    left_grid = [to_grid(p) for p in left]
    right_grid = [to_grid(p) for p in right]

    def dedupe(pts):
        out = [pts[0]]
        for p in pts[1:]:
            if p != out[-1]:
                out.append(p)
        return out

    left_grid = dedupe(left_grid)
    right_grid = dedupe(right_grid)

    def sample(pts, count):
        if len(pts) <= count:
            return pts
        step = len(pts) / count
        return [pts[int(i * step)] for i in range(count)]

    left_grid = sample(left_grid, target)
    right_grid = sample(right_grid, target)
    m = min(len(left_grid), len(right_grid))
    left_grid = left_grid[:m]
    right_grid = right_grid[:m]

    # Force the real racing direction (all our circuits race CLOCKWISE as drawn
    # north-up). The grid is screen-y-down, where a clockwise loop has positive
    # shoelace. If the generated corridor came out counter-clockwise, reverse the
    # traversal by swapping the two borders and reversing point order -- this
    # leaves the corridor polygon (hence its validity) untouched, only flipping
    # which way is "forward" start->finish.
    def corridor_shoelace(left, right):
        loop = left + right[::-1]
        s = 0.0
        k = len(loop)
        for i in range(k):
            x1, y1 = loop[i]
            x2, y2 = loop[(i + 1) % k]
            s += x1 * y2 - x2 * y1
        return s

    if corridor_shoelace(left_grid, right_grid) < 0:  # counter-clockwise -> flip
        left_grid, right_grid = right_grid[::-1], left_grid[::-1]

    with open(output_path, 'w') as f:
        f.write("# Theoretical Racing track file\n")
        f.write(f"# Traced from bacinger/f1-circuits ({geojson_path.split('/')[-1]})\n")
        f.write(f"name={name}\n")
        f.write(f"gameX={grid_x}\n")
        f.write(f"gameY={grid_y}\n")
        f.write("trackLeft=" + ";".join(f"{p[0]},{p[1]}" for p in left_grid) + "\n")
        f.write("trackRight=" + ";".join(f"{p[0]},{p[1]}" for p in right_grid) + "\n")

    print(f"Wrote {output_path}: {len(left_grid)} left, {len(right_grid)} right points")


if __name__ == "__main__":
    main()
