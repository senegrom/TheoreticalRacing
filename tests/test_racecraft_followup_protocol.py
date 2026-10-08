"""Policy-memory acceptance regressions for rc4 inside the bound cf4 protocol."""
import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import racecraft_validation as validation
import racecraft_corpus as corpus


def state(plan=None):
    identity = 'a' * 64
    header = f'rc3,0,1,0,0,0,{identity}' if plan is None else f'rc4,0,1,0,0,0,{identity},{plan}'
    return header + ';1,1,20,10,0,0,0,0,1,0,0,0,0,1;2,1,30,10,0,0,0,0,1,0,0,0,0,1'


class FollowupProtocolTests(unittest.TestCase):
    def test_old_empty_memory_format_remains_supported(self):
        self.assertEqual(validation.snapshot(state())[0][0], 0)
        self.assertEqual(corpus.board(state())[0][0], 'rc3')

    def test_complete_pending_memory_round_trip(self):
        text = state('SE~' + 'b' * 64 + '.-')
        row = corpus.parse_capture('RACECRAFT_STATE ' + text + '|E|W|E|E|W,E|W,E')[0]
        self.assertEqual(row['snapshot'], text)
        self.assertIn(text, validation.query(row, 100))

    def test_memory_is_bound_even_when_physical_board_is_identical(self):
        original = dict(actual='E', snapshot=state('SE~' + 'b' * 64 + '.-'), legalActions=['E'])
        changed = dict(original, snapshot=state('N~' + 'b' * 64 + '.-'))
        response = dict(schema=4, baseline='E', maxMoves=100,
                        requestSha256=hashlib.sha256(validation.query(original, 100).encode()).hexdigest())
        with self.assertRaisesRegex(ValueError, 'complete request'):
            validation.validate_response(changed, response, 100)
        with self.assertRaisesRegex(ValueError, 'complete request'):
            validation.validate_response(dict(original, snapshot=state()), response, 100)

    def test_invalid_memory_rejected(self):
        for plan in ('SE~x.-', 'JUMP~' + 'b' * 64 + '.-',
                     'SE~' + 'b' * 64, '-.-.-', 'SE~' + 'B' * 64 + '.-'):
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                validation.snapshot(state(plan))

    def test_capture_parser_uses_the_same_strict_memory_validation(self):
        with self.assertRaises(ValueError):
            corpus.parse_capture('RACECRAFT_STATE ' + state('SE~x.-') + '|E|W|E|E|W,E|W,E')


if __name__ == '__main__':
    unittest.main()
