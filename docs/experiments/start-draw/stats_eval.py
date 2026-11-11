"""Round 345 start-draw battery: two-sided chi-square verdicts on StartDraws.java's stats output.

python -I stats_eval.py <stats.txt> [alpha]

Each test row is a Pearson statistic with its df: car k's index against uniform, each pair of cars' index table
against independence (joint12 for cars 1 and 2, pairXY for the other 27 pairs), car 1's lag-one seed difference
against uniform. The repeat1 rows are no tests: the share of seeds whose car 1 index equals the previous seed's (fair
1/Z). Both tails are flagged: p < alpha (too uneven) and p > 1 - alpha (too even: a lattice, which a seeded LCG's
first outputs are). With 24 zone sizes there are 24 x 37 = 888 test rows per variant (8 marginals, 28 car pairs, one
lag). The 8 with df 0 (Z = 8: car 8, which has one cell left, and its 7 pairs) test nothing and are skipped, which
leaves 880 tests: nominally a fair draw flags 2 x alpha x 880 = 1.76. The p-values are only near uniform. A df-1 row
(Z = 8 car 7, Z = 9 car 8) is discrete: over an even number n of seeds an exact n/2 split gives chi2 = 0 and p = 1,
which a fair draw shows with probability C(n, n/2)/2^n (0.025 at n = 1000), not alpha."""
import collections
import sys

from scipy.stats import chi2

alpha = float(sys.argv[2]) if len(sys.argv) > 2 else 1e-3
rows = [line.split() for line in open(sys.argv[1])][1:]
by = collections.defaultdict(list)
rep = collections.defaultdict(list)
for v, z, test, df, stat, n in rows:
    if test == 'repeat1':
        rep[v].append((int(z), float(stat)))
        continue
    if int(df) == 0:  # Z = 8: car 8 has one cell left, so car8 and pair18..pair78 test nothing (chi2.sf gives nan)
        continue
    p = chi2.sf(float(stat), int(df))
    by[v].append((int(z), test, int(df), float(stat), p))

print('alpha %g two-sided; tests per variant %d' % (alpha, len(next(iter(by.values())))))
for v, tests in by.items():
    low = [t for t in tests if t[4] < alpha]
    high = [t for t in tests if t[4] > 1 - alpha]
    kinds = collections.Counter(t[1] if t[1].startswith(('joint', 'lag')) else 'pairs' if t[1].startswith('pair')
                                else 'car' + ('1' if t[1] == 'car1' else '2-8') for t in low + high)
    worst = min(tests, key=lambda t: min(t[4], 1 - t[4]))
    r = rep[v]
    excess = max(r, key=lambda zr: abs(zr[1] * zr[0] - 1))
    print('%-10s flagged %3d (uneven %3d, too even %3d)  by test %s  worst Z=%d %s chi2=%.1f df=%d p=%.3g  '
          'car-1 repeat of previous seed: worst Z=%d %.3f (fair %.3f)' % (
              v, len(low) + len(high), len(low), len(high), dict(sorted(kinds.items())), worst[0], worst[1],
              worst[3], worst[2], worst[4], excess[0], excess[1], 1 / excess[0]))
