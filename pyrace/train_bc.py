"""Behaviour cloning: train the transformer policy to imitate AI2.9's moves.

Loads data/bc_data.npz, trains, reports train/val top-1 accuracy (how often the
net picks AI2.9's exact move), and saves the weights to data/bc_policy.pt.

Usage: python train_bc.py [epochs]
"""
from __future__ import annotations

import os
import sys

import numpy as np
import torch
import torch.nn as nn

from model import RacePolicy

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "bc_data.npz")
OUT = os.path.join(HERE, "data", "bc_policy.pt")


def load():
    d = np.load(DATA)
    t = lambda k, dt: torch.tensor(d[k], dtype=dt)
    return (t("ego", torch.float32), t("opps", torch.float32),
            t("opp_mask", torch.float32), t("act_mask", torch.float32),
            t("action", torch.long))


def main() -> int:
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    torch.set_num_threads(1)   # tiny model: 1 thread avoids oversubscription overhead
    torch.manual_seed(0)
    ego, opps, om, am, act = load()
    n = ego.size(0)
    g = torch.Generator().manual_seed(0)
    perm = torch.randperm(n, generator=g)
    n_val = max(1, n // 6)
    vi, ti = perm[:n_val], perm[n_val:]

    model = RacePolicy()
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    lossf = nn.CrossEntropyLoss()
    # majority-class baseline (how often AI2.9's move == the single most common move)
    base = torch.bincount(act, minlength=9).max().item() / n

    def acc(idx):
        model.eval()
        with torch.no_grad():
            lo = model(ego[idx], opps[idx], om[idx], am[idx])
            return (lo.argmax(1) == act[idx]).float().mean().item()

    bs = 256
    for ep in range(epochs):
        model.train()
        for b in torch.randperm(ti.size(0)).split(bs):
            i = ti[b]
            opt.zero_grad()
            lo = model(ego[i], opps[i], om[i], am[i])
            loss = lossf(lo, act[i])
            loss.backward()
            opt.step()
        if ep % 10 == 0 or ep == epochs - 1:
            print(f"epoch {ep:3d}  loss {loss.item():.3f}  "
                  f"train_acc {acc(ti):.3f}  val_acc {acc(vi):.3f}")

    print(f"\nmajority-move baseline: {base:.3f}")
    print(f"final  train {acc(ti):.3f}  val {acc(vi):.3f}  (n={n}, val={n_val})")
    torch.save(model.state_dict(), OUT)
    print(f"saved -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
