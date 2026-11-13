#!/usr/bin/env python3
"""Decision specimens for the regression pins.

A pin's races hold outcomes: a summary, finish moves, a trajectory digest. They show that the races still run as
measured, not that the mechanism a pin is named for still acts in them. A decision specimen is one more race in
which that mechanism changes a real decision of a car, a decision of the race itself and not one inside a
forecast. Each was found by a fleet scan with a scratch build that prints the legs of top-level decisions only,
and confirmed by a twin scratch build with the mechanism off in top-level decisions only, which races the same
race up to the specimen's move and parts there (racing-memory.md, "Decision specimens", 2026-11-13). The pin
checks the specimen race's summary, its trajectory digest and the decision's line.

That check holds the race and the line. It cannot tell which mechanism chose the line: only the print build and
the twin do. So when a later change moves a specimen's race, the specimen is not re-frozen from measurement like
an outcome: the mechanism is shown again in a real decision of the new race or of another one, by a print build
and a twin, or the pin drops the specimen and says that it awaits one. tests/test_decision_specimen.py holds the
list of pins with specimens, so that neither happens unnoticed.

A specimen races the live tracks with eight AI2 cars on random starts and the bench profile's single lap, in a
runtime of its own: a pin that installs frozen fixture tracks would otherwise race another geometry under the
same name.
"""

from pathlib import Path
import sys
import tempfile
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import normalized_lines, normalized_sha256  # noqa: E402


class Specimen(NamedTuple):
    """One race and the decision in it."""

    track: str
    seed: int
    summary: tuple  # (finishers, crashes, the finishers' own-move counts in finishing order)
    sha256: str  # the race's normalized trajectory digest
    decision: str  # the decision's log line, its kind label erased ("AI")


def check(pin: str, specimen: Specimen, timeout: int = 1200) -> None:
    """Race the specimen and stop with the pin's name on any difference."""
    name = f"{pin} decision specimen, {specimen.track} seed {specimen.seed}"
    saved = (bench_ai.JAR, bench_ai.LOG, bench_ai.PROPS)
    try:
        with tempfile.TemporaryDirectory(prefix="decision-specimen-") as directory:
            bench_ai.JAR = str(ROOT / "theoreticRacing.jar")
            bench_ai.configure_runtime(directory)
            bench_ai.set_nplayers(8)
            bench_ai.set_kinds(["AI2"] * 8)
            summary = bench_ai.run_track(specimen.track, timeout=timeout, seed=specimen.seed)
            if summary is None:
                raise SystemExit(f"{name}: the race failed")
            log_path = Path(bench_ai.LOG)
            if not log_path.is_file():
                raise SystemExit(f"{name}: the race left no log")
            log = log_path.read_text(encoding="utf-8")
    finally:
        bench_ai.JAR, bench_ai.LOG, bench_ai.PROPS = saved
    if summary != specimen.summary:
        raise SystemExit(f"{name}: summary changed: {summary}, expected {specimen.summary}")
    if specimen.decision not in normalized_lines(log):
        raise SystemExit(f"{name}: decision missing: {specimen.decision}")
    digest = normalized_sha256(log)
    if digest != specimen.sha256:
        raise SystemExit(f"{name}: trajectory changed: {digest}, expected {specimen.sha256}")
