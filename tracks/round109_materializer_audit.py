#!/usr/bin/env python3
"""Audit source materializers preserved on an unfinished Round-107 branch."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import traceback

ROOT = Path.cwd()
BRANCH = os.environ["AUDIT_BRANCH"]
SLUG = os.environ["AUDIT_SLUG"]
OUT = ROOT / f"round109-materializer-{SLUG}.json"
PATCH = ROOT / f"round109-materializer-{SLUG}.patch"


def run(args: list[str], *, cwd: Path = ROOT, check: bool = True,
        timeout: int = 1800, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(args, cwd=cwd, text=True, capture_output=True,
                        timeout=timeout, env=env)
    if check and cp.returncode:
        raise RuntimeError(
            f"command failed ({cp.returncode}): {' '.join(args)}\n"
            f"stdout:\n{cp.stdout[-3000:]}\nstderr:\n{cp.stderr[-3000:]}"
        )
    return cp


def configure(source: Path, destination: Path) -> None:
    lines, kinds = [], 0
    for line in source.read_text().splitlines():
        if line.startswith("nPlayers="):
            line = "nPlayers=8"
        if re.match(r"^player[1-8]Kind=", line):
            line = line.split("=", 1)[0] + "=AI1"
            kinds += 1
        lines.append(line)
    if kinds != 8:
        raise RuntimeError(f"expected 8 kinds, got {kinds}")
    destination.write_text("\n".join(lines) + "\n")


def locate_log(directory: Path) -> Path:
    valid = []
    for path in directory.glob("*.log"):
        if "# results" in path.read_text(errors="replace"):
            valid.append(path)
    if not valid:
        raise RuntimeError(f"no valid log in {directory}")
    return max(valid, key=lambda path: path.stat().st_mtime_ns)


def parse(path: Path) -> dict:
    moves: dict[int, int] = {}
    finishes: dict[str, int] = {}
    crashes: set[int] = set()
    order: list[int] = []
    for line in path.read_text().splitlines():
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
    return {
        "finishes": finishes,
        "crashes": sorted(crashes),
        "order": order,
        "finisher_moves": sum(finishes.values()),
    }


def race(work: Path, jar: Path, track: str, seed: int, label: str) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"r109m-{label}-{track}-") as directory:
        tmp = Path(directory)
        props = tmp / "AI1.properties"
        configure(work / "tracks/bench.properties", props)
        cp = run([
            "java", "-Djava.awt.headless=true", "-jar", str(jar.resolve()),
            "--auto", "--track", track, "--props", str(props),
            "--log", str(tmp / "race.log"), "--seed", str(seed),
        ], cwd=work, check=False, timeout=1800)
        if cp.returncode:
            raise RuntimeError(cp.stderr[-3000:])
        return parse(locate_log(tmp))


def gain(candidate: dict, baseline: dict) -> bool:
    return (
        len(candidate["finishes"]) > len(baseline["finishes"])
        or len(candidate["crashes"]) < len(baseline["crashes"])
    ) and not (
        len(candidate["finishes"]) < len(baseline["finishes"])
        or len(candidate["crashes"]) > len(baseline["crashes"])
    )


def candidate_helpers(branch_tree: Path) -> list[Path]:
    helpers = []
    for path in branch_tree.rglob("*.py"):
        rel = path.relative_to(branch_tree).as_posix()
        if not rel.startswith("tracks/"):
            continue
        name = path.name.lower()
        if not any(word in name for word in (
            "107", "rescue", "candidate", "apply", "material", "controller"
        )):
            continue
        source = path.read_text(errors="replace")
        if "RaceAi.java" not in source or "write_text" not in source:
            continue
        if "argparse.ArgumentParser" in source:
            continue
        helpers.append(path)
    return sorted(helpers)[:24]


def main() -> int:
    report = {
        "branch": BRANCH,
        "qualified": False,
        "selected_helper": None,
        "changed_lines": None,
        "baseline": {},
        "candidate": {},
        "helpers": [],
        "error": None,
    }
    base_work = Path("/tmp") / f"round109-materializer-base-{SLUG}"
    try:
        run(["git", "fetch", "origin", "master", BRANCH])
        for path in (base_work,):
            if path.exists():
                run(["git", "worktree", "remove", "--force", str(path)], check=False)
                shutil.rmtree(path, ignore_errors=True)
        run(["git", "worktree", "add", "--detach", str(base_work), "origin/master"])
        run(["sh", "./build_main.sh"], cwd=base_work, timeout=600)
        baseline_jar = ROOT / f"round109-materializer-baseline-{SLUG}.jar"
        shutil.copy2(base_work / "theoreticRacing.jar", baseline_jar)
        for track, seed in (("hungaroring", 144), ("zandvoort", 115), ("lemans", 4)):
            report["baseline"][f"{track}:{seed}"] = race(
                base_work, baseline_jar, track, seed, "baseline"
            )

        with tempfile.TemporaryDirectory(prefix=f"round109-tools-{SLUG}-") as directory:
            tool_root = Path(directory)
            archive = tool_root / "tracks.tar"
            raw = run([
                "git", "archive", "--format=tar", f"origin/{BRANCH}", "tracks"
            ]).stdout
            # git archive is binary; rerun without text capture into a file.
            with archive.open("wb") as handle:
                cp = subprocess.run(
                    ["git", "archive", "--format=tar", f"origin/{BRANCH}", "tracks"],
                    cwd=ROOT, stdout=handle, stderr=subprocess.PIPE, timeout=120,
                )
            if cp.returncode:
                raise RuntimeError(cp.stderr.decode(errors="replace"))
            with tarfile.open(archive) as tar:
                tar.extractall(tool_root, filter="data")
            helpers = candidate_helpers(tool_root)
            report["helper_count"] = len(helpers)

            qualified = []
            for index, helper in enumerate(helpers):
                rel = helper.relative_to(tool_root).as_posix()
                item = {
                    "helper": rel,
                    "applied": False,
                    "built": False,
                    "qualified": False,
                    "changed_lines": None,
                    "candidate": {},
                    "error": None,
                }
                work = Path("/tmp") / f"round109-materializer-{SLUG}-{index}"
                try:
                    if work.exists():
                        run(["git", "worktree", "remove", "--force", str(work)], check=False)
                        shutil.rmtree(work, ignore_errors=True)
                    run(["git", "worktree", "add", "--detach", str(work), "origin/master"])
                    env = os.environ.copy()
                    env["PYTHONPATH"] = str(tool_root)
                    applied = run(
                        [sys.executable, str(helper)], cwd=work, check=False,
                        timeout=180, env=env,
                    )
                    if applied.returncode:
                        item["error"] = applied.stderr[-2000:] or applied.stdout[-2000:]
                        continue
                    changed = run(["git", "diff", "--name-only"], cwd=work).stdout.splitlines()
                    if "src/tr/logic/RaceAi.java" not in changed:
                        item["error"] = f"no RaceAi change: {changed}"
                        continue
                    merged_ai = (work / "src/tr/logic/RaceAi.java").read_bytes()
                    run(["git", "reset", "--hard", "origin/master"], cwd=work)
                    (work / "src/tr/logic/RaceAi.java").write_bytes(merged_ai)
                    run(["git", "diff", "--check"], cwd=work)
                    item["applied"] = True
                    numstat = run([
                        "git", "diff", "--numstat", "origin/master", "--",
                        "src/tr/logic/RaceAi.java"
                    ], cwd=work).stdout.split()
                    if len(numstat) >= 2 and numstat[0].isdigit() and numstat[1].isdigit():
                        item["changed_lines"] = int(numstat[0]) + int(numstat[1])
                    run(["sh", "./run_tests.sh"], cwd=work, timeout=900)
                    run(["sh", "./build_main.sh"], cwd=work, timeout=600)
                    item["built"] = True
                    jar = ROOT / f"round109-materializer-{SLUG}-{index}.jar"
                    shutil.copy2(work / "theoreticRacing.jar", jar)
                    for track, seed in (("hungaroring", 144), ("zandvoort", 115), ("lemans", 4)):
                        item["candidate"][f"{track}:{seed}"] = race(
                            work, jar, track, seed, f"candidate-{index}"
                        )
                    item["qualified"] = (
                        gain(item["candidate"]["hungaroring:144"], report["baseline"]["hungaroring:144"])
                        and item["candidate"]["zandvoort:115"] == report["baseline"]["zandvoort:115"]
                        and item["candidate"]["lemans:4"] == report["baseline"]["lemans:4"]
                    )
                    if item["qualified"]:
                        regression_commands = [
                            "tests/headless_smoke.py", "tests/golden_races.py",
                            "tests/ai1_pace_regression.py", "tests/ai1_mixed_safety_regression.py",
                            "tests/ai1_field_neutral_regression.py", "tests/ai1_staged_pace_regression.py",
                            "tests/ai1_energy_pace_regression.py", "tests/ai1_cross_model_pace_regression.py",
                            "tests/ai1_finish_frontier_regression.py", "tests/ai1_thread_fragility_regression.py",
                        ]
                        for test in regression_commands:
                            run([sys.executable, test], cwd=work, timeout=1800)
                        patch = run([
                            "git", "diff", "--binary", "origin/master", "--",
                            "src/tr/logic/RaceAi.java"
                        ], cwd=work).stdout
                        qualified.append((item["changed_lines"] or 10**9, rel, patch, item))
                    jar.unlink(missing_ok=True)
                except Exception as exc:
                    item["error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
                finally:
                    report["helpers"].append(item)
                    if work.exists():
                        run(["git", "worktree", "remove", "--force", str(work)], check=False)
                        shutil.rmtree(work, ignore_errors=True)

            if qualified:
                qualified.sort(key=lambda row: (row[0], row[1]))
                _, rel, patch, item = qualified[0]
                PATCH.write_text(patch)
                report["qualified"] = True
                report["selected_helper"] = rel
                report["changed_lines"] = item["changed_lines"]
                report["candidate"] = item["candidate"]
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    finally:
        OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        for jar in ROOT.glob(f"round109-materializer-*-{SLUG}.jar"):
            jar.unlink(missing_ok=True)
        if base_work.exists():
            run(["git", "worktree", "remove", "--force", str(base_work)], check=False)
            shutil.rmtree(base_work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
