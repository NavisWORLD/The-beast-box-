"""Authenticated Buddy research endpoint; trained synthetic fixture, no QPU."""
import pytest
import torch
from fastapi.testclient import TestClient


@pytest.fixture
def trained(tmp_path):
    from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
    from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
    from rawrphos.training.checkpoint import save_checkpoint, rng_state

    tokenizer = RawrphosTokenizer.train(
        ["The little cat sat on a warm mat."] * 10, 300,
    )
    torch.manual_seed(8)
    model = RawrphosLM(RawrphosConfig(
        vocab_size=tokenizer.vocab_size, d_model=32,
        n_heads=4, n_layers=2, max_seq_len=128,
    ))
    ids = torch.tensor([tokenizer.encode("The little cat sat on a warm mat.")])
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
    loss = model(ids[:, :-1], targets=ids[:, 1:])["loss"]
    loss.backward()
    optimizer.step()
    folder = tmp_path / "trained"
    save_checkpoint(
        folder, model, tokenizer, {
            "training_steps": 1,
            "training_tokens": ids.shape[1] - 1,
            "training_seq_len": ids.shape[1] - 1,
            "release_status": "test-fixture-trained",
            "hardware": {"device": "cpu"},
        }, {"rng": rng_state()},
    )
    return folder


def test_shadow_api_is_authenticated_bounded_and_weight_frozen(trained):
    from rawrphos.inference.server import create_app

    app = create_app(trained, "owner-" + "X" * 40, max_new_tokens=16)
    client = TestClient(app)
    auth = {"Authorization": "Bearer owner-" + "X" * 40}
    request = {
        "model": "rawrphos-native",
        "prompt": "The cat",
        "control_vector": [0.2, -0.2] * 6,
        "qstate_metric12": [1.0, -1.0] * 6,
        "max_tokens": 4,
        "seed": 67,
    }

    assert client.post("/v1/quantum-buddy-shadow", json=request).status_code == 401
    before = client.get("/model/info", headers=auth).json()["checkpoint_sha256"]
    response = client.post("/v1/quantum-buddy-shadow", headers=auth, json=request)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["checkpoint_sha256"] == before
    assert result["model_weights_changed"] is False
    assert result["quantum_advantage_proven"] is False
    assert isinstance(result["response_ordinary"], str)
    assert isinstance(result["response_buddy"], str)
    assert result["logit_l2"] >= 0.0
    assert len(result["gate_by_layer"]) == 2
    assert len(result["sigma_by_layer"]) == 2
    assert client.get("/model/info", headers=auth).json()["checkpoint_sha256"] == before

    for changes in (
        {"qstate_metric12": [1.1] * 12},
        {"qstate_metric12": [False] * 12},
        {"control_vector": [0.1] * 11},
        {"max_tokens": 1000},
        {"unexpected": "tools"},
    ):
        bad = {**request, **changes}
        assert client.post("/v1/quantum-buddy-shadow", headers=auth, json=bad).status_code == 400

    # Ordinary chat must not accept state fields or invoke Buddy functionality.
    ordinary = {
        "model": "rawrphos-native",
        "messages": [{"role": "user", "content": "The cat"}],
        "temperature": 0, "max_tokens": 2, "seed": 67,
    }
    assert client.post("/v1/chat/completions", headers=auth, json=ordinary).status_code == 200
    assert client.post(
        "/v1/chat/completions", headers=auth,
        json={**ordinary, "qstate_metric12": request["qstate_metric12"]},
    ).status_code == 400


def test_busy_model_does_not_fallback_to_another_provider(trained):
    from rawrphos.inference.server import create_app
    app = create_app(trained, "owner-" + "X" * 40, max_new_tokens=16)
    client = TestClient(app)
    auth = {"Authorization": "Bearer owner-" + "X" * 40}
    request = {
        "model": "rawrphos-native",
        "prompt": "The cat",
        "control_vector": [0.1] * 12,
        "qstate_metric12": [0.2] * 12,
        "max_tokens": 2,
        "seed": 67,
    }
    acquired = app.state.engine.lock.acquire(blocking=False)
    assert acquired
    try:
        result = client.post("/v1/quantum-buddy-shadow", headers=auth, json=request)
    finally:
        app.state.engine.lock.release()
    assert result.status_code == 429
    assert "fallback" not in result.text.lower()
