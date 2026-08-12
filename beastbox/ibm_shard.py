from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .quantum import majority_decode, retrieve_pub_counts, submit_real_chunks
from .shard_transport import SealedShard, chunks_to_key, continuity_score, key_to_chunks, prepare_required_shard, recover_required_shard


def submit_required_state(
    state: dict[str, Any],
    required_fields: list[str],
    *,
    shots: int = 1024,
    chunk_bits: int = 8,
    backend_name: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Prepare sealed mission state and submit only the ephemeral key bits to IBM.

    Returned receipt deliberately contains no plaintext key. The caller should
    persist this receipt and end the submitting process before recovery.
    """
    artifact, key = prepare_required_shard(state, required_fields, key_bytes=16)
    chunks = key_to_chunks(key, chunk_bits=chunk_bits)
    ibm = submit_real_chunks(chunks, shots=shots, backend_name=backend_name, confirm=confirm)
    receipt = {
        "schema": "beastbox.ibm-required-state.v1",
        "required_fields": list(required_fields),
        "chunk_bits": chunk_bits,
        "sealed_shard": artifact.to_dict(),
        "ibm": ibm.to_dict(),
        "plaintext_key_persisted": False,
    }
    # Python cannot promise cryptographic RAM erasure. The benchmark guarantee
    # is narrower: no plaintext key is written into this returned/persisted receipt.
    key = b""
    return receipt


def recover_required_state(receipt: dict[str, Any]) -> dict[str, Any]:
    if receipt.get("schema") != "beastbox.ibm-required-state.v1":
        raise ValueError("unsupported IBM shard receipt")
    job_id = str(receipt["ibm"]["ibm_native_job_id"])
    width = int(receipt["chunk_bits"])
    pubs = retrieve_pub_counts(job_id)
    expected_pubs = int(receipt["ibm"]["pubs"])
    if len(pubs) != expected_pubs:
        raise ValueError(f"PUB count mismatch: expected {expected_pubs}, got {len(pubs)}")
    decoded = [majority_decode(counts, width) for counts in pubs]
    key = chunks_to_key(decoded)
    artifact = SealedShard(**receipt["sealed_shard"])
    state = recover_required_shard(artifact, key)
    score = continuity_score(state, list(receipt["required_fields"]))
    return {
        "state": state,
        "continuity_score": score,
        "decoded_chunks": decoded,
        "key_commitment_match": True,
        "ibm_native_job_id": job_id,
        "pubs_retrieved": len(pubs),
    }


def write_receipt(path: str | Path, receipt: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
