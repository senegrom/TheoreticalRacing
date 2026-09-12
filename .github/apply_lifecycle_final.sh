#!/bin/bash
set -euo pipefail
for i in 0 1 2 3; do git show bfa8ad2ee1835aae922eab06afd5f0f45307d647:.github/lifecycle.patch.gz.$i; done | gzip -dc > "$RUNNER_TEMP/lifecycle.patch"
echo "274186a9714ce280652dbd5a87cf1192cabdce008c94ce5a79621c0cb0603c54  $RUNNER_TEMP/lifecycle.patch" | sha256sum -c -
git apply --index "$RUNNER_TEMP/lifecycle.patch"
test "$(git write-tree)" = 4514d674cc77b9231c949ee44449e03358ee97bc
git show "$GITHUB_SHA":.github/lifecycle-finalization.patch.gz | gzip -dc > "$RUNNER_TEMP/finalization.patch"
echo "72a77c24806551acb7336591c65b74a3233963e65b7bf9f4a7dcfb1263af22ec  $RUNNER_TEMP/finalization.patch" | sha256sum -c -
git apply --index "$RUNNER_TEMP/finalization.patch"
git diff --cached --check
test "$(git write-tree)" = f2f82ad80ff6fdcf0d1821b42f156038fa90f98b
# Finalization changes test setup, measured golden fixtures and documentation only.
test -z "$(git diff --name-only 4514d674cc77b9231c949ee44449e03358ee97bc -- src tracks)"
