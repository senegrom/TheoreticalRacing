#!/usr/bin/env python3
"""Real worker transport under CPU load, independent of the Java golden suite.

The fixture deliberately burns CPU. It must not prevent UI paints, timer updates,
error handling or stopping/replacing a race. It does not simulate racing rules.
"""
import argparse
import functools
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
  if (m.method==='work') { const end=performance.now()+1800; while(performance.now()<end) {} }
  postMessage({scope:'theoretical-racing',id:m.id,result:m.method});
};
"""
HARNESS = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Worker test</title></head><body>
<button id="click">Responsive button</button>
<script type="module">
import {Engine} from './engine.js?v=3';
window.Engine=Engine; window.errors=[]; window.engine=new Engine((_text,p)=>{if(p?.failure) errors.push(p.failure)});
window.ticks=0; setInterval(()=>ticks++, 20);
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
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(WEB / 'dist')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = getattr(p, args.browser).launch()
            context = browser.new_context()
            context.route('**/worker-harness.html', lambda route: route.fulfill(body=HARNESS, content_type='text/html'))
            context.route('**/runtime.js?*', lambda route: route.fulfill(body=FIXTURE, content_type='text/javascript'))
            page = context.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}/worker-harness.html')
            page.evaluate('ready')
            page.evaluate("window.before=ticks; window.finished=false; void engine.call('work').then(()=>finished=true).catch(()=>{})")
            page.locator('#click').click(timeout=800)
            page.wait_for_function('ticks > before+5', timeout=800)
            assert page.evaluate('clicked===1 && !finished'), 'worker CPU load blocked UI'
            # Termination is synchronous on the UI thread; pending work rejects.
            page.evaluate("window.old=engine; window.abort=''; engine.call('second').catch(e=>abort=e.name); old.destroy(); window.engine=new Engine();")
            page.wait_for_function("abort==='AbortError'")
            assert page.evaluate('old.dead && old.pending.size===0')
            assert page.evaluate("engine.call('fresh')") == 'fresh'
            # A fatal worker error rejects every request, even after boot completed.
            page.evaluate("window.failures=[]; engine.call('crash').catch(e=>failures.push(e.message)); engine.call('queued').catch(e=>failures.push(e.message));")
            page.wait_for_function('failures.length===2')
            assert page.evaluate('engine.dead && engine.pending.size===0')
            # Unanswered operation timeouts also terminate, not just reject.
            page.evaluate("""window.originalTimer=setTimeout;
              window.setTimeout=(fn,ms,...a)=>originalTimer(fn,ms===300000?30:ms,...a);
              window.engine=new Engine(); window.timedOut=false;
              engine.call('work').catch(()=>timedOut=true);
            """)
            page.wait_for_function('timedOut && engine.dead')
            page.evaluate('window.setTimeout=originalTimer')
            page.close(); browser.close()
        print(f'{args.browser}: worker CPU isolation, cancellation, replacement, fatal errors and timeouts passed', flush=True)
    finally:
        server.shutdown(); server.server_close()


if __name__ == '__main__':
    main()
