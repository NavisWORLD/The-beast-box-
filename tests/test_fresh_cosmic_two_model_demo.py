from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "demo" / "fresh_cosmic_conversation.py"


def _load_demo_module():
    spec = importlib.util.spec_from_file_location("fresh_cosmic_conversation", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_choose_two_distinct_models_prefers_two_different_available_brains() -> None:
    demo = _load_demo_module()
    ids = [
        "aphrodite/TheDrummer/Behemoth-X-123B-v2.1",
        "aphrodite/TheDrummer/Skyfall-31B-v4.2",
        "other/model-24B",
    ]

    first, second = demo.choose_two_distinct_models(ids)

    assert first != second
    assert first in ids
    assert second in ids
    assert "Behemoth" in first
    assert "Skyfall" in second


def test_choose_two_distinct_models_rejects_single_model_catalog() -> None:
    demo = _load_demo_module()

    try:
        demo.choose_two_distinct_models(["only/model"])
    except RuntimeError as exc:
        assert "two distinct" in str(exc).lower()
    else:
        raise AssertionError("expected a two-model requirement failure")
