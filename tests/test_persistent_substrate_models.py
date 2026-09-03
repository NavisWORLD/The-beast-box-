from __future__ import annotations

from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")

from beastbox.persistent_substrate.models import (
    TransformersNLLAdapter,
    ZerefNLLAdapter,
    parameter_sha256,
)
from beastbox.persistent_substrate.protocol import PromptCase


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


def _prompt() -> PromptCase:
    return PromptCase(
        prompt_id="adapter-contract-001",
        prompt="ab",
        kind="calibration",
        paired_group="adapter-contract",
    )


def _assert_frozen_score(adapter, model) -> None:
    before = parameter_sha256(model)
    assert model.training is False
    assert all(parameter.grad is None for parameter in model.parameters())

    score = adapter.score(_prompt(), candidate_id="candidate-ca", continuation="ca")

    after = parameter_sha256(model)
    assert before == after
    assert score.model_id == adapter.model_id
    assert score.prompt_id == "adapter-contract-001"
    assert score.candidate_id == "candidate-ca"
    assert score.continuation_token_count == 2
    assert score.conditional_nll >= 0.0
    assert torch.isfinite(torch.tensor(score.conditional_nll))
    assert score.checkpoint_identity == adapter.checkpoint_identity
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
        adapter.score(_prompt(), candidate_id="candidate-x", continuation="x")


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
            adapter.score(_prompt(), candidate_id="empty", continuation="")
