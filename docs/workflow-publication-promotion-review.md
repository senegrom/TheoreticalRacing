# Publication and candidate-cohort workflow fixes (2026-09-11)

This addresses the two workflow findings from the review of `59a5530`, on top of
`5aa9c8b`. The newer round-234 policy and its re-frozen corpus are preserved.
No Java policy, referee, map, bundled track, saved user setting or golden pin is
changed by this patch.

## Every current master push has a publication path

Browser path filtering now applies only to pull requests. Every push handled by
CI (the workflow accepts master pushes only), including documentation-only
successors, builds and tests a fresh browser artifact. Manual runs also do so.

A newer push can still cancel an older CI run, but the successor no longer loses
its unpublished engine changes by considering only its immediate diff. The
existing supported-JDK, golden, tooling and browser requirements all remain on
the publication job. Failures, skipped dependencies and cancellations cannot
bypass that gate. The latest-master guard is unchanged: rerunning an old revision
still cannot overwrite a newer release. To recover a cancelled publication
without another push, manually dispatch CI at current master.

The regression constructs a real three-commit repository: deployed code, an
unpublished engine change, then a documentation successor. It verifies the
successor requires a browser artifact, the old SHA is rejected by the actual
publication guard, and the current SHA is allowed. Documentation-only pull
requests still skip browser checks; no extra API lookup or deployment permission
is needed for deciding coverage. The tradeoff is more browser work on master
rather than a fragile last-deployment lookup.

## Compare the candidate that is actually selected

The manual promotion workflow no longer uses label-only AI1/AI2 comparisons.
Its matrix covers 2/4/8 cars, legacy/informed/scatter starts and independent seed
windows 1–5, 6–10 and 11–15: 27 jobs, with at most three running concurrently.
Every job runs all courses beside the built JAR, not just the fast-track subset.
Both mirror grids use identical all-AI1 rosters and settings; only candidateSlots
changes from the odd half to the even half. The selected source revision must
implement its experimental policy behind that existing gate.

`tracks/promotion_pair.py` creates fresh runtime profiles using decoded
Java-properties keys. It checks the requested field size, controllers and slots,
then delegates each grid to `fleet_grid.py`. One JVM runs at a time with an
explicit `-Xmx8g` in the workflow. Ambient JVM option variables are empty in CI
and rejected by the runner when nonempty; they cannot silently override the
reference heap. An explicit alternative --heap is recorded for local experiments,
not substituted for the workflow's reference configuration.

Before reporting, the runner checks each completed manifest against its original
request and each actual log against the requested roster and candidate slots.
`head_to_head.py` independently validates the complete mirrored classifications,
complementary balanced cohorts, seeds, geometry and configuration and scores
finishing places. Binary, runtime, course, source-profile, generated-profile and
tooling changes are rechecked between grids and after scoring. The final report
is published only on success. Failed attempts retain logs/manifests for diagnosis
but do not have `head-to-head.txt`; existing directories are never overwritten.
Artifacts include the profiles, manifests, full logs and successful score report,
including diagnostic files on failure. Effective start fallbacks and courses
that disable laps remain visible in the raw logs under the existing referee rules.

A green battery is evidence completion, not automatic policy approval. Finishing
place is the comparison criterion; field crashes and summed moves do not veto a
candidate. Historical label benchmarks and the archived duel screen are retained
as diagnostics, not presented as the modern candidate promotion route.

## Regression scope

Unit tests exercise all nine field/start combinations, complete mirrors, missing
or wrong candidate cohorts, complete wrong-controller logs, changed inputs,
missing/malformed final profiles, Java failure, scorer failure, hidden heap
settings, malformed selections and preservation of existing evidence. Workflow
contracts assert all 27 matrix combinations, the production command, fixed heap,
full-course scope and artifact retention, rather than the retired label commands.

`tests/promotion_pair_regression.py`, run by normal CI on both JDK 25 and JDK 26,
executes the real production command over Hairpin and Circle in all nine field/
start configurations: 36 positive races, 168 car-races (84 per policy cohort).
It also verifies that a real, otherwise complete race with candidate metadata
removed is rejected before a successful comparison can be published. These are
contract checks, not a new fleet campaign or a claimed performance improvement.

Local Java validation uses supplementary OpenJDK 21. Supported-release builds
and exact completed suite outcomes are recorded in the published CI evidence.
