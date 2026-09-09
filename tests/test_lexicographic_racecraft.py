"""An earlier result must dominate every later pace or survival change."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'docs/experiments/round232/lexicographic.py'
spec = importlib.util.spec_from_file_location('racecraft_lexicographic', path)
lex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lex)


class LexicographicRacecraftTests(unittest.TestCase):
    def test_later_gains_do_not_buy_a_slower_winner(self):
        self.assertEqual(lex.compare((11, 12, 13), (10, 20, 30)), (1, 1))

    def test_equal_winner_permits_a_new_second_finish(self):
        self.assertEqual(lex.compare((10, 20, float('inf')),
                                     (10, float('inf'), float('inf'))), (-1, 2))

    def test_equal_prefix_permits_a_faster_third(self):
        self.assertEqual(lex.compare((10, 12, 15), (10, 12, 16)), (-1, 3))

    def test_earlier_improvement_can_outweigh_a_later_crash(self):
        self.assertEqual(lex.compare((9, float('inf')), (10, 11)), (-1, 1))

    def test_crash_moves_are_not_finish_times(self):
        row = dict(moves=[4, 10, 11], finish_order=[2])
        self.assertEqual(lex.vector(row), (10, float('inf'), float('inf')))

    def test_missing_results_tie(self):
        self.assertEqual(lex.compare((10, float('inf')), (10, float('inf'))), (0, None))


if __name__ == '__main__':
    unittest.main()
