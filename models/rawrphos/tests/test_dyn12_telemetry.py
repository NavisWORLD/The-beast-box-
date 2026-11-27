"""dyn12 mouth telemetry (2026-11-23): measure the 12D path at the injection point; never change behavior.

R = ||dyn12_path||_2 / ||text_path||_2 at the cond54_direct injection (model.py forward):
text_path is the token stream x at the last input position before the addition, dyn12_path is
what cond_in adds there. The H1 probe at pin 43504 measured the tensor path ~220,000x weaker
than the text path; this telemetry moves that claim from IMPLEMENTED to MEASURED by recording R
per live turn. It measures the direct path only, not the routed cond_gain path.
"""
import math

import torch
from rawrphos.architecture.model import (RawrphosConfig, RawrphosLM, upgrade_to_trinity, upgrade_to_hebbian,
                                         upgrade_to_cond54, upgrade_to_cond54_direct)


def small(**kw):
    torch.manual_seed(0)
    return RawrphosLM(RawrphosConfig(vocab_size=64, d_model=32, n_heads=2, n_layers=3, max_seq_len=64, **kw)).eval()


def ids(): return torch.randint(0, 64, (1, 12), generator=torch.Generator().manual_seed(1))


def cond(): return torch.tensor([[((i * 7) % 13 - 6) / 7 for i in range(54)]])


def direct():
    return upgrade_to_cond54_direct(upgrade_to_cond54(upgrade_to_hebbian(upgrade_to_trinity(small())))).eval()


def tel(m):
    return getattr(m, "_dyn12_telemetry", None)


def test_telemetry_records_nonzero_finite_ratio():
    d = direct(); x = ids(); c = cond()
    with torch.no_grad():
        d.cond_in.weight.normal_(0, .05)
        d(x, condition54=c)
    t = tel(d)
    assert t is not None and t["schema"] == "zeref-dyn12-telemetry-v1" and t["condition54_sent"] is True
    for key in ("prefill", "last"):
        m = t[key]
        assert m is not None
        assert m["text_path_l2"] > 0 and m["dyn12_path_l2"] > 0
        assert math.isfinite(m["ratio_R"]) and m["ratio_R"] > 0
        assert math.isfinite(m["condition54_l2"]) and m["condition54_l2"] > 0
        assert math.isfinite(m["cond_in_weight_l2"]) and m["cond_in_weight_l2"] > 0
    # Single forward: prefill and last are the same measurement.
    assert t["prefill"] == t["last"]
    # The recorded norms match an independent recomputation from the same weights.
    with torch.no_grad():
        expect_text = float(d.token(x)[:, -1, :].norm(2).item())
        expect_dyn = float(d.cond_in(c).norm(2).item())
    assert t["last"]["text_path_l2"] == expect_text
    assert t["last"]["dyn12_path_l2"] == expect_dyn
    assert t["last"]["ratio_R"] == expect_dyn / max(expect_text, 1e-12)


def test_zero_condition_gives_zero_ratio():
    d = direct(); x = ids()
    with torch.no_grad():
        d.cond_in.weight.normal_(0, .05)
        d(x, condition54=torch.zeros(1, 54))
    m = tel(d)["last"]
    assert m["condition54_l2"] == 0.0 and m["dyn12_path_l2"] == 0.0 and m["ratio_R"] == 0.0
    assert m["cond_in_weight_l2"] > 0  # weights moved; the input was zero


def test_zero_weights_give_zero_ratio():
    d = direct(); x = ids()  # cond_in is zero-initialised at upgrade: weights never moved
    with torch.no_grad():
        assert float(d.cond_in.weight.norm(2).item()) == 0.0
        d(x, condition54=cond())
    m = tel(d)["last"]
    assert m["condition54_l2"] > 0 and m["cond_in_weight_l2"] == 0.0
    assert m["dyn12_path_l2"] == 0.0 and m["ratio_R"] == 0.0


def test_no_condition54_records_nothing():
    d = direct(); x = ids()
    with torch.no_grad():
        d(x)
    assert tel(d) is None


def test_telemetry_does_not_change_logits():
    d = direct(); x = ids(); c = cond()
    with torch.no_grad():
        d.cond_in.weight.normal_(0, .05)
        a = d(x, condition54=c)["logits"]
        b = d(x, condition54=c)["logits"]
    assert torch.equal(a, b)


def _direct_checkpoint(tmp_path):
    """Tiny cond54_direct checkpoint with non-zero cond_in weights (a moved-weights brain)."""
    from rawrphos.tokenizer.tokenizer import RawrphosTokenizer
    from rawrphos.training.checkpoint import rng_state, save_checkpoint
    t = RawrphosTokenizer.train(['The little cat sat on a warm mat.'] * 10, 300)
    torch.manual_seed(8)
    m = RawrphosLM(RawrphosConfig(vocab_size=t.vocab_size, d_model=32, n_heads=4, n_layers=2,
                                  max_seq_len=512, state_mode='tri'))
    m = upgrade_to_cond54_direct(upgrade_to_cond54(upgrade_to_hebbian(upgrade_to_trinity(m))))
    with torch.no_grad():
        m.cond_in.weight.normal_(0, .05)
    p = tmp_path / 'dyn12'
    save_checkpoint(p, m, t, {'training_steps': 1, 'training_tokens': 8, 'training_seq_len': 8,
                              'release_status': 'test-fixture-trained', 'hardware': {'device': 'cpu'}},
                    {'rng': rng_state()})
    return p


def test_server_receipt_carries_telemetry(tmp_path):
    """End to end: model -> engine -> server receipt. With condition54, R is non-zero and finite;
    without it, the receipt says condition54_sent False with nulls (the drop, stated plainly)."""
    from fastapi.testclient import TestClient
    from rawrphos.inference.server import create_app
    key = 'test-key-' + 'x' * 32
    client = TestClient(create_app(_direct_checkpoint(tmp_path), key, max_new_tokens=8))
    auth = {'Authorization': 'Bearer ' + key}
    body = {'model': 'rawrphos-native', 'messages': [{'role': 'user', 'content': 'The cat'}],
            'max_tokens': 4, 'temperature': 0}
    plain = client.post('/v1/chat/completions', headers=auth, json=body)
    assert plain.status_code == 200
    t0 = plain.json()['dyn12_telemetry']
    assert t0['schema'] == 'zeref-dyn12-telemetry-v1' and t0['condition54_sent'] is False
    assert t0['prefill'] is None and t0['last'] is None
    cond = client.post('/v1/chat/completions', headers=auth,
                       json=dict(body, condition54=[0.1] * 12 + [0.0] * 42))
    assert cond.status_code == 200
    t1 = cond.json()['dyn12_telemetry']
    assert t1['condition54_sent'] is True and t1['prefill'] is not None and t1['last'] is not None
    assert math.isfinite(t1['last']['ratio_R']) and t1['last']['ratio_R'] > 0
    assert t1['last']['condition54_l2'] > 0 and t1['last']['cond_in_weight_l2'] > 0


def test_prefill_and_last_across_cached_steps():
    d = direct(); x = ids(); c = cond()
    with torch.no_grad():
        d.cond_in.weight.normal_(0, .05)
        out = d(x[:, :-1], condition54=c, use_cache=True)
        prefill = dict(tel(d)["prefill"])
        step = d(x[:, -1:], condition54=c, past_key_values=out["past_key_values"], use_cache=True,
                 attention_mask=torch.ones(1, x.shape[1], dtype=torch.bool))
    t = tel(d)
    assert t["prefill"] == prefill  # the turn's prefill is kept
    # The decode step overwrote last: its text norm is the one-token stream's, not the prefill's.
    with torch.no_grad():
        assert t["last"]["text_path_l2"] == float(d.token(x[:, -1:])[:, -1, :].norm(2).item())
        assert t["prefill"]["text_path_l2"] == float(d.token(x[:, :-1])[:, -1, :].norm(2).item())
    assert math.isfinite(t["last"]["ratio_R"]) and t["last"]["ratio_R"] > 0
    assert torch.allclose(step["logits"][:, -1],
                          d(x, condition54=c)["logits"][:, -1], atol=1e-5)
