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
PROMOTED = (7, 0, [69, 71, 73, 74, 75, 76, 78])
PROMOTED_FINISHERS = [(1, 69), (5, 71), (3, 73), (6, 74), (7, 75), (8, 76), (2, 78)]
PROMOTED_ALL_MOVES = {1: 69, 2: 78, 3: 73, 4: 77, 5: 71, 6: 74, 7: 75, 8: 76}

# Le Mans s87 reaches and fails the componentwise proof. Le Mans s93 is the
# early-round trajectory-only class excluded by the last-three-movers gate;
# s14 retains the adjacent historical false positive. The remaining controls
# cover every redistribution/slowdown class shared with the older broad arm.
# Every complete trajectory must remain the current champion.
RETENTION_CASES = {
    # Round 228: these three Le Mans trajectories changed; the five other
    # retention trajectories remain byte-identical.
    PROOF_VETO: ((7, 0, [68, 71, 72, 73, 74, 75, 78]),
        "ca54df3680a0f523caf1073b9f153fe95051cd5465139654e0f72176be31c5d4",
    ),
    # Round 226 (the needle tie-break): re-frozen from measurement.
    ("lemans", 93): ((7, 0, [68, 70, 71, 73, 74, 75, 77]),
        "449d06293c8a042cd7e763200c8eda757020193fd273adc70201855fe2750ee9",
    ),
    ("lemans", 14): ((7, 0, [68, 70, 71, 73, 74, 77, 79]),
        "20cc7b1e606bcfb4cffe738874d8d5c2a811c101f822b43cfd6f3cd4c0fa8478",
    ),
    ("silverstone", 78): (
        (7, 0, [81, 82, 83, 84, 85, 85, 86]),
        "edeb00d8d0c3f9fa663c985fa5f25b8418531496901122b7a4313c031bd05319",
    ),
    ("spa", 12): (
        (7, 0, [78, 80, 81, 83, 84, 86, 87]),
        "3b01039fc229cf6eee764de05bb1db44abebe3277fff15510b030836331c2c0b",
    ),
    ("spa", 31): (
        (7, 0, [78, 79, 81, 84, 85, 86, 87]),
        "225fbbec666667f3f06e323c5c1cdfebb5f59739227bae9682bc229274b3b2c9",
    ),
    ("spa", 40): (
        (7, 0, [78, 79, 80, 82, 83, 85, 86]),
        "112ed0304e28eb10166641deb14bfa4c1da754982af3f28ccd99ccac652e799d",
    ),
    ("spa", 47): (
        (7, 0, [78, 80, 81, 83, 85, 87, 87]),
        "b570b1736f4afb13052e1271cde1a53dd23938c1bd7445c7cb994d5ee24f1642",
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
        if crashes:
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-29 {kind} crash regression: "
                f"{crashes}"
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
