"""Round 345 start-draw battery: what a fair seed-only draw gives on the fleet's zones, as acceptance bands.

python -I fair_bands.py <zones.txt> [replicates]

Any draw that reads only (seed, car, pool size) gives every track with the same zone size the same index sequence,
so the fleet-level window counts are clustered by zone size; the Monte Carlo shares one draw per zone size.
Prints, per field size, distinct grids of 840 units per 10-seed window, the Kish size, the held-out units that copy a
seeds 1-10 grid, and the per-car spread (mean distinct cells per car over 84 tracks x 4 windows)."""
import collections
import sys

import numpy as np

zones = collections.Counter()
for line in open(sys.argv[1]):
    zones[line.split()[0]] += 1
Zc = collections.Counter(zones.values())
R = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
rng = np.random.default_rng(344)
for n in (2, 4, 8):
    D = np.zeros(R)
    C = np.zeros(R)
    K = np.zeros(R)
    for Z, m in Zc.items():
        a = np.stack([rng.integers(0, Z - k, size=(R, 20)) for k in range(n)], axis=-1)
        code = np.zeros((R, 20), dtype=np.int64)
        for k in range(n):
            code = code * 64 + a[:, :, k]
        for r in range(R):
            u, cnt = np.unique(code[r, :10], return_counts=True)
            D[r] += m * len(u)
            K[r] += m * (cnt ** 2).sum()
            C[r] += m * np.isin(code[r, 10:], u).sum()
    kish = 840 * 840 / K
    print('n=%d: distinct %.1f sd %.1f (1%% %.0f); Kish %.1f sd %.1f (1%% %.1f); held-out copies %.1f sd %.1f (99%% %.0f)'
          % (n, D.mean(), D.std(), np.percentile(D, 1), kish.mean(), kish.std(), np.percentile(kish, 1),
             C.mean(), C.std(), np.percentile(C, 99)))
spread = np.zeros(R)
for r in range(R):
    tot = 0
    for Z, m in Zc.items():
        a = rng.integers(0, Z, size=(4, 10))
        tot += m * sum(len(set(row)) for row in a)
    spread[r] = tot / (84 * 4)
print('per-car spread: mean %.3f sd %.3f; 0.1%%-99.9%% band %.2f-%.2f' % (
    spread.mean(), spread.std(), np.percentile(spread, 0.1), np.percentile(spread, 99.9)))
print('a car constant over one 10-seed window: probability Z^-9 per (track, car, window), at most %.1e on the fleet'
      % (1 / 8 ** 9))
