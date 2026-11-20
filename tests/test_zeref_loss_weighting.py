"""2026-11-19 no-promotion fix: row-weighted loss option in the 006 grouped backward (default unchanged)."""
import sys
import pytest
torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
sys.path[:0] = ["models", "scripts", "."]


def _setup(monkeypatch, mode):
    if mode is None:
        monkeypatch.delenv("ZEREF_006_LOSS_WEIGHTING", raising=False)
    else:
        monkeypatch.setenv("ZEREF_006_LOSS_WEIGHTING", mode)
    sys.modules.pop("zeref_continuation_006", None)
    import zeref_continuation_006 as Z
    from rawrphos.architecture.model import RawrphosLM, RawrphosConfig
    torch.manual_seed(0)
    m = RawrphosLM(RawrphosConfig(vocab_size=64, d_model=32, n_layers=2, n_heads=2, max_seq_len=32))
    # one long row (20 supervised tokens) and two short chat-like rows (2 and 3 supervised tokens)
    batch = [{"input": list(range(1, 21)), "target": list(range(2, 22))},
             {"input": [3, 4, 5, 6], "target": [-100, -100, 7, 8]},
             {"input": [5, 6, 7, 8, 9], "target": [-100, -100, 10, 11, 12]}]
    return Z, m, batch


def _manual(m, batch, mode):
    F = torch.nn.functional
    per, toks = [], []
    for r in batch:
        lg = m(torch.tensor([r["input"]]))["logits"][0].float()
        y = torch.tensor(r["target"])
        ce = F.cross_entropy(lg, y, ignore_index=-100, reduction="sum")
        n = int((y != -100).sum())
        per.append(ce / n); toks.append((ce, n))
    if mode == "row":
        return sum(per) / len(per)
    return sum(c for c, _ in toks) / sum(n for _, n in toks)


@pytest.mark.parametrize("mode", [None, "token", "row"])
def test_grouped_backward_matches_the_named_weighting(monkeypatch, mode):
    Z, m, batch = _setup(monkeypatch, mode)
    assert Z.LOSS_WEIGHTING == (mode or "token")  # default stays the old token-mean
    x, y, mask = Z.collate(batch)
    m.zero_grad(); Z.grouped_backward(m, batch, y, mask, 0, None)
    g1 = [p.grad.clone() for p in m.parameters() if p.grad is not None]
    m.zero_grad(); _manual(m, batch, mode or "token").backward()
    g2 = [p.grad.clone() for p in m.parameters() if p.grad is not None]
    assert len(g1) == len(g2) and all(torch.allclose(a, b, atol=1e-5, rtol=1e-4) for a, b in zip(g1, g2))


def test_row_weighting_gives_short_rows_their_share(monkeypatch):
    Z, m, batch = _setup(monkeypatch, "row")
    tok, row = _manual(m, batch, "token"), _manual(m, batch, "row")
    assert not torch.isclose(tok, row)  # the two objectives really differ on mixed lengths


def test_unknown_weighting_is_refused(monkeypatch):
    monkeypatch.setenv("ZEREF_006_LOSS_WEIGHTING", "bogus")
    sys.modules.pop("zeref_continuation_006", None)
    with pytest.raises(ValueError):
        import zeref_continuation_006  # noqa: F401
