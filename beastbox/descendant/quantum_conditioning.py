"""Numerical quantum conditioning contract for Descendant-001.

The core feature-vector helpers are dependency-free.  The optional torch adapter is
available when the ``ml`` extra is installed.  Zero initialisation is a hard
lineage invariant: attaching the adapter must not change the MEMORY parent before
an optimisation step occurs.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

FEATURE_ORDER = (
    "normalized_entropy",
    "bit_one_fraction",
    "bit_balance_distance",
    "mean_longest_run",
    "adjacent_bit_agreement",
    "unique_outcomes",
    "shannon_entropy_bits",
)

# Expected physical/statistical ranges for the pinned 5-bit archive.  Values are
# clipped only for conditioning stability; the immutable packet preserves the raw
# derived values and hashes separately.
_FEATURE_RANGES = (
    (0.0, 1.0),   # normalized entropy
    (0.0, 1.0),   # bit one fraction
    (0.0, 0.5),   # distance from 0.5
    (1.0, 5.0),   # mean longest run for 5 bits
    (0.0, 1.0),   # adjacent agreement
    (1.0, 32.0),  # unique 5-bit outcomes
    (0.0, 5.0),   # Shannon entropy bits
)


def _validate_alpha(alpha: float) -> float:
    value = float(alpha)
    if not math.isfinite(value) or not 0.0 < value <= 1.0:
        raise ValueError("alpha must be finite and in (0, 1]")
    return value


def feature_vector(packet: Any) -> tuple[float, ...]:
    features = getattr(packet, "features", None)
    if not isinstance(features, Mapping):
        raise ValueError("packet.features must be a mapping")
    missing = [name for name in FEATURE_ORDER if name not in features]
    if missing:
        raise ValueError(f"packet missing quantum features: {missing}")
    return tuple(float(features[name]) for name in FEATURE_ORDER)


def normalize_feature_vector(values: Iterable[float]) -> tuple[float, ...]:
    vals = tuple(float(v) for v in values)
    if len(vals) != len(FEATURE_ORDER):
        raise ValueError(f"expected {len(FEATURE_ORDER)} quantum features")
    if not all(math.isfinite(v) for v in vals):
        raise ValueError("quantum features must be finite")
    out: list[float] = []
    for value, (lo, hi) in zip(vals, _FEATURE_RANGES, strict=True):
        clipped = min(max(value, lo), hi)
        # map the documented range to [-1, 1]
        out.append(((clipped - lo) / (hi - lo)) * 2.0 - 1.0)
    return tuple(out)


def bounded_geometry_scale(projection: Iterable[float], *, alpha: float = 0.25) -> tuple[float, ...]:
    """Map an arbitrary projection to a bounded multiplicative CST geometry scale."""

    gain = _validate_alpha(alpha)
    values = tuple(float(v) for v in projection)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("geometry projection must be finite")
    return tuple(1.0 + gain * math.tanh(v) for v in values)


try:  # optional dependency; base package intentionally has no hard torch dependency
    import torch
    from torch import nn
except ImportError:  # pragma: no cover - exercised by base CI import behaviour
    torch = None
    nn = None


def apply_geometry_scale(x54, scale):
    """Apply a 54D multiplicative scale to native CST state geometry."""

    if torch is None:
        raise ImportError("apply_geometry_scale requires the optional 'ml' dependency (torch)")
    if x54.shape[-1] != 54 or scale.shape[-1] != 54:
        raise ValueError("expected 54D CST geometry")
    while scale.ndim < x54.ndim:
        scale = scale.unsqueeze(-2)
    return x54 * scale


if nn is not None:
    class Quantum54Adapter(nn.Module):
        """Zero-initialised 7→54D conditioner for the CST state kernel."""

        def __init__(self) -> None:
            super().__init__()
            self.linear = nn.Linear(len(FEATURE_ORDER), 54, bias=True)
            nn.init.zeros_(self.linear.weight)
            nn.init.zeros_(self.linear.bias)

        def forward(self, values):
            if values.shape[-1] != len(FEATURE_ORDER):
                raise ValueError(f"expected final dimension {len(FEATURE_ORDER)}")
            # Tensor equivalent of normalize_feature_vector, kept differentiable with
            # respect to adapter weights while packet values remain constants.
            lo = values.new_tensor([r[0] for r in _FEATURE_RANGES])
            hi = values.new_tensor([r[1] for r in _FEATURE_RANGES])
            if not torch.isfinite(values).all():
                raise ValueError("quantum features must be finite")
            normalized = ((values.clamp(min=lo, max=hi) - lo) / (hi - lo)) * 2.0 - 1.0
            return self.linear(normalized)

        def geometry_scale(self, values, *, alpha: float = 0.25):
            """Return a bounded multiplicative 54D scale; exact identity at zero init."""

            gain = _validate_alpha(alpha)
            return 1.0 + gain * torch.tanh(self.forward(values))
else:
    class Quantum54Adapter:  # pragma: no cover - only used without optional ML extra
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError("Quantum54Adapter requires the optional 'ml' dependency (torch)")
