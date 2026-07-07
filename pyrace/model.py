"""Set-attention transformer policy.

Tokens = [ego, opponent_1, ..., opponent_7]; a Transformer encoder lets the ego
token attend over the opponents (permutation-invariant, padding-masked). The
ego token's output is decoded to 9 move logits, masked to the legal moves.
"""
from __future__ import annotations

import torch
import torch.nn as nn

from features import EGO_DIM, OPP_DIM, MAX_OPP, N_ACTIONS


class RacePolicy(nn.Module):
    def __init__(self, d_model: int = 64, nhead: int = 4, layers: int = 2, ff: int = 128):
        super().__init__()
        self.ego_proj = nn.Linear(EGO_DIM, d_model)
        self.opp_proj = nn.Linear(OPP_DIM, d_model)
        enc = nn.TransformerEncoderLayer(d_model, nhead, dim_feedforward=ff,
                                         batch_first=True, activation="gelu")
        self.encoder = nn.TransformerEncoder(enc, layers)
        self.head = nn.Sequential(
            nn.Linear(d_model, d_model), nn.GELU(), nn.Linear(d_model, N_ACTIONS)
        )

    def forward(self, ego, opps, opp_mask, act_mask):
        # ego [B,EGO_DIM]  opps [B,MAX_OPP,OPP_DIM]  masks [B,MAX_OPP],[B,N_ACTIONS]
        ego_tok = self.ego_proj(ego).unsqueeze(1)          # [B,1,d]
        opp_tok = self.opp_proj(opps)                       # [B,MAX_OPP,d]
        tokens = torch.cat([ego_tok, opp_tok], dim=1)       # [B,1+MAX_OPP,d]
        pad = torch.cat([torch.zeros(ego.size(0), 1, device=ego.device),
                         1.0 - opp_mask], dim=1).bool()     # True = ignore (padding)
        enc = self.encoder(tokens, src_key_padding_mask=pad)
        logits = self.head(enc[:, 0])                       # ego token -> [B,N_ACTIONS]
        return logits.masked_fill(act_mask == 0, -1e9)
