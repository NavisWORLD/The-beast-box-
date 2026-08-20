from dataclasses import dataclass

from beastbox.full_zeref import (
    NativeTrinityTextProvider,
    handle_resident_request,
    projection_readiness,
    state_from_entropy12,
    subject_environment_safe,
)


@dataclass
class FakeTelemetry:
    enabled: bool = True
    zero_state_identity: bool = False
    hidden_modulation_norm: float = 0.01
    geometry_modulation_norm: float = 0.02
    gate_before: float | None = 0.1
    gate_after: float | None = 0.11
    sigma_before: float | None = 5.0
    sigma_after: float | None = 5.1
    affinity_divergence: float | None = 0.001
    logits_sha256: str = "a" * 64
    internal12_summary: list[float] = None
    layer_count: int = 2

    def __post_init__(self):
        if self.internal12_summary is None:
            self.internal12_summary = [0.2] * 12


class FakeNative:
    itos = {0: "A", 1: "\n"}


class FakeAdapter:
    def __init__(self):
        self.calls = 0
        self.enabled_values = []

    def score(self, prompt, state, *, enabled):
        self.calls += 1
        self.enabled_values.append(enabled)
        telemetry = FakeTelemetry(enabled=enabled)
        if not enabled:
            telemetry.hidden_modulation_norm = 0.0
            telemetry.geometry_modulation_norm = 0.0
            telemetry.affinity_divergence = 0.0
            telemetry.internal12_summary = [0.0] * 12
        return {"step": self.calls, "prompt": prompt}, telemetry


class FakeResidentRuntime:
    def doctor(self):
        return {"ok": True, "state_step": 7}

    def respond(self, text, *, system_prompt=None):
        return {"response": f"echo:{text}", "system_prompt": system_prompt}


def test_native_text_provider_generates_and_advances_feedback_state():
    state = state_from_entropy12([0.25] * 12)
    before = list(state.feedback12)
    adapter = FakeAdapter()
    chosen = iter([0, 1])
    provider = NativeTrinityTextProvider(
        FakeNative(),
        state,
        adapter=adapter,
        max_new_tokens=8,
        token_selector=lambda _logits: next(chosen),
    )

    text = provider.generate("hello")

    assert text == "A\n"
    assert adapter.calls == 2
    assert adapter.enabled_values == [True, True]
    assert state.feedback12 != before
    assert state.step >= 3
    assert provider.last_telemetry["native_enabled"] is True
    assert provider.last_telemetry["geometry_modulation_norm"] > 0
    assert provider.last_telemetry["generated_tokens"] == 2


def test_native_disabled_provider_does_not_feed_back_state():
    state = state_from_entropy12([0.25] * 12)
    before_feedback = list(state.feedback12)
    before_step = state.step
    adapter = FakeAdapter()
    chosen = iter([0, 1])
    provider = NativeTrinityTextProvider(
        FakeNative(),
        state,
        adapter=adapter,
        enabled=False,
        max_new_tokens=8,
        token_selector=lambda _logits: next(chosen),
    )

    assert provider.generate("hello") == "A\n"
    assert adapter.enabled_values == [False, False]
    assert state.feedback12 == before_feedback
    assert state.step == before_step
    assert provider.last_telemetry["native_enabled"] is False
    assert provider.last_telemetry["geometry_modulation_norm"] == 0.0


def test_zero_entropy_state_preserves_exact_12_42_54_shapes():
    state = state_from_entropy12([0.0] * 12)
    assert len(state.external12) == 12
    assert len(state.external42) == 42
    assert len(state.external54) == 54
    assert state.external54 == state.external12 + state.external42
    assert "54_block_balance" in state.projection_hashes


def test_subject_environment_rejects_ibm_token_presence():
    assert subject_environment_safe({"PATH": "/usr/bin"}) is True
    assert subject_environment_safe({"IBM_QUANTUM_TOKEN": "masked-value"}) is False


def test_projection_readiness_requires_balanced_state_and_native_hashes():
    state_hashes = {
        "sensor_to_12_seed": "a" * 64,
        "12_to_42": "b" * 64,
        "54_block_balance": "c" * 64,
    }
    native_hashes = {"native_trinity": "d" * 64}
    assert projection_readiness(state_hashes, native_hashes) is True
    assert projection_readiness({"12_to_42": "b" * 64}, native_hashes) is False
    assert projection_readiness(state_hashes, {}) is False


def test_resident_request_protocol_keeps_one_runtime_for_chat_and_doctor():
    runtime = FakeResidentRuntime()
    assert handle_resident_request(runtime, {"op": "doctor"}) == {"ok": True, "state_step": 7}
    out = handle_resident_request(runtime, {"op": "chat", "text": "hello", "system_prompt": "local"})
    assert out["response"] == "echo:hello"
    assert out["system_prompt"] == "local"


def test_resident_request_protocol_rejects_unknown_operation():
    runtime = FakeResidentRuntime()
    try:
        handle_resident_request(runtime, {"op": "root-shell"})
    except ValueError as exc:
        assert "unsupported resident operation" in str(exc)
    else:
        raise AssertionError("unknown operation must fail closed")
