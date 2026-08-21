#!/usr/bin/env python3
"""Pin the exact-private score-slack pace frontier and its identity vetoes."""

import hashlib
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

HUNGARORING_SEED = 12
HUNGARORING_PROMOTED = (7, 0, [118, 121, 124, 126, 127, 129, 131])
HUNGARORING_LEGACY = (7, 0, [118, 121, 124, 126, 128, 129, 131])
HUNGARORING_PROMOTED_FINISHERS = [
    (3, 118),
    (7, 121),
    (4, 124),
    (1, 126),
    (6, 127),
    (8, 129),
    (2, 131),
]
HUNGARORING_LEGACY_ALL_MOVES = {
    1: 126,
    2: 131,
    3: 118,
    4: 124,
    5: 130,
    6: 128,
    7: 121,
    8: 129,
}
HUNGARORING_ALL_MOVES = {
    "AI1": {1: 126, 2: 131, 3: 118, 4: 124, 5: 130, 6: 127, 7: 121, 8: 129},
    "AI2": {1: 126, 2: 131, 3: 118, 4: 124, 5: 130, 6: 127, 7: 121, 8: 129},
}
HUNGARORING_DECISION = {
    "AI1": "370 p2 AI1 SW v(3,2)→(2,3) (49,110)→(51,113) ok",
    "AI2": "370 p2 AI2 SW v(3,2)→(2,3) (49,110)→(51,113) ok",
}
HUNGARORING_NORMALIZED_SHA256 = (
    "185cc5d2b8abf4722e23c17a73ab5e71b167c456d1b5256832d66a5aece8fca6"
)

# Each case pins one false-positive class from the broader score-slack screens:
# identity swap, order redistribution, coasting, far-TTF field drift, braking,
# short-phase overlap, distant-field drift, high-energy redistribution, and a
# steering-reversal finisher swap. The final rule must leave every complete
# trajectory equal to the current champion.
VETO_CASES = {
    ("lemans", 2): (
        (7, 0, [65, 67, 68, 69, 71, 72, 74]),
        "311 p7 {kind} N v(1,5)→(1,4) (82,144)→(83,148) ok",
    ),
    ("spa", 1): (
        (7, 0, [78, 79, 80, 82, 83, 84, 86]),
        "163 p3 {kind} NW v(4,9)→(3,8) (95,95)→(98,103) ok",
    ),
    ("hungaroring", 40): (
        (7, 0, [118, 121, 124, 125, 126, 127, 128]),
        "352 p8 {kind} NONE v(3,2)→(3,2) (49,110)→(52,112) ok",
    ),
    ("interlagos", 47): (
        (7, 0, [122, 123, 125, 126, 127, 128, 130]),
        "175 p7 {kind} SW v(6,-3)→(5,-2) (35,8)→(40,6) ok",
    ),
    ("monza", 30): (
        (7, 0, [77, 78, 79, 80, 80, 81, 82]),
        "238 p6 {kind} E v(-9,0)→(-8,0) (125,69)→(117,69) ok",
    ),
    ("monaco", 35): (
        (7, 0, [109, 111, 113, 115, 117, 118, 120]),
        "609 p1 {kind} N v(1,5)→(1,4) (16,116)→(17,120) ok",
    ),
    ("zandvoort", 34): (
        (7, 0, [139, 140, 141, 142, 143, 144, 145]),
        "80 p8 {kind} SE v(3,-8)→(4,-7) (31,61)→(35,54) ok",
    ),
    ("monza", 145): (
        (7, 0, [77, 78, 79, 80, 80, 81, 81]),
        "174 p6 {kind} NE v(-8,5)→(-7,4) (192,46)→(185,50) ok",
    ),
    ("serpentine", 38): (
        (7, 0, [103, 103, 103, 103, 104, 104, 104]),
        "364 p4 {kind} S v(1,-4)→(1,-3) (17,65)→(18,62) ok",
    ),
}
VETO_NORMALIZED_SHA256 = {
    ("lemans", 2): "2b3ae563aa2b04a704c6e920b458a2acad01070cf17e206c76c431875a66eaca",
    ("spa", 1): "9b9d38ea1a2e6c50f7a425849cba5ef97e0b0ba53726fe15936e0d3c33a433cb",
    ("hungaroring", 40): "d421114c61870afb3759a4d065ac5fa807ec8921de80e580c1d848e36027afce",
    ("interlagos", 47): "2a2a65eef6571694fbc3c274f0f1f51893faf82d91e7f0d0af2957730f689914",
    ("monza", 30): "10d7a0a0d665c6a2612ea2367ddaf04331ca4b5401d2eafc70ee83e19391af55",
    ("monaco", 35): "b3441b736bbfd7595ae5eaf3cdc86b0a6712bc9233a3dfe17a64e782e9a64890",
    ("zandvoort", 34): "fd46bc1213512c6acaafa7e7783fad19db44667bcc84dad0fcb69b8d68acec58",
    ("monza", 145): "bdabaff4f771e6fe5a1414c4470d2aba59a4bc5d125ece3468c6874935ca91cf",
    ("serpentine", 38): "e081392cf11674acbbf839eebb301ed78f3d18670ae710ec036893dba30f2f22",
}


def finishers(text: str) -> list[tuple[int, int]]:
    moves: dict[int, int] = {}
    result = []
    for line in text.splitlines():
        match = re.match(r"^(\d+) p(\d+) ", line)
        if match is None:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if "FINISH" in line:
            result.append((player, moves[player]))
    return result


def player_moves(text: str) -> dict[int, int]:
    result: dict[int, int] = {}
    for line in text.splitlines():
        match = re.match(r"^(\d+) p(\d+) ", line)
        if match is not None:
            player = int(match.group(2))
            result[player] = result.get(player, 0) + 1
    return result


def normalized_lines(text: str) -> list[str]:
    return [
        line.replace("AI1", "AI").replace("AI2", "AI")
        for line in text.splitlines()
        if line.startswith("player")
        or line.startswith("# turns")
        or line.startswith("# results")
        or (line and line[0].isdigit())
    ]


def normalized_sha256(text: str) -> str:
    normalized = "\n".join(normalized_lines(text)).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    cases = [("hungaroring", HUNGARORING_SEED), *VETO_CASES]
    with tempfile.TemporaryDirectory(prefix="ai1-private-slack-") as directory:
        bench_ai.configure_runtime(directory)
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
    for kind, promoted_moves in actual_moves.items():
        deltas = [
            promoted_moves[player] - HUNGARORING_LEGACY_ALL_MOVES[player]
            for player in sorted(promoted_moves)
        ]
        if any(delta > 0 for delta in deltas) or not any(delta < 0 for delta in deltas):
            raise SystemExit(
                f"private-slack Hungaroring seed-12 {kind} is not a strict "
                f"Pareto gain over {HUNGARORING_LEGACY}: {deltas}"
            )
    for kind, decision in HUNGARORING_DECISION.items():
        if decision not in logs[(kind, "hungaroring", HUNGARORING_SEED)].splitlines():
            raise SystemExit(
                f"private-slack Hungaroring seed-12 {kind} decision missing: {decision}"
            )
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

    for (track, seed), (expected, decision_template) in VETO_CASES.items():
        for kind in ("AI1", "AI2"):
            actual = summaries[(kind, track, seed)]
            if actual != expected:
                raise SystemExit(
                    f"private-slack {track} seed-{seed} {kind} veto regression: "
                    f"{actual}, expected {expected}"
                )
            decision = decision_template.format(kind=kind)
            if decision not in logs[(kind, track, seed)].splitlines():
                raise SystemExit(
                    f"private-slack {track} seed-{seed} {kind} veto missing: {decision}"
                )
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
