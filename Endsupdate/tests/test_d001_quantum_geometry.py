import math

import pytest


def test_public_geometry_api_exists_and_zero_projection_is_identity():
    from beastbox.descendant import quantum_conditioning as qc

    assert hasattr(qc, "geometry_scale")
    assert hasattr(qc, "apply_geometry_modulation")
    scale = qc.geometry_scale([0.0] * 54, alpha=0.25)
    assert scale == pytest.approx((1.0,) * 54, abs=0.0)


def test_geometry_scale_is_bounded():
    from beastbox.descendant import quantum_conditioning as qc

    scale = qc.geometry_scale([100.0, -100.0] + [0.0] * 52, alpha=0.25)
    assert all(math.isfinite(v) for v in scale)
    assert min(scale) >= 0.75
    assert max(scale) <= 1.25


def test_multiplicative_geometry_can_change_pairwise_distance_but_common_translation_cannot():
    from beastbox.descendant import quantum_conditioning as qc

    a = [1.0, 2.0] + [0.0] * 52
    b = [3.0, 6.0] + [0.0] * 52
    translation = [7.0, -4.0] + [0.0] * 52

    def dist2(x, y):
        return sum((u - v) ** 2 for u, v in zip(x, y, strict=True))

    original = dist2(a, b)
    translated = dist2(
        [x + q for x, q in zip(a, translation, strict=True)],
        [x + q for x, q in zip(b, translation, strict=True)],
    )
    assert translated == pytest.approx(original, abs=0.0)

    scale = qc.geometry_scale([2.0, -2.0] + [0.0] * 52, alpha=0.25)
    scaled = dist2(
        [x * s for x, s in zip(a, scale, strict=True)],
        [x * s for x, s in zip(b, scale, strict=True)],
    )
    assert scaled != pytest.approx(original)


def test_torch_geometry_modulation_is_exact_identity_at_zero_projection():
    torch = pytest.importorskip("torch")
    from beastbox.descendant import quantum_conditioning as qc

    x = torch.randn(2, 8, 54)
    projection = torch.zeros(2, 54)
    out = qc.apply_geometry_modulation(x, projection, alpha=0.25)
    assert torch.equal(out, x)
