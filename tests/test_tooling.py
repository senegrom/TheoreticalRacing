import contextlib
import importlib
import io
import os
from pathlib import Path
import struct
import tempfile
import types
import unittest
from unittest import mock

from tracks import oracle_roll
from tracks.forensics_common import (
    INF, LogMove, Reach, normalized_lines, normalized_sha256, parse_move, reconstruct_board,
)


class ForensicsCommonTests(unittest.TestCase):
    def test_forensic_entry_points_are_import_safe(self):
        modules = (
            'tracks.board_at', 'tracks.oracle_roll', 'tracks.needle_audit',
        )
        for module in modules:
            with self.subTest(module=module):
                importlib.import_module(module)

    def test_parse_move_exposes_behavior_fields(self):
        move = parse_move('12 p3 AI1 SW v(2,-1)>(1,0) (8,9)>(9,9) FINISH\n')
        self.assertIsNotNone(move)
        self.assertEqual(12, move.index)
        self.assertEqual(3, move.player)
        self.assertEqual('SW', move.direction)
        self.assertEqual((8, 9, 9, 9), (move.x, move.y, move.new_x, move.new_y))
        self.assertEqual('FINISH', move.status)
        self.assertIsNone(parse_move('# results\n'))

    def test_parse_move_splits_the_outcome_from_its_detail(self):
        timed_out = parse_move('40 p8 AI2 N v(0,-1)>(0,-2) (3,9)>(3,7) TIMEOUT place=8\n')
        self.assertIsNotNone(timed_out)
        self.assertEqual('TIMEOUT', timed_out.status)
        self.assertEqual(' place=8', timed_out.detail)
        crashed = parse_move('41 p2 AI1 E v(1,0)>(2,0) (3,9)>(5,9) CRASH place=8\n')
        self.assertEqual(('CRASH', ' place=8'), (crashed.status, crashed.detail))
        self.assertEqual('', parse_move('1 p1 AI1 E v(0,0)>(1,0) (1,2)>(2,2) ok\n').detail)
        lap = parse_move('2 p1 AI1 E v(1,0)>(1,0) (2,2)>(3,2) LAP 1/2\n')
        self.assertEqual(('LAP 1/2', ''), (lap.status, lap.detail))

    def test_normalized_log_projection_is_frozen(self):
        text = (
            'player1 name=A kind=AI1 start=1,2\n'
            '# Grid 150x150\n'
            '1 p1 AI2 E v(0,0)>(1,0) (1,2)>(2,2) ok\n'
        )
        expected = [
            'player1 name=A kind=AI start=1,2',
            '1 p1 AI E v(0,0)>(1,0) (1,2)>(2,2) ok',
        ]
        self.assertEqual(expected, normalized_lines(text))
        self.assertEqual(
            'd0d317c17a1bd9d4c5866595364ae12d24bcf4ee52a09dd2ce4218248475d782',
            normalized_sha256(text),
        )

    def test_oracle_verification_fails_on_a_truncated_observed_log(self):
        class FakeOracle:
            def ask(self, mover, cars):
                return 0, 0, 'XXXXAXXXX'

        cars = [(index, 0, 0, 0, 0) for index in range(8)]
        observed = [
            LogMove(
                index + 1, index + 1, 'NONE',
                0, 0, 0, 0, index, 0, index, 0, 'ok',
            )
            for index in range(8)
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(oracle_roll.verify(FakeOracle(), cars, 0, observed, 1))
            self.assertFalse(oracle_roll.verify(FakeOracle(), cars, 0, observed[:-1], 1))

    def test_reconstruct_board_reads_log_once_consistently(self):
        log_text = (
            '# checkpoints disabled\n'
            'player1 name=Driver One kind=AI1 start=1,2\n'
            'player2 name=B kind=AI2 start=5,6\n'
            '1 p1 AI1 E v(0,0)>(1,0) (1,2)>(2,2) ok\n'
            '2 p2 AI2 N v(0,0)>(0,-1) (5,6)>(5,5) CRASH\n'
            '3 p1 AI1 NONE v(1,0)>(1,0) (2,2)>(3,2) ok\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'race.log'
            path.write_text(log_text, encoding='utf-8')
            cars, mover, moves = reconstruct_board(path, 2, player_count=2)

        self.assertEqual([(2, 2, 1, 0, 0), (5, 6, 0, 0, 0)], cars)
        self.assertEqual(1, mover)
        self.assertEqual([2, 3], [move.index for move in moves])

    def test_reconstruct_board_retires_a_timed_out_car(self):
        log_text = (
            '# checkpoints disabled\n'
            'player1 name=A kind=AI1 start=1,2\n'
            'player2 name=B kind=AI2 start=5,6\n'
            '1 p1 AI1 E v(0,0)>(1,0) (1,2)>(2,2) ok\n'
            '2 p2 AI2 N v(0,0)>(0,-1) (5,6)>(5,5) TIMEOUT place=2\n'
            '3 p1 AI1 NONE v(1,0)>(1,0) (2,2)>(3,2) ok\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'race.log'
            path.write_text(log_text, encoding='utf-8')
            cars, mover, moves = reconstruct_board(path, 3, player_count=2)

        self.assertEqual([(2, 2, 1, 0, 0), (5, 6, 0, 0, 90)], cars)
        self.assertEqual(0, mover)
        self.assertEqual([3], [move.index for move in moves])

    def test_reconstruct_board_rejects_a_missing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'race.log'
            path.write_text(
                '# checkpoints disabled\n'
                'player1 name=A kind=AI1 start=1,2\n'
                '1 p1 AI1 E v(0,0)>(1,0) (1,2)>(2,2) ok\n',
                encoding='utf-8',
            )
            with self.assertRaisesRegex(ValueError, 'move 2 was not found'):
                reconstruct_board(path, 2, player_count=1)

    def test_reach_validates_and_indexes_binary_dump(self):
        values = [INF] * 18  # width=2, height=1, velocity span=3
        values[12] = 7       # (x=1, y=0, vx=0, vy=-1)
        payload = struct.pack('<iii', 2, 1, 1) + struct.pack('<18i', *values)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reach.bin'
            path.write_bytes(payload)
            reach = Reach(path)
            self.assertEqual('<i', reach.VALUE.format)
            self.assertEqual(7, reach.turns(1, 0, 0, -1))
            self.assertIsNone(reach.turns(0, 0, 0, 0))
            self.assertIsNone(reach.turns(2, 0, 0, 0))
            self.assertIsNone(reach.turns(1, 0, 2, 0))

            path.write_bytes(payload + b'!')
            with self.assertRaisesRegex(ValueError, 'size mismatch'):
                Reach(path)

if __name__ == '__main__':
    unittest.main()
