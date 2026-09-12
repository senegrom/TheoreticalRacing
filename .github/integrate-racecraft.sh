#!/bin/bash
set -euo pipefail
for i in 0 1 2; do git show "$GITHUB_SHA":.github/racecraft-resolution.gz.$i; done | gzip -dc > "$RUNNER_TEMP/resolution.patch"
echo "9b973b81a4cb013c041d8b8990a9e9749b620a4d3b264b39ab574ad096b462be  $RUNNER_TEMP/resolution.patch" | sha256sum -c -
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
if git cherry-pick --no-commit 9d23057d37de220d2301ff26dcda898eef858a53; then
  echo 'Expected explicit integration conflicts were absent' >&2
  exit 1
fi
python3 - <<'PY'
import subprocess
paths = subprocess.check_output(['git', 'diff', '--name-only', '--diff-filter=U'], text=True).splitlines()
assert paths == ['racing-memory.md', 'src/tr/logic/RaceAiTactics.java'], paths
PY
git checkout --ours racing-memory.md src/tr/logic/RaceAiTactics.java
git add racing-memory.md src/tr/logic/RaceAiTactics.java
test "$(git write-tree)" = 88ff53f7d48cac4026447a815a67cb6de28ff415
git apply --index "$RUNNER_TEMP/resolution.patch"
git diff --cached --check
test "$(git write-tree)" = e11b4bccaa2cab3852f691cc792581d5ca2a98c8
