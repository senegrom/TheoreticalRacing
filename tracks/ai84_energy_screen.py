#!/usr/bin/env python3
"""Exact Round-84 cap-13 screen against Round 83 master."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "7a3c35033dc227ae5e2444a54d03d7869629bf1e"
BASE_JAR = ROOT / "theoreticRacing-ai83.jar"
CANDIDATE_JAR = ROOT / "theoreticRacing-ai84.jar"
TRACKS = [
    "silverstone", "spa", "lemans", "monaco", "nurburgring",
    "hungaroring", "interlagos", "zandvoort", "coil",
]
CASES = [(track, seed) for track in TRACKS for seed in range(1, 26)]


def checked(*args: str, cwd: Path = ROOT) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def build_jars() -> None:
    base = Path("/tmp/ai83")
    if base.exists():
        shutil.rmtree(base)
    checked("git", "worktree", "add", str(base), BASE_SHA)
    checked("sh", "./build_main.sh", cwd=base)
    shutil.copyfile(base / "theoreticRacing.jar", BASE_JAR)

    source = ROOT / "src" / "tr" / "logic" / "RaceAi.java"
    text = source.read_text()
    old = "private final static int\t\tAI1_STAGED_MAX_SPEED2_GAIN\t= 9;"
    new = "private final static int\t\tAI1_STAGED_MAX_SPEED2_GAIN\t= 13;"
    if old in text:
        if text.count(old) != 1:
            raise SystemExit("unexpected Round-83 energy constant count")
        source.write_text(text.replace(old, new))
    elif new not in text:
        raise SystemExit("neither Round-83 nor provisional energy constant found")
    checked("sh", "./build_main.sh")
    shutil.copyfile(ROOT / "theoreticRacing.jar", CANDIDATE_JAR)


def write_props(path: Path) -> None:
    text = (ROOT / "tracks" / "bench.properties").read_text()
    text = re.sub(r"nPlayers=\d+", "nPlayers=8", text)
    for index in range(1, 9):
        text = re.sub(
            rf"^(player{index}Kind=).*$", rf"\g<1>AI1", text, flags=re.MULTILINE
        )
    path.write_text(text)


def run_race(jar: Path, track: str, seed: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="ai84-race-") as directory:
        directory = Path(directory)
        props = directory / "bench.properties"
        log = directory / "game.log"
        write_props(props)
        command = [
            "java", "-Djava.awt.headless=true", "-jar", str(jar), "--auto",
            "--track", track, "--props", str(props), "--log", str(log),
            "--seed", str(seed),
        ]
        process = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=900,
            env=os.environ.copy()
        )
        if process.returncode != 0 or "Aborting" in process.stdout or not log.exists():
            return {
                "invalid": True,
                "returncode": process.returncode,
                "stdout": process.stdout[-2000:],
                "stderr": process.stderr[-4000:],
            }
        moves: dict[int, int] = {}
        crashes: set[int] = set()
        finish_moves: list[int] = []
        for line in log.read_text().splitlines():
            match = re.match(r"^(\d+) p(\d+) ", line)
            if not match:
                continue
            player = int(match.group(2))
            moves[player] = moves.get(player, 0) + 1
            if "CRASH" in line:
                crashes.add(player)
            elif "FINISH" in line:
                finish_moves.append(moves[player])
        return {
            "finishes": len(finish_moves),
            "crashes": len(crashes),
            "moves": finish_moves,
            "move_sum": sum(finish_moves),
        }


def classify(baseline: dict, candidate: dict) -> str:
    if baseline.get("invalid") or candidate.get("invalid"):
        return "INVALID"
    base_safety = baseline["finishes"], baseline["crashes"]
    candidate_safety = candidate["finishes"], candidate["crashes"]
    if candidate_safety != base_safety:
        if (
            candidate["finishes"] >= baseline["finishes"]
            and candidate["crashes"] <= baseline["crashes"]
        ):
            return "SAFETY_IMPROVEMENT"
        return "SAFETY_REGRESSION"
    if candidate["moves"] == baseline["moves"]:
        return "IDENTICAL"
    if candidate["move_sum"] < baseline["move_sum"]:
        return "PACE_IMPROVEMENT"
    if candidate["move_sum"] > baseline["move_sum"]:
        return "PACE_REGRESSION"
    return "REDISTRIBUTION"


def main() -> int:
    build_jars()
    details = []
    counts: dict[str, int] = {}
    net_delta = 0
    for index, (track, seed) in enumerate(CASES, 1):
        baseline = run_race(BASE_JAR, track, seed)
        candidate = run_race(CANDIDATE_JAR, track, seed)
        status = classify(baseline, candidate)
        counts[status] = counts.get(status, 0) + 1
        delta = candidate.get("move_sum", 0) - baseline.get("move_sum", 0)
        net_delta += delta
        if status != "IDENTICAL":
            details.append(
                {
                    "case": f"{track}:{seed}",
                    "status": status,
                    "delta": delta,
                    "baseline": baseline,
                    "candidate": candidate,
                }
            )
            print(
                f"{status:18} {track}:{seed:<2} "
                f"f/c {baseline.get('finishes')}/{baseline.get('crashes')} -> "
                f"{candidate.get('finishes')}/{candidate.get('crashes')} "
                f"moves {baseline.get('move_sum')} -> "
                f"{candidate.get('move_sum')} ({delta:+})",
                flush=True,
            )
        if index % 25 == 0 or index == len(CASES):
            print(f"completed {index}/{len(CASES)} races", flush=True)

    report = {
        "baseline": BASE_SHA,
        "candidate": "energy-cap-13",
        "counts": counts,
        "net_move_delta": net_delta,
        "details": details,
    }
    (ROOT / "ai84-energy-screen.json").write_text(
        json.dumps(report, indent=2, sort_keys=True)
    )
    with (ROOT / "ai84-energy-screen.txt").open("w") as output:
        output.write(json.dumps({"counts": counts, "net_move_delta": net_delta}, sort_keys=True))
        output.write("\n")
        for row in details:
            output.write(
                f"{row['status']:18} {row['case']:24} {row['delta']:+}\n"
            )

    bad = sum(
        counts.get(name, 0)
        for name in ("INVALID", "SAFETY_REGRESSION", "PACE_REGRESSION", "REDISTRIBUTION")
    )
    gains = counts.get("PACE_IMPROVEMENT", 0) + counts.get("SAFETY_IMPROVEMENT", 0)
    if bad:
        print(f"energy candidate has {bad} regression-class results", flush=True)
        return 2
    if gains == 0:
        print("energy candidate is inert", flush=True)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
