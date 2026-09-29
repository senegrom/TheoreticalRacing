#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p web/build
rm -rf web/build/classes web/dist
mkdir -p web/dist/tracks
python3 web/scripts/export_icons.py --output web/dist
python3 web/scripts/prepare_sources.py web/build/src
find web/build/src -name '*.java' | sort > web/build/sources.txt
mkdir -p web/build/classes
javac --release 17 -encoding UTF-8 -Xlint:all -Werror -d web/build/classes @web/build/sources.txt
python3 web/scripts/engine_identity.py record web/build/src web/build/classes
# A fixed entry date: two builds of one commit publish one jar.
jar --create --date=2026-01-01T00:00:00Z --file web/dist/racing.jar -C web/build/classes .
cp tracks/*.track web/dist/tracks/
java -Djava.awt.headless=true -cp web/dist/racing.jar tr.logic.BrowserBridge catalogue > web/dist/tracks.json
cp web/build/engine-sources.json web/dist/
for f in index.html app.css app.js activity.js board.js engine.js runtime.js manifest.webmanifest; do
    cp "web/$f" web/dist/
done
ENGINE_ID=$(python3 web/scripts/engine_identity.py stamp web/build/classes web/dist/runtime.js)
# The page loads the jar by this build's name (runtime.js); racing.jar stays for the tools.
cp web/dist/racing.jar "web/dist/racing-$(printf '%.12s' "$ENGINE_ID").jar"
cp LICENSE web/dist/LICENSE.txt
printf '' > web/dist/.nojekyll
python3 - <<'PY'
from pathlib import Path
import hashlib, json
root = Path('web/dist')
(root / 'track-hashes.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('tracks').glob('*.track'))}, indent=2) + '\n')
PY
python3 web/scripts/stamp_versions.py web/dist
python3 web/scripts/site_artifact.py seal web/dist
printf 'Browser build: web/dist/\n'
