"""The actual promotion entry point must run both requested policy cohorts."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from tracks import promotion_pair as pair, fleet_grid
from tracks.benchmark_io import candidate_slots, configured_players, read_properties, update_properties
from test_benchmark_integrity import race_log
from test_release_gate import block


class PromotionPairTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.jar = self.root / 'candidate.jar'
        self.jar.write_bytes(b'fixture binary; fleet process is mocked')
        self.java = self.root / 'java'
        self.java.write_text('#!/bin/sh\nexit 0\n')
        self.java.chmod(0o755)
        tracks = self.root / 'tracks'
        tracks.mkdir()
        for name in ('hairpin', 'chicane'):
            (tracks / (name + '.track')).write_text('fixture course ' + name)
        self.source = self.root / 'source.properties'
        self.original = (b'# caller bytes stay intact\nnPlayers : 4\nmaxPlayers=9\nlaps=3\n'
                         b'player1Name=Andr\xe9\n' + b''.join(
                             ('player%dKind : AI2\n' % n).encode() for n in range(1, 10)))
        self.source.write_bytes(self.original)
        self.calls = []
        env = mock.patch.dict(os.environ, {key: '' for key in pair.JAVA_OPTIONS})
        env.start()
        self.addCleanup(env.stop)

    def fleet(self, command, *, cwd, env, check):
        self.assertTrue(check)
        self.assertEqual(command[1], str(pair.ROOT / 'tracks/fleet_grid.py'))
        self.assertEqual(command[-2], '1', 'reference-heap JVMs must run serially')
        self.assertEqual(env['RACING_HEAP'], '-Xmx8g')
        self.calls.append(env.copy())
        out = Path(command[-1])
        out.mkdir()
        lo, hi = fleet_grid.seed_range(command[-3])
        seeds = range(lo, hi + 1)
        props = Path(env['RACING_PROPS'])
        settings = read_properties(props)
        roster = configured_players(props)
        slots = settings.get('candidateSlots', '')
        tracks = env['RACING_TRACKS'].split(',')
        manifest = fleet_grid.manifest_for(self.jar, props, self.java, ['-Xmx8g'], tracks, lo, hi)
        text = fleet_grid.json_text(manifest)
        (out / 'manifest.json').write_text(text)
        import hashlib
        run_id = hashlib.sha256(text.encode()).hexdigest()
        for track in tracks:
            logs = []
            for seed in seeds:
                log = out / ('%s_s%d.log' % (track, seed))
                log.write_text('# laps 3\n# start-placement %s\n' % settings['aiStartPlacement'] +
                               race_log(count=len(roster), slots=slots,
                                        names={n: p[0] for n, p in roster.items()},
                                        kinds={n: p[1] for n, p in roster.items()}), encoding='utf-8')
                logs.append({'sha256': fleet_grid.digest(log), 'counts': fleet_grid.parse_log(log)})
            record = dict(run_id=run_id, seeds=list(seeds), no_loop=False, logs=logs)
            (out / (track + '.complete.json')).write_text(fleet_grid.json_text(record))
        return subprocess.CompletedProcess(command, 0)

    def run_pair(self, players=2, mode='legacy', effect=None, extra=()):
        out = self.root / ('pair-%d' % len(list(self.root.glob('pair-*'))))
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(pair.subprocess, 'run', side_effect=effect or self.fleet), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = pair.main(['--out', str(out), '--jar', str(self.jar), '--props', str(self.source),
                                '--java', str(self.java), '--players', str(players), '--start-mode', mode,
                                '--seeds', '1-2', *extra])
        return status, out, stdout.getvalue(), stderr.getvalue()

    def test_complete_mirrors_all_fields_and_start_modes(self):
        for count in (2, 4, 8):
            for mode in ('legacy', 'informed', 'scatter'):
                with self.subTest(count=count, mode=mode):
                    status, out, output, errors = self.run_pair(count, mode)
                    self.assertEqual(status, 0, errors)
                    self.assertIn('candidate car-races', output)
                    self.assertIn('mirrored races 4:', (out / 'head-to-head.txt').read_text())
                    cohorts = []
                    for label in ('odd', 'even'):
                        profile = out / (label + '.properties')
                        players = configured_players(profile)
                        self.assertEqual(len(players), count)
                        self.assertEqual({kind for _, kind in players.values()}, {'AI1'})
                        settings = read_properties(profile)
                        self.assertEqual(settings['aiStartPlacement'], mode)
                        cohorts.append(candidate_slots(settings['candidateSlots']))
                    self.assertEqual(cohorts[0] | cohorts[1], set(range(1, count + 1)))
                    self.assertFalse(cohorts[0] & cohorts[1])
                    self.assertEqual(len(cohorts[0]), len(cohorts[1]))
                    self.assertEqual(self.source.read_bytes(), self.original)

    def test_grid_failure_has_no_comparison(self):
        status, out, output, _ = self.run_pair(effect=subprocess.CalledProcessError(17, ['fleet']))
        self.assertEqual(status, 1)
        self.assertFalse((out / 'head-to-head.txt').exists())
        self.assertNotIn('mean place', output)

    def test_missing_or_wrong_candidate_cohorts_are_rejected(self):
        original = pair.write_profile
        for slots in ('', '1,2'):
            def bad_writer(path, *args):
                roster = original(path, *args)
                update_properties(path, {'candidateSlots': slots})
                return roster
            with self.subTest(slots=slots), mock.patch.object(pair, 'write_profile', side_effect=bad_writer):
                status, out, output, errors = self.run_pair()
            self.assertEqual(status, 1, output)
            self.assertFalse((out / 'head-to-head.txt').exists())
            self.assertIn('promotion pair:', errors)

    def test_wrong_roster_in_complete_logs_is_rejected(self):
        def fake(command, **kw):
            result = self.fleet(command, **kw)
            grid = Path(command[-1])
            for log in grid.glob('*.log'):
                log.write_text(log.read_text().replace('AI1', 'AI2'))
            # Retain complete, checksum-consistent wrong-controller logs: roster
            # validation, not a stale hash, must catch the wrong experiment.
            for path in grid.glob('*.complete.json'):
                record = json.loads(path.read_text())
                for seed, saved in zip(record['seeds'], record['logs']):
                    saved['sha256'] = fleet_grid.digest(grid / (path.name.split('.')[0] + '_s%d.log' % seed))
                path.write_text(fleet_grid.json_text(record))
            return result
        status, out, output, errors = self.run_pair(effect=fake)
        self.assertEqual(status, 1)
        self.assertIn('requested candidate/champion cohorts', errors)
        self.assertNotIn('mean place', output)

    def test_changed_inputs_between_mirrors_fail_before_next_fleet(self):
        for target in (self.jar, self.root / 'tracks/hairpin.track', self.source, self.java):
            before = target.read_bytes()
            calls = len(self.calls)
            def change(command, **kw):
                result = self.fleet(command, **kw)
                target.write_bytes(before + b'changed')
                return result
            with self.subTest(path=target):
                status, out, output, _ = self.run_pair(effect=change)
                self.assertEqual(status, 1)
                self.assertEqual(len(self.calls), calls + 1)
                self.assertFalse((out / 'head-to-head.txt').exists())
                self.assertNotIn('mean place', output)
            target.write_bytes(before)

    def test_final_profile_read_failure_and_assignment_edit_have_no_report(self):
        for edit in (lambda p: p.unlink(), lambda p: p.write_text('bad=\\uNOPE\n'),
                     lambda p: update_properties(p, {'candidateSlots': '1'})):
            calls = 0
            def change(command, **kw):
                nonlocal calls
                result = self.fleet(command, **kw)
                calls += 1
                if calls == 2:
                    edit(Path(kw['env']['RACING_PROPS']))
                return result
            status, out, output, _ = self.run_pair(effect=change)
            self.assertEqual(status, 1)
            self.assertEqual(calls, 2)
            self.assertFalse((out / 'head-to-head.txt').exists())
            self.assertNotIn('mean place', output)

    def test_jvm_environment_override_fails_before_racing(self):
        for key in pair.JAVA_OPTIONS:
            with mock.patch.dict(os.environ, {key: '-Xmx768m'}):
                status, out, _, _ = self.run_pair()
                self.assertEqual(status, 1)
                self.assertFalse(out.exists())
        self.assertEqual(self.calls, [])

    def test_invalid_selection_and_clamped_or_malformed_profile_fail_before_racing(self):
        for extra in (('--tracks', 'hairpin', 'hairpin'), ('--tracks', '../bad'),
                      ('--tracks', 'absent'), ('--seeds', '2-1'), ('--heap=-Xmx8g -Dextra=x',)):
            status, _, _, _ = self.run_pair(extra=extra)
            self.assertEqual(status, 1, extra)
        for data in (self.original + b'maxPlayers=1\n', b'bad=\\uNOPE\n'):
            self.source.write_bytes(data)
            status, _, _, _ = self.run_pair()
            self.assertEqual(status, 1)
            self.assertEqual(self.source.read_bytes(), data)
        self.assertEqual(self.calls, [])

    def test_scorer_failure_has_no_successful_report(self):
        with mock.patch.object(pair.head_to_head, 'main', return_value=2):
            status, out, output, _ = self.run_pair()
        self.assertEqual(status, 1)
        self.assertFalse((out / 'head-to-head.txt').exists())
        self.assertNotIn('mean place', output)

    def test_existing_output_is_never_overwritten(self):
        out = self.root / 'keep'
        out.mkdir()
        sentinel = out / 'head-to-head.txt'
        sentinel.write_text('previous evidence')
        status, _, _, _ = self.run_pair(extra=('--out', str(out)))
        self.assertEqual(status, 1)
        self.assertEqual(sentinel.read_text(), 'previous evidence')
        self.assertEqual(self.calls, [])


class PromotionWorkflowTests(unittest.TestCase):
    def test_workflow_runs_candidate_pairs_not_label_benchmarks(self):
        workflow = (pair.ROOT / '.github/workflows/promotion-gate.yml').read_text()
        battery = block(workflow, '  battery:')
        for line in ('players: [2, 4, 8]', 'mode: [legacy, informed, scatter]',
                     "seeds: ['1-5', '6-10', '11-15']", 'needs: verify', 'max-parallel: 3'):
            self.assertIn(line, battery)
        self.assertIn('python tracks/promotion_pair.py --players "$PLAYERS" --start-mode "$START_MODE"', battery)
        self.assertIn('--seeds "$SEEDS" --heap=-Xmx8g --out promotion-evidence', battery)
        for old in ('bench_ai.py', 'bench_iso.py', '--tracks', 'continue-on-error:'):
            self.assertNotIn(old, battery)
        self.assertIn('path: promotion-evidence/', battery)
        self.assertIn('if: always()', battery)
        for key in pair.JAVA_OPTIONS:
            self.assertIn(key + ": ''", workflow)
        self.assertIn('python tests/promotion_pair_regression.py', block(workflow, '  verify:'))
        ci = (pair.ROOT / '.github/workflows/ci.yml').read_text()
        self.assertIn('python3 tests/promotion_pair_regression.py', block(ci, '  java:'))


if __name__ == '__main__':
    unittest.main()
