#!/usr/bin/env python3
"""Hand-authored Circuit de la Sarthe for theoreticRacing.

The OSM trace was missing ~40% of the lap (public-road sections) and the
Chaikin rediscretisation smoothed the rest into a featureless triangle.
This builder authors the centerline from the circuit's documented corner
sequence -- S/F, Dunlop curve + chicane, esses, Tertre Rouge, Mulsanne
straight with its two chicanes, Mulsanne corner, Indianapolis, Arnage,
Porsche Curves, Maison Blanche, Ford chicanes -- as Catmull-Rom control
points (the spline passes THROUGH every point, so chicanes survive),
samples it densely, decimates adaptively (dense in corners, coarse on
straights), offsets both borders, and validates everything before
writing. Asserts all checks, then writes once.
"""
import math, pathlib

W, H = 196, 375
HALF = 2.75          # half corridor width (~5.5 wide)
GAP = 6.0            # S/F gap target per side
SEG_STRAIGHT = 4.2   # decimation step on straights
SEG_CORNER = 2.4     # decimation step in corners

# Racing order, starting at the S/F heading north (lapFwd = departure of
# the first segments). Screen coords: x east, y south.
WP = [
    (26, 58),                                  # S/F line
    (27, 44), (30, 30),                        # pit straight north
    (35, 17), (45, 10),                        # Dunlop curve (right, over the hill)
    (54, 12), (58, 19),                        # Dunlop chicane
    (54, 28), (62, 40), (62, 49),              # Esses de la Foret (two clear sweeps)
    (69, 56),                                  # Tertre Rouge -> onto the straight
    (102, 128),                                # Hunaudieres chord 1
    (96, 137), (104, 146), (107, 153),         # Mulsanne chicane 1
    (141, 208),                                # chord 2
    (135, 217), (143, 226), (146, 233),        # Mulsanne chicane 2
    (178, 292),                                # chord 3 -> corner approach
    (183, 301), (186, 307), (183, 312), (176, 313), (169, 315),  # Virage de Mulsanne (near-hairpin right)
    (150, 322), (126, 331),                    # run toward Indianapolis
    (104, 341), (96, 347), (88, 344), (80, 349),     # Indianapolis (pronounced right-left)
    (70, 351), (63, 346), (60, 336),           # Arnage (slow right, turns north)
    (53, 312), (48, 290),                      # climb NNW
    (42, 274), (27, 260), (21, 244), (33, 230), (25, 214),  # Porsche Curves (sweeping esses)
    (23, 198), (28, 183), (23, 168),           # Maison Blanche
    (21, 146), (21, 120),                      # run to Ford
    (26, 104), (18, 95), (26, 86), (19, 77),   # Ford chicanes (double right-left)
    (23, 67),                                  # final approach to the line
]

def catmull(P, samples_per=40):
    """Closed-loop Catmull-Rom, densely sampled."""
    n = len(P)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        for s in range(samples_per):
            t = s / samples_per
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    return out

def turn_at(S, i, span=5):
    a, b, c = S[(i - span) % len(S)], S[i], S[(i + span) % len(S)]
    h1 = math.atan2(b[1] - a[1], b[0] - a[0])
    h2 = math.atan2(c[1] - b[1], c[0] - b[0])
    d = abs(h2 - h1)
    return min(d, 2 * math.pi - d)

def decimate(S):
    """Adaptive arc-length decimation of the closed sample loop."""
    out = [S[0]]
    acc = 0.0
    for i in range(1, len(S)):
        acc += math.dist(S[i - 1], S[i])
        step = SEG_CORNER if turn_at(S, i) > 0.18 else SEG_STRAIGHT
        if acc >= step:
            out.append(S[i])
            acc = 0.0
    return out

def offset(S, side):
    """Offset the closed centerline by HALF using averaged normals."""
    n = len(S)
    out = []
    for i in range(n):
        a, b, c = S[(i - 1) % n], S[i], S[(i + 1) % n]
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        nx, ny = v1[1] + v2[1], -(v1[0] + v2[0])
        ln = math.hypot(nx, ny) or 1.0
        out.append((b[0] + side * HALF * nx / ln, b[1] + side * HALF * ny / ln))
    return out

def cut_cusps(S, max_span=14):
    """Excise small self-intersection loops (offset cusps at tight corners).
    Only local loops are cut; a genuine large crossing still reaches the
    validator and fails the build."""
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
    """Integer snap, dedupe, unfold A-B-A spikes to fixpoint."""
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
        if len(Q) > 2 and Q[0] == Q[-1]:
            Q.pop()
            changed = True
        R = []
        i = 0
        while i < len(Q):
            if len(R) >= 1 and i + 1 < len(Q) and Q[i + 1] == R[-1]:
                i += 2  # A-B-A: drop B and the repeat of A
                changed = True
                continue
            R.append(Q[i])
            i += 1
        P = R
    return P

def cut_gap(P, gap):
    """Open the closed ring at the S/F: drop trailing points within gap of P[0]."""
    while len(P) > 3 and math.dist(P[0], P[-1]) < gap:
        P.pop()
    return P

def seg_pt_dist(a, b, p):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

def poly_dist(p, P):
    return min(seg_pt_dist(P[i], P[i + 1], p) for i in range(len(P) - 1))

def segs_intersect(p1, p2, p3, p4):
    def o(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if v == 0 else (1 if v > 0 else -1)
    o1, o2, o3, o4 = o(p1, p2, p3), o(p1, p2, p4), o(p3, p4, p1), o(p3, p4, p2)
    return o1 != o2 and o3 != o4

def self_intersects(P):
    n = len(P) - 1
    for i in range(n):
        for j in range(i + 2, n):
            if segs_intersect(P[i], P[i + 1], P[j], P[j + 1]):
                return (i, j)
    return None

def cross_intersects(A, B):
    for i in range(len(A) - 1):
        for j in range(len(B) - 1):
            if segs_intersect(A[i], A[i + 1], B[j], B[j + 1]):
                return (i, j)
    return None

def build_side(center, side):
    P = offset(center, side)
    for _ in range(6):  # cusp-cut and snap can each re-expose the other; fixpoint
        P = snap_clean(cut_cusps(P))
    return cut_gap(P, GAP)

center = decimate(catmull(WP))
left = build_side(center, -1)
right = build_side(center, +1)

# --- validate everything, then write once ---
for name, P in (('left', left), ('right', right)):
    assert len(P) >= 60, (name, len(P))
    for x, y in P:
        assert 2 <= x <= W - 2 and 2 <= y <= H - 2, (name, x, y)
    for i in range(len(P) - 1):
        assert 1.0 <= math.dist(P[i], P[i + 1]) <= 8.0, (name, i, P[i], P[i + 1])
    si = self_intersects(P)
    assert si is None, (name, 'self-intersect', si, P[si[0]] if si else None)
ci = cross_intersects(left, right)
assert ci is None, ('cross-intersect', ci)
wmins = []
for p in left:
    wmins.append(poly_dist(p, right))
for p in right:
    wmins.append(poly_dist(p, left))
wmin = min(wmins)
assert wmin >= 2.5, ('corridor too narrow', wmin)
gl, gr = math.dist(left[0], left[-1]), math.dist(right[0], right[-1])
assert 3.0 <= gl <= 10.0 and 3.0 <= gr <= 10.0, ('gap', gl, gr)

out = pathlib.Path('E:/OneDrive/Coding/Java/theoreticRacing/tracks/lemans.track')
txt = ('# Theoretical Racing track file\n'
       '# Hand-authored Circuit de la Sarthe (corner-sequence faithful)\n'
       'name=Le Mans\n'
       f'gameX={W}\n'
       f'gameY={H}\n'
       'lapClosable=true\n'
       'trackLeft=' + ';'.join(f'{x},{y}' for x, y in left) + '\n'
       'trackRight=' + ';'.join(f'{x},{y}' for x, y in right) + '\n')
out.write_text(txt, encoding='utf-8')
med = sorted(wmins)[len(wmins) // 2]
print(f'wrote {out}: nL={len(left)} nR={len(right)} corridor min={wmin:.2f} med={med:.2f} gapL={gl:.1f} gapR={gr:.1f}')
