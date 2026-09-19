"""Cancellation and observability diagnostics for the isolated CST candidate.

Decimal arithmetic re-sums already-computed float64 term telemetry. It does
NOT rerun source equations at arbitrary precision or establish physical truth.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
import math
from typing import Mapping

from .model import Parameters


def score_diagnostics(
    corrected: Mapping[str, float],
    ablated: Mapping[str, float],
    p: Parameters,
) -> dict[str, str | float | bool]:
    """Quantify whether a nonzero Q term survives the float64 total.

    Report Decimal numbers as strings so JSON does not coerce them to float.
    """
    if not all(math.isfinite(v) for v in (*corrected.values(), *ablated.values())):
        raise ValueError("diagnostics require finite corrected/ablated telemetry")
    if not math.isfinite(p.reference_energy_j) or p.reference_energy_j <= 0:
        raise ValueError("invalid reference energy")
    if corrected["information_j"] == 0 or ablated["information_j"] != 0:
        raise ValueError("expected a nonzero information term and zero-term ablation")
    keys = ("kinetic_j", "gravity_j", "coupling_j", "information_j")
    with localcontext() as ctx:
        ctx.prec = 110
        denominator = Decimal(str(p.reference_energy_j))
        cc = sum((Decimal(str(corrected[k])) for k in keys), Decimal(0)) / denominator
        aa = sum((Decimal(str(ablated[k])) for k in keys), Decimal(0)) / denominator
        difference = cc - aa
        information_effect = Decimal(str(corrected["information_j"])) / denominator
        # Use the actual final-score ulp, rather than conflating J and score units.
        half_ulp_j = Decimal(str(math.ulp(ablated["score"]))) * denominator / 2
        ratio = abs(Decimal(str(corrected["information_j"]))) / half_ulp_j
        # The estimate presumes term linearity in eta at the frozen inputs and
        # a locally unchanged ULP. It is not a recommended coefficient fit.
        eta_threshold = half_ulp_j / abs(Decimal(str(corrected["information_j"])))
        return {
            "binary64_score_equal": corrected["score"] == ablated["score"],
            "information_j": corrected["information_j"],
            "binary64_half_ulp_j": float(half_ulp_j),
            "info_to_half_ulp": str(ratio),
            "decimal_resummed_corrected": str(cc),
            "decimal_resummed_ablated": str(aa),
            "decimal_resummed_delta": str(difference),
            "information_delta_from_float_terms": str(information_effect),
            "eta_for_half_ulp_estimate": str(eta_threshold),
            "precision_scope": "decimal re-summation of pre-rounded float64 terms only",
        }
