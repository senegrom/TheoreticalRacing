from pathlib import Path
import copy
import importlib.util
import unittest

from test_racecraft_corpus import case, trial, snapshot, encode, corpus

FILE = Path(__file__).resolve().parents[1] / 'tools' / 'racecraft_breeder.py'
spec = importlib.util.spec_from_file_location('racecraft_breeder', FILE)
breeder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(breeder)


def response(prefix=None, complete=True):
    prefix = [] if prefix is None else prefix
    record = case()
    action = prefix[0] if prefix else record['actual']
    tail = trial(action, True, complete=complete)
    actions = [r.split(':')[1] for r in tail['trace'] if r.startswith('0:')]
    endpoint = None
    if not prefix: endpoint = record['snapshot']
    elif len(prefix) == 1 and len(actions) > 1:
        _, rows = corpus.board(snapshot())
        first = tail['trace'][0].split(':')
        rows[0][2:6] = list(map(int, first[2:6]))
        endpoint = encode(2, 0, 0, 0, rows)
    answer = dict(schema=1, requestSha256=corpus.validation.sha(breeder.request(record, prefix, 10)),
                  rootIdentity='a' * 64, baseline='E', maxMoves=10, prefix=prefix,
                  validPrefix=True, forcedExecuted=min(len(prefix),len(actions)), endpoint=endpoint,
                  legalNext=['N','E'] if endpoint else [], ownActions=actions, seeds=[], trial=tail)
    return record, answer


class BreederTests(unittest.TestCase):
    def test_completed_control(self):
        c, a = response()
        self.assertIsNotNone(breeder.validate(c, [], a, 10))

    def test_reachable_prefix_endpoint(self):
        c, a = response(['E'])
        self.assertIsNotNone(breeder.validate(c, ['E'], a, 10))

    def test_multi_move_prefix(self):
        c, a = response(['E','E'])
        self.assertIsNotNone(breeder.validate(c, ['E','E'], a, 10))

    def test_wrong_second_action(self):
        c, a = response(['E','N'])
        with self.assertRaises(ValueError): breeder.validate(c, ['E','N'], a, 10)

    def test_complete_request_bound(self):
        c, a = response()
        with self.assertRaises(ValueError): breeder.validate(c, [], a, 9)

    def test_dynamic_root_bound(self):
        c, a = response()
        c['snapshot'] = c['snapshot'].replace('rc3,0,', 'rc3,1,')
        with self.assertRaises(ValueError): breeder.validate(c, [], a, 10)

    def test_endpoint_cannot_be_invented(self):
        c, a = response(['E'])
        h, rows = corpus.board(a['endpoint']); rows[0][2] += 1
        a['endpoint'] = encode(2,0,0,0,rows)
        with self.assertRaises(ValueError): breeder.validate(c, ['E'], a, 10)

    def test_truncated_not_labelled(self):
        c, a = response(complete=False)
        self.assertIsNone(breeder.validate(c, [], a, 10))

    def test_invalid_not_complete(self):
        c, a = response(); a['validPrefix'] = False
        with self.assertRaises(ValueError): breeder.validate(c, [], a, 10)

    def test_false_continuation(self):
        c, a = response(); a['ownActions'] = ['W']
        with self.assertRaises(ValueError): breeder.validate(c, [], a, 10)

    def test_bad_legal_children(self):
        c, a = response(); a['legalNext'] = ['E','E']
        with self.assertRaises(ValueError): breeder.validate(c, [], a, 10)

    def test_missing_endpoint(self):
        c, a = response(['E']); a['endpoint'] = None; a['legalNext'] = []
        with self.assertRaises(ValueError): breeder.validate(c, ['E'], a, 10)

    def test_prefix_limit(self):
        with self.assertRaises(ValueError): breeder.request(case(), ['E'] * 5, 10)

    def test_place_before_time(self):
        self.assertGreater(breeder.quality(dict(place=3,ownMoves=1),dict(place=1,ownMoves=100)),(0,0))
        self.assertLess(breeder.quality(dict(place=1,ownMoves=100),dict(place=2,ownMoves=1)),(0,0))

    def test_diversity_categories(self):
        c, a = response(); t = a['trial']
        self.assertNotEqual(breeder.descriptor(c,['N'],t,t),breeder.descriptor(c,['S'],t,t))
        changed = copy.deepcopy(t); changed['trace'][1] = changed['trace'][1].replace('NONE','E')
        self.assertNotEqual(breeder.descriptor(c,['N'],t,t),breeder.descriptor(c,['N'],t,changed))


if __name__ == '__main__': unittest.main()
