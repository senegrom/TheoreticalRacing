"""Research contracts and constructed training witnesses; no fleet-gain claims."""
from __future__ import annotations
import copy
import importlib.util
import io
import contextlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tracks'))
sys.path.insert(0, str(ROOT / 'tools'))
import racecraft_metrics as metrics
import racecraft_pairs as pairs
from benchmark_io import read_properties
import fleet_grid


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result

screen = module('research_screen', ROOT / 'docs/experiments/duel-lookahead/run_screen.py')
lone = module('research_lone', ROOT / 'docs/experiments/duel-lookahead/run_1vfield.py')


def pair(track='hairpin', ordinal=1):
    a, b = [0.] * 18, [0.] * 18
    a[4] = b[4] = .020; a[16] = 1.; b[16] = 0.
    return dict(schema=1, engine='a'*64, policy='b'*64, race_id=pairs.hash_text(track + str(ordinal)),
                state_id=pairs.hash_text(track + 'state' + str(ordinal)), track=track,
                family=metrics.family(track), seed=ordinal, seat=0,
                a=dict(action=5, verdict=12, features=a), b=dict(action=4, verdict=12, features=b),
                place_a=1, place_b=2, moves_a=20, moves_b=21, fate_a='FINISH', fate_b='SURVIVOR')


class MetricsTests(unittest.TestCase):
    def test_only_equal_place_real_finishers_contribute_time(self):
        m = metrics.MatchedMetrics()
        m.add({1: 1}, {1: 1}, {1: 10}, {1: 12}, {1: 'FINISH'}, {1: 'FINISH'}, 1)
        for fate in ('CRASH', 'TIMEOUT', None):
            m.add({1: 2}, {1: 2}, {1: 1}, {1: 99}, {} if fate is None else {1: fate}, {1: 'FINISH'}, 1)
        m.add({1: 1}, {1: 2}, {1: 3}, {1: 4}, {1: 'FINISH'}, {1: 'FINISH'}, 1)
        self.assertEqual([-2], m.time); self.assertEqual(4, m.places['tie']); self.assertEqual(1, m.places['gain'])
        self.assertEqual(1, m.fates[0]['SURVIVOR']); self.assertIn('-2.000 moves', '\n'.join(m.lines()))

    def test_track_and_family_sensitivity(self):
        self.assertEqual('fractal', metrics.family('fractal23'))
        lines = metrics.sensitivity({'fractal1': [-1.], 'fractal2': [-.5], 'hairpin': [.2]})
        self.assertIn('excluding strongest track fractal1: -0.150', lines[0])
        self.assertIn('excluding strongest family fractal: +0.200', lines[1])
        self.assertEqual([], metrics.sensitivity({}))

    def test_model_coefficients_are_embedded_not_merely_path_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'p.properties'; m = Path(temp) / 'model.properties'; out = Path(temp) / 'out.properties'
            m.write_text('schema=paired-ridge-1\nplace=1,2\n'); p.write_text(f'racecraftModel={m}\nracecraftFeatures=paired-shadow\n')
            out.write_text(metrics.profile_text(p, {'nPlayers': '4'}))
            values = read_properties(out)
            self.assertNotIn('racecraftModel', values); self.assertEqual('1,2', values['racecraftModel.place'])
            self.assertEqual('paired-shadow', values['racecraftFeatures']); self.assertEqual('4', values['nPlayers'])
            m.write_text('place=9,9\n'); self.assertEqual('1,2', read_properties(out)['racecraftModel.place'])
            with self.assertRaisesRegex(ValueError, 'Embed'):
                fleet_grid.manifest_for(Path(temp)/'missing.jar', p, Path(sys.executable), [], [], 1, 1)

    def test_reverse_runner_rotates_every_old_champion_seat(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); jar = root/'racing.jar'; jar.write_bytes(b'fixture'); p=root/'p.properties'
            p.write_text('nPlayers=4\nracecraftFeatures=contingent\n'); profiles=[]
            with mock.patch.object(lone, 'run_grid', side_effect=lambda a,j,p,g: profiles.append(read_properties(p))), \
                 mock.patch.object(lone, 'report', return_value='report\n') as report, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, lone.main(['--out', str(root/'out'), '--jar', str(jar), '--props', str(p),
                                               '--players', '4', '--reverse', '--tracks', 'hairpin']))
            self.assertEqual(['1,2,3,4', '2,3,4', '1,3,4', '1,2,4', '1,2,3'], [p['candidateSlots'] for p in profiles])
            self.assertTrue(report.call_args.args[3]); self.assertTrue(all(p['racecraftFeatures']=='contingent' for p in profiles))


class PairLearningTests(unittest.TestCase):
    def test_paired_place_learning_with_family_holdout(self):
        data=[pair('fractal1',1), pair('fractal2',2), pair('hairpin',3)]
        model, stats = pairs.fit(data, {'hairpin'})
        self.assertLess(model['place'][16], 0)
        self.assertEqual(2, stats['training_pairs']); self.assertEqual(1, stats['supported_pairs'])
        self.assertEqual(0, stats['place_regret']); self.assertEqual([0.]*18, model['time'])

    def test_time_residual_only_uses_equal_place_actual_finishes(self):
        a=pair(); a.update(place_b=1, fate_b='FINISH', moves_a=18, moves_b=20)
        b=pair('circle'); b.update(place_b=1, fate_b='FINISH', moves_a=18, moves_b=20)
        model, stats=pairs.fit([a,b], {'circle'})
        self.assertEqual(1, stats['time_training_pairs']); self.assertLess(model['time'][16],0)
        self.assertEqual(0,stats['equal_place_time_regret'])

    def test_ood_never_counts_as_validated_prediction(self):
        a=pair(); b=pair('circle'); b['a']['features'][9]=10
        _, stats=pairs.fit([a,b], {'circle'})
        self.assertEqual(1,stats['out_of_domain_pairs']); self.assertEqual(0,stats.get('supported_pairs',0))

    def test_rejects_race_leakage_duplicates_and_incomplete_labels(self):
        a=pair(); b=pair('circle'); b['race_id']=a['race_id']
        with self.assertRaisesRegex(ValueError,'whole race'): pairs.fit([a,b], {'circle'})
        b=copy.deepcopy(a); b['a'],b['b']=b['b'],b['a']
        with self.assertRaisesRegex(ValueError,'duplicate'): pairs.fit([a,b,pair('circle')], {'circle'})
        for update in ({'fate_a':'RUNNING'}, {'engine':'bad'}, {'place_a':True}, {'moves_a':-1}):
            b=pair(); b.update(update)
            with self.assertRaises(ValueError): pairs.validate_pair(b)
        b=pair(); b['a']['features'][0]=float('nan')
        with self.assertRaises(ValueError): pairs.validate_pair(b)
        with self.assertRaisesRegex(ValueError,'held-out'): pairs.fit([a], set())

    def test_train_cli_binds_labels_and_outputs_unpromoted_model(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); labels=root/'labels'; labels.mkdir(); path=labels/'pairs.jsonl'
            path.write_text('\n'.join(json.dumps(p) for p in [pair('fractal1'),pair('hairpin')])+'\n')
            pairs.save_json(labels/'manifest.json',dict(schema=1,complete=True,pairs=pairs.digest(path)))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0,pairs.main(['train','--labels',str(labels),'--holdout-families','hairpin','--out',str(root/'model')]))
            validation=json.loads((root/'model/validation.json').read_text())
            self.assertFalse(validation['promoted']); self.assertFalse(set(validation['training_races']) & set(validation['validation_races']))
            model=read_properties(root/'model/model.properties'); self.assertEqual('paired-ridge-1',model['schema'])
            self.assertTrue(all(math.isfinite(float(v)) for v in model['place'].split(',')))
            path.write_text(path.read_text()+'\n')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertNotEqual(0,pairs.main(['train','--labels',str(labels),'--holdout-families','hairpin','--out',str(root/'bad')]))

    def test_trace_and_terminal_fates_cannot_be_forged_by_partial_tail(self):
        row=dict(engine='a'*64,policy='b'*64)
        tail=dict(engine='a'*64,policy='b'*64,places=[1,2],moves=[2,1],outcomes=['FINISH','SURVIVOR'],
                  trace=['0:5:10,8,0,0:11,8,1,0:FINISH:0,1,1'],complete=True)
        tail['trace_hash']=pairs.hash_text('\n'.join(tail['trace']))
        pairs.validate_tail(tail,row,2)
        self.assertEqual(['0:5:10,8,0,0:11,8,1,0:FINISH:1'],pairs.trace_projection(tail['trace']))
        tail['outcomes'][0]='RUNNING'
        with self.assertRaisesRegex(ValueError,'unresolved'): pairs.validate_tail(tail,row,2)
        tail['complete']=False; pairs.validate_tail(tail,row,2)
        tail['trace_hash']='f'*64
        with self.assertRaisesRegex(ValueError,'digest'): pairs.validate_tail(tail,row,2)


if __name__ == '__main__': unittest.main()
