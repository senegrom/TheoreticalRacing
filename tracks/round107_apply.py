#!/usr/bin/env python3
"""Apply the Round 107 one-way safety-rescue candidate.

The opening-pack extension may refine a danger switch that the ordinary
champion search already requested, but it may not initiate a new switch.  This
keeps benign opening pace lines unchanged while allowing full-fidelity rivals
to repair a doomed switch target.  The equal-speed target veto is the separate
late-pack rescue.  Both mutable recursion/debug flags are instance-owned.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def replace_exact(source: str, old: str, new: str, count: int, label: str) -> str:
    found = source.count(old)
    if found < count:
        raise SystemExit(f"{label}: expected at least {count} matches, found {found}")
    return source.replace(old, new, count)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents", choices=("ai1", "both"), default="ai1")
    args = parser.parse_args()
    copies = 1 if args.agents == "ai1" else 2

    race = Path("src/tr/logic/RaceAi.java")
    source = race.read_text()

    # Correctness: one RaceAi belongs to one game.  Concurrent games must not
    # suppress each other's true-confirmation or simulation tracing state.
    static_depth = "\tprivate static int\t\t\t\ttrueConfirmDepth;"
    instance_depth = "\tprivate int\t\t\t\t\ttrueConfirmDepth;"
    if static_depth in source:
        source = source.replace(static_depth, instance_depth, 1)
    elif instance_depth not in source:
        source, changed = re.subn(
            r"(?m)^\s*private\s+static\s+int\s+trueConfirmDepth\s*;\s*$",
            "\tprivate int\t\t\t\t\ttrueConfirmDepth;",
            source,
            count=1,
        )
        if changed != 1 and "trueConfirmDepth" not in source:
            raise SystemExit("trueConfirmDepth declaration not found")

    static_trace = "\tstatic volatile boolean\t\t\tsimTrace;"
    instance_trace = "\tvolatile boolean\t\t\t\tsimTrace;"
    if static_trace in source:
        source = source.replace(static_trace, instance_trace, 1)
    elif instance_trace not in source:
        source, changed = re.subn(
            r"(?m)^\s*static\s+volatile\s+boolean\s+simTrace\s*;\s*$",
            "\tvolatile boolean\t\t\t\tsimTrace;",
            source,
            count=1,
        )
        if changed != 1 and "simTrace" not in source:
            raise SystemExit("simTrace declaration not found")

    constant_anchor = (
        "\tprivate final static int\t\tAI1_SLOW_PACK_SPD2_SMALL\t= 12;"
        "\t// round 71 (promoted): speed floor for the small-field gate "
        "(start-grid moves stay below it)\n"
    )
    opening_constant = (
        "\tprivate final static int\t\tAI1_OPENING_PACK_MAX_HISTORY\t= 4;"
        "\t// round 107: full-fidelity rivals may refine an existing opening-pack "
        "danger switch, never initiate one\n"
    )
    if "AI1_OPENING_PACK_MAX_HISTORY" not in source:
        source = replace_exact(
            source,
            constant_anchor,
            constant_anchor + opening_constant,
            1,
            "opening-pack constant anchor",
        )

    ordinary = '''\t\t\t\t\t\tchosen = dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\ttrue, funnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS, true);
'''
    one_way = '''\t\t\t\t\t\tfinal Direction round107OrdinaryDanger = dangerJointSearch(pos, vel,
\t\t\t\t\t\t\t\tplayerNum, chosen, true, true, true, true,
\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_HORIZON : AI1_DJS_SLOW_ROUNDS,
\t\t\t\t\t\t\t\tfunnelRisk ? AI1_DEEP_CERT_RIVALS : AI1_SCORER_MAXRIVALS, true);
\t\t\t\t\t\tfinal boolean openingPackConfirm = denseSlowPack
\t\t\t\t\t\t\t\t&& kindHomogeneousRoster(playerNum)
\t\t\t\t\t\t\t\t&& game.players[game.subgamestate].getHistory().size()
\t\t\t\t\t\t\t\t\t\t<= AI1_OPENING_PACK_MAX_HISTORY
\t\t\t\t\t\t\t\t&& round107OrdinaryDanger != chosen;
\t\t\t\t\t\tchosen = openingPackConfirm
\t\t\t\t\t\t\t\t? dangerJointSearch(pos, vel, playerNum, chosen, true, true, true,
\t\t\t\t\t\t\t\t\t\ttrue, AI1_DJS_SLOW_ROUNDS, AI1_SCORER_MAXRIVALS, true,
\t\t\t\t\t\t\t\t\t\ttrue, true, true)
\t\t\t\t\t\t\t\t: round107OrdinaryDanger;
'''
    source = replace_exact(source, ordinary, one_way, copies, "opening-pack danger call")

    target_old = '''\t\t\t\t\t\t\t\t\t\tif (game.crossesFinish(pos[0], pos[1], ax, ay)
\t\t\t\t\t\t\t\t\t\t\t\t|| simOutcome(ax, ay, avx, avy, playerNum, AI1_DEEP_HORIZON,
\t\t\t\t\t\t\t\t\t\t\t\t\t\ttrue, true, true, true) >= 0) {
'''
    target_new = '''\t\t\t\t\t\t\t\t\t\tboolean falseAliveTarget = false;
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
'''
    source = replace_exact(source, target_old, target_new, copies, "equal-speed target veto")
    race.write_text(source)

    game = Path("src/tr/logic/RaceGame.java")
    game_source = game.read_text()
    if "RaceAi.simTrace" in game_source:
        game_source = game_source.replace("RaceAi.simTrace", "ai.simTrace")
    game.write_text(game_source)


if __name__ == "__main__":
    main()
