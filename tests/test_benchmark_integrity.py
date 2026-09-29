"""Invalid measurements must fail closed; valid last-survivor races still score."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest import mock

from tracks import bench_ai, forensics_common, head_to_head, fleet_grid
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
        for key in ('JAR', 'PROPS', 'LOG'):
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
        record = {'run_id': run_id, 'seeds': list(range(lo, hi + 1)), 'no_loop': False, 'potential': None, 'logs': logs}
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


def publish(grid, manifest, seeds):
    """A grid's manifest and its tracks' validated completion markers."""
    text = fleet_grid.json_text(manifest)
    (grid / 'manifest.json').write_text(text, encoding='utf-8')
    run_id = hashlib.sha256(text.encode('utf-8')).hexdigest()
    for track in manifest['tracks']:
        logs = [{'sha256': fleet_grid.digest(grid / ('%s_s%d.log' % (track, seed))),
                 'counts': fleet_grid.parse_log(grid / ('%s_s%d.log' % (track, seed)))} for seed in seeds]
        record = {'run_id': run_id, 'seeds': list(seeds), 'no_loop': False, 'potential': None, 'logs': logs}
        (grid / (track + '.complete.json')).write_text(fleet_grid.json_text(record), encoding='utf-8')


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
            for grid, slots in ((control, []), (seat1, [1]), (seat2, [2])):
                publish(grid, {'jar': 'build', 'tracks': {'example': 'x'}, 'seeds': [1, 2],
                               'comparison': {'properties': 'profile', 'candidate_slots': slots}}, range(1, 3))
            text = run_1vfield.report(control, {1: seat1, 2: seat2}, range(1, 3))
            # Review, 2026-09-29: a seat raced with another profile is refused.
            publish(seat2, {'jar': 'build', 'tracks': {'example': 'x'}, 'seeds': [1, 2],
                            'comparison': {'properties': 'other profile', 'candidate_slots': [2]}}, range(1, 3))
            with self.assertRaisesRegex(ValueError, 'profile'):
                run_1vfield.report(control, {1: seat1, 2: seat2}, range(1, 3))
            # Review, 2026-09-28: a seat raced by another build is refused, and
            # so is a grid whose track never completed.
            publish(seat2, {'jar': 'other build', 'tracks': {'example': 'x'}, 'seeds': [1, 2],
                            'comparison': {'properties': 'profile', 'candidate_slots': [2]}}, range(1, 3))
            with self.assertRaisesRegex(ValueError, 'another build'):
                run_1vfield.report(control, {1: seat1, 2: seat2}, range(1, 3))
            (seat1 / 'example.complete.json').unlink()
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                run_1vfield.report(control, {1: seat1}, range(1, 3))
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
        # Review, 2026-09-29: a lapped course that reports nothing fails closed.
        with self.assertRaisesRegex(ValueError, 'no exact potential'):
            fleet_grid.potential_status('lemans', '[start] placements ready\n')
        for text in (legacy, capped.replace('over the distance cap', 'heap too small')):
            with self.assertRaises(ValueError):
                fleet_grid.potential_status('lemans', text)
        # A lowered -Dtr.optimalBuildBytes caps every course: not the champion.
        with self.assertRaisesRegex(ValueError, 'not the default 1536'):
            fleet_grid.potential_status('lemans', capped.replace('distance 1536 MiB', 'distance 512 MiB'))
        with self.assertRaises(ValueError) as frontier:
            fleet_grid.potential_status('lemans', capped.replace('over the distance cap', 'frontier budget'))
        self.assertNotIn('raise the heap', str(frontier.exception))

    def test_the_default_cap_is_the_engines(self):
        # The runner accepts "over the distance cap" only at the engine's own
        # cap; a raised Java constant must move this one with it.
        source = (Path(__file__).resolve().parents[1] / 'src/tr/logic/RaceGame.java').read_text(encoding='utf-8')
        m = re.search(r'OPTIMAL_BUDGET_BYTES = (\d+)L << 20;', source)
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), forensics_common.DEFAULT_DISTANCE_CAP_MIB)

    def test_runners_refuse_a_demoted_champion(self):
        skipped = '[optimal] potential SKIPPED (heap too small) in 0.0s (distance 1536 MiB, total 0 MiB)\n'
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()) as errors:
            bench_ai.configure_runtime(tmp)
            completed = subprocess.CompletedProcess([], 0, stdout=skipped, stderr='')
            with mock.patch.object(bench_ai.subprocess, 'run', return_value=completed):
                self.assertIsNone(bench_ai.run_track('lemans', seed=1))
                self.assertIsNone(bench_ai.run_track_h2h('lemans', seed=1))
        self.assertIn('raced without it', errors.getvalue())

    def test_the_default_jobs_fit_in_memory(self):
        gib = 1 << 30
        self.assertEqual(8 * gib, fleet_grid.heap_bytes(['-Xmx8g']))
        self.assertEqual(512 << 20, fleet_grid.heap_bytes(['-Xms1g', '-Xmx512m']))
        self.assertEqual(4 * gib, fleet_grid.heap_bytes(['-Xmx1g', '-Xmx4g']))  # the JVM takes the last
        self.assertIsNone(fleet_grid.heap_bytes(['-Xms1g']))
        self.assertEqual(3, fleet_grid.default_jobs(['-Xmx8g'], memory=32 * gib, cpus=16))
        self.assertEqual(2, fleet_grid.default_jobs(['-Xmx8g'], memory=64 * gib, cpus=2))
        self.assertEqual(1, fleet_grid.default_jobs(['-Xmx8g'], memory=4 * gib, cpus=8))
        self.assertEqual(3, fleet_grid.default_jobs([], memory=32 * gib, cpus=8))

    def test_races_run_from_private_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'tracks').mkdir()
            (root / 'tracks' / 'a.track').write_text('a')
            jar, props = root / 'race.jar', root / 'p.properties'
            jar.write_bytes(b'jar')
            props.write_text('nPlayers=8\n')
            manifest = {'jar': fleet_grid.digest(jar), 'properties': fleet_grid.digest(props),
                        'tracks': {'a': fleet_grid.digest(root / 'tracks' / 'a.track')}}
            out = root / 'out'
            out.mkdir()
            run_jar, run_props = fleet_grid.snapshot_inputs(out, manifest, jar, props, ['a'])
            self.assertNotEqual(jar, run_jar)
            jar.write_bytes(b'rebuilt')  # the original changes; the copy raced does not
            self.assertTrue(fleet_grid.snapshot_matches(manifest, run_jar, run_props, ['a']))
            run_props.write_text('nPlayers=2\n')  # but a write into the copy is caught
            self.assertFalse(fleet_grid.snapshot_matches(manifest, run_jar, run_props, ['a']))
            with self.assertRaises(ValueError):  # an original already off the manifest
                fleet_grid.snapshot_inputs(out, manifest, jar, props, ['a'])

    def test_a_marker_without_the_potential_is_not_resumable(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            log = out / 'a_s1.log'
            log.write_text(race_log(''), encoding='utf-8')
            record = {'run_id': 'r', 'seeds': [1], 'no_loop': False, 'potential': 'built',
                      'logs': [{'sha256': fleet_grid.digest(log), 'counts': fleet_grid.parse_log(log)}]}
            (out / 'a.complete.json').write_text(json.dumps(record), encoding='utf-8')
            self.assertIsNotNone(fleet_grid.completed(out, 'a', 'r', range(1, 2)))
            del record['potential']
            (out / 'a.complete.json').write_text(json.dumps(record), encoding='utf-8')
            self.assertIsNone(fleet_grid.completed(out, 'a', 'r', range(1, 2)))

    def test_a_killed_grid_resumes_without_racing_finished_tracks(self):
        # Ctrl+C reaches the main thread while track b's JVM runs and c waits:
        # b's JVM is stopped, c never starts, and a resumes as finished.
        import _thread
        import sys
        import time
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jar = root / 'racing.jar'
            jar.write_bytes(b'jar')
            (root / 'tracks').mkdir()
            for track in ('a', 'b', 'c'):
                (root / 'tracks' / (track + '.track')).write_text(track)
            props = root / 'p.properties'
            props.write_text('nPlayers=8\n')
            launched = []
            interrupted = []

            def fake_java(jvms, command, stream, timeout):
                track = command[command.index('--track') + 1]
                launched.append(track)
                if track == 'b' and not interrupted:
                    interrupted.append(True)
                    deadline = time.monotonic() + 10  # b races a while: a is published first
                    while not (root / 'out' / 'a.complete.json').exists() and time.monotonic() < deadline:
                        time.sleep(0.01)
                    _thread.interrupt_main()
                    deadline = time.monotonic() + 10
                    while not jvms.stopped and time.monotonic() < deadline:
                        time.sleep(0.01)
                    return -15 if jvms.stopped else 0  # killed by the grid
                log = command[command.index('--log') + 1]
                lo, hi = map(int, command[command.index('--seed') + 1].split('-'))
                for seed in range(lo, hi + 1):
                    Path(log[:-len('.log')] + '_s%d.log' % seed).write_text(race_log(''), encoding='utf-8')
                stream.write('[optimal] potential built in 0.1s (distance 1536 MiB, total 100 MiB)\n')
                return 0

            env = {'RACING_JAR': str(jar), 'RACING_PROPS': str(props), 'RACING_JAVA': sys.executable,
                   'RACING_TRACKS': ''}
            out = str(root / 'out')
            with mock.patch.dict(os.environ, env), \
                    mock.patch.object(fleet_grid.Jvms, 'run', autospec=True, side_effect=fake_java), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(KeyboardInterrupt):
                    fleet_grid.main(['1-2', '1', out])
                self.assertEqual(['a', 'b'], launched, 'a queued track started after the interrupt')
                self.assertFalse((root / 'out' / 'b.complete.json').exists())
                self.assertEqual(0, fleet_grid.main(['1-2', '1', out]))
            self.assertEqual(['a', 'b', 'b', 'c'], launched)
            record = json.loads((root / 'out' / 'a.complete.json').read_text(encoding='utf-8'))
            self.assertEqual('built', record['potential'])

    def test_stopping_the_grid_ends_its_jvms_and_refuses_new_ones(self):
        import sys
        import threading
        import time
        jvms = fleet_grid.Jvms()
        codes = []
        with tempfile.TemporaryFile('w+') as stream:
            worker = threading.Thread(target=lambda: codes.append(jvms.run(
                [sys.executable, '-c', 'import time; time.sleep(60)'], stream, 120)))
            worker.start()
            deadline = time.monotonic() + 10
            while not jvms.running and time.monotonic() < deadline:
                time.sleep(0.01)
            started = time.monotonic()
            jvms.stop()
            worker.join(15)
            self.assertFalse(worker.is_alive())
            self.assertLess(time.monotonic() - started, 15)
            self.assertEqual(1, len(codes))
            self.assertNotEqual(0, codes[0])
            with self.assertRaises(ValueError):
                jvms.run([sys.executable, '-c', 'pass'], stream, 10)


if __name__ == '__main__':
    unittest.main()
