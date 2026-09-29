"""All quality outcomes allowed; distinguish self-review from oracle disclosure."""
import json
import re
import pytest
from scripts import cosmos_self_critique_005 as pilot

def test_frozen_distinct_novel_probes_and_uncontaminated_own_review_prompt():
    pilot.valid()
    assert len(pilot.CASES)==8 and pilot.SEED==67
    assert len(pilot.ARMS)==8
    for c in pilot.CASES:
        neutral=pilot.static_question(c["question"])
        critique=pilot.review_prompt(c,"FINAL: WRONG")
        assert c["gold"] not in neutral
        assert c["gold"] not in critique
        assert "Reviewer discloses" not in critique
        for label in ("neutral_retry","true_correctness_bit","false_correctness_bit"):
            assert c["gold"] not in pilot.revision_prompt(
                c,"FINAL: WRONG",label,baseline_correct=False)
        oracle=pilot.revision_prompt(c,"FINAL: WRONG","gold_disclosure")
        assert "Reviewer discloses" in oracle and c["gold"] in oracle
        novel=pilot.new_task_prompt(c,critique="VERDICT: INCORRECT\nFINAL: WRONG")
        assert c["transfer"] in novel and c["transfer_gold"] not in novel

def test_frozen_strict_vs_semantic_first_line_prevents_format_false_negatives():
    assert pilot.grade("FINAL: 43","43","addition")
    assert pilot.semantic_grade("17 + 26 is 43.","43","addition")
    assert not pilot.grade("17 + 26 is 43.","43","addition")
    assert pilot.semantic_grade("The answer is 43.","43","addition")
    assert not pilot.semantic_grade("17+26 is 143.","43","addition")
    assert not pilot.semantic_grade("Something about 43 and maybe 44","43","addition")
    assert pilot.semantic_grade("The answer is X4N","X4N","reverse")
    assert not pilot.semantic_grade("The answer is x4n","X4N","reverse")
    assert pilot.semantic_grade("FINAL: COBALT","COBALT","uppercase")
    assert not pilot.semantic_grade("FINAL: cobalt","COBALT","uppercase")
    assert pilot.verdict("VERDICT: INCORRECT\nFINAL: 43")=="INCORRECT"
    assert pilot.verdict("I am perhaps wrong")=="UNPARSEABLE"

def test_transfer_self_review_gold_leak_is_excluded():
    assert pilot.has_new_gold("Reviewer explanation: 42","42")
    assert not pilot.has_new_gold("Some number 142","42")
    assert not pilot.has_new_gold("VERDICT: INCORRECT\nFINAL: WRONG","42")

def test_null_self_correction_cannot_pass_using_an_oracle_control():
    class Unhelpful:
        name="native18k"
        original="fixture-only-not-a-real-model"
        def __call__(self,prompt):
            # Synthetic *software* fixture: will repeat the exact leaked gold
            # answer only in the intentionally unscored oracle condition.
            if "Reviewer discloses the correct answer: " in prompt:
                answer=prompt.split("Reviewer discloses the correct answer: ",1)[1].split(".",1)[0]
                return "FINAL: "+answer
            return "FINAL: WRONG"
        def verify_immutable(self):return True
    result=pilot.run(Unhelpful())
    assert len(result["cases"])==8
    assert result["aggregate"]["gold_disclosure"]["correct"]==8
    assert result["aggregate"]["self_critique"]["correct"]==0
    assert result["semantic_aggregate"]["self_critique"]["correct"]==0
    assert result["synthetic_candidate_self_correction_pattern_observed"] is False
    assert result["reliable_generative_self_correction_proven"] is False
    for row in result["cases"]:
        assert "generation" not in row
        assert "VERDICT: INCORRECT" not in json.dumps(row)
