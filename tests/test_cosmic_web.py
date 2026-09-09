from __future__ import annotations

import json

import pytest

from beastbox.cosmic_entry import main as cosmic_main
from beastbox.cosmic_web import CosmicApp, ProviderProfile, render_cosmic_ui, validate_bind_host


def test_cosmic_app_swaps_reference_brain_without_swapping_substrate(tmp_path):
    app = CosmicApp(tmp_path)
    first = app.dispatch(
        "POST",
        "/api/chat",
        {"text": "remember the sky code is marigold", "provider": {"kind": "reference", "model": "Brain A"}},
    )
    second = app.dispatch(
        "POST",
        "/api/chat",
        {"text": "what is the sky code?", "provider": {"kind": "reference", "model": "Brain B"}},
    )

    assert first[0] == second[0] == 200
    assert first[1]["runtime"]["system_id"] == second[1]["runtime"]["system_id"]
    assert second[1]["result"]["model"]["model"] == "Brain B"
    assert "marigold" in second[1]["result"]["model"]["prompt"]
    assert second[1]["brain_changed"] is True
    assert second[1]["substrate_preserved"] is True


def test_remote_provider_requires_cloud_authority_and_profiles_never_contain_key_values(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUD_KEY_ENV", "CLOUD_KEY_SENTINEL_NEVER_PERSIST_12345")
    app = CosmicApp(tmp_path)
    profile = {
        "kind": "compatible",
        "model": "remote-model",
        "base_url": "https://models.example.test/v1",
        "allow_remote": True,
        "api_key_env": "CLOUD_KEY_ENV",
    }

    denied = app.dispatch("POST", "/api/provider", profile)
    assert denied == (403, {"error": "cloud authority required"})
    assert app.dispatch("POST", "/api/authority", {"action": "grant", "name": "cloud"})[0] == 200
    saved = app.dispatch("POST", "/api/provider", profile)
    assert saved[0] == 200
    encoded = json.dumps(saved[1], sort_keys=True)
    assert "CLOUD_KEY_SENTINEL_NEVER_PERSIST_12345" not in encoded
    settings = (tmp_path / "cosmic-provider.json").read_text(encoding="utf-8")
    assert "CLOUD_KEY_SENTINEL_NEVER_PERSIST_12345" not in settings
    assert "CLOUD_KEY_ENV" in settings


def test_sensor_events_require_matching_live_authority_and_master_stop_revokes(tmp_path):
    app = CosmicApp(tmp_path)
    event = {"schema": "sensor-event-v1", "source": "software-event", "text": "mic rms 0.2", "features": [0.2]}

    denied = app.dispatch("POST", "/api/event", {"modality": "microphone", "event": event})
    assert denied[0] == 403
    app.dispatch("POST", "/api/authority", {"action": "grant", "name": "microphone"})
    accepted = app.dispatch("POST", "/api/event", {"modality": "microphone", "event": event})
    assert accepted[0] == 200
    stopped = app.dispatch("POST", "/api/authority", {"action": "master_stop"})
    assert stopped[1]["authority"]["microphone"] is False
    assert app.dispatch("POST", "/api/event", {"modality": "microphone", "event": event})[0] == 403


def test_qbay_live_submission_is_default_denied(tmp_path):
    app = CosmicApp(tmp_path)
    status, body = app.dispatch("POST", "/api/quantum", {"provider": "ibm", "shots": 16})
    assert status == 403
    assert body == {"error": "quantum live authority required"}


def test_provider_profile_validates_kind_model_and_secret_reference():
    profile = ProviderProfile.from_dict({"kind": "ollama", "model": "qwen", "base_url": "http://127.0.0.1:11434"})
    assert profile.kind == "ollama"
    with pytest.raises(ValueError):
        ProviderProfile.from_dict({"kind": "compatible", "model": "", "base_url": "http://127.0.0.1:1234/v1"})
    with pytest.raises(ValueError):
        ProviderProfile.from_dict({"kind": "compatible", "model": "m", "api_key_env": "BAD-NAME"})


def test_bind_is_loopback_only():
    assert validate_bind_host("127.0.0.1") == "127.0.0.1"
    assert validate_bind_host("localhost") == "localhost"
    with pytest.raises(ValueError, match="loopback"):
        validate_bind_host("0.0.0.0")


def test_cosmic_ui_has_real_browser_privacy_controls_and_progressive_surfaces():
    html = render_cosmic_ui()
    for label in (
        "ORBIT",
        "BRAIN",
        "BRAIN BAY",
        "VISION",
        "LISTEN",
        "VOICE",
        "REALITY",
        "MEMORY VAULT",
        "SYNAPSE TRACE",
        "FILES",
        "WORKSPACE",
        "Q-BAY",
        "CONNECTIONS",
        "AUTHORITY",
        "SETTINGS",
    ):
        assert label in html
    assert "navigator.mediaDevices.getUserMedia" in html
    assert "speechSynthesis" in html
    assert "MASTER PRIVACY" in html
    assert "prefers-reduced-motion" in html
    assert "BRAIN CHANGED" in html
    assert "SUBSTRATE PRESERVED" in html
    assert "camera-derived features are not vision understanding" in html.lower()


def test_cosmic_headless_smoke_initializes_real_durable_state(tmp_path, capsys):
    assert cosmic_main(["--smoke", "--data-dir", str(tmp_path)]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["schema"] == "cosmic-ui-smoke-v1"
    assert receipt["valid"] is True
    assert receipt["turn"] == 0
    assert receipt["authority_grants"] == 0
    assert len(receipt["checkpoint_sha256"]) == 64


def test_healthz_is_minimal_and_never_exposes_runtime_state(tmp_path):
    app = CosmicApp(tmp_path)
    status, body = app.dispatch("GET", "/healthz")

    assert status == 200
    assert body == {"schema": "beastbox-health-v1", "status": "alive"}
    encoded = json.dumps(body, sort_keys=True).lower()
    assert "memory" not in encoded
    assert "authority" not in encoded
    assert "token" not in encoded


def test_readyz_proves_durable_runtime_without_exposing_memory_contents(tmp_path):
    app = CosmicApp(tmp_path)
    status, body = app.dispatch("GET", "/readyz")

    assert status == 200
    assert body["schema"] == "beastbox-readiness-v1"
    assert body["ready"] is True
    assert body["runtime_valid"] is True
    assert body["provider_kind"] == "reference"
    assert len(body["system_id"]) >= 8
    assert len(body["checkpoint_sha256"]) == 64
    encoded = json.dumps(body, sort_keys=True).lower()
    assert "prompt" not in encoded
    assert "memory_records" not in encoded
    assert "credential" not in encoded
