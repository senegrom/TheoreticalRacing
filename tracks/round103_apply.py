#!/usr/bin/env python3
"""Materialize Round 103's bounded six-rival switch confirmation."""
from __future__ import annotations

from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
RACE_AI = ROOT / "src" / "tr" / "logic" / "RaceAi.java"


def replace_once(source: str, old: str, new: str, description: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"expected one {description}, found {count}")
    return source.replace(old, new, 1)


def materialize_race_ai() -> None:
    source = RACE_AI.read_text(encoding="utf-8")

    static_latch = re.compile(
        r"(?m)^(\s*private\s+)static\s+(boolean\s+inTrueRivalConfirm\s*;\s*)$"
    )
    if static_latch.search(source):
        source, count = static_latch.subn(r"\1\2", source, count=1)
        if count != 1:
            raise RuntimeError("failed to make true-confirmation latch instance-scoped")
    elif not re.search(r"(?m)^\s*private\s+boolean\s+inTrueRivalConfirm\s*;\s*$", source):
        raise RuntimeError("true-confirmation latch not found")

    old_target = (
        "\t\t\t\t\t\t\tAI1_TRUE_CONFIRM_ROUNDS, simFinishVanish, exactSelf, exactRivals, true,\n"
        "\t\t\t\t\t\t\tscorerSelf, true, scorerCap, null, null, null) >= 0;"
    )
    new_target = (
        "\t\t\t\t\t\t\tAI1_TRUE_CONFIRM_ROUNDS, simFinishVanish, exactSelf, exactRivals, true,\n"
        "\t\t\t\t\t\t\tscorerSelf, true, Math.max(scorerCap, AI1_DEEP_CERT_RIVALS),\n"
        "\t\t\t\t\t\t\tnull, null, null) >= 0;"
    )
    if old_target in source:
        source = replace_once(source, old_target, new_target, "three-rival target confirmation")
    elif new_target not in source:
        raise RuntimeError("switch-target confirmation call not found")

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
    if old_ai2 in source:
        source = replace_once(source, old_ai2, new_ai2, "AI2 true-confirmation fallback")
    elif new_ai2 not in source:
        raise RuntimeError("AI2 deep fallback not found")

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
    if "Round 103: target confirmation uses at least" not in source:
        source = replace_once(source, comment_anchor, comment_replacement, "target-confirmation comment")

    RACE_AI.write_text(source, encoding="utf-8")


def write_regression() -> None:
    test = '''#!/usr/bin/env python3
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
    (ROOT / "tests" / "ai_true_rival_confirmation_regression.py").write_text(
        test, encoding="utf-8"
    )


def update_development_notes() -> None:
    path = ROOT / "AI_DEVELOPMENT.md"
    source = path.read_text(encoding="utf-8")
    heading = "## Round 103: six-rival switch-target confirmation"
    if heading in source:
        return
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
    path.write_text(source.rstrip() + textwrap.dedent(section) + "\n", encoding="utf-8")


def main() -> None:
    materialize_race_ai()
    write_regression()
    update_development_notes()


if __name__ == "__main__":
    main()
