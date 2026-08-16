import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def load_runner():
    path = Path("scripts/run_d001_quantum_geometry.py")
    spec = importlib.util.spec_from_file_location("d001_quantum_geometry_runner", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cycle_indices_cycles_deterministically():
    mod = load_runner()
    assert mod.cycle_indices(5, 3) == [0, 1, 2, 0, 1]
    assert mod.cycle_indices(0, 3) == []
    with pytest.raises(ValueError, match="items"):
        mod.cycle_indices(1, 0)


def test_canonical_hash_is_order_independent_for_json_metadata():
    mod = load_runner()
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert mod.canonical_hash(a) == mod.canonical_hash(b)
    assert mod.canonical_hash(a) == hashlib.sha256(json.dumps(a, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def test_state_digest_changes_if_tensor_changes():
    torch = pytest.importorskip("torch")
    mod = load_runner()
    state = {"x": torch.tensor([1.0]), "y": torch.tensor([[2.0, 3.0]])}
    first = mod.state_digest(state)
    state["x"][0] = 2.0
    assert mod.state_digest(state) != first


def test_state_digest_is_key_order_independent():
    torch = pytest.importorskip("torch")
    mod = load_runner()
    x = torch.tensor([1.0])
    y = torch.tensor([2.0])
    assert mod.state_digest({"x": x, "y": y}) == mod.state_digest({"y": y, "x": x})
