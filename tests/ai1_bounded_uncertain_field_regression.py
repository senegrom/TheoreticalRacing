#!/usr/bin/env python3
"""Pin bounded uncertain-field acceleration and its faithful confirmation."""

import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

TARGET = ("lemans", 29)
PROOF_VETO = ("lemans", 87)
PROMOTED = (7, 0, [65, 67, 69, 71, 72, 73, 75])
LEGACY = (7, 0, [65, 67, 69, 71, 73, 74, 76])
PROMOTED_FINISHERS = [
    (1, 65),
    (3, 67),
    (6, 69),
    (5, 71),
    (7, 72),
    (8, 73),
    (2, 75),
]
LEGACY_FINISHERS = [
    (1, 65),
    (3, 67),
    (6, 69),
    (5, 71),
    (7, 73),
    (8, 74),
    (2, 76),
]
PROMOTED_ALL_MOVES = {
    1: 65,
    2: 75,
    3: 67,
    4: 74,
    5: 71,
    6: 69,
    7: 72,
    8: 73,
}
LEGACY_ALL_MOVES = {
    1: 65,
    2: 76,
    3: 67,
    4: 75,
    5: 71,
    6: 69,
    7: 73,
    8: 74,
}
PROMOTED_NORMALIZED_SHA256 = (
    "5a6b5cbdaa28110e350a753779ea0e38d99dcdba125b91eb32ee504401df28dc"
)
PROMOTED_DECISION = (
    "88 p8 {kind} N v(3,-2)→(3,-3) (18,17)→(21,14) ok"
)
TARGET_VECTOR = (
    "AIDBG FIELD-VECTOR p=8 chosen=(20,15)v(2,-2) "
    "candidate=(21,14)v(3,-3) rounds=8 self=52->51 field=352->351 "
    "projected=401->400 componentwise=true accepted=true "
    "chosenRivals={p1=54,p2=60,p3=56,p4=60,p5=56,p6=57,p7=58} "
    "candidateRivals={p1=54,p2=59,p3=56,p4=60,p5=56,p6=57,p7=58}"
)
PROOF_VETO_VECTOR = (
    "AIDBG FIELD-VECTOR p=7 chosen=(24,13)v(3,-1) "
    "candidate=(25,11)v(4,-3) rounds=8 self=50->50 field=346->346 "
    "projected=396->396 componentwise=false accepted=false "
    "chosenRivals={p1=55,p2=58,p3=59,p4=56,p5=53,p6=56,p8=59} "
    "candidateRivals={p1=55,p2=59,p3=59,p4=56,p5=53,p6=56,p8=58}"
)

# Le Mans s87 reaches and fails the componentwise proof. Le Mans s93 is the
# early-round trajectory-only class excluded by the last-three-movers gate;
# s14 retains the adjacent historical false positive. The remaining controls
# cover every redistribution/slowdown class shared with the older broad arm.
# Every complete trajectory must remain the current champion.
RETENTION_CASES = {
    PROOF_VETO: (
        (7, 0, [65, 68, 69, 71, 73, 74, 76]),
        "8f863081827df30248ddd394b6968ada32702967b8d257022364703eae5168fc",
    ),
    ("lemans", 93): (
        (7, 0, [65, 67, 69, 71, 73, 75, 76]),
        "23cc4c4a2b3247914a43efa9616cc6ac324345206d0e4a4f9fe1b797730a79b1",
    ),
    ("lemans", 14): (
        (7, 0, [65, 67, 68, 70, 71, 73, 75]),
        "d834d3bdab58dcb6109130b6f8361e67977b1d548f10462b0d5b6cf0bb026e69",
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


def race_events(
    text: str,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]], dict[int, int]]:
    moves: dict[int, int] = {}
    finishers: list[tuple[int, int]] = []
    crashes: list[tuple[int, int]] = []
    for line in text.splitlines():
        match = re.match(r"^(\d+) p(\d+) ", line)
        if match is None:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if "FINISH" in line:
            finishers.append((player, moves[player]))
        if "CRASH" in line:
            crashes.append((player, moves[player]))
    return finishers, crashes, moves


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
    vector_logs = {}
    cases = [TARGET, *RETENTION_CASES]
    with tempfile.TemporaryDirectory(
        prefix="bounded-uncertain-field-regression-"
    ) as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["lemans"]))  # frozen pre-2026-08-29 geometry
        bench_ai.set_nplayers(8)
        for kind in ("AI1", "AI2"):
            bench_ai.set_all_to(kind)
            for track, seed in cases:
                try:
                    if (track, seed) in (TARGET, PROOF_VETO):
                        summary, stderr = run_vector_debug_track(track, seed)
                        vector_logs[(kind, track, seed)] = [
                            line
                            for line in stderr.splitlines()
                            if line.startswith("AIDBG FIELD-VECTOR ")
                        ]
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
        deltas = [
            moves[player] - LEGACY_ALL_MOVES[player]
            for player in sorted(PROMOTED_ALL_MOVES)
        ]
        if any(delta > 0 for delta in deltas) or not any(
            delta < 0 for delta in deltas
        ):
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-29 {kind} lost strict Pareto "
                f"gain over {LEGACY}: {deltas}"
            )
        if [player for player, _ in finishers] != [
            player for player, _ in LEGACY_FINISHERS
        ]:
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-29 {kind} changed legacy "
                f"finisher order: {finishers}, expected identities from {LEGACY_FINISHERS}"
            )
        decision = PROMOTED_DECISION.format(kind=kind)
        if decision not in target_log.splitlines():
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-29 {kind} decision missing: "
                f"{decision}"
            )
        digest = normalized_sha256(target_log)
        if digest != PROMOTED_NORMALIZED_SHA256:
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-29 {kind} trajectory "
                f"regression: {digest}, expected {PROMOTED_NORMALIZED_SHA256}"
            )

    if normalized_lines(logs[("AI1", *TARGET)]) != normalized_lines(
        logs[("AI2", *TARGET)]
    ):
        raise SystemExit(
            "bounded uncertain-field Le Mans seed-29 promotion is not mirrored"
        )

    for kind in ("AI1", "AI2"):
        actual_vectors = vector_logs[(kind, *TARGET)]
        if actual_vectors != [TARGET_VECTOR]:
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-29 {kind} faithful "
                f"confirmation regression: {actual_vectors}, expected {[TARGET_VECTOR]}"
            )

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

    for kind in ("AI1", "AI2"):
        actual_vectors = vector_logs[(kind, *PROOF_VETO)]
        if actual_vectors != [PROOF_VETO_VECTOR]:
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-87 {kind} componentwise "
                f"veto regression: {actual_vectors}, expected {[PROOF_VETO_VECTOR]}"
            )

    print(
        "AI1BoundedUncertainFieldRegression: OK "
        "(Le Mans s29 strict all-driver -4/finisher -3 mirrored; "
        "eight-round target/vector proof, Le Mans s87 componentwise veto, "
        "and seven outer retention trajectories pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
