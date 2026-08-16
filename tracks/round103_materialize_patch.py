#!/usr/bin/env python3
"""Materialize the verified Round 103 six-rival switch confirmation."""
from pathlib import Path
import textwrap

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text(encoding="utf-8")

old_latch = "\tprivate static boolean\t\t\tinTrueRivalConfirm;"
new_latch = "\tprivate boolean\t\t\t\tinTrueRivalConfirm;"
assert source.count(old_latch) == 1
source = source.replace(old_latch, new_latch, 1)

old_target = (
    "\t\t\t\t\t\t\tAI1_TRUE_CONFIRM_ROUNDS, simFinishVanish, exactSelf, exactRivals, true,\n"
    "\t\t\t\t\t\t\tscorerSelf, true, scorerCap, null, null, null) >= 0;"
)
new_target = (
    "\t\t\t\t\t\t\tAI1_TRUE_CONFIRM_ROUNDS, simFinishVanish, exactSelf, exactRivals, true,\n"
    "\t\t\t\t\t\t\tscorerSelf, true, Math.max(scorerCap, AI1_DEEP_CERT_RIVALS),\n"
    "\t\t\t\t\t\t\tnull, null, null) >= 0;"
)
assert source.count(old_target) == 1
source = source.replace(old_target, new_target, 1)

old_ai2 = (
    "\t\t\t\t\t\t\t\tif (deepChoice == chosen)\n"
    "\t\t\t\t\t\t\t\t\tdeepChoice = dangerJointSearch(pos, vel, playerNum, chosen, true, true,\n"
    "\t\t\t\t\t\t\t\t\t\t\ttrue, true, AI1_DEEP_HORIZON);"
)
new_ai2 = (
    "\t\t\t\t\t\t\t\tif (deepChoice == chosen)\n"
    "\t\t\t\t\t\t\t\t\tdeepChoice = dangerJointSearch(pos, vel, playerNum, chosen, true, true,\n"
    "\t\t\t\t\t\t\t\t\t\t\ttrue, true, AI1_DEEP_HORIZON, AI1_SCORER_MAXRIVALS,\n"
    "\t\t\t\t\t\t\t\t\t\t\tfalse, false, true);"
)
assert source.count(old_ai2) == 1
source = source.replace(old_ai2, new_ai2, 1)

comment_anchor = (
    "\t\tif (trueDead && best != null) {\n"
    "\t\t\t// Round 99: the cheap world proposed the switch target; make the\n"
)
comment_replacement = (
    "\t\tif (trueDead && best != null) {\n"
    "\t\t\t// Round 103: target confirmation uses at least the existing six-rival\n"
    "\t\t\t// deep certificate. Zigzag seed 76 proved the nearest-three net can\n"
    "\t\t\t// omit a box-forming rival and accept a false survivor. The wider net\n"
    "\t\t\t// is paid only after a cheap-dead verdict proposes a switch.\n"
    "\t\t\t// Round 99: the cheap world proposed the switch target; make the\n"
)
assert source.count(comment_anchor) == 1
source = source.replace(comment_anchor, comment_replacement, 1)
race.write_text(source, encoding="utf-8")

regression = '''#!/usr/bin/env python3
"""Pin Round 103's six-rival true-confirmation rescue for both agents."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

EXPECTED = (7, 0, [65, 65, 65, 66, 67, 67, 68])


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    results = {}
    with tempfile.TemporaryDirectory(prefix="true-confirm-r103-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            results[kind] = bench_ai.run_track("zigzag", timeout=1800, seed=76)
    for kind, actual in results.items():
        if actual != EXPECTED:
            raise SystemExit(
                f"Round-103 Zigzag seed-76 {kind} regression: {actual}, expected {EXPECTED}"
            )
    if results["AI1"] != results["AI2"]:
        raise SystemExit(f"Round-103 agent identity lost: {results}")
    print("AITrueRivalConfirmationRegression: OK (Zigzag s76 7 finishers, 0 crashes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
Path("tests/ai_true_rival_confirmation_regression.py").write_text(
    regression, encoding="utf-8"
)

development = Path("AI_DEVELOPMENT.md")
doc = development.read_text(encoding="utf-8")
section = '''

## Round 103: six-rival switch-target confirmation

A cheap danger rollout can propose a survivor after declaring the incumbent
line dead. Round 103 preserves that asymmetric design but confirms the proposed
switch against at least the established six-rival deep certificate instead of
the nearest-three set. Zigzag seed 76 showed that the omitted fourth-to-sixth
rival can complete the box: the three-rival world accepted NE, while the wider
faithful world rejects it and selects a genuine survivor. Both AI1 and AI2 now
finish seven cars with zero crashes on that boundary. The true-confirmation
latch is instance-scoped, so concurrent games cannot suppress each other.
'''
if "## Round 103: six-rival switch-target confirmation" not in doc:
    development.write_text(
        doc.rstrip() + textwrap.dedent(section).rstrip() + "\n",
        encoding="utf-8",
    )
