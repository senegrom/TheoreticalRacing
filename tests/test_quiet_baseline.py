"""Contracts for the independent quiet-rule attribution comparator."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('quiet_baseline_regression', Path(__file__).with_name('quiet_baseline_regression.py'))
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class QuietBaselineTests(unittest.TestCase):
    def test_case_coverage(self):
        cases = MOD.cases()
        self.assertEqual(len(cases), 34)
        self.assertEqual(len({c['name'] for c in cases}), 34)
        self.assertEqual(sum(c['frozen'] for c in cases), 20)
        self.assertEqual({c['kind'] for c in cases if c['frozen']}, {'AI1', 'AI2'})
        self.assertTrue(any(c['track'] == 'monza' and c['seed'] == 145 for c in cases))

    def test_rejects_trajectory_difference_even_with_equal_result(self):
        left = '1 p1 AI2 N v(0,0)\n# results\n1. A\n2. B\n'
        right = left.replace('AI2 N', 'AI2 E')
        with self.assertRaisesRegex(AssertionError, 'at line 1'):
            MOD.require_same(left, right, 'changed action')

    def test_rejects_missing_action(self):
        with self.assertRaises(AssertionError):
            MOD.require_same('1 p1 AI2 N\n2 p2 AI2 S\n', '1 p1 AI2 N\n', 'truncated')

    def test_ignores_only_nonbehavioral_headers(self):
        MOD.require_same('# build a\n1 p1 AI2 N\n# results\n1. A\n',
                         '# build b\n1 p1 AI2 N\n# results\n1. A\n', 'headers')

    def test_refuses_changed_classification(self):
        with self.assertRaises(AssertionError):
            MOD.require_same('# results\n1. A\n2. B\n', '# results\n1. B\n2. A\n', 'places')


if __name__ == '__main__':
    unittest.main()
