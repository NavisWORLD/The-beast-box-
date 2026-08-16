import math

import pytest


def test_feature_order_is_frozen():
    from beastbox.descendant.quantum_conditioning import FEATURE_ORDER

    assert FEATURE_ORDER == (
        "normalized_entropy",
        "bit_one_fraction",
        "bit_balance_distance",
        "mean_longest_run",
        "adjacent_bit_agreement",
        "unique_outcomes",
        "shannon_entropy_bits",
    )


def test_normalize_feature_vector_is_finite_and_deterministic():
    from beastbox.descendant.quantum_conditioning import normalize_feature_vector

    raw = (0.9, 0.51, 0.01, 2.5, 0.49, 32.0, 4.5)
    first = normalize_feature_vector(raw)
    second = normalize_feature_vector(raw)
    assert first == second
    assert len(first) == 7
    assert all(math.isfinite(x) for x in first)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_normalize_feature_vector_rejects_nonfinite(bad):
    from beastbox.descendant.quantum_conditioning import normalize_feature_vector

    values = [0.0] * 7
    values[3] = bad
    with pytest.raises(ValueError, match="finite"):
        normalize_feature_vector(values)


def test_feature_vector_uses_named_packet_features():
    from beastbox.descendant.quantum_conditioning import feature_vector

    class Packet:
        features = {
            "shannon_entropy_bits": 4.5,
            "normalized_entropy": 0.9,
            "bit_one_fraction": 0.51,
            "bit_balance_distance": 0.01,
            "mean_longest_run": 2.5,
            "adjacent_bit_agreement": 0.49,
            "unique_outcomes": 32.0,
        }

    assert feature_vector(Packet()) == (0.9, 0.51, 0.01, 2.5, 0.49, 32.0, 4.5)


def test_torch_adapter_is_exact_zero_at_initialization():
    torch = pytest.importorskip("torch")
    from beastbox.descendant.quantum_conditioning import Quantum54Adapter

    adapter = Quantum54Adapter()
    x = torch.tensor([[0.1, -0.2, 0.3, 0.4, 0.5, 0.6, -0.7]], dtype=torch.float32)
    y = adapter(x)
    assert tuple(y.shape) == (1, 54)
    assert torch.count_nonzero(y).item() == 0
    assert torch.count_nonzero(adapter.linear.weight).item() == 0
    assert torch.count_nonzero(adapter.linear.bias).item() == 0


def test_geometry_scale_is_exact_identity_at_zero_init():
    torch = pytest.importorskip("torch")
    from beastbox.descendant.quantum_conditioning import Quantum54Adapter

    adapter = Quantum54Adapter()
    f = torch.tensor([[0.9, 0.51, 0.01, 2.5, 0.49, 32.0, 4.5]], dtype=torch.float32)
    scale = adapter.geometry_scale(f, alpha=0.25)
    assert tuple(scale.shape) == (1, 54)
    assert torch.equal(scale, torch.ones_like(scale))


def test_nonzero_adapter_changes_pairwise_geometry():
    torch = pytest.importorskip("torch")
    from beastbox.descendant.quantum_conditioning import Quantum54Adapter, apply_geometry_scale

    adapter = Quantum54Adapter()
    with torch.no_grad():
        adapter.linear.weight[0, 0] = 1.0
    f = torch.tensor([[0.9, 0.51, 0.01, 2.5, 0.49, 32.0, 4.5]], dtype=torch.float32)
    x54 = torch.randn(1, 4, 54, generator=torch.Generator().manual_seed(7))
    before = torch.cdist(x54, x54) ** 2
    after_x = apply_geometry_scale(x54, adapter.geometry_scale(f, alpha=0.25))
    after = torch.cdist(after_x, after_x) ** 2
    assert not torch.equal(before, after)


def test_geometry_scale_rejects_unbounded_alpha():
    torch = pytest.importorskip("torch")
    from beastbox.descendant.quantum_conditioning import Quantum54Adapter

    adapter = Quantum54Adapter()
    f = torch.zeros((1, 7), dtype=torch.float32)
    with pytest.raises(ValueError, match="alpha"):
        adapter.geometry_scale(f, alpha=1.1)
