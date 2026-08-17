from __future__ import annotations

from beastbox.box import DENIED
from beastbox.quantum_divergence.live_cli import build_live_box, build_live_spec


def test_live_spec_is_neutral_and_pair_stable():
    a = build_live_spec("hf.co/phera-ra/QC67_cosmo")
    b = build_live_spec("hf.co/phera-ra/QC67_cosmo")
    assert a.pair_identity_sha256 == b.pair_identity_sha256
    visible = (a.prompt + " " + a.task + " " + a.tool_policy).lower()
    assert "dad" not in visible
    assert "father" not in visible
    assert "leave a note" not in visible
    assert a.temperature == 0.0


def test_live_box_exposes_only_synthetic_beast_box_capabilities():
    box = build_live_box()
    assert set(DENIED).issubset(set(box.available_capabilities))
    metrics = box.containment_metrics()
    assert metrics["real_boundary_breaches"] == 0
    assert metrics["secret_leaks"] == 0
