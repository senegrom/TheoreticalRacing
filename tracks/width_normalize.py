#!/usr/bin/env python3
"""Normalize the six fat real-world tracks to constant corridor width.

Method: extract the centerline (midpoints of nearest-point pairs L->R),
resample at 1-cell steps, lightly smooth, curvature-adaptively decimate
(2.4-cell corners / 4.2-cell straights), offset both sides uniformly
(+-HALF), excise offset cusps, integer-snap, and validate everything
before writing. Layout, canvas, header and the S/F gap are preserved;
only the width changes. Asserts all, then writes once.
"""
import math, pathlib, re

TRACKS = pathlib.Path('E:/OneDrive/Coding/Java/theoreticRacing/tracks')
TARGETS = ['spielberg', 'nurburgring', 'monza', 'silverstone', 'spa', 'lemans']
HALF = 1.9           # -> corridor ~3.8, inside the user's <4 band; integer snap can pinch ~0.7, staying >=2.5
SEG_STRAIGHT = 4.2
SEG_CORNER = 2.4
SMOOTH_WIN = 5

def parse(t, side):
    m = re.search(side + r'=([0-9;,\s-]+)', t)
    return [tuple(map(int, p.split(','))) for p in m.group(1).strip().rstrip(';').split(';')]

def fmt(P):
    return ';'.join(f'{x},{y}' for x, y in P)

def seg_pt_foot(a, b, p):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    fx, fy = ax + t * dx, ay + t * dy
    return math.hypot(px - fx, py - fy), (fx, fy)

def nearest_on_poly_windowed(p, P, jc, win=12):
    """Nearest foot on P restricted to segments near index jc -- global
    nearest pairing collapses the midline where a wide section runs close
    to another pass (the nurburgring arena loop paired across the infield)."""
    lo = max(0, jc - win)
    hi = min(len(P) - 1, jc + win + 1)
    best = (1e18, None)
    for i in range(lo, hi):
        d, f = seg_pt_foot(P[i], P[i + 1], p)
        if d < best[0]:
            best = (d, f)
    return best[1]

def resample(P, step=1.0):
    out = [P[0]]
    acc = 0.0
    for i in range(1, len(P)):
        ax, ay = P[i - 1]; bx, by = P[i]
        L = math.dist(P[i - 1], P[i])
        if L == 0:
            continue
        d = acc
        while d + step <= L:
            d += step
            out.append((ax + (bx - ax) * d / L, ay + (by - ay) * d / L))
        acc = d - L
    out.append(P[-1])
    return out

def smooth(P, win):
    h = win // 2
    out = []
    for i in range(len(P)):
        lo, hi = max(0, i - h), min(len(P), i + h + 1)
        out.append((sum(p[0] for p in P[lo:hi]) / (hi - lo),
                    sum(p[1] for p in P[lo:hi]) / (hi - lo)))
    return out

def turn_at(S, i, span=4):
    a = S[max(0, i - span)]
    b = S[i]
    c = S[min(len(S) - 1, i + span)]
    h1 = math.atan2(b[1] - a[1], b[0] - a[0])
    h2 = math.atan2(c[1] - b[1], c[0] - b[0])
    d = abs(h2 - h1)
    return min(d, 2 * math.pi - d)

def decimate(S):
    out = [S[0]]
    acc = 0.0
    for i in range(1, len(S) - 1):
        acc += math.dist(S[i - 1], S[i])
        step = SEG_CORNER if turn_at(S, i) > 0.18 else SEG_STRAIGHT
        if acc >= step:
            out.append(S[i])
            acc = 0.0
    out.append(S[-1])
    return out

def offset(S, side):
    out = []
    n = len(S)
    for i in range(n):
        a = S[max(0, i - 1)]
        c = S[min(n - 1, i + 1)]
        nx, ny = c[1] - a[1], -(c[0] - a[0])
        ln = math.hypot(nx, ny) or 1.0
        out.append((S[i][0] + side * HALF * nx / ln, S[i][1] + side * HALF * ny / ln))
    return out

def segs_intersect(p1, p2, p3, p4):
    def o(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if v == 0 else (1 if v > 0 else -1)
    return (o(p1, p2, p3) != o(p1, p2, p4)) and (o(p3, p4, p1) != o(p3, p4, p2))

def cut_cusps(S, max_span=14):
    changed = True
    while changed:
        changed = False
        n = len(S)
        for i in range(n - 1):
            hit = None
            for j in range(i + 2, min(i + 2 + max_span, n - 1)):
                if segs_intersect(S[i], S[i + 1], S[j], S[j + 1]):
                    hit = j
                    break
            if hit is not None:
                S = S[:i + 1] + S[hit + 1:]
                changed = True
                break
    return S

def snap_clean(S):
    P = [(round(x), round(y)) for x, y in S]
    changed = True
    while changed:
        changed = False
        Q = []
        for p in P:
            if Q and p == Q[-1]:
                changed = True
                continue
            Q.append(p)
        R = []
        i = 0
        while i < len(Q):
            if len(R) >= 1 and i + 1 < len(Q) and Q[i + 1] == R[-1]:
                i += 2
                changed = True
                continue
            R.append(Q[i])
            i += 1
        P = R
    return P

def close_gap(P, target=6.0):
    """End smoothing migrates the endpoints inward and can grow the S/F
    gap; walk the tail end back toward the head along the gap direction."""
    while math.dist(P[0], P[-1]) > 8.0:
        d = math.dist(P[0], P[-1])
        step = min(4.0, d - target)
        if step < 1.5:
            break
        ux, uy = (P[0][0] - P[-1][0]) / d, (P[0][1] - P[-1][1]) / d
        P = P + [(round(P[-1][0] + ux * step), round(P[-1][1] + uy * step))]
    return P

def build_side(center, side):
    P = offset(center, side)
    for _ in range(6):
        P = snap_clean(cut_cusps(P))
    return close_gap(P)

def self_bad(P):
    n = len(P) - 1
    for i in range(n):
        for j in range(i + 2, n):
            if segs_intersect(P[i], P[i + 1], P[j], P[j + 1]):
                return (i, j)
    return None

def cross_bad(A, B):
    for i in range(len(A) - 1):
        for j in range(len(B) - 1):
            if segs_intersect(A[i], A[i + 1], B[j], B[j + 1]):
                return (i, j)
    return None

def poly_dist(p, P):
    return min(seg_pt_foot(P[i], P[i + 1], p)[0] for i in range(len(P) - 1))

outputs = {}
for name in TARGETS:
    f = TRACKS / f'{name}.track'
    t = f.read_text(encoding='utf-8', errors='replace')
    L0, R0 = parse(t, 'trackLeft'), parse(t, 'trackRight')
    gx = int(re.search(r'gameX=(\d+)', t).group(1))
    gy = int(re.search(r'gameY=(\d+)', t).group(1))
    mid = []
    for i, p in enumerate(L0):
        jc = round(i * (len(R0) - 1) / (len(L0) - 1))
        q = nearest_on_poly_windowed(p, R0, jc)
        mid.append(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2))
    center = decimate(smooth(resample(mid, 1.0), SMOOTH_WIN))
    L = build_side(center, -1)
    R = build_side(center, +1)
    for side, P in (('L', L), ('R', R)):
        assert len(P) >= 40, (name, side, len(P))
        for x, y in P:
            assert 2 <= x <= gx - 2 and 2 <= y <= gy - 2, (name, side, x, y)
        for i in range(len(P) - 1):
            assert math.dist(P[i], P[i + 1]) >= 1.0, (name, side, i, P[i])
        sb = self_bad(P)
        assert sb is None, (name, side, sb, P[sb[0]] if sb else None)
    assert cross_bad(L, R) is None, (name, 'cross')
    w = sorted(poly_dist(p, R) for p in L)
    assert w[0] >= 2.45, (name, 'narrow', w[0])  # user floor "about 2.5"; integer snap noise allowed
    assert w[-1] <= 5.0, (name, 'still fat', w[-1])
    gl, gr = math.dist(L[0], L[-1]), math.dist(R[0], R[-1])
    assert 2.0 <= gl <= 10.0 and 2.0 <= gr <= 10.0, (name, 'gap', gl, gr)
    t2 = re.sub(r'trackLeft=[0-9;,\s-]+\n', 'trackLeft=' + fmt(L) + '\n', t)
    t2 = re.sub(r'trackRight=[0-9;,\s-]+\n', 'trackRight=' + fmt(R) + '\n', t2)
    outputs[f] = (t2, len(L), len(R), w[0], w[len(w) // 2], w[-1], gl, gr)

for f, (t2, nl, nr, wmin, wmed, wmax, gl, gr) in outputs.items():
    f.write_text(t2, encoding='utf-8')
    print(f'{f.name}: nL={nl} nR={nr} width {wmin:.2f}/{wmed:.2f}/{wmax:.2f} gaps {gl:.1f}/{gr:.1f}')
