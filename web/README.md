# Theoretical Racing — browser edition

**[Play on GitHub Pages](https://senegrom.github.io/TheoreticalRacing/)**

A native HTML/Canvas interface around the original Java engine. Like mahjong,
decisions live in one engine, not in a separate JavaScript ruleset. The engine
runs locally in the browser through the pinned CheerpJ 4.3 Java 17 runtime.
Players need no Java installation, account, game server or browser plugin.

## Hosting and automatic updates

The site tracks `master`. A push that changes what the site contains -- the
web app, the engine, the track files, shared tests/build scripts, dependency
configuration, the licence or the workflow itself --
runs `.github/workflows/browser.yml`. Publication requires **all three gates**:
full engine CI, native parity, and both real browser suites. Engine CI is a local
reusable call to `.github/workflows/ci.yml` at the **same commit**; it includes
JDK 25/26 builds and core tests, tooling checks, headless smoke, query replay,
lap progression, the golden corpus, every champion regression pin, and benchmark
failure propagation. A failed, skipped or cancelled gate prevents publication;
a green browser parity result cannot override a failed engine test. The exact
tested artifact is then deployed to GitHub Pages. Commits
that touch none of those (a ledger entry, say) do not run it, and nothing is
published that has not passed.

The repository's Pages publishing source is **GitHub Actions**. There is no
generated branch to edit: the artifact is served straight from the run that
built it, which is why deleting the old `gh-pages` branch cost the site
nothing. The published site still includes `source.tar.gz` (corresponding AGPL
source for the exact commit) and `deployment.json` (that commit and the
repository). After deployment the workflow plays a real Java race against the
public URL, and saves the evidence as `live-pages-evidence` in Actions.

Generated `site/` files are not versioned. The publish job empties a staging
folder under `RUNNER_TEMP` before downloading the tested artifact. The build's
`asset-manifest.json` binds every file to its SHA-256 digest and source commit;
missing files, altered files, symlinks and leftovers fail publication. Matching
source is archived from that exact checkout, then hashed into the manifest too.
The page links current `master`, the exact corresponding source archive, and
the immutable build commit. The commit link is stamped before the artifact is
hashed and tested; publication does not rewrite the tested HTML. Local builds
without revision metadata leave the commit link hidden rather than guessing.

General CI and browser publication share one engine test definition through
`workflow_call`. The browser job depends on its own validation result instead of
polling unrelated CI runs. Changes to that definition or any track-tooling input
also trigger browser validation. The expensive manual promotion battery remains
separate; publication does not claim to have run it.

Public verification first waits for a cache-busted `deployment.json` matching
`--expected-sha` and the repository, then starts gameplay. An older functioning
site cannot satisfy the revision gate. Publication jobs queue without cancelling
one another, and a final guard refuses a candidate that is no longer current
`master`. Thus an old workflow rerun cannot roll back the site or cancel a newer
run. A skipped superseded build can be replaced by dispatching the workflow on
current `master`, including when the newer commit was only a ledger edit.

No personal access token is stored in the repository: deployment uses the
run's own OIDC identity, so the workflow needs `pages: write` and
`id-token: write` and no write access to repository contents.

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
list conveniences into equivalent Java 17 expressions, and adds erasable
output-only reachability progress hooks. Upstream drift fails the build. AI and
move-query sources are byte-for-byte copies. No game decisions are changed.

`java/tr/logic/BrowserBridge.java` exports snapshots, queries the existing live
referee for previews and forwards commands to the public methods used by Swing.
Canvas renders Java's actual corridor and exact finish segment; it never decides
legality. One dedicated Web Worker owns each Java runtime. Starting a new race
or stopping work terminates the old worker immediately.

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
node --test web/tests/engine.test.mjs
python3 -m unittest discover -s web/tests -p 'test_*.py'
python3 -m pip install playwright==1.57.0
python3 -m playwright install chromium webkit
python3 web/tests/browser_e2e.py --browser chromium
python3 web/tests/browser_e2e.py --browser webkit
python3 web/tests/browser_e2e.py --browser chromium --url https://senegrom.github.io/TheoreticalRacing/ --expected-sha "$(git rev-parse HEAD)"
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
not a runtime/gameplay test; `--url` requires `--expected-sha` and exercises an
already deployed site only after verifying its revision.

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


## Responsiveness and honest progress

The Java runtime now runs in a dedicated Web Worker, not on the page's event
loop in an iframe. Each operation shows a spinner, an elapsed-time counter and a
progress bar. Track preparation reports actual phases and percentages of the
current finite scan. BFS and AI search have unknown final work sizes: they use
indeterminate bars (with explored-state counts where available), never an
invented percentage or ETA. Pause takes effect after the current AI turn; Stop
race terminates it immediately and explicitly discards that race.

The three-minute boot and five-minute operation watchdogs measure silence,
not total elapsed time. Changed runtime stages or progress counters restart
monitoring; repeated counters do not count as advancement. Silence produces a
visible warning with **Keep waiting** and **Stop race**, never an automatic
termination. Keep waiting retains pending calls and restarts monitoring; genuine
progress dismisses the warning automatically. Explicit worker failures still
terminate and reject outstanding calls. No watchdog changes the AI search or
its outcome. Deterministic clock tests cover the old five-minute race-loss bug,
late completion, duplicate telemetry, cancellation and fatal failures.

`instrument_progress.py` inserts only tagged, output-only statements in the
browser copy of Reachability. Removing those lines and reversing the two audited startup-scheduling edits
recovers the exact original source, which CI asserts. Original `src/`, AI policies, traversal order, bounds,
geometry, caches and all tracks remain unchanged. The full parity corpus still
checks complete desktop/browser race logs. Progress instrumentation is not used
as an AI cutoff or a search budget. Readiness polling transfers only a small
status object instead of repeatedly rebuilding/rendering full race snapshots.

Physical icon filenames now include both the Racing name and a revision, so
iOS and tab icons do not depend solely on a query-string cache buster. The app ID
and start URL remain unchanged. This does not edit the separate PlateLoader app
or clear another app's data. An existing Home Screen shortcut may still need to
be removed and added again from the Racing page to refresh its saved icon.


## Stable race layout and preparation stages

The activity slot stays mounted during the whole race, including the delay
between computer turns. Its title, progress, elapsed time and warning/Continue
slots have fixed dimensions. The acceleration pad and confirmation button also
stay mounted on AI turns (disabled), rather than changing the control layout.
Driver names, status, telemetry, results and notifications cannot resize the
board or move the pad. Normal resizing/rotation and explicit pan/zoom still work.

Startup has two distinct indicators: the current scan/search, and a checklist
with a second progress bar for **completed prerequisite stages**, not elapsed
or remaining time. The actual Java geometry selects six stages for a single-lap
course (runtime, geometry, distance map, cache check, finish routes, driving
maps) or nine when lap maps are needed (lap routes, lap safety, lap driving).
Computed placement on a checkpoint course adds a tenth stage, Exact race map;
this was formerly a lazy calculation on the first AI driving turn.
Validated cache hits can satisfy stages without recomputation. Checkpoint
convergence and the different braking/safety passes remain visible within their
stage; there is no guessed time percentage or fixed number of convergence rounds.

One RaceGame owns one Reachability and one RaceAi controller, shared by all
1–9 drivers. The map build does not depend on their chosen starting positions.
A confirmed preset starts preparation immediately; a custom drawing starts it
only after both valid borders are confirmed. Distance BFS now joins the existing
background preparation thread, so it too can overlap car placement. No additional
worker, per-driver map copy, geometry rebuild or weaker search is introduced.
Start-cell display is cached once inside the start-zone bounds, retaining the
exact original x-then-y cell order and checking occupancy on each snapshot.

Starting-cell **selection** is now computed by default in interactive Java and
browser games. Each AI waits for all shared maps (including the exact full-race
potential on checkpoint courses), then scores the free cells against the live
positions of cars already placed. Placement order and driving turn order remain
the roster order: an AI cannot see a later player's future placement. Humans
whose placement turn comes first can place while the maps are building.

This is an intentional starting-policy change, not just rescheduling. The driving
AI, track geometry, physics and finish rules are unchanged. The score is the
minimum finish time after a first move legal against current occupancy, followed
by the exact solo route within the engine's velocity domain. It is not a proven
multiplayer optimum: rivals can move before or after that first turn. Seeds break
only equal-score ties, and each AI scores afresh after earlier placements.

Legacy benchmark placement remains an explicit setup option and the default for
headless benchmark runs. The aiStartPlacement=informed property enables computed
starts in headless Java too; aiStartPlacement=legacy requests the historical
first-free/seeded-random policy. Existing golden fixtures are tested in explicit
legacy mode, unchanged, alongside new native/browser computed-start comparisons.
If the exact multi-lap map exceeds the existing memory budget, computed placement
fails visibly rather than silently switching to random starts; choose a smaller
course/fewer laps or explicitly select the legacy policy.

The startup regression blocks only the distance-entry telemetry observer and
proves humans can place while BFS is blocked, while AIs remain unplaced until
both distance and full-race potential barriers have been released. Mixed
human/AI fields, nine-driver fields, undo and two-lap preparation are covered.
There is still just one shared geometry/distance/potential build, not one per AI.
Browser regressions compare actual element bounds through human/AI transitions,
thinking, pauses, warnings and continuation at five viewport sizes. The real
Java browser golden race also records and checks stable bounds across AI turns.
