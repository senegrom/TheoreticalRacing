#!/bin/sh
set -eu
git show HEAD:.github/quiet-clearance.patch.gz | gzip -dc > "$RUNNER_TEMP/clearance.patch"
echo "d047a8cf34010949ff6a1d0d2d8d7e2442e885e9d473ce2e27cbb0444bcffe90  $RUNNER_TEMP/clearance.patch" | sha256sum -c -
for i in 0 1 2; do git show HEAD:.github/quiet-second.patch.gz.$i; done | gzip -dc > "$RUNNER_TEMP/second.patch"
echo "5b0f198f61dd1918e4b2e66979ee22adc326084fc06ce0d07bee0d04f2b48057  $RUNNER_TEMP/second.patch" | sha256sum -c -
git rm -q .github/quiet-clearance.patch.gz .github/quiet-second.patch.gz.* .github/quiet-final-apply.sh .github/workflows/quiet-clearance-validation.yml
test "$(git write-tree)" = 3c237f54a610e33efe9a67c1dbac4f7133ba70bc
git apply --index "$RUNNER_TEMP/clearance.patch"
test "$(git write-tree)" = df3abd12ca32828a33996a627859e9f56f661c3f
git apply --index "$RUNNER_TEMP/second.patch"
test "$(git write-tree)" = 7c4358a67fd467c55e3563f78fe2cdad502d5857
mkdir -p evidence
git write-tree > evidence/tree.txt
