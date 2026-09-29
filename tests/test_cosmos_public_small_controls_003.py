"""Source-only protocol integrity checks; actual public model inference is separate CI."""
from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from scripts import cosmos_public_small_controls_003 as pilot
from scripts.cosmos_native_correction_002 import (
    CASES as NATIVE_CASES,
    ARM_NAMES as NATIVE_ARMS,
    prompt_for as native_prompt_for,
    sha256 as native_sha256,
)


class FakeTokenizer:
    bos_token_id = 1
    eos_token_id = 2
    chat_template = "official-upstream-fixture"
    def encode(self, text, add_special_tokens=False):
        return [ord(ch) + 3 for ch in text]
    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        assert tokenize is True and add_generation_prompt is True
        return [1, 41] + self.encode(messages[0]["content"]) + [42]


def test_identical_source_committed_native_task_fixture_and_five_shared_arms():
    pilot.validate_cases()
    assert pilot.CASES is NATIVE_CASES
    assert pilot.sha256(pilot.CASES) == native_sha256(NATIVE_CASES)
    assert set(pilot.ARM_NAMES).issubset(set(NATIVE_ARMS))
    assert set(NATIVE_ARMS)-set(pilot.ARM_NAMES) == {"correct_example_standard_attention"}
    for case in pilot.CASES:
        for arm in pilot.ARM_NAMES:
            assert pilot.prompt_for(case, arm, prior_response="wrong answer") == native_prompt_for(
                case, arm, prior_response="wrong answer"
            )


def test_two_independent_pinned_public_model_families_with_full_sha256():
    assert set(pilot.MODELS) == {"smollm2-135m", "qwen2.5-0.5b"}
    assert {item["architecture"] for item in pilot.MODELS.values()} == {"llama", "qwen2"}
    for item in pilot.MODELS.values():
        assert len(item["revision"]) == 40
        assert len(item["weights_sha256"]) == 64
        assert item["declared_license"] == "apache-2.0"
        assert item["expected_parameter_range"][0] > 3_909_956


def test_raw_and_chat_prompt_conditions_are_not_silently_mixed():
    tok = FakeTokenizer()
    p = native_prompt_for(NATIVE_CASES[0], "baseline")
    raw = pilot.tokens_for_prompt(tok, p, "raw_native_compatible")
    chat = pilot.tokens_for_prompt(tok, p, "official_chat_template")
    assert raw[0] == 1 and raw[1:] == tok.encode(p)
    assert chat[:2] == [1, 41] and chat[-1] == 42
    assert raw != chat
    with pytest.raises(ValueError, match="unregistered"):
        pilot.tokens_for_prompt(tok, p, "mystery")


def test_missing_official_chat_template_fails_closed():
    tok = FakeTokenizer()
    tok.chat_template = ""
    with pytest.raises(ValueError, match="not published"):
        pilot.tokens_for_prompt(tok, "short", "official_chat_template")


def test_five_shared_arms_do_not_claim_native_ablation_or_independent_holdout():
    assert pilot.FORMAT_NAMES == ("raw_native_compatible", "official_chat_template")
    assert pilot.ARM_NAMES == (
        "baseline", "neutral_example", "correct_example",
        "incorrect_example", "direct_correction",
    )
    assert pilot.MAX_OUTPUT_TOKENS == 12
    assert pilot.SEED == 67


def test_weight_file_checksum_is_over_actual_local_payload(tmp_path):
    file = tmp_path / pilot.WEIGHT_FILENAME
    file.write_bytes(b"known synthetic model payload, NOT a real checkpoint")
    assert pilot.hash_file(file) == hashlib.sha256(file.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="unregistered"):
        pilot.download_and_verify("unregistered", tmp_path / "new")


def test_no_future_model_inference_is_claimed_by_this_source_only_suite():
    # The actual real weights must pass CPU CI before measured claims are made.
    assert not hasattr(pilot, "SIMULATED_QUALITY_SCORE")
