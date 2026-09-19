from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "d001-quantum-provenance-audit.yml"


def test_quantum_provenance_audit_is_pinned_read_only_and_conservative():
    assert WORKFLOW.exists(), "quantum provenance audit workflow must exist"
    text = WORKFLOW.read_text(encoding="utf-8")
    lower = text.lower()

    # Exact immutable source identities.
    assert "phera-ra/QC67_cosmo" in text
    assert "b414724c627300c41b099dcc6853766d08fd27a4" in text
    assert "NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2" in text
    assert "dddb1325b90c9abbe8da77974874e5770623035e" in text

    # Frozen HF evidence files from the Prime snapshot.
    assert "data/quantum_measurements_manifest.json" in text
    assert "data/quantum_measurements_public.jsonl" in text
    assert "data/training/quantum_train_summary_20260722.json" in text

    # Repo-native IBM workload exports are independently inventoried.
    assert "workloads (4)" in text
    assert "-info.json" in text
    assert "-result.json" in text
    assert "ibm_fez" in text

    # Provenance classes and evidence fields must be explicit.
    for token in (
        "hardware",
        "simulator",
        "unknown",
        "fixed_seed",
        "prng_control",
        "provider",
        "backend",
        "job_id",
        "shots",
        "source_sha256",
        "raw_evidence_sha256",
    ):
        assert token in lower

    # A completed IBM job can be hardware evidence only when backend/job/result
    # provenance is present; a sibling checkpoint label is never inherited by Prime.
    assert "spark_cst.pt" in text
    assert "do_not_inherit_checkpoint_quantum_label" in text
    assert "unknown_from_prime_artifact" in text

    # Read-only sources, artifact-only output.
    assert "contents: read" in lower
    assert "persist-credentials: false" in lower
    assert "upload-artifact" in lower
    assert "git push" not in lower
    assert "upload_file" not in lower
    assert "hf_api.create" not in lower
