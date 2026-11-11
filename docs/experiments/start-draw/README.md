# Start-draw battery (round 345)

On random starts (`aiStartPlacement=legacy`, the headless default) the AI car in
roster slot k takes a cell from its free list: the start zone's cells in x-then-y
order, minus the cells of cars 1..k-1. With a seed, the index into that list is
the seed's draw. A field's grid is therefore a pure function of the zone's cell
list, the seed and the number of cars, so any draw can be tested offline on every
fleet track, without racing.

Until round 345 the cars read one `new java.util.Random(seed)` in turn
(`master` below). For a power-of-two bound, its first output keeps the top bits
of one LCG step, and small seeds barely move those bits. In every seed 1-255,
car 1 took the same cell of every 8- or 16-cell zone. That is 8 fleet tracks:
interlagos and zandvoort (8 cells), and hybrid1, hybrid6, hybrid12, hybrid14,
hybrid15 and lobe2 (16 cells). Since round 345 each car takes its own output of
the seed's SplitMix64 stream, the draw that computed starts use to break ties
(`StartPlacement.draw`, round 344; `percar` below). Scattered starts keep their
own stream and are not part of this battery.

## Files

- `zones.txt`: every fleet track's start-zone cells, in x-then-y order
  (`track x y`, one cell per line; 84 tracks).
- `StartDraws.java`: the draws as index sequences.
  - `dump` writes the raw indices for 8 cars.
  - `stats` writes chi-square statistics: each car's index against uniform,
    every pair of cars against independence, and car 1's lag-one difference
    from seed to seed.
  - The variants: `master`; `discard1` (master with its first output thrown
    away, a negative control); `splittable` (`new SplittableRandom(seed)`);
    `mixseed` (`Random` seeded through SplitMix64); and `percar` (the
    round-345 draw).
- `window_metrics.py`: statistics over the screens' 10-seed windows 1-10,
  11-20, 21-30 and 31-40. Per variant and field size it prints one mean,
  `spread`: the distinct cells a car takes over a window's 10 seeds,
  averaged over the four windows, the 84 tracks and the n cars (a fair
  draw: 7.81). For each window it counts:
  - distinct grids of 840 units;
  - held-out grids that copy one from seeds 1-10;
  - tracks on which car 1 takes one cell in every seed, and (track, car)
    pairs on which any car does.
- `fair_bands.py`: the same counts for a fair draw, as acceptance bands.
  Needs numpy.
- `stats_eval.py`: two-sided chi-square verdicts at alpha = 1e-3. A lattice
  reads too even, a bias too uneven; by chance, an exact tie in a two-cell
  (df 1) row also reads too even. Needs scipy.

```
Z=8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,24,25,26,27,28,30,33,42,48   # the 24 zone sizes in zones.txt
java StartDraws.java dump dump.txt 1 40 $Z
python -I window_metrics.py zones.txt dump.txt
python -I fair_bands.py zones.txt
java StartDraws.java stats stats.txt 1 100000 $Z
python -I stats_eval.py stats.txt
```

The other `stats_eval` files in `results/` are the same two commands over seeds
`1 1000`, `-1000 0` and `1 1000000`; the last was run with a sixth argument,
`splittable,mixseed,percar` (the variants to run; all five without it).

## Results (`results/`)

| Check | master | percar | A fair draw |
|---|---|---|---|
| Tracks with car 1 on one cell in every seed of a 10-seed window (8 / 4 / 2 cars) | 8 / 8 / 8 | 0 / 0 / 0 | about 0 (Z^-9 per track, car and window) |
| Distinct duel grids per window, of 840 | 814 / 814 / 807 / 814 | 824 / 832 / 826 / 839 | 825.1, sd 7.9 |
| Held-out duel grids copying one from seeds 1-10 | 50 / 33 / 33 | 43 / 42 / 23 | 32.8, sd 12.0 |
| Distinct 8- and 4-car grids per window, of 840 | 840 | 840 | 840 (4 cars: 839.8) |
| Chi-square tests flagged of 880, seeds 1-1000 / 1-100,000 / -1000..0 | 673 / 817 / 663 | 1 / 0 / 1 | about 1.8 |
| Car 1 repeating the previous seed's cell, worst zone (seeds 1-1000) | 0.991 (16 cells; fair 0.062) | 0.054 (25 cells; fair 0.040) | 1/Z |

`discard1` fails as `master` does (652-823 flags). `splittable`, `mixseed` and
`percar` all pass: 0-5 flags. `percar`'s one flag over seeds 1-1000 is an exact
tie, not a lattice: car 7 of an 8-cell zone has two cells and takes each in
exactly 500 seeds (chi2 = 0, p = 1), which a fair draw does with probability
C(1000, 500)/2^1000 = 0.025; over seeds 1-100,000 the same row reads chi2 =
0.76. Over seeds 1 to 1,000,000, `percar` flags 1 test of 880.
