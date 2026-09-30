"""Diagnostic contracts, not a retroactive rescore of original COSMOS 009."""
import pytest
from scripts import cosmos_wiring_calibration_011 as d

def test_actual_durable_product_advances_cns_but_current_r12_is_unadvanced():
    actual=d.actual_product_wiring_audit()
    assert actual["actual_cns_step_after_turns"]==2
    assert actual["cns_dyn12_changes_with_turns"] is True
    assert actual["synthetic_memory_seen"] is True
    # Canary for *current product* disconnect. Remove only on future
    # separately reviewed version of product with an active transition.
    assert actual["r12_transition_occurred"] is False
    assert actual["r12_sequence_before"]==actual["r12_sequence_after"]==0
    assert actual["r12_initial_and_final_coupling"]==[0.0,0.0]
    assert actual["actual_two_turn_route_labels"]==[
        "RefractiveMemoryRouter","RefractiveMemoryRouter"]

def test_009_isolated_default_state_has_no_active_refractive_coupling():
    check=d.isolated_009_router_audit()
    assert check["fixture_seed"]==17
    assert check["static_sequence_used_by_009"]==0
    assert check["static_dyn12_used_by_009"]==[0.0]*12
    assert check["r12_initial_reality_coupling"]==0.0
    assert check["refractive_reflection_inactive_in_009"] is True
    assert check["actual_product_adaptive_weights_auto_enabled"] is False
    assert check["short_eight_original_exact_retrieval"]["oracle"]==8
    assert check["short_eight_original_exact_retrieval"]["lexical"]==8

def test_oracle_probes_cannot_accidentally_contain_calculated_gold():
    assert d.SEED==17 and d.SAMPLE_CASES==4
    assert d.BUDGETS==(18,80)
    assert d.CONDITIONS==(
        "copy_seed","arithmetic_only","original_009_oracle",
        "structured_011_oracle")
    docs,cases=d.source_fixture(d.SEED,d.SAMPLE_LENGTH)
    for case in cases[:d.SAMPLE_CASES]:
        doc=docs[case["gold_doc_idx"]]
        strings=d.format_prompts(case,doc)
        assert set(strings)==set(d.CONDITIONS)
        assert str(case["gold"]) not in strings["copy_seed"]
        assert str(case["gold"]) not in strings["original_009_oracle"]
        assert str(case["gold"]) not in strings["structured_011_oracle"]
        assert str(doc["seed"]) in strings["arithmetic_only"]
        assert doc["text"] in strings["original_009_oracle"]
        assert doc["name"] in strings["structured_011_oracle"]

@pytest.mark.parametrize(("text","strict","semantic"),[
    ("FINAL: 482","482","482"),
    ("The answer is 482.","","482"),
    ("480 + 2 = 482","", "482"),
    ("FINAL: 1482 and 482","",""),
    ("possibly 482 maybe 483","",""),
    ("480 + 3 = 482","",""),
    ("RESULT: 482","","482"),
    ("FINAL: UNKNOWN","UNKNOWN","UNKNOWN"),
])
def test_strict_original_and_separate_conservative_semantic(text,strict,semantic):
    s=d.parse_answer(text)
    m=d.first_line_semantic(text,480,2)
    assert s==(strict or None)
    assert m==(semantic or None)
