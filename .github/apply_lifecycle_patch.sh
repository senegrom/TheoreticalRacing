#!/bin/bash
set -euo pipefail
for i in 0 1 2 3; do git show "$GITHUB_SHA":.github/lifecycle.patch.gz.$i; done | gzip -dc > "$RUNNER_TEMP/lifecycle.patch"
echo "274186a9714ce280652dbd5a87cf1192cabdce008c94ce5a79621c0cb0603c54  $RUNNER_TEMP/lifecycle.patch" | sha256sum -c -
git apply --index "$RUNNER_TEMP/lifecycle.patch"
git diff --cached --check
test "$(git write-tree)" = 4514d674cc77b9231c949ee44449e03358ee97bc
