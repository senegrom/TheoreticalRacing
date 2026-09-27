"""Invalid measurements must fail closed; valid last-survivor races still score."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from tracks import bench_ai, head_to_head, fleet_grid
from tracks.benchmark_io import comparison_profile, read_properties


def race_log(slots='1,3,5,7', names=None, count=8, kinds=None, crashes=0):
    names = names or {n: 'Player %d' % n for n in range(1, count + 1)}
    kinds = kinds or {n: 'AI1' for n in names}
    lines = ['# Theoretical Racing 0.3.0 — game log', '# Grid 80x30',
             'trackLeft=0,0;0,10', 'trackRight=10,0;10,10']
    if slots:
        lines.append('# candidate-slots ' + slots)
    lines += ['player%d name=%s kind=%s start=%d,0' % (n, names[n], kinds[n], n)
              for n in range(1, count + 1)]
    places = {}
    for turn, n in enumerate(range(1, count if count > 1 else 2), 1):
        crashing = n <= crashes
        place = count - n + 1 if crashing else n - crashes
        places[place] = names[n]
        lines.append('%d p%d %s E v(0,0)→(1,0) (%d,0)→(%d,0) %s place=%d' %
                     (turn, n, kinds[n], n, n + 1, 'CRASH' if crashing else 'FINISH', place))
    if count > 1:
        places[count - crashes] = names[count]
    lines += ['# results'] + ['%d. %s' % (p, places[p]) for p in sorted(places)]
    return '\n'.join(lines) + '\n'


class CompletedLogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'race.log'
        for key in ('JAR', 'PROPS', 'LOG', 'SEEDS'):
            self.addCleanup(setattr, bench_ai, key, getattr(bench_ai, key))

    def parse(self, text):
        self.path.write_text(text, encoding='utf-8')
        return bench_ai.parse_race_log(self.path)

    def test_results_header_alone_is_not_a_completed_race(self):
        self.assertIsNone(self.parse('# results\n'))

    def test_complete_race_includes_last_survivor_without_finish_event(self):
        self.assertEqual((7, 0, [1] * 7), self.parse(race_log()))

    def test_default_names_are_all_scored(self):
        self.path.write_text(race_log(), encoding='utf-8')
        places, slots, crashed = head_to_head.read(self.path)
        self.assertEqual(set(range(1, 9)), set(places))
        self.assertEqual({1, 3, 5, 7}, slots)
        self.assertEqual(set(), crashed)

    def test_one_spaced_name_cannot_disappear(self):
        names = {n: chr(64 + n) for n in range(1, 9)}
        names[1] = 'Driver One'
        self.path.write_text(race_log(names=names), encoding='utf-8')
        self.assertEqual(8, len(head_to_head.read(self.path)[0]))

    def test_incomplete_mixed_benchmark_returns_failure(self):
        bench_ai.configure_runtime(self.tmp.name)
        self.addCleanup(setattr, bench_ai, 'SEEDS', bench_ai.SEEDS)
        jar = Path(self.tmp.name) / 'race.jar'
        jar.write_bytes(b'fixture binary')
        (jar.parent / 'tracks').mkdir()
        (jar.parent / 'tracks/example.track').write_bytes(b'fixture course')
        bench_ai.JAR = str(jar)
        races = []
        def fake_java(command, **kwargs):
            if '--auto' in command:
                races.append(command)
                Path(bench_ai.LOG).write_text('# results\n')
            return subprocess.CompletedProcess(command, 0, '', '')
        with mock.patch.object(bench_ai.subprocess, 'run', side_effect=fake_java), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(bench_ai.main(['--h2h', '--seeds', '1', 'example']))
        self.assertEqual(1, len(races), 'preflight must not hide the incomplete-log assertion')

    def test_corrupt_classifications_and_terminal_sequences_are_rejected(self):
        good = race_log()
        invalid = [good.split('# results')[0] + '# results\n',
                   good.replace('8. Player 8\n', ''),
                   good.replace('8. Player 8', '8. Unknown'),
                   good.replace('8. Player 8', '7. Player 8'),
                   good.replace('8. Player 8', '8. Player 7'),
                   good.replace('name=Player 8', 'name=Player 7'),
                   good.replace('player8 name=', 'player7 name='),
                   good.replace('FINISH place=1', 'FINISH place=8'),
                   good.replace('2 p2', '3 p2'),
                   good.replace('2 p2 AI1', '2 p2 AI2'),
                   good.replace('2 p2', '2 p1'),
                   good + '# results\n',
                   good.replace('# results', '8 p8 AI1 E v(0,0)→(1,0) (8,0)→(9,0) FINISH place=8\n# results')]
        for i, text in enumerate(invalid):
            with self.subTest(case=i):
                self.assertIsNone(self.parse(text))

    def test_crashes_timeouts_and_solo_races_preserve_their_real_outcomes(self):
        self.assertEqual((0, 7, []), self.parse(race_log(crashes=7)))
        self.assertEqual((6, 0, [1] * 6), self.parse(race_log(crashes=1).replace('CRASH', 'TIMEOUT')))
        self.assertEqual((1, 0, [1]), self.parse(race_log(count=1, slots='')))
        self.assertEqual((0, 1, []), self.parse(race_log(count=1, slots='', crashes=1)))

    def test_configured_roster_mismatch_is_rejected(self):
        bench_ai.configure_runtime(self.tmp.name)
        # A complete two-car log must not satisfy a requested eight-car race.
        def fake_java(command, **kwargs):
            Path(bench_ai.LOG).write_text(race_log(count=2, slots=''), encoding='utf-8')
            return subprocess.CompletedProcess(command, 0, '', '')
        with mock.patch.object(bench_ai.subprocess, 'run', side_effect=fake_java), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(bench_ai.run_track('example'))
            self.assertIsNone(bench_ai.run_track_h2h('example'))


def ordered_log(slots, order):
    """A complete race in which the players finish in ``order``; the last one
    is the last survivor. ``slots`` is the candidate-slot list, or None."""
    names = {n: 'Player %d' % n for n in order}
    lines = ['# Theoretical Racing 0.3.0 — game log', '# Grid 80x30',
             'trackLeft=0,0;0,10', 'trackRight=10,0;10,10']
    if slots:
        lines.append('# candidate-slots ' + slots)
    lines += ['player%d name=%s kind=AI1 start=%d,0' % (n, names[n], n) for n in sorted(order)]
    for place, n in enumerate(order[:-1], 1):
        lines.append('%d p%d AI1 E v(0,0)→(1,0) (%d,0)→(%d,0) FINISH place=%d' % (place, n, n, n + 1, place))
    lines += ['# results'] + ['%d. %s' % (p, names[n]) for p, n in enumerate(order, 1)]
    return '\n'.join(lines) + '\n'


class MirroredGridTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.java = self.root / 'java'
        self.java.write_bytes(b'fake java for manifest hashing only')
        self.jar = self.root / 'racing.jar'
        self.jar.write_bytes(b'candidate and champion binary')
        (self.root / 'tracks').mkdir()
        (self.root / 'tracks/example.track').write_text('course')

    def grid(self, name, slots, lo=1, hi=2, extra='', mutate=None, log=None):
        directory = self.root / name
        directory.mkdir()
        props = self.root / (name + '.properties')
        props.write_text('nPlayers=8\ncandidateSlots=' + slots + '\n' + extra)
        manifest = fleet_grid.manifest_for(self.jar, props, self.java, ['-Xmx1g'], ['example'], lo, hi)
        if mutate:
            mutate(manifest)
        (directory / 'manifest.json').write_text(fleet_grid.json_text(manifest))
        import hashlib
        run_id = hashlib.sha256(fleet_grid.json_text(manifest).encode()).hexdigest()
        logs = []
        for seed in range(lo, hi + 1):
            path = directory / ('example_s%d.log' % seed)
            path.write_text(log(seed) if log else race_log(slots), encoding='utf-8')
            logs.append({'sha256': fleet_grid.digest(path), 'counts': fleet_grid.parse_log(path)})
        record = {'run_id': run_id, 'seeds': list(range(lo, hi + 1)), 'no_loop': False, 'logs': logs}
        (directory / 'example.complete.json').write_text(fleet_grid.json_text(record))
        return directory

    def score(self, *directories):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = head_to_head.main([str(d) for d in directories])
        return status, output.getvalue(), errors.getvalue()

    def test_complete_complementary_pairs_cancel_grid_advantage(self):
        a = self.grid('a', '1,3,5,7')
        b = self.grid('b', '2,4,6,8')
        status, output, error = self.score(a, b)
        self.assertEqual(0, status, error)
        self.assertIn('candidate 4.500   champion 4.500', output)
        self.assertIn('mirrored races 2', output)

    def test_the_paired_statistic_and_its_units(self):
        # Pin the promotion statistic itself (review, 2026-09-27): scoring one
        # grid only, flipping the sign or printing the SD as the SE all passed.
        # The candidate gains in both halves, unequally over the two seeds.
        a = self.grid('a', '1,3,5,7', log=lambda seed: ordered_log(
            '1,3,5,7', [1, 2, 3, 4, 5, 6, 7, 8] if seed == 1 else [1, 3, 5, 7, 2, 4, 6, 8]))
        b = self.grid('b', '2,4,6,8', log=lambda seed: ordered_log('2,4,6,8', [2, 1, 4, 3, 6, 5, 8, 7]))
        status, output, error = self.score(a, b)
        self.assertEqual(0, status, error)
        self.assertIn('mirrored races 2: candidate minus champion mean place -1.750  '
                      '(standard error 0.750; negative favours the candidate)', output)
        self.assertIn('per candidate car -0.875 places (standard error 0.375)', output)

    def test_duplicate_and_noncomplementary_inputs_are_rejected(self):
        a = self.grid('a', '1,3,5,7')
        b = self.grid('b', '1,3,5,7')
        for pair in ((a, a), (a, b), (a,)):
            status, output, _ = self.score(*pair)
            self.assertNotEqual(0, status)
            self.assertNotIn('mean place', output)

    def test_missing_truncated_stale_and_unmanifested_grids_fail_closed(self):
        a = self.grid('a', '1,3,5,7')
        for mode in ('missing', 'truncated', 'extra', 'manifest', 'marker'):
            with self.subTest(mode=mode):
                b = self.grid(mode, '2,4,6,8')
                path = b / 'example_s2.log'
                if mode == 'missing':
                    path.unlink()
                elif mode == 'truncated':
                    path.write_text('# results\n')
                elif mode == 'extra':
                    (b / 'stale_s1.log').write_text(race_log(), encoding='utf-8')
                elif mode == 'manifest':
                    (b / 'manifest.json').unlink()
                else:
                    (b / 'example.complete.json').unlink()
                status, output, _ = self.score(a, b)
                self.assertNotEqual(0, status)
                self.assertEqual('', output)

    def test_incompatible_experiments_are_not_combined(self):
        a = self.grid('a', '1,3,5,7')
        variants = [('seeds', dict(lo=2, hi=3)),
                    ('props', dict(extra='aiStartPlacement=informed\n')),
                    ('jar', dict(mutate=lambda m: m.update(jar='different'))),
                    ('schema', dict(mutate=lambda m: m.update(schema=1))),
                    ('runtime', dict(mutate=lambda m: m.update(java_sha256='different'))),
                    ('heap', dict(mutate=lambda m: m.update(heap=['-Xmx2g']))),
                    ('assignment', dict(mutate=lambda m: m['comparison'].update(candidate_slots=[1, 3, 5, 7])))]
        for name, kwargs in variants:
            with self.subTest(name=name):
                b = self.grid(name, '2,4,6,8', **kwargs)
                self.assertNotEqual(0, self.score(a, b)[0])

    def test_nonoverlapping_seed_slices_combine_but_duplicate_pairs_do_not(self):
        a, b = self.grid('a', '1,3,5,7'), self.grid('b', '2,4,6,8')
        c, d = self.grid('c', '1,3,5,7', 3, 4), self.grid('d', '2,4,6,8', 3, 4)
        self.assertIn('mirrored races 4', self.score(a, b, c, d)[1])
        e, f = self.grid('e', '1,3,5,7'), self.grid('f', '2,4,6,8')
        self.assertNotEqual(0, self.score(a, b, e, f)[0])

    def test_property_aliases_and_continuations_only_exclude_the_real_assignment(self):
        a, b = self.root / 'a.properties', self.root / 'b.properties'
        a.write_bytes(b'! comment\nnPlayers : 8\ncandidate\\u0053lots = 1,3,\\\n  5,7\nlabel=hello\\ world\n')
        b.write_bytes(b'nPlayers=8\nlabel:hello world\ncandidateSlots=2,4,6,8\n')
        self.assertEqual('1,3,5,7', read_properties(a)['candidateSlots'])
        self.assertEqual(comparison_profile(a)['properties'], comparison_profile(b)['properties'])
        self.assertNotEqual(comparison_profile(a)['candidate_slots'], comparison_profile(b)['candidate_slots'])


class BaselineCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.jar = self.root / 'candidate.jar'
        self.jar.write_bytes(b'candidate-v1')
        (self.root / 'tracks').mkdir()
        self.track = self.root / 'tracks/example.track'
        self.track.write_bytes(b'course')
        self.cache = self.root / 'baseline.json'
        for key in ('JAR', 'PROPS', 'LOG', 'SEEDS'):
            self.addCleanup(setattr, bench_ai, key, getattr(bench_ai, key))
        bench_ai.JAR = str(self.jar)
        bench_ai.configure_runtime(self.root / 'runtime')
        bench_ai.SEEDS = [1]
        env = {k: v for k, v in os.environ.items() if not k.startswith('BENCH_')}
        env['BENCH_BASELINE'] = str(self.cache)
        patch = mock.patch.dict(os.environ, env, clear=True)
        patch.start()
        self.addCleanup(patch.stop)

    def bench(self, *, failed=False, side_effect=None):
        with mock.patch.object(bench_ai, 'run_track', return_value=None if failed else (7, 0, [10] * 7),
                               side_effect=side_effect) as single, \
                mock.patch.object(bench_ai, 'run_track_batch',
                                  return_value=None if failed else [(7, 0, [10] * 7)] * len(bench_ai.SEEDS)) as batch, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            status = bench_ai.bench(['example'])
        return status, single.call_count + batch.call_count

    def test_identical_experiment_reuses_only_the_champion_column(self):
        self.assertEqual((True, 2), self.bench())
        self.assertEqual((True, 1), self.bench())

    def test_five_seed_baseline_rejects_one_seed_and_shifted_windows(self):
        bench_ai.SEEDS = [1, 2, 3, 4, 5]
        self.assertTrue(self.bench()[0])
        self.assertEqual(35, json.loads(self.cache.read_text())['rows']['example'][0])
        for seeds in ([1], [6, 7, 8, 9, 10]):
            bench_ai.SEEDS = seeds
            self.assertEqual((False, 0), self.bench())

    def test_changed_properties_binary_tracks_and_legacy_cache_are_rejected(self):
        self.assertTrue(self.bench()[0])
        for path in (Path(bench_ai.PROPS), self.jar, self.track):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b'\nlaps=2\n')
                self.assertEqual((False, 0), self.bench())
                path.write_bytes(original)
        self.cache.write_text(json.dumps({'example': [7, 0, 10]}))
        self.assertEqual((False, 0), self.bench())

    def test_frozen_champion_survives_candidate_rebuild_and_is_actually_executed(self):
        frozen = self.root / 'frozen.jar'
        frozen.write_bytes(b'champion')
        with mock.patch.dict(os.environ, {'BENCH_CHAMPION_JAR': str(frozen)}):
            observed = []
            def run(*args, **kwargs):
                observed.append(bench_ai.JAR)
                return 7, 0, [10] * 7
            self.assertTrue(self.bench(side_effect=run)[0])
            self.assertEqual([str(self.jar), str(frozen)], observed)
            self.jar.write_bytes(b'candidate-v2')
            self.assertEqual((True, 1), self.bench())
            frozen.write_bytes(b'different champion')
            self.assertEqual((False, 0), self.bench())

    def test_failed_or_mutating_runs_never_publish_a_baseline(self):
        original = Path(bench_ai.PROPS).read_bytes()
        self.assertFalse(self.bench(failed=True)[0])
        self.assertFalse(self.cache.exists())
        def mutate(*args, **kwargs):
            self.track.write_bytes(self.track.read_bytes() + b'changed')
            return 7, 0, [10] * 7
        self.assertFalse(self.bench(side_effect=mutate)[0])
        self.assertFalse(self.cache.exists())
        self.assertEqual(original, Path(bench_ai.PROPS).read_bytes())

    def test_corrupt_results_and_nonfinite_metrics_are_rejected(self):
        self.assertTrue(self.bench()[0])
        saved = self.cache.read_text()
        for row in (None, [7, 0, float('nan')], [True, 0, 10], [7, -1, 10], [8, 0, 10]):
            with self.subTest(row=row):
                import hashlib
                data = json.loads(saved)
                data['rows']['example'] = row
                data['rows_sha256'] = hashlib.sha256(fleet_grid.json_text(data['rows']).encode()).hexdigest()
                self.cache.write_text(json.dumps(data))
                self.assertEqual((False, 0), self.bench())
        data = json.loads(saved)
        data['rows']['example'][2] = 5  # plausible corruption still fails the digest
        self.cache.write_text(json.dumps(data))
        self.assertEqual((False, 0), self.bench())

    def test_frozen_champion_does_not_hide_a_candidate_mutating_mid_run(self):
        frozen = self.root / 'frozen.jar'
        frozen.write_bytes(b'champion')
        def mutate(*args, **kwargs):
            self.jar.write_bytes(self.jar.read_bytes() + b'changed')
            return 7, 0, [10] * 7
        with mock.patch.dict(os.environ, {'BENCH_CHAMPION_JAR': str(frozen)}):
            self.assertFalse(self.bench(side_effect=mutate)[0])
            self.assertFalse(self.cache.exists())


if __name__ == '__main__':
    unittest.main()


class LoneCandidateReportTests(unittest.TestCase):
    """run_1vfield.report, the lone-candidate check CLAUDE.md requires before a
    promotion, had no test at all (review, 2026-09-27)."""

    def test_seat_pairing_mean_and_standard_error(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'docs/experiments/duel-lookahead'))
        import run_1vfield
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            control, seat1, seat2 = root / 'control', root / 'seat1', root / 'seat2'
            for d in (control, seat1, seat2):
                d.mkdir()
            (control / 'manifest.json').write_text(json.dumps({'tracks': {'example': 'x'}}), encoding='utf-8')
            # Control: seat 1 wins seed 1, seat 2 wins seed 2.
            (control / 'example_s1.log').write_text(ordered_log(None, [1, 2]), encoding='utf-8')
            (control / 'example_s2.log').write_text(ordered_log(None, [2, 1]), encoding='utf-8')
            # The lone candidate in seat 1: 0 on seed 1, -1 on seed 2; in seat 2:
            # -1 on seed 1, +1 on seed 2. Units -0.5 and 0: mean -0.25, SE 0.25.
            (seat1 / 'example_s1.log').write_text(ordered_log('1', [1, 2]), encoding='utf-8')
            (seat1 / 'example_s2.log').write_text(ordered_log('1', [1, 2]), encoding='utf-8')
            (seat2 / 'example_s1.log').write_text(ordered_log('2', [2, 1]), encoding='utf-8')
            (seat2 / 'example_s2.log').write_text(ordered_log('2', [1, 2]), encoding='utf-8')
            text = run_1vfield.report(control, {1: seat1, 2: seat2}, range(1, 3))
        self.assertIn('paired track-seeds 2: candidate minus champion place -0.250  '
                      '(standard error 0.250; negative favours the candidate)', text)
        self.assertIn('crashes      lone candidate 0   champion in the same seat 0', text)


class FleetGridGuardTests(unittest.TestCase):
    """Review, 2026-09-27: a demoted champion must not pass as a measurement,
    and a killed runner must not race its finished tracks again."""

    def test_a_potential_skipped_for_want_of_heap_fails_the_track(self):
        built = '[optimal] potential built in 1.2s (distance 1536 MiB, total 859 MiB)\n'
        self.assertEqual('built', fleet_grid.potential_status('lemans', built))
        capped = '[optimal] potential SKIPPED (over the distance cap) in 0.0s (distance 1536 MiB, total 0 MiB)\n'
        self.assertEqual('capped', fleet_grid.potential_status('nordschleife', capped))
        legacy = '[optimal] potential SKIPPED (over budget) in 0.0s (distance 1536 MiB, total 0 MiB)\n'
        self.assertEqual('capped', fleet_grid.potential_status('nordschleife', legacy))
        self.assertIsNone(fleet_grid.potential_status('hairpin', '[laps] too coarse -- laps disabled\n'))
        for text in (legacy, capped.replace('over the distance cap', 'heap too small')):
            with self.assertRaises(ValueError):
                fleet_grid.potential_status('lemans', text)

    def test_a_killed_grid_resumes_without_racing_finished_tracks(self):
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = root / 'racing.jar'
            jar.write_bytes(b'jar')
            (root / 'tracks').mkdir()
            for track in ('a', 'b'):
                (root / 'tracks' / (track + '.track')).write_text(track)
            props = root / 'p.properties'
            props.write_text('nPlayers=8\n')
            launched = []

            def fake_java(command, cwd=None, stdout=None, stderr=None, timeout=None, check=False):
                track = command[command.index('--track') + 1]
                launched.append(track)
                if launched == ['a', 'b']:
                    raise KeyboardInterrupt  # the runner is killed during track b
                log = command[command.index('--log') + 1]
                lo, hi = map(int, command[command.index('--seed') + 1].split('-'))
                for seed in range(lo, hi + 1):
                    Path(log[:-len('.log')] + '_s%d.log' % seed).write_text(race_log(''), encoding='utf-8')
                stdout.write('[optimal] potential built in 0.1s (distance 1536 MiB, total 100 MiB)\n')
                return subprocess.CompletedProcess(command, 0)

            env = {'RACING_JAR': str(jar), 'RACING_PROPS': str(props), 'RACING_JAVA': sys.executable,
                   'RACING_TRACKS': ''}
            out = str(root / 'out')
            with mock.patch.dict(os.environ, env), \
                    mock.patch.object(fleet_grid.subprocess, 'run', side_effect=fake_java), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(KeyboardInterrupt):
                    fleet_grid.main(['1-2', '1', out])
                self.assertEqual(0, fleet_grid.main(['1-2', '1', out]))
            self.assertEqual(['a', 'b', 'b'], launched)
            record = json.loads((root / 'out' / 'a.complete.json').read_text(encoding='utf-8'))
            self.assertEqual('built', record['potential'])
