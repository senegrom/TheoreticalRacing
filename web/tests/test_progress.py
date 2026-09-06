"""Output-only progress hooks must leave every engine expression intact."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/scripts'))
from instrument_progress import instrument, strip


class ProgressTests(unittest.TestCase):
    def test_original_engine_is_preserved(self):
        source = (ROOT / 'src/tr/logic/Reachability.java').read_text()
        generated = (ROOT / 'web/build/src/tr/logic/Reachability.java').read_text()
        self.assertEqual(generated, instrument(source))
        self.assertEqual(strip(generated), source)
        for name in ['RaceAi.java', 'MoveQueries.java', 'GateFixedPoint.java']:
            self.assertEqual((ROOT / 'src/tr/logic' / name).read_bytes(),
                             (ROOT / 'web/build/src/tr/logic' / name).read_bytes())

    def test_hooks_fail_closed_when_the_engine_changes(self):
        source = (ROOT / 'src/tr/logic/Reachability.java').read_text()
        with self.assertRaisesRegex(RuntimeError, 'drift'):
            instrument(source.replace('void computeDistMap()', 'void newDistMap()'))


if __name__ == '__main__':
    unittest.main()
