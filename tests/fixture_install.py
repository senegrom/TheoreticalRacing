"""Private-install helper for pins hosted on frozen reference geometry.

The 2026-08-29 fleet edit rescaled/widened several canonical tracks (and
sprint left the fleet entirely). Pins whose byte-frozen boards, masks or
race baselines were derived on the OLD geometry stage a private install:
a copy of the current jar with the frozen fixture tracks beside it (the
game resolves tracks/ next to the jar). The AI code under test is always
the live build -- only the reference geometry is frozen.

Usage, after bench_ai.configure_runtime(directory):

    import fixture_install
    bench_ai.JAR = str(fixture_install.install(directory, ["lemans"]))
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def install(directory, tracks):
    """Stage the jar plus the named frozen tracks in `directory`; returns
    the private jar path."""
    base = Path(directory)
    jar = base / "theoreticRacing.jar"
    if not jar.is_file():
        shutil.copyfile(ROOT / "theoreticRacing.jar", jar)
    tdir = base / "tracks"
    if not tdir.is_dir():
        tdir.mkdir()
        for live in (ROOT / "tracks").glob("*.track"):
            shutil.copyfile(live, tdir / live.name)
    for name in tracks:
        shutil.copyfile(FIXTURES / f"{name}.track", tdir / f"{name}.track")
    return jar
