#!/usr/bin/env python3
"""Audit an unfinished Round-107 branch against the current live champion.

The branch is merged into a detached master worktree, then every merged path
except RaceAi.java is discarded. This isolates reusable policy logic from old
controllers, workflows, reports and stale test fixtures. A candidate qualifies
only if it repairs Hungaroring seed 144, leaves the Round-108 Zandvoort rescue
and Le Mans seed 4 outcome-identical, and passes the current core regression
suite.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import traceback

ROOT = Path.cwd()
BRANCH = os.environ["AUDIT_BRANCH"]
SLUG = re.sub(r"[^A-Za-z0-9_.-]+", "-", BRANCH).strip("-")
OUT = ROOT / f"round109-audit-{SLUG}.json"
PATCH = ROOT / f"round109-audit-{SLUG}.patch"
WORK = Path("/tmp") / f"round109-audit-{SLUG}"


def run(args: list[str], *, cwd: Path = ROOT, check: bool = True,
        timeout: int = 3600, capture: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=capture,
        timeout=timeout,
    )
    if check and result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(args)}\n"
            f"stdout:\n{result.stdout[-4000:]}\nstderr:\n{result.stderr[-4000:]}"
        )
    return result


def configure_props(source: Path, destination: Path) -> None:
    lines: list[str] = []
    saw_players = 0
    for line in source.read_text().splitlines():
        if re.match(r"^nPlayers=", line):
            line = "nPlayers=8"
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=AI1"
            saw_players += 1
        lines.append(line)
    if saw_players != 8:
        raise RuntimeError(f"expected eight player-kind entries, found {saw_players}")
    destination.write_text("\n".join(lines) + "\n")


def parse_log(path: Path) -> dict:
    moves: dict[int, int] = {}
    finishes: dict[str, int] = {}
    crashes: set[int] = set()
    order: list[int] = []
    saw_results = False
    for line in path.read_text().splitlines():
        if line.startswith("# results"):
            saw_results = True
        match = re.match(r"^(\d+) p(\d+) ", line)
        if not match:
            continue
        player = int(match.group(2))
        moves[player] = moves.get(player, 0) + 1
        if "CRASH" in line:
            crashes.add(player)
        elif "FINISH" in line:
            finishes[str(player)] = moves[player]
            order.append(player)
    if not saw_results:
        raise RuntimeError(f"invalid race log: {path}")
    return {
        "finishes": finishes,
        "crashes": sorted(crashes),
        "order": order,
        "finisher_moves": sum(finishes.values()),
    }


def run_case(jar: Path, track: str, seed: int, label: str) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"r109-{label}-{track}-") as directory:
        tmp = Path(directory)
        props = tmp / "AI1.properties"
        log = tmp / "race.log"
        configure_props(WORK / "tracks" / "bench.properties", props)
        result = run(
            [
                "java", "-Djava.awt.headless=true", "-jar", str(jar), "--auto",
                "--track", track, "--props", str(props), "--log", str(log),
                "--seed", str(seed),
            ],
            cwd=WORK,
            check=False,
            timeout=1800,
        )
        if result.returncode:
            raise RuntimeError(
                f"{label} {track} seed {seed} failed: {result.stderr[-4000:]}"
            )
        return parse_log(log)


def safety_better(candidate: dict, baseline: dict) -> bool:
    return (
        len(candidate["finishes"]) > len(baseline["finishes"])
        or len(candidate["crashes"]) < len(baseline["crashes"])
    ) and not (
        len(candidate["finishes"]) < len(baseline["finishes"])
        or len(candidate["crashes"]) > len(baseline["crashes"])
    )


def main() -> int:
    report: dict = {
        "branch": BRANCH,
        "qualified": False,
        "merge_ok": False,
        "build_ok": False,
        "tests_ok": False,
        "changed_lines": None,
        "changed_files_before_isolation": [],
        "baseline": {},
        "candidate": {},
        "error": None,
    }
    try:
        run(["git", "fetch", "origin", "master", BRANCH])
        if WORK.exists():
            run(["git", "worktree", "remove", "--force", str(WORK)], check=False)
            shutil.rmtree(WORK, ignore_errors=True)
        run(["git", "worktree", "add", "--detach", str(WORK), "origin/master"])

        run(["sh", "./build_main.sh"], cwd=WORK, timeout=600)
        baseline_jar = ROOT / f"round109-baseline-{SLUG}.jar"
        shutil.copy2(WORK / "theoreticRacing.jar", baseline_jar)
        for track, seed in (("hungaroring", 144), ("zandvoort", 115), ("lemans", 4)):
            report["baseline"][f"{track}:{seed}"] = run_case(
                baseline_jar, track, seed, "baseline"
            )

        merge = run(
            ["git", "merge", "--no-commit", "--no-ff", f"origin/{BRANCH}"],
            cwd=WORK,
            check=False,
            timeout=300,
        )
        if merge.returncode:
            report["error"] = (
                "merge failed\n" + merge.stdout[-2000:] + "\n" + merge.stderr[-2000:]
            )
            return 0
        report["merge_ok"] = True
        changed = run(
            ["git", "diff", "--cached", "--name-only"], cwd=WORK
        ).stdout.splitlines()
        report["changed_files_before_isolation"] = changed

        merged_ai = (WORK / "src/tr/logic/RaceAi.java").read_bytes()
        run(["git", "reset", "--hard", "origin/master"], cwd=WORK)
        (WORK / "src/tr/logic/RaceAi.java").write_bytes(merged_ai)
        if not run(
            ["git", "diff", "--quiet", "origin/master", "--", "src/tr/logic/RaceAi.java"],
            cwd=WORK,
            check=False,
        ).returncode:
            report["error"] = "merged branch produced no RaceAi change"
            return 0

        numstat = run(
            ["git", "diff", "--numstat", "origin/master", "--", "src/tr/logic/RaceAi.java"],
            cwd=WORK,
        ).stdout.strip().split()
        if len(numstat) >= 2 and numstat[0].isdigit() and numstat[1].isdigit():
            report["changed_lines"] = int(numstat[0]) + int(numstat[1])
        patch = run(
            ["git", "diff", "--binary", "origin/master", "--", "src/tr/logic/RaceAi.java"],
            cwd=WORK,
        ).stdout
        PATCH.write_text(patch)
        run(["git", "diff", "--check"], cwd=WORK)

        run(["sh", "./run_tests.sh"], cwd=WORK, timeout=900)
        run(["sh", "./build_main.sh"], cwd=WORK, timeout=600)
        report["build_ok"] = True
        candidate_jar = ROOT / f"round109-candidate-{SLUG}.jar"
        shutil.copy2(WORK / "theoreticRacing.jar", candidate_jar)

        regression_commands = [
            [sys.executable, "tests/headless_smoke.py"],
            [sys.executable, "tests/golden_races.py"],
            [sys.executable, "tests/ai1_pace_regression.py"],
            [sys.executable, "tests/ai1_mixed_safety_regression.py"],
            [sys.executable, "tests/ai1_field_neutral_regression.py"],
            [sys.executable, "tests/ai1_staged_pace_regression.py"],
            [sys.executable, "tests/ai1_energy_pace_regression.py"],
            [sys.executable, "tests/ai1_cross_model_pace_regression.py"],
            [sys.executable, "tests/ai1_finish_frontier_regression.py"],
            [sys.executable, "tests/ai1_thread_fragility_regression.py"],
        ]
        for command in regression_commands:
            run(command, cwd=WORK, timeout=1800)
        report["tests_ok"] = True

        for track, seed in (("hungaroring", 144), ("zandvoort", 115), ("lemans", 4)):
            report["candidate"][f"{track}:{seed}"] = run_case(
                candidate_jar, track, seed, "candidate"
            )

        h_key = "hungaroring:144"
        z_key = "zandvoort:115"
        l_key = "lemans:4"
        report["qualified"] = (
            safety_better(report["candidate"][h_key], report["baseline"][h_key])
            and report["candidate"][z_key] == report["baseline"][z_key]
            and report["candidate"][l_key] == report["baseline"][l_key]
        )
    except Exception as exc:  # always publish a machine-readable report
        report["error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    finally:
        OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        for jar in ROOT.glob(f"round109-*-{SLUG}.jar"):
            jar.unlink(missing_ok=True)
        if WORK.exists():
            run(["git", "worktree", "remove", "--force", str(WORK)], check=False)
            shutil.rmtree(WORK, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
