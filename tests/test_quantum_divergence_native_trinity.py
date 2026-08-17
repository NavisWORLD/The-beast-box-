from __future__ import annotations

import math
import threading

import pytest

torch = pytest.importorskip("torch")
from torch import nn
import torch.nn.functional as F

from beastbox.quantum_divergence.native_trinity import NativeTrinityAdapter
from beastbox.quantum_divergence.trinity_state import (
    SensorFixture,
    TrinityConfig,
    compose_trinity_state,
)


class _FakeAttention(nn.Module):
    def __init__(self, embd: int = 8, heads: int = 2):
        super().__init__()
        self.nh = heads
        self.hd = embd // heads
        self.qkv = nn.Linear(embd, 3 * embd)
        self.proj = nn.Linear(embd, embd)
        self.drop = nn.Identity()
        self.w54 = nn.Linear(embd, 54, bias=False)
        self.log_sigma = nn.Parameter(torch.tensor(math.log(1.4)))
        self.gate = nn.Parameter(torch.tensor([0.25]))
        self.use_cst = True
        self.last_gate = 0.0

    def forward(self, x, mask):
        B, T, C = x.shape
        q, k, v = self.qkv(x).split(C, dim=2)
        sh = lambda t: t.view(B, T, self.nh, self.hd).transpose(1, 2)
        q, k, v = sh(q), sh(k), sh(v)
        a = F.softmax((q @ k.transpose(-2, -1)) / math.sqrt(self.hd) + mask[:T, :T], dim=-1)
        if self.use_cst:
            x54 = self.w54(x)
            d2 = torch.cdist(x54, x54, p=2.0) ** 2
            sig = torch.exp(self.log_sigma).clamp(0.05, 50.0)
            H = torch.exp(-d2 / (2 * sig * sig))
            H = H.masked_fill(mask[:T, :T] < 0, 0.0)
            H = H / H.sum(-1, keepdim=True).clamp_min(1e-9)
            raw = self.gate
            g = raw + (raw.clamp(0.01, 1.0) - raw).detach()
            a = (1 - g) * a + g * H.unsqueeze(1)
            self.last_gate = float(g.detach())
        y = (self.drop(a) @ v).transpose(1, 2).contiguous().view(B, T, C)
        return self.proj(y)


class _FakeBlock(nn.Module):
    def __init__(self, embd: int = 8):
        super().__init__()
        self.ln1 = nn.LayerNorm(embd)
        self.attn = _FakeAttention(embd=embd)
        self.ln2 = nn.LayerNorm(embd)
        self.mlp = nn.Sequential(nn.Linear(embd, 16), nn.GELU(), nn.Linear(16, embd))

    def forward(self, x, mask):
        x = x + self.attn(self.ln1(x), mask)
        return x + self.mlp(self.ln2(x))


class _FakeNet(nn.Module):
    def __init__(self, vocab: int = 16, embd: int = 8, block: int = 32):
        super().__init__()
        self.tok = nn.Embedding(vocab, embd)
        self.pos = nn.Embedding(block, embd)
        self.blocks = nn.ModuleList([_FakeBlock(embd), _FakeBlock(embd)])
        self.lnf = nn.LayerNorm(embd)
        self.head = nn.Linear(embd, vocab, bias=False)
        self.register_buffer("mask", torch.triu(torch.full((block, block), float("-inf")), 1))

    def forward(self, idx):
        T = idx.size(1)
        x = self.tok(idx) + self.pos(torch.arange(T, device=idx.device))
        for block in self.blocks:
            x = block(x, self.mask)
        return self.head(self.lnf(x))


class _FakeNative:
    def __init__(self):
        torch.manual_seed(4)
        self.stoi = {str(i): i for i in range(10)}
        self.stoi.update({"a": 10, "b": 11, "c": 12, " ": 13, ":": 14, "\n": 15})
        self.itos = {v: k for k, v in self.stoi.items()}
        self.block = 32
        self.m = _FakeNet(vocab=len(self.stoi), block=self.block)
        self.m.eval()
        self.lock = threading.Lock()

    def encode(self, text: str):
        return [self.stoi[c] for c in text if c in self.stoi]

    def _logits(self, idx):
        return self.m(idx)


def _state(entropy, include_sensors=True):
    return compose_trinity_state(
        sensor_fixture=SensorFixture.fixed(seed=31, captured_at=100.0),
        entropy12=entropy,
        include_sensors=include_sensors,
        config=TrinityConfig(),
        now=100.0,
    )


def test_disabled_adapter_is_identity():
    native = _FakeNative()
    adapter = NativeTrinityAdapter(native)
    prompt = "abc 0123"
    idx = torch.tensor([native.encode(prompt)], dtype=torch.long)
    with torch.no_grad(), native.lock:
        baseline = native._logits(idx[:, -native.block:]).detach().clone()
    got, telemetry = adapter.score(prompt, _state([0.0] * 12, include_sensors=False), enabled=False)
    torch.testing.assert_close(got, baseline, atol=1e-6, rtol=1e-5)
    assert telemetry.enabled is False
    assert adapter.hooks_remaining == 0


def test_zero_external_state_is_identity_even_when_enabled():
    native = _FakeNative()
    adapter = NativeTrinityAdapter(native)
    prompt = "abc 0123"
    idx = torch.tensor([native.encode(prompt)], dtype=torch.long)
    with torch.no_grad(), native.lock:
        baseline = native._logits(idx[:, -native.block:]).detach().clone()
    got, telemetry = adapter.score(prompt, _state([0.0] * 12, include_sensors=False), enabled=True)
    torch.testing.assert_close(got, baseline, atol=1e-6, rtol=1e-5)
    assert telemetry.zero_state_identity is True
    assert adapter.hooks_remaining == 0


def test_nonzero_state_moves_all_three_injection_channels_and_logits():
    native = _FakeNative()
    adapter = NativeTrinityAdapter(native)
    prompt = "abc 0123"
    idx = torch.tensor([native.encode(prompt)], dtype=torch.long)
    with torch.no_grad(), native.lock:
        baseline = native._logits(idx[:, -native.block:]).detach().clone()
    got, telemetry = adapter.score(
        prompt,
        _state([0.25, -0.2, 0.15, -0.1, 0.05, 0.3, -0.25, 0.2, -0.15, 0.1, -0.05, 0.18]),
        enabled=True,
    )
    assert not torch.allclose(got, baseline)
    assert telemetry.enabled is True
    assert telemetry.hidden_modulation_norm > 0.0
    assert telemetry.geometry_modulation_norm > 0.0
    assert telemetry.affinity_divergence is not None and telemetry.affinity_divergence > 0.0
    assert telemetry.gate_before is not None
    assert telemetry.gate_after is not None
    assert telemetry.sigma_before is not None
    assert telemetry.sigma_after is not None
    assert telemetry.gate_after != telemetry.gate_before or telemetry.sigma_after != telemetry.sigma_before
    assert len(telemetry.internal12_summary) == 12
    assert adapter.hooks_remaining == 0


def test_candidate_digit_distribution_is_complete_and_normalized():
    native = _FakeNative()
    adapter = NativeTrinityAdapter(native)
    result = adapter.score_candidate_digits(
        "abc 0123",
        _state([0.1] * 12),
        enabled=True,
    )
    assert set(result.logits) == set("0123456789")
    assert set(result.probabilities) == set("0123456789")
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-6
    assert result.selected_digit in "0123456789"
