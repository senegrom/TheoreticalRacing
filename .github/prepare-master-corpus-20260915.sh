#!/bin/bash
set -euo pipefail
BASE=094f242214b7bc5176a2a236df8bb1cac4d04b86
SAVED_BASE=9668703dc1489383bde78f2460476e9f6daa1da0
SAVED_FIX=8d18dbd3cd720977dfb649e8f585fbaa80200740
test "$(git rev-parse HEAD)" = "$BASE"
git diff "$SAVED_BASE" "$SAVED_FIX" -- . ':(exclude)racing-memory.md' | git apply --index
git show 4be2137a49bd4deae1581f5556742ae117a2fa18:tests/query_replay_regression.py > tests/query_replay_regression.py
git add tests/query_replay_regression.py
test "$(git write-tree)" = 119d2e50c6a3539349ed95082be1421acf445890
for i in 0 1 2 3 4 5 6; do git show "$GITHUB_SHA":.github/master-corpus-20260915.patch.gz.$i; done | gzip -dc > "$RUNNER_TEMP/measured-corpus.patch"
echo "20ad52face47e85873a465852c35ecaca1a5f95320b480c689f10767b9dfd542  $RUNNER_TEMP/measured-corpus.patch" | sha256sum -c -
git apply --index "$RUNNER_TEMP/measured-corpus.patch"
test "$(git write-tree)" = 65d1d57f5d001c6f391c5d19a4c091c1ea36e2a3
git diff --cached --exit-code 119d2e50c6a3539349ed95082be1421acf445890 -- src tracks user.properties
