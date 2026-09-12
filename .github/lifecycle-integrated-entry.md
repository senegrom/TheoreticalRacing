## Review follow-up (2026-09-12): physical private lanes and terminal lifecycle

The four findings from `745798f` are repaired: the exact private-lane oracle
covers physical rival speeds with full lap/checkpoint state; rollouts stop when
the referee classifies the last survivor; interactive timeout retirements now
create Undo snapshots. Pending simulated moves also obey timeout precedence.
The existing champion, third-move opt-in and referee rules are not replaced.

New physical-occupancy, model/referee and non-modal Undo regressions cover the
concrete failures and adjacent boundary cases. Measurement uses mirrored cohorts
in a disposable comparison binary with the unchanged base scorer as control;
the unrelated third-move candidate is disabled on both sides only in that binary.
Full-course, reference-heap comparisons and supported-JDK/golden outcomes belong
to this change's publication evidence. See `docs/private-lane-lifecycle-review.md`.
No saved user settings, bundled geometry or persisted map formats change.

Three golden trajectories move because of rollout termination, isolated with
private-only and rollout-only binaries. All three preserve order/crashes;
Monaco s9 4p is two turns shorter (551 -> 549). Only those three measured hashes
and that turn count are re-frozen, with explicit fixture reasons. The other
nine goldens and all 24 champion pin expectations remain unchanged. The
source-isolation record is in docs/experiments/lifecycle/golden-audit.json.

Integration preserves the later round-238 funnel-guard deletion and campaign
notes from `9668703`; final validation and mirrored comparisons use that base.

