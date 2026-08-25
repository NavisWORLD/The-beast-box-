from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any, Mapping, Sequence

from beastbox.cst12_physics_probe_003 import ARM_ORDER, circular_mean, wrap_phase

MIRROR_ARM = "MIRROR_CAL"
CALIBRATION_METHOD = "leave-one-out-circular-mean-by-layout"


def apply_crossfit_harmonic_calibration(
    blocks: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Apply a held-out circular mirror phase calibration within each layout.

    For block b, the calibration phase is the circular mean of MIRROR_CAL
    residuals from every *other* block in the same physical layout.  The block's
    own mirror observation is never used to calibrate itself.  The same phase
    offset is subtracted from every arm in the block, so relative scientific
    contrasts are invariant by construction.
    """
    if not blocks:
        raise ValueError("harmonic calibration requires blocks")

    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for block in blocks:
        layout = str(block.get("layout_key", ""))
        if not layout:
            raise ValueError("harmonic calibration requires layout_key")
        epsilon = block.get("epsilon")
        if not isinstance(epsilon, Mapping) or MIRROR_ARM not in epsilon:
            raise ValueError("harmonic calibration requires MIRROR_CAL residuals")
        missing = set(ARM_ORDER) - set(epsilon)
        if missing:
            raise ValueError(f"harmonic calibration block missing arms: {sorted(missing)}")
        grouped[layout].append(block)

    for layout, rows in grouped.items():
        if len(rows) < 2:
            raise ValueError(f"layout {layout} requires at least two mirror blocks for cross-fit calibration")

    out: list[dict[str, Any]] = []
    for block in blocks:
        layout = str(block["layout_key"])
        block_id = int(block["block_id"])
        refs = [
            float(other["epsilon"][MIRROR_ARM])
            for other in grouped[layout]
            if int(other["block_id"]) != block_id
        ]
        if not refs:
            raise ValueError(f"layout {layout} has no held-out mirror references")
        bias = circular_mean(refs)
        epsilon = block["epsilon"]
        epsilon_calibrated = {
            arm: wrap_phase(float(epsilon[arm]) - bias)
            for arm in ARM_ORDER
        }
        row = dict(block)
        row["harmonic_calibration_method"] = CALIBRATION_METHOD
        row["harmonic_reference_count"] = len(refs)
        row["harmonic_bias"] = bias
        row["mirror_holdout_epsilon"] = epsilon_calibrated[MIRROR_ARM]
        row["epsilon_calibrated"] = epsilon_calibrated
        out.append(row)
    return out


def harmonic_holdout_metric(calibrated_blocks: Sequence[Mapping[str, Any]]) -> float:
    if not calibrated_blocks:
        raise ValueError("harmonic holdout metric requires calibrated blocks")
    values = [abs(float(block["mirror_holdout_epsilon"])) for block in calibrated_blocks]
    return float(statistics.median(values))
