"""CLI/schema checks for independently enabled contingent and prefix arms."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from tracks import chooser_lab as lab
from tracks.benchmark_io import read_properties


class ContingentPrefixToolingTests(unittest.TestCase):
    def profile(self, flags, *, budget=4096):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/'base.properties'; target=Path(tmp)/'new.properties'
            original=b'nPlayers : 4\nlaps=2\ncandidateSlots=2,4\n# do not change this source\n'
            base.write_bytes(original)
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                code=lab.main(['profile','--base',str(base),'--out',str(target),
                    '--experiments',flags,'--budget',str(budget)])
            self.assertEqual(base.read_bytes(),original)
            values=read_properties(target) if target.exists() else None
            return code,values
    def test_contingent_profile(self):
        code,p=self.profile('contingent')
        self.assertEqual(code,0);self.assertEqual(p['chooser.experiments'],'contingent')
        self.assertEqual(p['candidateSlots'],'');self.assertEqual(p['laps'],'2')
    def test_prefix_is_separate(self):
        self.assertEqual(self.profile('setup,prefix')[0],0)
        self.assertEqual(self.profile('contingent,prefix')[0],0)
    def test_prefix_without_branches_rejected(self):
        self.assertEqual(self.profile('prefix'),(2,None))
    def test_conflicting_models_rejected(self):
        for flags in ('contingent,aware','contingent,student','contingent,assist',
                      'contingent,legacy-guarded','contingent,legacy-unchecked'):
            with self.subTest(flags=flags): self.assertEqual(self.profile(flags),(2,None))
    def test_duplicate_rejected(self):
        self.assertEqual(self.profile('contingent,contingent'),(2,None))
    def test_unknown_rejected(self):
        self.assertEqual(self.profile('contingent,coalition'),(2,None))
    def test_zero_is_valid_identity_control(self):
        code,p=self.profile('contingent,prefix',budget=0)
        self.assertEqual(code,0);self.assertEqual(p['chooser.policyBudget'],'0')
    def test_terminal_comparison_remains_explicit(self):
        code,p=self.profile('contingent,prefix,terminal')
        self.assertEqual(code,0);self.assertEqual(p['chooser.experiments'],'contingent,prefix,terminal')
