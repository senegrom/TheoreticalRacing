#!/usr/bin/env python3
"""Temporary diagnostics for Round-84 high-energy staged decisions."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("lemans", 3), ("lemans", 19),
    ("spa", 9), ("spa", 11), ("spa", 17),
    ("silverstone", 18),
]


def checked(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def instrument() -> None:
    source = ROOT / "src" / "tr" / "logic" / "RaceAi.java"
    text = source.read_text()
    old = "private final static int\t\tAI1_STAGED_MAX_SPEED2_GAIN\t= 9;"
    new = "private final static int\t\tAI1_STAGED_MAX_SPEED2_GAIN\t= 16;"
    if old in text:
        if text.count(old) != 1:
            raise SystemExit("unexpected energy constant count")
        text = text.replace(old, new)
    elif new not in text:
        raise SystemExit("energy constant not found")

    old_block = """\t\t\tfinal int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,
\t\t\t\t\tAI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
\t\t\tif (candidateFinal < 0 || candidateFinal >= chosenFinal
\t\t\t\t\t|| rolloutFieldCost[0] > chosenField)
\t\t\t\tcontinue;
"""
    new_block = """\t\t\tfinal int candidateFinal = scorerFieldOutcome(nx, ny, nvx, nvy, playerNum,
\t\t\t\t\tAI1_STAGED_HORIZON, AI1_DEEP_CERT_RIVALS, rolloutFieldCost);
\t\t\tfinal long candidateField = rolloutFieldCost[0];
\t\t\tif (AI_DEBUG_DJS)
\t\t\t\tSystem.err.println(\"AIDBG STAGED-CAND p=\" + playerNum + \" pos=(\" + pos[0] + \",\"
\t\t\t\t\t\t+ pos[1] + \") chosen=\" + chosen + \" d=\" + d + \" ahead=\" + rivalsAhead
\t\t\t\t\t\t+ \" ttf=\" + chosenT + \"->\" + turns + \" speed2=\" + chosenSpeed2
\t\t\t\t\t\t+ \"->\" + speed2 + \" gain=\" + (speed2 - chosenSpeed2)
\t\t\t\t\t\t+ \" self=\" + chosenFinal + \"->\" + candidateFinal + \" field=\"
\t\t\t\t\t\t+ chosenField + \"->\" + candidateField + \" rest=\" + restDelta
\t\t\t\t\t\t+ \" trap=\" + trap + \" unc=\" + unc);
\t\t\tif (candidateFinal < 0 || candidateFinal >= chosenFinal
\t\t\t\t\t|| candidateField > chosenField)
\t\t\t\tcontinue;
"""
    if text.count(old_block) != 1:
        raise SystemExit("staged candidate block not found")
    source.write_text(text.replace(old_block, new_block))


def write_props(path: Path) -> None:
    text = (ROOT / "tracks" / "bench.properties").read_text()
    text = re.sub(r"nPlayers=\d+", "nPlayers=8", text)
    for index in range(1, 9):
        text = re.sub(
            rf"^(player{index}Kind=).*$", rf"\g<1>AI1", text, flags=re.MULTILINE
        )
    path.write_text(text)


def run(track: str, seed: int) -> tuple[list[str], list[int]]:
    with tempfile.TemporaryDirectory(prefix="ai84-diagnostic-") as directory:
        directory = Path(directory)
        props = directory / "bench.properties"
        log = directory / "game.log"
        write_props(props)
        process = subprocess.run(
            [
                "java", "-Djava.awt.headless=true", "-Dai.debug.djs=true",
                "-jar", str(ROOT / "theoreticRacing.jar"), "--auto",
                "--track", track, "--props", str(props), "--log", str(log),
                "--seed", str(seed),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=900,
            env=os.environ.copy(),
            check=True,
        )
        lines = [
            line for line in process.stderr.splitlines()
            if "AIDBG STAGED" in line
        ]
        moves: dict[int, int] = {}
        finish_moves: list[int] = []
        for line in log.read_text().splitlines():
            match = re.match(r"^(\d+) p(\d+) ", line)
            if not match:
                continue
            player = int(match.group(2))
            moves[player] = moves.get(player, 0) + 1
            if "FINISH" in line:
                finish_moves.append(moves[player])
        return lines, finish_moves


def main() -> int:
    instrument()
    checked("sh", "./build_main.sh")
    output = ROOT / "ai84-energy-diagnostics.txt"
    with output.open("w") as stream:
        for track, seed in CASES:
            lines, moves = run(track, seed)
            stream.write(f"[{track}:{seed}] moves={moves}\n")
            stream.write("\n".join(lines))
            stream.write("\n")
    print(output.read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
