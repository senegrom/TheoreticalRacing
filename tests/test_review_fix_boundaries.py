"""Regression coverage for lap-review benchmark identity and resumable completion."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from tracks import fleet_grid


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

    def test_no_completion_is_published_before_its_revalidation(self):
        # Since 2026-09-27 each track's marker follows its own revalidation, not
        # the whole grid's, so a killed runner resumes; the second manifest read
        # is that revalidation.
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
