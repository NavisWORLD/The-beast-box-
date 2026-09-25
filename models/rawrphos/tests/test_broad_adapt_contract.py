"""A broad-data phase keeps a fixed 80/20 source budget and immutable scope."""
import pytest
from rawrphos.training.broad_adapt import BroadConfig, sampling_weights
from rawrphos.scripts.prepare_broad_curriculum import CATEGORIES,VERSION


def make_rows():
    old=[
        {"source":"public-old","category":"dialogue"},
        {"source":"public-old","category":"dialogue"},
        {"source":"public-old","category":"greeting"},
    ]
    broad=[
        {"source":VERSION,"category":name} for name in CATEGORIES
    ]
    broad.append({"source":VERSION,"category":"arithmetic"})
    return old+broad,len(old)


def test_old_mass_eighty_percent_synthetic_twenty_category_balanced():
    all_rows,n=make_rows()
    weights=sampling_weights(all_rows,n)
    assert abs(weights[:n].sum().item()-0.8)<1e-10
    assert abs(weights[n:].sum().item()-0.2)<1e-10
    assert abs(weights.sum().item()-1.0)<1e-10
    arithmetic=[weights[n+i].item() for i,r in enumerate(all_rows[n:])
                if r["category"]=="arithmetic"]
    assert len(arithmetic)==2
    assert abs(sum(arithmetic)-weights[n].item())<1e-10


def test_unknown_old_category_and_wrong_ordering_fail_closed():
    rows,n=make_rows()
    rows[0]["category"]="unauthorized_category"
    with pytest.raises(ValueError,match="unknown"):
        sampling_weights(rows,n)
    rows,n=make_rows()
    rows[n]["source"]="public-old"
    with pytest.raises(ValueError,match="ordering"):
        sampling_weights(rows,n)


def test_unauthorized_distribution_and_context_cannot_be_silently_tuned():
    BroadConfig()
    for spec in (
        {"broad_mass":0.25,"old_mass":0.75},
        {"learning_rate":.00008},
        {"max_seq_len":512},
        {"checkpoint_every":500},
    ):
        with pytest.raises(ValueError):
            BroadConfig(**spec)
