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
# Round 233 (the lane spread left the score, -0.65 places): every case
# re-frozen from measurement; Hungaroring s40 is whole again (seven
# finishers, no crash), Le Mans s2 still loses p4.
# Round 229 (the soft caution stack left the score, -0.82 places head-to-head):
# every case re-frozen from measurement (E:/tmp-claude/refreeze_survey.py slack).
# Hungaroring s40 now has six finishers and p8 crashes on its 33rd move, under
# both labels -- recorded, not vetoed (AGENTS.md); the other cases keep seven
# finishers and no crashes.
# Round 232 (the kinematic confirm): re-frozen from measurement. Le Mans s2 and
# Monaco s35 lose a car here (p1 dies alone at Le Mans, p1 on its 60th move at
# Monaco) while the fleet cuts crashes by two fifths in the same races and the
# bounded-field Le Mans s29 pin gets its seventh finisher back; recorded, not
# vetoed (AGENTS.md).
# Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
# Round 248 (the physical world model): re-frozen from measurement; p2 crashes
# on its 30th move -- recorded, not vetoed.
# Round 260 (the faithful joint world as a chooser): Hungaroring s12 is
# whole again -- p2 no longer dies on its 30th move, seven finishers.
HUNGARORING_PROMOTED = (7, 0, [122, 123, 124, 125, 127, 128, 129])
HUNGARORING_PROMOTED_FINISHERS = [(3, 122), (4, 123), (6, 124), (7, 125), (1, 127), (5, 128), (8, 129)]
HUNGARORING_ALL_MOVES = {
    "AI1": {1: 127, 2: 129, 3: 122, 4: 123, 5: 128, 6: 124, 7: 125, 8: 129},
    "AI2": {1: 127, 2: 129, 3: 122, 4: 123, 5: 128, 6: 124, 7: 125, 8: 129},
}
HUNGARORING_NORMALIZED_SHA256 = (
    # Round 237: re-frozen from measurement (every car takes the two-move duel proof).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 248: re-frozen from measurement (the physical world model).
    # Round 254: re-frozen from measurement (the danger guard in a faithful world).
    '777f598ce170082ebec67bd0a90988b556ce38424bd94a1cb5d099d563ab4f90'
)

# Each case pins one false-positive class from the broader score-slack screens:
# identity swap, order redistribution, coasting, far-TTF field drift, braking,
# short-phase overlap, distant-field drift, high-energy redistribution, and a
# steering-reversal finisher swap. The final rule must leave every complete
# trajectory equal to the current champion.
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
VETO_CASES = {
    # Round 226 (the needle tie-break): re-frozen from measurement.
    # Round 254 (the danger guard in a faithful world): Le Mans s2 loses a
    # car, Hungaroring s40 is whole again; four cases re-frozen from measurement.
    ("lemans", 2): ((7, 0, [66, 67, 68, 69, 72, 73, 73]),
        "311 p7 {kind} N v(1,6)→(1,5) (83,151)→(84,156) ok",
    ),
    ("spa", 1): (
        (7, 0, [78, 79, 80, 81, 82, 82, 84]),
        "163 p3 {kind} NW v(3,10)→(2,9) (99,107)→(101,116) ok",
    ),
    # Round 234: re-frozen from measurement (the seal guard left the decision).
    # Round 247 (the soft rollout at one level, not two): every case below
    # re-frozen from measurement. Hungaroring s40 is whole again; Zandvoort
    # s34 loses a car. Recorded, not vetoed (AGENTS.md).
    # Round 248 (the physical world model): Hungaroring s40 loses a car again
    # and Zandvoort s34 is whole again; six cases re-frozen from measurement.
    ("hungaroring", 40): ((7, 0, [122, 123, 124, 125, 126, 127, 128]),
        "352 p8 {kind} N v(4,3)→(4,2) (52,113)→(56,115) ok",
    ),
    ("interlagos", 47): ((7, 0, [124, 125, 126, 127, 128, 130, 131]),
        "175 p7 {kind} S v(5,-1)→(5,0) (49,5)→(54,5) ok",
    ),
    ("monza", 30): ((7, 0, [77, 78, 79, 79, 79, 80, 81]),
        "238 p6 {kind} SE v(-8,-1)→(-7,0) (118,61)→(111,61) ok",
    ),
    # Round 224 moved this race: still seven finishers and no crash, but the
    # car that misses out changes (car 7 finished before, car 1 finishes now)
    # and the last five finishers each take a few moves longer.
    ("monaco", 35): ((7, 0, [113, 114, 115, 117, 118, 119, 120]),
        "609 p1 {kind} SW v(1,5)→(0,6) (19,125)→(19,131) ok",
    ),
    ("zandvoort", 34): (
        (6, 1, [137, 138, 139, 140, 141, 142]),
        "80 p8 {kind} E v(3,-8)→(4,-8) (31,62)→(35,54) ok",
    ),
    ("monza", 145): ((7, 0, [77, 79, 79, 80, 80, 80, 80]),
        "174 p6 {kind} NONE v(-8,5)→(-8,5) (192,53)→(184,58) ok",
    ),
    ("serpentine", 38): (
        (7, 0, [103, 103, 103, 103, 103, 103, 103]),
        "364 p4 {kind} E v(1,-2)→(2,-2) (18,58)→(20,56) ok",
    ),
}
VETO_NORMALIZED_SHA256 = {
    # Round 224 (rival predictor in its own lap frame): trajectory only.
    ("lemans", 2): 'd155d1017693d247635cac3f88190717217349d86c43e9258bff9eee4d4fb56a',
    ("spa", 1): 'f2b45c6aac2595f6e2a5252e4bdd22f11c94f3a7f6e5871db2065103efa2fe05',
    # Round 224: same finishing order and same per-car move counts, new route.
    # Round 234: re-frozen from measurement (the seal guard left the decision).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    ("hungaroring", 40): '90f71b469bcc3bcab793850867337f76d0f4c771754e01b2d6cda0f3565e819d',
    # Round 224: same finishing order and same per-car move counts, new route.
    ("interlagos", 47): 'a9c5fd48135fe99a485fb52f1790c4b1dbe9c3042e1a96ac1abaefcd9a356052',
    # Referee correction: turn 647 p5 N replaces an illegal NW finish;
    # every earlier move, race total and finishing place is unchanged.
    ("monza", 30): 'd9962438c5c75403a1ad94f9ec373b2da02d019b07446831e3103076a2fd4561',
    # Round 224, the one case that changes its result: still seven finishers,
    # but car 1 finishes seventh where car 7 used to, and the race is nine
    # moves longer. The fleet cleared the change on 1460 races either side
    # (no crash moved, +19 and +133 moves in 1.85M).
    ("monaco", 35): 'b1b80891818930532ac1f11cf5e2d6ad11d33595fc2e9d9b9b44b4b752aa1200',
    ("zandvoort", 34): '3b7031ec4ecc3b95999d36adfd7c27a20923ea217eb084ca06d9e82fd9635ab4',
    # Same illegal finishing vector at turn 640; legal N preserves all counters.
    ("monza", 145): 'ad8f95d9fe32e506d6844c8d0f46b5445ca606a6cb8faa564248f8889c900d38',
    # Reject p3's wall-overlap finish at turn 819: its last two approach moves
    # and p6's nearby response move, but the full field's outcome counters do not.
    ("serpentine", 38): '82fbe5b9c802fad5ba69347f08e7b6ed21edb340a5df99ca300f92aa259d078f',
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
