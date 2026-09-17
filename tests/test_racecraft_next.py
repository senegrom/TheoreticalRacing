"""Second-batch learning, evidence, league and diagnostic contracts."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tracks import racecraft_lab as lab
from tracks import racecraft_next as nxt
from tests.test_racecraft_lab import row as old_row, action as old_action, dataset


def row(family='one', race='a', course='b'):
    r=old_row(family,race,course)
    for a in r['actions']:a['features'] += [0.] * 7
    return r


def model():
    m={'version':2,'features':list(nxt.FEATURES),'weights':[1.]+[0.]*19,
       'timeWeights':[0.,1.]+[0.]*18,'placeRadius':0.,'margin':.05,'trainingSha256':'a'*64}
    for field in ('Families','Courses','Races'):
        m['training'+field]=['train'];m['validation'+field]=['validation']
    return m


def make_dataset(path,rows):
    dataset(path,rows)
    ident={'jar_sha256':'1'*64,'props_sha256':'2'*64,'course_sha256':rows[0]['course_sha256']}
    m=json.loads((path/'manifest.json').read_text())
    m.update(schema=2,features=list(nxt.FEATURES),state_policy='experimental',generating_policy=ident,continuation_policy=ident)
    (path/'manifest.json').write_text(lab.encoded(m))
    return path


class RacecraftNextTests(unittest.TestCase):
    def test_place_has_priority_and_uncertainty_is_not_tie(self):
        m=model();a=[0.,1.]+[0.]*17;b=[1.,0.]+[0.]*17
        self.assertTrue(nxt.better(m,a,b,8));self.assertFalse(nxt.better(m,b,a,8))
        b[0]=0;self.assertTrue(nxt.better(m,b,a,8))
        m['placeRadius']=.6;self.assertFalse(nxt.better(m,b,a,8))
        self.assertIsNone(nxt.predicted_place(m,a,8))

    def test_out_of_range_place_is_unknown(self):
        m=model();m['weights'][-1]=2
        self.assertIsNone(nxt.predicted_place(m,[0.]*19,8))

    def test_actual_ledger_conversion_keeps_source_board(self):
        from tracks.forensics_common import ReplayBoard
        p=object.__new__(nxt.PolicyOracle)
        board=ReplayBoard([(10,10,0,0,0,0,0),(-100000,-100000,0,0,99,0,0),
                           (20,10,0,0,0,0,0)],laps=1,turns=7,complete=True)
        converted=p.classified(board,{1:3},0,1)
        self.assertEqual(converted[1][4],3);self.assertEqual(board[1][4],99)
        with self.assertRaises(ValueError):p.classified(board,{},0,0)
        with self.assertRaises(ValueError):p.classified(board,{0:1,1:3},1,1)

    def test_place_head_ignores_time_values(self):
        rows=[row()];changed=copy.deepcopy(rows)
        changed[0]['actions'][0]['outcome']['own_moves']=100000
        a=nxt.fit_heads(rows,10,.05,.001);b=nxt.fit_heads(changed,10,.05,.001)
        self.assertEqual(a[0],b[0]);self.assertEqual(a[2],0)

    def test_time_head_only_trains_equal_place_pairs(self):
        r=row();r['actions'][1]['outcome']['place']=2;r['actions'][1]['outcome']['own_moves']=2
        _,t,count=nxt.fit_heads([r],100,.05,.001)
        self.assertEqual(count,1);self.assertGreater(t[0],0)

    def test_censored_group_excluded_from_both_heads(self):
        r=row();r['actions'][1]['outcome']={'complete':False,'place':None,'own_moves':None}
        with self.assertRaises(ValueError):nxt.fit_heads([r],10,.05,.001)

    def test_finite_schema_and_split_validation(self):
        m=model();nxt.validate_model(m)
        for key,value in (('version',True),('weights',[float('nan')]*20),('timeWeights',[0]*19),('placeRadius',1.1),('margin',float('inf')),('trainingSha256',''),('trainingFamilies',['validation'])):
            with self.assertRaises(ValueError):nxt.validate_model(dict(m,**{key:value}))

    def test_feature_protocol_compatibility(self):
        lab.check_features([0.]*19,nxt.FEATURES)
        with self.assertRaises(ValueError):lab.check_features([0.]*19)
        with self.assertRaises(ValueError):lab.check_features([0.]*12,nxt.FEATURES)

    def test_regret_separates_omission_from_selection(self):
        r=row();r['audit']={'shortlist':[r['baseline']],'exhausted':True,'completedRounds':1,'reason':'budget'}
        report=nxt.regret_report([r]);d=report['details'][0]
        self.assertEqual(d['place_regret'],1);self.assertTrue(d['best_missing_from_shortlist']);self.assertEqual(d['selection_regret_within_shortlist'],0)
        r['audit']['shortlist']=[a['direction'] for a in r['actions']]
        d=nxt.regret_report([r])['details'][0]
        self.assertFalse(d['best_missing_from_shortlist']);self.assertEqual(d['selection_regret_within_shortlist'],1)

    def test_regret_censors_whole_decision(self):
        r=row();r['actions'][0]['outcome']={'complete':False,'place':None,'own_moves':None}
        report=nxt.regret_report([r]);self.assertEqual(report['usable'],0);self.assertEqual(report['excluded'],1)

    def test_lineup_holds_opponents_fixed_and_rotates(self):
        for focal in range(8):
            for density in (1,4,7):
                fixed=nxt.lineup(8,focal,density,'historical','candidate')
                a=fixed.copy();a[focal]='baseline';b=fixed.copy();b[focal]='candidate'
                self.assertEqual([i for i in range(8) if a[i]!=b[i]],[focal])
                self.assertEqual(b.count('candidate'),density)
                self.assertEqual(a.count('candidate'),density-1)
        for density in (0,9):
            with self.assertRaises(ValueError):nxt.lineup(8,0,density,'b','c')

    def test_source_vs_continuation_identity_required(self):
        with tempfile.TemporaryDirectory() as temp:
            p=make_dataset(Path(temp)/'data',[row()]);self.assertEqual(len(nxt.load([p])[0]),1)
            m=json.loads((p/'manifest.json').read_text());del m['generating_policy'];(p/'manifest.json').write_text(lab.encoded(m))
            with self.assertRaises(ValueError):nxt.load([p])

    def test_dataset_hash_and_declared_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            p=make_dataset(Path(temp)/'data',[row()]);m=json.loads((p/'manifest.json').read_text());m['outputs']={'0-0.jsonl':lab.digest(p/'0-0.jsonl')};(p/'manifest.json').write_text(lab.encoded(m))
            (p/'0-0.jsonl').write_text('modified')
            with self.assertRaises(ValueError):nxt.load([p])

    def test_profile_exports_both_heads_no_slots_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);base=p/'base';base.write_text('nPlayers=2\nplayer1Kind=AI1\nplayer2Kind=AI1\n')
            m=p/'model';m.write_text(lab.encoded(model()));out=p/'out'
            args=argparse.Namespace(experiments='diverse,progressive,lexicographic',base=base,model=m,out=out,
                                    rounds=2,extra_rounds=1,budget=96,extension_budget=64,alternatives=2)
            nxt.profile(args);props=lab.read_properties(out)
            self.assertEqual(props['candidateSlots'],'');self.assertEqual(props['racecraft.model.features'],','.join(nxt.FEATURES))
            self.assertEqual(len(props['racecraft.model.timeWeights'].split(',')),20)
            with self.assertRaises(FileExistsError):nxt.profile(args)

    def test_complete_train_validate_evaluate_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);a=make_dataset(p/'a',[row()]);b=make_dataset(p/'b',[row('two','c','d')]);c=make_dataset(p/'c',[row('three','e','f')])
            model_path=p/'model'
            nxt.train(argparse.Namespace(train=[a],validation=[b],epochs=20,rate=.05,l2=.001,margin=.05,out=model_path))
            nxt.evaluate(argparse.Namespace(model=model_path,data=[c],out=p/'eval'))
            with self.assertRaises(ValueError):nxt.evaluate(argparse.Namespace(model=model_path,data=[b],out=p/'leak'))
            with self.assertRaises(ValueError):nxt.train(argparse.Namespace(train=[a],validation=[a],epochs=20,rate=.05,l2=.001,margin=.05,out=p/'bad'))

    def test_inputs_fail_closed_when_missing_or_changed(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'file';p.write_text('one');inputs=nxt.Inputs([p]);inputs.verify();p.write_text('two')
            with self.assertRaises(ValueError):inputs.verify()
            p.unlink()
            with self.assertRaises(OSError):inputs.verify()


if __name__=='__main__':unittest.main()
