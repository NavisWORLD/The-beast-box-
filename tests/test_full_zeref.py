from dataclasses import dataclass

from beastbox.full_zeref import NativeTrinityTextProvider, state_from_entropy12


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

    def score(self, prompt, state, *, enabled):
        self.calls += 1
        # The injected selector below avoids any torch dependency in this unit test.
        return {"step": self.calls, "prompt": prompt}, FakeTelemetry()


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
    assert state.feedback12 != before
    assert state.step >= 3
    assert provider.last_telemetry["native_enabled"] is True
    assert provider.last_telemetry["geometry_modulation_norm"] > 0
    assert provider.last_telemetry["generated_tokens"] == 2


def test_zero_entropy_state_preserves_exact_12_42_54_shapes():
    state = state_from_entropy12([0.0] * 12)
    assert len(state.external12) == 12
    assert len(state.external42) == 42
    assert len(state.external54) == 54
    assert state.external54 == state.external12 + state.external42
    assert "54_block_balance" in state.projection_hashes
