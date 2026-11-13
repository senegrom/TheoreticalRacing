"""The decision-specimen check and the pins that hold specimens (tests/decision_specimen.py)."""
import ast
from pathlib import Path
import unittest
from unittest import mock

import decision_specimen

ROOT = Path(__file__).resolve().parents[1]

# Every pin with decision specimens, and how many it holds. A specimen is not dropped, added or re-frozen from
# measurement silently (decision_specimen.py says what to do when its race moves): this list changes with it.
SPECIMENS = {
    "ai1_early_round_trap_regression": 1,
    "ai1_field_neutral_regression": 1,
    "ai1_finish_denial_regression": 1,
    "ai1_graduated_field_accel_regression": 1,
    "ai1_pace_regression": 2,
    "ai1_staged_pace_regression": 2,
}

LOG = "\n".join([
    "# Theoretical Racing test log",
    "player 1 A AI2",
    "1 p1 AI2 E v(0,0)→(1,0) (5,5)→(6,5) ok",
    "2 p2 AI2 N v(0,0)→(0,-1) (5,6)→(5,5) ok",
    "# turns 2",
    "# results",
]) + "\n"
SUMMARY = (7, 0, [3, 3, 3, 3, 3, 3, 3])
DECISION = "1 p1 AI E v(0,0)→(1,0) (5,5)→(6,5) ok"


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.bench = decision_specimen.bench_ai
        # as a pin leaves it after racing a frozen fixture: another jar, its own runtime's files
        patch = mock.patch.multiple(self.bench, JAR="fixture/theoreticRacing.jar", LOG="pin/last_game.log",
                                    PROPS="pin/bench.properties")
        patch.start()
        self.addCleanup(patch.stop)
        self.before = (self.bench.JAR, self.bench.LOG, self.bench.PROPS)
        self.calls = []

    def race(self, log=LOG, summary=SUMMARY):
        """bench_ai.run_track replaced by a race that leaves `log` and returns `summary`."""
        bench = self.bench

        def run_track(track, timeout=240, seed=None):
            self.calls.append({
                "track": track,
                "seed": seed,
                "jar": bench.JAR,
                "kinds": [kind for _, kind in bench.configured_players(bench.PROPS).values()],
                "runtime": Path(bench.LOG).parent,
            })
            if log is not None:
                Path(bench.LOG).write_text(log, encoding="utf-8")
            return summary

        return mock.patch.object(bench, "run_track", run_track)

    @staticmethod
    def specimen(**changes):
        fields = {
            "track": "coil",
            "seed": 4,
            "summary": SUMMARY,
            "sha256": decision_specimen.normalized_sha256(LOG),
            "decision": DECISION,
        }
        fields.update(changes)
        return decision_specimen.Specimen(**fields)

    def stops(self, specimen, message, **race):
        with self.race(**race), self.assertRaises(SystemExit) as stop:
            decision_specimen.check("a pin", specimen)
        self.assertEqual(f"a pin decision specimen, coil seed 4: {message}", str(stop.exception.code))
        self.assertEqual(self.before, (self.bench.JAR, self.bench.LOG, self.bench.PROPS))

    def test_a_matching_race_passes_in_a_runtime_of_its_own(self):
        with self.race():
            self.assertIsNone(decision_specimen.check("a pin", self.specimen()))
        self.assertEqual(1, len(self.calls))
        call = self.calls[0]
        self.assertEqual(("coil", 4), (call["track"], call["seed"]))
        # the live tracks beside the repository's jar, whatever fixture jar the pin raced before
        self.assertEqual(str(ROOT / "theoreticRacing.jar"), call["jar"])
        self.assertEqual(["AI2"] * 8, call["kinds"])
        self.assertFalse(call["runtime"].exists())
        self.assertEqual(self.before, (self.bench.JAR, self.bench.LOG, self.bench.PROPS))

    def test_a_changed_summary_stops(self):
        changed = (7, 0, [3, 3, 3, 3, 3, 3, 4])
        self.stops(self.specimen(summary=changed), f"summary changed: {SUMMARY}, expected {changed}")

    def test_a_missing_decision_line_stops(self):
        moved = "2 p1 AI E v(0,0)→(1,0) (5,5)→(6,5) ok"
        self.stops(self.specimen(decision=moved), f"decision missing: {moved}")

    def test_the_decision_is_a_whole_line(self):
        part = "1 p1 AI E v(0,0)→(1,0)"
        self.stops(self.specimen(decision=part), f"decision missing: {part}")

    def test_a_changed_trajectory_stops(self):
        digest = decision_specimen.normalized_sha256(LOG)
        self.stops(self.specimen(sha256="0" * 64), f"trajectory changed: {digest}, expected {'0' * 64}")

    def test_a_failed_race_stops(self):
        self.stops(self.specimen(), "the race failed", summary=None)

    def test_a_race_without_a_log_stops(self):
        self.stops(self.specimen(), "the race left no log", log=None)


def helper_call(node, name):
    """Whether `node` is a call of decision_specimen.<name>."""
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == name
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "decision_specimen")


class PinTests(unittest.TestCase):
    def test_every_specimen_is_checked_once_and_the_list_is_whole(self):
        found = {}
        for path in sorted((ROOT / "tests").glob("ai1_*_regression.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            built = [
                target.id
                for node in tree.body if isinstance(node, ast.Assign) and helper_call(node.value, "Specimen")
                for target in node.targets if isinstance(target, ast.Name)
            ]
            constructed = sum(helper_call(node, "Specimen") for node in ast.walk(tree))
            mains = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
            checks = [node for main in mains for node in ast.walk(main) if helper_call(node, "check")]
            with self.subTest(pin=path.stem):
                # each specimen is a module constant, and main() passes each to the check exactly once
                self.assertEqual(constructed, len(built))
                self.assertEqual(len(checks), sum(helper_call(node, "check") for node in ast.walk(tree)))
                for call in checks:
                    self.assertEqual(2, len(call.args))
                    self.assertIsInstance(call.args[0], ast.Constant)
                    self.assertIsInstance(call.args[1], ast.Name)
                self.assertEqual(sorted(built), sorted(call.args[1].id for call in checks))
                self.assertEqual(len(built), len(set(built)))
            if built or checks:
                found[path.stem] = len(built)
        self.assertEqual(SPECIMENS, found)


if __name__ == "__main__":
    unittest.main()
