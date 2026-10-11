# Response-memory compatibility

The creative experiments reuse committed follow-up memory and can be combined
with earlier response strategies. During integration two old input boundaries
were inconsistent with that combination: the capture reader rejected `rc6`,
although the strict validator supported it, and cf4 requests were limited to
17,000 characters, although valid bounded response tables can exceed that size.

The capture reader now delegates rc6 validation to the existing strict checker.
The cf4 envelope accepts at most 280,000 characters; the inner snapshot remains
limited to 262,144 and each response table to 256 entries. This does not change
racing rules, increase proof budgets, or authenticate arbitrary tables as proofs.

Regression tests cover a full 256-entry table, malformed masks and unknown
versions, the complete request digest, scope restoration, and suffix commits
with only the new creative flags enabled. Hint queries remain read-only.

Captures are still pinned to their executable and tooling hashes. Regenerate
captures after changing the executable or the capture/validation tool versions;
do not bypass the manifest checks to reuse an older capture with this code.
