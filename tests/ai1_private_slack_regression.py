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
HUNGARORING_PROMOTED =(7, 0, [124, 130, 135, 138, 142, 143, 145])
HUNGARORING_LEGACY = (7, 0, [118, 121, 124, 126, 128, 129, 131])
HUNGARORING_PROMOTED_FINISHERS =[(3, 124), (5, 130), (4, 135), (7, 138), (1, 142), (6, 143), (8, 145)]
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
    "AI1": {1: 142, 2: 145, 3: 124, 4: 135, 5: 130, 6: 143, 7: 138, 8: 145},
    "AI2": {1: 142, 2: 145, 3: 124, 4: 135, 5: 130, 6: 143, 7: 138, 8: 145},
}
HUNGARORING_DECISION = {
    "AI1": "370 p2 AI1 SW v(3,2)→(2,3) (49,110)→(51,113) ok",
    "AI2": "370 p2 AI2 SW v(3,2)→(2,3) (49,110)→(51,113) ok",
}
HUNGARORING_NORMALIZED_SHA256 = (
    "b3f2ac61f8d6cbb78e667190f0a1a56f3c8fbb66cda6a1150a8a7997a8e7d279"
)

# Each case pins one false-positive class from the broader score-slack screens:
# identity swap, order redistribution, coasting, far-TTF field drift, braking,
# short-phase overlap, distant-field drift, high-energy redistribution, and a
# steering-reversal finisher swap. The final rule must leave every complete
# trajectory equal to the current champion.
VETO_CASES = {
    ("lemans", 2): ((7, 0, [69, 71, 77, 79, 82, 83, 85]),
        "311 p7 {kind} N v(1,5)→(1,4) (82,144)→(83,148) ok",
    ),
    ("spa", 1): (
        (7, 0, [78, 79, 80, 82, 83, 84, 86]),
        "163 p3 {kind} NW v(4,9)→(3,8) (95,95)→(98,103) ok",
    ),
    ("hungaroring", 40): ((7, 0, [123, 129, 135, 137, 139, 141, 144]),
        "352 p8 {kind} NONE v(3,2)→(3,2) (49,110)→(52,112) ok",
    ),
    ("interlagos", 47): ((7, 0, [129, 135, 136, 137, 138, 139, 141]),
        "175 p7 {kind} SW v(6,-3)→(5,-2) (35,8)→(40,6) ok",
    ),
    ("monza", 30): ((7, 0, [80, 80, 81, 82, 83, 84, 86]),
        "238 p6 {kind} E v(-9,0)→(-8,0) (125,69)→(117,69) ok",
    ),
    ("monaco", 35): ((7, 0, [114, 119, 124, 128, 131, 133, 135]),
        "609 p1 {kind} N v(1,5)→(1,4) (16,116)→(17,120) ok",
    ),
    ("zandvoort", 34): (
        (7, 0, [139, 140, 141, 142, 143, 144, 145]),
        "80 p8 {kind} SE v(3,-8)→(4,-7) (31,61)→(35,54) ok",
    ),
    ("monza", 145): ((7, 0, [80, 81, 81, 82, 83, 83, 84]),
        "174 p6 {kind} NE v(-8,5)→(-7,4) (192,46)→(185,50) ok",
    ),
    ("serpentine", 38): (
        (7, 0, [103, 103, 103, 103, 104, 104, 104]),
        "364 p4 {kind} S v(1,-4)→(1,-3) (17,65)→(18,62) ok",
    ),
}
VETO_NORMALIZED_SHA256 = {
    ("lemans", 2): "b560a6ee2ad23b2acd4207c1fb4efb217f9bd3eff5e7220036836f49017052c7",
    ("spa", 1): "9b9d38ea1a2e6c50f7a425849cba5ef97e0b0ba53726fe15936e0d3c33a433cb",
    ("hungaroring", 40): "dc443ed0a5e37aa47b3f955478d0c53640b1eadbf3ba1b6157a3267bbe96eb71",
    ("interlagos", 47): "4d658c5ce3b5a3bc373f03dd313bbba43385b3b45b86a8fef05bbbf1ae16ce2d",
    ("monza", 30): "c70e157ca61b8d195228db485c6f5ef35ef4af41fdf830792c91402e2cffd4e9",
    ("monaco", 35): "50a19409b7943f4817f6f3bd7065b27b0ce9b429a1eb584288950eb7a192a32b",
    ("zandvoort", 34): "fd46bc1213512c6acaafa7e7783fad19db44667bcc84dad0fcb69b8d68acec58",
    ("monza", 145): "bbaf6fedf526dd2229fdaf83ad41b6114ddd0bc469306ded75f397133cba92b6",
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
    # Round 215 retired this check: HUNGARORING_LEGACY_ALL_MOVES came from the
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

    for (track, seed), (expected, decision_template) in VETO_CASES.items():
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
