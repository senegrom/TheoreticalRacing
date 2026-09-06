# Theoretical Racing — browser edition

**[Play on GitHub Pages](https://senegrom.github.io/TheoreticalRacing/)**

A native HTML/Canvas interface around the original Java engine. Like mahjong,
decisions live in one engine, not in a separate JavaScript ruleset. The engine
runs locally in the browser through the pinned CheerpJ 4.3 Java 17 runtime.
Players need no Java installation, account, game server or browser plugin.

## Hosting and automatic updates

Application source stays on `browser`. After the native parity and both real
browser test suites pass, `.github/workflows/browser.yml` publishes the exact
tested static artifact to the generated `gh-pages` branch and requests a Pages
build. Nothing is pushed or merged to `master`.

The repository's Pages publishing source is **Deploy from a branch → gh-pages
→ / (root)**. Do not edit the generated branch by hand: a successful browser
build replaces its contents. The site includes `source.tar.gz` (corresponding
AGPL source) and `deployment.json` (the source commit). The publisher rejects
stale source commits and unexpected publishing-source changes, uses non-force
updates, and verifies the deployed commit before running real Java gameplay
against the public URL. Evidence is saved as `live-pages-evidence` in Actions.

On initial setup, the publisher stages a complete site commit and records it
in the `pages-publication` artifact. Creating `gh-pages` at that commit through
the maintainer connection initializes project Pages. Subsequent publications
are automatic; no personal access token is stored in the repository.

## Build and play locally

The browser build needs JDK 17+, Python 3.9+ and the pinned icon-export dependencies in `web/requirements-icons.txt` (CairoSVG uses the system Cairo library). Desktop/parity tests require
the repository's supported JDK 25+.

```sh
python3 -m pip install -r web/requirements-icons.txt
sh web/build.sh
python3 web/serve.py --port 8080
# Open http://localhost:8080
```

Serve the contents of `web/dist` over HTTP(S) with byte-range support (206 /
Content-Range). Subdirectory hosting is supported. Opening `index.html` as a
`file:` URL does not work. The standard `python -m http.server` also lacks
byte ranges; use `web/serve.py` or `npx http-server web/dist`. The app checks
host compatibility before starting Java. A prebuilt `browser-webapp` artifact
is available from the workflow for other static hosts.

## What is preserved

* Rules, finish approaches, checkpoints, laps, collisions, retirement, turn
  ordering and undo enter the original `RaceGame` methods.
* AI1 and AI2 use the original promoted `RaceAi` policy, not separate invented
  difficulty levels. The full reachability computation and search are retained.
* All 84 `.track` files are copied byte-for-byte. The original Java parser
  exports the catalogue. `track-hashes.json` and `engine-sources.json` allow
  independent audits.
* Seeded placement uses the original Java RNG and start-cell enumeration.
  A blank seed keeps the legacy first-free placement order.

The port does not modify `src/`. At build time, `scripts/prepare_sources.py`
changes only the Swing presentation/scheduling imports and counted Java 21
list conveniences into equivalent Java 17 expressions. Upstream drift fails
that build. AI, reachability and move-query sources are byte-for-byte copies.

`java/tr/logic/BrowserBridge.java` exports snapshots, queries the existing live
referee for previews and forwards commands to the public methods used by Swing.
Canvas renders Java's actual corridor and exact finish segment; it never decides
legality. One hidden same-origin iframe owns each Java runtime. Starting a new
race destroys the old realm and its workers.

## Interface

Configure 1–9 human/computer drivers, colours, names, order, track, laps and an
optional seed. Draw custom tracks through the original validator. Use touch,
mouse or coordinate inputs for placement/drawing, and pan, pinch, zoom, fit or
focus the board. Keyboard controls are explained in the in-app help.

Select a move to preview, then confirm it. Crashes require separate consent.
Undo restores the human decision and intervening AI replies. AI pause, step
and pacing affect scheduling only. Exported logs retain the original format.
Settings are saved locally when storage is available; active races are not
restored after reloading or leaving the page.

## Verification

```sh
sh run_tests.sh
sh web/build.sh
python3 web/tests/parity.py
python3 web/tests/server_test.py
python3 -m unittest discover -s web/tests -p 'test_*.py'
python3 -m pip install playwright==1.57.0
python3 -m playwright install chromium webkit
python3 web/tests/browser_e2e.py --browser chromium
python3 web/tests/browser_e2e.py --browser webkit
python3 web/tests/browser_e2e.py --browser chromium --url https://senegrom.github.io/TheoreticalRacing/
```

Parity compares complete desktop/adapter logs byte-for-byte for all 12 existing
golden races plus unseeded AI1, negative-seed mixed AI1/AI2 and multi-lap races.
It checks original golden hashes, original finish/checkpoint/rollout/geometry
contracts, repeated previews, crash consent, undo including AI replies, drawing
and validation. Existing fixtures are not rewritten. Track/source hashes are
verified, and the publisher has offline transport-contract tests.

Chromium and phone-sized touch WebKit run the actual CheerpJ JVM and match a
complete race against an existing Java golden. Both exercise human placement,
repeated previews, confirmation, undo, session replacement and custom drawing.
Mobile tests also check that confirmation is visible on the initial screen.
Screenshots and logs are saved on success or failure. `--ui-only` is explicitly
not a runtime/gameplay test; `--url` exercises an already deployed site.

## Runtime, resources and licensing

Large circuits retain the original exact reachability calculation and can need
substantial startup time and memory, particularly on phones. Preparation or
failure is reported rather than substituting a weaker AI. Keep the tab visible
to run computer turns.

Unlike mahjong's bundled Rust/Wasm engine, this app loads Java from
`https://cjrtnc.leaningtech.com/4.3/loader.js`. It needs network access and is not
an offline/self-contained PWA. The home-screen manifest does not install an
incomplete service-worker cache. Game decisions run locally; the runtime is
third-party code downloaded by the browser.

Game and adapter retain AGPL-3.0. CheerpJ has its separate
[Community License](https://cheerpj.com/docs/licensing.html), covering personal
and FOSS projects with attribution; other uses or runtime self-hosting may need
a commercial licence. Keep the app's runtime credit and game-source links.

The port started from `b9471692e748c7a6c9d509e6b5992d1f7e8d8268` and incorporates
master `fcee261ea27fb17b971819d573b8272f502a4f82`, including its lap-aware AI and
exact finish-geometry fixes, without changing those sources. Engine/track edits
must rerun the differential and real-browser checks before publication.

## UI and installed-app review

The browser/Apple icon family is generated from `branding/racing-icon.svg`;
see `branding/README.md`. The Install button explains Home Screen / Dock setup.
Standalone mode includes safe-area spacing, and touch text inputs avoid Safari’s
small-input zoom. This is still an online web app; active races are not persisted.

UI regression coverage (`python3 web/tests/ui_e2e.py`) uses isolated presentation
fixtures, not an alternative game engine. It checks setup validation, narrow and
landscape layouts, long names, keyboard/touch controls, stale downloads, setup
cancellation, errors, notification dismissal and icon declarations. Actual Java
runtime gameplay is checked separately by `browser_e2e.py` on both browser engines
and the deployed public site. Device-level iOS Home Screen installation cannot
be automated by these desktop WebKit tests and should also be checked on an iPhone.
