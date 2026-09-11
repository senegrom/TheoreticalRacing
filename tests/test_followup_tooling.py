"""Regression contracts for uncached benchmarks and the legacy era referee."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tracks import bench_ai, cross_era, extract_baseline

STARTS = [(n, 0) for n in range(1, 9)]
SLOTS = {0, 2, 4, 6}


class UncachedBenchmarkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.jar = self.root / 'candidate.jar'
        self.jar.write_bytes(b'candidate')
        self.champion = self.root / 'champion' / 'champion.jar'
        self.champion.parent.mkdir()
        self.champion.write_bytes(b'champion')
        self.tracks = []
        for jar in (self.jar, self.champion):
            (jar.parent / 'tracks').mkdir()
            track = jar.parent / 'tracks/example.track'
            track.write_bytes(b'same course')
            self.tracks.append(track)
        for name in ('JAR', 'PROPS', 'LOG', 'SEEDS'):
            self.addCleanup(setattr, bench_ai, name, getattr(bench_ai, name))
        bench_ai.configure_runtime(self.root / 'runtime')
        bench_ai.JAR = str(self.jar)
        bench_ai.SEEDS = [1]
        self.saved_props = Path(bench_ai.PROPS).read_bytes()
        environment = {k: v for k, v in os.environ.items() if not k.startswith('BENCH_')}
        environment['BENCH_CHAMPION_JAR'] = str(self.champion)
        patch = mock.patch.dict(os.environ, environment, clear=True)
        patch.start()
        self.addCleanup(patch.stop)

    def run_bench(self, effect=None):
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch.object(bench_ai, 'run_track', side_effect=effect,
                               return_value=(7, 0, [10] * 7)) as run, \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = bench_ai.bench(['example'])
        self.assertEqual(self.saved_props, Path(bench_ai.PROPS).read_bytes())
        self.assertEqual(str(self.jar), bench_ai.JAR)
        return result, run.call_count, output.getvalue(), errors.getvalue()

    def test_uncached_identical_courses_run_both_binaries(self):
        seen = []
        def record(*args, **kwargs):
            seen.append(bench_ai.JAR)
            return 7, 0, [10] * 7
        result, calls, _, _ = self.run_bench(record)
        self.assertTrue(result)
        self.assertEqual(2, calls)
        self.assertEqual([str(self.jar), str(self.champion)], seen)

    def test_uncached_different_courses_fail_before_any_race(self):
        self.tracks[1].write_bytes(b'different course under the same name')
        result, calls, output, errors = self.run_bench()
        self.assertFalse(result)
        self.assertEqual(0, calls)
        self.assertEqual('', output)
        self.assertIn('track data differ', errors)

    def test_uncached_inputs_cannot_change_during_comparison(self):
        for target in (self.jar, self.champion, *self.tracks, Path(bench_ai.PROPS)):
            with self.subTest(target=str(target)):
                original = target.read_bytes()
                def mutate(*args, **kwargs):
                    target.write_bytes(target.read_bytes() + b'\nlaps=2\n')
                    return 7, 0, [10] * 7
                result, _, output, errors = self.run_bench(mutate)
                self.assertFalse(result)
                self.assertNotIn('TOTAL', output)
                self.assertTrue('changed during' in errors or 'track data differ' in errors)
                target.write_bytes(original)


class ScriptedOracle:
    def __init__(self, symbols='X', *, repeat=True):
        self.symbols, self.repeat = symbols, repeat
        self.calls = []
        self.boards = []
        self.closed = False

    def ask(self, mover, cars):
        self.calls.append(mover)
        self.boards.append([car[:] for car in cars])
        symbol = self.symbols[(len(self.calls) - 1) % len(self.symbols)] if self.repeat else self.symbols[mover]
        return 0, 0, 'XXXX' + symbol + 'XXXX'

    def close(self):
        self.closed = True


class CrossEraClassificationTests(unittest.TestCase):
    def classify(self, symbols, **kwargs):
        current = ScriptedOracle(symbols)
        # The older brain proposes NONE, but its claimed legality is ignored.
        old = ScriptedOracle('F')
        result = cross_era.classify(current, old, STARTS, SLOTS, **kwargs)
        return result, current, old

    def test_seventh_crash_ends_race_before_survivor_moves(self):
        (places, fates), current, _ = self.classify('X')
        self.assertEqual([8, 7, 6, 5, 4, 3, 2, 1], places)
        self.assertEqual(7, fates.count(99))
        self.assertEqual(list(range(7)), current.calls)

    def test_mixed_finishes_and_crashes_fill_distinct_places(self):
        (places, fates), current, _ = self.classify('FXFXFXF')
        self.assertEqual([1, 8, 2, 7, 3, 6, 4, 5], places)
        self.assertEqual(3, fates.count(99))
        self.assertEqual(7, len(current.calls))

    def test_all_finishes_still_leave_last_survivor(self):
        (places, fates), current, _ = self.classify('F')
        self.assertEqual(list(range(1, 9)), places)
        self.assertEqual(0, fates.count(99))
        self.assertEqual(7, len(current.calls))

    def test_retired_cars_have_live_referee_sentinel_state(self):
        _, current, _ = self.classify('X')
        self.assertEqual([-100000, -100000, 0, 0, 99], current.boards[1][0])
        _, current, _ = self.classify('F')
        self.assertEqual([-100000, -100000, 0, 0, 90], current.boards[1][0])

    def test_retired_slots_are_skipped_on_later_rounds(self):
        (places, _), current, _ = self.classify('XAAAAAAAXXXXXX', max_rounds=2)
        self.assertEqual([8, 7, 6, 5, 4, 3, 2, 1], places)
        self.assertEqual(list(range(8)) + list(range(1, 7)), current.calls)

    def test_horizon_without_completion_never_invents_places(self):
        with self.assertRaisesRegex(ValueError, 'incomplete.*no classification'):
            self.classify('A', max_rounds=2)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.classify('FFFFAAA', max_rounds=1)

    def test_terminal_last_allowed_move_is_accepted(self):
        (places, _), current, _ = self.classify('AXXXXXXX', max_rounds=1)
        self.assertEqual([1, 8, 7, 6, 5, 4, 3, 2], places)
        self.assertEqual(list(range(8)), current.calls)

    def test_invalid_referee_output_is_not_a_legal_move(self):
        with self.assertRaisesRegex(ValueError, 'invalid legacy'):
            self.classify('?')

    def test_failure_closes_both_oracles(self):
        current, old = ScriptedOracle('A'), ScriptedOracle('A')
        with mock.patch.object(cross_era, 'start_positions', return_value=STARTS), \
                mock.patch.object(cross_era, 'Oracle', side_effect=[current, old]):
            with self.assertRaises(ValueError):
                cross_era.race('example', 1, SLOTS, max_rounds=1)
        self.assertTrue(current.closed and old.closed)

    def test_second_oracle_start_failure_also_closes_first(self):
        current = ScriptedOracle()
        with mock.patch.object(cross_era, 'start_positions', return_value=STARTS), \
                mock.patch.object(cross_era, 'Oracle', side_effect=[current, OSError('failed')]):
            with self.assertRaises(OSError):
                cross_era.race('example', 1, SLOTS)
        self.assertTrue(current.closed)

    def test_incomplete_second_mirror_does_not_report_a_partial_mean(self):
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch.object(cross_era, 'experiment_identity', return_value={}), \
                mock.patch.object(cross_era, 'race', side_effect=[(list(range(1, 9)), [90] * 8),
                                                            ValueError('incomplete')]), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertNotEqual(0, cross_era.main(['example', '1']))
        self.assertEqual('', output.getvalue())
        self.assertIn('incomplete', errors.getvalue())


def completed_log():
    lines = ['# Grid 10x10', 'trackLeft=0,0;0,10', 'trackRight=10,0;10,10']
    lines += ['player%d name=Player %d kind=AI2 start=%d,0' % (n, n, n) for n in range(1, 9)]
    lines += ['%d p%d AI2 NONE v(0,0)>(0,0) (%d,0)>(%d,0) FINISH place=%d' %
              (n, n, n, n, n) for n in range(1, 8)]
    lines += ['# results'] + ['%d. Player %d' % (n, n) for n in range(1, 9)]
    return '\n'.join(lines) + '\n'


class CrossEraStartTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        patch = mock.patch.object(cross_era, 'S', str(self.root))
        patch.start()
        self.addCleanup(patch.stop)
        (self.root / 'era_AI2.properties').write_text('nPlayers=8\n' + ''.join(
            'player%dKind=AI2\n' % n for n in range(1, 9)))
        self.paths = []

    def writer(self, text=None, stdout=''):
        def run(command, **kwargs):
            self.assertTrue(kwargs['check'])
            log = Path(command[command.index('--log') + 1])
            self.paths.append(log)
            log.write_text(completed_log() if text is None else text, encoding='utf-8')
            return subprocess.CompletedProcess(command, 0, stdout, '')
        return run

    def test_each_successful_invocation_has_unique_cleaned_output(self):
        with mock.patch.object(cross_era.subprocess, 'run', side_effect=self.writer()):
            self.assertEqual(STARTS, cross_era.start_positions('example', 1))
            self.assertEqual(STARTS, cross_era.start_positions('example', 1))
        self.assertNotEqual(*self.paths)
        self.assertTrue(all(not path.exists() for path in self.paths))

    def test_process_failure_cannot_read_previous_log(self):
        stale = self.root / 'cross_start_example_1.log'
        stale.write_text(completed_log(), encoding='utf-8')
        error = subprocess.CalledProcessError(2, ['java'], stderr='Properties file not found')
        with mock.patch.object(cross_era.subprocess, 'run', side_effect=error):
            with self.assertRaises(subprocess.CalledProcessError):
                cross_era.start_positions('example', 1)
        self.assertEqual(completed_log(), stale.read_text(encoding='utf-8'))

    def test_success_status_with_incomplete_log_is_rejected(self):
        with mock.patch.object(cross_era.subprocess, 'run', side_effect=self.writer('# results\n')):
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                cross_era.start_positions('example', 1)
        self.assertFalse(self.paths[0].exists())

    def test_missing_new_log_does_not_fall_back_to_older_output(self):
        (self.root / 'cross_start_example_1.log').write_text(completed_log(), encoding='utf-8')
        with mock.patch.object(cross_era.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            with self.assertRaises(OSError):
                cross_era.start_positions('example', 1)

    def test_declared_start_order_cannot_reassign_player_slots(self):
        lines = completed_log().splitlines()
        lines[3:11] = reversed(lines[3:11])
        with mock.patch.object(cross_era.subprocess, 'run', side_effect=self.writer('\n'.join(lines) + '\n')):
            self.assertEqual(STARTS, cross_era.start_positions('example', 1))

    def test_unsupported_progress_is_not_dropped_by_legacy_protocol(self):
        cases = [(completed_log(), '[laps] gate geometry: S/F CP1 CP2'),
                 ('# laps 2\n' + completed_log(), ''),
                 ('# start-placement scatter\n' + completed_log(), '')]
        for text, stdout in cases:
            with self.subTest(stdout=stdout, text=text[:20]), \
                    mock.patch.object(cross_era.subprocess, 'run', side_effect=self.writer(text, stdout)):
                with self.assertRaisesRegex(ValueError, 'cannot carry'):
                    cross_era.start_positions('example', 1)

    def test_main_reports_java_error_without_any_performance_result(self):
        error = subprocess.CalledProcessError(2, ['java'], stderr='Properties file not found')
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch.object(cross_era, 'experiment_identity', return_value={}), \
                mock.patch.object(cross_era, 'race', side_effect=error), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(2, cross_era.main(['example', '1']))
        self.assertEqual('', output.getvalue())
        self.assertIn('Properties file not found', errors.getvalue())


class RetiredExtractionTests(unittest.TestCase):
    def test_old_command_never_creates_or_overwrites_a_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            report, out = Path(directory) / 'bench.log', Path(directory) / 'baseline.json'
            report.write_text('hairpin | 7/0 mv=17.143 | 7/0 mv=17.143\n')
            for exists in (False, True):
                if exists:
                    out.write_text('preserve existing evidence')
                errors = io.StringIO()
                with contextlib.redirect_stderr(errors):
                    self.assertNotEqual(0, extract_baseline.main([str(report), str(out), '2']))
                self.assertIn('BENCH_BASELINE', errors.getvalue())
                self.assertIn('retired', errors.getvalue())
                self.assertEqual(exists, out.exists())
                if exists:
                    self.assertEqual('preserve existing evidence', out.read_text())

    def test_process_exit_code_reflects_retirement(self):
        result = subprocess.run([sys.executable, extract_baseline.__file__, 'unused.log', 'unused.json'],
                                capture_output=True, text=True, check=False)
        self.assertEqual(2, result.returncode)
        self.assertIn('No output was written', result.stderr)


if __name__ == '__main__':
    unittest.main()
