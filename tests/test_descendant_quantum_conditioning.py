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
