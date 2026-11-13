"""12D into the mouth, training side: pairing receipt, text dropout, gain floor; flag default off."""
import json
import sys

import pytest

torch = pytest.importorskip("torch"); pytest.importorskip("safetensors")
sys.path[:0] = ["models", "scripts"]
import zeref_mouth12_train as M12  # noqa: E402

STATE = [0.12, -0.34, 0.5, 0.0, -1.7, 0.2, 0.3, -0.7, 0.05, 0.11, -0.22, 0.33]


def _desc(state):
    return json.dumps({"schema": "lived-state-descriptor-v1", "basis": "dyn12-v1", "sequence": 3, "state12": state})


def _enc(text, add_bos=False, add_eos=False):
    ids = [b % 64 for b in text.encode()]
    return ([1] if add_bos else []) + ids + ([2] if add_eos else [])


def _row():
    return {"mode": "chat", "served_shape": True, "user": "hi", "assistant": "purr",
            "messages": [{"role": "system", "content": _desc(STATE)},
                         {"role": "system", "content": "You are Zeref."},
                         {"role": "user", "content": "hi"}]}


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv("ZEREF_12D_MOUTH", raising=False)
    assert M12.enabled() is False
    import zeref_continuation_006 as Z
    assert Z.MOUTH12 is False and Z.MOUTH12_INFO == {}


def test_row_is_paired_with_its_own_descriptor_state_and_has_a_hidden_variant():
    ex = M12.encode_row(_enc, _row(), limit=4096)
    assert ex["state12"] == STATE
    assert M12.condition54(ex["state12"])[:12] == [max(-1, min(1, x)) for x in STATE]
    assert M12.condition54(ex["state12"])[12:] == [0.0] * 42
    assert len(ex["hidden"]["input"]) < len(ex["input"])
    assert ex["hidden"]["target"][-len(_enc(" purr", add_eos=True)):] == _enc(" purr", add_eos=True)


def test_rows_without_state_are_untouched():
    row = {"mode": "chat", "user": "hi", "assistant": "purr"}
    ex = M12.encode_row(_enc, row, limit=4096)
    assert "state12" not in ex and M12.pool_entry(ex).get("state12") is None


def test_dropout_hides_text_keeps_tensor_and_tallies():
    entry = M12.pool_entry(M12.encode_row(_enc, _row(), limit=4096))
    g = torch.Generator().manual_seed(7); tally = {}
    out = M12.apply_dropout([entry] * 200 + [{"input": [1], "target": [2]}], g, 0.5, tally)
    hidden = sum(1 for r in out if r.get("_text_hidden"))
    assert tally["state_rows"] == 200 and tally["tensor_only_rows"] == hidden and 60 < hidden < 140
    conds = M12.condition_rows(out, lambda j: [0.0] * 54)
    assert all(c[:12] == M12.condition54(STATE)[:12] for c in conds[:200]) and conds[200] == [0.0] * 54
    assert M12.apply_dropout([entry], torch.Generator().manual_seed(7), 0.0, {})[0]["input"] == entry["input"]


def test_gain_floor_keeps_sign_and_lifts_zeros():
    class M: pass
    m = M(); m.cond_gain = torch.nn.Parameter(torch.zeros(54))
    m.cond_gain.data[3] = -0.01; m.cond_gain.data[7] = 0.243; m.cond_gain.data[20] = 0.0
    after = M12.floor_gain(m, 0.25)
    assert after[0] == 0.25 and after[3] == -0.25 and after[7] == 0.25
    m.cond_gain.data[7] = 0.9; assert M12.floor_gain(m, 0.25)[7] == 0.9
    assert float(m.cond_gain.data[20]) == 0.0  # band slots untouched


def test_floored_gain_makes_the_state_reach_the_logits():
    from rawrphos.architecture.model import RawrphosConfig, RawrphosLM, upgrade_to_cond54, upgrade_to_trinity
    torch.manual_seed(0)
    m = upgrade_to_cond54(upgrade_to_trinity(RawrphosLM(RawrphosConfig.from_dict(
        {"vocab_size": 64, "d_model": 32, "n_layers": 2, "n_heads": 2, "max_seq_len": 16}))))
    x = torch.randint(0, 64, (1, 8)); c = torch.tensor([M12.condition54(STATE)])
    z = torch.zeros(1, 54)
    with torch.no_grad():
        same = (m(x, condition54=c)["logits"] - m(x, condition54=z)["logits"]).abs().max()
        M12.floor_gain(m, 0.25)
        moved = (m(x, condition54=c)["logits"] - m(x, condition54=z)["logits"]).abs().max()
    assert float(same) == 0.0 and float(moved) > 0.0
