# Self-play profile follow-up (2026-09-11)

This follows the review of `fce7170c`. The remaining finding was that valid
Java-properties syntax could leave self-play running a different field or
controller from the one named by its report. No racing policy, referee, map,
track, persisted map-cache format or behavioral golden pin is changed.

## Decode keys before assigning the experiment

The setters now update decoded properties rather than matching raw lines.
Colon/whitespace separators, indentation, escaped keys, continuations and
last-wins duplicate declarations all resolve to the actual Java key. Missing
active controller keys are created; `set_all_to` covers every active slot,
including a ninth slot, without changing inactive controllers.

The isolated runtime profile is serialized as deterministic, escaped ASCII.
Other effective keys and values survive, including Latin-1 bytes and Unicode
escapes. Non-ASCII characters are emitted as UTF-16 code-unit escapes. Source
formatting/comments need not survive inside the temporary runtime file; the
caller-owned profile and saved runtime bytes are preserved exactly. Malformed
input is decoded before any setter write. The self-play and mixed-field cleanup
paths both restore bytes instead of assuming UTF-8.

`bench(tracks, nplayers=8)` makes field size explicit. The isolated `2car` and
`4car` modes pass their requested count instead of monkeypatching a setter.
Profiles whose `maxPlayers` setting prevents that count are rejected, not
silently run as smaller fields. Invalid setter arguments and partial roster
assignments are rejected too.

## Verify what was requested, not just what was configured

Self-play checks the effective roster after setup, before changing controller
arms, around each race process and before reporting or publishing a baseline.
Every active slot must match the requested controller and count. A no-op setter,
unexpected field/controller edit, missing profile or malformed final read cannot
produce a successful aggregate. Rewriting an arm cannot conceal a previous
unexpected roster edit.

The self-play manifest normalizes active AI labels only after that check. Field
size, inactive controllers, names, other settings, courses, binaries, seeds and
runtime remain bound. A frozen champion still survives an unrelated candidate
rebuild, and a cache hit runs only the candidate arm. Row bounds now use the
requested field's maximum retirement count, rather than eight-car assumptions.

Self-play manifests use schema 2 and include `nplayers`. Older baseline files
fail the existing manifest check; use a new `BENCH_BASELINE` file. They are not
silently imported, rewritten or treated as evidence for a different field.
Mixed-field manifests retain their existing semantics.

## Regression evidence

Sixteen new Python tests cover alternate and absent keys, duplicate/escaped/
continued keys, Unicode and Latin-1 preservation, all active sizes, no-op setters,
clamping, altered or missing final inputs, inactive-slot edits, cached comparisons,
small-field cache bounds, explicit isolated-mode arguments and mixed-field reuse.
The complete Python suite passes 143 tests.

`tests/selfplay_profile_regression.py` is added to normal CI. An independent
`java.util.Properties` probe compares the actual Java maps before and after
setup, including separators, whitespace, surrogate pairs, a lone surrogate,
control characters and unrelated settings. A recording Java launcher then
forwards to the real JVM without changing the CLI or game. All 45 recorded races
have the requested names, controllers and field sizes, across 8car/4car/2car,
baseline creation and candidate-only cache reuse. Incompatible cached fields,
clamped fields and malformed inputs fail before racing. Inputs and evidence
are temporary; repository courses and `user.properties` are never edited.

Local Java checks use supplementary OpenJDK 21. Publication validation runs the
strict build and Java suites on JDK 25/26, and the Python, real-JVM profile,
headless/replay, golden and champion regression suites on JDK 25. Exact completed
results belong to the commit's CI evidence. This is a measurement-correctness
fix, not a new AI promotion or a full fleet campaign.
