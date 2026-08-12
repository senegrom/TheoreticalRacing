"""Rival-policy matrix vs the two oracle-proven queue boxes.

For each candidate RIVAL policy, replicate the in-game simOutcome world
EXACTLY (me = selfMove proxy, exactSelf semantics; round 0 = players after
the mover; finish-vanish; null-move = death) using oracle mask queries for
legality/occupancy and the reach dump for ttf -- and test, at both crash
sites, whether the policy (a) flags the champion's real chosen landing as
DEAD and (b) keeps the oracle-proven survivor ALIVE. A policy that does both
reproduces the real boxes and is worth building in Java.

Policies: greedy (min ttf) | gmom (min ttf, tie: faster) |
          shape (ttf + trap ladder) | smom (shape, tie: faster) |
          orivals (real scorer for rivals, selfMove me -- buildable ceiling)
"""
import os
import sys

if __package__:
    from .forensics_common import DIRS, Oracle, Reach, log_player_count, reconstruct_board
else:
    from forensics_common import DIRS, Oracle, Reach, log_player_count, reconstruct_board

HERE = os.path.dirname(os.path.abspath(__file__))
# Reach dumps and logs resolve against RACING_WORK_DIR (default: this script's
# directory); RACING_PROPS can select matching non-eight-car properties. The
# SITES table below references campaign-era artifacts as worked examples --
# point WORK at a directory
# holding your own logs/dumps to analyze new sites.
S = os.environ.get('RACING_WORK_DIR', HERE)
JAR = os.path.join(os.path.dirname(HERE), 'theoreticRacing.jar')
PROPS = os.environ.get('RACING_PROPS', os.path.join(HERE, 'bench.properties'))


def board_at(log, target):
    cars, mover, _ = reconstruct_board(log, target, log_player_count(log))
    return [list(car) for car in cars], mover


class Sim:
    def __init__(self, oracle, reach, policy):
        self.o = oracle
        self.reach = reach
        self.policy = policy          # rival policy name

    def viable(self, i, cars):
        """Rival/self candidates: list of (diridx, tt, spd2, land). 'F' returns
        the instant-win marker."""
        x, y, vx, vy, fin = cars[i]
        _, _, mask = self.o.ask(i, cars)
        out = []
        for ci, (dx, dy) in enumerate(DIRS):
            c = mask[ci]
            if c == 'F':
                return 'F', ci
            if c != 'A':
                continue
            nvx, nvy = vx + dx, vy + dy
            tt = self.reach.turns(x + nvx, y + nvy, nvx, nvy)
            if tt is None:
                continue
            out.append((ci, tt, nvx * nvx + nvy * nvy, (x + nvx, y + nvy, nvx, nvy)))
        return 'M', out

    def tier(self, i, cars, land):
        """Safe-successor count (cap 3) of `land` for car i: query from the
        post-move board."""
        saved = cars[i][:]
        cars[i] = [land[0], land[1], land[2], land[3], 0]
        _, _, mask = self.o.ask(i, cars)
        cars[i] = saved
        n = sum(1 for c in mask if c in 'AF')
        return min(n, 3)

    def rival_move(self, i, cars):
        if self.policy == 'orivals':
            dx, dy, mask = self.o.ask(i, cars)
            ci = DIRS.index((dx, dy))
            c = mask[ci]
            if c == 'F':
                return 'F', None
            if c != 'A':
                return None, None            # scorer itself is boxed -> dies
            x, y, vx, vy, fin = cars[i]
            return 'M', (x + vx + dx, y + vy + dy, vx + dx, vy + dy)
        kind, v = self.viable(i, cars)
        if kind == 'F':
            return 'F', None
        if not v:
            return None, None
        need_tier = self.policy in ('shape', 'smom')
        best = None
        for ci, tt, spd2, land in v:
            trap = 0.0
            if need_tier:
                tr = self.tier(i, cars, land)
                trap = 50.0 if tr == 0 else 2.0 if tr == 1 else 0.5 if tr == 2 else 0.0
            score = tt + trap
            if best is None:
                best = (score, spd2, ci, land)
                continue
            better = score < best[0] - 1e-9
            if not better and abs(score - best[0]) <= 1e-9 and self.policy in ('gmom', 'smom'):
                better = spd2 > best[1]
            if better:
                best = (score, spd2, ci, land)
        return 'M', best[3]

    def self_move(self, i, cars):
        """selfMove replica: max tier (cap 3), tie -> min tt, first-wins."""
        kind, v = self.viable(i, cars)
        if kind == 'F':
            return 'F', None
        if not v:
            return None, None
        best = None                    # (tier, tt, ci, land)
        for ci, tt, spd2, land in v:
            tr = self.tier(i, cars, land)
            if best is None or tr > best[0] or (tr == best[0] and tt < best[1]):
                best = (tr, tt, ci, land)
        return 'M', best[3]

    def roll(self, cars, me, rounds):
        cars = [c[:] for c in cars]
        for r in range(rounds):
            start = me + 1 if r == 0 else 0
            for i in range(start, len(cars)):
                if cars[i][4] != 0 or (i == me and r == 0):
                    continue
                kind, land = self.rival_move(i, cars) if i != me else self.self_move(i, cars)
                if kind == 'F':
                    cars[i][4] = 90
                    continue
                if kind is None:
                    if i == me:
                        return 'DEAD@r%d' % r
                    cars[i][4] = 99
                    continue
                cars[i] = [land[0], land[1], land[2], land[3], 0]
        f = cars[me]
        tt = self.reach.turns(f[0], f[1], f[2], f[3])
        tier = self.tier(me, cars, (f[0], f[1], f[2], f[3]))
        return 'alive t=%s tier=%d' % ('DOOM' if tt is None else tt, tier)


SITES = [
    ('silverstone', 'champ_logs/inert_AI1_silverstone_s6.log', 145,
     [('chosen W', 3), ('survivor N', 1)]),
    ('hungaroring', 'champ_logs/inert_AI1_hungaroring_s6.log', 181,
     [('chosen W', 3), ('survivor NONE', 4)]),
]
# The rounds 59-65 pocket sites (hungaroring m389, lemans m63, zigzag m102,
# hairpin m90) were resolved by promoted mechanisms and their session logs
# purged; regenerate the race + reach dump before re-adding an entry. Current
# entries are live investigation sites.
POCKET = [
    ('zandvoort', 'harvest/h8_zandvoort_s42.log', 566,
     [('chosen SW', 6), ('survivor S', 7), ('survivor NW', 0)]),
    ('coil', 'harvest/h8_coil_s32.log', 247,
     [('chosen NE', 2), ('survivor NONE', 4), ('survivor N', 1)]),
    ('zandvoort', 'harvest/h8_zandvoort_s45.log', 920,
     [('chosen E', 5), ('survivor SE', 8)]),
    ('interlagos', 'r73_inter_s10.log', 103,
     [('chosen NE', 2), ('survivor NONE', 4), ('survivor S', 7)]),
    ('nurburgring', 'harvest/h8_nurburgring_s19.log', 260,
     [('chosen E', 5), ('survivor N', 1)]),
    ('monaco', 'harvest/h4_monaco_s9.log', 27,
     [('chosen NONE', 4), ('survivor N', 1), ('survivor SE', 8)]),
]
POLICIES = ['greedy', 'gmom', 'shape', 'smom', 'orivals']


def main():
    reconfigure = getattr(sys.stdout, 'reconfigure', None)
    if reconfigure is not None:
        reconfigure(encoding='utf-8', errors='replace')
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    sites = POCKET if len(sys.argv) > 2 and sys.argv[2] == 'pocket' else SITES
    global POLICIES
    if len(sys.argv) > 3:
        POLICIES = sys.argv[3].split(',')
    for track, log, target, cands in sites:
        reach = Reach(os.path.join(S, 'reach_%s.bin' % track))
        cars0, mover = board_at(os.path.join(S, log), target)
        oracle = Oracle(track, JAR, PROPS)
        try:
            print('%s m%d (p%d):' % (track, target, mover + 1))
            for label, ci in cands:
                dx, dy = DIRS[ci]
                x, y, vx, vy, fin = cars0[mover]
                nvx, nvy = vx + dx, vy + dy
                row = ['  %-14s' % label]
                for pol in POLICIES:
                    cc = [c[:] for c in cars0]
                    cc[mover] = [x + nvx, y + nvy, nvx, nvy, 0]
                    sim = Sim(oracle, reach, pol)
                    row.append('%s=%s' % (pol, sim.roll(cc, mover, rounds)))
                print(' '.join(row))
            print('  (%d oracle asks)' % oracle.asks)
        finally:
            oracle.close()


if __name__ == '__main__':
    main()
