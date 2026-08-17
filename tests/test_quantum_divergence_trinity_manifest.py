from __future__ import annotations

from beastbox.quantum_divergence.trinity_manifest import REQUIRED_GATES, failed_gates, validate_manifest


def _valid_manifest():
    payload = {name: True for name in REQUIRED_GATES}
    payload.update(
        {
            "credential_persisted": False,
            "state_prompt_decoration": False,
            "native_state_injection": True,
            "prompts_frozen_across_arms": True,
            "dyn54_semantics": "dyn12-concatenated-with-dyn42",
            "projection_hashes": {
                "state": {"12_to_42": "a" * 64},
                "native": {"native_trinity": "b" * 64},
            },
        }
    )
    return payload


def test_valid_manifest_has_no_failed_gates():
    manifest = _valid_manifest()
    assert failed_gates(manifest) == []
    validate_manifest(manifest)


def test_each_required_gate_is_enforced():
    for gate in REQUIRED_GATES:
        manifest = _valid_manifest()
        manifest[gate] = False
        assert gate in failed_gates(manifest)


def test_manifest_rejects_missing_projection_hashes():
    manifest = _valid_manifest()
    manifest["projection_hashes"] = {}
    try:
        validate_manifest(manifest)
    except ValueError as exc:
        assert "projection" in str(exc).lower()
    else:
        raise AssertionError("missing projection hashes must fail")


def test_manifest_rejects_credential_persistence_or_prompt_state_decoration():
    for key, value in (("credential_persisted", True), ("state_prompt_decoration", True)):
        manifest = _valid_manifest()
        manifest[key] = value
        try:
            validate_manifest(manifest)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{key}={value!r} must fail")
