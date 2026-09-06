#!/usr/bin/env python3
"""Real worker transport under CPU load, independent of the Java golden suite.

The fixture deliberately burns CPU. It must not prevent UI paints, timer updates,
error handling or stopping/replacing a race. It does not simulate racing rules.
"""
import argparse
import functools
import json
import os
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
from playwright.sync_api import sync_playwright

WEB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB))
from serve import RangeHandler

FIXTURE = """
postMessage({scope:'theoretical-racing',ready:true});
onmessage = ({data:m}) => {
  if (m.method==='crash') throw new Error('Test worker failure');
  if (m.method==='work') {
    postMessage({scope:'theoretical-racing',progress:{phase:'CPU stress',done:0,total:0}});
    const end=performance.now()+3000; while(performance.now()<end) {}
  }
  postMessage({scope:'theoretical-racing',id:m.id,result:m.method});
};
"""
HARNESS = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Worker test</title></head><body>
<button id="click">Responsive button</button>
<script type="module">
import {Engine} from './engine.js?v=4';
window.Engine=Engine; window.errors=[]; window.cpuStarted=false;
window.engine=new Engine((_text,p)=>{if(p?.failure) errors.push(p.failure); if(p?.phase==='CPU stress') cpuStarted=true;});
window.ticks=0; setInterval(()=>ticks++, 20);
window.frames=0; function paint(){frames++; requestAnimationFrame(paint)}; requestAnimationFrame(paint);
window.clicked=0; document.querySelector('button').onclick=()=>clicked++;
window.ready=engine.ready;
</script></body></html>"""


class Quiet(RangeHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', choices=['chromium', 'webkit'], default='chromium')
    args = parser.parse_args()
    out = WEB / 'build/browser-tests' / ('worker-' + args.browser)
    out.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(WEB / 'dist')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            options = {'executable_path': os.environ['CHROMIUM_PATH']} if args.browser == 'chromium' and os.environ.get('CHROMIUM_PATH') else {}
            browser = getattr(p, args.browser).launch(**options)
            context = browser.new_context()
            context.route('**/worker-harness.html', lambda route: route.fulfill(body=HARNESS, content_type='text/html'))
            context.route('**/runtime.js?*', lambda route: route.fulfill(body=FIXTURE, content_type='text/javascript'))
            page = context.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}/worker-harness.html')
            page.evaluate('ready')
            # Warm the visible document before measuring CPU isolation. A locator's
            # actionability checks can consume slow headless WebKit paint frames;
            # use an actual pointer event at the already-verified button instead.
            page.locator('#click').click()
            page.wait_for_function('frames>=3 && clicked===1')
            button = page.locator('#click').bounding_box()
            assert button is not None
            page.evaluate("window.before=ticks; window.beforeFrames=frames; window.finished=false; void engine.call('work').then(()=>finished=true).catch(()=>{})")
            page.wait_for_function('cpuStarted', polling=20)
            page.mouse.click(button['x'] + button['width']/2, button['y'] + button['height']/2)
            page.wait_for_function('clicked===2 && ticks > before+5 && frames>beforeFrames', timeout=1500, polling=20)
            evidence = page.evaluate('({clicked,timerTicks:ticks-before,paintFrames:frames-beforeFrames,finished,cpuStarted})')
            (out / 'isolation.json').write_text(json.dumps(evidence, indent=2))
            assert not evidence['finished'], 'UI only responded after worker CPU load ended'
            # Termination is synchronous on the UI thread; pending work rejects.
            page.evaluate("window.old=engine; window.abort=''; engine.call('second').catch(e=>abort=e.name); old.destroy(); window.engine=new Engine();")
            page.wait_for_function("abort==='AbortError'")
            assert page.evaluate('old.dead && old.pending.size===0')
            assert page.evaluate("engine.call('fresh')") == 'fresh'
            # A fatal worker error rejects every request, even after boot completed.
            page.evaluate("window.failures=[]; engine.call('crash').catch(e=>failures.push(e.message)); engine.call('queued').catch(e=>failures.push(e.message));")
            page.wait_for_function('failures.length===2')
            assert page.evaluate('engine.dead && engine.pending.size===0')
            # Inactivity warns without killing the worker or rejecting its result.
            page.evaluate("""window.originalTimer=setTimeout;
              window.setTimeout=(fn,ms,...a)=>originalTimer(fn,ms===300000?30:ms,...a);
              window.engine=new Engine(); window.finished=false; window.waitError='';
              void engine.call('work').then(value=>{window.finished=value==='work'}).catch(e=>waitError=e.message);
            """)
            page.wait_for_function('engine.stalled && !finished')
            assert page.evaluate('!engine.dead && engine.pending.size===1 && !waitError')
            page.evaluate('engine.keepWaiting()')
            page.wait_for_function('finished', timeout=10000)
            assert page.evaluate('!engine.dead && engine.pending.size===0 && !engine.stalled && !waitError')
            page.evaluate('window.setTimeout=originalTimer')
            page.close(); browser.close()
        print(f'{args.browser}: worker CPU isolation, cancellation, replacement, fatal errors and non-destructive inactivity warnings passed', flush=True)
    finally:
        server.shutdown(); server.server_close()


if __name__ == '__main__':
    main()
