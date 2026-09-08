from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "demo" / "fresh_cosmic_conversation.py"


def _load_demo_module():
    # The unit under test is pure model-selection logic. CI's normal quality
    # environment intentionally does not install Playwright, so provide only the
    # two import names needed to load the demo module without exercising browser code.
    playwright = types.ModuleType("playwright")
    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.expect = lambda *args, **kwargs: None
    sync_api.sync_playwright = lambda *args, **kwargs: None
    playwright.sync_api = sync_api
    sys.modules["playwright"] = playwright
    sys.modules["playwright.sync_api"] = sync_api

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
