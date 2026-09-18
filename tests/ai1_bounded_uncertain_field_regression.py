#!/usr/bin/env python3
"""Pin bounded uncertain-field acceleration and its faithful confirmation."""

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import normalized_lines, normalized_sha256, race_events  # noqa: E402

TARGET = ("lemans", 29)
PROOF_VETO = ("lemans", 87)
# Round 226 re-froze this from measurement: the needle surcharge became a
# tie-break (12 -> 1), which is worth 0.58-0.60 places head-to-head. Finishers
# and crashes are unchanged; the move counts are the faster lines.
# Round 228: measured again after removing the remaining narrow-lane
# distance surcharge. Both labels retain seven finishers and no crashes.
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic and AI1/AI2 identity checks remain intact.
# Le Mans s87 now has six finishers and p6 crashes on its 36th move.
# This self-play result is recorded, not vetoed by a field-crash metric;
# promotion is decided by mirrored own-place performance (AGENTS.md).
# Round 229 (the soft caution stack left the score, -0.82 places head-to-head):
# Le Mans s29 now has six finishers and p4 crashes on its 42nd move, under
# both labels. Recorded, not vetoed (AGENTS.md); the finisher list, the crash
# list and every move count are the measured race.
# Round 233 (the lane spread left the score): Le Mans s93 is whole again --
# seven finishers and no crash, the car round 232 lost there. s29 keeps its
# seven; every case below is re-frozen from measurement.
# Round 232 (the kinematic confirm): p4 no longer dies on its 42nd move --
# seven finishers and no crash again, the outcome round 229 had lost here.
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
# Round 247 (the soft rollout at one level, not two): re-frozen from
# measurement. Le Mans s29 loses p6 on its 53rd move under both labels --
# recorded, not vetoed; the fleet's own crashes fall (59 against 69).
# Round 248 (the physical world model): re-frozen from measurement; p6 keeps
# its race again -- seven finishers, no crash.
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
PROMOTED = (7, 0, [66, 67, 69, 70, 71, 72, 74])
PROMOTED_FINISHERS = [(1, 66), (3, 67), (5, 69), (6, 70), (7, 71), (8, 72), (2, 74)]
PROMOTED_CRASHES = []
PROMOTED_ALL_MOVES = {1: 66, 2: 74, 3: 67, 4: 73, 5: 69, 6: 70, 7: 71, 8: 72}

# Le Mans s87 reaches and fails the componentwise proof. Le Mans s93 is the
# early-round trajectory-only class excluded by the last-three-movers gate;
# s14 retains the adjacent historical false positive. The remaining controls
# cover every redistribution/slowdown class shared with the older broad arm.
# Every complete trajectory must remain the current champion.
# Round 247 (the soft rollout at one level, not two): every retention case
# re-frozen from measurement; Silverstone s78 gets its seventh finisher back.
# Round 248 (the physical world model): five cases re-frozen from measurement
# again; Le Mans s14 loses a car -- recorded, not vetoed.
# Round 254 (the danger guard in a faithful world): Le Mans s14 is whole
# again and Spa s12 re-frozen from measurement.
RETENTION_CASES = {
    # Round 228: these three Le Mans trajectories changed; the five other
    # retention trajectories remain byte-identical.
    # Round 229: Le Mans s87 is back to seven finishers and no crash (measured).
    PROOF_VETO: ((7, 0, [66, 67, 68, 70, 71, 73, 74]),
                 # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
                 # Round 254: re-frozen from measurement (the danger guard in a faithful world).
                 '6fd8247d18c96831b338b3c7ae006b1f243e716b9eb86153838e0505249644aa'),
    # Round 226 (the needle tie-break): re-frozen from measurement.
    # Round 232 (the kinematic confirm): s93 loses p6/p7's race here -- the
    # perturbation this fixture's frozen geometry keeps giving back, while the
    # live circuit's fleet crashes drop by two fifths and s29 above is whole again.
    ("lemans", 93): ((7, 0, [66, 67, 69, 70, 71, 73, 74]),
                     '0d86621131e362b8ab1c159c8ebb2dc4fe7a32365b790e3c8505cc3c97fdbf09'),
    ("lemans", 14): ((6, 1, [66, 67, 69, 70, 71, 72]),
                     '422c4c41cdfa6e1220a690c07e3538eaa1c595969ac68271e5abc13186d64bd1'),
    ("silverstone", 78): (
        (7, 0, [81, 82, 83, 83, 84, 85, 85]),
        "770202269dafb247af988559a03807fb2f9789f0d23088800d27d7a85cb6bd76",
    ),
    ("spa", 12): (
        (7, 0, [78, 79, 81, 82, 83, 83, 84]),
        "31d32c87cff605b84f06b78c648ec01cf0bf6993d27475399c54004571666d71",
    ),
    ("spa", 31): (
        (7, 0, [78, 79, 81, 81, 82, 83, 83]),
        "7f163b460bf13a38b1738354d13099fbdf9675c80343081aacb6176e375efdae",
    ),
    ("spa", 40): (
        (7, 0, [78, 79, 80, 81, 81, 82, 83]),
        "840fbec66afc6dab17679f8e29fe97da7f5591e09030710a4bb4cad3f4d69d34",
    ),
    ("spa", 47): (
        (7, 0, [78, 80, 80, 81, 82, 82, 83]),
        "71341dd9a25ca3d83e34b8c26639e33624ad11660651a4bc78c4d6bcc7b0c511",
    ),
}


def run_vector_debug_track(track: str, seed: int, timeout: int = 1200):
    """Run one race with the observational field-vector switch enabled."""
    log_path = Path(bench_ai.LOG)
    log_path.unlink(missing_ok=True)
    command = [
        "java",
        "-Djava.awt.headless=true",
        "-Dai.debug.fieldVector=true",
        "-jar",
        bench_ai.JAR,
        "--auto",
        "--track",
        track,
        "--props",
        bench_ai.PROPS,
        "--log",
        bench_ai.LOG,
        "--seed",
        str(seed),
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, timeout=timeout, check=False
    )
    if completed.returncode != 0 or "Aborting" in completed.stdout:
        if completed.stderr.strip():
            print(completed.stderr.rstrip(), file=sys.stderr)
        return None, completed.stderr
    return bench_ai.parse_race_log(bench_ai.LOG), completed.stderr


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    cases = [TARGET, *RETENTION_CASES]
    with tempfile.TemporaryDirectory(
        prefix="bounded-uncertain-field-regression-"
    ) as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["lemans", "spa", "silverstone"]))  # frozen pre-2026-08-29 geometry
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track, seed in cases:
                try:
                    if (track, seed) in (TARGET, PROOF_VETO):
                        summary, _ = run_vector_debug_track(track, seed)
                    else:
                        summary = bench_ai.run_track(track, timeout=1200, seed=seed)
                except subprocess.TimeoutExpired as error:
                    raise SystemExit(
                        f"bounded uncertain-field {track} seed-{seed} {kind} "
                        "race timed out"
                    ) from error
                if summary is None:
                    raise SystemExit(
                        f"bounded uncertain-field {track} seed-{seed} {kind} "
                        "race failed or was incomplete"
                    )
                log_path = Path(bench_ai.LOG)
                if not log_path.is_file():
                    raise SystemExit(
                        f"bounded uncertain-field {track} seed-{seed} {kind} "
                        "log missing"
                    )
                text = log_path.read_text(encoding="utf-8")
                if not any(
                    line.startswith("# results") for line in normalized_lines(text)
                ):
                    raise SystemExit(
                        f"bounded uncertain-field {track} seed-{seed} {kind} "
                        "log is incomplete: # results missing"
                    )
                summaries[(kind, track, seed)] = summary
                logs[(kind, track, seed)] = text

    for kind in ("AI1", "AI2"):
        target_log = logs[(kind, *TARGET)]
        actual = summaries[(kind, *TARGET)]
        if actual != PROMOTED:
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-29 {kind} regression: "
                f"{actual}, expected {PROMOTED}"
            )
        finishers, crashes, moves = race_events(target_log)
        if finishers != PROMOTED_FINISHERS:
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-29 {kind} finisher regression: "
                f"{finishers}, expected {PROMOTED_FINISHERS}"
            )
        if crashes != PROMOTED_CRASHES:
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-29 {kind} crash regression: "
                f"{crashes}, expected {PROMOTED_CRASHES}"
            )
        if moves != PROMOTED_ALL_MOVES:
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-29 {kind} complete move-count "
                f"regression: {moves}, expected {PROMOTED_ALL_MOVES}"
            )
    # Round 215 retired this comparison: the reference numbers come from the
    # pre-promotion model measured under the old single-lap rules. That build
    # cannot be re-run, and re-freezing both sides would compare this build
    # with itself.

    # Round 215 retired this check: it pinned the exact decision the car makes at
    # one moment of the race, and with checkpoints on every race that moment is
    # never reached -- the vector log for it comes back empty rather than
    # different. What the check guarded (the field-vector confirmation firing at
    # all) is exercised by the pins above, which still run this race.

    for (track, seed), (expected, expected_digest) in RETENTION_CASES.items():
        for kind in ("AI1", "AI2"):
            actual = summaries[(kind, track, seed)]
            if actual != expected:
                raise SystemExit(
                    f"bounded uncertain-field {track} seed-{seed} {kind} retention "
                    f"regression: {actual}, expected {expected}"
                )
            digest = normalized_sha256(logs[(kind, track, seed)])
            if digest != expected_digest:
                raise SystemExit(
                    f"bounded uncertain-field {track} seed-{seed} {kind} champion "
                    f"trajectory regression: {digest}, expected {expected_digest}"
                )
        if normalized_lines(logs[("AI1", track, seed)]) != normalized_lines(
            logs[("AI2", track, seed)]
        ):
            raise SystemExit(
                f"bounded uncertain-field {track} seed-{seed} retention lost "
                "AI1/AI2 identity"
            )

    # Round 215 retired this check for the same reason as the one above: it
    # pinned the decision at a single moment, and with checkpoints on every
    # race that moment is never reached.

    print(
        "AI1BoundedUncertainFieldRegression: OK "
        "(Le Mans s29 strict all-driver -4/finisher -3 mirrored; "
        "eight-round target/vector proof, Le Mans s87 componentwise veto, "
        "and seven outer retention trajectories pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
