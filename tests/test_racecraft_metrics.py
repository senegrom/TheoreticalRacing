"""The screen reports' diagnostics (tracks/racecraft_metrics.py) and the
wrappers' --props, --players 4 and --reverse. No Java: logs are written here,
grids get manifests and completion markers from the real fleet runner, and
the wrappers' grid runs are mocked."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tracks import fleet_grid, head_to_head
from tracks import racecraft_metrics as metrics
from tracks.benchmark_io import comparison_profile, read_properties

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


screen = module('metrics_screen', ROOT / 'docs/experiments/duel-lookahead/run_screen.py')
lone = module('metrics_lone', ROOT / 'docs/experiments/duel-lookahead/run_1vfield.py')


def race_log(fates, slots=(), grid='80x30'):
    """A complete race. ``fates`` maps each car to (event, own move) -- FINISH,
    CRASH or TIMEOUT on that own move -- or to None; the race ends when all
    cars but one have retired, and that one is the last survivor."""
    count = len(fates)
    names = {n: chr(64 + n) for n in fates}
    lines = ['# Theoretical Racing 0.3.0 — game log']
    if slots:
        lines.append('# candidate-slots ' + ','.join(map(str, sorted(slots))))
    lines += ['# Grid ' + grid, 'trackLeft=0,0;0,10', 'trackRight=10,0;10,10']
    lines += ['player%d name=%s kind=AI1 start=%d,0' % (n, names[n], n) for n in sorted(fates)]
    own, places = dict.fromkeys(fates, 0), {}
    turn = finished = retired = 0
    while retired < count - 1:
        for n in sorted(fates):
            if n in places or retired == count - 1:
                continue
            turn += 1
            own[n] += 1
            event, at = fates[n] or ('', 0)
            outcome = 'ok'
            if own[n] == at:
                places[n] = finished + 1 if event == 'FINISH' else count - (retired - finished)
                retired += 1
                finished += event == 'FINISH'
                outcome = '%s place=%d' % (event, places[n])
            lines.append('%d p%d AI1 E v(0,0)→(1,0) (%d,0)→(%d,0) %s' % (turn, n, n, n + 1, outcome))
        if turn > 1000:
            raise AssertionError('these fates never end the race')
    for n in fates:
        places.setdefault(n, finished + 1)
    lines.append('# results')
    lines += ['%d. %s' % (p, names[n]) for n, p in sorted(places.items(), key=lambda item: item[1])]
    return '\n'.join(lines) + '\n'


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


class MetricsTests(unittest.TestCase):
    def test_only_equal_place_real_finishers_contribute_time(self):
        m = metrics.MatchedMetrics()
        m.add({1: 1}, {1: 1}, {1: 10}, {1: 12}, {1: 'FINISH'}, {1: 'FINISH'}, 1)
        for fate in ('CRASH', 'TIMEOUT', None):
            m.add({1: 2}, {1: 2}, {1: 1}, {1: 99}, {} if fate is None else {1: fate}, {1: 'FINISH'}, 1)
        m.add({1: 1}, {1: 2}, {1: 3}, {1: 4}, {1: 'FINISH'}, {1: 'FINISH'}, 1)
        self.assertEqual([-2], m.time)
        self.assertEqual(4, m.places['tie'])
        self.assertEqual(1, m.places['gain'])
        self.assertEqual(1, m.fates[0]['SURVIVOR'])
        lines = m.lines()
        self.assertEqual('same-seat place comparisons, candidate against champion: gains 1, losses 0, ties 4', lines[0])
        self.assertIn('-2.000 moves', '\n'.join(lines))

    def test_track_and_family_sensitivity(self):
        self.assertEqual('fractal', metrics.family('fractal23'))
        self.assertEqual('serpentine', metrics.family('serpentine2'))
        self.assertEqual('spiral', metrics.family('spiral'))
        self.assertEqual([
            "excluding the candidate's strongest track fractal1 (contributes -0.333 to the reading): "
            '-0.150 places (2 track-seed units)',
            'leave-one-track-out over 3 tracks: least favourable to the candidate -0.150 without fractal1, '
            'most favourable -0.750 without hairpin',
            "excluding the candidate's strongest family fractal (contributes -0.500 to the reading): "
            '+0.200 places (1 track-seed units)',
            'leave-one-family-out over 2 families: least favourable to the candidate +0.200 without fractal, '
            'most favourable -0.750 without hairpin',
        ], metrics.sensitivity({'fractal1': [-1.], 'fractal2': [-.5], 'hairpin': [.2]}))
        self.assertEqual([], metrics.sensitivity({}))

    def test_the_strongest_family_is_chosen_by_its_summed_gain(self):
        # Review, 2026-10-19: chosen by its MEAN, one course (spiral) beat a
        # family that carries more of the gain. Here fractal carries -1.5 of
        # the -2.5 summed gain; spiral has the larger mean, and leaving it out
        # is still the least favourable reading, which the second line shows.
        units = {'fractal1': [-.25, -.25], 'fractal2': [-.25, -.25], 'fractal3': [-.25, -.25],
                 'spiral': [-.5, -.5], 'hairpin': [0., 0.]}
        lines = metrics.sensitivity(units)
        self.assertEqual("excluding the candidate's strongest family fractal (contributes -0.150 to the reading): "
                         '-0.250 places (4 track-seed units)', lines[2])
        self.assertEqual('leave-one-family-out over 3 families: least favourable to the candidate -0.188 '
                         'without spiral, most favourable -0.312 without hairpin', lines[3])

    def test_a_loss_on_one_course_shows_and_ties_name_nothing(self):
        # Review, 2026-10-19: a loss that sits on one course (320 diverse:
        # Nordschleife) was invisible, and a tied screen named a 'strongest' track.
        lines = metrics.sensitivity({'bigoval': [0., 0.], 'monaco': [0., 0.], 'nordschleife': [1., .5]},
                                    'old champion entrant')
        self.assertEqual(["excluding the old champion entrant's strongest track: no track contributes a gain for it",
                          'leave-one-track-out over 3 tracks: least favourable to the old champion entrant '
                          '+0.375 without bigoval or one other, most favourable +0.000 without nordschleife'], lines[:2])
        tied = metrics.sensitivity({'bigoval': [0., 0.], 'monaco': [0., 0.]})
        self.assertEqual(["excluding the candidate's strongest track: no track contributes a gain for it",
                          'leave-one-track-out over 2 tracks: +0.000 whichever track is left out'], tied[:2])
        self.assertEqual(['leave-one-track-out: at least two tracks required',
                          'leave-one-family-out: at least two families required'],
                         metrics.sensitivity({'hairpin': [-1.]}))

    def test_tied_groups_are_counted_not_hidden(self):
        lines = metrics.sensitivity({'hairpin': [-1.], 'monaco': [-1.], 'spa': [-1.],
                                     'bigoval': [0.], 'circle': [0.], 'gear': [0.]})
        self.assertEqual(["excluding the candidate's strongest track hairpin (contributes -0.167 to the reading, "
                          'as do 2 other tracks): -0.400 places (5 track-seed units)',
                          'leave-one-track-out over 6 tracks: least favourable to the candidate -0.400 without '
                          'hairpin or any of 2 others, most favourable -0.600 without bigoval or any of 2 others'],
                         lines[:2])
        lines = metrics.sensitivity({'fractal1': [-1.], 'fractal2': [-1.], 'hybrid1': [-1.], 'hybrid2': [-1.],
                                     'monaco': [0.]})
        self.assertEqual("excluding the candidate's strongest family fractal (contributes -0.400 to the reading, "
                         'as does one other family): -0.667 places (3 track-seed units)', lines[2])

    def test_model_coefficients_are_embedded_not_merely_path_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            p, m = Path(temp) / 'p.properties', Path(temp) / 'model.properties'
            out = Path(temp) / 'out.properties'
            m.write_text('schema=paired-ridge-1\nplace=1,2\n', encoding='utf-8')
            # Forward slashes: a backslash is a properties escape (it broke this on Windows).
            p.write_text(f'racecraftModel={m.as_posix()}\nexampleArm=on\n', encoding='utf-8')
            out.write_text(metrics.profile_text(p, {'nPlayers': '4'}), encoding='utf-8')
            values = read_properties(out)
            self.assertNotIn('racecraftModel', values)
            self.assertEqual('1,2', values['racecraftModel.place'])
            self.assertEqual('on', values['exampleArm'])
            self.assertEqual('4', values['nPlayers'])
            m.write_text('place=9,9\n', encoding='utf-8')
            self.assertEqual('1,2', read_properties(out)['racecraftModel.place'])

    def test_canonical_profiles_read_as_the_old_verbatim_ones(self):
        # The JVM's map, and the mirrored grids' comparison fingerprint, are
        # those of the old line-filtered copies; only the bytes differ.
        base_path = ROOT / 'tracks/lap_bench.properties'
        base = base_path.read_text(encoding='utf-8')
        base = '\n'.join(line for line in base.splitlines()
                         if line.partition('=')[0].strip() not in {'nPlayers', 'candidateSlots', 'aiStartPlacement'}) + '\n'
        with tempfile.TemporaryDirectory() as temp:
            for players, slots in ((2, '1'), (4, '2,4'), (8, '1,3,5,7'), (8, '')):
                old, new = Path(temp) / 'old.properties', Path(temp) / 'new.properties'
                old.write_text(base + f'nPlayers={players}\naiStartPlacement=informed\n'
                               + (f'candidateSlots={slots}\n' if slots else ''), encoding='utf-8')
                new.write_text(metrics.profile_text(base_path, {'nPlayers': str(players), 'aiStartPlacement': 'informed',
                                                                'candidateSlots': slots}), encoding='utf-8')
                expected = read_properties(old)
                expected.setdefault('candidateSlots', '')  # RaceGame reads empty as absent
                self.assertEqual(expected, read_properties(new))
                self.assertEqual(comparison_profile(old), comparison_profile(new))
                new.read_bytes().decode('ascii')


class WrapperTests(unittest.TestCase):
    def test_four_car_screen_carries_the_base_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            jar, props = root / 'candidate.jar', root / 'arm.properties'
            jar.write_bytes(b'fixture only; Java is mocked')
            props.write_text('nPlayers=8\nexampleArm=on\ncandidateSlots=1\n', encoding='utf-8')
            complete = mock.Mock(stdout='verified comparison\n')
            with mock.patch.object(screen, 'run_grid_process') as grid, \
                    mock.patch.object(screen.subprocess, 'run', return_value=complete), \
                    contextlib.redirect_stdout(io.StringIO()):
                status = screen.main(['--jar', str(jar), '--out', str(root / 'out'), '--props', str(props),
                                      '--players', '4', '--modes', 'legacy', '--tracks', 'hairpin'])
            self.assertEqual(0, status)
            self.assertEqual(2, grid.call_count)
            cohorts = [read_properties(root / 'out' / f'4p-legacy-{label}.properties') for label in ('odd', 'even')]
            self.assertEqual(['1,3', '2,4'], [c['candidateSlots'] for c in cohorts])
            for profile in cohorts:
                self.assertEqual(('4', 'legacy', 'on'),
                                 (profile['nPlayers'], profile['aiStartPlacement'], profile['exampleArm']))

    def test_entrant_runner_rotates_every_seat_both_ways(self):
        for reverse, expected in ((False, ['', '1', '2', '3', '4']),
                                  (True, ['1,2,3,4', '2,3,4', '1,3,4', '1,2,4', '1,2,3'])):
            with self.subTest(reverse=reverse), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                jar, p = root / 'racing.jar', root / 'p.properties'
                jar.write_bytes(b'fixture')
                p.write_text('nPlayers=8\nexampleArm=on\n', encoding='utf-8')
                profiles, grids = [], []

                def run_grid(args, jar, props, grid):
                    profiles.append(read_properties(props))
                    grids.append(grid.name)
                with mock.patch.object(lone, 'run_grid', side_effect=run_grid), \
                        mock.patch.object(lone, 'report', return_value='report\n') as report, \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(0, lone.main(['--out', str(root / 'out'), '--jar', str(jar), '--props', str(p),
                                                   '--players', '4', '--tracks', 'hairpin']
                                                  + (['--reverse'] if reverse else [])))
                self.assertEqual(expected, [profile['candidateSlots'] for profile in profiles])
                self.assertTrue(all(profile['exampleArm'] == 'on' and profile['nPlayers'] == '4'
                                    for profile in profiles))
                self.assertIs(reverse, report.call_args.args[3])
                suffix = '-reverse' if reverse else ''
                self.assertEqual(f'4p-legacy{suffix}-control', grids[0])
                self.assertTrue((root / 'out' / f'4p-legacy{suffix}-1vfield.txt').is_file())


class ReportLineTests(unittest.TestCase):
    """The new lines on complete grids; the reading's own lines keep their text."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.java = self.root / 'java'
        self.java.write_bytes(b'fake java for manifest hashing only')
        self.jar = self.root / 'racing.jar'
        self.jar.write_bytes(b'candidate and champion binary')
        (self.root / 'tracks').mkdir()
        for track in ('fractal1', 'hairpin'):
            (self.root / 'tracks' / (track + '.track')).write_text('course ' + track)

    def mirrored(self, name, slots, races):
        directory = self.root / name
        directory.mkdir()
        props = self.root / (name + '.properties')
        props.write_text('nPlayers=2\ncandidateSlots=%d\n' % slots, encoding='utf-8')
        manifest = fleet_grid.manifest_for(self.jar, props, self.java, ['-Xmx1g'], ['fractal1', 'hairpin'], 1, 2)
        for (track, seed), fates in races.items():
            (directory / ('%s_s%d.log' % (track, seed))).write_text(race_log(fates, {slots}), encoding='utf-8')
        publish(directory, manifest, range(1, 3))
        return directory

    def test_mirrored_screen_adds_its_block_after_the_per_car_line(self):
        f, c, t = 'FINISH', 'CRASH', 'TIMEOUT'
        odd = self.mirrored('odd', 1, {('fractal1', 1): {1: (f, 10), 2: None}, ('fractal1', 2): {1: (f, 9), 2: None},
                                       ('hairpin', 1): {1: (c, 3), 2: None}, ('hairpin', 2): {1: None, 2: (t, 5)}})
        even = self.mirrored('even', 2, {('fractal1', 1): {1: (f, 11), 2: None}, ('fractal1', 2): {1: None, 2: (f, 9)},
                                         ('hairpin', 1): {1: (f, 12), 2: None}, ('hairpin', 2): {1: None, 2: (t, 5)}})
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(0, head_to_head.main([str(odd), str(even)]), errors.getvalue())
        lines = output.getvalue().splitlines()
        at = lines.index('per candidate car +0.000 places (standard error 0.204), the unit of the lone-candidate check')
        self.assertEqual('mirrored races 4: candidate minus champion mean place +0.000  '
                         '(standard error 0.408; negative favours the candidate)', lines[at - 1])
        self.assertEqual([
            'same-seat place comparisons, candidate against champion: gains 2, losses 2, ties 4',
            'candidate terminal fates: FINISH=3, CRASH=1, TIMEOUT=1, SURVIVOR=3',
            'champion terminal fates: FINISH=2, CRASH=0, TIMEOUT=1, SURVIVOR=5',
            'equal-place, both FINISH: 1 paired own-time comparisons, candidate minus champion -1.000 moves',
            'Equal-place time is conditional/descriptive; survivors, crashes and timeouts are excluded.',
            "excluding the candidate's strongest track fractal1 (contributes -0.250 to the reading): "
            '+0.500 places (2 track-seed units)',
            'leave-one-track-out over 2 tracks: least favourable to the candidate +0.500 without fractal1, '
            'most favourable -0.500 without hairpin',
            "excluding the candidate's strongest family fractal (contributes -0.250 to the reading): "
            '+0.500 places (2 track-seed units)',
            'leave-one-family-out over 2 families: least favourable to the candidate +0.500 without fractal, '
            'most favourable -0.500 without hairpin',
            '',
            'tracks where the candidate gains most (mean place difference, candidate car-races):',
        ], lines[at + 1:at + 12])
        self.assertEqual('1 tracks favour the candidate, 1 the champion, 0 tied', lines[-1])

    def lone_grids(self, reverse):
        """Two cars, one course, two seeds. The entrant gains seat 1 on seed 1
        and finishes a move sooner in it on seed 2; seat 2 races as the control."""
        f = 'FINISH'
        roster = {1, 2}
        control = {1: {1: None, 2: (f, 8)}, 2: {1: (f, 8), 2: None}}
        seat = {1: {1: {1: (f, 7), 2: None}, 2: {1: (f, 7), 2: None}},
                2: {1: {1: None, 2: (f, 8)}, 2: {1: (f, 8), 2: None}}}
        grids = {}
        for label, slots, races in [('control', roster if reverse else set(), control)] + [
                ('seat%d' % s, roster - {s} if reverse else {s}, seat[s]) for s in (1, 2)]:
            directory = self.root / ('reverse' if reverse else 'lone') / label
            directory.mkdir(parents=True)
            for seed, fates in races.items():
                (directory / ('fractal1_s%d.log' % seed)).write_text(race_log(fates, slots), encoding='utf-8')
            publish(directory, {'jar': 'build', 'tracks': {'fractal1': 'x'}, 'seeds': [1, 2],
                                'comparison': {'properties': 'profile', 'candidate_slots': sorted(slots)}},
                    range(1, 3))
            grids[label] = directory
        return grids

    def test_entrant_report_appends_its_lines_in_the_entrant_labels(self):
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                grids = self.lone_grids(reverse)
                text = lone.report(grids['control'], {1: grids['seat1'], 2: grids['seat2']}, range(1, 3), reverse)
                lines = text.splitlines()
                entrant, resident = ('old champion entrant', 'candidate resident') if reverse else ('candidate', 'champion')
                favour = 'old champion entrant' if reverse else 'candidate'
                self.assertEqual(f'1 tracks favour the {favour}, 0 the {resident if reverse else "champion"}, 0 tied',
                                 lines[-8])
                self.assertEqual([
                    f'same-seat place comparisons, {entrant} against {resident}: gains 1, losses 0, ties 3',
                    f'{entrant} terminal fates: FINISH=3, CRASH=0, TIMEOUT=0, SURVIVOR=1',
                    f'{resident} terminal fates: FINISH=2, CRASH=0, TIMEOUT=0, SURVIVOR=2',
                    f'equal-place, both FINISH: 2 paired own-time comparisons, {entrant} minus {resident} -0.500 moves',
                    'Equal-place time is conditional/descriptive; survivors, crashes and timeouts are excluded.',
                    'leave-one-track-out: at least two tracks required',
                    'leave-one-family-out: at least two families required',
                ], lines[-7:])
                self.assertEqual(reverse, lines[0].startswith('REVERSE ENTRY'))
                self.assertIn('paired track-seeds 2: %s place -0.250  (standard error 0.250; %s)'
                              % (('old champion minus candidate', 'negative means the old champion exploits the new field')
                                 if reverse else ('candidate minus champion', 'negative favours the candidate')), text)

    def test_entrant_report_refuses_a_missing_seat_or_another_field(self):
        grids = self.lone_grids(False)
        with self.assertRaisesRegex(ValueError, 'every seat exactly once'):
            lone.report(grids['control'], {1: grids['seat1']}, range(1, 3))
        log = grids['seat2'] / 'fractal1_s2.log'
        log.write_text(race_log({1: ('FINISH', 8), 2: None}, {2}, grid='90x30'), encoding='utf-8')
        publish(grids['seat2'], {'jar': 'build', 'tracks': {'fractal1': 'x'}, 'seeds': [1, 2],
                                 'comparison': {'properties': 'profile', 'candidate_slots': [2]}}, range(1, 3))
        with self.assertRaisesRegex(ValueError, 'roster or geometry'):
            lone.report(grids['control'], {1: grids['seat1'], 2: grids['seat2']}, range(1, 3))


if __name__ == '__main__':
    unittest.main()
