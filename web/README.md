# Theoretical Racing — browser edition

This branch keeps the desktop game and adds a native HTML/Canvas interface. Like
mahjong, decisions live in one engine, not in a second JavaScript ruleset.
Here the existing Java engine runs **locally in the browser** through the pinned
CheerpJ 4.3 Java 17 runtime. No Java installation, account, game server or plugin
is needed by the player.

## Build and play

The browser build needs JDK 17+ and Python 3.9+. The desktop/original parity tests
need the repository's supported JDK 25+ (the original sources also compile with
Java 21, but that is not the desktop build's supported target).

```sh
sh web/build.sh
python3 web/serve.py --port 8080
# Open http://localhost:8080
```

Serve **the contents of `web/dist`** on a static HTTPS host with HTTP byte-range
support (206 / Content-Range), including a
repository subdirectory on GitHub Pages. Opening `index.html` as a `file:` URL
will not work. Neither will the standard `python -m http.server`, which lacks
byte ranges; use the included `web/serve.py` for local development or
`npx http-server web/dist`. The runtime checks host compatibility at startup.
The Browser app workflow publishes a `browser-webapp` artifact;
extract it and serve its contents. The workflow does not change the repository's
Pages settings or deploy/merge to master.

## What is preserved

* Every rule, finish approach, checkpoint, lap transition, collision, retirement,
  turn ordering and undo operation enters the original `RaceGame` methods.
* Both AI labels, AI1 and AI2, use the original promoted `RaceAi` policy. They are
  deliberately not presented as different difficulty levels: the Java game
  currently uses two labels for the same policy.
* All 84 `.track` files are copied byte-for-byte. The catalogue is exported by
  the **original Java parser**, not parsed/reconstructed in JavaScript. The site
  contains `track-hashes.json` and `engine-sources.json` for auditing.
* Original Java RNG and the original start-cell enumeration determine seeded
  AI placement. A blank seed preserves the legacy first-free placement order.
* The full reachability computation, speed range, AI search and numerical Java
  geometry are retained. There is no simplified, mobile or fallback AI.

`src/` is not modified by the port. `scripts/prepare_sources.py` copies it at
build time, swapping only the Swing presentation/scheduling imports and a small
number of Java 21 list conveniences for equivalent Java 17 expressions. Each
replacement is counted so an upstream edit requires an explicit audit. The AI,
reachability and move-query sources are byte-for-byte copies.

`java/tr/logic/BrowserBridge.java` is a transport adapter: it exports snapshots,
reads the existing live move referee for previews, and forwards actions to the
same public methods that the Swing UI calls. Geometry is exported from the Java
`Area` for display. Canvas never decides whether a move or placement is legal.
One hidden same-origin iframe owns each Java runtime and its workers; replacing
a race destroys that realm instead of leaving an old AI worker running.

## Browser interface

Configure 1–9 human/computer drivers, original colours, names, starting order,
track, laps and optional seed. Draw custom tracks with the original validator.
Tap the grid or use explicit coordinate inputs for placement/drawing. The board
supports drag, pinch, zoom, fit and focusing on a car or start line.

Select a move to preview, then confirm. Invalid moves require separate crash
consent. Undo restores the human decision and all intervening computer replies.
AI pause, single-step and pacing change scheduling only, not the policy. Race
logs export in the original format. Controls support touch, mouse and keyboard;
settings are saved locally when storage is available. Active races are **not**
restored after reloading or leaving the page.

## Verification

```sh
sh run_tests.sh
sh web/build.sh
python3 web/tests/parity.py
python3 web/tests/server_test.py
python3 -m pip install playwright==1.57.0
python3 -m playwright install chromium webkit
python3 web/tests/browser_e2e.py --browser chromium
python3 web/tests/browser_e2e.py --browser webkit
```

Parity compares the complete desktop and adapter logs byte-for-byte across all
12 pre-existing golden races, plus unseeded AI1, negative-seed mixed AI1/AI2 and
multi-lap races. It also checks those original golden hashes, runs the original
finish/checkpoint rule-contract tests on the generated engine, and tests repeat
previews, crash consent, human undo including AI replies, drawing and validation.
No existing golden fixture is changed. Track and source hashes are verified.

The browser tests run the actual CheerpJ JVM, finish a seeded race, and compare
its log with the existing Java golden. Chromium additionally exercises human
placement, repeat previews, keyboard confirmation, undo and replacement of a
running session, custom drawing and subdirectory hosting. WebKit runs at a phone-sized touch viewport. Screenshots and
console logs are uploaded whether the tests pass or fail. `--ui-only` tests only
layout and setup; it is explicitly not a Java-runtime or gameplay parity test.

## Runtime, resources and licensing

The original engine is sizeable and builds exact reachability maps; large
circuits can need substantial startup time and memory, particularly on phones.
The UI reports preparation/failure rather than weakening the AI. Keep the tab
visible to run computer turns. Readiness is polled without joining the Java
worker on the UI path.

Unlike mahjong's bundled Rust/Wasm engine, this edition loads its Java runtime
from `https://cjrtnc.leaningtech.com/4.3/loader.js`. It therefore needs network
access and is **not advertised as an offline/self-contained PWA**. The app has a
home-screen manifest but does not install an incomplete service-worker cache.
The runtime is third-party code, fetched by the browser; the game server does
not receive race decisions.

The game and adapter retain the repository's AGPL-3.0 licence. The runtime has
its separate [CheerpJ Community License](https://cheerpj.com/docs/licensing.html),
which covers personal and FOSS projects with attribution; self-hosting the
runtime or other uses may require a commercial licence. The app credits CheerpJ
and links its game source. Do not remove those credits or redistribute the
runtime without the appropriate permission.

The port starts from desktop commit `b9471692e748c7a6c9d509e6b5992d1f7e8d8268`.
Future engine/track edits must rerun the differential and real-browser tests.
