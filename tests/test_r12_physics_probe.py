from __future__ import annotations

import importlib.util


def test_probe001_core_module_exists() -> None:
    """RED gate: production module must not exist until this test is observed failing."""
    assert importlib.util.find_spec("beastbox.r12_physics_probe") is not None
