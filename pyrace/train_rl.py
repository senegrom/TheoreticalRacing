"""RL self-play: fine-tune the BC clone to EXCEED AI2.9.

All 8 cars run the current (stochastic) policy; each car is rewarded by its
finishing place. REINFORCE with the value head as a baseline. Warm-started from
the BC clone, so the policy already drives -- RL sharpens the racecraft in
traffic (the frontier AI2.9's opponent-blind heuristics can't fully exploit).

Usage: python train_rl.py [iterations]
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import numpy as np
import torch
import torch.nn.functional as F

from track import Track
from engine import RaceState, Car, ACCELS
from features import compute_dist_map, encode, BIG, JAVA_MAX
from reachability import ensure_reach
from gamelog import parse_log
from model import RacePolicy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
JAR = os.path.join(ROOT, "theoreticRacing.jar")
LOG = os.path.join(ROOT, "last_game.log")
PROPS = os.path.join(ROOT, "user.properties")
BC = os.path.join(HERE, "data", "bc_policy.pt")
OUT = os.path.join(HERE, "data", "rl_policy.pt")

# fast + traffic-rich tracks: keep rollouts cheap, focus on the racecraft RL targets
TRACKS = ["sprint", "hairpin", "triangle", "curve", "bigoval", "chicane", "zigzag"]

_setups: dict = {}


def _starts(track_name: str):
    bak = open(PROPS, encoding="utf-8").read()
    open(PROPS, "w", encoding="utf-8").write(re.sub(r"(player[1-8]Kind=)AI[12]", r"\g<1>AI1", bak))
    subprocess.run(["java", "-jar", JAR, "--auto", "--track", track_name],
                   capture_output=True, text=True, timeout=300)
    open(PROPS, "w", encoding="utf-8").write(bak)
    starts, _ = parse_log(LOG)
    return starts


def setup(track_name: str):
    if track_name in _setups:
        return _setups[track_name]
    t = Track.load(os.path.join(ROOT, "tracks", f"{track_name}.track"))
    dist = compute_dist_map(t)
    maxd = float(dist[dist < BIG].max()) if (dist < BIG).any() else 1.0
    reach = ensure_reach(track_name)
    finite = reach.turns[reach.turns < JAVA_MAX]
    maxt = float(finite.max()) if finite.size else 1.0
    starts = _starts(track_name)
    _setups[track_name] = (t, dist, maxd, reach, maxt, starts)
    return _setups[track_name]


def rollout(model: RacePolicy, track_name: str, sample=True):
    """One self-play game; returns per-decision samples + each car's reward.
    samples: list of (ego, opps, om(effective), st, action, car). rewards[car]."""
    t, dist, maxd, reach, maxt, starts = setup(track_name)
    n = max(starts)
    state = RaceState(track=t, cars=[Car(*starts[i + 1]) for i in range(n)])
    samples = []
    guard = 0
    while not state.over and guard < 4000:
        i = state.turn
        board = [(c.x, c.y, c.vx, c.vy, c.done) for c in state.cars]
        ego, opps, om, am, st, alive = encode(board, i, t, dist, maxd, reach, maxt)
        eff = alive if alive.any() else am                 # restrict to feasible moves
        with torch.no_grad():
            lo, _ = model.act_value(torch.tensor(ego[None]), torch.tensor(opps[None]),
                                    torch.tensor(om[None]), torch.tensor(eff[None]),
                                    torch.tensor(st[None]))
        p = F.softmax(lo[0], dim=0)
        a_idx = int(torch.multinomial(p, 1)) if sample else int(lo[0].argmax())
        samples.append((ego, opps, om, eff, st, a_idx, i))
        state.step(ACCELS[a_idx])
        guard += 1
    # reward = normalized finishing place (relative, symmetric ~0.5 in self-play)
    # + an ABSOLUTE crash penalty so the policy has a signal it can actually move
    # (finishing beats crashing regardless of place).
    rewards = np.zeros(n, dtype=np.float32)
    for idx, c in enumerate(state.cars):
        place = c.place if c.place > 0 else n
        rewards[idx] = (n - place) / (n - 1) - (0.6 if c.crashed else 0.0)
    return samples, rewards, state.finished_first, state.finished_last


def main() -> int:
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    torch.set_num_threads(1)
    torch.manual_seed(0)
    model = RacePolicy()
    if os.path.isfile(BC):
        model.load_state_dict(torch.load(BC), strict=False)   # value_head starts fresh
        print("warm-started from BC clone (value head fresh)")
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-5)

    games_per_iter = 6
    for it in range(iters):
        egos, oppz, oms, ams, sts, acts, rets = [], [], [], [], [], [], []
        fin = crash = 0
        for g in range(games_per_iter):
            tr = TRACKS[(it * games_per_iter + g) % len(TRACKS)]
            samples, rewards, ff, fl = rollout(model, tr)
            fin += ff; crash += fl
            for (ego, opps, om, eff, st, a, car) in samples:
                egos.append(ego); oppz.append(opps); oms.append(om)
                ams.append(eff); sts.append(st); acts.append(a); rets.append(rewards[car])
        ego = torch.tensor(np.stack(egos)); opps = torch.tensor(np.stack(oppz))
        om = torch.tensor(np.stack(oms)); am = torch.tensor(np.stack(ams))
        st = torch.tensor(np.stack(sts)); act = torch.tensor(acts, dtype=torch.long)
        ret = torch.tensor(rets, dtype=torch.float32)

        logits, value = model.act_value(ego, opps, om, am, st)
        logp = F.log_softmax(logits, dim=1).gather(1, act[:, None]).squeeze(1)
        adv = (ret - value.detach())
        adv = (adv - adv.mean()) / (adv.std() + 1e-6)
        p = F.softmax(logits, dim=1)
        entropy = -(p * F.log_softmax(logits, dim=1)).sum(1).mean()
        loss = -(logp * adv).mean() + 0.5 * F.mse_loss(value, ret) - 0.01 * entropy
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if it % 5 == 0 or it == iters - 1:
            print(f"iter {it:3d}  loss {loss.item():+.3f}  reward {ret.mean():.3f}  "
                  f"ent {entropy.item():.2f}  fin/crash {fin}/{crash}")
    torch.save(model.state_dict(), OUT)
    print(f"saved -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
