"""Local logic contracts for the research tooling (no JVM or model promotion)."""
import argparse
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from tracks import chooser_lab as lab


def row(identity='a', family='a'):
    a = [0.0] * 19; b = a.copy(); b[0] = 1
    return {'id': identity, 'race': identity, 'family': family, 'geometry': family, 'teacher': 't',
            'teacher_profile': 'p', 'audit': {'features': {'N': a, 'E': b}, 'scoreChoice': 'N', 'baseline': 'E',
                'teacher': [{'action': 'N', 'outcome': {'verdict': 6}}, {'action': 'E', 'outcome': {'verdict': 3}}]}}


class ChooserLabTests(unittest.TestCase):
    def test_training_direction(self):
        weights = lab.fit([row()], 100, .5, .001)
        self.assertLess(weights[0], 0)
        report = lab.model_report([row()], weights, 0)
        self.assertEqual(report['equal_teacher_value'], 1)
        self.assertEqual(report['mean_teacher_time_regret_on_live'], 0)

    def test_dead_worse_than_any_live(self):
        r = row(); r['audit']['teacher'][1]['outcome']['verdict'] = -1
        self.assertGreater(lab.fit([r], 20, .5, 0)[0], 0)

    def test_unknown_not_training_failure(self):
        r = row(); r['audit']['teacher'][0]['outcome']['verdict'] = lab.INF
        self.assertEqual(lab.teacher_actions(r), [])
        with self.assertRaises(ValueError): lab.fit([r], 10, .1, 0)

    def test_equal_values_not_labels(self):
        r = row(); r['audit']['teacher'][1]['outcome']['verdict'] = 6
        with self.assertRaises(ValueError): lab.fit([r], 10, .1, 0)

    def test_whole_population_separation(self):
        a = row(); b = row('b', 'b'); lab.separate([a], [b])
        for key in ('id', 'race', 'family', 'geometry'):
            c = copy.deepcopy(b); c[key] = a[key]
            with self.assertRaises(ValueError): lab.separate([a], [c])

    def test_bad_hyperparameters(self):
        for parameters in ((0,.1,0),(10,float('nan'),0),(10,.1,-1)):
            with self.assertRaises(ValueError): lab.fit([row()], *parameters)

    def test_focal_replacement_keeps_opponents(self):
        for focal in range(8):
            for density in (1,4,7):
                fixed = lab.lineup(8, focal, density, 'base', 'candidate')
                self.assertEqual(fixed.count('candidate'), density - 1)
                a = fixed.copy(); b = fixed.copy(); a[focal] = 'base'; b[focal] = 'candidate'
                self.assertEqual([i for i in range(8) if a[i] != b[i]], [focal])

    def test_invalid_league_population(self):
        for values in ((8,8,1), (8,0,9), (8,0,0)):
            with self.assertRaises(ValueError): lab.lineup(*values, 'b','c')

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'data.json'; lab.write_new(p, {'x':1})
            with self.assertRaises(FileExistsError): lab.write_new(p, {'x':2})
            self.assertEqual(json.loads(p.read_text()), {'x':1})

    def test_changed_and_missing_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'input'; p.write_text('one'); identity = lab.hashes([p]); lab.unchanged(identity)
            p.write_text('two')
            with self.assertRaises(ValueError): lab.unchanged(identity)
            p.unlink()
            with self.assertRaises(OSError): lab.unchanged(identity)

    def test_pending_dataset_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); (p/'pending.json').write_text('{}')
            with self.assertRaises(ValueError): lab.load([p])

    def test_model_finiteness_and_provenance(self):
        model = {'version':'chooser-distill-v1','features':lab.FEATURES,'weights':[0.0]*19,
                 'margin':.05,'trainingSha256':'a'*64,
                 'training':{k:[] for k in ('race','family','geometry')}, 'validation':{k:[] for k in ('race','family','geometry')}}
        lab.validate_model(model)
        model['weights'][0] = float('nan')
        with self.assertRaises(ValueError): lab.validate_model(model)
        model['weights'][0] = 0; del model['training']
        with self.assertRaises(ValueError): lab.validate_model(model)

    def test_student_falls_back_relative_to_scorer(self):
        report = lab.model_report([row()], [0.0]*19, .05)
        self.assertEqual(report['switches_from_scorer'], 0)
        self.assertEqual(report['mean_teacher_time_regret_on_live'], 3)

    def test_audit_no_hook_is_not_a_prediction_error(self):
        r = {'turn':0,'path':'before-chooser','proposal':'','final':'N','stages':[], 'teacher':[]}
        result = lab.audit_report([r], [])
        self.assertEqual(result['first_errors_by_model'], {})
        self.assertEqual(result['cases'][0]['reason'], 'final_not_forecast')

    def test_retained_profile_changes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'teacher.properties').write_text('chooser.experiments=')
            identity=lab.snapshot_identity(p,['teacher.properties']);lab.verify_snapshots(p,identity)
            (p/'teacher.properties').write_text('chooser.experiments=setup')
            with self.assertRaises(ValueError):lab.verify_snapshots(p,identity)
            with self.assertRaises(ValueError):lab.verify_snapshots(p,{'../elsewhere':'a'})

    def test_source_geometry_must_match(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'course';p.write_text('gameX=10\ngameY=20\ntrackLeft=1,2;3,4\ntrackRight=4,5;6,7\n')
            race=argparse.Namespace(profile={'grid':'10x20','laps':'2','trackLeft':'1,2;3,4','trackRight':'4,5;6,7'})
            lab.verify_geometry(race,p,{'laps':'2'})
            with self.assertRaises(ValueError):lab.verify_geometry(race,p,{'laps':'1'})
            race.profile['trackLeft']='1,2;4,4'
            with self.assertRaises(ValueError):lab.verify_geometry(race,p,{'laps':'2'})

    def test_profile_disables_slots(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)/'base'; out = Path(d)/'out'; base.write_text('candidateSlots=1,2\nnPlayers=2\n')
            args = argparse.Namespace(base=base,out=out,experiments='aware,setup',rounds=12,budget=100,
                    move_budget=200,setup_width=2,audit=False,audit_every=1,model=None,legacy_model=None)
            lab.profile(args)
            from tracks.benchmark_io import read_properties
            self.assertEqual(read_properties(out)['candidateSlots'], '')
            self.assertEqual(base.read_text(), 'candidateSlots=1,2\nnPlayers=2\n')

    def test_legacy_arm_cannot_combine(self):
        args=argparse.Namespace(experiments='legacy-unchecked,aware')
        with self.assertRaises(ValueError):lab.profile(args)


if __name__ == '__main__': unittest.main()
