"""No quality-success bias: test leakage, matching, causality and null reporting."""
import pytest
from scripts import cosmos_dyn12_controlled_006 as pilot

def test_fixed_disjoint_splits_and_new_four_binding_distribution():
    a=pilot.dataset(11); b=pilot.dataset(11)
    assert a==b
    assert {k:len(v) for k,v in a.items()}=={
        "train":1536,"dev":128,"test":256,"ood_four_bindings":128}
    seen={k:set(v) for k,v in a.items()}
    for left in seen:
        for right in seen:
            if left!=right: assert not seen[left].intersection(seen[right])
    assert all(len(x[0])==9 for x in a["train"])
    assert all(len(x[0])==11 for x in a["ood_four_bindings"])
    for rows in a.values():
        for seq,target in rows:
            assert seq[0]==1 and 18 in seq
            lookup=dict(zip(seq[1:seq.index(18):2],seq[2:seq.index(18):2]))
            assert target==lookup[seq[-1]]

def test_equal_initial_tensor_hash_and_finite_12d_mechanism():
    # Main repository Product CI intentionally omits the optional native Torch
    # package. The dedicated experiment CI installs it and MUST execute this
    # mechanistic test (its workflow separately enforces that dedicated gate).
    pytest.importorskip("rawrphos")
    parts=pilot.dataset(11)
    proof=pilot.mechanism_preflight(11,parts["train"])
    assert proof["causal_prefix_unchanged"] and proof["state_attention_active"]
    assert proof["initial_dyn12_standard_logit_distance"]>0
    assert len(proof["gradient_max_abs"])==4
    initial=set()
    counts=set()
    for mode in pilot.MODES:
        model=pilot.model_for(mode,11)
        initial.add(pilot.tensor_digest(model))
        counts.add(model.parameter_count())
    assert initial=={proof["same_initial_parameter_sha256"]}
    assert len(counts)==1

def test_unregistered_hyperparameter_search_is_forbidden():
    with pytest.raises(ValueError,match="unregistered"):
        pilot.model_for("better_by_definition",11)
    with pytest.raises(ValueError,match="unregistered"):
        pilot.model_for("dyn12",1234)
    with pytest.raises(ValueError,match="unregistered"):
        pilot.run_seed(1234)

def test_preregistered_summarizer_preserves_negative_results_and_missing_seeds_fail():
    def fake(seed):
        rows=[]
        for mode,acc in zip(pilot.MODES,(0.125,0.625,0.5)):
            ev={part:{"accuracy":acc,"last_token_cross_entropy_nats":1.0,
                      "correct":int(acc*256),"count":256}
                for part in ("dev","test","ood_four_bindings")}
            rows.append({"mode":mode,"eval":ev})
        return {"seed":seed,"schema":"cosmos-native-dyn12-independent-training-006-seed-v1",
                "independently_trained_models":rows}
    rows=[fake(i) for i in pilot.SEEDS]
    report=pilot.summarize(rows)
    assert report["paired_differences"]["dyn12_minus_standard"]==[-0.5]*3
    assert report["preregistered_synthetic_candidate_pattern_observed"] is False
    assert report["novel_intelligence_advantage_proven"] is False
    with pytest.raises(ValueError,match="precisely"):
        pilot.summarize(rows[:-1])
