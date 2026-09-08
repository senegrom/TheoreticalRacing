#!/usr/bin/env python3
"""Pin the exact-private score-slack pace frontier and its identity vetoes."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import finishers, normalized_lines, normalized_sha256, player_moves  # noqa: E402

HUNGARORING_SEED = 12
# Round 226 re-froze this from measurement: the needle surcharge became a
# tie-break (12 -> 1), which is worth 0.58-0.60 places head-to-head. Finishers
# and crashes are unchanged; the move counts are the faster lines.
HUNGARORING_PROMOTED =(7, 0, [124, 127, 132, 135, 138, 139, 142])
HUNGARORING_PROMOTED_FINISHERS =[(3, 124), (4, 127), (5, 132), (7, 135), (6, 138), (8, 139), (1, 142)]
HUNGARORING_ALL_MOVES = {
    "AI1": {1: 142, 2: 141, 3: 124, 4: 127, 5: 132, 6: 138, 7: 135, 8: 139},
    "AI2": {1: 142, 2: 141, 3: 124, 4: 127, 5: 132, 6: 138, 7: 135, 8: 139},
}
HUNGARORING_NORMALIZED_SHA256 = (
    "372a692a7722ce76c75df1d235a8de9de0a422d19e5939dd484215cc17e71728"
)

# Each case pins one false-positive class from the broader score-slack screens:
# identity swap, order redistribution, coasting, far-TTF field drift, braking,
# short-phase overlap, distant-field drift, high-energy redistribution, and a
# steering-reversal finisher swap. The final rule must leave every complete
# trajectory equal to the current champion.
VETO_CASES = {
    # Round 226 (the needle tie-break): re-frozen from measurement.
    ("lemans", 2): ((7, 0, [69, 71, 74, 75, 76, 78, 80]),
        "311 p7 {kind} N v(1,5)→(1,4) (82,144)→(83,148) ok",
    ),
    ("spa", 1): (
        (7, 0, [78, 79, 80, 82, 83, 84, 86]),
        "163 p3 {kind} NW v(4,9)→(3,8) (95,95)→(98,103) ok",
    ),
    ("hungaroring", 40): ((7, 0, [123, 129, 132, 135, 137, 138, 141]),
        "352 p8 {kind} NONE v(3,2)→(3,2) (49,110)→(52,112) ok",
    ),
    ("interlagos", 47): ((7, 0, [127, 131, 133, 134, 136, 139, 140]),
        "175 p7 {kind} SW v(6,-3)→(5,-2) (35,8)→(40,6) ok",
    ),
    ("monza", 30): ((7, 0, [79, 80, 81, 82, 82, 83, 83]),
        "238 p6 {kind} E v(-9,0)→(-8,0) (125,69)→(117,69) ok",
    ),
    # Round 224 moved this race: still seven finishers and no crash, but the
    # car that misses out changes (car 7 finished before, car 1 finishes now)
    # and the last five finishers each take a few moves longer.
    ("monaco", 35): ((7, 0, [117, 121, 126, 128, 129, 132, 133]),
        "609 p1 {kind} N v(1,5)→(1,4) (16,116)→(17,120) ok",
    ),
    ("zandvoort", 34): (
        (7, 0, [139, 140, 141, 142, 143, 144, 145]),
        "80 p8 {kind} SE v(3,-8)→(4,-7) (31,61)→(35,54) ok",
    ),
    ("monza", 145): ((7, 0, [78, 80, 81, 81, 81, 83, 83]),
        "174 p6 {kind} NE v(-8,5)→(-7,4) (192,46)→(185,50) ok",
    ),
    ("serpentine", 38): (
        (7, 0, [103, 103, 103, 103, 104, 104, 104]),
        "364 p4 {kind} S v(1,-4)→(1,-3) (17,65)→(18,62) ok",
    ),
}
VETO_NORMALIZED_SHA256 = {
    # Round 224 (rival predictor in its own lap frame): trajectory only.
    ("lemans", 2): "6e12e3aafa450c003d946d2e17ea2e5e3fcbb34191033d27ef07971c391fb1da",
    ("spa", 1): "9b9d38ea1a2e6c50f7a425849cba5ef97e0b0ba53726fe15936e0d3c33a433cb",
    # Round 224: same finishing order and same per-car move counts, new route.
    ("hungaroring", 40): "5fb02291e86764143dbbef0a312d4ebffa94ab7d0f41b4330220048c4d794d05",
    # Round 224: same finishing order and same per-car move counts, new route.
    ("interlagos", 47): "e3ef986fd2836045a022483708180f23379b49a3636368583089d9acbe236a6c",
    # Referee correction: turn 647 p5 N replaces an illegal NW finish;
    # every earlier move, race total and finishing place is unchanged.
    ("monza", 30): "67f129625462d644791f43c3dd876b61342b70fe88f3279bb4f12a8279793826",
    # Round 224, the one case that changes its result: still seven finishers,
    # but car 1 finishes seventh where car 7 used to, and the race is nine
    # moves longer. The fleet cleared the change on 1460 races either side
    # (no crash moved, +19 and +133 moves in 1.85M).
    ("monaco", 35): "edd291c173c273168691184fddb6530ca7e306887df4341f9e7e3ef23ac89957",
    ("zandvoort", 34): "fd46bc1213512c6acaafa7e7783fad19db44667bcc84dad0fcb69b8d68acec58",
    # Same illegal finishing vector at turn 640; legal N preserves all counters.
    ("monza", 145): "7586919cad80d61aa99cdcc4f961305df47aebbcbd95b9a96f08f5ea8fe32713",
    # Reject p3's wall-overlap finish at turn 819: its last two approach moves
    # and p6's nearby response move, but the full field's outcome counters do not.
    ("serpentine", 38): "82de9001dbb13f1ee6fce99387032658ac199c9dc977f3ca05e679e48bd44b0a",
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    cases = [("hungaroring", HUNGARORING_SEED), *VETO_CASES]
    with tempfile.TemporaryDirectory(prefix="ai1-private-slack-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["hungaroring", "interlagos", "lemans", "monaco", "zandvoort", "spa", "monza"]))  # frozen pre-2026-08-29 geometry
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track, seed in cases:
                summaries[(kind, track, seed)] = bench_ai.run_track(
                    track, timeout=1200, seed=seed
                )
                logs[(kind, track, seed)] = Path(bench_ai.LOG).read_text(
                    encoding="utf-8"
                )

    for kind in ("AI1", "AI2"):
        actual = summaries[(kind, "hungaroring", HUNGARORING_SEED)]
        if actual != HUNGARORING_PROMOTED:
            raise SystemExit(
                f"private-slack Hungaroring seed-12 {kind} regression: "
                f"{actual}, expected {HUNGARORING_PROMOTED}"
            )

    actual_finishers = {
        kind: finishers(logs[(kind, "hungaroring", HUNGARORING_SEED)])
        for kind in ("AI1", "AI2")
    }
    expected_finishers = {
        "AI1": HUNGARORING_PROMOTED_FINISHERS,
        "AI2": HUNGARORING_PROMOTED_FINISHERS,
    }
    if actual_finishers != expected_finishers:
        raise SystemExit(
            "private-slack Hungaroring seed-12 finisher regression: "
            f"{actual_finishers}, expected {expected_finishers}"
        )
    actual_moves = {
        kind: player_moves(logs[(kind, "hungaroring", HUNGARORING_SEED)])
        for kind in ("AI1", "AI2")
    }
    if actual_moves != HUNGARORING_ALL_MOVES:
        raise SystemExit(
            "private-slack Hungaroring seed-12 complete move-count regression: "
            f"{actual_moves}, expected {HUNGARORING_ALL_MOVES}"
        )
    # Round 215 retired the all-move comparison: its reference came from the
    # pre-promotion build under the old single-lap rules. Under checkpoints on
    # every race both builds drive different races, so a Pareto comparison
    # between them measures the rule change, not the policy.
    # Round 215 retired this check: it pinned one decision by the exact log line
    # it appears on, and with checkpoints on every race the car is somewhere else
    # by that move. The move-count pins above still hold the whole field.
    if normalized_lines(logs[("AI1", "hungaroring", HUNGARORING_SEED)]) != normalized_lines(
        logs[("AI2", "hungaroring", HUNGARORING_SEED)]
    ):
        raise SystemExit("private-slack Hungaroring seed-12 promotion is not mirrored")
    for kind in ("AI1", "AI2"):
        digest = normalized_sha256(logs[(kind, "hungaroring", HUNGARORING_SEED)])
        if digest != HUNGARORING_NORMALIZED_SHA256:
            raise SystemExit(
                f"private-slack Hungaroring seed-12 {kind} trajectory regression: "
                f"{digest}, expected {HUNGARORING_NORMALIZED_SHA256}"
            )

    for (track, seed), (expected, _) in VETO_CASES.items():
        for kind in ("AI1", "AI2"):
            actual = summaries[(kind, track, seed)]
            if actual != expected:
                raise SystemExit(
                    f"private-slack {track} seed-{seed} {kind} veto regression: "
                    f"{actual}, expected {expected}"
                )
            # Round 215 retired this check: it looked for one veto at one move
            # index, and the race no longer reaches that state. The digest below
            # still pins the whole trajectory.
            digest = normalized_sha256(logs[(kind, track, seed)])
            expected_digest = VETO_NORMALIZED_SHA256[(track, seed)]
            if digest != expected_digest:
                raise SystemExit(
                    f"private-slack {track} seed-{seed} {kind} champion-trajectory "
                    f"regression: {digest}, expected {expected_digest}"
                )
        if normalized_lines(logs[("AI1", track, seed)]) != normalized_lines(
            logs[("AI2", track, seed)]
        ):
            raise SystemExit(
                f"private-slack {track} seed-{seed} veto lost champion identity"
            )

    print(
        "AI1PrivateSlackRegression: OK "
        "(Hungaroring s12 strict -1 mirrored; nine false-positive classes vetoed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
