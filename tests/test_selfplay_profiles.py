"""Self-play must run the controllers and field size named in its report."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from tracks import bench_ai, bench_iso
from tracks.benchmark_io import configured_players, read_properties, update_properties


class ProfileSetterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        for name in ('PROPS', 'LOG'):
            self.addCleanup(setattr, bench_ai, name, getattr(bench_ai, name))
        bench_ai.configure_runtime(temporary.name)
        self.props = Path(bench_ai.PROPS)

    def test_alternative_separators_and_indentation_set_effective_keys(self):
        for separator in ('=', ' = ', ':', ' : ', ' ', '\t', '\f'):
            with self.subTest(separator=repr(separator)):
                self.props.write_text('  nPlayers' + separator + '4\n' + ''.join(
                    '\tplayer%dKind%sAI2\n' % (n, separator) for n in range(1, 5)))
                bench_ai.set_nplayers(2)
                bench_ai.set_all_to('AI1')
                self.assertEqual(['AI1'] * 2, [k for _, k in configured_players(self.props).values()])
                self.assertEqual('AI2', read_properties(self.props)['player3Kind'])

    def test_escaped_duplicate_and_continued_keys_cannot_shadow_assignments(self):
        self.props.write_bytes(b'nPlayers=8\nn\\u0050layers : 4\n'
                               b'player1Kind=AI1\nplayer1K\\u0069nd : AI2\n'
                               b'player2Ki\\\n  nd : AI2\n'
                               b'player3Kind=HUMAN\nplayer4Kind=HUMAN\n')
        bench_ai.set_nplayers(2)
        bench_ai.set_kinds(['AI2', 'AI1'])
        self.assertEqual(['AI2', 'AI1'], [k for _, k in configured_players(self.props).values()])
        self.assertEqual(1, self.props.read_text().count('player1Kind='))
        self.assertEqual('HUMAN', read_properties(self.props)['player3Kind'])

    def test_absent_keys_and_ninth_active_slot_are_assigned(self):
        self.props.write_bytes(b'other=nPlayers=4\n')
        bench_ai.set_nplayers(9)
        bench_ai.set_all_to('AI1')
        self.assertEqual(['AI1'] * 9, [k for _, k in configured_players(self.props).values()])
        self.assertEqual('nPlayers=4', read_properties(self.props)['other'])

    def test_serialization_preserves_all_unassigned_effective_values(self):
        original = (b'! comment\r\nnPlayers : 2\r\nplayer1Name=Andr\xe9\r\n'
                    b'player2Name=\\uD83D\\uDE80\n\\#key\\:\\==\\ leading\\tvalue  \n'
                    b'empty=\n=empty key\npath=C\\:\\\\tmp\\\\file\n'
                    b'controls=\\u0000\\n\\r\\f\nodd=\\uD800\n'
                    b'tail=continued\\\n  text\nlast=discarded\\')
        self.props.write_bytes(original)
        expected = read_properties(self.props)
        expected['nPlayers'] = '4'
        update_properties(self.props, {'nPlayers': '4'})
        self.assertTrue(self.props.read_bytes().isascii())
        self.assertEqual(expected, read_properties(self.props))
        stable = self.props.read_bytes()
        update_properties(self.props, {})
        self.assertEqual(stable, self.props.read_bytes())

    def test_malformed_escape_is_rejected_without_writing(self):
        original = b'nPlayers=4\nunknown=\\uZZZZ\n'
        self.props.write_bytes(original)
        with self.assertRaisesRegex(ValueError, 'Unicode'):
            bench_ai.set_nplayers(2)
        self.assertEqual(original, self.props.read_bytes())

    def test_invalid_arguments_and_partial_rosters_are_rejected(self):
        for count in (0, 10, True, '2'):
            with self.subTest(count=count), self.assertRaises(ValueError):
                bench_ai.set_nplayers(count)
        bench_ai.set_nplayers(2)
        for kinds in ([], ['AI1'], ['AI1', 'HUMAN'], ['AI1'] * 10):
            with self.subTest(kinds=kinds), self.assertRaises(ValueError):
                bench_ai.set_kinds(kinds)


class SelfPlayProfileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ('PROPS', 'LOG', 'JAR', 'SEEDS'):
            self.addCleanup(setattr, bench_ai, name, getattr(bench_ai, name))
        bench_ai.configure_runtime(self.root / 'runtime')
        self.props = Path(bench_ai.PROPS)
        self.original = self.props.read_bytes()
        self.jar = self.root / 'candidate.jar'
        self.jar.write_bytes(b'candidate')
        self.champion = self.root / 'champion.jar'
        self.champion.write_bytes(b'champion')
        (self.root / 'tracks').mkdir()
        (self.root / 'tracks/example.track').write_bytes(b'course')
        self.java = self.root / 'java'
        self.java.write_bytes(b'fixture runtime')
        bench_ai.JAR = str(self.jar)
        bench_ai.SEEDS = [1]
        self.cache = self.root / 'baseline.json'
        environment = {k: v for k, v in os.environ.items() if not k.startswith('BENCH_')}
        environment['BENCH_CHAMPION_JAR'] = str(self.champion)
        for patch in (mock.patch.dict(os.environ, environment, clear=True),
                      mock.patch.object(bench_ai.shutil, 'which', return_value=str(self.java)),
                      mock.patch.object(bench_ai.subprocess, 'run',
                                        return_value=subprocess.CompletedProcess([], 0, '', 'fixture JVM'))):
            patch.start()
            self.addCleanup(patch.stop)

    def compare(self, nplayers=8, effect=None):
        saved = self.props.read_bytes()
        observed = []
        output, errors = io.StringIO(), io.StringIO()
        def single(*args, **kwargs):
            players = configured_players(self.props)
            observed.append((bench_ai.JAR, [k for _, k in players.values()]))
            if effect:
                effect(len(observed))
            retired = max(1, len(players) - 1)
            return retired, 0, [10] * retired
        def batch(track, seeds):
            result = single(track)
            return [result] * len(seeds)
        with mock.patch.object(bench_ai, 'run_track', side_effect=single), \
                mock.patch.object(bench_ai, 'run_track_batch', side_effect=batch), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = bench_ai.bench(['example'], nplayers=nplayers)
        self.assertEqual(saved, self.props.read_bytes(), 'profile bytes not restored')
        self.assertEqual(str(self.jar), bench_ai.JAR, 'candidate binary not restored')
        return result, observed, output.getvalue(), errors.getvalue()

    def test_every_requested_field_runs_both_correct_controllers(self):
        for count in (1, 2, 4, 8, 9):
            for seeds in ([None], [1], [1, 2]):
                with self.subTest(count=count, seeds=seeds):
                    # Valid aliases, duplicate declarations and omitted slots.
                    self.props.write_bytes(b'nPlayers=8\nnPlayers : 4\nplayer1Kind : AI2\n'
                                           b'player2K\\u0069nd AI2\nplayer3Ki\\\n nd=HUMAN\n')
                    bench_ai.SEEDS = seeds
                    result, seen, output, errors = self.compare(count)
                    self.assertTrue(result, errors)
                    self.assertEqual([(str(self.jar), ['AI1'] * count),
                                      (str(self.champion), ['AI2'] * count)], seen)
                    self.assertIn('TOTAL', output)

    def test_latin1_profiles_are_restored_byte_for_byte(self):
        self.props.write_bytes(self.original + b'player1Name=Andr\xe9\r\n')
        self.assertTrue(self.compare()[0])

    def test_clamped_field_and_malformed_profiles_fail_before_any_race(self):
        for suffix in (b'maxPlayers : 2\n', b'unknown=\\uZZZZ\n'):
            with self.subTest(suffix=suffix):
                self.props.write_bytes(self.original + suffix)
                result, seen, output, errors = self.compare(8)
                self.assertFalse(result)
                self.assertEqual([], seen)
                self.assertNotIn('TOTAL', output)
                self.assertIn('benchmark:', errors)

    def test_noop_setters_cannot_produce_success_or_a_baseline(self):
        for setter in ('set_nplayers', 'set_all_to'):
            with self.subTest(setter=setter), \
                    mock.patch.dict(os.environ, {'BENCH_BASELINE': str(self.cache)}), \
                    mock.patch.object(bench_ai, setter, return_value=None):
                self.props.write_bytes(b'nPlayers : 4\n' + b''.join(
                    b'player%dKind : AI2\n' % n for n in range(1, 5)))
                result, seen, output, errors = self.compare(2)
                self.assertFalse(result)
                self.assertEqual([], seen)
                self.assertNotIn('TOTAL', output)
                self.assertIn('roster differs', errors)
                self.assertFalse(self.cache.exists())

    def test_unexpected_roster_edits_are_detected_before_they_can_be_overwritten(self):
        for change in ({'player1Kind': 'AI2'}, {'nPlayers': '4'}, {'player1Name': 'Other'},
                       {'player9Kind': 'AI1'}, {'laps': '2'}):
            for last in (1, 2):
                with self.subTest(change=change, last=last), \
                        mock.patch.dict(os.environ, {'BENCH_BASELINE': str(self.cache)}):
                    # On the AI2 arm, changing AI2 to AI1 is the unexpected edit.
                    changed = {'player1Kind': 'AI1'} if last == 2 and 'player1Kind' in change else change
                    result, seen, output, errors = self.compare(
                        2, lambda n: update_properties(self.props, changed) if n == last else None)
                    self.assertFalse(result)
                    self.assertEqual(last, len(seen))
                    self.assertNotIn('TOTAL', output)
                    self.assertIn('benchmark:', errors)
                    self.assertFalse(self.cache.exists())

    def test_missing_and_malformed_final_profiles_fail_without_success(self):
        for change in (self.props.unlink, lambda: self.props.write_bytes(b'bad=\\uZZZZ\n')):
            with self.subTest(change=change):
                result, seen, output, errors = self.compare(2, lambda n: change() if n == 2 else None)
                self.assertFalse(result)
                self.assertEqual(2, len(seen))
                self.assertNotIn('TOTAL', output)
                self.assertIn('benchmark:', errors)

    def test_cached_baseline_remains_bound_to_field_and_expected_assignment(self):
        with mock.patch.dict(os.environ, {'BENCH_BASELINE': str(self.cache)}):
            result, seen, _, errors = self.compare(2)
            self.assertTrue(result, errors)
            self.assertEqual(2, len(seen))
            cached = self.cache.read_bytes()
            result, seen, _, errors = self.compare(2)
            self.assertTrue(result, errors)
            self.assertEqual([(str(self.jar), ['AI1'] * 2)], seen)
            self.assertEqual(cached, self.cache.read_bytes())
            self.assertFalse(self.compare(4)[0])
            with mock.patch.object(bench_ai, 'set_all_to', return_value=None):
                result, seen, output, _ = self.compare(2)
                self.assertFalse(result)
                self.assertEqual([], seen)
                self.assertNotIn('TOTAL', output)
                self.assertEqual(cached, self.cache.read_bytes())

    def test_cache_rejects_impossible_small_field_totals(self):
        from tracks.fleet_grid import json_text
        import hashlib
        with mock.patch.dict(os.environ, {'BENCH_BASELINE': str(self.cache)}):
            self.assertTrue(self.compare(2)[0])
            data = json.loads(self.cache.read_text())
            data['rows']['example'][0] = 2  # Two cars stop at the first retirement.
            data['rows_sha256'] = hashlib.sha256(json_text(data['rows']).encode()).hexdigest()
            self.cache.write_text(json.dumps(data))
            result, seen, output, errors = self.compare(2)
            self.assertFalse(result)
            self.assertEqual([], seen)
            self.assertNotIn('TOTAL', output)
            self.assertIn('invalid baseline result row', errors)

    def test_mixed_fields_accept_alternate_properties_and_restore_source_bytes(self):
        self.props.write_bytes(b'nPlayers : 4\nplayer1Kind : AI2\nplayer2Kind AI2\n'
                               b'player1Name=Andr\xe9\n')
        saved = self.props.read_bytes()
        assignments = []
        def race(*args, **kwargs):
            kinds = [k for _, k in configured_players(self.props).values()]
            assignments.append(kinds)
            return {k: (kinds.index(k) + 1, 1, 0) for k in ('AI1', 'AI2')}
        with mock.patch.object(bench_ai, 'run_track_h2h', side_effect=race), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(bench_ai.bench_field(['example'], 2, 1))
        self.assertEqual([['AI1', 'AI2'], ['AI2', 'AI1']], assignments)
        self.assertEqual(saved, self.props.read_bytes())


class IsolatedModeTests(unittest.TestCase):
    def test_field_size_is_explicit_and_setter_is_not_monkeypatched(self):
        for name in ('PROPS', 'LOG', 'SEEDS'):
            self.addCleanup(setattr, bench_iso.m, name, getattr(bench_iso.m, name))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'custom.properties'
            source.write_bytes(b'nPlayers : 4\nplayer1Kind : AI2\n')
            setter = bench_iso.m.set_nplayers
            for mode, kwargs in (('2car', {'nplayers': 2}), ('4car', {'nplayers': 4}), ('8car', {})):
                with self.subTest(mode=mode), \
                        mock.patch.dict(os.environ, {'RACING_PROPS': str(source)}), \
                        mock.patch.object(bench_iso, 'S', directory), \
                        mock.patch.object(bench_iso.m, 'bench', return_value=True) as bench, \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertTrue(bench_iso.main([mode, '1', 'example']))
                    bench.assert_called_once_with(['example'], **kwargs)
                    self.assertIs(setter, bench_iso.m.set_nplayers)
                    self.assertFalse(Path(bench_iso.m.PROPS).exists())
            self.assertEqual(b'nPlayers : 4\nplayer1Kind : AI2\n', source.read_bytes())


if __name__ == '__main__':
    unittest.main()
