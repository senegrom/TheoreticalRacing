import contextlib
import importlib
import io
from pathlib import Path
import struct
import tempfile
import unittest

from tracks import bench_ai, oracle_roll
from tracks.forensics_common import INF, LogMove, Reach, parse_move, reconstruct_board


class BenchmarkCliTests(unittest.TestCase):
    def test_defaults_to_regular_self_play(self):
        args = bench_ai.parse_cli([])
        self.assertEqual('self-play', args.mode)
        self.assertEqual(bench_ai.DEFAULT_TRACKS, args.tracks)
        self.assertEqual([None], args.seed_values)

    def test_four_player_aliases_are_equivalent(self):
        canonical = bench_ai.parse_cli(['--4p', '--seeds', '2', 'sprint'])
        alias = bench_ai.parse_cli(['--2v2', '--seeds', '2', 'sprint'])
        self.assertEqual('4p', canonical.mode)
        self.assertEqual(canonical.mode, alias.mode)
        self.assertEqual([1, 2], canonical.seed_values)
        self.assertEqual(canonical.seed_values, alias.seed_values)
        self.assertEqual(['sprint'], alias.tracks)

    def test_seed_range_and_slow_field_mode(self):
        args = bench_ai.parse_cli(
            ['--h2h', '--slow', '--seeds', '3', '--seed-start', '6']
        )
        self.assertEqual('h2h', args.mode)
        self.assertEqual(bench_ai.SLOW_TRACKS, args.tracks)
        self.assertEqual([6, 7, 8], args.seed_values)

    def test_seed_start_requires_count(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                bench_ai.parse_cli(['--seed-start', '2'])
        self.assertEqual(2, raised.exception.code)

    def test_modes_are_mutually_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                bench_ai.parse_cli(['--h2h', '--1v1'])
        self.assertEqual(2, raised.exception.code)

    def test_seed_values_must_be_positive(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                bench_ai.parse_cli(['--seeds', '0'])
        self.assertEqual(2, raised.exception.code)


class ForensicsCommonTests(unittest.TestCase):
    def test_forensic_entry_points_are_import_safe(self):
        for module in ('tracks.board_at', 'tracks.oracle_roll', 'tracks.policy_matrix'):
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

    def test_reconstruct_board_rejects_a_missing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'race.log'
            path.write_text(
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
            self.assertEqual(7, reach.turns(1, 0, 0, -1))
            self.assertIsNone(reach.turns(0, 0, 0, 0))
            self.assertIsNone(reach.turns(2, 0, 0, 0))
            self.assertIsNone(reach.turns(1, 0, 2, 0))

            path.write_bytes(payload + b'!')
            with self.assertRaisesRegex(ValueError, 'size mismatch'):
                Reach(path)


if __name__ == '__main__':
    unittest.main()
