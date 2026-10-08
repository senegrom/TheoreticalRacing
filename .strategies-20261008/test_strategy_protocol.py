"""Independent structural and request-binding checks for response strategy memory."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import racecraft_validation as validation

class ResponseProtocolTests(unittest.TestCase):
    def encoded(self, node=None, version='rc6'):
        node = node if node is not None else 'a'*64+'_3_2_2'
        memory='R_'+node+'~'+'b'*64+'.-'
        return version+',0,2,0,0,0,'+'c'*64+','+memory+';1,1,20,10,0,0,0,0,1,0,0,0,0,1;2,1,25,10,0,0,0,0,1,0,0,0,0,1'
    def test_valid_response(self):
        header,rows=validation.snapshot(self.encoded())
        self.assertEqual((header[0],header[2],len(rows)),(0,0,2))
    def test_bad_masks_and_horizons(self):
        for tail in ('0_2_2','512_2_2','3_0_2','3_4_2','3_2_0','3_2_10','03_2_2'):
            with self.subTest(tail=tail),self.assertRaises(ValueError): validation.snapshot(self.encoded('a'*64+'_'+tail))
    def test_duplicates_and_sort_order(self):
        a='a'*64+'_3_2_2';b='b'*64+'_3_1_2'
        for value in (a+'!'+a,b+'!'+a):
            with self.assertRaises(ValueError): validation.snapshot(self.encoded(value))
    def test_bound_and_version(self):
        with self.assertRaises(ValueError): validation.snapshot(self.encoded(version='rc5'))
        nodes='!'.join(f'{i:064x}_3_1_2' for i in range(257))
        with self.assertRaises(ValueError): validation.snapshot(self.encoded(nodes))
    def test_full_request_binds_strategy(self):
        first=dict(actual='E',snapshot=self.encoded())
        second=dict(actual='E',snapshot=self.encoded('a'*64+'_5_2_2'))
        self.assertNotEqual(validation.sha(validation.query(first,300)),validation.sha(validation.query(second,300)))

if __name__=='__main__': unittest.main()
