"""Failure-injection tests for trustworthy fleet results and complete replay."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tracks import fleet_grid, oracle_roll
from tracks.forensics_common import (
    CandidateMask, LogMove, ReplayBoard, Transition, parse_v2_answer, reconstruct_board,
)

ROOT = Path(__file__).resolve().parents[1]
FAKE_JAVA = r'''#!__PYTHON__
import os, re, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ['FLEET_TEST_CALLS'], 'a') as stream:
    stream.write('called\n')
mode = Path(os.environ['FLEET_TEST_MODE']).read_text().strip()
if mode == 'mutate':
    Path(args[args.index('--props') + 1]).write_text('changed during run')
if mode == 'fail-no-loop':
    print('[laps] track boundary too coarse for gates -- laps disabled')
if mode.startswith('fail'):
    sys.exit(17)
lo, hi = map(int, re.fullmatch(r'(-?\d+)-(-?\d+)', args[args.index('--seed') + 1]).groups())
base = Path(args[args.index('--log') + 1])
for seed in range(lo, hi + 1):
    if mode == 'missing' and seed == hi:
        continue
    text = ('player1 name=FINISH CRASH TIMEOUT kind=AI1 start=1,1\n'
            'player2 name=B kind=AI2 start=2,1\n'
            '# turns: turn player kind dir vBefore vAfter pos newPos outcome\n'
            '1 p1 AI1 E v(0,0)>(1,0) (1,1)>(2,1) FINISH place=1\n')
    if mode != 'partial':
        text += '# results\n1. FINISH CRASH TIMEOUT\n2. B\n'
    (base.parent / (base.stem + '_s%d' % seed + base.suffix)).write_text(text)
if mode == 'no-loop':
    print('[laps] track boundary too coarse for gates -- laps disabled')
'''


class FleetRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.out = self.work / 'out'
        self.jar = self.work / 'race.jar'
        self.jar.write_bytes(b'build-one')
        self.props = self.work / 'race.properties'
        self.props.write_text('nPlayers=2\nlaps=3\n')
        self.track = self.work / 'tracks' / 'test.track'
        self.track.parent.mkdir()
        self.track.write_text('fixture')
        self.java = self.work / 'java'
        self.java.write_text(FAKE_JAVA.replace('__PYTHON__', sys.executable))
        self.java.chmod(0o755)
        self.mode = self.work / 'mode'
        self.mode.write_text('success')
        self.calls = self.work / 'calls'
        self.env = dict(os.environ, RACING_JAR=str(self.jar), RACING_JAVA=str(self.java),
                        RACING_PROPS=str(self.props), RACING_TRACKS='test', RACING_HEAP='-Xmx1g',
                        RACING_TIMEOUT='10', FLEET_TEST_MODE=str(self.mode), FLEET_TEST_CALLS=str(self.calls))

    def run_grid(self, seeds='1', jobs='1'):
        return subprocess.run([sys.executable, str(ROOT / 'tracks/fleet_grid.py'), seeds, jobs, str(self.out)],
                              env=self.env, capture_output=True, text=True, timeout=20)

    def count(self):
        return len(self.calls.read_text().splitlines()) if self.calls.exists() else 0

    def test_failed_java_is_nonzero_and_retryable_even_with_stale_log(self):
        self.mode.write_text('fail')
        first = self.run_grid()
        self.assertNotEqual(0, first.returncode)
        self.assertIn('unusable=1', first.stdout)
        # An old plausible log outside the isolated attempt must never be accepted.
        (self.out / 'test_s1.log').write_text('old log FINISH\n# results\n')
        second = self.run_grid()
        self.assertNotEqual(0, second.returncode)
        self.assertEqual(2, self.count())
        self.mode.write_text('success')
        third = self.run_grid()
        self.assertEqual(0, third.returncode, third.stderr)
        self.assertIn('races=1 crashes=0 timeouts=0 moves=1 unusable=0', third.stdout)
        self.assertEqual(3, self.count())

    def test_partial_and_missing_results_are_not_completed(self):
        for mode in ('partial', 'missing', 'fail-no-loop'):
            with self.subTest(mode=mode):
                self.mode.write_text(mode)
                result = self.run_grid('1-2')
                self.assertNotEqual(0, result.returncode)
                self.assertFalse((self.out / 'test.complete.json').exists())
        self.assertEqual(3, self.count())

    def test_successful_resume_skips_java_but_ignores_unrelated_rows(self):
        self.assertEqual(0, self.run_grid().returncode)
        (self.out / 'unrelated.row').write_text('unrelated 1 fin=9 crash=90 timeout=0 moves=999\n')
        self.mode.write_text('fail')
        result = self.run_grid()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(1, self.count())
        self.assertNotIn('unrelated', (self.out / 'fleet.txt').read_text())
        self.assertIn('crashes=0', result.stdout)

    def test_seed_change_rejects_resume_before_running_java(self):
        self.assertEqual(0, self.run_grid().returncode)
        before = (self.out / 'fleet.txt').read_text()
        changed = self.run_grid('11-20')
        self.assertEqual(2, changed.returncode)
        self.assertIn('manifest differs', changed.stderr)
        self.assertEqual(1, self.count())
        self.assertEqual(before, (self.out / 'fleet.txt').read_text())

    def test_changed_build_profile_track_and_runtime_are_rejected(self):
        self.assertEqual(0, self.run_grid().returncode)
        for path in (self.jar, self.props, self.track, self.java):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b'\n# changed\n')
                self.assertEqual(2, self.run_grid().returncode)
                path.write_bytes(original)
        self.assertEqual(1, self.count())

    def test_corrupt_completed_log_is_retried_not_trusted(self):
        self.assertEqual(0, self.run_grid().returncode)
        (self.out / 'test_s1.log').write_text('truncated')
        self.mode.write_text('fail')
        self.assertNotEqual(0, self.run_grid().returncode)
        self.assertEqual(2, self.count())

    def test_singleton_uses_batch_names_and_outcome_grammar(self):
        result = self.run_grid('7')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue((self.out / 'test_s7.log').exists())
        self.assertEqual('test 7 fin=1 crash=0 timeout=0 moves=1\n', (self.out / 'fleet.txt').read_text())

    def test_mid_run_input_change_invalidates_completion_markers(self):
        self.mode.write_text('mutate')
        result = self.run_grid()
        self.assertEqual(2, result.returncode)
        self.assertIn('inputs changed during', result.stderr)
        self.assertFalse((self.out / 'test.complete.json').exists())

    def test_legacy_unmanifested_directory_fails_closed(self):
        self.out.mkdir()
        (self.out / 'test.row').write_text('test 1 MISSING\n')
        self.assertEqual(2, self.run_grid().returncode)
        self.assertEqual(0, self.count())

    def test_no_loop_is_accepted_only_after_successful_complete_races(self):
        self.mode.write_text('no-loop')
        result = self.run_grid('1-2')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('test NOLOOP\n', (self.out / 'fleet.txt').read_text())
        self.assertEqual(0, self.run_grid('1-2').returncode)
        self.assertEqual(1, self.count())

    def test_directory_lock_prevents_overlapping_runs(self):
        self.out.mkdir()
        with fleet_grid.directory_lock(self.out):
            result = self.run_grid()
        self.assertEqual(2, result.returncode)
        self.assertIn('another fleet run', result.stderr)
        self.assertEqual(0, self.count())

    def test_invalid_arguments_do_not_launch_java(self):
        for seeds, jobs in (('9-1', '1'), ('1', '0'), ('9223372036854775808', '1')):
            self.assertNotEqual(0, self.run_grid(seeds, jobs).returncode)
        self.assertEqual(0, self.count())

    def test_seed_range_supports_signed_longs(self):
        self.assertEqual((-5, -1), fleet_grid.seed_range('-5--1'))
        self.assertEqual((7, 7), fleet_grid.seed_range('7'))


class ExactReplayTests(unittest.TestCase):
    @staticmethod
    def verify(symbol, observed, *, cars=None):
        class FakeOracle:
            def ask(self, mover, board):
                return 0, 0, 'XXXX' + symbol + 'XXXX'
        if cars is None:
            cars = [(1, 2, 1, 0, 0), (4, 2, 0, 0, 0), (5, 2, 0, 0, 0)]
        with contextlib.redirect_stdout(io.StringIO()):
            return oracle_roll.verify(FakeOracle(), cars, 0, observed, 1)

    @staticmethod
    def move(status='FINISH', **changes):
        fields = dict(index=1, player=1, direction='NONE', old_vx=1, old_vy=0,
                      new_vx=1, new_vy=0, x=1, y=2, new_x=2, new_y=2, status=status)
        fields.update(changes)
        return LogMove(**fields)

    def test_finish_is_not_crash_or_timeout(self):
        self.assertFalse(self.verify('F', [self.move('CRASH')]))
        self.assertFalse(self.verify('X', [self.move('FINISH')]))
        self.assertFalse(self.verify('F', [self.move('TIMEOUT')]))

    def test_positions_and_velocities_must_match(self):
        for changes in ({'new_x': 77}, {'new_vx': 7}, {'x': 0}, {'old_vy': 2}):
            self.assertFalse(self.verify('F', [self.move(**changes)]))

    def test_last_survivor_matches_engine_termination(self):
        cars = [(1, 2, 1, 0, 0), (4, 2, 0, 0, 0)]
        self.assertTrue(self.verify('F', [self.move()], cars=cars))
        self.assertFalse(self.verify('F', [self.move(), self.move('ok', index=2, player=2)], cars=cars))

    def test_empty_or_zero_length_window_cannot_claim_exact_match(self):
        self.assertFalse(self.verify('A', []))
        with self.assertRaises(ValueError):
            oracle_roll.verify(None, [(1, 1, 0, 0, 0)], 0, [], 0)

    def test_v2_nonfinal_crossing_preserves_clock_and_progress(self):
        board = ReplayBoard([(59, 5, 1, 0, 0, 0, 0), (10, 5, 0, 0, 0, 0, 1)],
                            laps=3, turns=42, complete=True)
        mask = CandidateMask('AAAAAAAAA', [Transition('LAP', 1, 1, 0)] * 9, 3)
        updated, fate = oracle_roll.apply_move(board, 0, 0, 0, mask)
        self.assertEqual('LAP 1/3', fate)
        self.assertEqual((60, 5, 1, 0, 0, 1, 1), updated[0])
        self.assertEqual((43, 3, True), (updated.turns, updated.laps, updated.complete))
        self.assertEqual(42, board.turns)
        self.assertEqual(0, board[0][5])

    def test_complete_replay_refuses_legacy_mask(self):
        board = ReplayBoard([(1, 1, 0, 0, 0, 0, 1)], complete=True)
        with self.assertRaises(ValueError):
            oracle_roll.apply_move(board, 0, 0, 0, 'AAAAAAAAA')

    def test_v2_reply_is_strictly_validated(self):
        payload = 'v2;0,0;AAAAAAAAA;' + '|'.join(['OK,0,1,0'] * 9)
        dx, dy, mask = parse_v2_answer(payload, 3)
        self.assertEqual((0, 0), (dx, dy))
        self.assertEqual(Transition('OK', 0, 1, 0), mask.transitions[4])
        for invalid in (payload + '|OK,0,1,0', payload.replace('AAAAAAAAA', 'FFFFFFFFF'),
                        payload.replace('OK,0,1,0', 'OK,0,7,0', 1)):
            with self.assertRaises(ValueError):
                parse_v2_answer(invalid, 3)

    def test_complete_reconstruction_preserves_laps_checkpoints_and_retirement(self):
        text = ('# laps 3\n'
                'player1 name=A kind=AI1 start=1,2\n'
                'player2 name=B kind=AI2 start=5,6\n'
                'player3 name=C kind=AI1 start=7,8\n'
                '1 p1 AI1 E v(0,0)>(1,0) (1,2)>(2,2) ok cp1\n'
                '2 p1 AI1 NONE v(1,0)>(1,0) (2,2)>(3,2) ok cp2\n'
                '3 p1 AI1 NONE v(1,0)>(1,0) (3,2)>(4,2) LAP 1/3\n'
                '4 p2 AI2 N v(0,0)>(0,-1) (5,6)>(5,5) CRASH place=3\n'
                '5 p1 AI1 NONE v(1,0)>(1,0) (4,2)>(5,2) ok cp1\n'
                '6 p3 AI1 NONE v(0,0)>(0,0) (7,8)>(7,8) ok\n')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'race.log'
            path.write_text(text)
            board, mover, real = reconstruct_board(path, 6, 3, complete=True)
            self.assertEqual((5, 2, 1, 0, 0, 1, 2), board[0])
            self.assertEqual((-100000, -100000, 0, 0, 99, 0, 1), board[1])
            self.assertEqual((5, 3, 2, 1), (board.turns, board.laps, mover, len(real)))
            with self.assertRaises(ValueError):
                reconstruct_board(path, 6, 3)


if __name__ == '__main__':
    unittest.main()
