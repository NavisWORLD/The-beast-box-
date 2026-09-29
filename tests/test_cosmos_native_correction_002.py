"""Source-only RED/GREEN tests: predeclared real-checkpoint experiment protocol.

These tests DO NOT mock a passing published checkpoint evaluation. Actual
pinned-weight inference runs only in the separately named real-CPU workflow.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import cosmos_native_correction_002 as pilot


def test_fixed_cases_have_no_duplicate_queries_or_gold_answer_leak():
    pilot.validate_cases()
    assert len(pilot.CASES) == 4
    assert pilot.sha256(pilot.CASES) == pilot.sha256(pilot.CASES)
    for case in pilot.CASES:
        assert case["gold"] != case["example_gold"]
        assert case["example_gold"] != case["false_example"]


def test_leakage_and_invalid_negative_control_fail_closed(monkeypatch):
    cases = [dict(row) for row in pilot.CASES]
    cases[1]["example"] = cases[0]["question"]
    monkeypatch.setattr(pilot, "CASES", tuple(cases))
    with pytest.raises(ValueError, match="collision"):
        pilot.validate_cases()


def test_explicit_arm_gold_leak_is_segregated_from_transfer():
    case = pilot.CASES[0]
    for arm in pilot.ARM_NAMES:
        prompt = pilot.prompt_for(case, arm, prior_response="wrong guess")
        assert len(prompt.encode()) < 1024
        assert case["question"] in prompt if arm != "direct_correction" else case["paraphrase"] in prompt
        if arm == "direct_correction":
            assert "Reviewer correction" in prompt
            assert case["gold"] in prompt
        else:
            assert "Reviewer correction" not in prompt
            assert case["gold"] not in prompt
        if arm == "incorrect_example":
            assert f"Example answer: {case['false_example']}" in prompt
    with pytest.raises(ValueError, match="unregistered"):
        pilot.prompt_for(case, "secret-cheating-arm")


def test_frozen_strict_response_grader_disallows_substring_credit():
    assert pilot.exact_first_line("Answer: 15.", "15")
    assert pilot.exact_first_line("\n15\nMore discussion", "15")
    assert not pilot.exact_first_line("150", "15")
    assert not pilot.exact_first_line("Maybe 15", "15")
    assert not pilot.exact_first_line("", "15")


def test_actual_runner_contract_reports_all_conditions_even_when_all_fail(monkeypatch):
    class Fake:
        model = SimpleNamespace(config=SimpleNamespace(attention_mode="dyn12"))

        def info(self):
            return {
                "model_id": "rawrphos-native", "training_steps": 14000,
                "checkpoint_sha256": pilot.CHECKPOINTS["14k"]["sha256"],
                "tokenizer_sha256": "fixture-not-a-real-checkpoint", "parameter_count": 0,
            }
    seen_modes = []

    def simulated_failure(engine, prompt, answer):
        seen_modes.append(engine.model.config.attention_mode)
        # Deliberately all wrong: no quality success gate, no fake training.
        return {
            "exact_first_line": False, "target_mean_nll_nats": 10.0,
            "generation": "unhelpful", "generation_sha256": "synthetic",
            "generated_tokens": 1, "target_token_count": 1,
        }

    monkeypatch.setattr(pilot, "weights_digest", lambda _: "same-weights")
    monkeypatch.setattr(pilot, "score_generated", simulated_failure)
    observed = pilot.run(Fake(), "14k")
    assert observed["checkpoint"] == "14k"
    assert observed["parameter_sha256_unchanged"] == "same-weights"
    assert len(observed["observations"]) == 4
    assert len(seen_modes) == 4 * len(pilot.ARM_NAMES)
    assert seen_modes.count("standard") == 4
    assert set(observed["aggregate"]) == set(pilot.ARM_NAMES)
    assert all(result["exact_first_line_fraction"] == 0.0 for result in observed["aggregate"].values())
    assert observed["no_model_training_or_product_memory"] is True


def test_real_model_identity_mismatch_must_not_be_silently_substituted(monkeypatch):
    class Fake:
        model = SimpleNamespace(config=SimpleNamespace(attention_mode="dyn12"))
        def info(self):
            return {
                "model_id": "rawrphos-native", "training_steps": 12000,
                "checkpoint_sha256": "0" * 64,
            }

    with pytest.raises(RuntimeError, match="metadata differs"):
        pilot.run(Fake(), "14k")
