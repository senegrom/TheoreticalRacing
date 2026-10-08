import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import racecraft_validation as v

class TrafficProtocolTests(unittest.TestCase):
    def state(self, memory, version='rc5'):
        return f'{version},0,1,0,0,0,' + 'a'*64 + ',' + memory + ';1,1,20,10,0,0,0,0,1,0,0,0,0,1;2,1,30,10,0,0,0,0,1,0,0,0,0,1'
    def test_bounded_suffix(self):
        v.snapshot(self.state('M_E+N+NE~'+'b'*64+'.-'))
    def test_request_binds_suffix(self):
        a=dict(actual='E',snapshot=self.state('M_E+N~'+'b'*64+'.-'))
        b=dict(actual='E',snapshot=self.state('M_E+S~'+'b'*64+'.-'))
        self.assertNotEqual(v.sha(v.query(a,100)),v.sha(v.query(b,100)))
    def test_rejects_long_or_malformed_suffix(self):
        for p in ('M_E+N+E+N','M_','M_E+BAD','M_E++N','M_E~E'):
            with self.subTest(p=p),self.assertRaises(ValueError):v.snapshot(self.state(p+'~'+'b'*64+'.-'))
    def test_old_version_cannot_smuggle_traffic_memory(self):
        with self.assertRaises(ValueError):v.snapshot(self.state('M_E~'+'b'*64+'.-','rc4'))
    def test_new_version_requires_traffic_memory(self):
        with self.assertRaises(ValueError):v.snapshot(self.state('E~'+'b'*64+'.-'))

if __name__ == '__main__':unittest.main()
