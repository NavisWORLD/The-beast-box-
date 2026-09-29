"""Source-only COSMOS 004 protocol/metric tests, NOT fake published performance."""
from __future__ import annotations
from scripts import cosmos_micro_originals_004 as micro
from scripts.cosmos_native_correction_002 import CASES, prompt_for, sha256
import pytest


def test_exact_four_cases_and_five_common_arms_without_cherry_picking():
    micro.validate_cases()
    assert micro.CASES is CASES
    assert micro.sha256(micro.CASES)==sha256(CASES)
    assert micro.ARMS==("baseline","neutral_example","correct_example","incorrect_example","direct_correction")
    assert micro.SURFACES==("full_native_text_bounded","compact_char_fit")
    assert micro.GENERATED_CHARACTERS==12
    assert micro.MAX_ENCODED_INPUT+micro.GENERATED_CHARACTERS==128


def test_two_original_models_are_pinned_distinct_and_not_claimed_independent():
    assert set(micro.LABELS)=={"phos","cosmos_born"}
    assert micro.REPO=="phera-ra/QC67_cosmo"
    assert len(micro.REV)==40
    assert len(micro.ORIGINAL_SHA)==5
    assert all(len(x)==64 for x in micro.ORIGINAL_SHA.values())
    # Keep the copied subset bit-for-bit aligned with the pre-existing
    # verified QC67 pins instead of maintaining a second handwritten hash.
    import json
    from pathlib import Path
    canonical = json.loads((Path(__file__).resolve().parent.parent /
                            "models/qc67/pins.json").read_text())
    assert micro.REV == canonical["hf_revision"]
    for name in ("weights/phos.pt", "architecture/cosmos_state_ladder.py",
                 "architecture/cosmos_spark_cst.py"):
        assert micro.ORIGINAL_SHA[name] == canonical["files"][name]



def test_compact_controls_keep_correct_and_false_examples_distinct():
    for case in CASES:
        sample={}
        for arm in micro.ARMS:
            prompt=micro.compact_prompt(case,arm,prior_response="irrelevant sample")
            assert len(prompt)<=230
            sample[arm]=prompt
            assert case["paraphrase"] in prompt if arm=="direct_correction" else case["question"] in prompt
        assert case["example_gold"] in sample["correct_example"]
        assert case["false_example"] in sample["incorrect_example"]
        assert "Correction: "+case["gold"] in sample["direct_correction"]
        assert "Correction:" not in sample["correct_example"]
        assert sample["baseline"]!=sample["neutral_example"]


def test_report_unsupported_chars_and_context_cutting_instead_of_silent_padding():
    case=CASES[0]
    valid={char:i for i,char in enumerate(sorted(set("Example:0123456789Q A?+=")))}
    text="!x"*90+"Q: 8+7=15"
    report=micro.prepare_prompt(text,valid,case,"baseline","compact_char_fit")
    assert report["unsupported_characters_removed"]>0
    assert report["full_prompt_sha256"]!=report["consumed_prompt_sha256"]
    assert report["left_context_characters_truncated"]>=0
    assert len(report["consumed_prompt"])<=116
    assert report["diagnostic"]["literal_target_query_in_consumed_context"] is False


def test_independent_grading_does_not_change_existing_strict_protocol():
    for case in CASES[:2]:
        assert micro.secondary_correct("The answer is "+case["gold"]+".",case)
        assert not micro.exact_first_line("The answer is "+case["gold"]+".",case["gold"])
        assert micro.exact_first_line(case["gold"],case["gold"])
    reversed_case=CASES[2]
    upper_case=CASES[3]
    assert micro.secondary_correct("Reverse: "+reversed_case["gold"],reversed_case)
    assert not micro.secondary_correct("reversed "+reversed_case["example_gold"],reversed_case)
    assert micro.secondary_correct("It is "+upper_case["gold"],upper_case)
    assert not micro.secondary_correct(upper_case["gold"].lower(),upper_case)


def test_fail_closed_on_unregistered_original_and_control(tmp_path):
    with pytest.raises(ValueError,match="unregistered"):
        micro.fetch_and_verify("random-model",tmp_path/"new")
    with pytest.raises(ValueError,match="unregistered"):
        micro.compact_prompt(CASES[0],"extra-secret-control")
