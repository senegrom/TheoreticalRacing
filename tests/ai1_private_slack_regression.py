#!/usr/bin/env python3
"""Pin the exact-private score-slack pace frontier and its identity vetoes."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import finishers, normalized_lines, normalized_sha256, player_moves  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

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
# Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); p2 crashes again, now on its 28th move (six finishers) -- recorded, not vetoed.
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); a car that crashed there now finishes (p2, lost on its 28th move since round 292b, is seventh on its 129th move).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
HUNGARORING_PROMOTED = (7, 0, [121, 122, 123, 124, 125, 127, 128])
HUNGARORING_PROMOTED_FINISHERS = [(3, 121), (4, 122), (6, 123), (7, 124), (8, 125), (1, 127), (2, 128)]
HUNGARORING_ALL_MOVES = {
    "AI2": {1: 127, 2: 128, 3: 121, 4: 122, 5: 127, 6: 123, 7: 124, 8: 125},
}
HUNGARORING_NORMALIZED_SHA256 = (
    # Round 237: re-frozen from measurement (every car takes the two-move duel proof).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 248: re-frozen from measurement (the physical world model).
    # Round 254: re-frozen from measurement (the danger guard in a faithful world).
    # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
    '088fcf5704962cb1f8af764f41f777feb6845915702eeb609c2dcda56e8896b2'
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
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296 (landings priced with the checkpoints they collect paid): Le Mans s2
    # keeps the car it has lost since round 254 and Interlagos s47 loses one (p2 on
    # its 57th move); six cases re-frozen from measurement -- recorded, not vetoed
    # (AGENTS.md).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); Spa s1 loses a car (p7 now crashes on its 28th move) -- recorded, not vetoed.
    ("lemans", 2): (7, 0, [66, 67, 68, 69, 71, 72, 73]),
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); a car that crashed there now finishes (p7, lost on its 28th move since round 281, is sixth on its 82nd move).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    ("spa", 1): (7, 0, [78, 79, 80, 81, 82, 82, 83]),
    # Round 234: re-frozen from measurement (the seal guard left the decision).
    # Round 247 (the soft rollout at one level, not two): every case below
    # re-frozen from measurement. Hungaroring s40 is whole again; Zandvoort
    # s34 loses a car. Recorded, not vetoed (AGENTS.md).
    # Round 248 (the physical world model): Hungaroring s40 loses a car again
    # and Zandvoort s34 is whole again; six cases re-frozen from measurement.
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    ("hungaroring", 40): (7, 0, [121, 122, 123, 124, 125, 127, 128]),
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); a car that crashed there now finishes (p2, lost on its 57th move since round 296, is second on its 125th move).
    ("interlagos", 47): (7, 0, [124, 125, 126, 127, 128, 129, 131]),
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    ("monza", 30): (7, 0, [77, 78, 79, 79, 79, 79, 79]),
    # Round 224 moved this race: still seven finishers and no crash, but the
    # car that misses out changes (car 7 finished before, car 1 finishes now)
    # and the last five finishers each take a few moves longer.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p8 now crashes on its 18th move -- recorded, not vetoed.
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout); a car that crashed there now finishes (p6, lost on its 18th move since round 292b, is seventh on its 120th move).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    ("monaco", 35): (7, 0, [113, 114, 115, 116, 118, 119, 120]),
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    ("zandvoort", 34): (7, 0, [137, 138, 139, 140, 141, 143, 144]),
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    ("monza", 145): (7, 0, [78, 78, 79, 79, 79, 79, 80]),
    ("serpentine", 38): (7, 0, [103, 103, 103, 103, 103, 103, 103]),
}
VETO_NORMALIZED_SHA256 = {
    # Round 224 (rival predictor in its own lap frame): trajectory only.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    ("lemans", 2): '1dc5c394c020adb8f15a8c4fcc81cc122c32e3b64776664ea10073081def49d7',
    # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    ("spa", 1): 'c407baae53da474d35e4200d90ca55553e5ebadacd6006f2fe54f4c96fc5660e',
    # Round 224: same finishing order and same per-car move counts, new route.
    # Round 234: re-frozen from measurement (the seal guard left the decision).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    ("hungaroring", 40): '07bc3b67d51e688cd9b4ba1b2f3524bde44183c863c1967d5b4630398c4b20de',
    # Round 224: same finishing order and same per-car move counts, new route.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 291: re-frozen from measurement (the grid rule at the finish, finishing without the potential, crossings that do not finish, no field-cost veto).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    ("interlagos", 47): '00f86b8011e16dff793eef9abfa34ac3b3421979e0d5bd2e929f673c71d72f41',
    # Referee correction: turn 647 p5 N replaces an illegal NW finish;
    # every earlier move, race total and finishing place is unchanged.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    ("monza", 30): '9bcadf2f4121a1c261fdeba79ff0f1c7c587992b067779353ed6f530cd037d02',
    # Round 224, the one case that changes its result: still seven finishers,
    # but car 1 finishes seventh where car 7 used to, and the race is nine
    # moves longer. The fleet cleared the change on 1460 races either side
    # (no crash moved, +19 and +133 moves in 1.85M).
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); the crash on the 18th move is now p6's, and p8, lost there since round 281, finishes sixth -- recorded, not vetoed.
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    ("monaco", 35): 'b66f70de219766c69349b53c162e19cc37bc19a7565b9b45af04da5a639d98fd',
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
    ("zandvoort", 34): '5dae80b30a653693c9a236e39bb6221de8600ac673f21698b7d98415866faf5d',
    # Same illegal finishing vector at turn 640; legal N preserves all counters.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    ("monza", 145): '2aecd77954a26c24a046edcf5df67233688a321f275b7fd196f02c5594ef5c4f',
    # Reject p3's wall-overlap finish at turn 819: its last two approach moves
    # and p6's nearby response move, but the full field's outcome counters do not.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    ("serpentine", 38): '533dd55485677a75b968b2468f515173340e09f586ec82496453755174f34746',
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
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for track, seed in cases:
                summaries[(kind, track, seed)] = bench_ai.run_track(
                    track, timeout=1200, seed=seed
                )
                logs[(kind, track, seed)] = Path(bench_ai.LOG).read_text(
                    encoding="utf-8"
                )

    for kind in LABELS:
        actual = summaries[(kind, "hungaroring", HUNGARORING_SEED)]
        if actual != HUNGARORING_PROMOTED:
            raise SystemExit(
                f"private-slack Hungaroring seed-12 {kind} regression: "
                f"{actual}, expected {HUNGARORING_PROMOTED}"
            )

    actual_finishers = {
        kind: finishers(logs[(kind, "hungaroring", HUNGARORING_SEED)])
        for kind in LABELS
    }
    expected_finishers = {
        "AI2": HUNGARORING_PROMOTED_FINISHERS,
    }
    if actual_finishers != expected_finishers:
        raise SystemExit(
            "private-slack Hungaroring seed-12 finisher regression: "
            f"{actual_finishers}, expected {expected_finishers}"
        )
    actual_moves = {
        kind: player_moves(logs[(kind, "hungaroring", HUNGARORING_SEED)])
        for kind in LABELS
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
    for kind in LABELS:
        digest = normalized_sha256(logs[(kind, "hungaroring", HUNGARORING_SEED)])
        if digest != HUNGARORING_NORMALIZED_SHA256:
            raise SystemExit(
                f"private-slack Hungaroring seed-12 {kind} trajectory regression: "
                f"{digest}, expected {HUNGARORING_NORMALIZED_SHA256}"
            )

    for (track, seed), expected in VETO_CASES.items():
        for kind in LABELS:
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

    print(
        "AI1PrivateSlackRegression: OK "
        "(Hungaroring s12 strict -1; nine false-positive classes vetoed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
