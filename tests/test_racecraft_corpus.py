from pathlib import Path
import hashlib
import importlib.util
import unittest

FILE = Path(__file__).resolve().parents[1] / 'tools' / 'racecraft_corpus.py'
spec = importlib.util.spec_from_file_location('racecraft_corpus', FILE)
corpus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(corpus)


def snapshot(positions=((10, 10, 0, 0), (20, 10, 0, 0), (30, 10, 0, 0))):
    rows = [[i + 1, 1, *p, 0, 0, 1, 0, 0, 0, 0, 1] for i, p in enumerate(positions)]
    return 'rc3,0,1,0,0,0,identity;' + ';'.join(','.join(map(str, r)) for r in rows)


def case():
    return dict(id='case', actual='E', scorer='E', chooser='N', opening='N',
                shortlist=['E', 'N'], snapshot=snapshot())


def trial(action, place, moves, complete=True):
    trace = ['0:E:11:10:1:0:OK:0:0:1:1:1']
    return dict(action=action, legal=True, complete=complete, place=place, ownMoves=moves,
                status='FINISHED', trace=trace,
                traceSha256=hashlib.sha256('\n'.join(trace).encode()).hexdigest())


class CorpusTests(unittest.TestCase):
    def response(self, *trials):
        return dict(schema=3, baseline='E', rootIdentity='identity', trials=list(trials))

    def test_capture_roundtrip(self):
        line = 'RACECRAFT_STATE ' + snapshot() + '|E|E|N|N|E,N'
        row = corpus.parse_capture('noise\n' + line)[0]
        self.assertEqual(row['actual'], 'E')
        self.assertEqual(row['shortlist'], ['E', 'N'])
        with self.assertRaises(ValueError):
            corpus.parse_capture(line + '\n' + line)

    def test_incomplete_is_not_a_label(self):
        value = corpus.analyze(case(), self.response(trial('E', 2, 3), trial('N', 1, 5, False)))
        self.assertFalse(value['labelled'])
        self.assertNotIn('placeGain', value)

    def test_place_before_time_and_downstream(self):
        value = corpus.analyze(case(), self.response(trial('E', 2, 3), trial('N', 1, 8)))
        self.assertEqual(value['placeGain'], 1)
        self.assertEqual(value['diagnosis'], 'downstream-replacement')

    def test_equal_place_uses_own_time(self):
        value = corpus.analyze(case(), self.response(trial('E', 1, 9), trial('N', 1, 7)))
        self.assertEqual(value['placeGain'], 0)
        self.assertEqual(value['ownMoveGain'], 2)

    def test_tie_keeps_observed_action(self):
        value = corpus.analyze(case(), self.response(trial('N', 1, 7), trial('E', 1, 7)))
        self.assertEqual(value['best'], 'E')
        self.assertEqual(value['diagnosis'], 'no-observed-regret')

    def test_missing_or_corrupt_control_rejected(self):
        with self.assertRaises(ValueError):
            corpus.analyze(case(), self.response(trial('N', 1, 7)))
        response = self.response(trial('E', 1, 7))
        response['trials'][0]['traceSha256'] = 'wrong'
        with self.assertRaises(ValueError):
            corpus.analyze(case(), response)

    def test_wrong_root(self):
        response = self.response(trial('E', 1, 7))
        response['rootIdentity'] = 'another-board'
        with self.assertRaises(ValueError):
            corpus.analyze(case(), response)

    def test_shortlist_not_forecast_error(self):
        value = corpus.analyze(case(), self.response(trial('E', 3, 7), trial('SE', 1, 9)))
        self.assertEqual(value['diagnosis'], 'shortlist-exclusion')

    def test_indirect_influence_is_shadow_only(self):
        value = corpus.influence_diagnostic(snapshot())
        self.assertEqual(value['direct'], [2])
        self.assertEqual(value['twoHop'], [2, 3])
        self.assertTrue(value['shadowOnly'])
        self.assertFalse(value['geometryClipped'])

    def test_closing_speed_not_initial_distance(self):
        value = corpus.influence_diagnostic(snapshot(((10, 10, 0, 0), (40, 10, -12, 0))), 2)
        self.assertIn(2, value['direct'])

    def test_unknown_diagnosis_stays_broad(self):
        record = case(); record['chooser'] = 'E'
        value = corpus.analyze(record, self.response(trial('E', 3, 7), trial('N', 1, 9)))
        self.assertEqual(value['diagnosis'], 'forecast-horizon-or-ranking')


if __name__ == '__main__':
    unittest.main()
