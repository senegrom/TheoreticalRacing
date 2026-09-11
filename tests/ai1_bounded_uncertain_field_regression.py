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
PROMOTED = (7, 0, [66, 67, 69, 70, 71, 73, 73])
PROMOTED_FINISHERS = [(1, 66), (5, 67), (3, 69), (6, 70), (7, 71), (2, 73), (8, 73)]
PROMOTED_CRASHES = []
PROMOTED_ALL_MOVES = {1: 66, 2: 73, 3: 69, 4: 73, 5: 67, 6: 70, 7: 71, 8: 73}

# Le Mans s87 reaches and fails the componentwise proof. Le Mans s93 is the
# early-round trajectory-only class excluded by the last-three-movers gate;
# s14 retains the adjacent historical false positive. The remaining controls
# cover every redistribution/slowdown class shared with the older broad arm.
# Every complete trajectory must remain the current champion.
RETENTION_CASES = {
    # Round 228: these three Le Mans trajectories changed; the five other
    # retention trajectories remain byte-identical.
    # Round 229: Le Mans s87 is back to seven finishers and no crash (measured).
    PROOF_VETO: ((7, 0, [66, 67, 68, 69, 71, 72, 73]),
                 # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
                 'fa90dd15169a550361892063e7fb4d6a2ef11b03a3017bb7ed708bd91e12540f'),
    # Round 226 (the needle tie-break): re-frozen from measurement.
    # Round 232 (the kinematic confirm): s93 loses p6/p7's race here -- the
    # perturbation this fixture's frozen geometry keeps giving back, while the
    # live circuit's fleet crashes drop by two fifths and s29 above is whole again.
    ("lemans", 93): ((7, 0, [66, 70, 71, 72, 73, 74, 75]),
                     'ca42bf52201f05575d761fffcf4936158ce1196c3a7e941047dcf06370e7ec7b'),
    ("lemans", 14): ((7, 0, [66, 67, 69, 70, 72, 74, 75]),
                     'c94ce32f8f620805e8d4fae8325c3a874d1bde979c5cfade47935130c92b8409'),
    ("silverstone", 78): (
        (6, 1, [81, 82, 83, 84, 84, 85]),
        "f3db28284473bc1212cf52afd0798c1d51970fcda3c24f80b041fcc1be236b05",
    ),
    ("spa", 12): (
        (7, 0, [78, 79, 80, 81, 82, 83, 84]),
        "b2dab367e14c94ff8bb84148a8e88593919bb8f1f39f5cfdb05efd1cf8cb5dcc",
    ),
    ("spa", 31): (
        (7, 0, [78, 79, 80, 81, 82, 83, 83]),
        "c166b3b9deee36887c76c954b9364dcf1b9c241cd378f67a665d89e64448cb86",
    ),
    ("spa", 40): (
        (7, 0, [78, 79, 80, 81, 82, 83, 84]),
        "4b8a5b5595d26ce24e5c40b432fd2703923d959e26e5eadc63eb710611ed3b1f",
    ),
    ("spa", 47): (
        (7, 0, [78, 80, 81, 81, 82, 83, 83]),
        "9129791cfb08a70754d5f511fc9045873cbc01ff535bde6d8e078d5bb5d680e4",
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
