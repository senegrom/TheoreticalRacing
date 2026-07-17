#!/usr/bin/env python3
"""Generate synthetic geometric .track files by offsetting a designed centerline.

Unlike build_track_from_geojson.py (which buffers a real circuit centerline into
a donut), these patterns are fully under our control, so we offset the centerline
directly by +/- half-width to get the two borders. This is exact and paired
(trackLeft[i] and trackRight[i] straddle centerline[i]); it stays valid as long as
every corner's turn radius exceeds the half-width, which each generator guarantees.

Open patterns (serpentine, spiral) race from one cap to the other, like chicane.
Closed patterns (cog) are cut at a start/finish point into two open borders with a
tiny S/F gap, like the F1 circuits.

Usage: build_synthetic.py <pattern> <output.track> <name> <gridX> <gridY> [width]
  pattern: serpentine | spiral | cog
"""

import math
import sys


def unit(dx, dy):
    n = math.hypot(dx, dy)
    return (dx / n, dy / n) if n else (0.0, 0.0)


# ---------------------------------------------------------------- centerlines

def gen_serpentine(lanes=5, length=170.0, pitch=34.0, step=6.0, pitch_jitter=0.0):
    """Horizontal lanes stacked `pitch` apart, joined by semicircular hairpins on
    alternating ends -- a boustrophedon snake you drive lane by lane. Open.

    pitch_jitter>0 gives every hairpin a slightly different radius: the gap to the
    next lane becomes pitch + pitch_jitter*(offset in [-1,1)), where the offsets
    are a golden-ratio low-discrepancy sequence -- deterministic, and each curve
    distinct rather than repeating. The smallest gap must still exceed the corridor
    width (each hairpin radius = gap/2 must stay above the half-width, else the
    inner offset border pinches). jitter=0 reproduces the uniform serpentine."""
    phi = 0.6180339887498949  # golden-ratio conjugate: well-spread distinct offsets
    gaps = [pitch + pitch_jitter * (2.0 * (((k + 1) * phi) % 1.0) - 1.0) for k in range(lanes - 1)]
    ys = [0.0]
    for g in gaps:
        ys.append(ys[-1] + g)
    c = []
    for k in range(lanes):
        y = ys[k]
        if k % 2 == 0:  # rightward
            x = 0.0
            while x < length:
                c.append((x, y))
                x += step
            c.append((length, y))
            end_x, side = length, +1.0
        else:  # leftward
            x = length
            while x > 0.0:
                c.append((x, y))
                x -= step
            c.append((0.0, y))
            end_x, side = 0.0, -1.0
        if k < lanes - 1:  # semicircular hairpin up to the next lane, its own radius
            r = gaps[k] / 2.0
            cy = y + r
            steps = max(6, int(math.pi * r / step))
            for s in range(1, steps):  # skip endpoints (lane ends supply them)
                ang = -math.pi / 2 + math.pi * s / steps
                c.append((end_x + side * r * math.cos(ang), cy + r * math.sin(ang)))
    return c, False


def gen_spiral(turns=2.6, pitch=46.0, r_min=14.0, step=7.0):
    """An Archimedean spiral wound inward -- drive from the outside to the core.
    Arm spacing (pitch) exceeds the corridor width so the arms never touch. Open."""
    b = pitch / (2 * math.pi)
    theta_max = 2 * math.pi * turns
    r0 = r_min + b * theta_max
    c = []
    theta = 0.0
    while theta < theta_max:
        r = r0 - b * theta
        c.append((r * math.cos(theta), r * math.sin(theta)))
        theta += step / max(r, 1.0)  # arc-length-ish steps
    r = r0 - b * theta_max
    c.append((r * math.cos(theta_max), r * math.sin(theta_max)))
    return c, False


def gen_cog(lobes=5, radius=105.0, amp=9.0, step=6.0):
    """A scalloped ring: radius wobbles sinusoidally, so the loop zig-zags in and
    out `lobes` times around a closed circuit. Cut into an S/F gap. Closed.
    Amplitude is kept gentle so the concave troughs' curvature radius stays well
    above the corridor half-width (otherwise the inner offset border pinches)."""
    c = []
    circumference = 2 * math.pi * radius
    n = max(120, int(circumference / step))
    for i in range(n):
        t = 2 * math.pi * i / n
        r = radius + amp * math.sin(lobes * t)
        c.append((r * math.cos(t), r * math.sin(t)))
    return c, True


def gen_slalom(waves=3, length=230.0, amp=24.0, step=6.0):
    """A flowing sine-wave corridor -- a smooth left-right slalom, gentler than
    the serpentine's hairpins. Open. Amplitude/wavelength kept mild so the wave
    crests' curvature radius stays above the corridor half-width."""
    c = []
    x = 0.0
    while x < length:
        c.append((x, amp * math.sin(2 * math.pi * waves * x / length)))
        x += step
    c.append((length, amp * math.sin(2 * math.pi * waves)))
    return c, False


GENERATORS = {
    'serpentine': gen_serpentine,
    'spiral': gen_spiral,
    'slalom': gen_slalom,
    'cog': gen_cog,
}


# ------------------------------------------------------------------- offsets

def offset(center, closed, w):
    """Offset the centerline by +/- w/2 along the local normal. Returns paired
    (left, right) polylines. For closed loops the borders are closed rings; the
    caller opens them at the S/F cut."""
    m = len(center)
    left, right = [], []
    for i in range(m):
        if closed:
            a, b = center[(i - 1) % m], center[(i + 1) % m]
        else:
            a = center[i - 1] if i > 0 else center[i]
            b = center[i + 1] if i < m - 1 else center[i]
        tx, ty = unit(b[0] - a[0], b[1] - a[1])
        nx, ny = -ty, tx  # +90 degrees
        cx, cy = center[i]
        left.append((cx + w / 2 * nx, cy + w / 2 * ny))
        right.append((cx - w / 2 * nx, cy - w / 2 * ny))
    return left, right


def open_closed_borders(left, right):
    """For a closed loop, punch the S/F gap at the loop's rightmost point (a
    smooth, single-segment spot) and rotate both rings to run from just past the
    cut back around to just before it."""
    cut = max(range(len(left)), key=lambda i: (left[i][0] + right[i][0]))
    left = left[cut + 1:] + left[:cut + 1]
    right = right[cut + 1:] + right[:cut + 1]
    return left, right


# --------------------------------------------------------------------- grid

def to_grid(left, right, grid_x, grid_y, margin=3):
    allpts = left + right
    minx = min(p[0] for p in allpts)
    maxx = max(p[0] for p in allpts)
    miny = min(p[1] for p in allpts)
    maxy = max(p[1] for p in allpts)
    scale = min((grid_x - 2 * margin) / (maxx - minx), (grid_y - 2 * margin) / (maxy - miny))

    def g(p):
        return (round(margin + (p[0] - minx) * scale), round(margin + (maxy - p[1]) * scale))

    return [g(p) for p in left], [g(p) for p in right], scale


def dedupe(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if p != out[-1]:
            out.append(p)
    return out


def min_corridor_cells(left, right):
    return min(math.hypot(l[0] - r[0], l[1] - r[1]) for l, r in zip(left, right))


def main():
    if len(sys.argv) < 6:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    pattern, out_path, name = sys.argv[1], sys.argv[2], sys.argv[3]
    grid_x, grid_y = int(sys.argv[4]), int(sys.argv[5])
    width = float(sys.argv[6]) if len(sys.argv) >= 7 else 24.0

    if pattern not in GENERATORS:
        print(f"unknown pattern {pattern}; choose from {list(GENERATORS)}", file=sys.stderr)
        sys.exit(2)

    # Extra key=value args tune the generator (e.g. lanes=4 length=95 pitch=24).
    kwargs = {}
    for a in sys.argv[7:]:
        if '=' in a:
            k, v = a.split('=', 1)
            kwargs[k] = float(v) if '.' in v else int(v)

    center, closed = GENERATORS[pattern](**kwargs)
    left, right = offset(center, closed, width)
    if closed:
        left, right = open_closed_borders(left, right)

    left_g, right_g, scale = to_grid(left, right, grid_x, grid_y)
    left_g, right_g = dedupe(left_g), dedupe(right_g)

    # Closed loops: the start zone (a 2-deep band the game extends off the
    # start line, +90 degrees of right0->left0) must point OUTWARD, away from
    # the loop interior. If it points inward it overlaps the finish line just
    # across the S/F cut, so cars cross the finish in a couple of moves without
    # lapping (the degenerate dart). Swapping the two borders flips that band
    # 180 degrees while leaving the corridor polygon identical -- so the zone
    # ends up outside the loop and a forward finish crossing needs a full lap.
    if closed:
        allp = left_g + right_g
        cx = sum(p[0] for p in allp) / len(allp)
        cy = sum(p[1] for p in allp) / len(allp)
        l0, r0 = left_g[0], right_g[0]
        dir_x, dir_y = l0[1] - r0[1], r0[0] - l0[0]  # matches makeStartZone
        out_x, out_y = (l0[0] + r0[0]) / 2 - cx, (l0[1] + r0[1]) / 2 - cy
        if dir_x * out_x + dir_y * out_y < 0:  # zone points inward -> flip it out
            left_g, right_g = right_g, left_g

    with open(out_path, 'w') as f:
        f.write("# Theoretical Racing track file\n")
        f.write(f"# Synthetic pattern: {pattern}\n")
        f.write(f"name={name}\n")
        f.write(f"gameX={grid_x}\n")
        f.write(f"gameY={grid_y}\n")
        f.write("trackLeft=" + ";".join(f"{x},{y}" for x, y in left_g) + "\n")
        f.write("trackRight=" + ";".join(f"{x},{y}" for x, y in right_g) + "\n")

    print(f"Wrote {out_path}: {len(left_g)} left / {len(right_g)} right pts, "
          f"corridor ~{min_corridor_cells(left_g, right_g):.1f} cells, scale={scale:.3f}")


if __name__ == "__main__":
    main()
