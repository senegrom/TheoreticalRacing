#!/usr/bin/env python3
"""Pin the high-speed moderate six-ahead pace frontier and its vetoes."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import finishers, normalized_lines, normalized_sha256, player_moves  # noqa: E402

TARGET = ("spa", 83)
PROMOTED = (7, 0, [79, 80, 81, 84, 84, 85, 87])
LEGACY = (7, 0, [79, 80, 81, 84, 84, 86, 88])
PROMOTED_FINISHERS = [
    (3, 79),
    (4, 80),
    (5, 81),
    (6, 84),
    (7, 84),
    (8, 85),
    (1, 87),
]
LEGACY_ALL_MOVES = {1: 88, 2: 87, 3: 79, 4: 80, 5: 81, 6: 84, 7: 84, 8: 86}
PROMOTED_ALL_MOVES = {1: 87, 2: 86, 3: 79, 4: 80, 5: 81, 6: 84, 7: 84, 8: 85}
PROMOTED_SHA256 = "286c77fc280d55d8e7ea3e8dd82ae7d8a79c124231af37571f3fa32640da3494"
PROMOTED_DECISION = (
    "201 p1 {kind} W v(1,7)→(0,7) (101,126)→(101,133) ok"
)

# These cases cover every redistribution or slowdown exposed by the historical
# broad six-ahead arm. The final candidate-speed and gain band must leave each
# complete trajectory equal to the champion.
VETO_CASES = {
    ("spa", 27): (
        (7, 0, [78, 79, 81, 83, 85, 85, 87]),
        "22139927cb20e3a445bb6888c5cbc961789a382e440ea4ace8c7dbcd585b4fa7",
    ),
    ("spa", 57): (
        (7, 0, [78, 80, 81, 84, 85, 86, 87]),
        "76c0345a51b61c46cb93c17f0864b460e8cd9d60f6617c866a7ea8f468906653",
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
    ("coil", 5): (
        (7, 0, [58, 59, 60, 61, 62, 62, 62]),
        "2a5e77b94114ad52d9db18cec6e7eaefa56c1f163c8a89c030ca3c08d79f564d",
    ),
    ("coil", 22): (
        (7, 0, [58, 59, 60, 61, 61, 62, 63]),
        "5f38ce668d1c704f19898e8a15aa881d8b8ccf0c3c7541e03894da36ed960f6b",
    ),
    ("silverstone", 78): (
        (7, 0, [81, 82, 83, 84, 85, 85, 86]),
        "edeb00d8d0c3f9fa663c985fa5f25b8418531496901122b7a4313c031bd05319",
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
        for kind in ("AI1", "AI2"):
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

    for kind in ("AI1", "AI2"):
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
        deltas = [moves[player] - LEGACY_ALL_MOVES[player] for player in sorted(moves)]
        if any(delta > 0 for delta in deltas) or not any(delta < 0 for delta in deltas):
            raise SystemExit(
                f"six-ahead high-speed Spa seed-83 {kind} lost strict Pareto gain "
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

    if normalized_lines(logs[("AI1", *TARGET)]) != normalized_lines(
        logs[("AI2", *TARGET)]
    ):
        raise SystemExit("six-ahead high-speed Spa seed-83 promotion is not mirrored")

    for (track, seed), (expected, expected_digest) in VETO_CASES.items():
        for kind in ("AI1", "AI2"):
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
        if normalized_lines(logs[("AI1", track, seed)]) != normalized_lines(
            logs[("AI2", track, seed)]
        ):
            raise SystemExit(
                f"six-ahead high-speed {track} seed-{seed} veto lost champion identity"
            )

    print(
        "AI1SixAheadHighSpeedRegression: OK "
        "(Spa s83 finisher -2/all-driver -3 mirrored; "
        "nine veto/retention controls pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
