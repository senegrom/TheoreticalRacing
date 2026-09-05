#!/usr/bin/env python3
"""Build tracks/nordschleife.track from the stitched OSM loop.

The 20.75 km loop (52 OSM raceway sections, 0.4% off the real 20.832 km)
is projected at the largest scale the 500-cell grid cap allows
(~12.2 m/cell; the GP sibling is 4.85 -- same-scale would need ~1250
cells). Closed-ring resample/smooth/decimate, S/F cut mid-way along the
straightest stretch (Doettinger Hoehe finds itself), uniform +-1.9
offset (fleet width law <4, floor ~2.5), real clockwise driving
direction. Asserts everything, then writes once. The loop is read from
nordschleife_loop.json next to this script.
"""
import json, math, pathlib

HERE = pathlib.Path(__file__).resolve()
LOOP = HERE.with_name('nordschleife_loop.json')
OUT = HERE.with_name('nordschleife.track')
HALF = 1.9
SEG_STRAIGHT = 4.2
SEG_CORNER = 2.0
SMOOTH_WIN = 9  # at ~12 m/cell the hairpins (Karussell) need rounding to radius ~3 cells or the inner offset self-crosses
MARGIN = 4.0
GAP_HALF = 3.0


def resample_closed(P, step=1.0):
    out = []
    acc = 0.0
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        L = math.dist(a, b)
        if L == 0:
            continue
        d = acc
        if not out:
            out.append(a)
        while d + step <= L:
            d += step
            out.append((a[0] + (b[0] - a[0]) * d / L, a[1] + (b[1] - a[1]) * d / L))
        acc = d - L
    return out


def smooth_closed(P, win):
    h = win // 2
    n = len(P)
    return [(sum(P[(i + k) % n][0] for k in range(-h, h + 1)) / win,
             sum(P[(i + k) % n][1] for k in range(-h, h + 1)) / win) for i in range(n)]


def turn_at_closed(P, i, span=4):
    n = len(P)
    a, b, c = P[(i - span) % n], P[i], P[(i + span) % n]
    h1 = math.atan2(b[1] - a[1], b[0] - a[0])
    h2 = math.atan2(c[1] - b[1], c[0] - b[0])
    d = abs(h2 - h1)
    return min(d, 2 * math.pi - d)


def decimate_open(Src):
    out = [Src[0]]
    acc = 0.0
    for i in range(1, len(Src) - 1):
        acc += math.dist(Src[i - 1], Src[i])
        step = SEG_CORNER if turn_at_closed(Src, i, 4) > 0.18 else SEG_STRAIGHT
        if acc >= step:
            out.append(Src[i])
            acc = 0.0
    out.append(Src[-1])
    return out


def offset(Sq, side):
    out = []
    m = len(Sq)
    for i in range(m):
        a = Sq[max(0, i - 1)]
        c = Sq[min(m - 1, i + 1)]
        nx, ny = c[1] - a[1], -(c[0] - a[0])
        ln = math.hypot(nx, ny) or 1.0
        out.append((Sq[i][0] + side * HALF * nx / ln, Sq[i][1] + side * HALF * ny / ln))
    return out


def segs_intersect(p1, p2, p3, p4):
    def o(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if v == 0 else (1 if v > 0 else -1)
    return (o(p1, p2, p3) != o(p1, p2, p4)) and (o(p3, p4, p1) != o(p3, p4, p2))


def cut_cusps(Sq, max_span=14):
    changed = True
    while changed:
        changed = False
        m = len(Sq)
        for i in range(m - 1):
            hit = None
            for j in range(i + 2, min(i + 2 + max_span, m - 1)):
                if segs_intersect(Sq[i], Sq[i + 1], Sq[j], Sq[j + 1]):
                    hit = j
                    break
            if hit is not None:
                Sq = Sq[:i + 1] + Sq[hit + 1:]
                changed = True
                break
    return Sq


def snap_clean(Sq):
    P = [(round(x), round(y)) for x, y in Sq]
    changed = True
    while changed:
        changed = False
        Q = []
        for p in P:
            if Q and p == Q[-1]:
                changed = True
                continue
            Q.append(p)
        Rr = []
        i = 0
        while i < len(Q):
            if len(Rr) >= 1 and i + 1 < len(Q) and Q[i + 1] == Rr[-1]:
                i += 2
                changed = True
                continue
            Rr.append(Q[i])
            i += 1
        P = Rr
    return P


def build_side(c, side):
    # offset the DENSE line (decimating the centerline first re-sharpens
    # rounded hairpins and the offset inherits the kink); the walls, being
    # parallel offsets of one smooth curve, stay parallel through their own
    # adaptive decimation
    P = offset(c, side)
    for _ in range(6):
        P = snap_clean(cut_cusps(P))
    return snap_clean(decimate_open(P))


def self_bad(P):
    m = len(P) - 1
    for i in range(m):
        for j in range(i + 2, m):
            if segs_intersect(P[i], P[i + 1], P[j], P[j + 1]):
                return (i, j)
    return None


def seg_pt(a, b, p):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def main():
    loop = json.loads(LOOP.read_text(encoding='utf-8'))
    if loop[0] == loop[-1]:
        loop = loop[:-1]
    lat0 = math.radians(sum(p[1] for p in loop) / len(loop))
    R = 6371000
    mx = [math.radians(p[0]) * math.cos(lat0) * R for p in loop]
    my = [-math.radians(p[1]) * R for p in loop]   # screen y grows south
    x0, y0 = min(mx), min(my)
    span_x, span_y = max(mx) - x0, max(my) - y0
    scale = (500 - 2 * MARGIN) / max(span_x, span_y)
    GX = int(math.ceil(span_x * scale + 2 * MARGIN))
    GY = int(math.ceil(span_y * scale + 2 * MARGIN))
    ring = [((px - x0) * scale + MARGIN, (py - y0) * scale + MARGIN) for px, py in zip(mx, my)]

    # real driving is clockwise north-up = counter-clockwise in y-down screen
    # coords = positive shoelace; reverse if needed
    sho = sum(ring[i][0] * ring[(i + 1) % len(ring)][1]
              - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring)))
    if sho < 0:
        ring.reverse()

    dense = smooth_closed(resample_closed(ring, 1.0), SMOOTH_WIN)
    # targeted hairpin rounding: wherever local curvature stays too tight for
    # the +-1.9 offset, average that neighborhood again until every corner has
    # radius the inner wall can survive
    for _ in range(80):
        nn = len(dense)
        # chord-heading delta ~ span/R: fires for radius < ~5.5 cells, giving the
        # +-1.9 offset comfortable margin (scale-forced: real 15 m hairpins
        # become ~60 m bends at 12.3 m/cell)
        hot = [i for i in range(nn) if turn_at_closed(dense, i, 3) > 0.42]
        if not hot:
            break
        marked = set()
        for i in hot:
            for k in range(-6, 7):
                marked.add((i + k) % nn)
        dense = [((sum(dense[(i + k) % nn][0] for k in range(-5, 6)) / 11,
                   sum(dense[(i + k) % nn][1] for k in range(-5, 6)) / 11)
                  if i in marked else dense[i]) for i in range(nn)]
    else:
        raise AssertionError('hairpin rounding did not converge')

    # S/F: center of the longest low-curvature stretch (Doettinger Hoehe)
    n = len(dense)
    flat = [turn_at_closed(dense, i, 8) < 0.03 for i in range(n)]
    best_len, best_start, cur = 0, 0, None
    for i in range(2 * n):
        if flat[i % n]:
            if cur is None:
                cur = i
            if i - cur + 1 > best_len:
                best_len, best_start = i - cur + 1, cur
        else:
            cur = None
        if cur is not None and i - cur + 1 >= n:
            break
    sf = (best_start + best_len // 2) % n
    print(f'straightest stretch: {best_len} cells; S/F at dense index {sf}')

    # rotate so the ring starts just after the S/F cut, then decimate OPEN
    rot = dense[sf:] + dense[:sf]
    gap_cells = int(round(2 * GAP_HALF))
    open_line = rot[gap_cells // 2: n - (gap_cells - gap_cells // 2)]

    print(f'dense centerline: {len(open_line)} cells, canvas {GX}x{GY}, ~{1/scale:.1f} m/cell')

    L = build_side(open_line, -1)
    Rt = build_side(open_line, +1)
    print(f'walls: nL={len(L)} nR={len(Rt)}')

    for side, P in (('L', L), ('R', Rt)):
        assert len(P) >= 200, (side, len(P))
        for x, y in P:
            assert 2 <= x <= GX - 2 and 2 <= y <= GY - 2, (side, x, y)
        for i in range(len(P) - 1):
            assert math.dist(P[i], P[i + 1]) >= 1.0, (side, i, P[i])
        sb = self_bad(P)
        assert sb is None, (side, sb, P[sb[0]] if sb else None)
    for i in range(len(L) - 1):
        for j in range(len(Rt) - 1):
            assert not segs_intersect(L[i], L[i + 1], Rt[j], Rt[j + 1]), ('cross', i, j, L[i])
    w = sorted(min(seg_pt(Rt[i], Rt[i + 1], p) for i in range(len(Rt) - 1)) for p in L)
    assert w[0] >= 2.45, ('narrow', w[0])
    assert w[-1] <= 6.0, ('fat', w[-1])  # single snapped-diagonal outliers allowed; the median carries the <4 rule
    assert w[len(w) // 2] < 4.0, ('median fat', w[len(w) // 2])
    gl, gr = math.dist(L[0], L[-1]), math.dist(Rt[0], Rt[-1])
    assert 2.0 <= gl <= 10.0 and 2.0 <= gr <= 10.0, ('gap', gl, gr)

    txt = ('# Theoretical Racing track file\n'
           '# Nuerburgring Nordschleife -- stitched from 52 OSM raceway sections\n'
           '# (20.75 km vs real 20.832 km). Largest scale the 500-cell grid\n'
           '# allows (~12.2 m/cell; the GP-Strecke sibling is ~4.9 m/cell).\n'
           'name=Nordschleife\n'
           f'gameX={GX}\n'
           f'gameY={GY}\n'
           'lapClosable=true\n'
           'trackLeft=' + ';'.join(f'{x},{y}' for x, y in L) + '\n'
           'trackRight=' + ';'.join(f'{x},{y}' for x, y in Rt) + '\n')
    OUT.write_text(txt, encoding='utf-8')
    print(f'wrote {OUT}: nL={len(L)} nR={len(Rt)} width {w[0]:.2f}/{w[len(w)//2]:.2f}/{w[-1]:.2f} gaps {gl:.1f}/{gr:.1f}')


if __name__ == '__main__':
    main()
