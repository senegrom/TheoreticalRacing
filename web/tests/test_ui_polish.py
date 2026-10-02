#!/usr/bin/env python3
import hashlib
import re
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]


class UiPolishContracts(unittest.TestCase):
    def test_setup_focus_and_cache_bust(self):
        html = (WEB / 'index.html').read_text(encoding='utf-8')
        self.assertIn('id="setup-title" tabindex="-1" autofocus', html)
        # Sources carry the placeholder only: the build stamps content hashes.
        for source in ('index.html', 'app.js', 'engine.js', 'activity.js', 'board.js', 'runtime.js'):
            for value in re.findall(r'\?v=([A-Za-z0-9]+)', (WEB / source).read_text(encoding='utf-8')):
                self.assertEqual('0', value, source)

    @unittest.skipUnless((WEB / 'dist/index.html').exists(), 'needs web/build.sh output')
    def test_every_published_version_is_its_targets_hash(self):
        dist = WEB / 'dist'
        for page in dist.iterdir():
            if page.suffix not in ('.html', '.js', '.css', '.webmanifest'):
                continue
            for name, value in re.findall(r'([A-Za-z0-9_.-]+)\?v=([A-Za-z0-9]+)', page.read_text(encoding='utf-8')):
                self.assertEqual(hashlib.sha256((dist / name).read_bytes()).hexdigest()[:12], value,
                                 f'{page.name} -> {name}')

    def test_responsive_setup_and_idle_state_are_explicit(self):
        css = (WEB / 'app.css').read_text(encoding='utf-8')
        for contract in [
            '/* 2026-09 responsive setup and chrome polish. */',
            'body[data-phase="PLAY"] .work-status[data-active="false"]',
            '@media(max-width:900px)',
            '#setup .setup-grid',
            '#setup #start',
            '.decision.driving .speed-label select',
        ]:
            self.assertIn(contract, css)


if __name__ == '__main__':
    unittest.main()
