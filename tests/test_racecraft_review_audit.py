"""Audit counters must describe executed proposals, not manufacture race results."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("review_audit", ROOT / "docs/experiments/racecraft-review/audit.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class ReviewAuditTests(unittest.TestCase):
    def row(self, turn=0):
        return {"schema": 1, "turn": turn, "player": 1,
                "stages": [{"stage": "scorer", "action": "N"},
                           {"stage": "chooser", "action": "E"},
                           {"stage": "pace", "action": "N"}],
                "candidates": [{"model": "nominal", "action": "N", "verdict": 12}],
                "selected": "N"}

    def summarize(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "race.stderr"
            path.write_text("other diagnostic\n" + "\n".join(rows) + "\n", encoding="utf-8")
            return audit.summarize([path])

    def encoded(self, row):
        return "RACECRAFT_REVIEW " + json.dumps(row)

    def test_proposal_is_not_execution(self):
        report = self.summarize([self.encoded(self.row())])
        self.assertEqual(report["counts"]["chooser_changes_from_scorer"], 1)
        self.assertEqual(report["counts"]["chooser_overridden_before_execution"], 1)
        self.assertEqual(report["counts"]["executed_changes_from_scorer"], 0)
        self.assertEqual(report["stage_changes"]["pace"], 1)
        self.assertIn("not finishing-place", report["interpretation"])

    def test_later_guard_changes_are_counted(self):
        row = self.row()
        row["selected"] = "S"
        report = self.summarize([self.encoded(row)])
        self.assertEqual(report["stage_changes"]["later-guards/final"], 1)
        self.assertEqual(report["counts"]["executed_changes_from_scorer"], 1)

    def test_early_return_has_no_fake_chooser(self):
        row = self.row()
        row["stages"] = []
        row["candidates"] = []
        report = self.summarize([self.encoded(row)])
        self.assertEqual(report["counts"]["no_chooser_decisions"], 1)
        self.assertNotIn("chooser_decisions", report["counts"])

    def test_duplicate_roots_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate root"):
            self.summarize([self.encoded(self.row()), self.encoded(self.row())])

    def test_malformed_schema_rejected(self):
        for row in ([], {"schema": 99}, {"schema": 1}):
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.summarize([self.encoded(row)])
        with self.assertRaises(ValueError):
            self.summarize(["RACECRAFT_REVIEW {invalid"])

    def test_no_decisions_rejected(self):
        with self.assertRaisesRegex(ValueError, "no real-decision"):
            self.summarize(["unrelated diagnostic"])

    def test_retained_and_discarded_proofs_separate(self):
        row = {"schema": 1, "nodes": 20, "cacheHits": 2, "exhausted": True,
               "completedProof": True, "retainedProof": False}
        lines = [self.encoded(self.row()), "RACECRAFT_DUEL " + json.dumps(row)]
        row["retainedProof"] = True
        lines.append("RACECRAFT_DUEL " + json.dumps(row))
        report = self.summarize(lines)
        self.assertEqual(report["counts"]["duel_discarded_proofs"], 1)
        self.assertEqual(report["counts"]["duel_retained_proofs"], 1)
        self.assertEqual(report["counts"]["duel_nodes"], 40)

    def test_boolean_text_not_treated_as_true(self):
        row = {"schema": 1, "nodes": 20, "cacheHits": 2, "exhausted": "false",
               "completedProof": True, "retainedProof": False}
        with self.assertRaisesRegex(ValueError, "invalid duel flag"):
            self.summarize([self.encoded(self.row()), "RACECRAFT_DUEL " + json.dumps(row)])


if __name__ == "__main__":
    unittest.main()
