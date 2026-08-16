#!/usr/bin/env python3
"""Materialize Round 104's stable forward-pack acceleration for both AIs.

The transformation is count-checked and deliberately contains no track, seed,
coordinate, or progress special case. It also makes Round 103's confirmation
recursion depth instance-owned so independent games cannot suppress one
another in the same JVM.
"""
from __future__ import annotations

from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
RACE_AI = ROOT / "src" / "tr" / "logic" / "RaceAi.java"
RACE_GAME = ROOT / "src" / "tr" / "logic" / "RaceGame.java"
TEST = ROOT / "tests" / "ai_forward_pack_acceleration_regression.py"
DEVELOPMENT = ROOT / "AI_DEVELOPMENT.md"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return source.replace(old, new, 1)


def make_instance_owned(source: str, field: str, *, required: bool) -> str:
    pattern = re.compile(
        rf"(?m)^(\s*private\s+)static\s+(?!final\b)([^;\n]*\b{re.escape(field)}\b[^;\n]*;)"
    )
    source, changed = pattern.subn(r"\1\2", source, count=1)
    if required and changed != 1:
        already = re.search(
            rf"(?m)^\s*private\s+(?!static\b)[^;\n]*\b{re.escape(field)}\b[^;\n]*;",
            source,
        )
        if already is None:
            raise RuntimeError(f"instance-state anchor not found for {field}")
    return source


def patch_race_ai() -> None:
    source = RACE_AI.read_text(encoding="utf-8")

    # Round 103 introduced a recursion depth rather than a binary latch, but it
    # must still be game-instance state. A shared static depth lets one race
    # disable confirmations in another race running in the same JVM.
    source = make_instance_owned(source, "trueConfirmDepth", required=True)

    const_anchor = (
        "\tprivate final static int\t\tAI1_STAGED_MAX_SPEED2_GAIN\t= 9;"
        "\t// at most one |v|=4->5 axis of extra energy vs the scorer\n"
    )
    constants = const_anchor + (
        "\tprivate final static int\t\tAI1_FIELD_ACCEL_MIN_SPEED2_GAIN\t= 16;"
        "\t// round 104: require a decisive one-turn acceleration\n"
        "\tprivate final static int\t\tAI1_FIELD_ACCEL_MIN_AHEAD\t= 2;"
        "\t// require a forward pack, not an isolated or trailing-car re-rank\n"
        "\tprivate final static int\t\tAI1_FIELD_ACCEL_MAX_AHEAD\t= 5;"
        "\t// six-ahead full-tail cases remain outside the bounded proof\n"
    )
    if "AI1_FIELD_ACCEL_MIN_SPEED2_GAIN" not in source:
        source = replace_once(source, const_anchor, constants, "field-acceleration constants")

    staged_call = (
        "\t\t\tchosen = stagedPaceOverride(pos, vel, playerNum, chosen, scoreByDir, scoreNSByDir,\n"
        "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n"
    )
    field_call = (
        "\t\t\tchosen = guardedFieldPaceOverride(pos, vel, playerNum, chosen,\n"
        "\t\t\t\t\ttrapByDir, uncByDir, poTByDir);\n"
    )
    if source.count(field_call) == 0:
        count = source.count(staged_call)
        if count != 2:
            raise RuntimeError(f"staged call: expected two AI bodies, found {count}")
        source = source.replace(staged_call, staged_call + field_call)
    elif source.count(field_call) != 2:
        raise RuntimeError("field acceleration must be mirrored into exactly two AI bodies")

    helper_anchor = (
        "\tprivate Direction privatePaceOverride(final int[] pos, final int[] vel, final int playerNum,\n"
    )
    helper = r'''	/** Round 104: recover a one-turn acceleration only in a bounded forward
	 * pack when the same eight-round scorer world proves strict mover and
	 * aggregate-field gains. Marginal energy changes, six-ahead tail cases,
	 * close switchbacks, and sub-fast near-finish lines retain the champion. */
	private Direction guardedFieldPaceOverride(final int[] pos, final int[] vel,
			final int playerNum, final Direction chosen, final double[] trapByDir,
			final double[] uncByDir, final int[] turnsByDir) {
		final int chosenT = turnsByDir[chosen.ordinal()];
		if (chosenT == Integer.MAX_VALUE || chosenT < AI1_FINISH_HOMOGENEOUS_TTF + 2
				|| !kindHomogeneousRoster(playerNum))
			return chosen;
		int liveRivals = 0, rivalsAhead = 0;
		long aheadProgress = 0L;
		final boolean stagedLaunch = useTrackDistanceForStagedLaunch(vel[0], vel[1],
				game.startZoneA.contains(pos[0], pos[1]));
		final int moverProgress = reach.distAt(pos[0], pos[1]);
		for (final Player rival : game.players) {
			if (rival.getNumber() == playerNum || rival.isFinished())
				continue;
			liveRivals++;
			final int[] rivalPos = rival.getPosition();
			final int rivalProgress = reach.distAt(rivalPos[0], rivalPos[1]);
			final boolean ahead = stagedLaunch
					? isStrictlyAheadByTrackDistance(moverProgress, rivalProgress)
					: ((long) rivalPos[0] - pos[0]) * vel[0]
							+ ((long) rivalPos[1] - pos[1]) * vel[1] > 0L;
			if (ahead) {
				rivalsAhead++;
				if (moverProgress != Integer.MAX_VALUE && rivalProgress != Integer.MAX_VALUE)
					aheadProgress += (long) moverProgress - rivalProgress;
			}
		}
		if (liveRivals < AI1_PRIVATE_FIELD_MIN_RIVALS
				|| rivalsAhead < AI1_FIELD_ACCEL_MIN_AHEAD
				|| rivalsAhead > AI1_FIELD_ACCEL_MAX_AHEAD || aheadProgress <= 0L)
			return chosen;

		final int chosenVx = vel[0] + chosen.dx, chosenVy = vel[1] + chosen.dy;
		final int chosenX = pos[0] + chosenVx, chosenY = pos[1] + chosenVy;
		final int chosenSpeed2 = speedSquared(chosenVx, chosenVy);
		int chosenFinal = Integer.MIN_VALUE;
		long chosenField = Long.MAX_VALUE;
		Direction best = null;
		int bestFinal = Integer.MAX_VALUE;
		long bestField = Long.MAX_VALUE;
		for (final Direction d : DIRECTIONS) {
			final int turns = turnsByDir[d.ordinal()];
			if (d == chosen || d == Direction.NONE || turns == Integer.MAX_VALUE
					|| turns + 1 != chosenT || trapByDir[d.ordinal()] != 0.0
					|| uncByDir[d.ordinal()] != 0.0)
				continue;
			final int nvx = vel[0] + d.dx, nvy = vel[1] + d.dy;
			final int speed2 = speedSquared(nvx, nvy);
			if (speed2 - chosenSpeed2 < AI1_FIELD_ACCEL_MIN_SPEED2_GAIN)
				continue;
			// Near the finish, leave sub-fast accelerations to the existing dual
			// full-finish certificate. The counterexample class gained one map
			// turn but lost real moves below the established fast-danger floor.
			if (turns <= AI1_FINISH_EXTENDED_TTF && speed2 < AI1_DJS_SPD2)
				continue;
			final int nx = pos[0] + nvx, ny = pos[1] + nvy;
			final int candidateInf = Math.max(Math.abs(nvx), Math.abs(nvy));
			final int candidateSpan = candidateInf * (candidateInf + 1) / 2;
			final int candidateRing = reach.minRingWidthAhead(nx, ny, candidateSpan);
			if (candidateRing < AI1_FUNNEL_WIDTH) {
				final int chosenInf = Math.max(Math.abs(chosenVx), Math.abs(chosenVy));
				final int chosenSpan = chosenInf * (chosenInf + 1) / 2;
				// Sustained narrow corridors require the complete admitted forward
				// quorum and separation beyond both braking envelopes.
				if (rivalsAhead < AI1_FIELD_ACCEL_MAX_AHEAD
						|| aheadProgress < (long) chosenSpan + candidateSpan)
					continue;
			}
			if (sealable(nx, ny, nvx, nvy, playerNum))
				continue;
			if (chosenFinal == Integer.MIN_VALUE) {
				chosenFinal = scorerFieldOutcome(chosenX, chosenY, chosenVx, chosenVy, playerNum,
						AI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
				chosenField = rolloutFieldCost[0];
				if (chosenFinal < 0 || chosenField >= ROLLOUT_FAILURE_COST)
					return chosen;
			}
			final int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,
					AI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
			final long candidateField = rolloutFieldCost[0];
			if (candidateFinal < 0 || candidateFinal >= chosenFinal
					|| candidateField >= chosenField)
				continue;
			if (best == null || candidateFinal < bestFinal
					|| candidateFinal == bestFinal && candidateField < bestField) {
				best = d;
				bestFinal = candidateFinal;
				bestField = candidateField;
			}
		}
		if (best != null && AI_DEBUG_DJS)
			System.err.println("AIDBG FIELD-ACCEL p=" + playerNum + " pos=(" + pos[0]
					+ "," + pos[1] + ") " + chosen + " -> " + best + " ttf " + chosenT
					+ " -> " + turnsByDir[best.ordinal()] + " ahead=" + rivalsAhead
					+ " progress=" + aheadProgress + " self " + chosenFinal + " -> "
					+ bestFinal + " field " + chosenField + " -> " + bestField);
		return best != null ? best : chosen;
	}

'''
    if "private Direction guardedFieldPaceOverride" not in source:
        source = replace_once(source, helper_anchor, helper + helper_anchor, "helper insertion")

    if source.count(field_call) != 2:
        raise RuntimeError("final AI1/AI2 field-acceleration mirror count is not two")
    if re.search(r"(?m)^\s*private\s+static\s+(?!final\b)[^;]*\btrueConfirmDepth\b", source):
        raise RuntimeError("trueConfirmDepth remains mutable static state")
    RACE_AI.write_text(source, encoding="utf-8")


def patch_query_trace_state() -> None:
    source = RACE_GAME.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    changed = 0
    for index, line in enumerate(lines):
        if "private static" not in line or "final" in line:
            continue
        match = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:=[^;]*)?;", line)
        if match is None:
            continue
        name = match.group(1)
        if "trace" not in name.lower():
            continue
        lines[index] = line.replace("private static", "private", 1)
        changed += 1
    source = "".join(lines)
    # The query tracer is diagnostic-only; older champions may not contain it.
    # When present, every non-final trace sink must be instance-owned.
    for line in source.splitlines():
        if re.search(r"\bprivate\s+static\s+(?!final\b)", line) and "trace" in line.lower():
            raise RuntimeError("mutable static query trace state remains")
    RACE_GAME.write_text(source, encoding="utf-8")
    print(f"instance-owned query trace fields changed: {changed}")


def write_regression() -> None:
    regression = r'''#!/usr/bin/env python3
"""Pin Round 104's mirrored stable forward-pack acceleration proof."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))
import bench_ai  # noqa: E402

EXPECTED = {
    ("coil", 9): (7, 0, [58, 59, 60, 61, 61, 62, 62]),
    ("interlagos", 40): (7, 0, [122, 123, 124, 125, 127, 129, 130]),
    ("spa", 7): (7, 0, [79, 80, 81, 83, 84, 85, 86]),
    ("silverstone", 56): (7, 0, [81, 82, 83, 84, 85, 85, 86]),
    ("interlagos", 38): (7, 0, [122, 123, 124, 125, 126, 127, 128]),
    ("spa", 57): (7, 0, [78, 80, 81, 84, 85, 86, 87]),
    ("zigzag", 76): (7, 0, [65, 65, 65, 66, 67, 67, 68]),
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")
    results = {}
    with tempfile.TemporaryDirectory(prefix="forward-pack-r104-") as directory:
        bench_ai.configure_runtime(directory)
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for case in EXPECTED:
                results[(kind, case)] = bench_ai.run_track(
                    case[0], timeout=1800, seed=case[1]
                )
    for kind in ("AI1", "AI2"):
        for case, expected in EXPECTED.items():
            actual = results[(kind, case)]
            if actual != expected:
                raise SystemExit(
                    f"Round-104 {case[0]} seed-{case[1]} {kind}: "
                    f"{actual}, expected {expected}"
                )
    for case in EXPECTED:
        if results[("AI1", case)] != results[("AI2", case)]:
            raise SystemExit(f"Round-104 AI identity lost at {case}: {results}")
    print(
        "AIForwardPackAccelerationRegression: OK "
        "(mirrored gains, Interlagos rescue, late-reversal vetoes, and Zigzag rescue pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    TEST.write_text(regression, encoding="utf-8")


def update_documentation() -> None:
    text = DEVELOPMENT.read_text(encoding="utf-8")
    heading = "## Round 104: stable forward-pack acceleration"
    if heading in text:
        return
    section = r'''

## Round 104: stable forward-pack acceleration

Round 104 recovers a one-turn acceleration that the ordinary scorer ranking
can leave on the table in a large homogeneous field. Admission requires an
exactly one-turn map gain, zero trap and uncertainty penalties, a decisive
speed-energy increase, a bounded two-to-five-rival forward pack, a non-sealable
landing, and strict eight-round improvement for both the mover and aggregate
field cost. Sustained narrow corridors additionally require the full admitted
forward quorum and separation beyond both braking envelopes. Near the finish,
sub-fast candidates remain under the existing dual full-finish certificate.

The same policy is applied independently in AI1 and AI2. Existing seal, danger,
finish, and true-rival-confirmation vetoes remain downstream. The Round 103
confirmation depth is also instance-owned so concurrent games cannot suppress
one another. The rule contains no track, seed, coordinate, or progress-specific
exception.
'''
    DEVELOPMENT.write_text(text.rstrip() + textwrap.dedent(section) + "\n", encoding="utf-8")


def main() -> int:
    patch_race_ai()
    patch_query_trace_state()
    write_regression()
    update_documentation()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
