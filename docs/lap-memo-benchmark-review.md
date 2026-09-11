# Lap memo and benchmark publication follow-up (2026-09-11)

This follows the review of `935ef474`. It fixes three reproduced boundary bugs;
no racing policy, referee rule, track, persisted map format or golden pin changes.

## Coherent lap memo adoption

The base memo fields are final, but a lap bundle extends an existing entry.
`adoptLapMemo` now holds `REACH_MEMO` through its readiness check and complete
field copy, using the same monitor as `publishLapMemo`. A reader cannot accept
`gateTurns` while the publisher is still assigning the other lap fields. The
lock protects a small reference copy, not map computation. Base memo lookup,
eviction policy, byte accounting and serial map values are unchanged. No disk
cache generation is retired: the defect was in adoption of an in-process lap
bundle, not persisted base-map construction.

`LapMemoPublicationTests`, included in `run_tests.sh`, uses the JDK debugger
interface to stop an actual production reader at the readiness check. It
asserts ownership of the publication monitor, schedules a writer and checks
that the writer blocks. After release, the reader correctly misses the as-yet
unpublished bundle; a retry after publication obtains every array/bitset and
both diagnostic fields. Certified-speed and shedable-landing queries and
repeat-publication byte accounting are checked too. The breakpoint is located
from the source boundary, not a hard-coded source line number. The pre-fix
implementation deterministically fails the monitor assertion.

## Fleet results become resumable only after validation

Workers now return candidate completion records instead of publishing markers.
Only the main runner, after successfully rechecking the experiment manifest,
publishes `.complete.json`. A failed final read is treated just like a changed
manifest: all selected completion markers, rows and `fleet.txt` are removed.
The cleanup also covers interruption during validation. Original logs remain
available for diagnosis but cannot make a fresh failed attempt resumable.

Restoring a missing course or malformed profile therefore reruns Java; restoring
inputs cannot convert an unvalidated result into a successful resumed grid.
Already validated, unchanged runs still resume without launching Java. The
runner's existing source hash also makes output from older runners incompatible
with the new manifest; use a new output directory for pre-fix runs.

## Mixed comparisons bind the experiment, not just cohort counts

`bench_field` captures the binary, selected course hashes, seeds, runtime and
all non-assignment settings. Before changing an assignment it verifies the
previous roster and experiment identity; after changing it, it verifies the new
roster. It rechecks before reporting, including after the final race. Only the
active `playerNKind` labels are excluded from the settings comparison, after
checking that their effective values exactly match the requested assignment.
Inactive slots and other Java-properties settings remain bound. This handles
legitimate mirrored fields without normalizing away unexpected external edits.
Missing/malformed inputs and process errors fail without a successful aggregate,
and the isolated runtime properties are restored. Self-play and champion cache
semantics are unchanged.

## Regression evidence and scope

Thirteen additional Python tests cover valid 2/4/8/9-car mirrors, changed binary,
course, settings, Java executable/options, seeds and roster, missing or malformed
final inputs, restoration/resume, old report invalidation, premature completion
publication and interrupted validation. The existing incomplete-log test now
has valid preflight inputs and asserts that Java is reached, so stricter input
validation cannot hide its original assertion. The new tests fail against the
reviewed production code and pass with the fixes.

Supplementary OpenJDK 21 real-JVM checks reject a changed Hairpin comparison
before the second mirror, then accept an unchanged comparison at 1.500 versus
1.500. The fleet recovery check executes Java twice (rather than reusing the
first, wrong-course result), with no completion marker surviving the failed
validation. These are input-integrity checks, not policy-performance evidence.

Publication validation uses JDK 25 for the strict build, all Java suites,
headless/replay/lap progress and referee differentials, all frozen goldens and
every champion regression pin, together with the Python unit suite. The normal
master workflow additionally tests JDK 26 and browser/parity/publication paths.
Exact completed job results belong to the commit's CI evidence. No full fleet
campaign or new AI promotion is claimed for this synchronization/tooling fix.
