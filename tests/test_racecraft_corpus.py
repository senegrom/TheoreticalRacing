from pathlib import Path
import copy
import importlib.util
import unittest

FILE = Path(__file__).resolve().parents[1] / 'tools' / 'racecraft_corpus.py'
spec = importlib.util.spec_from_file_location('racecraft_corpus', FILE)
corpus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(corpus)

IDENTITY = 'a' * 64
ROSTER = {1: ('P1', 'AI1'), 2: ('P2', 'AI1')}


def snapshot(positions=((10, 10, 0, 0), (20, 10, 0, 0)), turn=0):
    rows = [[i+1, 1, *p, 0, 0, 1, 0, 0, 0, 0, 1] for i, p in enumerate(positions)]
    return encode(turn, 0, 0, 0, rows)


def encode(turn, slot, first, last, rows):
    return f'rc3,{turn},1,{slot},{first},{last},{IDENTITY};' + ';'.join(','.join(map(str, r)) for r in rows)


def case():
    return dict(id='case', actual='E', scorer='E', chooser='N', opening='N',
                shortlist=['E', 'N'], snapshot=snapshot(), legalActions=['N', 'E'])


def trial(action, finish, *, quick=False, complete=True):
    _, rows = corpus.board(snapshot())
    dx, dy = corpus.DIRECTIONS[action]
    first, last, clock, slot, own = 0, 0, 0, 0, 0
    trace = []
    actions = [(0, action)] if quick or not complete else [(0, action), (1, 'NONE'), (0, action)]
    for k, (actor, direction) in enumerate(actions):
        row = rows[actor]
        ax, ay = corpus.DIRECTIONS[direction]
        vx, vy = row[4]+ax, row[5]+ay
        x, y = row[2]+vx, row[3]+vy
        terminal = complete and k == len(actions)-1
        status = ('FINISH' if finish else 'CRASH') if terminal else 'OK'
        if terminal:
            place = 1 if finish else 2
            first, last = (1, 0) if finish else (0, 1)
            row[2:7] = [-100000, -100000, 0, 0, place]
            rows[1][6] = 3-place
        else:
            place = 0; row[2:6] = [x, y, vx, vy]
        clock += 1; own += actor == 0
        trace.append(f'{actor}:{direction}:{x}:{y}:{vx}:{vy}:{status}:{place}:0:1:1:{clock}')
        slot = actor if terminal else 1-actor
    return dict(action=action, legal=True, complete=complete, place=rows[0][6], ownMoves=own,
                status=('FINISHED' if finish else 'CRASHED') if complete else 'RUNNING', trace=trace,
                traceSha256=corpus.validation.sha('\n'.join(trace)), finalState=encode(clock, slot, first, last, rows))


def response(record, *trials):
    return dict(schema=4, baseline=record['actual'], rootIdentity=IDENTITY, maxMoves=10,
                requestSha256=corpus.validation.sha(corpus.validation.query(record, 10)),
                legalActions=record['legalActions'], trials=list(trials))


def log_of(control):
    _, rows = corpus.board(snapshot())
    lines = []
    for text in control['trace']:
        f = text.split(':'); actor = int(f[0]); row = rows[actor]
        x,y,vx,vy = map(int,f[2:6]); status = 'ok' if f[6] == 'OK' else f[6]
        lines.append(f'{f[11]} p{actor+1} AI1 {f[1]} v({row[4]},{row[5]})→({vx},{vy}) '
                     f'({row[2]},{row[3]})→({x},{y}) {status}' + (f' place={f[7]}' if status != 'ok' else ''))
        row[2:6] = [x,y,vx,vy]
    _, final = corpus.board(control['finalState'])
    lines.append('# results')
    lines.extend(f'{rank}. P{i+1}' for rank in (1,2) for i,row in enumerate(final) if row[6] == rank)
    return '\n'.join(lines)+'\n'


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.case = case()
        self.base, self.alt = trial('E', False), trial('N', True)
        self.answer = response(self.case, self.base, self.alt)
        self.log = log_of(self.base)

    def analyze(self, answer=None, record=None, log=None):
        return corpus.analyze(record or self.case, answer or self.answer, max_moves=10,
                              original_race=self.log if log is None else log, roster=ROSTER)

    def test_capture_roundtrip(self):
        line = 'RACECRAFT_STATE '+snapshot()+'|E|E|N|N|E,N|N,E'
        value = corpus.parse_capture(line)[0]
        self.assertEqual(value['legalActions'], ['N','E'])
        with self.assertRaises(ValueError): corpus.parse_capture(line+'\n'+line)

    def test_place_before_time_and_downstream(self):
        value = self.analyze()
        self.assertEqual(value['placeGain'], 1)
        self.assertEqual(value['diagnosis'], 'downstream-replacement')

    def test_equal_place_uses_own_time(self):
        base, alt = trial('E',True), trial('N',True,quick=True)
        value = self.analyze(response(self.case,base,alt), log=log_of(base))
        self.assertEqual(value['placeGain'], 0)
        self.assertEqual(value['ownMoveGain'], 1)

    def test_tie_keeps_observed_action(self):
        value=self.analyze(response(self.case,self.base,trial('N',False)))
        self.assertEqual(value['best'],'E')

    def test_incomplete_has_no_label(self):
        value=self.analyze(response(self.case,self.base,trial('N',False,complete=False)))
        self.assertFalse(value['labelled'])
        self.assertNotIn('placeGain',value)

    def test_every_legal_action_required(self):
        for trials in ([self.base], [self.base,self.base,self.alt], [self.base,self.alt,trial('S',True)]):
            with self.assertRaises(ValueError): self.analyze(response(self.case,*trials))

    def test_same_policy_identity_different_dynamic_board_rejected(self):
        record=copy.deepcopy(self.case); record['snapshot']=snapshot(((11,10,0,0),(20,10,0,0)),turn=5)
        with self.assertRaises(ValueError): self.analyze(record=record)

    def test_budget_is_bound_to_request(self):
        value=copy.deepcopy(self.answer); value['maxMoves']=20
        with self.assertRaises(ValueError): self.analyze(value)

    def test_malformed_results_rejected(self):
        mutations = [('place',99), ('ownMoves',-1), ('status','RUNNING'), ('finalState',None),
                     ('complete',False), ('legal',False), ('traceSha256','wrong')]
        for key,value in mutations:
            answer=copy.deepcopy(self.answer); answer['trials'][0][key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): self.analyze(answer)

    def test_empty_and_nonsense_traces_rejected_even_with_correct_hash(self):
        for trace in ([], ['not a referee transition']):
            answer=copy.deepcopy(self.answer); answer['trials'][0]['trace']=trace
            answer['trials'][0]['traceSha256']=corpus.validation.sha('\n'.join(trace))
            with self.assertRaises(ValueError): self.analyze(answer)

    def test_control_must_reproduce_more_than_first_action(self):
        altered=self.log.replace('3 p1 AI1 E', '3 p1 AI1 N')
        with self.assertRaises(ValueError): self.analyze(log=altered)

    def test_control_places_must_match_original(self):
        altered=self.log.replace('1. P2\n2. P1','1. P1\n2. P2')
        with self.assertRaises(ValueError): self.analyze(log=altered)

    def test_no_control_log_no_label(self):
        with self.assertRaises(ValueError): self.analyze(log='')

    def test_invalid_kinematics_rejected(self):
        answer=copy.deepcopy(self.answer); t=answer['trials'][0]
        t['trace'][0]=t['trace'][0].replace(':11:10:1:0:',':99:10:1:0:')
        t['traceSha256']=corpus.validation.sha('\n'.join(t['trace']))
        with self.assertRaises(ValueError): self.analyze(answer)

    def test_indirect_influence_is_shadow_only(self):
        value=corpus.influence_diagnostic(snapshot(((10,10,0,0),(20,10,0,0),(30,10,0,0))))
        self.assertEqual(value['direct'],[2]); self.assertEqual(value['twoHop'],[2,3])
        self.assertTrue(value['shadowOnly']); self.assertFalse(value['geometryClipped'])

    def test_closing_speed_not_distance(self):
        self.assertIn(2,corpus.influence_diagnostic(snapshot(((10,10,0,0),(40,10,-12,0))),2)['direct'])


if __name__ == '__main__': unittest.main()
