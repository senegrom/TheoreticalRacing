# Quiet-rule baseline and research isolation (2026-09-21)

This is a correction to the research branch's stale expected traces, **not a
rollback of the 20-cell rule and not a promotion of contingent search**.
The owner-defined distance is unchanged. Master is not updated by this work.

## Why the existing run was red

The published research branch at `f53c0df` already contains the quiet-mode fix.
Its JDK 25/26 contracts pass, but its corpus still describes the old policy which
could prioritize a checkpoint over exact solo descent outside 20 cells.
Run 35613608288 retained five new golden hashes and two changed champion hashes.
Every golden's turns, finishes, crashes and classification stayed unchanged.
Both failed champion scripts reached a trajectory assertion after their
finisher, crash and per-player-move assertions passed. The complete local probe
also found a later Monza-s145 hash mismatch masked by the Interlagos assertion;
all its outcome assertions remain unchanged. This is not permission to
ignore future differences: the entire trajectory is still pinned.

`tests/fixtures/quiet-baseline-refresh.json` preserves all eight old/new hashes,
the previous CI run, unchanged golden summaries and the independent-reference
recipe. Reasons are beside the changed expectations. No numeric outcome,
comparison assertion, fixture geometry or production source is changed here.

## Independent causal control

The control is NOT an experiment-off copy of the full research branch. It is
master `3466471efcb0cba8940b155e00a606b64c91b1ac`, with ONLY
`tests/fixtures/quiet-rule-reference.patch` applied to `RaceAi.java`.
That small patch moves exact solo selection before traffic/checkpoint precedence
at the owner-defined distance and includes the point-to-point equivalent. It
contains none of the chooser laboratory, contingent replies, prefix snapshots,
model code, audit hooks or experimental flags.

On a supported JDK, in a separate checkout of that exact master commit:

```sh
git apply --unidiff-zero /path/to/research/tests/fixtures/quiet-rule-reference.patch
sh build_main.sh
```

Then, in the research checkout:

```sh
sh build_main.sh
python tests/quiet_baseline_regression.py \
  --reference-jar /path/to/quiet-only/theoreticRacing.jar \
  --heap=-Xmx8g --out results/quiet-attribution
```

The comparator executes all twelve golden cases plus Rand3 and EVERY case of
the affected private-slack script under BOTH AI labels: 34 matched cases, 68
complete races. It installs exactly the script's seven frozen course fixtures. It requires identical complete move/result lines, not merely identical
classification or crash totals. The reference uses exactly the same supplied
geometry and profiles. Any mismatch, incomplete race, changed input or missing
log fails the comparison. Logs, profiles, hashes and a pending/completion marker
are retained; the comparator never rewrites a fixture.

The small unit suite explicitly rejects an action difference with equal race
results, a missing action, and a classification change. It permits only
non-behavioral header differences. This makes the attribution check independent
of the golden digest refresh.

## Validation boundary

The source-specific clearance run requires supported-JDK correctness, the
independent comparison, every golden and champion script, native prefix/full
plan identity, and the existing teacher/league laboratory. A sharded full fleet
runs all 84 bundled courses, seeds 1-10, with eight AI cars under each of legacy,
informed and scattered starts. The fleet uses explicit heaps, isolated caches,
unchanged tracks, generated disposable profiles, and validated completion markers.
Its counters describe the corrected default policy; it does NOT measure the
incremental gain of `contingent` or `prefix`, and is not a head-to-head promotion.

The extended corpus check may have a separate source tree from the fleet stage
when it adds a newly exposed stale hash or more attribution tests. Reusing fleet
evidence is allowed only after proving the entire production engine, tracks,
profiles and benchmark tooling are byte-identical across those trees; no runtime
change can inherit the earlier run's result.

Complete results and exact tested source identities belong to the retained run
artifacts and the delivery report. An incomplete fleet or failed validation must
remain visible; no publishing step is allowed to treat it as successful.
The current scope is the quiet-rule correction and the requested first/third
research ideas (response-contingent plans and exact prefix reuse). The proposed
learned rollout-endpoint evaluator is not in this branch. Existing teacher
policy distillation is a different feature and is not an endpoint evaluator.
