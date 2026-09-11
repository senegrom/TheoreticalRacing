"""Regression coverage for lap-review benchmark identity and resumable completion."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from tracks import bench_ai, fleet_grid


class MixedFieldIdentityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.jar = self.root / 'racing.jar'
        self.jar.write_bytes(b'policy')
        (self.root / 'tracks').mkdir()
        self.track = self.root / 'tracks/example.track'
        self.track.write_bytes(b'course')
        self.java = self.root / 'java'
        self.java.write_bytes(b'runtime')
        for name in ('JAR', 'PROPS', 'LOG', 'SEEDS'):
            self.addCleanup(setattr, bench_ai, name, getattr(bench_ai, name))
        bench_ai.configure_runtime(self.root / 'runtime')
        bench_ai.JAR = str(self.jar)
        bench_ai.SEEDS = [1]
        self.props = Path(bench_ai.PROPS)
        self.original_props = self.props.read_bytes()
        # Manifest version discovery is isolated; the actual identity hashes and
        # property parsing are production code, not mocked comparisons.
        patch = mock.patch.object(bench_ai.shutil, 'which', return_value=str(self.java))
        patch.start(); self.addCleanup(patch.stop)
        patch = mock.patch.object(bench_ai.subprocess, 'run',
                                  return_value=subprocess.CompletedProcess([], 0, '', 'fixture JVM'))
        patch.start(); self.addCleanup(patch.stop)

    def compare(self, effect=None, nplayers=2, ai1n=1):
        output, errors = io.StringIO(), io.StringIO()
        calls = []
        def race(*args, **kwargs):
            players = bench_ai.configured_players(self.props)
            calls.append([kind for _, kind in players.values()])
            result = {kind: (sum(n for n, (_, k) in players.items() if k == kind),
                             sum(k == kind for _, k in players.values()), 0)
                      for kind in ('AI1', 'AI2')}
            if effect:
                effect(len(calls))
            return result
        with mock.patch.object(bench_ai, 'run_track_h2h', side_effect=race), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = bench_ai.bench_field(['example'], nplayers, ai1n)
        self.assertEqual(self.original_props, self.props.read_bytes(), 'runtime profile was not restored')
        return result, calls, output.getvalue(), errors.getvalue()

    def test_all_field_sizes_allow_only_the_intended_mirrors(self):
        for nplayers, ai1n in ((2, 1), (4, 2), (8, 4), (9, 4)):
            with self.subTest(nplayers=nplayers):
                result, calls, output, errors = self.compare(nplayers=nplayers, ai1n=ai1n)
                self.assertTrue(result, errors)
                front = ['AI1'] * ai1n + ['AI2'] * (nplayers - ai1n)
                self.assertEqual([front, front[::-1]], calls)
                self.assertIn('TOTAL mean place', output)

    def test_binary_course_profile_and_runtime_changes_fail_before_next_mirror(self):
        for path in (self.jar, self.track, self.props, self.java):
            with self.subTest(path=path):
                original = path.read_bytes()
                try:
                    result, calls, output, errors = self.compare(
                        lambda _: path.write_bytes(path.read_bytes() + b'\nlaps=2\n'))
                    self.assertFalse(result)
                    self.assertEqual(1, len(calls))
                    self.assertNotIn('TOTAL', output)
                    self.assertIn('changed during', errors)
                finally:
                    path.write_bytes(original)

    def test_unreadable_or_malformed_final_inputs_never_report_success(self):
        for path, mutation in ((self.track, lambda p: p.unlink()),
                               (self.props, lambda p: p.write_bytes(b'bad=\\uZZZZ\n'))):
            with self.subTest(path=path):
                original = path.read_bytes()
                try:
                    def change(last):
                        if last == 2:
                            mutation(path)
                    result, calls, output, errors = self.compare(change)
                    self.assertFalse(result)
                    self.assertEqual(2, len(calls))
                    self.assertNotIn('TOTAL', output)
                    self.assertIn('benchmark:', errors)
                finally:
                    path.write_bytes(original)

    def test_final_race_changes_are_checked_too(self):
        original = self.track.read_bytes()
        try:
            result, calls, output, errors = self.compare(
                lambda n: self.track.write_bytes(b'other course') if n == 2 else None)
            self.assertFalse(result)
            self.assertEqual(2, len(calls))
            self.assertNotIn('TOTAL', output)
            self.assertIn('changed during', errors)
        finally:
            self.track.write_bytes(original)

    def test_external_assignment_edits_are_not_hidden_by_the_next_mirror(self):
        result, calls, output, errors = self.compare(
            lambda _: self.props.write_text(self.props.read_text().replace('player1Kind=AI1', 'player1Kind=AI2')))
        self.assertFalse(result)
        self.assertEqual(1, len(calls))
        self.assertNotIn('TOTAL', output)
        self.assertIn('roster differs', errors)

    def test_java_option_and_seed_changes_invalidate_the_comparison(self):
        for change in (lambda _: os.environ.__setitem__('JAVA_TOOL_OPTIONS', '-Xmx111m'),
                       lambda _: setattr(bench_ai, 'SEEDS', [999])):
            with self.subTest(change=change), mock.patch.dict(os.environ, {}, clear=False):
                bench_ai.SEEDS = [1]
                result, calls, output, errors = self.compare(change)
                self.assertFalse(result)
                self.assertEqual(1, len(calls))
                self.assertNotIn('TOTAL', output)
                self.assertIn('changed during', errors)

    def test_missing_initial_course_fails_without_racing(self):
        self.track.unlink()
        result, calls, output, errors = self.compare()
        self.assertFalse(result)
        self.assertEqual([], calls)
        self.assertEqual('', output)
        self.assertIn('benchmark:', errors)

    def test_process_errors_fail_cleanly_and_restore_settings(self):
        def fail(_):
            raise OSError('injected launch failure')
        result, calls, output, errors = self.compare(fail)
        self.assertFalse(result)
        self.assertEqual(1, len(calls))
        self.assertNotIn('TOTAL', output)
        self.assertIn('injected launch failure', errors)


class FleetFinalValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.out = self.root / 'out'
        self.jar = self.root / 'race.jar'; self.jar.write_bytes(b'policy')
        self.props = self.root / 'race.properties'; self.props.write_text('nPlayers=2\nlaps=1\n')
        self.track = self.root / 'tracks/example.track'
        self.track.parent.mkdir(); self.track.write_bytes(b'course')
        self.java = self.root / 'java'; self.java.write_bytes(b'runtime')
        self.environment = dict(RACING_JAR=str(self.jar), RACING_PROPS=str(self.props),
                                RACING_JAVA=str(self.java), RACING_TRACKS='example', RACING_HEAP='-Xmx1g')
        self.calls = 0
        self.effect = None

    def java_run(self, command, **kwargs):
        self.calls += 1
        log = Path(command[command.index('--log') + 1])
        log.with_name('example_s1.log').write_text(
            'player1 name=A kind=AI1 start=1,1\n'
            'player2 name=B kind=AI2 start=2,1\n'
            '1 p1 AI1 E v(0,0)>(1,0) (1,1)>(2,1) FINISH place=1\n'
            '# results\n1. A\n2. B\n')
        if self.effect:
            self.effect()
        return subprocess.CompletedProcess(command, 0)

    def grid(self):
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, self.environment), \
                mock.patch.object(fleet_grid.shutil, 'which', return_value=str(self.java)), \
                mock.patch.object(fleet_grid.subprocess, 'run', side_effect=self.java_run), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = fleet_grid.main(['1', '1', str(self.out)])
        return status, output.getvalue(), errors.getvalue()

    def assert_no_publication(self):
        for name in ('example.complete.json', 'example.row', 'fleet.txt'):
            self.assertFalse((self.out / name).exists(), name + ' survived failed validation')

    def test_missing_final_course_is_rerun_after_restoration(self):
        original = self.track.read_bytes()
        self.effect = self.track.unlink
        status, output, _ = self.grid()
        self.assertEqual(2, status)
        self.assertNotIn('FLEETDONE', output)
        self.assert_no_publication()
        self.track.write_bytes(original)
        self.effect = None
        self.assertEqual(0, self.grid()[0])
        self.assertEqual(2, self.calls)
        self.assertEqual(0, self.grid()[0])
        self.assertEqual(2, self.calls, 'validated resume unnecessarily launched another JVM')

    def test_malformed_final_profile_is_rerun_after_restoration(self):
        original = self.props.read_bytes()
        self.effect = lambda: self.props.write_bytes(b'bad=\\uZZZZ\n')
        self.assertEqual(2, self.grid()[0])
        self.assert_no_publication()
        self.props.write_bytes(original)
        self.effect = None
        self.assertEqual(0, self.grid()[0])
        self.assertEqual(2, self.calls)

    def test_failed_revalidation_removes_preexisting_markers_rows_and_report(self):
        self.assertEqual(0, self.grid()[0])
        actual = fleet_grid.manifest_for
        calls = 0
        def manifest(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('injected final manifest read failure')
            return actual(*args)
        with mock.patch.object(fleet_grid, 'manifest_for', side_effect=manifest):
            self.assertEqual(2, self.grid()[0])
        self.assert_no_publication()
        self.assertEqual(0, self.grid()[0])
        self.assertEqual(2, self.calls)

    def test_no_completion_is_published_before_final_validation(self):
        actual = fleet_grid.manifest_for
        calls = 0
        def manifest(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.assertEqual(1, self.calls)
                self.assertTrue((self.out / 'example_s1.log').exists())
                self.assert_no_publication()
            return actual(*args)
        with mock.patch.object(fleet_grid, 'manifest_for', side_effect=manifest):
            self.assertEqual(0, self.grid()[0])
        self.assertTrue((self.out / 'example.complete.json').exists())

    def test_interrupted_final_validation_cannot_leave_resumable_output(self):
        self.assertEqual(0, self.grid()[0])
        actual = fleet_grid.manifest_for
        calls = 0
        def manifest(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt()
            return actual(*args)
        with mock.patch.object(fleet_grid, 'manifest_for', side_effect=manifest):
            with self.assertRaises(KeyboardInterrupt):
                self.grid()
        self.assert_no_publication()


if __name__ == '__main__':
    unittest.main()
