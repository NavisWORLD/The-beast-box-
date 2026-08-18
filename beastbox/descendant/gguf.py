"""Truthful metadata helpers for descendant GGUF export."""

from __future__ import annotations

from typing import Mapping


def provenance_metadata(checkpoint: Mapping[str, object]) -> dict[str, object]:
    return {
        "d001.stage": str(checkpoint.get("stage") or "UNKNOWN"),
        "d001.parent_prime_gguf_sha256": str(checkpoint.get("parent_prime_gguf_sha256") or checkpoint.get("parent_gguf_sha256") or "unknown"),
        "d001.parent_checkpoint_sha256": str(checkpoint.get("parent_checkpoint_sha256") or "unknown"),
        "d001.quantum_source": str(checkpoint.get("quantum_source") or "unknown"),
        "d001.historical_optimizer_continuity": bool(checkpoint.get("historical_optimizer_continuity", False)),
    }


def build_description(checkpoint: Mapping[str, object]) -> str:
    stage = str(checkpoint.get("stage") or "UNKNOWN")
    quantum_source = str(checkpoint.get("quantum_source") or "unknown")
    base = (
        f"COSMOS/Zeref D001 {stage}: 54D mixture-of-states Hebbian attention, "
        "continued from the canonical trainable reconstruction of immutable Zeref Prime. "
        "Requires a llama.cpp runtime implementing LLM_ARCH_COSMOS. "
    )
    if quantum_source in {"unknown", "unknown_from_prime_artifact"}:
        return base + "Quantum provenance unknown from the Prime artifact; no hardware-origin claim is made by this GGUF."
    return base + f"Quantum provenance label: {quantum_source}; consult the external evidence manifest for its proof scope."
