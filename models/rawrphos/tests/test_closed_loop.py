import sys, math, torch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rawrphos.architecture.model import RawrphosConfig, RawrphosLM
from rawrphos.architecture.closed_loop import attach_closed_loop, load_chsh, BellSource, MODES

def _m():
    torch.manual_seed(0); return RawrphosLM(RawrphosConfig(vocab_size=64, d_model=32, n_heads=2, n_layers=2, max_seq_len=64, attention_mode="standard"))

def test_off_is_bit_identical():
    m = _m(); x = torch.randint(64, (2, 10)); a = m(x)["logits"].clone(); attach_closed_loop(m, "off"); assert torch.equal(a, m(x)["logits"])

def test_all_modes_finite_and_trainable():
    for mode in MODES[1:]:
        m = _m(); attach_closed_loop(m, mode); x = torch.randint(64, (3, 12)); out = m(x, targets=x)
        assert torch.isfinite(out["logits"]).all(); out["loss"].backward()
        assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in m.closed_loop.parameters())

def test_chsh_source_labelled_and_controls_bounded():
    c = load_chsh(); assert c["job_id"] == "db8iu85ckpjs73b13msg" and c["label"] == "REAL IBM QUANTUM HARDWARE RUN"
    rec = BellSource(c, "recorded"); assert rec.S > 2.5
    assert BellSource(c, "lhv").lhv_S() <= 2 + 1e-9
    E = []
    for s in range(4):
        b = BellSource(c, "recorded"); E.append(float(b(torch.full((1024,), s)).mean()))
    assert abs((E[0] + E[1] + E[2] - E[3]) - rec.S) < 1e-6
