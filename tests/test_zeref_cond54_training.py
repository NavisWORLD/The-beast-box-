"""cond54 training path: state paired with text rows, resume mapping, fair unconditioned gate."""
import json
import os
import sys
import pytest
torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
sys.path[:0] = ["models", "scripts", "."]


def _tick(i):
    counts = {"000": 40 + i, "001": 50, "010": 20, "011": 40 - i, "100": 20, "101": 30, "110": 26, "111": 30}
    return {"beast_id": "bb-deada969", "simulated": True, "status": "ok", "tick": i + 1, "at_epoch": 1.8e9 + 60 * i,
            "growth_source": {"target": "rigetti.sim.qvm", "counts": counts, "shots": sum(counts.values()), "job_id": f"j{i}"}}


@pytest.fixture()
def ticks_file(tmp_path):
    p = tmp_path / "ticks.jsonl"
    rows = [_tick(i) for i in range(6)]
    rows.insert(3, {"beast_id": "bb-deada969", "simulated": True, "status": "failed", "tick": 99})  # failed ticks are skipped
    p.write_text("\n".join(json.dumps(r) for r in rows))
    return str(p)


def test_ticks_become_routed_vectors_with_masked_zeros(ticks_file):
    from beastbox.spark_feed import load_ticks, tick_condition54
    ticks = load_ticks(ticks_file)
    assert [t["tick"] for t in ticks] == [1, 2, 3, 4, 5, 6]
    c = tick_condition54(ticks[0])
    v = c["cond54"]
    assert len(v) == 54 and all(-1 <= x <= 1 for x in v)
    assert any(v[12:18]) and not any(v[18:])  # only the quantum band is live; the rest is exactly 0.0
    assert c["tally"]["simulated"] > 0 and c["tally"]["missing"] > 0
    assert tick_condition54(ticks[0])["receipt_sha256"] == c["receipt_sha256"]  # deterministic


def test_bank_loads_and_ab_is_report_only(ticks_file, monkeypatch):
    monkeypatch.setenv("ZEREF_COND54", "1"); monkeypatch.setenv("ZEREF_SPARK_TICKS", ticks_file)
    sys.modules.pop("zeref_continuation_006", None)
    import zeref_continuation_006 as Z
    from rawrphos.architecture.model import RawrphosLM, RawrphosConfig, upgrade_to_trinity, upgrade_to_hebbian, upgrade_to_cond54
    bank = Z.cond54_bank()
    assert len(bank) == 6 and Z.COND_INFO["pairing"].startswith("by training-step time")
    torch.manual_seed(0)
    m = upgrade_to_hebbian(upgrade_to_trinity(RawrphosLM(RawrphosConfig(vocab_size=64, d_model=32, n_layers=2, n_heads=2, max_seq_len=16))))
    c = upgrade_to_cond54(m)
    rows = [{"input": [1, 2, 3, 4], "target": [-100, -100, 5, 6]}, {"input": [2, 3, 4, 5], "target": [-100, 4, 5, 6]}]
    ab = Z.cond54_ab(c, rows)
    assert ab["gain_nonzero_slots"] == 0  # zero gain at upgrade: every arm equals the unconditioned score
    assert abs(ab["real_ticks"] - ab["unconditioned"]) < 1e-5 and abs(ab["mismatched_ticks"] - ab["unconditioned"]) < 1e-5
    assert Z.cond54_ab(m, rows) is None  # model without cond54: no A/B


def test_optimizer_resume_maps_parent_state_after_cond54_upgrade():
    sys.modules.pop("zeref_continuation_006", None)
    import zeref_continuation_006 as Z
    from rawrphos.architecture.model import RawrphosLM, RawrphosConfig, upgrade_to_trinity, upgrade_to_hebbian, upgrade_to_cond54
    torch.manual_seed(0)
    p = upgrade_to_hebbian(upgrade_to_trinity(RawrphosLM(RawrphosConfig(vocab_size=64, d_model=32, n_layers=2, n_heads=2, max_seq_len=16))))
    opt = torch.optim.AdamW([{"params": p.base_parameters()}, {"params": p.hebbian_parameters()}], lr=1e-3)
    x = torch.randint(0, 64, (2, 8)); p(x, targets=x)["loss"].backward(); opt.step()
    names = {id(q): k for k, q in p.named_parameters()}
    meta = {"optimizer_group_param_names": [[names[id(q)] for q in g["params"]] for g in opt.param_groups]}
    c = upgrade_to_cond54(p)
    base, hebb = c.base_parameters(), c.hebbian_parameters()
    new = torch.optim.AdamW([{"params": base}, {"params": hebb}], lr=1e-3)
    out, log = Z.map_optimizer_state(opt.state_dict(), c, [base, hebb], meta, c)
    new.load_state_dict(out)
    assert log["layout"] == "saved_names"
    assert [g["fresh"] for g in log["groups"]] == [0, 1] and not any(g["reinitialized"] for g in log["groups"])  # only cond_gain is fresh
