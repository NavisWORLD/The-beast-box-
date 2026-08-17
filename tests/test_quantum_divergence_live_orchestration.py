from __future__ import annotations

from beastbox.box import DENIED
from beastbox.quantum_divergence.live_cli import build_live_box, build_live_spec, build_resume_receipt


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


def test_resume_receipt_preserves_original_hardware_provenance():
    receipt = build_resume_receipt(
        job_id="da1l0maein7c73bdi2d0",
        backend="ibm_marrakesh",
        shots=2048,
        circuit_sha256="8ccea7c430e7e42a664d92ce99f8b8107b1983f2e5710e2763aef9c3458c4c85",
    )
    assert receipt.job_id == "da1l0maein7c73bdi2d0"
    assert receipt.backend == "ibm_marrakesh"
    assert receipt.shots == 2048
    assert receipt.circuit_sha256 == "8ccea7c430e7e42a664d92ce99f8b8107b1983f2e5710e2763aef9c3458c4c85"
    assert receipt.pubs == 1
