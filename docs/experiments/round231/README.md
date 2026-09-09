# Round 231: choose the faster checkpoint crossing

The previous champion takes the first qualifying checkpoint touch in direction
order. Several legal touches can have different distances left to finish.
Rank those existing eligible touches by the exact remaining distance **after
all ordered gate events on the move**. Keep enum-order ties and the previous
choice if no eligible successor has a finite exact value.

This preserves the existing velocity, geometry, occupied-cell, continuing-map,
needle-headway and robust-landing checks. Immediate finishes, non-final S/F
precedence and the pure opponent predictor keep their existing rules. Both AI
labels run the resulting policy without an experimental switch.

## Head-to-head result

The baseline is master `18ef55eb22dad4c5a955b59cf65410e7d86b9e8e`, the
Round-228 surcharge-free champion. Master subsequently advanced to `f37ce13`
with an icon-dependency update; its racing engine, tests and fleet inputs are
unchanged, and that update is preserved in this branch. Each start mode covers
all 84 tracks and
fresh seeds 21–30, with candidate slots 1/3/5/7 and then 2/4/6/8. Each mode has
840 mirrored pairs, 1,680 races and 6,720 car-races per policy.

| Start placement | Candidate place | Champion place | Difference | Paired SE | Wins C / H | Crashes C / H |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| legacy | 3.829 | 5.171 | -1.343 | 0.047 | 1183 / 497 | 40 / 28 |
| informed | 3.829 | 5.171 | -1.343 | 0.048 | 1204 / 476 | 33 / 35 |
| scatter | 4.344 | 4.656 | -0.312 | 0.016 | 967 / 713 | 5 / 4 |

Lower finishing place is better. A crash already receives that car's recorded
last place. The comparison therefore includes crashes without a second safety
penalty. Own place is the primary criterion; summed field moves do not decide
promotion. This is a measured mean-place improvement, not a promise that every
car or track improves.

Tracks favoring candidate / champion / tied: legacy: 69 / 2 / 13; informed: 68 / 2 / 14; scatter: 64 / 2 / 18.
The paired standard errors describe the fixed track/seed corpus. They are not
a guarantee about unseen tracks, opponents or seeds. The 11 no-lap tracks are
included in the place comparison.

## Candidate-only fleet

Three additional complete grids contain 2,520 races. These descriptive totals
cover the 730 lap races per mode; `all-metrics.json` also retains the 110 no-lap
races per mode. There is no new champion-only grid in this round.

| Start placement | Finishers | Crashes | Timeouts | Field moves |
| --- | ---: | ---: | ---: | ---: |
| legacy | 5,072 | 38 | 0 | 1,782,051 |
| informed | 5,070 | 40 | 0 | 1,780,339 |
| scatter | 5,105 | 5 | 0 | 1,442,035 |

The mixed and candidate-only grids together contain 7,560 validated races.
The all-candidate grids run the exact production patch. The mixed patch differs
only by its candidate-slot activation guard. Each policy has the same runtime,
heap and inputs within a race. Nordschleife uses a disjoint 8 GiB single-worker
shard; the other 83 tracks use 4 GiB heaps and two workers. Every JVM uses
`-XX:ActiveProcessorCount=2`. No track, referee or fleet-tool changes are needed.

## Validation and recorded expectations

JDK 25 builds with warnings as errors. Core, all 23 AI regression scripts,
all 12 golden cases, headless smoke, query replay and lap-progress checks pass.
Sixteen AI scripts pass unchanged. Seven scripts have measured constant updates;
their function bodies and explicit safety/AI-label identity checks are unchanged.
The refreshed seven scripts were verified again in CI, with 67 complete race
recordings checked against local measurements. The production JAR hashes and
golden JSON agree between local and CI runs.

One recorded retention case changes its terminal counters: frozen Le Mans seed
87 has six finishers and p6 crashes on its 36th move, under both AI labels.
Its exact expected snapshot is now 6/1, with the reason beside the value. The
other measured regression cases retain seven finishers and no crashes. Seven
golden trajectories change; all twelve retain their finisher and crash counts.
The owner's rule in `AGENTS.md` makes this self-play crash descriptive, while
the mixed-field own-place result decides promotion.

## Screening and selection

Two screens used 24 tracks, legacy starts, seeds 11–13 and mirrored slots:

| Screen arm | Place difference C − H | Paired SE | Wins C / H | Crashes C / H |
| --- | ---: | ---: | ---: | ---: |
| Remove field pace vetoes | -0.00694 | 0.011 | 72 / 72 | 8 / 7 |
| Wider certified finish window | 0.00000 | 0.000 | 72 / 72 | 7 / 7 |
| Both initial changes | -0.00694 | 0.011 | 72 / 72 | 8 / 7 |
| Rank checkpoint touches | -0.53125 | 0.105 | 86 / 58 | 8 / 5 |
| Rank non-final lap crossings | +0.04167 | 0.020 | 70 / 74 | 8 / 7 |
| Both crossing changes | -0.56250 | 0.105 | 87 / 57 | 8 / 5 |

The initial ideas were essentially tied and were not promoted. Checkpoint
selection carries the gate-choice gain. Choose checkpoint only: the isolated
lap-crossing change loses and its incremental combined effect is small.
The full fleet uses fresh seeds and is the promotion measurement. Both screens'
864 races, source manifests, compact outcomes and native scorer reports are
preserved in `initial-screen/` and `gate-screen/`.

## Evidence and replay

- [Initial screen](https://github.com/senegrom/TheoreticalRacing/actions/runs/34320631936).
- [Gate-choice screen](https://github.com/senegrom/TheoreticalRacing/actions/runs/34321589460).
- [Full fleet and initial regression checks](https://github.com/senegrom/TheoreticalRacing/actions/runs/34322144366).
- [Refreshed regression verification](https://github.com/senegrom/TheoreticalRacing/actions/runs/34322910098).

The full run retains its initial failures against historical golden/pin values;
the separate verification run checks the measured expectations normally. Fleet
completion and regression verification are recorded separately in
`validation.json`; an old fixture mismatch is not disguised as a passing job.

`audit.py` requires every track, seed, complementary slot assignment, complete
terminal result, input manifest, log hash and recomputed counter before export.
The mixed/all outcome CSVs retain each car's place, own move count and terminal
status, plus raw and normalized log hashes. Vectors are ordered by player 1–8.
`unfinished` is the eighth car still racing when the other seven have retired.
Source JSON files retain the exact profiles, input hashes, Java version and
downloaded ZIP digests. Actions retain raw logs for 14 days; the compact evidence
and experiment commits remain in Git history.

To rebuild the mixed-field experiment:

```sh
git worktree add --detach ../round231-replay 319e2d9a589e44620ebb5e1ba1dccf7403bff01a
cd ../round231-replay
git apply docs/experiments/round231/checkpoint-candidate.patch
sh build_main.sh
```

That commit's `.github/workflows/racecraft-round231-full.yml` records every
profile, shard and fleet command. Commit `b897c6fce6b2409518f5965e9c525e34cff7c3ba`
preserves the production/fixture patches, capture helper and verification
workflow. Temporary workflows, the capture helper and production/fixture patch carriers
are removed from the final tree; their history remains available.

Extract all 18 fleet ZIPs into directories named after their artifacts, beside
the ZIPs, and audit them with this revision's track files and parser:

```sh
python docs/experiments/round231/audit.py /path/to/artifacts /tmp/round231-audit --phase mixed
python docs/experiments/round231/audit.py /path/to/artifacts /tmp/round231-audit --phase all
python docs/experiments/round231/screen_audit.py /path/to/artifacts /tmp/round231-screen gates
```

Use `initial` instead of `gates` for the first screen. The preserved
`head-to-head-*.txt` files also come directly from `tracks/head_to_head.py`
using each mode's odd/even regular and Nordschleife directories.
