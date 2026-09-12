#!/bin/bash
set -euo pipefail
for i in 0 1 2 3; do git show bfa8ad2ee1835aae922eab06afd5f0f45307d647:.github/lifecycle.patch.gz.$i; done | gzip -dc > "$RUNNER_TEMP/lifecycle.patch"
echo "274186a9714ce280652dbd5a87cf1192cabdce008c94ce5a79621c0cb0603c54  $RUNNER_TEMP/lifecycle.patch" | sha256sum -c -
git apply --index --exclude=racing-memory.md "$RUNNER_TEMP/lifecycle.patch"
git show 5f4e4890c22242fd62b8e013c6095806285f899c:.github/lifecycle-finalization.patch.gz | gzip -dc > "$RUNNER_TEMP/finalization.patch"
echo "72a77c24806551acb7336591c65b74a3233963e65b7bf9f4a7dcfb1263af22ec  $RUNNER_TEMP/finalization.patch" | sha256sum -c -
git apply --index --exclude=racing-memory.md "$RUNNER_TEMP/finalization.patch"
python - <<'PY'
from pathlib import Path
import os, subprocess
p=Path('racing-memory.md')
header,body=p.read_text().split('\n\n',1)
entry=subprocess.check_output(['git','show',os.environ['GITHUB_SHA']+':.github/lifecycle-integrated-entry.md']).decode()
p.write_text(header+'\n\n'+entry+body)
p=Path('docs/private-lane-lifecycle-review.md')
s=p.read_text()
old='Base: `745798f613406790f88b44607a2a827ad7856a98`.'
assert s.count(old)==1, s[:200]
s=s.replace(old,'Initial review base: `745798f613406790f88b44607a2a827ad7856a98`.\nIntegrated onto `9668703dc1489383bde78f2460476e9f6daa1da0`; the subsequent\nround-238 funnel deletion and all campaign notes are preserved.')
s+='''
## Integration boundary

The first fixes and golden-source isolation used `745798f`. Master subsequently
advanced to `9668703`, changing only the campaign ledger and removing the old
funnel guard from `RaceAi`. This integration keeps that deletion. The final
supported-JDK suites, golden corpus and comparison fleets use the combined
source against the newer base. Earlier partial or complete fleet outputs are
not substituted for those integration results.
'''
p.write_text(s)
PY
git add racing-memory.md docs/private-lane-lifecycle-review.md
git diff --cached --check
test "$(git write-tree)" = 3661687882a2778a2066d8a952914a1680900301
