## Review branch, 2026-09-26: chooser continuity, retained duel proofs and isolated research arms

Baseline: `31bf6b986b669831a4ebc0b9d87cac5adb711a96` (round 278). NOT a promotion.
The review's changes require BOTH `candidateSlots` and explicit `racecraftReview`
flags. The control retains the original decisions, including the crossing abort
and exhausted-search abstention, until a full fleet clears their replacement.
No owner rule, track, map, golden expectation or `user.properties` is changed.

Implemented arms: `crossing` uses the full referee result instead of aborting a
chooser comparison on a nonterminal geometric S/F crossing; `duel-anytime`
retains only completed certificates on exhaustion; `duel-cache` memoizes complete
joint-state/depth/clock subproblems per horizon attempt. Cache savings may fund
additional nodes, so this is measured as a policy arm, not called decision-invisible.
`projected-place` re-tests unresolved-horizon ordering on the post-278 pipeline;
`diverse` adds at most one distinct acceleration proposal; `selective` compares
one stronger first reply only on nominally tied, directly interacting choices.
The latter is a bounded first-response prototype, not a port/promotion of the
older contingent-prefix branch or a universal opponent proof.

`racecraftReviewAudit=true` records scorer/chooser/pace proposals, the final
returned action, immutable forecast observations and duel budget counters.
Forecast snapshots are explicitly NOT replay-ready referee states or training
labels. The accompanying research plan includes the full contingent-prefix
follow-up, exact prefix equivalence, a joint-endpoint value learner, complete
counterfactual labels, held-out track families, and the required promotion matrix.

New functional tests check gating, deterministic shortlist and projected ordering,
nonterminal crossing continuity, low-budget retained proof soundness using the
independent existing physical verifier, and cache/control equivalence with a
non-exhausting budget. See `docs/experiments/racecraft-review/validation.json`
for commands actually executed. No new place improvement, CPU speedup, full-fleet
clearance or trained endpoint model is claimed by this PR.
