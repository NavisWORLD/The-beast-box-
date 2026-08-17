from __future__ import annotations

from typing import Any


REQUIRED_GATES = (
    "zero_state_identity",
    "mechanism_live",
    "arm_isolation",
    "sensor_freshness",
    "ibm_provenance_verified",
    "full_action_coverage",
    "hard_containment",
    "evidence_chain_valid",
    "prompts_frozen_across_arms",
)


def failed_gates(manifest: dict[str, Any]) -> list[str]:
    return [name for name in REQUIRED_GATES if manifest.get(name) is not True]


def validate_manifest(manifest: dict[str, Any]) -> None:
    failed = failed_gates(manifest)
    if failed:
        raise ValueError("Trinity final verification gates failed: " + ", ".join(failed))
    if manifest.get("credential_persisted") is not False:
        raise ValueError("credential persistence must be false")
    if manifest.get("state_prompt_decoration") is not False:
        raise ValueError("state prompt decoration must be false")
    if manifest.get("native_state_injection") is not True:
        raise ValueError("native state injection must be true")
    if manifest.get("dyn54_semantics") != "dyn12-concatenated-with-dyn42":
        raise ValueError("dyn54 semantics must remain dyn12 concatenated with dyn42")
    projections = manifest.get("projection_hashes") or {}
    state_hashes = projections.get("state") or {}
    native_hashes = projections.get("native") or {}
    if not state_hashes or not native_hashes:
        raise ValueError("projection hashes are incomplete")
    for group_name, group in (("state", state_hashes), ("native", native_hashes)):
        for name, digest in group.items():
            if not isinstance(digest, str) or len(digest) != 64:
                raise ValueError(f"invalid {group_name} projection hash {name}")
