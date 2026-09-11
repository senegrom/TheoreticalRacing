"""The experiment wrapper must preserve profiles and mirror actual roster slots."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1]/'docs/experiments/duel-lookahead/run_screen.py'
SPEC = importlib.util.spec_from_file_location('duel_screen', PATH)
screen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(screen)


class DuelScreenTests(unittest.TestCase):
    def test_profiles_are_idempotent_but_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'profile.properties'
            screen.write_once(path, 'candidateSlots=1\n')
            screen.write_once(path, 'candidateSlots=1\n')
            with self.assertRaises(ValueError):
                screen.write_once(path, 'candidateSlots=2\n')
            self.assertEqual(path.read_text(), 'candidateSlots=1\n')

    def test_mirrors_and_all_start_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'results'
            jar = Path(directory)/'candidate.jar'
            jar.write_bytes(b'fixture only; Java is mocked')
            complete = subprocess.CompletedProcess([], 0, stdout='verified comparison\n')
            with patch.object(screen.subprocess, 'run', return_value=complete) as run:
                status = screen.main(['--jar', str(jar), '--out', str(out), '--tracks', 'hairpin'])
            self.assertEqual(status, 0)
            self.assertEqual(run.call_count, 18)  # 12 grids + 6 independently checked mirror pairs
            for players in (2, 8):
                for mode in ('legacy', 'informed', 'scatter'):
                    cohorts = []
                    for label in ('odd', 'even'):
                        text = (out/f'{players}p-{mode}-{label}.properties').read_text()
                        props = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
                        self.assertEqual(props['nPlayers'], str(players))
                        self.assertEqual(props['aiStartPlacement'], mode)
                        cohorts.append(set(map(int, props['candidateSlots'].split(','))))
                    self.assertFalse(cohorts[0] & cohorts[1])
                    self.assertEqual(cohorts[0] | cohorts[1], set(range(1, players+1)))
                    self.assertEqual(len(cohorts[0]), len(cohorts[1]))
                    self.assertEqual((out/f'{players}p-{mode}-head-to-head.txt').read_text(),
                                     'verified comparison\n')
            for call in run.call_args_list:
                self.assertTrue(call.kwargs['check'])
                if 'env' in call.kwargs:
                    self.assertEqual(call.kwargs['env']['RACING_JAR'], str(jar))
                    self.assertEqual(call.kwargs['env']['RACING_TRACKS'], 'hairpin')

    def test_failed_grid_has_no_performance_report(self):
        with tempfile.TemporaryDirectory() as directory:
            out, jar = Path(directory)/'results', Path(directory)/'candidate.jar'
            jar.write_bytes(b'fixture')
            with patch.object(screen.subprocess, 'run',
                              side_effect=subprocess.CalledProcessError(1, ['fleet'])):
                status = screen.main(['--jar', str(jar), '--out', str(out), '--players', '2',
                                      '--modes', 'legacy', '--tracks', 'hairpin'])
            self.assertEqual(status, 1)
            self.assertFalse(list(out.glob('*head-to-head.txt')))


if __name__ == '__main__':
    unittest.main()
