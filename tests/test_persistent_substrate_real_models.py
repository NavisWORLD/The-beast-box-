from __future__ import annotations

import math
from types import SimpleNamespace

import pytest


torch = pytest.importorskip("torch")

from beastbox.persistent_substrate.real_models import (  # noqa: E402
    EXPECTED_MODEL_A_CHECKPOINT_SHA256,
    EXPECTED_MODEL_B_REVISION,
    RealCandidateScore,
    TransformersConditionalNLLAdapter,
    ZerefConditionalNLLAdapter,
    parameter_sha256,
)


class TinyZeref(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        torch.manual_seed(7)
        self.embedding = torch.nn.Embedding(8, 6)
        self.head = torch.nn.Linear(6, 8, bias=False)

    def forward(self, input_ids):
        hidden = self.embedding(input_ids)
        return self.head(hidden), None


class TinyHF(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        torch.manual_seed(11)
        self.embedding = torch.nn.Embedding(32, 7)
        self.head = torch.nn.Linear(7, 32, bias=False)

    def forward(self, *, input_ids, attention_mask=None, use_cache=False):
        del attention_mask, use_cache
        return SimpleNamespace(logits=self.head(self.embedding(input_ids)))


class CharacterTokenizer:
    pad_token_id = 0
    eos_token_id = 0

    def __call__(self, text, *, add_special_tokens=False, **kwargs):
        del add_special_tokens, kwargs
        return {"input_ids": [ord(ch) % 31 + 1 for ch in text]}


def test_frozen_real_model_identities_match_sealed_round_trip() -> None:
    assert EXPECTED_MODEL_A_CHECKPOINT_SHA256 == (
        "454f3017618a81fb9a13393b215d448f365534baf5b607e19d1438955921e425"
    )
    assert EXPECTED_MODEL_B_REVISION == "4e53f736cbb20a9a0f56b4c4bf378d9f306ff915"


def test_parameter_sha256_is_deterministic_and_parameter_sensitive() -> None:
    model = TinyZeref().eval()
    first = parameter_sha256(model)
    second = parameter_sha256(model)
    assert first == second
    assert len(first) == 64

    with torch.no_grad():
        model.embedding.weight[0, 0] += 1.0
    assert parameter_sha256(model) != first


def test_zeref_adapter_scores_candidate_without_parameter_drift() -> None:
    model = TinyZeref().eval()
    stoi = {ch: index for index, ch in enumerate("abcdefgh")}
    adapter = ZerefConditionalNLLAdapter(
        model=model,
        stoi=stoi,
        block=8,
        checkpoint_identity={"checkpoint_sha256": "a" * 64},
        tokenizer_id="tiny-character-tokenizer",
    )
    before = parameter_sha256(model)
    score = adapter.score(
        prompt_id="unit-zeref",
        prompt="ab",
        candidate="cd",
    )
    after = parameter_sha256(model)

    assert isinstance(score, RealCandidateScore)
    assert before == after
    assert score.model_id == "zeref-pinned-active-checkpoint"
    assert score.prompt_id == "unit-zeref"
    assert score.candidate == "cd"
    assert math.isfinite(score.conditional_nll)
    assert score.conditional_nll >= 0
    assert score.predicted_units == 2
    assert score.unit_kind == "character"
    assert len(score.input_ids_sha256) == 64


def test_smol_adapter_scores_candidate_without_parameter_drift() -> None:
    model = TinyHF().eval()
    tokenizer = CharacterTokenizer()
    adapter = TransformersConditionalNLLAdapter(
        model=model,
        tokenizer=tokenizer,
        model_id="HuggingFaceTB/SmolLM2-135M",
        checkpoint_identity={"revision": EXPECTED_MODEL_B_REVISION},
        tokenizer_id="tiny-character-tokenizer",
    )
    before = parameter_sha256(model)
    score = adapter.score(
        prompt_id="unit-smol",
        prompt="ab",
        candidate="cd",
    )
    after = parameter_sha256(model)

    assert isinstance(score, RealCandidateScore)
    assert before == after
    assert score.model_id == "HuggingFaceTB/SmolLM2-135M"
    assert score.prompt_id == "unit-smol"
    assert score.candidate == "cd"
    assert math.isfinite(score.conditional_nll)
    assert score.conditional_nll >= 0
    assert score.predicted_units == 2
    assert score.unit_kind == "subword_token"
    assert len(score.input_ids_sha256) == 64


def test_transformers_adapter_rejects_prompt_prefix_tokenization_drift() -> None:
    class PrefixDriftTokenizer(CharacterTokenizer):
        def __call__(self, text, *, add_special_tokens=False, **kwargs):
            del add_special_tokens, kwargs
            if text == "ab":
                return {"input_ids": [1, 2]}
            if text == "abcd":
                return {"input_ids": [9, 2, 3, 4]}
            return super().__call__(text)

    adapter = TransformersConditionalNLLAdapter(
        model=TinyHF().eval(),
        tokenizer=PrefixDriftTokenizer(),
        model_id="HuggingFaceTB/SmolLM2-135M",
        checkpoint_identity={"revision": EXPECTED_MODEL_B_REVISION},
        tokenizer_id="prefix-drift-tokenizer",
    )
    with pytest.raises(ValueError, match="tokenization prefix"):
        adapter.score(prompt_id="drift", prompt="ab", candidate="cd")
