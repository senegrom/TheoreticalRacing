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
  pattern: serpentine | spiral | cog | random | weave | lobes | hybrid | fractal (seed=N per circuit)
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



def gen_random(seed=1, npts=12, box=240.0, disp=0.55, minr=17.0, step=6.0, passes=8):
    """A MEANINGFUL random closed circuit, not a noisy corridor: sample points,
    take their convex hull (a plausible outer loop), pull each edge midpoint a
    random fraction toward the centroid (real corners, chicanes and straights of
    varying length), then Chaikin-smooth until every discrete turn radius clears
    minr -- the same radius-above-half-width invariant the designed patterns
    guarantee, so the inner offset border never pinches. Uniformly resampled;
    candidate loops whose centerline self-intersects or whose non-adjacent
    sections pass closer than 2*minr (a neck the offset borders would merge
    across) are rejected and the next derived seed is tried. Deterministic per
    seed: the track-seed is a second fuzzing axis alongside the start-grid seed.
    Pass minr >= width/2 + 3 for the chosen width."""
    import random

    def hull(ps):
        ps = sorted(set(ps))
        def half(seq):
            h = []
            for q in seq:
                while len(h) >= 2 and ((h[-1][0]-h[-2][0])*(q[1]-h[-2][1])
                                       - (h[-1][1]-h[-2][1])*(q[0]-h[-2][0])) <= 0:
                    h.pop()
                h.append(q)
            return h
        lo, hi = half(ps), half(reversed(ps))
        return lo[:-1] + hi[:-1]

    def circumradius(a, b, c):
        area2 = abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
        if area2 < 1e-9:
            return float('inf')
        return (math.hypot(b[0]-a[0], b[1]-a[1]) * math.hypot(c[0]-b[0], c[1]-b[1])
                * math.hypot(a[0]-c[0], a[1]-c[1])) / (2.0 * area2)

    def chaikin(loop):
        out = []
        m = len(loop)
        for i in range(m):
            a, b = loop[i], loop[(i+1) % m]
            out.append((0.75*a[0]+0.25*b[0], 0.75*a[1]+0.25*b[1]))
            out.append((0.25*a[0]+0.75*b[0], 0.25*a[1]+0.75*b[1]))
        return out

    def resample(loop, d):
        pts = []
        m = len(loop)
        carry = 0.0
        for i in range(m):
            a, b = loop[i], loop[(i+1) % m]
            seg = math.hypot(b[0]-a[0], b[1]-a[1])
            pos = carry
            while pos < seg:
                f = pos / seg
                pts.append((a[0]+f*(b[0]-a[0]), a[1]+f*(b[1]-a[1])))
                pos += d
            carry = pos - seg
        return pts

    def seg_intersect(p1, p2, p3, p4):
        def cr(o, a, b):
            return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
        d1, d2 = cr(p3, p4, p1), cr(p3, p4, p2)
        d3, d4 = cr(p1, p2, p3), cr(p1, p2, p4)
        return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))

    for attempt in range(64):
        rng = random.Random(seed * 1000 + attempt)
        pts = [(rng.uniform(0, box), rng.uniform(0, box)) for _ in range(npts)]
        h = hull(pts)
        if len(h) < 5:
            continue
        cx = sum(q[0] for q in h) / len(h)
        cy = sum(q[1] for q in h) / len(h)
        loop = []
        for i in range(len(h)):
            a, b = h[i], h[(i+1) % len(h)]
            loop.append(a)
            mx, my = (a[0]+b[0])/2.0, (a[1]+b[1])/2.0
            f = rng.uniform(0.0, disp)
            loop.append((mx + f*(cx-mx), my + f*(cy-my)))
        # Measure curvature on a step-spaced RESAMPLE each pass: raw Chaikin
        # points sit sub-unit apart, where the discrete circumradius of
        # near-collinear triples reads huge regardless of the curve's true
        # radius -- checking them directly accepts arbitrarily sharp elbows.
        c = None
        for _ in range(passes):
            loop = chaikin(loop)
            rc = resample(loop, step)
            m = len(rc)
            if m >= 24 and min(circumradius(rc[(i-1) % m], rc[i], rc[(i+1) % m])
                               for i in range(m)) >= minr:
                c = rc
                break
        if c is None:
            continue
        m = len(c)
        bad = False
        for i in range(m):
            for j in range(i+1, m):
                if abs(i-j) <= 3 or (i == 0 and j >= m-3):
                    continue
                if seg_intersect(c[i], c[(i+1) % m], c[j], c[(j+1) % m]):
                    bad = True
                    break
                dx = c[i][0]-c[j][0]
                dy = c[i][1]-c[j][1]
                # Neck bound: offset borders (w/2 ~ minr-3 each side) merge
                # when non-adjacent centerline sections pass closer than about
                # the corridor width; 1.8*minr leaves legitimate hairpins
                # (diametric distance 2*minr at the tightest radius) alone.
                # The index guard skips everything within a half-circle's arc
                # at the minimum radius, so a U-turn never tests against its
                # own far side.
                guard = max(6, int(3.5 * minr / step))
                if abs(i-j) > guard and m-abs(i-j) > guard and dx*dx+dy*dy < (1.8*minr)**2:
                    bad = True
                    break
            if bad:
                break
        if bad:
            continue
        return c, True
    raise SystemExit(f"gen_random: no valid loop after 64 attempts (seed {seed})")



# ---------------------------------------------- shared random-family helpers

def _circumradius(a, b, c):
    area2 = abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))
    if area2 < 1e-9:
        return float('inf')
    return (math.hypot(b[0]-a[0], b[1]-a[1]) * math.hypot(c[0]-b[0], c[1]-b[1])
            * math.hypot(a[0]-c[0], a[1]-c[1])) / (2.0 * area2)


def _chaikin(loop):
    out = []
    m = len(loop)
    for i in range(m):
        a, b = loop[i], loop[(i+1) % m]
        out.append((0.75*a[0]+0.25*b[0], 0.75*a[1]+0.25*b[1]))
        out.append((0.25*a[0]+0.75*b[0], 0.25*a[1]+0.75*b[1]))
    return out


def _resample(loop, d):
    pts = []
    m = len(loop)
    carry = 0.0
    for i in range(m):
        a, b = loop[i], loop[(i+1) % m]
        seg = math.hypot(b[0]-a[0], b[1]-a[1])
        pos = carry
        while pos < seg:
            f = pos / seg
            pts.append((a[0]+f*(b[0]-a[0]), a[1]+f*(b[1]-a[1])))
            pos += d
        carry = pos - seg
    return pts


def _seg_intersect(p1, p2, p3, p4):
    def cr(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    d1, d2 = cr(p3, p4, p1), cr(p3, p4, p2)
    d3, d4 = cr(p1, p2, p3), cr(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def _finish_loop(loop, minr, step, passes, neck_factor=1.8):
    """Smooth until a step-spaced resample clears minr everywhere, then
    reject on centerline self-intersection or non-adjacent necks. Returns
    the finished centerline or None."""
    c = None
    for _ in range(passes):
        loop = _chaikin(loop)
        rc = _resample(loop, step)
        m = len(rc)
        if m >= 24 and min(_circumradius(rc[(i-1) % m], rc[i], rc[(i+1) % m])
                           for i in range(m)) >= minr:
            c = rc
            break
    if c is None:
        return None
    m = len(c)
    guard = max(6, int(3.5 * minr / step))
    for i in range(m):
        for j in range(i+1, m):
            if abs(i-j) <= 3 or (i == 0 and j >= m-3):
                continue
            if _seg_intersect(c[i], c[(i+1) % m], c[j], c[(j+1) % m]):
                return None
            dx = c[i][0]-c[j][0]
            dy = c[i][1]-c[j][1]
            if abs(i-j) > guard and m-abs(i-j) > guard \
                    and dx*dx+dy*dy < (neck_factor*minr)**2:
                return None
    return c


def gen_weave(seed=1, cols=4, rows=3, minr=8.0, step=6.0, passes=6):
    """The outline of a random spanning tree on a cols x rows grid: a
    closed loop that genuinely WEAVES -- serpentine passages, U-turns and
    parallel corridors at controlled spacing (see module docstring for the
    pitch/inset guarantee). Deterministic per seed; rejected candidates
    try derived seeds."""
    import random
    # Sizing system (all three constraints bind): sampled OUTER arcs at
    # radius `inset` survive Chaikin at ~0.9x, so inset = 1.15*minr; INNER
    # corner arcs need radius rin = 1.35*minr and occupy (inset+rin) of leg
    # on each side, and a wall-tip wrap puts two of them on one pitch, so
    # pitch = 2*(inset+rin) = 5*minr; opposite sides of an edge then sit
    # 2*inset = 2.3*minr apart and adjacent corridors pitch-2*inset =
    # 2.7*minr -- both above the 1.8*minr merge bound.
    inset = 1.25 * minr
    rin = 1.35 * minr
    pitch = 5.2 * minr
    for attempt in range(64):
        rng = random.Random(seed * 1000 + attempt)
        nodes = [(c, r) for c in range(cols) for r in range(rows)]
        adj = {n: [] for n in nodes}
        start = rng.choice(nodes)
        seen = {start}
        stack = [start]
        while stack:
            c, r = stack[-1]
            nbrs = [(c+dc, r+dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if (c+dc, r+dr) in adj and (c+dc, r+dr) not in seen]
            if not nbrs:
                stack.pop()
                continue
            nxt = rng.choice(nbrs)
            adj[(c, r)].append(nxt)
            adj[nxt].append((c, r))
            seen.add(nxt)
            stack.append(nxt)

        def ang(u, v):
            return math.atan2(v[1]-u[1], v[0]-u[0])

        # contour walk over directed half-edges: from (u,v) continue with
        # the next neighbor of v clockwise from u -- traces the outline.
        first = min(nodes, key=lambda n: (n[1], n[0]))
        v0 = max(adj[first], key=lambda w: ang(first, w))
        walk = []
        u, v = first, v0
        for _ in range(8 * cols * rows):
            walk.append((u, v))
            back = ang(v, u)
            nxt = min(adj[v], key=lambda w: (ang(v, w) - back) % (2*math.pi)
                      if (ang(v, w) - back) % (2*math.pi) > 1e-9 else 2*math.pi)
            u, v = v, nxt
            if (u, v) == (first, v0):
                break
        # Proper offset-polyline emission (right-hand offset): per half-edge
        # a midpoint at +inset; at each junction, OUTER corners (left turns
        # and leaf U-turns) get arc points swept CCW from the incoming to
        # the outgoing right-normal, INNER corners (right turns) get the
        # single miter point v + (n1+n2)*inset/(1+d1.d2). One-sided arcs
        # zigzag against the midpoints and floor the curvature (measured).
        loop = []
        nwalk = len(walk)
        for idx, (a, b) in enumerate(walk):
            mx = (a[0] + b[0]) / 2.0 * pitch
            my = (a[1] + b[1]) / 2.0 * pitch
            d1x, d1y = unit(b[0]-a[0], b[1]-a[1])
            n1x, n1y = d1y, -d1x
            loop.append((mx + n1x*inset, my + n1y*inset))
            nb = walk[(idx + 1) % nwalk][1]
            d2x, d2y = unit(nb[0]-b[0], nb[1]-b[1])
            n2x, n2y = d2y, -d2x
            cross = d1x*d2y - d1y*d2x
            dot = d1x*d2x + d1y*d2y
            vx, vy = b[0]*pitch, b[1]*pitch
            if cross > 1e-9 or (abs(cross) <= 1e-9 and dot < 0):
                a1 = math.atan2(n1y, n1x)
                sweep = (math.atan2(n2y, n2x) - a1) % (2*math.pi)
                narc = max(2, int(sweep / (math.pi / 8)))
                for k in range(1, narc + 1):
                    th = a1 + sweep * k / (narc + 1)
                    loop.append((vx + inset*math.cos(th), vy + inset*math.sin(th)))
            elif cross < -1e-9:
                # Inner corners: a miter point stays a corner and Chaikin
                # rounds any corner to ~0.6x its local support (measured ~5
                # at the tongue corners) -- emit a genuine three-point inner
                # arc instead: center on the bisector at distance
                # (inset+rin)/(1+d1.d2) along (n1+n2), tangent radius rin.
                denom = 1.0 + dot
                if denom > 1e-6:
                    cxr = vx + (n1x+n2x)*(inset+rin)/denom
                    cyr = vy + (n1y+n2y)*(inset+rin)/denom
                    bx, by = unit(n1x+n2x, n1y+n2y)
                    loop.append((cxr - n1x*rin, cyr - n1y*rin))
                    loop.append((cxr - bx*rin, cyr - by*rin))
                    loop.append((cxr - n2x*rin, cyr - n2y*rin))
        c = _finish_loop(loop, minr, step, passes)
        if c is not None:
            return c, True
    raise SystemExit(f"gen_weave: no valid loop after 64 attempts (seed {seed})")


def gen_lobes(seed=1, minr=8.0, step=6.0, passes=6):
    """Radial-harmonic loop r(theta) = R(1 + sum a_k cos(k theta + phi)).
    A dominant k=2 is an hourglass/peanut, k=3 a trefoil, k=5 a gear;
    the harmonic mix is drawn per seed with amplitudes capped so the
    waist clears the neck bound. Deterministic per seed."""
    import random
    for attempt in range(64):
        rng = random.Random(seed * 1000 + attempt)
        R = 110.0
        ks = rng.choice([(2,), (2, 3), (3,), (2, 5), (3, 5), (2, 4)])
        amps = {}
        budget = rng.uniform(0.28, 0.42)
        for idx, k in enumerate(ks):
            a = budget * (0.72 if idx == 0 else 0.28) / max(1, len(ks) - 1 if idx else 1)
            amps[k] = a * rng.uniform(0.8, 1.0)
        phis = {k: rng.uniform(0, 2*math.pi) for k in ks}
        n = 180
        loop = []
        for i in range(n):
            th = 2*math.pi*i/n
            r = R * (1.0 + sum(amps[k]*math.cos(k*th + phis[k]) for k in ks))
            loop.append((r*math.cos(th), r*math.sin(th)))
        c = _finish_loop(loop, minr, step, passes, neck_factor=2.0)
        if c is not None:
            return c, True
    raise SystemExit(f"gen_lobes: no valid loop after 64 attempts (seed {seed})")



def _inner_arc(vx, vy, n1x, n1y, n2x, n2y, dot, inset, rin):
    """Three points rounding an inner corner at node (vx,vy): center on the
    bisector at (inset+rin)/(1+dot) along (n1+n2), tangent radius rin."""
    denom = 1.0 + dot
    if denom <= 1e-6:
        return []
    cxr = vx + (n1x+n2x)*(inset+rin)/denom
    cyr = vy + (n1y+n2y)*(inset+rin)/denom
    bx, by = unit(n1x+n2x, n1y+n2y)
    return [(cxr - n1x*rin, cyr - n1y*rin),
            (cxr - bx*rin, cyr - by*rin),
            (cxr - n2x*rin, cyr - n2y*rin)]


def gen_hybrid(seed=1, npts=10, box=240.0, disp=0.4, minr=8.0, step=6.0,
               passes=8):
    """Hull flow plus one serpentine comb: the displaced hull loop's longest
    edge is replaced by 2-3 outward fingers (half-width 1.25*minr, spacing
    2.2*minr between finger walls, sampled semicircle tips, three-point
    inner arcs at the bases). Deterministic per seed."""
    import random

    def hull(ps):
        ps = sorted(set(ps))
        def half(seq):
            h = []
            for q in seq:
                while len(h) >= 2 and ((h[-1][0]-h[-2][0])*(q[1]-h[-2][1])
                                       - (h[-1][1]-h[-2][1])*(q[0]-h[-2][0])) <= 0:
                    h.pop()
                h.append(q)
            return h
        lo, hi = half(ps), half(reversed(ps))
        return lo[:-1] + hi[:-1]

    fw = 1.25 * minr
    rin = 1.35 * minr
    # adjacent fingers' base arcs each consume rin of baseline, so the
    # wall-to-wall gap must clear 2*rin with margin
    gap = 3.2 * minr
    for attempt in range(96):
        rng = random.Random(seed * 1000 + attempt)
        pts = [(rng.uniform(0, box), rng.uniform(0, box)) for _ in range(npts)]
        h = hull(pts)
        if len(h) < 5:
            continue
        cx = sum(q[0] for q in h) / len(h)
        cy = sum(q[1] for q in h) / len(h)
        # graft the comb into the longest full hull edge (its midpoint stays
        # undisplaced -- displaced half-edges are too short for a comb);
        # every other edge gets the random inward midpoint displacement
        hn = len(h)
        eh = max(range(hn), key=lambda i: math.hypot(h[(i+1) % hn][0]-h[i][0],
                                                     h[(i+1) % hn][1]-h[i][1]))
        loop = []
        ei = -1
        for i in range(hn):
            a, b = h[i], h[(i+1) % hn]
            loop.append(a)
            if i == eh:
                ei = len(loop) - 1
                continue
            mx, my = (a[0]+b[0])/2.0, (a[1]+b[1])/2.0
            f = rng.uniform(0.0, disp)
            loop.append((mx + f*(cx-mx), my + f*(cy-my)))
        A, B = h[eh], h[(eh+1) % hn]
        ex, ey = B[0]-A[0], B[1]-A[1]
        elen = math.hypot(ex, ey)
        ux, uy = ex/elen, ey/elen
        # outward normal: away from the centroid
        nx, ny = -uy, ux
        mx, my = (A[0]+B[0])/2.0, (A[1]+B[1])/2.0
        if (mx-cx)*nx + (my-cy)*ny < 0:
            nx, ny = -nx, -ny
        end = rin + minr    # baseline the base arcs eat, plus margin
        nf = rng.choice((2, 3))
        span = nf*2*fw + (nf-1)*gap
        if span > elen - 2*end:
            nf = 2
            span = nf*2*fw + (nf-1)*gap
            if span > elen - 2*end:
                continue
        depth = rng.uniform(3.0, 5.0) * minr
        s0 = (elen - span) / 2.0
        comb = []
        for k in range(nf):
            sl = s0 + k*(2*fw+gap)
            sr = sl + 2*fw
            blx, bly = A[0]+ux*sl, A[1]+uy*sl        # base left
            brx, bry = A[0]+ux*sr, A[1]+uy*sr        # base right
            tcx, tcy = A[0]+ux*(sl+fw)+nx*depth, A[1]+uy*(sl+fw)+ny*depth
            # base corners are perpendicular; turn-side normals are (n,-u)
            # entering and (u,n) leaving, for either loop winding
            comb += _inner_arc(blx, bly, nx, ny, -ux, -uy, 0.0, 0.0, rin)
            comb.append((blx+nx*depth, bly+ny*depth))   # tangent to tip circle
            # sampled semicircle tip around (tcx,tcy), radius fw, from -u side to +u side
            a1 = math.atan2(-uy, -ux)
            for j in range(1, 8):
                th = a1 + math.pi * j / 8.0 * (1 if (ux*ny-uy*nx) < 0 else -1)
                comb.append((tcx + fw*math.cos(th), tcy + fw*math.sin(th)))
            comb.append((brx+nx*depth, bry+ny*depth))
            comb += _inner_arc(brx, bry, ux, uy, nx, ny, 0.0, 0.0, rin)
        loop = loop[:ei+1] + comb + loop[ei+1:]
        c = _finish_loop(loop, minr, step, passes)
        if c is not None:
            return c, True
    raise SystemExit(f"gen_hybrid: no valid loop after 96 attempts (seed {seed})")



def _corner_arc(vx, vy, d1x, d1y, d2x, d2y, rin):
    """Generic corner fillet at (vx,vy) from direction d1 to d2 (unit
    vectors): turn side from the cross sign, turn-side normals fed to the
    _inner_arc formula. Reproduces the hybrid base-corner pairs."""
    cross = d1x*d2y - d1y*d2x
    if cross > 0:
        m1x, m1y = -d1y, d1x
        m2x, m2y = -d2y, d2x
    else:
        m1x, m1y = d1y, -d1x
        m2x, m2y = d2y, -d2x
    return _inner_arc(vx, vy, m1x, m1y, m2x, m2y, m1x*m2x + m1y*m2y, 0.0, rin)


def _comb_fingers(ax, ay, ux, uy, nx, ny, positions, fw, depth, rin):
    """Finger emission shared by the hybrid and fractal combs: for each
    (sl, sr) span along the edge from (ax,ay), an outward finger with
    corner fillets and a sampled semicircle tip."""
    pts = []
    for sl, sr in positions:
        blx, bly = ax + ux*sl, ay + uy*sl
        brx, bry = ax + ux*sr, ay + uy*sr
        tcx, tcy = ax + ux*(sl+fw) + nx*depth, ay + uy*(sl+fw) + ny*depth
        pts += _corner_arc(blx, bly, ux, uy, nx, ny, rin)
        pts.append((blx + nx*depth, bly + ny*depth))
        a1 = math.atan2(-uy, -ux)
        step = 1 if (ux*ny - uy*nx) < 0 else -1
        for j in range(1, 8):
            th = a1 + math.pi * j / 8.0 * step
            pts.append((tcx + fw*math.cos(th), tcy + fw*math.sin(th)))
        pts.append((brx + nx*depth, bry + ny*depth))
        pts += _corner_arc(brx, bry, -nx, -ny, ux, uy, rin)
    return pts


def _fractal_control(rng, npts, box, disp, minr):
    """One attempt at the fractal control loop, or None if infeasible."""

    def hull(ps):
        ps = sorted(set(ps))
        def half(seq):
            h = []
            for q in seq:
                while len(h) >= 2 and ((h[-1][0]-h[-2][0])*(q[1]-h[-2][1])
                                       - (h[-1][1]-h[-2][1])*(q[0]-h[-2][0])) <= 0:
                    h.pop()
                h.append(q)
            return h
        lo, hi = half(ps), half(reversed(ps))
        return lo[:-1] + hi[:-1]

    fw_s = 1.25 * minr      # sub-finger half-width
    rin_s = 1.35 * minr     # sub base fillet
    rin = 1.35 * minr       # big-finger fillets
    sub_gap = 3.2 * minr    # wall-to-wall between sub-fingers
    sub_depth = 3.0 * minr
    big_depth = 6.5 * minr
    plain_fw = 1.25 * minr
    plain_gap = 3.2 * minr
    plain_end = rin_s + minr

    pts = [(rng.uniform(0, box), rng.uniform(0, box)) for _ in range(npts)]
    h = hull(pts)
    if len(h) < 5:
        return None
    hn = len(h)
    cx = sum(q[0] for q in h) / hn
    cy = sum(q[1] for q in h) / hn
    order = sorted(range(hn), key=lambda i: -math.hypot(h[(i+1) % hn][0]-h[i][0],
                                                        h[(i+1) % hn][1]-h[i][1]))
    e_big, e_plain = order[0], order[1]

    def edge_frame(ei):
        A, B = h[ei], h[(ei+1) % hn]
        ex, ey = B[0]-A[0], B[1]-A[1]
        elen = math.hypot(ex, ey)
        ux, uy = ex/elen, ey/elen
        nx, ny = -uy, ux
        mx, my = (A[0]+B[0])/2.0, (A[1]+B[1])/2.0
        if (mx-cx)*nx + (my-cy)*ny < 0:
            nx, ny = -nx, -ny
        return A, elen, ux, uy, nx, ny

    # the antlered finger: tip edge must fit the two-sub comb
    A, elen, ux, uy, nx, ny = edge_frame(e_big)
    sub_span = 2*(2*fw_s) + sub_gap
    FW = (sub_span + 2*(rin + rin_s + 0.25*minr)) / 2.0
    need = 2*FW + 2*(rin + minr)
    if elen < need:
        return None
    s0 = (elen - 2*FW) / 2.0
    blx, bly = A[0] + ux*s0, A[1] + uy*s0
    brx, bry = A[0] + ux*(s0 + 2*FW), A[1] + uy*(s0 + 2*FW)
    tlx, tly = blx + nx*big_depth, bly + ny*big_depth
    antler = []
    antler += _corner_arc(blx, bly, ux, uy, nx, ny, rin)
    antler += _corner_arc(tlx, tly, nx, ny, ux, uy, rin)
    tip0 = rin + rin_s + 0.25*minr
    sub_positions = [(tip0, tip0 + 2*fw_s),
                     (tip0 + 2*fw_s + sub_gap, tip0 + 4*fw_s + sub_gap)]
    antler += _comb_fingers(tlx, tly, ux, uy, nx, ny, sub_positions,
                            fw_s, sub_depth, rin_s)
    trx, try_ = brx + nx*big_depth, bry + ny*big_depth
    antler += _corner_arc(trx, try_, ux, uy, -nx, -ny, rin)
    antler += _corner_arc(brx, bry, -nx, -ny, ux, uy, rin)

    # optional plain two-finger comb on the second-longest edge
    A2, elen2, ux2, uy2, nx2, ny2 = edge_frame(e_plain)
    plain = None
    span2 = 2*(2*plain_fw) + plain_gap
    if elen2 >= span2 + 2*plain_end:
        p0 = (elen2 - span2) / 2.0
        plain_positions = [(p0, p0 + 2*plain_fw),
                           (p0 + 2*plain_fw + plain_gap, p0 + 4*plain_fw + plain_gap)]
        plain = _comb_fingers(A2[0], A2[1], ux2, uy2, nx2, ny2, plain_positions,
                              plain_fw, rng.uniform(3.0, 4.0) * minr, rin_s)

    loop = []
    for i in range(hn):
        a, b = h[i], h[(i+1) % hn]
        loop.append(a)
        if i == e_big:
            loop += antler
            continue
        if i == e_plain and plain is not None:
            loop += plain
            continue
        mx, my = (a[0]+b[0])/2.0, (a[1]+b[1])/2.0
        f = rng.uniform(0.0, disp)
        loop.append((mx + f*(cx-mx), my + f*(cy-my)))
    return loop


def gen_fractal(seed=1, npts=8, box=200.0, disp=0.35, minr=8.0, step=6.0,
                passes=8):
    """Serpentines at two scales: one big antlered finger (its tip sprouts
    two small serpentine fingers) on the longest hull edge, a plain
    two-finger comb on the second-longest when it fits. Deterministic per
    seed."""
    import random
    for attempt in range(160):
        rng = random.Random(seed * 1000 + attempt)
        loop = _fractal_control(rng, npts, box, disp, minr)
        if loop is None:
            continue
        c = _finish_loop(loop, minr, step, passes)
        if c is not None:
            return c, True
    raise SystemExit(f"gen_fractal: no valid loop after 160 attempts (seed {seed})")


GENERATORS = {
    'serpentine': gen_serpentine,
    'spiral': gen_spiral,
    'slalom': gen_slalom,
    'cog': gen_cog,
    'random': gen_random,
    'weave': gen_weave,
    'lobes': gen_lobes,
    'hybrid': gen_hybrid,
    'fractal': gen_fractal,
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
