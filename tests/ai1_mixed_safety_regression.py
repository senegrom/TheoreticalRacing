#!/usr/bin/env python3
"""Pin the Round-93 mixed-roster safety boundary and the Gear front order."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tracks"))

import bench_ai  # noqa: E402

# Round 94's Gear seed 1 in the front ordering (slots 1-4 AI1, 5-8 AI2),
# measured 2026-09-27: the first four grid slots finish first to fourth.
GEAR_FRONT_MEASURED = {"AI1": (10, 4, 0), "AI2": (26, 4, 0)}


def main() -> int:
    if not Path(bench_ai.JAR).is_file():
        raise SystemExit("theoreticRacing.jar not found; run build_main.sh first")

    # Round 78's case, Le Mans seed 2 (the unrestricted fast two-exit proof once
    # accelerated one car into another's crash 66 moves later), is the same race
    # as ai1_private_slack_regression's Le Mans s2, pinned there by digest; it
    # raced here as label halves only (review, 2026-09-28).
    with tempfile.TemporaryDirectory(prefix="theoretical-racing-ai1-mixed-") as directory:
        bench_ai.configure_runtime(directory)
        import fixture_install
        bench_ai.JAR = str(fixture_install.install(directory, ["lemans"]))  # frozen pre-2026-08-29 geometry
        bench_ai.set_nplayers(8)

        # Round 93: player 6 used to choose S from the
        # fast L2 state below and crash 30 global moves later. The normal
        # three-round model sees that landing alive but fragile; a bounded
        # four-round scorer-rival recheck proves S dies and SW survives.
        # Round 215: the orderings are mirror images now -- one policy, two grid
        # slots -- so each carries its own totals instead of sharing one.
        expected_by_label = {
            # Round 229: re-frozen from measurement (the soft caution stack left the score); finishers and crashes unchanged.
            # Round 234 (the seal guard left the decision): re-frozen from
            # measurement. The two orderings stay exact mirrors of each other.
            # Round 247 (the soft rollout at one level, not two): p7 keeps its
            # race here, so both orderings are crash-free again.
            # Round 254: re-frozen from measurement; still crash-free.
            # Round 260 (the chooser): p7 takes the wall here again, exactly as
            # in round 234 -- recorded, not vetoed (AGENTS.md), and pinned by
            # its identity below. The two orderings stay exact mirrors.
            # Round 278 (the chooser's pick stands): p7 keeps its race, both
            # orderings crash-free again and still exact mirrors.
            # 2026-09-27: one ordering. The reverse ordering was the same race
            # with the labels swapped (one policy since round 222); the label
            # invariance pin checks that once for every pin.
            # Round 281: re-frozen from measurement (every live rival plays its scorer in the chooser's rollouts).
            # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); p8, seventh home before, now crashes on its 55th move and seven finishers become six, so p1, still the car running at the end, moves up to seventh -- recorded, not vetoed, and pinned by its identity below.
            # Round 300a: re-frozen from measurement (every live rival plays its scorer in every top-level rollout).
            # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); p8, which crashed on its 55th move in rounds 292b and 300a, now keeps its race and comes home seventh on its 72nd, so six finishers become seven again and p1, still the car running at the end, drops back to eighth -- crash-free again, and that is what is pinned below.
            "front": {"AI1": (14, 4, 0), "AI2": (22, 4, 0)},
        }
        orderings = (
            ("front", ["AI1"] * 4 + ["AI2"] * 4),
        )
        # Round 215: the move index moved with the rules, the placing did not.
        # Round 229: p6 comes home fourth now, on the same move (565) in both orderings.
        # Round 233: p6 comes home sixth now, on the same move (561) in both orderings.
        # Round 234: p6 no longer places sixth here at all; the pattern and
        # its check retire with the crash recorded below.
        for label, kinds in orderings:
            bench_ai.set_kinds(kinds)
            result = bench_ai.run_track_h2h("lemans", timeout=600, seed=7)
            if result != expected_by_label[label]:
                raise SystemExit(
                    f"Round-93 mixed Le Mans seed-7 {label} regression: {result}"
                )
            log_lines = Path(bench_ai.LOG).read_text(encoding="utf-8").splitlines()
            # Round 234: this race is no longer crash-free. The seal guard used
            # to buy p7 a line here; without it p7 arrives at (84,150) too fast
            # and takes the wall. The rule records a crash rather than vetoing
            # it (AGENTS.md), so pin the crash by its identity instead.
            # Round 247: the one-level rollout keeps p7 on the road here, so the
            # race is crash-free again and that is what is pinned.
            # Round 260: one crash again, p7 into the wall at (20,136) on move
            # 439 in both orderings -- the round-234 identity pin returns.
            # Round 278: crash-free again, and that is what is pinned.
            # Round 292b: re-frozen from measurement (the chooser judges the pace landing it adds); one crash again, p8 into the wall at (20,137) on move 440, its 55th -- recorded, not vetoed, and the round-234 identity pin returns for p8.
            # Round 301a': re-frozen from measurement (the pace swap breaks only exact faithful ties); crash-free again -- p8 survives move 440, its 55th, and comes home seventh on move 555, its 72nd -- and that is what is pinned, as in rounds 247 and 278.
            crashed = [line for line in log_lines if " CRASH " in line]
            if crashed:
                raise SystemExit(
                    f"Round-93 mixed Le Mans seed-7 {label} crash set changed: {crashed}"
                )
        # Round 215 retired this check: it pinned a single move by its index in
        # the log, and with checkpoints on every race and the finish-wall rule the
        # car no longer reaches that state at all (verified by replaying the same
        # race on the pre-change build). The behaviour it guarded is covered by the
        # fleet grid and the exact-optimum check.
        # Round 234 retired the p6 placing check with the crash above: p6 no
        # longer comes home sixth in this race, and the placing was a recorded
        # property of the old trajectory rather than a rule the policy owes.
        # The finishing totals pinned above cover the outcome that matters.

        # Round 94's longer finish sprint is homogeneous-only. The unrestricted
        # experiment shifted places against the frozen policy on Gear. Until
        # 2026-09-27 this summed both orderings, which is 36 places per label by
        # construction (the two orderings mirror each other), so it could only
        # fail on a crash; the ordering's own measured totals are pinned now.
        bench_ai.set_kinds(orderings[0][1])
        gear = bench_ai.run_track_h2h("gear", timeout=600, seed=1)
        expected_gear = GEAR_FRONT_MEASURED
        if gear != expected_gear:
            raise SystemExit(
                f"Round-94 mixed Gear seed-1 place-boundary regression: {gear}, expected {expected_gear}"
            )

    print(
        "AI1MixedSafetyRegression: OK "
        "(Le Mans seed 7 safe; Gear seed 1 mixed places pinned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
