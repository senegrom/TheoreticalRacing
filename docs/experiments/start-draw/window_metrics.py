"""Round 345 start-draw battery: the random-start draw's screen-window statistics on every fleet track.

python -I window_metrics.py <zones.txt> <dump.txt> [variants...]

For each variant of StartDraws.java and field size n in (8, 4, 2) over the screens' seed windows 1-10, 11-20,
21-30, 31-40 (a unit is one (track, seed); on random starts both halves of a mirrored pair share the grid, and a race
is a pure function of grid and policies, so one grid is one unit):
  distinct  distinct grids (ordered cell tuples) of 840 units, and the Kish size N^2/sum m^2
  copies    held-out units (11-20, 21-30, 31-40) whose grid already occurs in 1-10 on the same track
  const1    tracks on which car 1 takes one cell in every seed of the window (of 84)
  constany  (track, car) pairs constant over the window
  spread    mean distinct cells per car over a window, against a fair draw's Z(1-(1-1/Z)^10)
A fair draw (ordered sampling without replacement, every grid equally likely) is computed exactly, except its Kish
size, which is 840^2 over the expected sum of squared multiplicities."""
import collections
import math
import sys

zones = collections.OrderedDict()
for line in open(sys.argv[1]):
    t, x, y = line.split()
    zones.setdefault(t, []).append((int(x), int(y)))
want = sys.argv[3:] or ['master', 'discard1', 'splittable', 'mixseed', 'percar']

draws = collections.defaultdict(dict)
for line in open(sys.argv[2]):
    f = line.split()
    if f[0] in want:
        draws[f[0]][(int(f[1]), int(f[2]))] = [int(v) for v in f[3:]]

WINDOWS = [(1, 10), (11, 20), (21, 30), (31, 40)]
SIZES = (8, 4, 2)


def grid(variant, track, seed, n):
    free = list(zones[track])
    idx = draws[variant][(len(free), seed)]
    return tuple(free.pop(idx[k]) for k in range(n))


def fair_distinct(N, m):
    return N * (1 - (1 - 1 / N) ** m)


def fair_kish_terms(N, m):
    # E[sum of squared multiplicities] for m draws from N equally likely values: m + m(m-1)/N
    return m + m * (m - 1) / N


rows = []
for n in SIZES:
    fair = dict(distinct=[0.0] * 4, copies=[0.0] * 4, sumsq=[0.0] * 4, spread=[])
    for track, cells in zones.items():
        Z = len(cells)
        N = math.perm(Z, n)
        for w in range(4):
            fair['distinct'][w] += fair_distinct(N, 10)
            fair['sumsq'][w] += fair_kish_terms(N, 10)
            if w:  # expected held-out units equal to one of seeds 1-10's grids
                fair['copies'][w] += 10 * (fair_distinct(N, 10) / N)
        fair['spread'].append(Z * (1 - (1 - 1 / Z) ** 10))
    rows.append(('fair', n, [round(v, 1) for v in fair['distinct']],
                 [round(840 * 840 / v, 1) for v in fair['sumsq']], [round(v, 1) for v in fair['copies']],
                 [0.0] * 4, [0.0] * 4, sum(fair['spread']) / len(fair['spread'])))
    for v in want:
        distinct, kish, copies, const1, constany = [], [], [], [], []
        spread = []
        first = {}
        for w, (lo, hi) in enumerate(WINDOWS):
            d = 0
            sumsq = 0
            cp = 0
            c1 = 0
            ca = 0
            for track in zones:
                grids = [grid(v, track, s, n) for s in range(lo, hi + 1)]
                mult = collections.Counter(grids)
                d += len(mult)
                sumsq += sum(m * m for m in mult.values())
                if w == 0:
                    first[track] = set(grids)
                else:
                    cp += sum(1 for g in grids if g in first[track])
                for k in range(n):
                    cells = {g[k] for g in grids}
                    if len(cells) == 1:
                        ca += 1
                        if k == 0:
                            c1 += 1
                    spread.append(len(cells))
            distinct.append(d)
            kish.append(round(840 * 840 / sumsq, 1))
            copies.append(cp)
            const1.append(c1)
            constany.append(ca)
        rows.append((v, n, distinct, kish, copies, const1, constany, sum(spread) / len(spread)))

print('%-10s %2s  %-22s %-30s %-18s %-14s %-16s %s' % ('variant', 'n', 'distinct/840 by window', 'Kish by window',
                                                          'copies of 1-10', 'car1 const', 'any car const', 'spread'))
for v, n, d, k, c, c1, ca, sp in rows:
    print('%-10s %2d  %-22s %-30s %-18s %-14s %-16s %.2f' % (
        v, n, '/'.join(str(x) for x in d), '/'.join(str(x) for x in k), '/'.join(str(x) for x in c[1:]),
        '/'.join(str(int(x)) for x in c1), '/'.join(str(int(x)) for x in ca), sp))
