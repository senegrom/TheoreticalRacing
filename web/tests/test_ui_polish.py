#!/usr/bin/env python3
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1]


class UiPolishContracts(unittest.TestCase):
    def test_setup_focus_and_cache_bust(self):
        html = (WEB / 'index.html').read_text()
        self.assertIn('id="setup-title" tabindex="-1" autofocus', html)
        self.assertIn('href="./app.css?v=8"', html)

    def test_responsive_setup_and_idle_state_are_explicit(self):
        css = (WEB / 'app.css').read_text()
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
