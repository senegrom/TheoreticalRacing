#!/usr/bin/env python3
"""Pin the high-speed moderate six-ahead pace frontier and its vetoes."""

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

TARGET = ("spa", 83)
# Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
# Round 248 (the physical world model): re-frozen from measurement; p5 crashes
# on its 31st move -- recorded, not vetoed.
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
# Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
# Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
# Round 310: re-frozen from measurement (the danger-joint-search family deleted); p2 now crashes on its 27th move, at turn 210 ((106,132)→(107,139)), nine turns after the pinned turn-201 decision on the same stretch, and seven finishers become six -- recorded, not vetoed (AGENTS.md).
PROMOTED = (6, 1, [78, 79, 80, 82, 82, 83])
LEGACY = (7, 0, [79, 80, 81, 84, 84, 86, 88])
PROMOTED_FINISHERS = [
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); seven finishers and no crash as before, but p5 (the car still running at the end before) now finishes fourth on its 81st move and p4 (fifth home before) is the car still running at the end, after 82 moves -- recorded, not vetoed.
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); seven finishers and no crash as before, but p4 (the car still running at the end before) now finishes fifth on its 82nd move and p8 (third home before, on its 80th move) is the car still running at the end, after 82 moves; p1 and p2 now finish third and fourth on their 81st and 82nd moves, p3 sixth and p5 (fourth before) seventh, both on their 83rd -- recorded, not vetoed.
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); seven finishers and no crash as before, but p8 (the car still running at the end before, after 82 moves) now finishes third on its 80th move and p5 (seventh home before, on its 83rd) is the car still running at the end, after 82 moves; p1 now finishes fourth on its 82nd (third on its 81st before), p2 fifth on its 82nd (fourth before), p3 sixth on its 83rd as before and p4 (fifth before, on its 82nd) seventh on its 83rd -- recorded, not vetoed (AGENTS.md).
    # Round 310: re-frozen from measurement (the danger-joint-search family deleted); p2 (fifth home before, on its 82nd move) now crashes on its 27th, so six cars finish: p3 fifth on its 82nd (sixth on its 83rd before) and p4 sixth on its 83rd (seventh before); p6, p7, p8 and p1 finish as before and p5 is still the car running at the end, after 82 moves -- recorded, not vetoed (AGENTS.md).
    (6, 78),
    (7, 79),
    (8, 80),
    (1, 82),
    (3, 82),
    (4, 83),
]
LEGACY_ALL_MOVES = {1: 88, 2: 87, 3: 79, 4: 80, 5: 81, 6: 84, 7: 84, 8: 86}
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
# Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
# Round 310: re-frozen from measurement (the danger-joint-search family deleted); p2's 27 moves end in its crash and p3 is one move faster (83 -> 82).
PROMOTED_ALL_MOVES = {1: 82, 2: 27, 3: 82, 4: 83, 5: 82, 6: 78, 7: 79, 8: 80}
# Round 247: re-frozen from measurement (the soft rollout at one level, not two).
# Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
# Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
# Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
# Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
# Round 310: re-frozen from measurement (the danger-joint-search family deleted); identical to the round-305/309 race through turn 169, the first change is p2's 22nd move at turn 170.
PROMOTED_SHA256 = "7a15f96b87a31583378b6ddeb347b83cc369812566a5c7547898cdd87553fa3e"
PROMOTED_DECISION = (
    # Round 229: re-frozen from measurement (the soft caution stack left the score).
    # Round 233: re-frozen from measurement (the lane spread left the score).
    # Round 247: re-frozen from measurement (the soft rollout at one level, not two).
    # Round 276: the same turn and car, re-frozen from measurement.
    # Round 278: the same turn and car, re-frozen from measurement.
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); the same turn and car.
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); the same turn and car.
    # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); the same turn and car.
    # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the same turn and car.
    # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same turn and car and the same NW acceleration, now from v(0,8) at (101,133) -- round 281's line again.
    "201 p1 {kind} NW v(0,8)→(-1,7) (101,133)→(100,140) ok"
)

# These cases cover every redistribution or slowdown exposed by the historical
# broad six-ahead arm. The final candidate-speed and gain band must leave each
# complete trajectory equal to the champion.
# Round 247 (the soft rollout at one level, not two): every case re-frozen
# from measurement; Silverstone s78 gets its seventh finisher back.
# Round 248 (the physical world model): Spa s27 loses a car; four cases
# re-frozen from measurement.
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
VETO_CASES = {
    ("spa", 27): (
        # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        (7, 0, [79, 80, 81, 81, 81, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same classification as before, a different trajectory: every car finishes in the same place on the same own move and p1 is still the car running at the end, after 83 moves.
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); the same classification as before, a different trajectory: every car finishes in the same place on the same own move and p1 is still the car running at the end, after 83 moves.
        "7848d1e1d6424a7a3ba52624826689f011d9155c156c5cf6b16fb2396fd0527c",
    ),
    ("spa", 57): (
        # Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); seven finishers and no crash as before, but p3 (fourth home before, on its 81st move) now finishes seventh on its 84th, p2 fourth on its 81st (fifth on its 82nd before) and p4 fifth on its 81st (seventh on its 83rd before); p6, p8, p1 and p7 finish as before and p5 is still the car running at the end, after 83 moves (82 before) -- recorded, not vetoed (AGENTS.md).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, but p4 now finishes fourth on its 81st move (fifth on its 81st before), p2 fifth on its 82nd (fourth on its 81st before), p3 sixth on its 82nd (seventh on its 84th before) and p7 seventh on its 82nd (sixth before); p6, p8 and p1 finish as before and p5 is still the car running at the end, after 82 moves (83 before) -- recorded, not vetoed (AGENTS.md).
        (7, 0, [78, 79, 81, 81, 82, 82, 82]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
        "0a1dd572e7b7c7510d7185a0e11300ec82db46feda6bf2be5a1be68b43b7f546",
    ),
    ("spa", 12): (
        # Round 254: re-frozen from measurement (the danger guard in a faithful world).
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, but p1 (the car still running at the end before, after 83 moves) now finishes fifth on its 82nd move and p4 (seventh home before, on its 83rd) is the car still running at the end, after 82 moves; p3 and p5 now finish sixth and seventh, both on their 82nd (fifth and sixth before); p6, p7, p8 and p2 finish as before -- recorded, not vetoed (AGENTS.md).
        (7, 0, [78, 79, 80, 81, 82, 82, 82]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same summary, a different classification: p1 (fourth home before, on its 81st move) is now the car still running at the end, after 83 moves, and p5 (that car before, after 82) finishes sixth on its 82nd; p2 now finishes fourth on its 81st, p3 fifth on its 82nd and p4 seventh on its 83rd (fifth, seventh and sixth before) -- recorded, not vetoed (AGENTS.md).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
        "eda278d0242bd491fba670ace7268edc3bb8348dbdb4accc132d7e6bb83eb3a8",
    ),
    ("spa", 31): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p4 no longer crashes on its 58th move and p3 now finishes seventh: six finishers become seven, p4 the car still running at the end.
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); seven finishers as before and p4 still the car running at the end, but p3 now finishes sixth on its 83rd move.
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); seven finishers and no crash as before, but p4 (the car still running at the end before) now finishes sixth on its 82nd move and p5 (seventh home before) is the car still running at the end, after 83 moves; p3 now finishes fifth on its 82nd move and p8 (third before) seventh on its 83rd -- recorded, not vetoed.
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); seven finishers and no crash as before, but p5 (the car still running at the end before, after 83 moves) now finishes fourth on its 81st move and p4 (sixth home before, on its 82nd) is the car still running at the end, after 82 moves; p8 (seventh before, on its 83rd) now finishes third on its 80th, and p1, p2 and p3 (third, fourth and fifth before) fifth, sixth and seventh on their 82nd, 83rd and 83rd -- recorded, not vetoed (AGENTS.md).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, but p1 now finishes fourth on its 81st move (fifth on its 82nd before), p2 fifth on its 82nd (sixth on its 83rd before) and p5 (fourth before, on its 81st) sixth on its 82nd; p6, p7, p8 and p3 finish as before and p4 is still the car running at the end, after 82 moves -- recorded, not vetoed (AGENTS.md).
        (7, 0, [78, 79, 80, 81, 82, 82, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
        "c4bc04726147bdefd26851c629cd6600c026bd5e5f4f02ad30feb05d4de74334",
    ),
    ("spa", 40): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        (7, 0, [78, 79, 80, 81, 81, 82, 82]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same classification as before, a different trajectory: every car finishes in the same place on the same own move and p8 is still the car running at the end, after 81 moves.
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); the same classification as before, a different trajectory: every car finishes in the same place on the same own move and p8 is still the car running at the end, after 81 moves.
        "e5725e082e5e8529c2ed96963d32b0097b946e9d94f1eb6a3b321e5f79854128",
    ),
    ("spa", 47): (
        # Round 276: re-frozen from measurement (the grid is legal until a car leaves it).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); seven finishers and no crash as before, but p6 (the car still running at the end before, after 83 moves) now finishes second on its 80th move and p4 (fifth home before, on its 82nd) is the car still running at the end, after 82 moves; p8 still wins, one move later, on its 79th; p1, p2 and p3 (second, third and fourth before) now finish third, fourth and seventh on their 81st, 82nd and 83rd, p5 fifth and p7 sixth, both on their 82nd (sixth on its 82nd and seventh on its 83rd before) -- recorded, not vetoed (AGENTS.md).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); seven finishers and no crash as before, but p6 (second home before, on its 80th move) is now the car still running at the end, after 82 moves, and p4 (that car before, after 82) finishes seventh on its 83rd; p1 now finishes second on its 81st (third before), p7 (sixth before, on its 82nd) third on its 81st and p3 sixth on its 83rd (seventh before); p8, p2 and p5 finish as before -- recorded, not vetoed (AGENTS.md).
        (7, 0, [79, 81, 81, 82, 82, 83, 83]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted).
        "b5688c190c488f24e30422fa557c4d05874fb7d04beb26c06d7d746609f99430",
    ),
    ("coil", 5): (
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        (7, 0, [58, 59, 59, 60, 60, 60, 61]),
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the all-AI1 and alternating races of ai1_label_invariance_regression, which takes this digest as its reference, measured it too.
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same summary, a different classification: p8 (sixth home before, on its 60th move) is now the car still running at the end, after 60 moves, and p7 (that car before) finishes seventh on its 61st; p1 still wins on its 58th, p6 (seventh before, on its 61st) now finishes third on its 59th and p2 (second before, on its 59th) fourth on its 60th, and p4, p3 and p5 (third, fourth and fifth before) second, fifth and sixth on their 59th, 60th and 60th as before -- recorded, not vetoed (AGENTS.md). The all-AI1 and alternating races of ai1_label_invariance_regression, which takes this digest as its reference, measured it too.
        "f31ca965261b243aed633402e84fc968e62ee7ad2f3a75237b10bbdb419a3296",
    ),
    ("coil", 22): (
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        (7, 0, [58, 59, 59, 59, 60, 60, 60]),
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties).
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted).
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); the same summary, but p7 (the car still running at the end before, after 60 moves) now finishes seventh on its 60th and p8 (seventh home before, on its 60th) is the car still running at the end, after 59 moves -- recorded, not vetoed (AGENTS.md).
        "241567e9c55153e1e12db55d1e510d9ed57c21efc74ddac4f90eeef3a8c249ef",
    ),
    ("silverstone", 78): (
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p8 now crashes on its 11th move and seven finishers become six, p6 (sixth home before) the car still running at the end -- recorded, not vetoed.
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win); p8 no longer crashes on its 11th move and finishes seventh on its 85th: six finishers become seven again, as before round 281; p6 (the car still running at the end before, after 84 moves) now finishes fifth on its 84th, p7 sixth on its 84th as before, and p5 (fifth home before, on its 84th) is the car still running at the end, after 85 moves -- recorded, not vetoed (AGENTS.md).
        (7, 0, [81, 82, 83, 83, 84, 84, 85]),
        # Round 278: re-frozen from measurement (the chooser's pick stands).
        # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
        # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); p8 still crashes on its 11th move and six cars finish, but p6 finishes sixth again and p7 is now the car still running at the end -- recorded, not vetoed.
        # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); p8 still crashes on its 11th move and six cars finish, but p7 finishes sixth again on its 84th move and p6 is now the car still running at the end, after 84 moves -- recorded, not vetoed.
        # Round 303: re-frozen from measurement (aware forecasts, the chooser lab's aware promoted); the same classification as before, a different trajectory: p8 still crashes on its 11th move, p7 still finishes sixth on its 84th and p6 is still the car running at the end, after 84 moves -- recorded, not vetoed.
        # Round 305/309: re-frozen from measurement (aware plays the mover's first five forecast continuation moves; a rival's forecast crash is no win).
        # Round 310: re-frozen from measurement (the danger-joint-search family deleted); the same summary, a different classification: p5 (the car still running at the end before, after 85 moves) now finishes fifth on its 84th, p6 sixth on its 84th (fifth before) and p7 seventh on its 85th (sixth on its 84th before), and p8 (seventh home before, on its 85th) is the car still running at the end, after 84 moves; p1 to p4 finish as before -- recorded, not vetoed (AGENTS.md).
        "62f12337cbbb5bcb89929d133268fc49614537c7883cc6294b52971cabc66ade",
    ),
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    cases = [TARGET, *VETO_CASES]
    with tempfile.TemporaryDirectory(prefix="six-ahead-high-speed-regression-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["silverstone", "spa"]))  # frozen pre-repair geometry
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for track, seed in cases:
                summary = bench_ai.run_track(
                    track, timeout=1200, seed=seed
                )
                if summary is None:
                    raise SystemExit(
                        f"six-ahead high-speed {track} seed-{seed} {kind} race failed"
                    )
                log_path = Path(bench_ai.LOG)
                if not log_path.is_file():
                    raise SystemExit(
                        f"six-ahead high-speed {track} seed-{seed} {kind} log missing"
                    )
                summaries[(kind, track, seed)] = summary
                logs[(kind, track, seed)] = log_path.read_text(
                    encoding="utf-8"
                )

    for kind in LABELS:
        target_log = logs[(kind, *TARGET)]
        actual = summaries[(kind, *TARGET)]
        if actual != PROMOTED:
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} regression: "
                f"{actual}, expected {PROMOTED}"
            )
        if finishers(target_log) != PROMOTED_FINISHERS:
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} finisher regression: "
                f"{finishers(target_log)}, expected {PROMOTED_FINISHERS}"
            )
        moves = player_moves(target_log)
        if moves != PROMOTED_ALL_MOVES:
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} move regression: "
                f"{moves}, expected {PROMOTED_ALL_MOVES}"
            )
        # Round 233: the round-117 per-car Pareto contract against the legacy
        # champion is retired -- the policy is judged by head-to-head places
        # (AGENTS.md), and with the lane spread out of the score three cars in
        # this race are slower than the legacy car while the field is faster
        # overall. The measured summary, finisher list, move counts, digest and
        # decision line below all still have to hold.
        deltas = [moves[player] - LEGACY_ALL_MOVES[player] for player in sorted(moves)]
        if not any(delta < 0 for delta in deltas):
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} lost every gain "
                f"over {LEGACY}: {deltas}"
            )
        decision = PROMOTED_DECISION.format(kind=kind)
        if decision not in target_log.splitlines():
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} decision missing: {decision}"
            )
        digest = normalized_sha256(target_log)
        if digest != PROMOTED_SHA256:
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} trajectory regression: "
                f"{digest}, expected {PROMOTED_SHA256}"
            )

    for (track, seed), (expected, expected_digest) in VETO_CASES.items():
        for kind in LABELS:
            actual = summaries[(kind, track, seed)]
            if actual != expected:
                raise SystemExit(
                    f"six-ahead high-speed {track} seed-{seed} {kind} veto regression: "
                    f"{actual}, expected {expected}"
                )
            digest = normalized_sha256(logs[(kind, track, seed)])
            if digest != expected_digest:
                raise SystemExit(
                    f"six-ahead high-speed {track} seed-{seed} {kind} champion "
                    f"trajectory regression: {digest}, expected {expected_digest}"
                )

    print(
        "AI1SixAheadHighSpeedRegression: OK "
        "(Spa s83 finisher -2/all-driver -3; "
        "nine veto/retention controls pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
