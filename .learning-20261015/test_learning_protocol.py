import copy
from fractions import Fraction
from pathlib import Path
import random
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import racecraft_learning_memory as memory
import racecraft_league as league
import racecraft_validation as validation
import racecraft_corpus as corpus

class LearningProtocolTests(unittest.TestCase):
    def test_segment_kinematics(self):
        start='20_8_1_0_0_1_1';end='25_8_3_0_0_1_1'
        memory.segment(start+'~E+E~'+end)
        with self.assertRaises(ValueError): memory.segment(start+'~E+E~26_8_3_0_0_1_1')
    def test_crossing_not_a_corner(self):
        with self.assertRaises(ValueError): memory.segment('20_8_1_0_0_1_1~E~22_8_2_0_1_1_1')
    def test_archive_duplicate(self):
        segment='20_8_1_0_0_1_1~E+E~25_8_3_0_0_1_1'
        with self.assertRaises(ValueError): memory.validate(segment+'/'+segment+'@-@-',1)
    def test_trail_continuity(self):
        a='20_8_1_0_0_1_1~E~22_8_2_0_0_1_1'
        b='23_8_2_0_0_1_1~E~26_8_3_0_0_1_1'
        with self.assertRaises(ValueError): memory.validate('-@'+a+'/'+b+'@-',1)
    def test_proof_table(self):
        key='a'*64
        self.assertEqual(memory.validate('-@-@1_50!'+key+'_E_2',1)['proofStates'],1)
        with self.assertRaises(ValueError): memory.validate('-@-@1_50!'+key+'_E_2!'+key+'_N_1',1)
        with self.assertRaises(ValueError): memory.validate('-@-@1_50!'+key+'_E_0',1)
    def test_rc7(self):
        trail='20_8_1_0_0_1_1~E~22_8_2_0_0_1_1'
        text='rc7,1,2,0,0,0,'+'a'*64+',-,-@'+trail+'@-.-@-@-;1,1,22,8,2,0,0,0,1,0,0,0,0,1;2,1,30,8,0,0,0,0,1,0,0,0,0,1'
        h,rows=validation.snapshot(text);self.assertEqual(h[0],1)
        self.assertEqual(corpus.board(text)[1],rows)
        other=text.replace(trail,'20_8_1_0_0_1_1~NONE~21_8_1_0_0_1_1')
        self.assertNotEqual(validation.sha(validation.query(dict(snapshot=text,actual='E'),10)),
                            validation.sha(validation.query(dict(snapshot=other,actual='E'),10)))
    def test_empty_noncanonical_memory(self):
        with self.assertRaises(ValueError): memory.validate('-@-@-',1)
    def test_genome_mutation_reproducible(self):
        a=random.Random(17);b=random.Random(17)
        self.assertEqual([league.mutate('g_0_20_4',a) for _ in range(20)],
                         [league.mutate('g_0_20_4',b) for _ in range(20)])
    def test_own_place_precedes_time(self):
        self.assertLess(league.fitness([(1,100)]),league.fitness([(2,1)]))
        self.assertEqual(league.fitness([(1,2),(2,4)]),(Fraction(3,2),Fraction(3)))
    def test_bad_genomes(self):
        for name in ('g_1_21_4','g_01_20_4','g_0_20_13','team','target'):
            with self.assertRaises(ValueError): league.profile(name)
    def test_league_request_binding(self):
        with self.assertRaises(ValueError): league.validate_answer({},'different',
            dict(schema=1,requestSha256=validation.sha('request'),maxMoves=10),10,['champion','scorer'])
    def test_league_incomplete_never_fitness(self):
        case=dict(snapshot='rc3,0,1,0,0,0,'+'a'*64+';1,1,10,8,0,0,0,0,1,0,0,0,0,1;2,1,20,8,0,0,0,0,1,0,0,0,0,1')
        request='test';names=['champion','scorer']
        response=dict(schema=1,requestSha256=validation.sha(request),maxMoves=10,profiles='/'.join(names),
            trial=dict(action='E',legal=True,complete=False,place=0,ownMoves=0,status='RUNNING',trace=[],
                traceSha256=validation.sha(''),finalState=case['snapshot']))
        with self.assertRaises(ValueError): league.validate_answer(case,request,response,10,names)
