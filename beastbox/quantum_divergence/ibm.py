from __future__ import annotations

from typing import Any

from beastbox.quantum import retrieve_pub_counts

from .entropy import EntropyReceipt, quantum_entropy_from_counts


def merge_pub_counts(pubs: list[dict[str, int]]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for counts in pubs:
        for key, value in counts.items():
            bitstring = str(key).replace(" ", "")
            merged[bitstring] = merged.get(bitstring, 0) + int(value)
    return merged


def load_real_ibm_entropy(receipt: dict[str, Any], dimensions: int = 12) -> EntropyReceipt:
    job_id = str(receipt.get("ibm_native_job_id", ""))
    if not job_id:
        raise ValueError("IBM receipt is missing ibm_native_job_id")
    pubs = retrieve_pub_counts(job_id)
    if not pubs:
        raise ValueError("IBM job returned no measurement counts")
    return quantum_entropy_from_counts(merge_pub_counts(pubs), receipt, dimensions)
