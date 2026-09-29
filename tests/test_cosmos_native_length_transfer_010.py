"""Fresh-seed real original dyn12 context extrapolation has matched controls."""
import pytest
from scripts import cosmos_native_length_transfer_010 as p

def test_exact_independent_new_seeds_and_monotonic_sequence_lengths():
    assert p.SEEDS==(19,43,71)
    assert not set(p.SEEDS).intersection(set(p.OLD_SEEDS))
    assert p.SPLITS["shift_four"]==(128,4)
    assert p.SPLITS["shift_five"]==(128,5)
    assert p.SPLITS["shift_six"]==(128,6)
    assert p.MAX_SEQ_LEN>=15
    for seed in p.SEEDS:
        parts=p.split_for_seed(seed)
        assert len({row for rows in parts.values() for row in rows})==sum(
            count for count,_ in p.SPLITS.values())
        for name,(n,bindings) in p.SPLITS.items():
            assert len(parts[name])==n
            assert all(len(row[0])==2*bindings+3 for row in parts[name])

def test_no_tuned_new_seeds_or_architectures():
    with pytest.raises(ValueError,match="unregistered"):
        p.split_for_seed(11)
    with pytest.raises(ValueError,match="nonregistered"):
        p.new_model("preferred-after-test",19)

def test_original_native_gate_is_live_not_shuffled_or_inert():
    pytest.importorskip("rawrphos")
    seed=19
    parts=p.split_for_seed(seed)
    v=p.mechanism_check(seed,parts)
    assert v["causal_on_4_5_6"]
    assert len(v["native_gradients"])==4
    heads={p.tensor_digest(p.new_model(mode,seed)) for mode in p.MODES}
    assert heads=={v["initial_parameter_sha256"]}
    counts={p.new_model(mode,seed).parameter_count() for mode in p.MODES}
    assert len(counts)==1

def test_underdelivering_control_scores_are_not_suppressed():
    def dummy(seed):
        modes=[]
        for mode,val in zip(p.MODES,(0.10,0.60,0.50)):
            metrics={
                length:{"accuracy":val,
                        "correct":round(val*(256 if length=="test_three" else 128)),
                        "count":256 if length=="test_three" else 128,
                        "last_token_cross_entropy_nats":1.0}
                for length in p.SPLITS if length!="train"
            }
            modes.append({"mode":mode,"eval":metrics})
        return {"seed":seed,"schema":"cosmos-original-dyn12-six-binding-010-seed-v1",
                "arms":modes}
    r=p.summarize([dummy(seed) for seed in p.SEEDS])
    assert not r["preregistered_multi_length_candidate"]
    assert not r["novel_native_12d_long_sequence_advantage_proven"]
    for level in ("shift_four","shift_five","shift_six"):
        assert r["paired_differences"]["standard"][level][0]<0
    with pytest.raises(ValueError,match="all preregistered"):
        p.summarize([dummy(seed) for seed in p.SEEDS[:-1]])
