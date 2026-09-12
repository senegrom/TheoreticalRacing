#!/bin/bash
set -euo pipefail
test "$(git rev-parse HEAD)" = 9668703dc1489383bde78f2460476e9f6daa1da0
for i in 0 1 2; do git show "$GITHUB_SHA":.github/boundary.patch.gz.$i; done | gzip -dc > "$RUNNER_TEMP/boundary.patch"
echo "14e44be54a71cabb3a8947c70a9c685748dc9a6d60d43cc2811ef27c661d8f99  $RUNNER_TEMP/boundary.patch" | sha256sum -c -
git apply --index "$RUNNER_TEMP/boundary.patch"
test "$(git write-tree)" = 21473683b03d20248a8415691ce040d5f775e3a8
git show "$GITHUB_SHA":.github/boundary-corpus.patch.gz | gzip -dc > "$RUNNER_TEMP/corpus.patch"
echo "4bf2840f69d55196436994898c2491d8ba3f6fbb5e5d45e68937afb10009c60a  $RUNNER_TEMP/corpus.patch" | sha256sum -c -
git apply --index "$RUNNER_TEMP/corpus.patch"
test "$(git write-tree)" = 528ad4b12312cfb53eb4408cba9922bda4ee204c
git diff --cached --check
