#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p web/build
rm -rf web/build/classes web/dist
mkdir -p web/dist/tracks
python3 web/scripts/prepare_sources.py web/build/src
find web/build/src -name '*.java' | sort > web/build/sources.txt
mkdir -p web/build/classes
javac --release 17 -encoding UTF-8 -Xlint:all -Werror -d web/build/classes @web/build/sources.txt
jar --create --file web/dist/racing.jar -C web/build/classes .
cp tracks/*.track web/dist/tracks/
java -Djava.awt.headless=true -cp web/dist/racing.jar tr.logic.BrowserBridge catalogue > web/dist/tracks.json
cp web/build/engine-sources.json web/dist/
for f in index.html app.css app.js board.js engine.js runtime.html runtime.js manifest.webmanifest icon.svg; do
    [ ! -f "web/$f" ] || cp "web/$f" web/dist/
done
cp LICENSE web/dist/LICENSE.txt
printf '' > web/dist/.nojekyll
python3 - <<'PY'
from pathlib import Path
import hashlib, json
root = Path('web/dist')
(root / 'track-hashes.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('tracks').glob('*.track'))}, indent=2) + '\n')
PY
printf 'Browser build: web/dist/\n'
