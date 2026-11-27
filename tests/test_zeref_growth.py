"""Tests for scripts.zeref_growth: deterministic function-preserving growth.

Pure standard library plus pytest. No torch on this box: the state dicts
here are small synthetic nested-list states built with the exact key names
and shapes of models/rawrphos/architecture/model.py, with deterministic
values from a fixed seed, so every check runs locally.
"""
import json
import math
import random

import pytest

from scripts import zeref_growth as growth

VOCAB = 8
D_MODEL = 4
N_LAYERS = 2
N_HEADS = 2
CONFIG = {
    "vocab_size": VOCAB,
    "d_model": D_MODEL,
    "n_layers": N_LAYERS,
    "n_heads": N_HEADS,
    "state_mode": "tri",
    "cond54": True,
    "cond54_direct": True,
    "hebbian": False,
    "hebbian_dim": 32,
}
LIVE_CONFIG = {
    "vocab_size": 4096,
    "d_model": 256,
    "n_layers": 44,
    "n_heads": 4,
    "state_mode": "tri",
    "cond54": True,
    "cond54_direct": True,
    "hebbian": False,
    "hebbian_dim": 32,
}


def _rand_matrix(rng, rows, cols):
    return [[rng.uniform(-0.5, 0.5) for _ in range(cols)] for _ in range(rows)]


def _rand_vector(rng, size):
    return [rng.uniform(-0.5, 0.5) for _ in range(size)]


def make_state(seed=1234, config=None):
    """Small synthetic state dict with model.py key names and shapes."""
    cfg = dict(CONFIG if config is None else config)
    rng = random.Random(seed)
    d = cfg["d_model"]
    hidden = growth.hidden_width(d)
    state = {}
    state["token.weight"] = _rand_matrix(rng, cfg["vocab_size"], d)
    state["state_init.weight"] = _rand_matrix(rng, 12, d)
    state["state_init.bias"] = _rand_vector(rng, 12)
    state["norm.weight"] = _rand_vector(rng, d)
    if cfg["state_mode"] == "tri":
        state["state_init42.weight"] = _rand_matrix(rng, 42, d)
        state["state_init42.bias"] = _rand_vector(rng, 42)
    if cfg["cond54"]:
        state["cond_gain"] = [0.0] * 54
    if cfg["cond54_direct"]:
        state["cond_in.weight"] = [[0.0] * 54 for _ in range(d)]
    for i in range(cfg["n_layers"]):
        p = "blocks.%d." % i
        state[p + "n1.weight"] = _rand_vector(rng, d)
        state[p + "n2.weight"] = _rand_vector(rng, d)
        state[p + "attn.qkv.weight"] = _rand_matrix(rng, 3 * d, d)
        state[p + "attn.qkv.bias"] = _rand_vector(rng, 3 * d)
        state[p + "attn.proj.weight"] = _rand_matrix(rng, d, d)
        state[p + "attn.proj.bias"] = _rand_vector(rng, d)
        state[p + "attn.gate_logit"] = -2.0
        state[p + "attn.log_sigma"] = -1.6
        state[p + "ffn.0.weight"] = _rand_matrix(rng, hidden, d)
        state[p + "ffn.0.bias"] = _rand_vector(rng, hidden)
        state[p + "ffn.2.weight"] = _rand_matrix(rng, d, hidden)
        state[p + "ffn.2.bias"] = _rand_vector(rng, d)
        if i < cfg["n_layers"] - 1 and cfg["state_mode"] == "tri":
            state[p + "transition.k"] = _rand_vector(rng, 12)
            state[p + "transition.g12"] = _rand_vector(rng, 12)
            state[p + "transition.g42"] = _rand_vector(rng, 42)
            state[p + "transition.drive.weight"] = _rand_matrix(rng, 42, d)
            state[p + "transition.drive.bias"] = _rand_vector(rng, 42)
            state[p + "transition.C.weight"] = _rand_matrix(rng, 42, 42)
            state[p + "transition.m42_12.weight"] = _rand_matrix(rng, 12, 42)
            state[p + "transition.m12_42.weight"] = _rand_matrix(rng, 42, 12)
            state[p + "transition.lam"] = 0.5
    return state


def test_parameter_count_grows_with_depth():
    parent = make_state()
    grown, report = growth.grow_depth(parent, 2)
    assert report["parent_layers"] == 2
    assert report["grown_layers"] == 4
    assert report["grown_params"] > report["parent_params"]
    assert report["added_params"] == report["grown_params"] - report["parent_params"]
    assert growth.count_parameters(grown) == report["grown_params"]
    assert growth.count_parameters(parent) == 3921


def test_parameter_count_grows_with_width():
    parent = make_state()
    grown, new_config, report = growth.grow_width(parent, CONFIG, 8)
    assert new_config["d_model"] == 8
    assert new_config["n_heads"] == 4
    assert report["grown_params"] > report["parent_params"]
    assert report["added_params"] == report["grown_params"] - report["parent_params"]
    assert growth.count_parameters(grown) == report["grown_params"]


def test_analytic_count_matches_live_shape():
    # vocab 4096, d_model 256, 44 layers, tri, cond54, cond54_direct.
    assert growth.parameter_count_for_config(**LIVE_CONFIG) == 22620887
    # Within 0.1 percent of the 22.64M figure quoted for the live pin.
    assert abs(22620887 - 22640000) / 22640000 < 0.001
    # Analytic count agrees with the explicit synthetic state count.
    assert growth.parameter_count_for_config(**CONFIG) == growth.count_parameters(make_state())


def test_depth_growth_preserves_outputs_at_init():
    parent = make_state()
    probe = [0.3, -0.7, 1.1, 0.2]
    grown, _ = growth.grow_depth(parent, 2)
    report = growth.parity_check(parent, grown, "depth", probe)
    assert report["passed"]
    assert all(c["passed"] for c in report["checks"])
    # Parent tensors are byte-identical in the grown state.
    for key in parent:
        assert grown[key] == parent[key]
    # Each new block is numerically an identity residual on the probe.
    assert growth.new_block_is_identity(grown, 2, probe)
    assert growth.new_block_is_identity(grown, 3, probe)


def test_width_growth_preserves_outputs_at_init():
    parent = make_state()
    probe = [0.3, -0.7, 1.1, 0.2]
    grown, new_config, _ = growth.grow_width(parent, CONFIG, 8)
    report = growth.parity_check(parent, grown, "width", probe, CONFIG, new_config)
    assert report["passed"]
    assert all(c["passed"] for c in report["checks"])
    by_name = {c["name"]: c for c in report["checks"]}
    assert by_name["logits_path_numeric_parity"]["status"] == "MEASURED"
    assert by_name["ffn_branch_numeric_parity"]["status"] == "MEASURED"
    assert by_name["attention_width_parity_by_padding"]["status"] == "STRUCTURAL"


def test_growth_is_deterministic():
    parent = make_state()
    grown_a, _ = growth.grow_depth(parent, 2)
    grown_b, _ = growth.grow_depth(parent, 2)
    assert grown_a == grown_b
    assert growth.canonical_hash(grown_a) == growth.canonical_hash(grown_b)
    wide_a, _, _ = growth.grow_width(parent, CONFIG, 8)
    wide_b, _, _ = growth.grow_width(parent, CONFIG, 8)
    assert wide_a == wide_b
    assert growth.canonical_hash(wide_a) == growth.canonical_hash(wide_b)
    # Growing does not mutate the parent.
    assert growth.canonical_hash(parent) == growth.canonical_hash(make_state())


def test_depth_growth_copies_transition_to_old_final_block():
    parent = make_state()
    assert "blocks.1.transition.k" not in parent
    grown, report = growth.grow_depth(parent, 1)
    assert "blocks.1.transition.k" in grown
    assert grown["blocks.1.transition.k"] == parent["blocks.0.transition.k"]
    assert "blocks.1.transition.k" in report["fresh_keys"]


def test_invalid_growth_requests_fail_cleanly():
    parent = make_state()
    with pytest.raises(ValueError):
        growth.grow_depth(parent, 0)
    with pytest.raises(ValueError):
        growth.grow_depth(parent, -1)
    with pytest.raises(ValueError):
        growth.grow_depth(parent, 2.0)
    with pytest.raises(ValueError):
        growth.grow_depth({}, 1)
    with pytest.raises(ValueError):
        growth.grow_depth({"token.weight": [[1.0]]}, 1)
    with pytest.raises(ValueError):
        growth.grow_width(parent, CONFIG, 4)
    with pytest.raises(ValueError):
        growth.grow_width(parent, CONFIG, 2)
    with pytest.raises(ValueError):
        growth.grow_width(parent, CONFIG, 7)
    with pytest.raises(ValueError):
        growth.grow_width(parent, CONFIG, 8, new_n_heads=2)
    with pytest.raises(ValueError):
        growth.grow_width(parent, CONFIG, 8, new_n_heads=3)
    with pytest.raises(ValueError):
        growth.grow_width(parent, CONFIG, 5)
    with pytest.raises(ValueError):
        growth.grow_width({"token.weight": [[1.0]]}, CONFIG, 8)
    broken = make_state()
    broken["blocks.0.ffn.0.weight"] = [[1.0]]
    with pytest.raises(ValueError):
        growth.grow_width(broken, CONFIG, 8)
    with pytest.raises(ValueError):
        growth.parameter_count_for_config(vocab_size=8, d_model=5, n_layers=2, n_heads=2)
    with pytest.raises(ValueError):
        growth.parity_check(parent, parent, "sideways", [1.0] * 4)


def test_width_norm_rescale_factor():
    parent = make_state()
    grown, _, report = growth.grow_width(parent, CONFIG, 8)
    assert report["norm_rescale"] == pytest.approx(math.sqrt(4 / 8))
    expected = [v * math.sqrt(4 / 8) for v in parent["norm.weight"]]
    assert grown["norm.weight"][:4] == pytest.approx(expected)
    assert grown["norm.weight"][4:] == [0.0] * 4


def test_grown_state_round_trips_through_json():
    parent = make_state()
    grown, _ = growth.grow_depth(parent, 1)
    blob = json.dumps(grown, sort_keys=True)
    assert growth.canonical_hash(json.loads(blob)) == growth.canonical_hash(grown)


def test_module_has_no_em_dash():
    import pathlib
    source = pathlib.Path(growth.__file__).read_text(encoding="utf-8")
    assert "\u2014" not in source
    assert "\u2014" not in pathlib.Path(__file__).read_text(encoding="utf-8")
