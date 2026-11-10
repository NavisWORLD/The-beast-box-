"""Optional CST psi readout for the Spark's 12D state. OFF by default. DERIVED. Never drives hardware.

Decided by Robot X under Cory's delegation 2026-11-09 (docs/DESIGN_DECISIONS.md D4). AI-WRITTEN GLUE.

The brief quoted psi = integral(phi*sqrt(m^2c^2 + c^4) + lambda*dx) dt. That exact form is in none of Cory's repos.
The closest real form, the one written for a 12D adaptive state, is
NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.20 README.md:78 (commit 5b6e010a253c):

    psi_i = (phi * Ec_i)/(c^2 m0) + lambda_i/E_ref + integral |dx12_i/dt| dt + (Omega_i * Ec_i)/E_ref + Ugrav_i/E_ref

It has the same three ingredients as the quoted one: a phi-scaled energy term, a lambda term, and an integrated
displacement (path) term. Mapping onto the Spark (DESIGN CHOICES, dimensionless "natural units"):
    c = m0 = E_ref = 1
    Ec      = mean(x^2) over dyn12                         (contextual energy of the state)
    lambda  = EMA of ln((|dx_t|+eps)/(|dx_{t-1}|+eps))     (local divergence rate, a Lyapunov-style ESTIMATE)
    path    = sum |dx_t| since the layer was switched on    (integral |dx12/dt| dt)
    Omega   = (D11 + 1)/2, the routed dominant-frequency drive in [0, 1]; 0 when D11 is masked
    Ugrav   = 0  (the Spark has no masses to couple; the term is kept and reported as 0)
Nothing reads this value back into routing, LEDs, speaker, UV or memory. Expression ignores it (tested).
"""
from __future__ import annotations

import math
from typing import Any

PHI = (1.0 + math.sqrt(5.0)) / 2.0
SOURCE = "NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.20 README.md:78 @5b6e010a253c"
EPS = 1e-9


class PsiLayer:
    def __init__(self, ema: float = 0.2) -> None:
        self.prev: list[float] | None = None
        self.prev_step = 0.0
        self.lam = 0.0
        self.path = 0.0
        self.ema = float(ema)
        self.n = 0

    def update(self, dyn12: list[float], d12: list[float], mask12: list[bool]) -> dict[str, Any]:
        x = [float(v) for v in dyn12]
        if len(x) != 12:
            raise ValueError("psi layer expects the 12D state")
        ec = sum(v * v for v in x) / 12.0
        if self.prev is not None:
            dx = math.sqrt(sum((a - b) ** 2 for a, b in zip(x, self.prev)))
            if self.n >= 2:
                self.lam = (1 - self.ema) * self.lam + self.ema * math.log((dx + EPS) / (self.prev_step + EPS))
            self.path += dx
            self.prev_step = dx
        self.prev = x
        self.n += 1
        omega = (float(d12[10]) + 1.0) / 2.0 if mask12[10] else 0.0
        terms = {"phi_energy": PHI * ec, "lambda": self.lam, "path": self.path, "omega_energy": omega * ec, "u_grav": 0.0}
        return {"psi": sum(terms.values()), "terms": terms, "Ec": ec, "omega": omega, "steps": self.n,
                "label": "DERIVED (CST psi readout, natural units; not a physical measurement)",
                "source": SOURCE, "drives_hardware": False}
