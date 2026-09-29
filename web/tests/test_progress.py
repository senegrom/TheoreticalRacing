"""Output-only progress hooks must leave every engine expression intact."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/scripts'))
from instrument_progress import instrument, instrument_game, instrument_optimal, instrument_placement, strip
from startup_schedule import adapt


class ProgressTests(unittest.TestCase):
    def test_original_engine_is_preserved(self):
        source = (ROOT / 'src/tr/logic/Reachability.java').read_text()
        generated = (ROOT / 'web/build/src/tr/logic/Reachability.java').read_text()
        self.assertEqual(generated, instrument(adapt("Reachability.java", source)))
        self.assertEqual(adapt("Reachability.java", strip(generated), reverse=True), source)
        original = (ROOT / 'src/tr/logic/OptimalPotential.java').read_text()
        generated_optimal = (ROOT / 'web/build/src/tr/logic/OptimalPotential.java').read_text()
        self.assertEqual(generated_optimal, instrument_optimal(original))
        self.assertEqual(strip(generated_optimal), original)
        placement = (ROOT / 'src/tr/logic/StartPlacement.java').read_text()
        generated_placement = (ROOT / 'web/build/src/tr/logic/StartPlacement.java').read_text()
        self.assertEqual(generated_placement, instrument_placement(placement))
        self.assertEqual(strip(generated_placement), placement)
        for name in ['RaceAi.java', 'MoveQueries.java', 'GateFixedPoint.java']:
            self.assertEqual((ROOT / 'src/tr/logic' / name).read_bytes(),
                             (ROOT / 'web/build/src/tr/logic' / name).read_bytes())

    def test_distance_scheduling_is_reversible_and_keeps_map_order(self):
        for name in ['RaceGame.java', 'Reachability.java']:
            source = (ROOT / 'src/tr/logic' / name).read_text()
            scheduled = adapt(name, source)
            self.assertEqual(adapt(name, scheduled, reverse=True), source)
            with self.assertRaisesRegex(RuntimeError, 'drift'):
                adapt(name, source.replace('reach.startReachabilityCompute();' if name == 'RaceGame.java' else 'final Thread t = new Thread', 'changed'))
        source = (ROOT / 'src/tr/logic/RaceGame.java').read_text()
        self.assertEqual(strip(instrument_game(source)), source)

    def test_the_daemon_shows_the_exact_map_stage(self):
        # Review, 2026-09-29: stage 9 was current only when the map built on
        # the daemon's own thread; the daemon now announces it where it waits.
        generated = instrument((ROOT / 'src/tr/logic/Reachability.java').read_text())
        head = 'if (!game.dumpsReachOnly()) { // a reach dump exits: no race follows\n'
        hook = generated[generated.index(head) + len(head):].splitlines()[0]
        self.assertIn('tr.browser.Progress.exactMap();', hook)

    def test_hooks_fail_closed_when_the_engine_changes(self):
        source = (ROOT / 'src/tr/logic/Reachability.java').read_text()
        with self.assertRaisesRegex(RuntimeError, 'drift'):
            instrument(source.replace('void computeDistMap()', 'void newDistMap()'))


if __name__ == '__main__':
    unittest.main()
