# Round 228: race narrow lanes at their actual distance

The champion adds one virtual turn to a narrow-lane state when a rival is
nearby. That discourages contesting fast lines even when the existing traffic
checks allow them. Remove this surcharge from both the mover's distance and
the distances used by rollout models. Keep collision, headway, seal, rollout,
and robust checkpoint/crossing checks. Every AI label runs the resulting policy.

## Head-to-head result

Against master `649776467534e9dcdb6e924fd4281e37ff81c5d7`, the candidate improves
mean finishing place in all three start modes. Each mode covers all 84 tracks,
seeds 1–10, twice: candidate slots 1/3/5/7 and then 2/4/6/8. That is 840 mirrored
pairs, 1,680 races, and 6,720 car-races per policy per mode. Grid advantage is
cancelled by the complementary assignments. The 11 tracks without lap gates
still produce complete races and are included in the place comparison.

| Start placement | Candidate place | Champion place | Difference | Paired SE | Wins C / H | Crashes C / H |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| legacy | 3.930 | 5.070 | -1.140 | 0.040 | 1066 / 614 | 17 / 4 |
| informed | 3.924 | 5.076 | -1.151 | 0.039 | 1079 / 601 | 9 / 4 |
| scatter | 4.455 | 4.545 | -0.090 | 0.007 | 871 / 809 | 2 / 0 |

Lower place is better. Crashes already receive the car's recorded last place;
the extra candidate crashes are included above. The candidate wins the primary
place comparison despite them. Whole-field move totals and crashes are
descriptive, under the owner's racecraft rule in `AGENTS.md`.

Tracks favoring candidate / champion / tied: legacy 70 / 3 / 11, informed
69 / 4 / 11, scatter 61 / 5 / 18. The reported standard error is the repository
scorer's descriptive standard error over these fixed track/seed pairs, not a
claim about every possible track, seed, or human opponent. Seeds 1–3 on ten
real circuits were also used for the preliminary screen; the larger fleet is
the promotion measurement, not a wholly independent holdout.

The existing `tracks/head_to_head.py` produces the three preserved text reports.
`audit.py` independently requires exact complementary pairs, all 840 cases in
each assignment, completed terminal results, track/profile/parser hashes,
manifest identities, raw-log hashes and recomputed counters before exporting
the measurements. It does not silently score partial grids.

## Candidate-only fleet

The additional three complete grids contain 2,520 races, including 730 lap
races per mode. The following descriptive totals cover those lap races, as
`fleet_grid.sh` reports them; `all-metrics.json` also includes the 110 no-lap
races per mode. There is no separate champion-only comparison in this round.

| Start placement | Finishers | Crashes | Timeouts | Field moves |
| --- | ---: | ---: | ---: | ---: |
| informed | 5073 | 37 | 0 | 1,806,934 |
| legacy | 5081 | 29 | 0 | 1,810,581 |
| scatter | 5105 | 5 | 0 | 1,461,772 |

Together the mixed and candidate-only grids contain 7,560 validated races.

## Validation and changed pins

JDK 25 builds with warnings as errors and the core suite pass. All 23
`tests/ai1_*_regression.py` scripts and all 12 golden cases pass the production
candidate. Eight regression scripts needed measured move/order/hash updates;
their safety assertions and AI1/AI2 trajectory-identity checks remain intact.
The golden runner was used once to measure and then again in ordinary check
mode. Local and GitHub golden JSON match exactly. Nurburgring seed 19 changes
from six finishers and one crash to seven finishers and no crash.

The gated experimental build with `candidateSlots` unset also passed core and
the original twelve goldens, confirming the champion control. The final source
is the production patch used by the passing regression runs: raw distance for
all AI cars. The existing candidate-slot instrument remains available for
future experiments; no experimental switch is needed to obtain the improvement.

Recorded runs:

- [Full grids](https://github.com/senegrom/TheoreticalRacing/actions/runs/34268684443): each 4 GiB cell has 83 complete tracks; only Nordschleife fails its memory-reserve guard on a later seed.
- [Nordschleife](https://github.com/senegrom/TheoreticalRacing/actions/runs/34270749090): all nine cells succeed at 8 GiB with one worker.
- [Initial regression measurements](https://github.com/senegrom/TheoreticalRacing/actions/runs/34269106700): core and 15 unchanged pins pass; eight historical expectations fail and are captured; twelve new goldens are measured.
- [Refreshed regression verification](https://github.com/senegrom/TheoreticalRacing/actions/runs/34271580481): all eight refreshed scripts and ordinary golden checking pass.

The first grid's nonzero status is retained. Its failed Nordschleife attempt is
excluded entirely; only the complete, disjoint 8 GiB shard supplies that track.
The heap guard and track tooling were not changed. Each pair of policies has
the same heap and runtime for a given track. The other 83 tracks use two workers
and 4 GiB heaps; all JVMs use `-XX:ActiveProcessorCount=2`. The manifests retain
the exact Java executable hash, JAR hash, profiles, track hashes and heap flags.

## Preserved evidence and replay

`mixed-outcomes.csv.gz` and `all-outcomes.csv.gz` preserve every accepted race's
eight finishing places, own move counts, terminal statuses, raw-log hash and
normalized trajectory hash. Pipe-separated vectors are ordered by player
number 1–8. `unfinished` is the car still racing when the seven other cars
have retired; its place is still scored. The source JSON files associate each
grid with its complete input manifest, accepted track list and ZIP hash.
`validation.json` links the job outcomes and artifact IDs/hashes. The raw logs
and observational regression captures are downloadable from the runs above
while their seven-day Actions retention lasts. The compact evidence here and
the exact experiment commits remain in Git history after that retention ends.

The experiment patches apply to the recorded base, not on top of the final
production source. To rebuild the mixed-field experiment:

```sh
git worktree add --detach ../round228-replay 4294df4bb95ab459c2c681d6651a75dd5508065f
cd ../round228-replay
git apply docs/experiments/round228/candidate.patch
sh build_main.sh
```

That commit's `.github/workflows/racecraft-zero-validation.yml` records the
exact profiles and full-grid invocation. Commit
`3d9a20f5cbb16c1a3a0b6e82a0cc61fe0c459d65` adds the Nordschleife-only workflow;
`34cbe1626aadb116f9a2576abfc1a476078e3770` preserves the production and fixture
patches, regression capture helper and final verification workflow. Temporary
workflows and production/fixture patch carriers are removed from the final PR
tree; their content remains accessible at those commits.

To audit downloaded fleet artifacts, keep the ZIPs and extract each into a
sibling directory named after its artifact (`round228-legacy-odd`, etc.). With
all 18 fleet archives available, run from this revision:

```sh
python docs/experiments/round228/audit.py /path/to/artifacts /tmp/round228-audit --phase mixed
python docs/experiments/round228/audit.py /path/to/artifacts /tmp/round228-audit --phase all
python tracks/head_to_head.py /path/to/artifacts/round228-legacy-odd/fleet /path/to/artifacts/round228-legacy-even/fleet /path/to/artifacts/round228-nordschleife-legacy-odd/fleet /path/to/artifacts/round228-nordschleife-legacy-even/fleet
```

Use the analogous directory names for informed and scatter scoring. The audit
fails on a missing case, invalid result, changed input or unpaired assignment.
It requires the recorded track files and runner/parser versions; use this
revision when auditing after future campaign changes.
