from __future__ import annotations

"""Trainable PHOS/dyn12-inspired reference language model.

This is an independent public reconstruction of the documented mechanism:
standard causal attention blended with a Gaussian affinity derived from a
12-dimensional evolving token state. It is not represented as the exact
published/private PHOS source.
"""

import math

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Install ML extra: pip install 'cosmos-beast-box[ml]'") from exc


class MixtureOfStatesAttention(nn.Module):
    def __init__(self, d_model: int, n_heads: int, state_dim: int = 12, gate_init: float = -1.0, sigma_init: float = 0.75):
        super().__init__()
        if d_model % n_heads:
            raise ValueError("d_model must be divisible by n_heads")
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.qkv = nn.Linear(d_model, 3 * d_model)
        self.out = nn.Linear(d_model, d_model)
        self.state_proj = nn.Linear(d_model, state_dim)
        self.gate_logit = nn.Parameter(torch.tensor(float(gate_init)))
        self.log_sigma = nn.Parameter(torch.tensor(math.log(float(sigma_init))))

    def _dynamic_state(self, x):
        raw = torch.tanh(self.state_proj(x))
        states = []
        prev = torch.zeros_like(raw[:, 0])
        for t in range(raw.shape[1]):
            prev = torch.tanh(0.82 * prev + 0.18 * raw[:, t])
            states.append(prev)
        return torch.stack(states, dim=1)

    def forward(self, x):
        b, t, d = x.shape
        qkv = self.qkv(x).view(b, t, 3, self.n_heads, self.head_dim)
        q, k, v = [qkv[:, :, i].transpose(1, 2) for i in range(3)]
        logits = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
        causal = torch.triu(torch.ones(t, t, device=x.device, dtype=torch.bool), diagonal=1)
        logits = logits.masked_fill(causal, float("-inf"))
        a = torch.softmax(logits, dim=-1)

        state = self._dynamic_state(x)
        delta = state[:, :, None, :] - state[:, None, :, :]
        d2 = (delta * delta).sum(dim=-1)
        sigma = self.log_sigma.exp().clamp_min(1e-4)
        h_logits = -d2 / (2.0 * sigma * sigma)
        h_logits = h_logits.masked_fill(causal, float("-inf"))
        h = torch.softmax(h_logits, dim=-1).unsqueeze(1)
        gate = torch.sigmoid(self.gate_logit)
        mixed = (1.0 - gate) * a + gate * h
        y = mixed @ v
        y = y.transpose(1, 2).contiguous().view(b, t, d)
        return self.out(y), {"state": state, "gate": gate.detach(), "sigma": sigma.detach(), "affinity": h.detach()}


class Block(nn.Module):
    def __init__(self, d_model: int, n_heads: int, mlp_ratio: int = 4):
        super().__init__()
        self.n1 = nn.LayerNorm(d_model)
        self.attn = MixtureOfStatesAttention(d_model, n_heads)
        self.n2 = nn.LayerNorm(d_model)
        self.mlp = nn.Sequential(nn.Linear(d_model, mlp_ratio * d_model), nn.GELU(), nn.Linear(mlp_ratio * d_model, d_model))

    def forward(self, x):
        y, telemetry = self.attn(self.n1(x))
        x = x + y
        x = x + self.mlp(self.n2(x))
        return x, telemetry


class PHOSReferenceLM(nn.Module):
    def __init__(self, vocab_size: int, d_model: int = 192, n_heads: int = 6, n_layers: int = 4, max_seq_len: int = 256):
        super().__init__()
        self.max_seq_len = max_seq_len
        self.token = nn.Embedding(vocab_size, d_model)
        self.pos = nn.Embedding(max_seq_len, d_model)
        self.blocks = nn.ModuleList([Block(d_model, n_heads) for _ in range(n_layers)])
        self.norm = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)
        self.head.weight = self.token.weight

    def forward(self, ids, targets=None):
        b, t = ids.shape
        if t > self.max_seq_len:
            raise ValueError("sequence longer than max_seq_len")
        p = torch.arange(t, device=ids.device)
        x = self.token(ids) + self.pos(p)[None, :, :]
        telemetry = []
        for block in self.blocks:
            x, tel = block(x)
            telemetry.append(tel)
        logits = self.head(self.norm(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), targets.reshape(-1))
        return {"logits": logits, "loss": loss, "telemetry": telemetry}
