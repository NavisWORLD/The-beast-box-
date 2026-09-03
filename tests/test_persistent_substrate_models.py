from __future__ import annotations

from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")

from beastbox.persistent_substrate.models import (
    TransformersNLLAdapter,
    ZerefNLLAdapter,
    parameter_sha256,
)


class TinyCharLM(torch.nn.Module):
    def __init__(self, vocab_size: int = 3) -> None:
        super().__init__()
        self.embedding = torch.nn.Embedding(vocab_size, 8)
        self.head = torch.nn.Linear(8, vocab_size, bias=False)

    def forward(self, idx, targets=None):
        del targets
        logits = self.head(self.embedding(idx))
        return logits, None


class TinyTokenizer:
    def __init__(self) -> None:
        self.vocab = {"a": 0, "b": 1, "c": 2}
        self.name_or_path = "tiny-tokenizer"

    def encode(self, text: str, *, add_special_tokens: bool = False):
        assert add_special_tokens is False
        return [self.vocab[ch] for ch in text]


class TinyTransformersLM(torch.nn.Module):
    def __init__(self, vocab_size: int = 3) -> None:
        super().__init__()
        self.embedding = torch.nn.Embedding(vocab_size, 8)
        self.head = torch.nn.Linear(8, vocab_size, bias=False)

    def forward(self, input_ids):
        logits = self.head(self.embedding(input_ids))
        return SimpleNamespace(logits=logits)


def _assert_frozen_score(adapter, model) -> None:
    before = parameter_sha256(model)
    assert model.training is False
    assert all(parameter.grad is None for parameter in model.parameters())

    score = adapter.score(prompt="ab", continuation="ca")

    after = parameter_sha256(model)
    assert before == after
    assert score.candidate == "ca"
    assert score.predicted_units == 2
    assert score.nll_nats >= 0.0
    assert score.normalized_nll >= 0.0
    assert torch.isfinite(torch.tensor(score.nll_nats))
    assert torch.isfinite(torch.tensor(score.normalized_nll))
    assert len(score.input_ids_sha256) == 64
    assert adapter.checkpoint_identity
    assert all(parameter.grad is None for parameter in model.parameters())


def test_zeref_adapter_scores_candidates_without_parameter_drift():
    torch.manual_seed(7)
    model = TinyCharLM()
    adapter = ZerefNLLAdapter(
        model=model,
        stoi={"a": 0, "b": 1, "c": 2},
        checkpoint_identity={
            "model_id": "zeref-fixture",
            "checkpoint_sha256": "1" * 64,
        },
        model_id="zeref-fixture",
    )
    _assert_frozen_score(adapter, model)
    assert adapter.score(prompt="ab", continuation="ca").unit_kind == "character"


def test_smol_adapter_scores_candidates_without_parameter_drift():
    torch.manual_seed(11)
    model = TinyTransformersLM()
    adapter = TransformersNLLAdapter(
        model=model,
        tokenizer=TinyTokenizer(),
        checkpoint_identity={
            "model_id": "smol-fixture",
            "revision": "2" * 40,
        },
        model_id="smol-fixture",
    )
    _assert_frozen_score(adapter, model)
    assert adapter.score(prompt="ab", continuation="ca").unit_kind == "token"


def test_parameter_hash_detects_parameter_change():
    torch.manual_seed(13)
    model = TinyCharLM()
    before = parameter_sha256(model)
    with torch.no_grad():
        next(model.parameters()).view(-1)[0].add_(1.0)
    assert parameter_sha256(model) != before


def test_zeref_adapter_rejects_unknown_tokenizer_character():
    model = TinyCharLM()
    adapter = ZerefNLLAdapter(
        model=model,
        stoi={"a": 0, "b": 1, "c": 2},
        checkpoint_identity={"checkpoint_sha256": "3" * 64},
        model_id="zeref-fixture",
    )
    with pytest.raises(ValueError, match="frozen tokenizer"):
        adapter.score(prompt="ab", continuation="x")


def test_transformers_adapter_rejects_unstable_suffix_boundary():
    class BoundaryMergingTokenizer(TinyTokenizer):
        def encode(self, text: str, *, add_special_tokens: bool = False):
            if text == "abca":
                return [0, 2, 0]
            return super().encode(text, add_special_tokens=add_special_tokens)

    adapter = TransformersNLLAdapter(
        model=TinyTransformersLM(),
        tokenizer=BoundaryMergingTokenizer(),
        checkpoint_identity={"revision": "5" * 40},
        model_id="smol-fixture",
    )
    with pytest.raises(ValueError, match="suffix boundary"):
        adapter.score(prompt="ab", continuation="ca")


def test_adapters_reject_empty_continuation():
    zeref = ZerefNLLAdapter(
        model=TinyCharLM(),
        stoi={"a": 0, "b": 1, "c": 2},
        checkpoint_identity={"checkpoint_sha256": "4" * 64},
        model_id="zeref-fixture",
    )
    smol = TransformersNLLAdapter(
        model=TinyTransformersLM(),
        tokenizer=TinyTokenizer(),
        checkpoint_identity={"revision": "5" * 40},
        model_id="smol-fixture",
    )
    for adapter in (zeref, smol):
        with pytest.raises(ValueError, match="continuation"):
            adapter.score(prompt="ab", continuation="")
