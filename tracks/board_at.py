#!/usr/bin/env python3
"""Reconstruct the board at one global move index of a game log.

Prints the mover's state, every live car, and the mover's 9 candidate
landings classified: BODY (live rival on the cell), DEAD-STATE (reach
says the landing state cannot finish / off-board), or OPEN. Segment-level
wall legality is NOT checkable offline -- an OPEN cell may still be an
illegal cut (use oracle_roll.py's mask for exact classification); a
DEAD-STATE/BODY verdict is definitive.

In a LAP race the dumped map is the finish map and knows nothing of the
checkpoint gates, so it calls live states DEAD-STATE wholesale; use
needle_audit.py there, which asks the game's oracle instead.

Usage: board_at.py <log> <reach.bin> <moveIndex>
"""
import argparse
import sys

if __package__:
    from .forensics_common import Reach, log_player_count, reconstruct_board
else:
    from forensics_common import Reach, log_player_count, reconstruct_board


def configure_console():
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace")


def main(argv=None):
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("log")
    parser.add_argument("reach_bin")
    parser.add_argument("move_index", type=int)
    args = parser.parse_args(argv)

    reach = Reach(args.reach_bin)
    cars, mover, real_moves = reconstruct_board(
        args.log, args.move_index, log_player_count(args.log)
    )
    move = real_moves[0]
    print(
        "move %d: p%d at (%d,%d) v(%d,%d) -> chose %s land (%d,%d) "
        "v(%d,%d) [%s]"
        % (
            move.index, move.player, move.x, move.y,
            move.old_vx, move.old_vy, move.direction,
            move.new_x, move.new_y, move.new_vx, move.new_vy, move.status,
        )
    )

    print("\nlive cars (post their last move):")
    for index, car in enumerate(cars):
        if index == mover or car[4] != 0:
            continue
        x, y, vx, vy, _ = car
        distance = max(abs(x - move.x), abs(y - move.y))
        print("  p%d (%d,%d) v(%d,%d)  dist=%d" % (index + 1, x, y, vx, vy, distance))

    bodies = {
        (car[0], car[1])
        for index, car in enumerate(cars)
        if index != mover and car[4] == 0
    }
    print(
        "\ncandidates from (%d,%d) v(%d,%d):"
        % (move.x, move.y, move.old_vx, move.old_vy)
    )
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            vx, vy = move.old_vx + dx, move.old_vy + dy
            x, y = move.x + vx, move.y + vy
            turns = reach.turns(x, y, vx, vy)
            classification = (
                "BODY" if (x, y) in bodies
                else "DEAD-STATE" if turns is None
                else "open t=%d" % turns
            )
            mark = " <== chosen" if (x, y) == (move.new_x, move.new_y) else ""
            print(
                "  d(%+d,%+d) land (%d,%d) v(%d,%d): %s%s"
                % (dx, dy, x, y, vx, vy, classification, mark)
            )


if __name__ == "__main__":
    main()
