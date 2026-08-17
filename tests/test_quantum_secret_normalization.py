from __future__ import annotations

from beastbox import quantum


def test_service_strips_secret_whitespace(monkeypatch):
    captured = {}

    class FakeService:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setenv("IBM_QUANTUM_TOKEN", "  secret-value\n")
    monkeypatch.setenv("IBM_QUANTUM_INSTANCE", "  crn:test  \n")
    monkeypatch.setattr(
        quantum,
        "_imports",
        lambda: (object, object, object, FakeService, object),
    )

    quantum._service()

    assert captured["token"] == "secret-value"
    assert captured["instance"] == "crn:test"
