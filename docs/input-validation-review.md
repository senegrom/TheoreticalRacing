# Input validation follow-up (2026-09-11)

This review starts from `80177394`, after the previous cache, checkpoint replay
and preparation-error fixes. Two additional input-boundary defects are corrected;
no AI policy, referee rule, map format or behavioral golden is changed.

## Cross-era experiments must share the same course and profile

The legacy exhibition command previously validated fresh results but could run
its two brains against different `.track` files under the same name. It also
accepted file changes between the two mirrored races. A complete classification
does not make those comparisons meaningful.

Before any race, `cross_era.py` now checks both eight-AI rosters, matching course
bytes in the two JAR installations, and matching properties except for the
intentionally different AI-kind labels. It captures both JARs, raw properties,
track data and Java executable/options, and rechecks identity after the complete
comparison before printing any results. Missing or incompatible inputs fail
before start generation. A changed experiment has no performance report.

Use matching settings and track files with `era_AI1.properties` and
`era_AI2.properties`. Different policy JARs are intentional and remain supported;
only their associated experiment inputs must agree. Existing checkpoint,
scattered-start and incomplete-horizon guards remain in force. This command is
still a legacy, non-checkpoint exhibition tool, not the modern promotion gate.

Seven new Python tests exercise matching inputs, different same-named courses,
missing files, both roster checks, profile differences, mid-comparison file
changes and runtime-option changes. Existing classification and process-error
unit tests still inject their original failures after the new preflight.

## Malformed track properties are rejected without losing saved settings

Java's properties decoder raises `IllegalArgumentException` for malformed
Unicode escapes. Both track readers previously caught only I/O errors, letting
malformed metadata escape the advertised null/false load-failure contract.

`TrackIO.loadTrackData` and `trackDeclaresClosable` now reject these decoder
errors. `loadTrack` returns false before changing saved track/settings. Valid
Unicode escapes and valid closure declarations continue to load. A repaired
file works on the next attempt; no restart is needed to repair the file itself.

`TrackImportTests`, run by `run_tests.sh` on both supported JDK CI jobs, covers
malformed name, border and closure properties, unchanged saved settings, valid
Unicode and recovery. It writes only a unique temporary track beside the test
classes and removes it afterwards. Bundled courses and personal properties are
never changed.

## Review and validation

Both new regression groups fail against the pre-fix code and pass with the
corrections. Supplementary OpenJDK 21 integration checks produce 4.500 versus
4.500 for identical policies over mirrored Hairpin races, reject the same-named
different course, and return CLI status 2 for malformed track text without an
exception stack trace or successful race log. The Python suite has 114 tests.

The final review checked the input-validation call order, no-partial-report
behavior, saved-settings preservation, Java/browser source transformation, and
compatibility with the existing cache/replay contracts. Exact suite outcomes
and supported JDK/browser CI status accompany the published commit's evidence.
These checks are not a new AI promotion or a full fleet campaign.
