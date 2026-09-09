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
# Round 228: re-frozen from complete recorded races after removing the
# narrow-lane distance surcharge: seven finishers and no crashes in every case.
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic and AI1/AI2 identity checks remain intact.
# Every case below retains seven finishers and zero crashes.
# Round 229 (the soft caution stack left the score, -0.82 places head-to-head):
# every case re-frozen from measurement (E:/tmp-claude/refreeze_survey.py slack).
# Hungaroring s40 now has six finishers and p8 crashes on its 33rd move, under
# both labels -- recorded, not vetoed (AGENTS.md); the other cases keep seven
# finishers and no crashes.
HUNGARORING_PROMOTED = (7, 0, [122, 123, 124, 125, 127, 129, 130])
HUNGARORING_PROMOTED_FINISHERS = [(3, 122),
                                  (4, 123),
                                  (7, 124),
                                  (8, 125),
                                  (6, 127),
                                  (1, 129),
                                  (5, 130)]
HUNGARORING_ALL_MOVES = {
    "AI1": {1: 129, 2: 130, 3: 122, 4: 123, 5: 130, 6: 127, 7: 124, 8: 125},
    "AI2": {1: 129, 2: 130, 3: 122, 4: 123, 5: 130, 6: 127, 7: 124, 8: 125},
}
HUNGARORING_NORMALIZED_SHA256 = (
    '616bdd972ccca13296b3f404306c44a40e4c0cb7effa33e24d7a9ae7a33d3e36'
)

# Each case pins one false-positive class from the broader score-slack screens:
# identity swap, order redistribution, coasting, far-TTF field drift, braking,
# short-phase overlap, distant-field drift, high-energy redistribution, and a
# steering-reversal finisher swap. The final rule must leave every complete
# trajectory equal to the current champion.
VETO_CASES = {
    # Round 226 (the needle tie-break): re-frozen from measurement.
    ("lemans", 2): ((7, 0, [66, 70, 71, 72, 74, 75, 76]),
        "311 p7 {kind} N v(1,5)→(1,4) (82,144)→(83,148) ok",
    ),
    ("spa", 1): (
        (7, 0, [78, 79, 80, 81, 83, 84, 84]),
        "163 p3 {kind} NW v(4,9)→(3,8) (95,95)→(98,103) ok",
    ),
    ("hungaroring", 40): ((6, 1, [122, 123, 124, 126, 127, 128]),
        "352 p8 {kind} NONE v(3,2)→(3,2) (49,110)→(52,112) ok",
    ),
    ("interlagos", 47): ((7, 0, [124, 125, 126, 128, 129, 130, 132]),
        "175 p7 {kind} SW v(6,-3)→(5,-2) (35,8)→(40,6) ok",
    ),
    ("monza", 30): ((7, 0, [78, 79, 80, 80, 81, 82, 83]),
        "238 p6 {kind} E v(-9,0)→(-8,0) (125,69)→(117,69) ok",
    ),
    # Round 224 moved this race: still seven finishers and no crash, but the
    # car that misses out changes (car 7 finished before, car 1 finishes now)
    # and the last five finishers each take a few moves longer.
    ("monaco", 35): ((7, 0, [114, 115, 117, 118, 119, 120, 121]),
        "609 p1 {kind} N v(1,5)→(1,4) (16,116)→(17,120) ok",
    ),
    ("zandvoort", 34): (
        (7, 0, [137, 138, 139, 141, 142, 143, 144]),
        "80 p8 {kind} SE v(3,-8)→(4,-7) (31,61)→(35,54) ok",
    ),
    ("monza", 145): ((7, 0, [78, 79, 79, 80, 80, 81, 82]),
        "174 p6 {kind} NE v(-8,5)→(-7,4) (192,46)→(185,50) ok",
    ),
    ("serpentine", 38): (
        (7, 0, [103, 103, 103, 103, 103, 104, 104]),
        "364 p4 {kind} S v(1,-4)→(1,-3) (17,65)→(18,62) ok",
    ),
}
VETO_NORMALIZED_SHA256 = {
    # Round 224 (rival predictor in its own lap frame): trajectory only.
    ("lemans", 2): '7f5827f0e0ea47ca50a991254fe169171c4f0ea53f3a48103ccd74ac2c71a121',
    ("spa", 1): "86b07820c6ebfe812ee620f728590fec5ea7242d86db91e3b17951ff15b38361",
    # Round 224: same finishing order and same per-car move counts, new route.
    ("hungaroring", 40): '32466092de94d6e240a609b4f3348db140c54410b5065ab0defacbace7140a0f',
    # Round 224: same finishing order and same per-car move counts, new route.
    ("interlagos", 47): 'ef09674a93909e238f06b73e95366c397af32acbc1fb2f8c6b20588596310d44',
    # Referee correction: turn 647 p5 N replaces an illegal NW finish;
    # every earlier move, race total and finishing place is unchanged.
    ("monza", 30): '862304cef740b5b51e79ef6772b5848e640c9fda41f66a164a01b5bf0e50bdab',
    # Round 224, the one case that changes its result: still seven finishers,
    # but car 1 finishes seventh where car 7 used to, and the race is nine
    # moves longer. The fleet cleared the change on 1460 races either side
    # (no crash moved, +19 and +133 moves in 1.85M).
    ("monaco", 35): 'cf4d930a6aaa52d7433281fc11bae50968fd22f774d21e3b2f6d02e5ffaf0da9',
    ("zandvoort", 34): "7a9780ef41e3eeba7bbf08357e6af234a275d11749a79b99435ee10d444d0121",
    # Same illegal finishing vector at turn 640; legal N preserves all counters.
    ("monza", 145): 'fb5203595ddf9780d88dd129cdee7dad283a34b64b2b2689319edfb1de221f25',
    # Reject p3's wall-overlap finish at turn 819: its last two approach moves
    # and p6's nearby response move, but the full field's outcome counters do not.
    ("serpentine", 38): "5c5641a88ad03a766b38d83dea7cf861549c35080755244df2a5db4c4313e209",
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
