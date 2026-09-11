"""An era comparison may change brains, not silently change the experiment."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tracks import cross_era


class CrossEraInputTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.jars = {}
        self.tracks = []
        self.props = []
        for era, kind in (('new', 'AI2'), ('old', 'AI1')):
            home = self.root / era
            (home / 'tracks').mkdir(parents=True)
            jar = home / 'racing.jar'
            jar.write_bytes(era.encode())  # Different policy binaries are intentional.
            self.jars[era] = jar
            track = home / 'tracks/example.track'
            track.write_text('same course')
            self.tracks.append(track)
            props = self.root / ('era_%s.properties' % kind)
            props.write_text('nPlayers=8\nlaps=1\n' + ''.join(
                'player%dKind=%s\n' % (n, kind) for n in range(1, 9)))
            self.props.append(props)
        for name, value in (('S', str(self.root)), ('NEW_JAR', str(self.jars['new'])),
                            ('OLD_JAR', str(self.jars['old']))):
            patch = mock.patch.object(cross_era, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def compare(self, effect=None):
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch.object(cross_era, 'race', side_effect=effect,
                               return_value=(list(range(1, 9)), [90] * 8)) as run, \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = cross_era.main(['example', '1'])
        return status, run.call_count, output.getvalue(), errors.getvalue()

    def test_different_brains_with_matching_inputs_are_compared(self):
        status, calls, output, errors = self.compare()
        self.assertEqual(0, status, errors)
        self.assertEqual(2, calls)
        self.assertEqual(2, output.count('mean place 4.500'))

    def test_same_named_different_courses_fail_before_racing(self):
        self.tracks[1].write_text('a different course under the same name')
        status, calls, output, errors = self.compare()
        self.assertNotEqual(0, status)
        self.assertEqual(0, calls)
        self.assertEqual('', output)
        self.assertIn('track data differ', errors)

    def test_missing_old_inputs_fail_before_racing(self):
        for path in (self.jars['old'], self.tracks[1], self.props[1]):
            with self.subTest(path=path):
                content = path.read_bytes()
                path.unlink()
                status, calls, output, _ = self.compare()
                self.assertNotEqual(0, status)
                self.assertEqual(0, calls)
                self.assertEqual('', output)
                path.write_bytes(content)

    def test_both_rosters_must_be_eight_computer_players(self):
        for path in self.props:
            for change in ('nPlayers=4', 'player3Kind=HUMAN'):
                with self.subTest(era=path, change=change):
                    content = path.read_text()
                    path.write_text(content + change + '\n')
                    status, calls, _, errors = self.compare()
                    self.assertNotEqual(0, status)
                    self.assertEqual(0, calls)
                    self.assertIn('eight-AI roster', errors)
                    path.write_text(content)

    def test_profile_differences_are_rejected_instead_of_reset_by_legacy_queries(self):
        for change in ('laps=2', 'aiStartPlacement=scatter', 'candidateSlots=1,3,5,7'):
            with self.subTest(change=change):
                content = self.props[1].read_text()
                self.props[1].write_text(content + change + '\n')
                status, calls, output, _ = self.compare()
                self.assertNotEqual(0, status)
                self.assertEqual(0, calls)
                self.assertEqual('', output)
                self.props[1].write_text(content)

    def test_mutating_either_binary_profile_or_course_suppresses_the_report(self):
        for path in (*self.jars.values(), *self.props, *self.tracks):
            with self.subTest(path=path):
                content = path.read_bytes()
                calls = 0
                def mutate(*args, **kwargs):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        path.write_bytes(content + b'\n# changed during a mirror\n')
                    return list(range(1, 9)), [90] * 8
                status, _, output, errors = self.compare(mutate)
                self.assertNotEqual(0, status)
                self.assertEqual('', output)
                self.assertTrue('changed during' in errors or 'track data differ' in errors)
                path.write_bytes(content)

    def test_runtime_options_cannot_change_between_mirrors(self):
        def mutate(*args, **kwargs):
            os.environ['JAVA_TOOL_OPTIONS'] = '-Dreview.changed=true'
            return list(range(1, 9)), [90] * 8
        with mock.patch.dict(os.environ):
            os.environ.pop('JAVA_TOOL_OPTIONS', None)
            status, _, output, errors = self.compare(mutate)
        self.assertNotEqual(0, status)
        self.assertEqual('', output)
        self.assertIn('changed during', errors)


if __name__ == '__main__':
    unittest.main()
