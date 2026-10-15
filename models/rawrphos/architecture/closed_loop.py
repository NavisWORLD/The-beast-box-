"""Optional CST closed-loop adapter for RAWRPHOS (additive; off unless attached).

Mirrors the Sim Earth CST closed loop (NavisWORLD/Cosmic-synapse-...-sim-engine- PR #68/#69):
  * a recurrent 54-channel loop state s_t in [0,1]^54 carried across positions,
  * Lorenz-coupled gating (a bounded Lorenz system forced by the state),
  * Hebbian fast weights (decaying outer-product memory, norm-bounded),
  * an optional Bell channel: the model's own state picks the CHSH setting each step and
    receives an outcome product in {-1,+1} replayed from the RECORDED real IBM CHSH run
    db8iu85ckpjs73b13msg (ibm_marrakesh), or from a classical LHV (|S|<=2) or matched-PRNG control.
Every quantity is unitless and bounded. The Bell outcome is replayed data, not a live quantum link.

Adoption (one flag):  attach_closed_loop(model, mode)  with mode in MODES.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import torch
from torch import nn

MODES = ("off", "ema", "loop", "bell_recorded", "bell_lhv", "bell_matched")
CHSH_RECEIPT = Path(__file__).resolve().parents[3] / "apps/beastbox-cloud/public/spark/ibm-cst-chsh-20261015.json"
SETTINGS = ("a0b0", "a0b1", "a1b0", "a1b1")


def load_chsh(path: Path = CHSH_RECEIPT) -> dict:
    d = json.loads(Path(path).read_text())
    if d.get("job_id") != "db8iu85ckpjs73b13msg" or d.get("source_class") != "RECORDED_IBM_HARDWARE":
        raise ValueError("unexpected CHSH source")
    tables = {}
    for r in d["runs"]:
        counts = {b: int(n) for b, n in (p.split(":") for p in r["c"].split(","))}
        tables[r["k"].split("chsh-")[1]] = counts
    return {"label": "REAL IBM QUANTUM HARDWARE RUN", "job_id": d["job_id"], "backend": d["backend"], "tables": tables}


class BellSource:
    """Outcome products for settings (i,j). 'recorded' replays the per-setting histogram in a fixed stride order;
    'matched' resamples the same per-setting joint table classically; 'lhv' shrinks each correlator by min(1,2/|S|)."""
    def __init__(self, chsh: dict, mode: str, seed: int = 0):
        self.mode = mode; self.g = torch.Generator().manual_seed(seed)
        seqs, E = [], []
        for k in SETTINGS:
            c = chsh["tables"][k]; n = sum(c.values())
            prods = []
            for b, m in sorted(c.items()): prods += [1.0 if b[0] == b[1] else -1.0] * m
            p = torch.tensor(prods)
            idx = (torch.arange(n) * 7919) % n          # deterministic replay order
            seqs.append(p[idx]); E.append(float(p.mean()))
        self.seqs, self.E = seqs, torch.tensor(E)
        S = E[0] + E[1] + E[2] - E[3]; self.S = S
        self.f = min(1.0, 2.0 / max(1e-9, abs(S))); self.k = [0, 0, 0, 0]

    def lhv_S(self): return float(self.S * self.f)

    def __call__(self, setting: torch.Tensor) -> torch.Tensor:  # setting: long [B] in 0..3
        out = torch.empty(setting.shape)
        for s in range(4):
            m = setting == s; n = int(m.sum())
            if not n: continue
            if self.mode == "recorded":
                seq = self.seqs[s]; i0 = self.k[s]; self.k[s] += n
                out[m] = seq[(torch.arange(n) + i0) % len(seq)]
            elif self.mode == "matched":
                seq = self.seqs[s]; out[m] = seq[torch.randint(len(seq), (n,), generator=self.g)]
            else:
                p = (1 + self.E[s] * self.f) / 2
                out[m] = torch.where(torch.rand(n, generator=self.g) < p, 1.0, -1.0)
        return out


class ClosedLoopAdapter(nn.Module):
    def __init__(self, d_model: int, mode: str = "loop", chsh: dict | None = None, seed: int = 0,
                 hebb_decay: float = 0.9, hebb_rate: float = 0.1):
        super().__init__()
        if mode not in MODES: raise ValueError(f"mode must be one of {MODES}")
        self.mode, self.d = mode, d_model
        self.inp = nn.Linear(d_model, 54); self.rec = nn.Linear(54, 54, bias=False)
        self.alpha = nn.Parameter(torch.tensor(-1.0))            # leak in (0,1) via sigmoid
        self.q = nn.Linear(54, 16, bias=False); self.kk = nn.Linear(54, 16, bias=False); self.v = nn.Linear(54, 16, bias=False)
        self.gate = nn.Linear(d_model, 1); self.lorenz_gain = nn.Parameter(torch.tensor(0.5))
        self.bell_emb = nn.Parameter(torch.zeros(54))
        self.out = nn.Linear(54 + 16, d_model); nn.init.zeros_(self.out.weight); nn.init.zeros_(self.out.bias)
        self.hebb_decay, self.hebb_rate = hebb_decay, hebb_rate
        self.bell = BellSource(chsh, mode.split("_", 1)[1], seed) if mode.startswith("bell") else None

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        if self.mode == "off": return h
        B, T, _ = h.shape; a = torch.sigmoid(self.alpha)
        s = torch.full((B, 54), 0.5, device=h.device)
        if self.mode == "ema":                              # moving-average baseline: no recurrence/Hebb/Lorenz/Bell
            outs = []
            for t in range(T):
                s = (1 - a) * s + a * torch.sigmoid(self.inp(h[:, t])); outs.append(torch.cat([s, torch.zeros(B, 16)], -1))
            return h + self.out(torch.stack(outs, 1))
        L = torch.tensor([0.1, 0.2, 0.3]).repeat(B, 1); F = torch.zeros(B, 16, 16); outs = []; gates = []
        for t in range(T):
            drive = self.inp(h[:, t]) + self.rec(s - 0.5)
            if self.bell is not None:
                setting = ((s[:, 6] > 0.5).long() * 2 + (s[:, 45] > 0.5).long()).detach()
                drive = drive + self.bell_emb * self.bell(setting)[:, None]
            s = (1 - a) * s + a * torch.sigmoid(drive)
            # Lorenz (sigma=10, rho=28, beta=8/3), x forced by mean state; bounded with reset
            x, y, z = L.unbind(-1); f = 2.0 * (s.mean(-1).detach() - 0.5); dt = 0.01
            L = torch.stack([x + dt * (10 * (y - x) + f), y + dt * (x * (28 - z) - y), z + dt * (x * y - 8 / 3 * z)], -1)
            L = torch.where(L.abs().amax(-1, keepdim=True) > 80, torch.tensor([0.1, 0.2, 0.3]), L)
            chaos = (L.norm(dim=-1) / 55).clamp(0, 1)
            g = torch.sigmoid(self.gate(h[:, t]).squeeze(-1) + self.lorenz_gain * (chaos - 0.5))
            q, k, v = torch.tanh(self.q(s)), torch.tanh(self.kk(s)), torch.tanh(self.v(s))
            read = torch.einsum("bij,bj->bi", F, q)
            F = self.hebb_decay * F + self.hebb_rate * torch.einsum("bi,bj->bij", v, k)
            F = F / F.flatten(1).norm(dim=-1).clamp(min=1.0)[:, None, None]   # bounded fast weights
            outs.append(g[:, None] * torch.cat([s, read], -1)); gates.append(g)
        return h + self.out(torch.stack(outs, 1))


def attach_closed_loop(model: nn.Module, mode: str = "loop", seed: int = 0, chsh: dict | None = None) -> ClosedLoopAdapter:
    """Attach to a RawrphosLM (hooks the final norm). mode='off' leaves outputs bit-identical."""
    if mode.startswith("bell") and chsh is None: chsh = load_chsh()
    ad = ClosedLoopAdapter(model.config.d_model, mode, chsh, seed)
    model.closed_loop = ad                                   # registers parameters
    model.norm.register_forward_hook(lambda _m, _i, out: ad(out))
    return ad
