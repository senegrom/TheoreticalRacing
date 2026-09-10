#!/usr/bin/env python3
"""Compare the external classifier with the actual Java referee after core compilation."""
import json
from pathlib import Path
import random
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tracks.cross_era import classify  # noqa: E402


def main():
    cases = ['XXXXXXX', 'FFFFFFF', 'FXFXFXF', 'AXXXXXXX', 'XAAAAAAAXXXXXX']
    rng = random.Random(7319)
    for _ in range(12):
        events = []
        while sum(c != 'A' for c in events) < 7:
            events.append(rng.choice('FXAA'))
        cases.append(''.join(events))
    for events in cases:
        class Current:
            def __init__(self):
                self.moves = 0

            def ask(self, index, cars):
                symbol = events[self.moves]
                self.moves += 1
                return 0, 0, 'XXXX' + symbol + 'XXXX'

        class Older:
            def ask(self, index, cars):
                return 0, 0, 'AAAAAAAAA'

        oracle = Current()
        places, _ = classify(oracle, Older(), [(n, 0) for n in range(8)], {0, 2, 4, 6})
        result = subprocess.run(
            ['java', '-Djava.awt.headless=true', '-cp', str(ROOT / 'test-bin'),
             'tr.logic.CrossEraRefereeFixture', events],
            cwd=ROOT, capture_output=True, text=True, timeout=30, check=True,
        )
        native = re.search(r'^CLASSIFICATION=(\[.*\])$', result.stdout, re.MULTILINE)
        turns = re.search(r'^COMMITTED_TURNS=(\d+)$', result.stdout, re.MULTILINE)
        if native is None or turns is None:
            raise AssertionError('Java fixture returned no classification: ' + result.stdout)
        if places != json.loads(native[1]) or oracle.moves != int(turns[1]):
            raise AssertionError('cross-era/live-referee mismatch for ' + events)
        print('%s: %s, %d committed moves; matches Java' % (events, places, oracle.moves))
    print('%d cross-era/live-referee differential cases passed' % len(cases))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
