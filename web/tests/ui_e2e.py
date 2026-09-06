#!/usr/bin/env python3
"""Network-free UI fixtures. Not a physics/policy substitute or parity test.

Render the real HTML/CSS/controller/canvas with a deterministic transport stub.
Actual HTTP assets, Java execution and public-site gameplay are tested separately
by browser_e2e.py. This suite deliberately runs offline in both browser engines.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

WEB = Path(__file__).resolve().parents[1]
MOCK = r'''
class Engine {
  constructor(onStatus) { this.dead = false; this.onStatus = onStatus; window.testEngine = this; onStatus('Loading the Java runtime…'); }
  async call(method, ...args) {
    window.calls.push([method, ...args]);
    if (method === 'create') {
      this.state = structuredClone(window.fixture);
      if (window.holdCreate) await new Promise(resolve => window.releaseCreate = resolve);
    }
    if (window.failNext) { const text = window.failNext; window.failNext = null; throw new Error(text); }
    if (this.dead) throw new DOMException('Race closed', 'AbortError');
    if (window.holdTick && method === 'tick') await new Promise(resolve => window.releaseTick = resolve);
    const s = this.state;
    if (method === 'log') return await new Promise(resolve => window.releaseLog = resolve);
    if (method === 'preview') s.selected = args[0];
    if (method === 'move') { s.turn++; s.current = 1; s.selected = -1; }
    if (method === 'undo') { s.turn = 0; s.current = 0; s.selected = -1; }
    if (method === 'click') s.lastClick = args;
    if (method === 'tick') s.turn++;
    return structuredClone(s);
  }
  keepWaiting() { window.keptWaiting=true; this.onStatus('', {stalled:false}); }
  destroy() { this.dead = true; }
}
'''


def fixture():
    return dict(phase='PLAY', status="Driver A's turn...", cols=35, rows=20, current=0,
                turn=0, laps=1, selected=-1, ok=False, undo=True, ready=True,
                left=[[3, 5], [30, 5]], right=[[3, 12], [30, 12]], finish=[[30, 5], [30, 12]],
                starts=[[4, 8]], startZone=None, checkpoints=None, closures=None, shape=[], prePath=[], messages=[],
                players=[dict(name='Driver ' + ch, number=i + 1, kind='HUMAN', color=col, position=[5+i, 8],
                              velocity=[1, 0], history=[[5+i, 8]], traceStart=0, place=0, lap=0, outcome='')
                         for i, (ch, col) in enumerate([('A', '#0000ff'), ('B', '#ff0000')])],
                moves=[dict(index=i, legal=i != 0, position=[5 + i % 3, 7 + i // 3], velocity=[i % 3, i // 3 - 1],
                            finishes=False, lap=False, timeout=False) for i in range(9)])


def load(page, state=None):
    html = (WEB / 'index.html').read_text()
    html = re.sub(r'<link\b[^>]*>', '', html)
    html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.S)
    image = base64.b64encode((WEB / 'dist/icons/racing-192.png').read_bytes()).decode()
    html = html.replace('./icons/racing-192.png', 'data:image/png;base64,' + image)
    html = html.replace('</head>', '<style>' + (WEB / 'app.css').read_text() + '</style></head>')
    page.set_content(html)
    page.evaluate('(s) => { window.fixture=s; window.calls=[]; window.fetch=async()=>new Response(JSON.stringify(window.catalog)); }', state or fixture())
    page.evaluate('(catalog) => window.catalog=catalog', json.loads((WEB / 'dist/tracks.json').read_text()))
    controller = (WEB / 'app.js').read_text()
    controller = re.sub(r'^import .*;\n', '', controller, flags=re.M)
    # Only the test realm has about:blank; served HTTP and file guards stay tested
    # against the unmodified app in the real browser suite.
    controller = controller.replace("if (!/^https?:$/.test(location.protocol))", 'if (false)')
    controller = controller.replace('import.meta.url', "'https://example.invalid/TheoreticalRacing/app.js'")
    board = (WEB / 'board.js').read_text().replace('export class Board', 'class Board')
    page.add_script_tag(type='module', content=MOCK + '\n' + board + '\n' + (WEB / 'activity.js').read_text().replace('export class Activity', 'class Activity') + '\n' + controller)
    page.wait_for_function('!document.querySelector("#track").disabled')


def start(page):
    page.locator('#start').click()
    page.wait_for_function('document.body.dataset.phase === window.fixture.phase')
    page.wait_for_function('document.querySelector(".decision").getAttribute("aria-busy") === "false"')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', choices=['chromium', 'webkit'], default='chromium')
    args = parser.parse_args()
    out = WEB / 'build/browser-tests' / ('ui-' + args.browser)
    out.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        options = {'executable_path': os.environ['CHROMIUM_PATH']} if args.browser == 'chromium' and os.environ.get('CHROMIUM_PATH') else {}
        browser = getattr(p, args.browser).launch(**options)
        for width, height in [(1440, 1000), (390, 844), (320, 568), (844, 390), (768, 1024)]:
            page = browser.new_page(viewport={'width': width, 'height': height}, has_touch=width <= 844)
            page.on('pageerror', lambda e: errors.append(str(e)))
            load(page)
            page.screenshot(path=str(out / f'setup-{width}.png'), full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'setup page overflows {width}'
            assert page.locator('#setup').evaluate('(e)=>e.scrollWidth <= e.clientWidth'), f'setup content overflows {width}'
            for policy in ['legacy', 'informed']:
                page.locator('#ai-start-policy').select_option(policy)
                assert page.locator('#setup').evaluate('(e)=>e.scrollWidth <= e.clientWidth'), f'{policy} selector overflows {width}'
            page.locator('#track').select_option('')
            page.locator('#cols').fill('501')
            assert not page.locator('#setup-form').evaluate('(f)=>f.checkValidity()')
            page.locator('#track').select_option('hairpin')
            assert page.locator('#setup-form').evaluate('(f)=>f.checkValidity()'), 'hidden invalid custom dimensions block preset track'
            start(page)
            page.screenshot(path=str(out / f'race-{width}.png'), full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'race overflows {width}'
            for key, expected in [('Q', 0), ('w', 1), ('ArrowRight', 5), ('Numpad1', 6)]:
                page.locator('#confirm').focus()  # Native focused button must not swallow letter shortcuts.
                page.keyboard.press(key)
                page.wait_for_function('(index) => document.querySelector(`#moves button[data-index="${index}"]`).getAttribute("aria-pressed") === "true"', arg=expected)
            page.locator('#confirm').click()
            page.wait_for_function('document.body.dataset.turn === "1"')
            page.locator('#confirm').focus(); page.keyboard.press('u')
            page.wait_for_function('document.body.dataset.turn === "0"')
            # Editing an input never sends an acceleration; held-key repeat is ignored.
            page.locator('#new-race').click()
            before = page.evaluate('window.calls.length')
            page.locator('#seed').fill('123'); page.keyboard.press('ArrowUp')
            assert before == page.evaluate('window.calls.length')
            # Cancelling replacement preserves the live race, without tearing down its engine.
            page.once('dialog', lambda d: d.dismiss())
            page.locator('#start').click()
            assert page.locator('#setup').evaluate('(e)=>e.open')
            assert not page.evaluate('window.testEngine.dead')
            page.locator('#close-setup').click()
            page.locator('#install').click()
            assert page.locator('#installation').evaluate('(e)=>e.open')
            page.keyboard.press('Escape')
            assert not page.locator('#installation').evaluate('(e)=>e.open')
            # Long unbroken names must not expand the page beyond the viewport.
            page.evaluate("window.testEngine.state.players[0].name='A'.repeat(40)")
            page.locator('#moves button').nth(4).click()
            page.wait_for_function('document.querySelector("#driver").textContent.length === 40')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'long driver name overflows {width}'
            # Human, AI idle, AI work, a slow-work hint and warning must all keep
            # the board, pad, confirm button, standings and activity slot anchored.
            def layout():
                return page.evaluate("""() => Object.fromEntries(['#board','.track-panel','.decision','#moves','#confirm','.button-row','#standings','#work-status'].map(k => {
                  const r=document.querySelector(k).getBoundingClientRect();
                  return [k,[r.x+scrollX,r.y+scrollY,r.width,r.height]];
                }))""")
            baseline = layout()
            def stable(label):
                now = layout()
                for selector in baseline:
                    assert all(abs(a-b)<0.6 for a,b in zip(baseline[selector],now[selector])), (width,label,selector,baseline[selector],now[selector])
            page.locator('#pause').click()
            page.evaluate("window.testEngine.state.players[0].kind='AI2';window.testEngine.state.players[0].name='Computer';window.holdTick=true")
            page.locator('#moves button').nth(4).click()
            page.wait_for_function('document.querySelector("#confirm").textContent === "AI driving"')
            stable('AI idle')
            assert page.locator('#moves').is_visible() and page.locator('#confirm').is_disabled()
            page.locator('#step').click()
            page.wait_for_function('typeof window.releaseTick === "function"')
            stable('AI thinking')
            page.evaluate("document.querySelector('[data-work-slow]').hidden=false;window.testEngine.onStatus('',{stalled:true})")
            stable('AI slow warning')
            page.screenshot(path=str(out / f'stable-thinking-{width}.png'), full_page=True)
            page.locator('#keep-waiting').click(); stable('Continue waiting')
            page.evaluate("window.testEngine.state.players[0].kind='HUMAN';window.testEngine.state.players[0].name='Driver A';window.releaseTick();window.holdTick=false")
            page.wait_for_function('document.querySelector("#moves button").disabled === false')
            stable('Human again')
            (out / f'layout-{width}.json').write_text(json.dumps({'before':baseline,'after':layout(),'passed':True}, indent=2))
            # Starting a new race clears stale previous-race controls even during a slow boot.
            page.locator('#new-race').click(); page.evaluate('window.holdCreate=true')
            page.once('dialog', lambda d: d.accept()); page.locator('#start').click()
            assert page.locator('#moves').is_hidden() and page.locator('#export').is_disabled()
            assert page.locator('#standings li').count() == 0
            assert page.locator('#work-status').is_visible()
            assert page.locator('[data-work-progress]').get_attribute('value') is None
            page.evaluate("window.testEngine.onStatus('', {kind:'preparation',phase:'Checking safe continuations',done:40,total:100,unit:'scan',stage:5,stages:9})")
            assert page.locator('[data-work-progress]').get_attribute('value') == '0.4'
            assert '40% of this scan' in page.locator('[data-work-detail]').inner_text()
            assert page.locator('[data-preparation-progress]').get_attribute('value') == '5'
            assert page.locator('[data-preparation-progress]').get_attribute('max') == '9'
            assert page.locator('[data-preparation-stages] li').count() == 9
            assert page.locator('[data-preparation-stages] li[data-state="current"]').inner_text() == 'Driving maps'
            for total, index in [(7, 6), (11, 10)]:
                page.evaluate("""([total,index]) => window.testEngine.onStatus('', {
                    kind:'preparation', phase:'Analysing starting alternatives for all AIs',
                    done:2,total:4,unit:'scan',stage:index,stages:total})""", [total,index])
                assert page.locator('[data-preparation-stages] li').count() == total
                assert page.locator('[data-preparation-stages] li[data-state="current"]').inner_text() == 'Starting alternatives'
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'candidate stage overflows {width}'
            page.evaluate("window.testEngine.onStatus('', {stalled:true})")
            assert page.locator('[data-work-stalled]').is_visible()
            assert page.locator('#keep-waiting').is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'wait warning overflows {width}'
            page.screenshot(path=str(out / f'waiting-{width}.png'), full_page=True)
            page.locator('#keep-waiting').click()
            assert page.evaluate('window.keptWaiting && !window.testEngine.dead')
            assert page.locator('[data-work-stalled]').is_hidden()
            page.evaluate('window.releaseCreate()'); page.wait_for_function('document.body.dataset.phase === "PLAY"')
            page.evaluate("window.failNext='Simulated engine failure'")
            page.locator('#moves button').nth(4).click()
            page.wait_for_function('!document.querySelector("#notice").hidden')
            assert 'Simulated engine failure' in page.locator('#notice').inner_text()
            assert page.locator('#confirm').is_disabled()
            assert 'stopped' in page.locator('#status').inner_text()
            page.locator('#dismiss-notice').click(); assert page.locator('#notice').is_hidden()
            page.close()
        # Long AI work remains visible, indeterminate, timed, and cancellable.
        page = browser.new_page(viewport={'width':390,'height':844})
        load(page); start(page)
        page.locator('#pause').click()
        page.evaluate("window.testEngine.state.players[0].kind='AI2';window.holdTick=true")
        page.locator('#moves button').nth(4).click()
        page.locator('#step').click()
        assert page.locator('#work-status').is_visible()
        assert 'thinking' in page.locator('[data-work-label]').inner_text()
        assert page.locator('[data-work-progress]').get_attribute('value') is None
        page.wait_for_function('document.querySelector("[data-work-elapsed]").textContent !== "0s elapsed"')
        page.once('dialog', lambda d:d.accept())
        page.locator('#stop-work').click()
        assert page.evaluate('window.testEngine.dead') and page.locator('#work-status').is_hidden()
        assert page.locator('#setup').evaluate('(e)=>e.open')
        page.close()
        # The same original drawing phase index is a border index, not a driver index.
        page = browser.new_page(viewport={'width':390,'height':844})
        drawing = fixture(); drawing.update(phase='DRAWTRACK', current=1, ok=True)
        load(page, drawing); start(page)
        assert page.locator('#driver').inner_text() == 'Right border'
        before = page.evaluate('window.calls.length')
        page.locator('#place-x').fill(''); page.locator('#place-y').fill('5'); page.locator('#place').click()
        assert before == page.evaluate('window.calls.length'), 'empty coordinate silently became zero'
        page.locator('#place-x').fill('4'); page.locator('#place').click()
        page.wait_for_function('window.testEngine.state.lastClick?.[0] === 4')
        page.close()
        # A stale log reply must not download into or report an error in the replacement race.
        page = browser.new_page(); downloads = []; page.on('download', lambda d: downloads.append(d))
        s=fixture(); s['turn']=2
        load(page,s); start(page); page.locator('#export').click()
        page.wait_for_function('typeof window.releaseLog === "function"')
        page.locator('#new-race').click(); page.once('dialog',lambda d:d.accept()); page.locator('#start').click()
        page.wait_for_function('document.body.dataset.phase === "PLAY"'); page.evaluate("window.releaseLog('old log')")
        page.wait_for_timeout(100)
        assert not downloads, 'old session exported after replacement'
        page.close()
        browser.close()
    assert not errors, errors
    (out / 'result.json').write_text(json.dumps({'passed': True, 'browser': args.browser, 'viewports':5, 'mode':'isolated UI fixtures'}))
    print(args.browser + ': UI regressions passed at 5 viewport sizes')


if __name__ == '__main__':
    main()
