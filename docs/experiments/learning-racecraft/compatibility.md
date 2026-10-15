# Final compatibility checks

The implementation at `a3aff4d` passed JDK 25 and 26 full contracts, Python,
current-master golden races, the 32 recovered-policy races and six complete
counterfactual cases, and the 36 strategy-arm races and six complete cases.
The new learning CLI stopped before its first race because it attempted to hash
an absent, untracked `user.properties` in a clean checkout. This was a runner
assumption, not a policy failure or a completed race screen.

Repair `eca87493daca31558fe70f2554eeccdff2f577e8` uses the older runners' rule:
hash caller files only when they exist. It also aligns the legacy breeder's
request-size bound with the larger rc7/cf4/league limits. A structural witness
populates all nine slots with 512 response records each, with proof policy OFF,
and verifies snapshot parsing and a complete breeder continuation. The records
are parser data, not claimed search-certified responses.

JDK 25 full Java and Python contracts passed again in run 38823146784. These
compatibility edits do not alter the driving policy. The focused read-only
learning workflow repeats both JDK suites and runs the corrected complete-race,
full-suffix counterfactual and league-evolution controls without cancelling the
already-running full regression/browser battery at the same driving code.

No performance gain, fleet clearance, or promotion follows from these checks.
Temporary write-capable repair workflows are removed from the branch.
