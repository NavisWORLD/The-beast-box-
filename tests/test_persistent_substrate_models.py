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
        self.inverse_vocab = {value: key for key, value in self.vocab.items()}
        self.name_or_path = "tiny-tokenizer"

    def encode(self, text: str, *, add_special_tokens: bool = False):
        assert add_special_tokens is False
        return [self.vocab[ch] for ch in text]

    def decode(self, ids, *, skip_special_tokens: bool = False):
        assert skip_special_tokens is False
        return "".join(self.inverse_vocab[int(value)] for value in ids)


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


def _zeref_adapter() -> tuple[ZerefNLLAdapter, TinyCharLM]:
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
    return adapter, model


def _smol_adapter() -> tuple[TransformersNLLAdapter, TinyTransformersLM]:
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
    return adapter, model


def test_zeref_adapter_scores_candidates_without_parameter_drift():
    adapter, model = _zeref_adapter()
    _assert_frozen_score(adapter, model)
    assert adapter.score(prompt="ab", continuation="ca").unit_kind == "character"


def test_smol_adapter_scores_candidates_without_parameter_drift():
    adapter, model = _smol_adapter()
    _assert_frozen_score(adapter, model)
    assert adapter.score(prompt="ab", continuation="ca").unit_kind == "token"


def test_complete_adapter_contract_has_stable_identity_ordered_scores_and_close():
    for adapter, model in (_zeref_adapter(), _smol_adapter()):
        before = parameter_sha256(model)
        identity_before = dict(adapter.identity)
        scores = adapter.score_candidates("ab", ["ca", "bc"])

        assert isinstance(scores, tuple)
        assert [score.candidate for score in scores] == ["ca", "bc"]
        assert dict(adapter.identity) == identity_before
        assert identity_before["model_id"] == adapter.model_id
        assert identity_before["parameter_sha256"] == before

        close_receipt = adapter.close()
        assert close_receipt["parameter_sha256_before"] == before
        assert close_receipt["parameter_sha256_after"] == before
        assert close_receipt["parameter_drift"] is False


def test_complete_adapter_contract_generates_greedy_receipt_without_parameter_drift():
    for adapter, model in (_zeref_adapter(), _smol_adapter()):
        before = parameter_sha256(model)
        receipt = adapter.generate("ab", max_new_tokens=2)
        after = parameter_sha256(model)

        assert before == after
        assert receipt["model_id"] == adapter.model_id
        assert receipt["max_new_tokens"] == 2
        assert receipt["generated_units"] == 2
        assert isinstance(receipt["text"], str)
        assert len(receipt["generated_ids_sha256"]) == 64
        assert receipt["parameter_sha256"] == before


def test_parameter_hash_detects_parameter_change():
    torch.manual_seed(13)
    model = TinyCharLM()
    before = parameter_sha256(model)
    with torch.no_grad():
        next(model.parameters()).view(-1)[0].add_(1.0)
    assert parameter_sha256(model) != before


def test_close_rejects_parameter_drift():
    adapter, model = _zeref_adapter()
    with torch.no_grad():
        next(model.parameters()).view(-1)[0].add_(1.0)
    with pytest.raises(RuntimeError, match="parameter drift"):
        adapter.close()


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


def test_generate_rejects_non_positive_budget():
    for adapter, _model in (_zeref_adapter(), _smol_adapter()):
        with pytest.raises(ValueError, match="max_new_tokens"):
            adapter.generate("ab", max_new_tokens=0)
