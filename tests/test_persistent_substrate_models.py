from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")
from torch import nn

from beastbox.persistent_substrate.models import (
    TransformersNLLAdapter,
    ZerefNLLAdapter,
    assert_frozen_model,
    parameter_sha256,
)


class TinyCausalLM(nn.Module):
    def __init__(self, vocab_size: int = 16, width: int = 8) -> None:
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, width)
        self.head = nn.Linear(width, vocab_size, bias=False)

    def forward(self, input_ids):
        return SimpleNamespace(logits=self.head(self.embedding(input_ids)))


class TinyTokenizer:
    def __init__(self) -> None:
        alphabet = " abcdefghijklmnopqrstuvwxyz[]|:\n0123456789"
        self.stoi = {ch: index for index, ch in enumerate(alphabet)}
        self.name_or_path = "tiny-tokenizer-v1"
        self.bos_token_id = None
        self.eos_token_id = None

    def encode(self, text: str, *, add_special_tokens: bool = False):
        del add_special_tokens
        return [self.stoi[ch] for ch in text]


def _frozen(model: nn.Module) -> nn.Module:
    model.eval()
    model.requires_grad_(False)
    return model


def test_parameter_hash_changes_only_when_parameters_change() -> None:
    torch.manual_seed(11)
    model = _frozen(TinyCausalLM())
    first = parameter_sha256(model)
    second = parameter_sha256(model)
    assert first == second

    with torch.no_grad():
        next(model.parameters()).view(-1)[0].add_(1.0)
    assert parameter_sha256(model) != first


def test_zeref_adapter_scores_without_parameter_drift() -> None:
    torch.manual_seed(12)
    tokenizer = TinyTokenizer()
    model = _frozen(TinyCausalLM(vocab_size=len(tokenizer.stoi)))
    adapter = ZerefNLLAdapter(
        model=model,
        stoi=tokenizer.stoi,
        model_id="fixture-zeref",
        checkpoint_identity={"checkpoint_sha256": "a" * 64},
        block_size=128,
    )
    before = parameter_sha256(model)
    score = adapter.score("memory: amber cedar river\nanswer:", "amber cedar river")
    after = parameter_sha256(model)

    assert before == after
    assert score.candidate == "amber cedar river"
    assert math.isfinite(score.nll_nats)
    assert math.isfinite(score.normalized_nll)
    assert score.predicted_units == len("amber cedar river")
    assert score.unit_kind == "character"
    assert len(score.input_ids_sha256) == 64


def test_transformers_adapter_scores_without_parameter_drift() -> None:
    torch.manual_seed(13)
    tokenizer = TinyTokenizer()
    model = _frozen(TinyCausalLM(vocab_size=len(tokenizer.stoi)))
    adapter = TransformersNLLAdapter(
        model=model,
        tokenizer=tokenizer,
        model_id="fixture-transformer",
        checkpoint_identity={"revision": "b" * 40},
    )
    before = parameter_sha256(model)
    score = adapter.score("memory: silver orbit\nanswer:", "silver orbit")
    after = parameter_sha256(model)

    assert before == after
    assert score.candidate == "silver orbit"
    assert math.isfinite(score.nll_nats)
    assert math.isfinite(score.normalized_nll)
    assert score.predicted_units == len("silver orbit")
    assert score.unit_kind == "token"
    assert len(score.input_ids_sha256) == 64


def test_frozen_model_assertion_rejects_train_mode_or_grad_parameters() -> None:
    model = TinyCausalLM()
    with pytest.raises(RuntimeError, match="eval mode"):
        assert_frozen_model(model)

    model.eval()
    with pytest.raises(RuntimeError, match="requires_grad"):
        assert_frozen_model(model)

    model.requires_grad_(False)
    assert_frozen_model(model)


def test_zeref_adapter_rejects_unsupported_candidate_characters() -> None:
    tokenizer = TinyTokenizer()
    model = _frozen(TinyCausalLM(vocab_size=len(tokenizer.stoi)))
    adapter = ZerefNLLAdapter(
        model=model,
        stoi=tokenizer.stoi,
        model_id="fixture-zeref",
        checkpoint_identity={"checkpoint_sha256": "c" * 64},
        block_size=128,
    )
    with pytest.raises(ValueError, match="unsupported"):
        adapter.score("answer:", "snowman ☃")
