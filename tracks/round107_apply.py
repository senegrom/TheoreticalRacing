#!/usr/bin/env python3
"""Materialize the narrowed Round 107 two-rescue policy.

The broad Round 106 opening-pack experiment rescued two crash sites but also
changed the Le Mans seed-4 finishing order.  Round 107 retains the independent
equal-speed false-target veto and limits the opening-pack full-fidelity world
to genuine static-funnel decisions.  Both policy copies are changed together.
"""
from __future__ import annotations

from pathlib import Path
import re
import textwrap

race = Path("src/tr/logic/RaceAi.java")
source = race.read_text()

# Correctness: confirmation and trace state belongs to one RaceAi/RaceGame.
source, depth_count = re.subn(
    r"(?m)^\tprivate static int(\s+)trueConfirmDepth;",
    r"\tprivate int\1trueConfirmDepth;",
    source,
    count=1,
)
source, trace_count = re.subn(
    r"(?m)^\tstatic volatile boolean(\s+)simTrace;",
    r"\tvolatile boolean\1simTrace;",
    source,
    count=1,
)
assert depth_count == 1, depth_count
assert trace_count == 1, trace_count

constant_anchor = (
    "\tprivate final static int\t\tAI1_SLOW_PACK_SPD2_SMALL\t= 12;"
    "\t// round 71 (promoted): speed floor for the small-field gate "
    "(start-grid moves stay below it)\n"
)
assert source.count(constant_anchor) == 1
source = source.replace(
    constant_anchor,
    constant_anchor
    + "\tprivate final static int\t\tAI1_OPENING_PACK_MAX_HISTORY\t= 4;"
      "\t// round 107: bounded full-fidelity confirmation in a homogeneous static funnel\n",
    1,
)

opening_old = """\t\t\t\t\t\tchosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS, true);
"""
opening_new = """\t\t\t\t\t\tfinal boolean openingPackConfirm = denseSlowPack
\t\t\t\t\t\t\t\t&& funnelRisk
\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t&& game.players[game.subgamestate].getHistory().size()
\t\t\t\t\t\t\t\t\t\t<= AI1_OPENING_PACK_MAX_HISTORY;
\t\t\t\t\t\tchosen = openingPackConfirm
\t\t\t\t\t\t\t\t? dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\t\t\ttrue, AI1_DJS_SLOW_ROUNDS, AI1_SCORER_MAXRIVALS, true,
\t\t\t\t\t\t\t\t\t\ttrue, true, true)
\t\t\t\t\t\t\t\t: dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS, true);
"""
assert source.count(opening_old) == 2, source.count(opening_old)
source = source.replace(opening_old, opening_new)

equal_old = """\t\t\t\t\t\t\t\t\t\tif (game.crossesFinish(pos[0], pos[1], ax, ay)
\t\t\t\t\t\t\t\t\t\t\t\t|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,
\t\t\t\t\t\t\t\t\t\t\t\t\t\ttrue, true, true, true) >= 0) {
"""
equal_new = """\t\t\t\t\t\t\t\t\t\tboolean falseAliveTarget = false;
\t\t\t\t\t\t\t\t\t\tif (poTByDir[chosen.ordinal()] == poTByDir[smomAlt.ordinal()]
\t\t\t\t\t\t\t\t\t\t\t\t&& Math.max(Math.abs(djvx), Math.abs(djvy))
\t\t\t\t\t\t\t\t\t\t\t\t\t\t== Math.max(Math.abs(avx), Math.abs(avy))
\t\t\t\t\t\t\t\t\t\t\t\t&& trapByDir[chosen.ordinal()] >= AI1_TRAP_L1
\t\t\t\t\t\t\t\t\t\t\t\t&& liveRivalsRemaining(playerNum) >= AI1_PRIVATE_FIELD_MIN_RIVALS
\t\t\t\t\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t\t\t\t\t&& trueConfirmDepth < AI1_TRUE_CONFIRM_MAXDEPTH) {
\t\t\t\t\t\t\t\t\t\t\ttrueConfirmDepth++;
\t\t\t\t\t\t\t\t\t\t\ttry {
\t\t\t\t\t\t\t\t\t\t\t\tfinal int confirmCap = Math.max(AI1_SCORER_MAXRIVALS,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tAI1_DEEP_CERT_RIVALS);
\t\t\t\t\t\t\t\t\t\t\t\tfinal boolean chosenTrueAlive = simOutcome(dcx, dcy, djvx, djvy,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tplayerNum, AI1_DEEP_HORIZON, true, true, true, true,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tfalse, true, confirmCap, null, null, null) >= 0;
\t\t\t\t\t\t\t\t\t\t\t\tfinal boolean altTrueAlive = simOutcome(ax, ay, avx, avy, playerNum,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tAI1_DEEP_HORIZON, true, true, true, true, false, true,
\t\t\t\t\t\t\t\t\t\t\t\t\t\tconfirmCap, null, null, null) >= 0;
\t\t\t\t\t\t\t\t\t\t\t\tfalseAliveTarget = chosenTrueAlive && !altTrueAlive;
\t\t\t\t\t\t\t\t\t\t\t} finally {
\t\t\t\t\t\t\t\t\t\t\t\ttrueConfirmDepth--;
\t\t\t\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\t\t\t}
\t\t\t\t\t\t\t\t\t\tif (!falseAliveTarget && (game.crossesFinish(pos[0], pos[1], ax, ay)
\t\t\t\t\t\t\t\t\t\t\t\t|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,
\t\t\t\t\t\t\t\t\t\t\t\t\t\ttrue, true, true, true) >= 0)) {
"""
assert source.count(equal_old) == 2, source.count(equal_old)
source = source.replace(equal_old, equal_new)
race.write_text(source)

game = Path("src/tr/logic/RaceGame.java")
game_source = game.read_text()
assert game_source.count("RaceAi.simTrace = true;") == 1
assert game_source.count("RaceAi.simTrace = false;") == 1
game_source = game_source.replace("RaceAi.simTrace = true;", "ai.simTrace = true;", 1)
game_source = game_source.replace("RaceAi.simTrace = false;", "ai.simTrace = false;", 1)
game.write_text(game_source)

regression = r'''#!/usr/bin/env python3
"""Pin Round 107's two crash rescues and the Le Mans neutrality boundary."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

EXPECTED = {
    ("hungaroring", 144): (7, 0, [118, 121, 122, 125, 127, 128, 129]),
    ("zandvoort", 115): (7, 0, [139, 140, 141, 142, 143, 144, 145]),
    ("lemans", 4): (7, 0, [65, 67, 69, 70, 71, 72, 75]),
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    results = {}
    with tempfile.TemporaryDirectory(prefix="round107-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for case in EXPECTED:
                results[(kind, case)] = bench_ai.run_track(
                    case[0], timeout=1200, seed=case[1]
                )
    for kind in ("AI1", "AI2"):
        for case, expected in EXPECTED.items():
            actual = results[(kind, case)]
            if actual != expected:
                raise SystemExit(
                    f"Round-107 {kind} {case} regression: {actual}, expected {expected}"
                )
    for case in EXPECTED:
        if results[("AI1", case)] != results[("AI2", case)]:
            raise SystemExit(f"Round-107 AI1/AI2 identity lost at {case}")
    print("AIRescueRegression: OK (two rescues, Le Mans neutral, agents identical)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
Path("tests/ai_rescue_regression.py").write_text(textwrap.dedent(regression))

memory = Path("AI_DEVELOPMENT.md")
if memory.exists():
    text = memory.read_text()
    anchor = "## Current champion and frontier baseline\n"
    if anchor in text and "## Round 107: narrowed opening-pack rescues" not in text:
        section = """## Round 107: narrowed opening-pack rescues

Round 107 separates two safety-positive mechanisms from the broader Round 106
experiment.  A homogeneous dense opening pack receives full-fidelity rival
moves only when the existing static-funnel signal is also present; this keeps
the Hungaroring seed-144 rescue while preserving Le Mans seed 4 exactly.  A
separate equal-speed target check prevents the topology model from switching
from a true-alive line to a false-alive alternative, rescuing Zandvoort seed
115.  Both rules remain structural and retain every downstream safety veto.
Mutable true-confirmation and simulation-trace state is instance-scoped.

"""
        memory.write_text(text.replace(anchor, section + anchor, 1))
