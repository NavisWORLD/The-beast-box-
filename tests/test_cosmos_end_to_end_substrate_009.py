"""Preflight frozen non-leaky real product routing vs generative control design.

Source-only tests are not model-generated performance evidence.
"""
import pytest

from scripts import cosmos_end_to_end_substrate_009 as p
from scripts.cosmos_learning_challenge import TRAIN_CORPUS
from beastbox.refractive_memory import WEIGHTS

def test_nonoverlapping_static_route_training_and_two_precommitted_lengths():
    assert p.SEEDS==(17,41)
    assert p.MODELS_UNDER_TEST==("smollm2-135m","qwen2.5-0.5b")
    assert p.ARMS==("no_evidence","lexical","frozen_r12","adaptive_r12","oracle")
    assert p.LENGTHS=={"short_8_records":8,"long_32_records":32}
    for seed in p.SEEDS:
        names=set()
        for length,count in p.LENGTHS.items():
            documents,cases=p.source_fixture(seed,length)
            assert len(documents)==count
            assert len(cases)==p.TESTED_PER_LENGTH[length]
            assert len({d["name"] for d in documents})==len(documents)
            assert not names.intersection({d["text"] for d in documents})
            names.update(d["text"] for d in documents)
            for case in cases:
                doc=documents[case["gold_doc_idx"]]
                assert case["gold"]==doc["seed"]+case["offset"]
                assert str(case["gold"]) not in doc["text"]
                assert doc["name"] in case["query"]
                assert all(doc["text"] not in train for train,_,_ in TRAIN_CORPUS)
    with pytest.raises(ValueError,match="unregistered"):
        p.source_fixture(999,"short_8_records")
    with pytest.raises(ValueError,match="unregistered"):
        p.source_fixture(17,"tuned_length")

def test_real_product_router_fit_and_persisted_synthetic_evidence():
    cases,metadata=p.retrieval_bundle(17)
    assert len(cases)==24
    assert set(metadata["adapted_weights"])==set(WEIGHTS)
    assert len({row["case_id"] for row in cases})==24
    assert metadata["train_sample_count"]==len(TRAIN_CORPUS)
    assert dict(WEIGHTS)==metadata["frozen_weights"]
    for case in cases:
        assert case["arms"]["oracle"]["retrieval_correct"] is True
        assert case["arms"]["no_evidence"]["retrieval_correct"] is None
        for arm in p.ARMS:
            context=case["arms"][arm]
            assert str(case["gold"]) not in context["prompt"]
            assert "FINAL:" in context["prompt"]
            assert case["arms"][arm]["prompt"].split("QUESTION:")[-1]==(
               case["arms"]["oracle"]["prompt"].split("QUESTION:")[-1])
    assert [sum(r["length"]==name for r in cases) for name in p.LENGTHS]==[8,16]

def test_two_frozen_model_pins_are_not_silent_substitutions():
    assert set(p.MODELS_UNDER_TEST).issubset(p.MODELS)
    assert p.GENERATIONS==18
    for name in p.MODELS_UNDER_TEST:
        assert len(p.MODELS[name]["revision"])==40
        assert len(p.MODELS[name]["weights_sha256"])==64

@pytest.mark.parametrize(("text","parsed"),[
    ("FINAL: 346","346"),
    ("346","346"),
    ("FINAL: UNKNOWN","UNKNOWN"),
    ("The answer is 346","None"),
    ("FINAL: 346; maybe 347","None"),
    ("FINAL: 1346 and another answer","None"),
    ("FINAL: 346\nexplanation","346"),
])
def test_strict_first_line_is_precommitted(text,parsed):
    assert p.parse_answer(text)==(None if parsed=="None" else parsed)

def test_negative_results_not_suppressed_by_aggregate():
    fake=[]
    for seed in p.SEEDS:
        for label in p.MODELS_UNDER_TEST:
            fake.append({
                "schema":"cosmos-original-generative-external-substrate-009-seed-model-v1",
                "seed":seed,"subject":label,"fixture_sha256":"fixture-v1",
                "summary":{length:{arm:{
                    "correct":0,"count":p.TESTED_PER_LENGTH[length],
                    "retrieval_correct":None if arm=="no_evidence" else 0,
                } for arm in p.ARMS} for length in p.LENGTHS}
            })
    summary=p.summarize(fake)
    assert summary["preregistered_multimodel_two_length_candidate_pattern"] is False
    assert summary["reliable_general_generative_improvement_proven"] is False
    assert len(summary["results"])==4
    with pytest.raises(ValueError,match="missing"):
        p.summarize(fake[:-1])
