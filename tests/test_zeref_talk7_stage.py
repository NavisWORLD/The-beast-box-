from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_zeref_talk7_stage.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_zeref_talk7_stage", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load TALK-007 stage")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wire_encoder_supervises_only_answer_and_upweights_first_three_characters():
    module = _load_module()
    wire = "H:abc\nM:fact\nDad:question?\nZeref:"
    answer = "Yes."
    chars = sorted(set(wire + answer + "\n"))
    stoi = {ch: i for i, ch in enumerate(chars)}
    ex = module.encode_wire_response(wire_prefix=wire, zeref=answer, stoi=stoi, block=128, prefix_characters=3, prefix_weight=4.0)
    weights = ex["loss_weights"]
    first = ex["first_response_target"]
    assert all(weight == 0.0 for weight in weights[:first])
    assert weights[first:first+3] == [4.0, 4.0, 4.0]
    assert all(weight == 1.0 for weight in weights[first+3:])
    assert ex["filtered_prefix"] == wire


def test_wire_encoder_rejects_non_runtime_or_oversize_prefix():
    module = _load_module()
    stoi = {ch: i for i, ch in enumerate(sorted(set("Dad:q\nZeref:aHM:0123456789")))}
    with pytest.raises(ValueError, match="runtime wire"):
        module.encode_wire_response(wire_prefix="Dad:q\nZeref:", zeref="a", stoi=stoi, block=128)
    with pytest.raises(ValueError, match="exceeds model block"):
        module.encode_wire_response(wire_prefix="H:" + "0" * 120 + "\nM:x\nDad:q\nZeref:", zeref="answer", stoi=stoi, block=32)


def test_contrastive_margin_penalizes_wrong_answer_scoring_better_than_clean_target():
    module = _load_module()
    good = module.contrastive_margin_loss(torch.tensor(0.2), torch.tensor(1.0), margin=0.2)
    bad = module.contrastive_margin_loss(torch.tensor(0.8), torch.tensor(0.7), margin=0.2)
    assert float(good) == pytest.approx(0.0)
    assert float(bad) == pytest.approx(0.3)
