from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import racecraft_corpus as corpus
from test_racecraft_corpus import snapshot

def response_snapshot(count=1, mask=1):
    old=snapshot();header,rows=old.split(';',1)
    nodes='!'.join(f'{i:064x}_{mask}_1_1' for i in range(count))
    return 'rc6'+header[3:]+',R_'+nodes+'~'+'a'*64+'.-;'+rows

class CreativeMemoryCaptureTests(unittest.TestCase):
    def test_capture_response_memory(self):
        state=response_snapshot()
        parsed=corpus.parse_capture('RACECRAFT_STATE '+state+'|E|E|E|null|E,N|E,N')
        self.assertEqual(parsed[0]['snapshot'],state)
        self.assertEqual(corpus.influence_diagnostic(state)['horizon'],3)
    def test_large_memory_remains_bounded(self):
        state=response_snapshot(256)
        self.assertGreater(len(state),17000)
        self.assertEqual(corpus.board(state)[0][0],'rc6')
    def test_validation_is_not_weakened(self):
        with self.assertRaises(ValueError):corpus.board(response_snapshot(mask=0))
        with self.assertRaises(ValueError):corpus.board(response_snapshot().replace('rc6,','rc7,',1))
