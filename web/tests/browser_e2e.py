#!/usr/bin/env python3
"""Real-browser checks, including a full CheerpJ race against an existing golden.

The UI-only mode does not start the JVM; it is not a substitute for runtime tests.
"""
import argparse
import functools
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from golden_races import normalized_log  # noqa: E402


sys.path.insert(0, str(ROOT / 'web'))
from serve import RangeHandler  # noqa: E402


class QuietHandler(RangeHandler):
    def log_message(self, fmt, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', choices=['chromium', 'webkit'], default='chromium')
    parser.add_argument('--ui-only', action='store_true')
    parser.add_argument('--url', help='Test an already deployed site instead of the local build')
    args = parser.parse_args()
    out = ROOT / 'web/build/browser-tests' / args.browser
    out.mkdir(parents=True, exist_ok=True)
    server = None
    if args.url:
        url = args.url.rstrip('/') + '/'
    else:
        server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / 'web')))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}/dist/'
    mobile = args.browser == 'webkit'
    messages, errors = [], []
    with sync_playwright() as p:
        browser = getattr(p, args.browser).launch()
        context = browser.new_context(viewport={'width': 390 if mobile else 1440, 'height': 844 if mobile else 1000}, has_touch=mobile, is_mobile=mobile, accept_downloads=True)
        page = context.new_page()
        page.on('console', lambda m: messages.append(f'{m.type}: {m.text}'))
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('requestfailed', lambda r: messages.append(f'FAILED {r.url}: {r.failure}'))
        page.set_default_timeout(30_000)
        try:
            page.goto(url)
            # Decode the real HTTP PNGs, including all Apple and manifest sizes.
            icons = page.evaluate("""async () => {
              const manifestLink = document.querySelector('link[rel=manifest]');
              const response = await fetch(manifestLink.href);
              if (!response.ok) throw new Error('Manifest is not served');
              const manifest = await response.json();
              if (manifest.id !== '/TheoreticalRacing/' || manifest.display !== 'standalone') throw new Error('Wrong installed-app identity');
              if (document.querySelector('meta[name=apple-mobile-web-app-capable]')?.content !== 'yes') throw new Error('Missing Apple standalone metadata');
              const links = [...document.querySelectorAll('link[rel=apple-touch-icon], link[rel=icon][type="image/png"]')].map(e => ({src:e.href, sizes:e.sizes.value}));
              for (const icon of manifest.icons) links.push({...icon, src:new URL(icon.src, manifestLink.href).href});
              return await Promise.all(links.map(async ({src,sizes}) => {
                if (!src.startsWith(new URL('./', location.href).href)) throw new Error('Icon escaped repository path');
                const image = new Image(); image.src=src; await image.decode();
                if (`${image.naturalWidth}x${image.naturalHeight}` !== sizes) throw new Error('Wrong image dimensions');
                return {src, sizes};
              }));
            }""")
            assert len(icons) == 8, 'Apple, browser or manifest icon missing'
            ico = page.request.get(url.rstrip('/') + '/favicon.ico?v=2')
            assert ico.ok and ico.body()[:6] == bytes([0, 0, 1, 0, 3, 0]), 'ICO fallback is not served'
            page.wait_for_function('document.querySelector("#setup").open')
            page.locator('#close-setup').click()
            page.locator('#install').click()
            assert page.locator('#installation').is_visible()
            page.locator('#close-install').click()
            page.locator('#new-race').click()
            page.wait_for_function('!document.querySelector("#track").disabled')
            assert page.locator('#track option').count() == 85, 'missing original tracks or custom drawing'
            assert page.locator('#setup').evaluate('(d) => d.open')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal page overflow'
            page.locator('#track').select_option('')
            assert page.locator('#setup-form').evaluate('(f) => f.checkValidity()'), 'custom-track option invalidates setup'
            page.locator('#track').select_option('hairpin')
            page.locator('#player-count').fill('2')
            for i, row in enumerate(page.locator('.roster-row').all()):
                row.locator('select').select_option('AI2')
                row.locator('[data-name]').fill(chr(65 + i))
            page.locator('#seed').fill('1')
            page.screenshot(path=str(out / 'setup.png'), full_page=True)
            if not args.ui_only:
                page.locator('#speed').select_option('0')
                page.locator('#start').click()
                page.wait_for_function('document.body.dataset.phase === "PLACEPLAYERS" || document.querySelector("#status").textContent.includes("could not start")', timeout=300_000)
                assert page.locator('body').get_attribute('data-phase') == 'PLACEPLAYERS', page.locator('#notice').inner_text()
                page.wait_for_function('!document.querySelector("#ok").disabled', timeout=600_000)
                page.locator('#ok').click()
                page.wait_for_function('document.body.dataset.phase === "FINISHED"', timeout=600_000)
                assert page.locator('body').get_attribute('data-turn') == '33', 'wrong golden race length'
                with page.expect_download() as downloaded:
                    page.locator('#export').click()
                target = out / 'hairpin-s1-2p.log'
                downloaded.value.save_as(target)
                digest = hashlib.sha256(normalized_log(target.read_text()).encode()).hexdigest()
                fixture = next(c for c in json.loads((ROOT / 'tests/golden_races.json').read_text())['cases'] if c['name'] == 'hairpin-s1-2p')
                assert digest == fixture['sha256'], f'Browser JVM differs from original golden: {digest}'
                page.screenshot(path=str(out / 'finished.png'), full_page=True)
                print(f'{args.browser}: real Java golden race matched {digest}', flush=True)
                # A new iframe must not receive events or callbacks from the old race.
                page.locator('#new-race').click()
                for row in page.locator('.roster-row').all():
                    row.locator('select').select_option('HUMAN')
                page.locator('#start').click()
                page.wait_for_function('document.body.dataset.phase === "PLACEPLAYERS"', timeout=300_000)
                page.locator('#first-start').click()
                page.wait_for_function('document.querySelector("#driver").textContent === "B"')
                page.locator('#first-start').click()
                page.wait_for_function('document.querySelector("#placement").hidden')
                page.wait_for_function('!document.querySelector("#ok").disabled && !document.querySelector("#ok").hidden', timeout=600_000)
                page.locator('#ok').click()
                page.wait_for_function('document.body.dataset.phase === "PLAY"')
                if mobile:
                    page.evaluate('scrollTo(0, 0)')
                    box = page.locator('#confirm').bounding_box()
                    assert box and box['y'] + box['height'] <= page.evaluate('innerHeight'), 'phone driving controls fall below the first screen'
                legal = page.locator('#moves button[data-legal="true"]').first
                legal.click(); legal.click()
                assert page.locator('body').get_attribute('data-turn') == '0', 'preview committed move'
                page.wait_for_function('!document.querySelector("#confirm").disabled')
                if mobile:
                    page.locator('#confirm').tap()
                else:
                    page.keyboard.press('Enter')
                page.wait_for_function('document.body.dataset.turn === "1"')
                page.locator('#undo').click()
                page.wait_for_function('document.body.dataset.turn === "0"')
                page.screenshot(path=str(out / 'human.png'), full_page=True)
                print(f'{args.browser}: placement, repeated preview, confirmation, undo and session replacement OK', flush=True)
                page.locator('#new-race').click()
                page.locator('#track').select_option('')
                page.locator('#player-count').fill('1')
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#start').click()
                page.wait_for_function('document.body.dataset.phase === "START"', timeout=300_000)
                page.locator('#ok').click()
                page.wait_for_function('document.body.dataset.phase === "DRAWTRACK"')
                for x, y in [(5, 5), (30, 5)]:
                    page.locator('#place-x').fill(str(x)); page.locator('#place-y').fill(str(y))
                    page.locator('#place').click()
                    page.wait_for_function('!document.querySelector("#place").disabled')
                page.locator('#ok').click()
                page.wait_for_function('document.querySelector("#ok").textContent.includes("Complete")')
                for x, y in [(5, 10), (30, 10)]:
                    page.locator('#place-x').fill(str(x)); page.locator('#place-y').fill(str(y))
                    page.locator('#place').click()
                    page.wait_for_function('!document.querySelector("#place").disabled')
                page.locator('#ok').click()
                page.wait_for_function('document.body.dataset.phase === "PLACEPLAYERS"')
                page.screenshot(path=str(out / 'custom-track.png'), full_page=True)
                print(f'{args.browser}: custom circuit drawing completed through the original validator', flush=True)
            assert not errors, errors
            (out / 'result.json').write_text(json.dumps({'browser': args.browser, 'ui_only': args.ui_only, 'passed': True}))
        finally:
            (out / 'console.log').write_text('\n'.join(messages))
            (out / 'errors.json').write_text(json.dumps(errors, indent=2))
            page.screenshot(path=str(out / 'last-state.png'), full_page=True)
            (out / 'last-state.html').write_text(page.content())
            browser.close()
            if server:
                server.shutdown()
                server.server_close()
    print(f'{args.browser}: passed', flush=True)


if __name__ == '__main__':
    main()
