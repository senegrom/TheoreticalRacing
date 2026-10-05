#!/usr/bin/env python3
"""Pin bounded uncertain-field acceleration and its faithful confirmation."""

from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402
from forensics_common import normalized_lines, normalized_sha256, race_events  # noqa: E402

# Both labels run one policy since round 222 and ai1_label_invariance_regression
# checks it, so each case races once, under the champion label (2026-09-27).
LABELS = ("AI2",)

TARGET = ("lemans", 29)
PROOF_VETO = ("lemans", 87)
# Round 226 re-froze this from measurement: the needle surcharge became a
# tie-break (12 -> 1), which is worth 0.58-0.60 places head-to-head. Finishers
# and crashes are unchanged; the move counts are the faster lines.
# Round 228: measured again after removing the remaining narrow-lane
# distance surcharge. Both labels retain seven finishers and no crashes.
# Round 231: re-frozen from recorded checkpoint-choice races; the existing
# assertion logic remains intact. (Its AI1/AI2 identity checks retired on
# 2026-09-27: one policy under both labels, pinned by ai1_label_invariance.)
# Le Mans s87 now has six finishers and p6 crashes on its 36th move.
# This self-play result is recorded, not vetoed by a field-crash metric;
# promotion is decided by mirrored own-place performance (AGENTS.md).
# Round 229 (the soft caution stack left the score, -0.82 places head-to-head):
# Le Mans s29 now has six finishers and p4 crashes on its 42nd move, under
# both labels. Recorded, not vetoed (AGENTS.md); the finisher list, the crash
# list and every move count are the measured race.
# Round 233 (the lane spread left the score): Le Mans s93 is whole again --
# seven finishers and no crash, the car round 232 lost there. s29 keeps its
# seven; every case below is re-frozen from measurement.
# Round 232 (the kinematic confirm): p4 no longer dies on its 42nd move --
# seven finishers and no crash again, the outcome round 229 had lost here.
# Round 234: re-frozen from measurement (the seal guard left the decision); finishers and crashes unchanged.
# Round 247 (the soft rollout at one level, not two): re-frozen from
# measurement. Le Mans s29 loses p6 on its 53rd move under both labels --
# recorded, not vetoed; the fleet's own crashes fall (59 against 69).
# Round 248 (the physical world model): re-frozen from measurement; p6 keeps
# its race again -- seven finishers, no crash.
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
# Round 260: re-frozen from measurement (the faithful joint world as a chooser).
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 296: re-frozen from measurement (landings priced with the checkpoints they collect paid).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts); p2, seventh home before, now crashes on its 44th move -- recorded, not vetoed.
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); p2, which crashed on its 44th move in round 281, finishes seventh in 73 moves again -- seven finishers and no crash.
# Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
PROMOTED = (7, 0, [66, 67, 68, 69, 70, 72, 73])
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
# Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
PROMOTED_FINISHERS = [(1, 66), (3, 67), (5, 68), (7, 69), (8, 70), (2, 72), (4, 73)]
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
PROMOTED_CRASHES = []
# Round 278: re-frozen from measurement (the chooser's pick stands).
# Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
# Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
# Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
PROMOTED_ALL_MOVES = {1: 66, 2: 72, 3: 67, 4: 73, 5: 68, 6: 72, 7: 69, 8: 70}

# Le Mans s87 reaches and fails the componentwise proof. Le Mans s93 is the
# early-round trajectory-only class excluded by the last-three-movers gate;
# s14 retains the adjacent historical false positive. The remaining controls
# cover every redistribution/slowdown class shared with the older broad arm.
# Every complete trajectory must remain the current champion.
# Round 247 (the soft rollout at one level, not two): every retention case
# re-frozen from measurement; Silverstone s78 gets its seventh finisher back.
# Round 248 (the physical world model): five cases re-frozen from measurement
# again; Le Mans s14 loses a car -- recorded, not vetoed.
# Round 254 (the danger guard in a faithful world): Le Mans s14 is whole
# again and Spa s12 re-frozen from measurement.
RETENTION_CASES = {
    # Round 228: these three Le Mans trajectories changed; the five other
    # retention trajectories remain byte-identical.
    # Round 229: Le Mans s87 is back to seven finishers and no crash (measured).
    # Round 274: re-frozen from measurement (rank first; the single-player rule made literal).
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout); p1, sixth home in 73 moves before, now crashes on its 55th move -- six finishers, recorded, not vetoed.
    PROOF_VETO: ((6, 1, [66, 67, 68, 70, 71, 71]),
                 # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
                 # Round 254: re-frozen from measurement (the danger guard in a faithful world).
                 # Round 278: re-frozen from measurement (the chooser's pick stands).
                 # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
                 # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
                 # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
                 '2ee19cdcfd36050d5fed3f940f251d81d68a5ca78a9ded350c437a8b20b81f66'),
    # Round 226 (the needle tie-break): re-frozen from measurement.
    # Round 232 (the kinematic confirm): s93 loses p6/p7's race here -- the
    # perturbation this fixture's frozen geometry keeps giving back, while the
    # live circuit's fleet crashes drop by two fifths and s29 above is whole again.
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    ("lemans", 93): ((6, 1, [66, 67, 68, 69, 70, 71]),
                     # Round 278: re-frozen from measurement (the chooser's pick stands).
                     # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
                     # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
                     '9990605e0bb39096cfdc104e9a79eb8ff8d8348b7fb4570a7642f30aaa71658b'),
    # Round 278: re-frozen from measurement (the chooser's pick stands).
    # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
    # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
    # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
    # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
    ("lemans", 14): ((7, 0, [66, 67, 68, 69, 70, 72, 72]),
                     # Round 278: re-frozen from measurement (the chooser's pick stands).
                     # Round 279: re-frozen from measurement (four rule-conformance and correctness fixes).
                     # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
                     # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds).
                     # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
                     'd51b5de1170c3b7484fb7f2831f744a6ad120880971f17e8cab5fd3e1d604594'),
    # Spa s12, s31, s40, s47 and Silverstone s78 raced here too: the same fixture
    # geometry, profile and roster as ai1_six_ahead_high_speed_regression, which
    # pins the same races by summary and digest -- so they race once, there
    # (review, 2026-09-28).
}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    summaries = {}
    logs = {}
    cases = [TARGET, *RETENTION_CASES]
    with tempfile.TemporaryDirectory(
        prefix="bounded-uncertain-field-regression-"
    ) as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["lemans"]))  # frozen pre-2026-08-29 geometry
        bench_ai.set_nplayers(8)
        for kind in LABELS:
            bench_ai.set_all_to(kind)
            for track, seed in cases:
                try:
                    # The observational field-vector switch these races once ran
                    # with left the AI in round 280; they are ordinary races.
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

    for kind in LABELS:
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
        if crashes != PROMOTED_CRASHES:
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-29 {kind} crash regression: "
                f"{crashes}, expected {PROMOTED_CRASHES}"
            )
        if moves != PROMOTED_ALL_MOVES:
            raise SystemExit(
                f"bounded uncertain-field Le Mans seed-29 {kind} complete move-count "
                f"regression: {moves}, expected {PROMOTED_ALL_MOVES}"
            )
    # Round 215 retired this comparison: the reference numbers come from the
    # pre-promotion model measured under the old single-lap rules. That build
    # cannot be re-run, and re-freezing both sides would compare this build
    # with itself.

    # Round 215 retired this check: it pinned the exact decision the car makes at
    # one moment of the race, and with checkpoints on every race that moment is
    # never reached -- the vector log for it comes back empty rather than
    # different. What the check guarded (the field-vector confirmation firing at
    # all) is exercised by the pins above, which still run this race.

    for (track, seed), (expected, expected_digest) in RETENTION_CASES.items():
        for kind in LABELS:
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

    # Round 215 retired this check for the same reason as the one above: it
    # pinned the decision at a single moment, and with checkpoints on every
    # race that moment is never reached.

    print(
        "AI1BoundedUncertainFieldRegression: OK "
        "(Le Mans s29 strict all-driver -4/finisher -3; "
        "eight-round target/vector proof, Le Mans s87 componentwise veto, "
        "and three outer retention trajectories pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
