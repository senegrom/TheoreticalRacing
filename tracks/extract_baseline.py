"""Extract one column of a two-column bench log into a BENCH_BASELINE cache,
so later candidate benches only race their own column (~2x faster).

Usage: extract_baseline.py <bench.log> <out.json> [col]
  col 2 (default) = the AI2 (champion) column; col 1 = the AI1 column (use
  when the candidate itself is the new champion, e.g. seeding caches on
  promotion).

Caution: per-track mv is stored at one printed decimal, so a later
bench-vs-cache TOTAL line can differ by ~0.01 from a live-vs-live run even
when every per-track row is identical (known rounding artifact).
"""
import json
import re
import sys

ROW = re.compile(
    r'^(\S+)\s+\|\s+(\d+)/(\d+) mv=\s*([\d.]+)\s+\|\s+(\d+)/(\d+) mv=\s*([\d.]+)')


def main():
    col = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    rows = {}
    for line in open(sys.argv[1], encoding='utf-8', errors='replace'):
        m = ROW.match(line)
        if not m or m.group(1) == 'TOTAL':
            continue
        track, f1, c1, mv1, f2, c2, mv2 = m.groups()
        rows[track] = [int(f1), int(c1), float(mv1)] if col == 1 else [int(f2), int(c2), float(mv2)]

    assert rows, 'no rows parsed'
    with open(sys.argv[2], 'w') as f:
        json.dump(rows, f)
    print('wrote %d tracks -> %s' % (len(rows), sys.argv[2]))


if __name__ == '__main__':
    main()
