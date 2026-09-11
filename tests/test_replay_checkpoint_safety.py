"""A one-lap log can still owe checkpoint progress: never drop it implicitly."""
from pathlib import Path
import tempfile
import unittest

from tracks.forensics_common import normalized_sha256, reconstruct_board
from tracks.policy_matrix import board_at

STARTS = ('player1 name=Driver One kind=AI2 start=1,2\n'
          'player2 name=Driver Two kind=AI2 start=5,2\n')
MOVES = ('1 p1 AI2 E v(0,0)>(1,0) (1,2)>(2,2) ok cp1 cp2\n'
         '2 p2 AI2 E v(0,0)>(1,0) (5,2)>(6,2) ok\n'
         '3 p1 AI2 E v(1,0)>(2,0) (2,2)>(4,2) FINISH place=1\n')


class CheckpointReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / 'race.log'

    def write(self, header='', moves=MOVES, starts=STARTS):
        self.log.write_text(header + starts + moves, encoding='utf-8')
        return self.log

    def test_single_lap_v2_preserves_the_finish_gate(self):
        self.write('# checkpoints enabled\n')
        cars, mover, moves = reconstruct_board(self.log, 3, 2, complete=True)
        self.assertEqual(1, cars.laps)
        self.assertEqual((0, 0), cars[0][5:])
        self.assertEqual(0, mover)
        self.assertEqual('FINISH', moves[0].status)
        with self.assertRaisesRegex(ValueError, 'complete=True'):
            reconstruct_board(self.log, 3, 2)

    def test_checkpoint_log_rejected_even_before_any_checkpoint_event(self):
        self.write('# checkpoints enabled\n', MOVES.splitlines(True)[1].replace('2 p2', '1 p2'))
        with self.assertRaisesRegex(ValueError, 'complete=True'):
            reconstruct_board(self.log, 1, 2)

    def test_policy_matrix_rejects_one_lap_checkpoints(self):
        with self.assertRaisesRegex(ValueError, 'checkpoint'):
            board_at(self.write('# checkpoints enabled\n'), 3)

    def test_historical_log_still_has_complete_replay(self):
        self.write()
        cars, _, _ = reconstruct_board(self.log, 3, 2, complete=True)
        self.assertEqual(0, cars[0][6])
        with self.assertRaisesRegex(ValueError, 'complete=True'):
            reconstruct_board(self.log, 1, 2)

    def test_unclassified_historical_log_does_not_prove_absence_of_checkpoints(self):
        self.write('', MOVES.replace(' cp1 cp2', ''))
        with self.assertRaisesRegex(ValueError, 'unclassified historical'):
            reconstruct_board(self.log, 1, 2)

    def test_declared_ungated_race_keeps_legacy_support(self):
        self.write('# checkpoints disabled\n', MOVES.replace(' cp1 cp2', ''))
        cars, mover, _ = reconstruct_board(self.log, 3, 2)
        self.assertEqual((2, 2, 1, 0, 0), cars[0])
        self.assertEqual(0, mover)

    def test_conflicting_progress_after_target_is_not_ignored(self):
        self.write('# checkpoints disabled\n')
        with self.assertRaisesRegex(ValueError, 'checkpoint'):
            reconstruct_board(self.log, 1, 2)

    def test_duplicate_and_malformed_checkpoint_headers_are_rejected(self):
        for header in ('# checkpoints disabled\n# checkpoints disabled\n',
                       '# checkpoints disabled\n# checkpoints enabled\n', '# checkpoints maybe\n'):
            with self.subTest(header=header):
                self.write(header, MOVES.replace(' cp1 cp2', ''))
                with self.assertRaisesRegex(ValueError, 'complete=True'):
                    reconstruct_board(self.log, 1, 2)

    def test_scattered_start_requires_full_progress(self):
        self.write('# checkpoints disabled\n# start-placement scatter\n', MOVES.replace(' cp1 cp2', ''))
        with self.assertRaisesRegex(ValueError, 'scattered'):
            reconstruct_board(self.log, 1, 2)
        self.write('# checkpoints disabled\n', MOVES.replace(' cp1 cp2', ''),
                   STARTS.replace('start=1,2', 'start=1,2 vel=0,0 gate=0'))
        with self.assertRaisesRegex(ValueError, 'start gate'):
            reconstruct_board(self.log, 1, 2)
        cars, _, _ = reconstruct_board(self.log, 1, 2, complete=True)
        self.assertEqual(0, cars[0][6], 'gate zero must not default to CP1')

    def test_multilap_guard_is_preserved(self):
        self.write('# laps 2\n# checkpoints disabled\n')
        with self.assertRaisesRegex(ValueError, 'multi-lap'):
            reconstruct_board(self.log, 1, 2)

    def test_metadata_does_not_refreeze_behavioral_goldens(self):
        text = STARTS + MOVES
        self.assertEqual(normalized_sha256(text), normalized_sha256('# checkpoints enabled\n' + text))


if __name__ == '__main__':
    unittest.main()
