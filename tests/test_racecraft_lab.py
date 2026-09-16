"""Contracts for evidence publication, pairwise learning and identity-free models."""
from pathlib import Path
import argparse
import copy
import hashlib
import io
import json
import tempfile
import unittest

from tracks import racecraft_lab as lab
from tracks.forensics_common import CandidateMask, ReplayBoard, Transition


class FakeOracle:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)

    def ask(self, mover, cars):
        outcome = self.outcomes.pop(0)
        return 0, 0, CandidateMask('A' * 9, [Transition(outcome, cars[mover][5], cars[mover][6], 0)] * 9, cars.laps)


def action(name, value, place, moves=1):
    f = [0.0] * len(lab.FEATURES)
    f[0] = value
    return {'direction': name, 'features': f,
            'outcome': {'complete': True, 'place': place, 'own_moves': moves, 'committed': moves}}


def row(family='one', race='a', course='b'):
    return {'id': race * 64 + ':1', 'race_sha256': race * 64, 'course_sha256': course * 64,
            'family': family, 'track': family + '-track', 'move': 1, 'focal': 0, 'players': 2,
            'baseline': lab.DIRNAMES[0], 'actions': [action(lab.DIRNAMES[0], 0, 2), action(lab.DIRNAMES[1], 1, 1)]}


def dataset(directory, rows):
    directory.mkdir()
    for ri, r in enumerate(rows):
        for ai, a in enumerate(r['actions']):
            name = '%d-%d.jsonl' % (ri, ai)
            (directory / name).write_text('{}\n')
            a.update(trace=name, trace_sha256=lab.digest(directory / name))
    text = ''.join(lab.encoded(r) + '\n' for r in rows)
    (directory / 'rows.jsonl').write_text(text)
    manifest = {'schema': 1, 'features': list(lab.FEATURES), 'rows_sha256': lab.digest(directory / 'rows.jsonl'),
                'samples': len(rows), 'family': rows[0]['family'], 'race_sha256': rows[0]['race_sha256'],
                'course_sha256': rows[0]['course_sha256']}
    (directory / 'manifest.json').write_text(lab.encoded(manifest))
    return directory


class RacecraftLabTests(unittest.TestCase):
    def test_place_before_time(self):
        self.assertLess(lab.key(action('E', 0, 1, 1000)), lab.key(action('W', 0, 2, 1)))

    def test_actual_survivor_classification(self):
        cars = ReplayBoard([(10, 10, 0, 0, 0, 0, 0)] * 3, laps=1, turns=0, complete=True)
        # P1 moves; P2/P3 crash; P1 gets first without any further move.
        result = lab.continue_action(FakeOracle(['OK', 'CRASH', 'CRASH']), cars, 0,
                                    lab.DIRNAMES.index('NONE'), {}, 0, 0, 10, io.StringIO())
        self.assertEqual(result['classification'], [1, 3, 2])
        self.assertEqual(result['own_moves'], 1)
        self.assertEqual(result['committed'], 3)
        self.assertEqual(cars.turns, 0)

    def test_partial_prior_classifications_and_slot_wrap(self):
        cars = ReplayBoard([(-100000, -100000, 0, 0, 90, 1, 0),
                            (10, 10, 0, 0, 0, 0, 0), (20, 10, 0, 0, 0, 0, 0)],
                           laps=1, turns=20, complete=True)
        result = lab.continue_action(FakeOracle(['TIMEOUT']), cars, 2, lab.DIRNAMES.index('NONE'),
                                    {0: 1}, 1, 0, 10, io.StringIO())
        self.assertEqual(result['classification'], [1, 2, 3])

    def test_solo_requires_terminal_move(self):
        cars = ReplayBoard([(10, 10, 0, 0, 0, 0, 0)], laps=1, turns=0, complete=True)
        result = lab.continue_action(FakeOracle(['OK', 'FINISH']), cars, 0, lab.DIRNAMES.index('NONE'),
                                    {}, 0, 0, 10, io.StringIO())
        self.assertEqual(result['own_moves'], 2)
        self.assertEqual(result['place'], 1)

    def test_budget_does_not_label_an_unfinished_race(self):
        cars = ReplayBoard([(10, 10, 0, 0, 0, 0, 0)] * 2, laps=1, turns=0, complete=True)
        result = lab.continue_action(FakeOracle(['OK']), cars, 0, lab.DIRNAMES.index('NONE'),
                                    {}, 0, 0, 1, io.StringIO())
        self.assertFalse(result['complete'])
        self.assertIsNone(result['place'])

    def test_whole_censored_decision_excluded(self):
        r = row()
        r['actions'][1]['outcome'] = {'complete': False, 'place': None, 'own_moves': None}
        self.assertEqual(lab.usable([r]), [])
        with self.assertRaises(ValueError):
            lab.fit([r], 10, .5, .01)

    def test_training_learns_comparative_direction(self):
        rows = [row()]
        w = lab.fit(rows, 100, .5, .001)
        self.assertLess(w[0], 0)
        self.assertEqual(w[1:], [0.0] * 11)
        self.assertEqual(lab.report(rows, w, .05)['mean_counterfactual_place_delta'], -1)
        self.assertEqual(w, lab.fit(rows, 100, .5, .001))

    def test_nonfinite_or_identity_features_rejected(self):
        for v in (float('nan'), float('inf'), 'trackname', 3, True):
            f = [0.0] * 12
            f[0] = v
            with self.assertRaises(ValueError):
                lab.check_features(f)
        with self.assertRaises(ValueError):
            lab.check_features([0.0] * 13)

    def test_group_and_geometry_leakage_rejected(self):
        train = [row()]
        for holdout in ([row('two', 'c', 'b')], [row('one', 'c', 'd')], [row('two', 'a', 'd')]):
            with self.assertRaises(ValueError):
                lab.separation(train, holdout)
        lab.separation(train, [row('two', 'c', 'd')])

    def test_dataset_hashes_and_trace_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            p = dataset(Path(temp) / 'data', [row()])
            self.assertEqual(len(lab.load_datasets([p])[0]), 1)
            (p / '0-0.jsonl').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'trace hash'):
                lab.load_datasets([p])

    def test_duplicate_decisions_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p = dataset(Path(temp) / 'data', [row()])
            with self.assertRaisesRegex(ValueError, 'duplicate decision'):
                lab.load_datasets([p, p])

    def test_pending_dataset_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            (p / 'rows.pending.jsonl').write_text(lab.encoded(row()))
            with self.assertRaises(FileNotFoundError):
                lab.load_datasets([p])

    def test_complete_outcome_bounds(self):
        with tempfile.TemporaryDirectory() as temp:
            r = row()
            r['actions'][0]['outcome']['place'] = 3
            p = dataset(Path(temp) / 'data', [r])
            with self.assertRaisesRegex(ValueError, 'invalid complete outcome'):
                lab.load_datasets([p])

    def test_end_to_end_training_export_holdout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            train = dataset(root / 'train', [row()])
            val = dataset(root / 'val', [row('two', 'c', 'd')])
            test = dataset(root / 'test', [row('three', 'e', 'f')])
            model = root / 'model.json'
            args = argparse.Namespace(train=[train], validation=[val], out=model, epochs=20, rate=.5, l2=.001, margin=.05)
            lab.train(args)
            lab.evaluate(argparse.Namespace(model=model, data=[test], out=root / 'eval.json'))
            with self.assertRaisesRegex(ValueError, 'untouched holdout'):
                lab.evaluate(argparse.Namespace(model=model, data=[val], out=root / 'bad.json'))
            base = root / 'base.properties'
            base.write_text('nPlayers=2\nplayer1Kind=AI1\nplayer2Kind=AI1\n')
            lab.profile(argparse.Namespace(base=base, out=root / 'arm.properties',
                                         experiments='interaction,opportunity,encounter,learned', model=model,
                                         rounds=2, extra_rounds=1, budget=96, extension_budget=64, alternatives=2))
            props = lab.read_properties(root / 'arm.properties')
            self.assertEqual(props['racecraft.model.features'], ','.join(lab.FEATURES))
            self.assertEqual(props['candidateSlots'], '')
            self.assertEqual(len(props['racecraft.model.weights'].split(',')), 12)
            self.assertNotIn('racecraft', base.read_text())
            with self.assertRaises(FileExistsError):
                lab.train(args)

    def test_models_need_finite_weights_and_schema(self):
        model = {'version': 1, 'features': list(lab.FEATURES), 'weights': [0.] * 12, 'margin': .05, 'trainingSha256': 'a' * 64}
        lab.validate_model(model)
        for key, value in (('version', 2), ('weights', [float('nan')] * 12), ('margin', -1), ('trainingSha256', ''), ('trainingSha256', None), ('weights', None), ('version', True)):
            broken = dict(model, **{key: value})
            with self.assertRaises(ValueError):
                lab.validate_model(broken)

    def test_model_margin_keeps_control(self):
        self.assertEqual(lab.report([row()], [-.01] + [0.] * 11, .05)['switches'], 0)

    def test_existing_files_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'evidence'
            lab.write_new(p, 'old')
            with self.assertRaises(FileExistsError):
                lab.write_new(p, 'new')
            self.assertEqual(p.read_text(), 'old')


if __name__ == '__main__':
    unittest.main()
