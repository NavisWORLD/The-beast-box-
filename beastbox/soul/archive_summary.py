"""Versioned replay adapter for the published IBM Fez decode summary.

The nine records below are copied from the historical
NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2
`workload_decode_summary.json` artifact at commit
2bb40a0befd9b1023d91513eddd8447e730fce0b.

They are source-reported summaries produced by `scripts/decode_workloads.py`.
They are NOT raw RuntimeDecoder payloads, do not contain full count histograms,
and are never relabeled as fresh hardware execution. This adapter defines a new
replay schema for engineering integration only.
"""
from __future__ import annotations

from typing import Any

from ..hashutil import sha256_obj
from .token import SoulToken

SOURCE_REPO = "NavisWORLD/The-Cosmic-Davis-12D-Hebbian-Transformer-ver.4.2"
SOURCE_COMMIT = "2bb40a0befd9b1023d91513eddd8447e730fce0b"
SOURCE_PATH = "workload_decode_summary.json"
SOURCE_BLOB_SHA1 = "084282a26bf923f03188a2be4c36f3fb34b09987"
SCHEMA = "ibm-fez-published-decode-summary-replay-v1"

IBM_FEZ_REPORTED_SUMMARIES: tuple[dict[str, Any], ...] = (
    {"job_id":"d6p6l343pels73a3jvc0","backend":"ibm_fez","timestamp":"2026-03-12T07:26:04.725408Z","entropy":0.8387,"top_state":"00000","total_shots":4224},
    {"job_id":"d6p6l8gbfi7c73a6n73g","backend":"ibm_fez","timestamp":"2026-03-12T07:26:26.789195Z","entropy":0.8393,"top_state":"10000","total_shots":4224},
    {"job_id":"d6p6lpobfi7c73a6n7rg","backend":"ibm_fez","timestamp":"2026-03-12T07:27:35.424613Z","entropy":0.8397,"top_state":"11011","total_shots":4224},
    {"job_id":"d6p6m269td6c73aq5jl0","backend":"ibm_fez","timestamp":"2026-03-12T07:28:08.851242Z","entropy":0.8384,"top_state":"10001","total_shots":4224},
    {"job_id":"d6p6m6e9td6c73aq5jqg","backend":"ibm_fez","timestamp":"2026-03-12T07:28:25.867379Z","entropy":0.8387,"top_state":"00000","total_shots":4224},
    {"job_id":"d6p6mbgbfi7c73a6n8ig","backend":"ibm_fez","timestamp":"2026-03-12T07:28:46.480852Z","entropy":0.839,"top_state":"00001","total_shots":4224},
    {"job_id":"d6p6mfs3pels73a3k110","backend":"ibm_fez","timestamp":"2026-03-12T07:29:03.440359Z","entropy":0.8407,"top_state":"00001","total_shots":4224},
    {"job_id":"d6p6mlc3pels73a3k190","backend":"ibm_fez","timestamp":"2026-03-12T07:29:25.569955Z","entropy":0.8382,"top_state":"00000","total_shots":4224},
    {"job_id":"d6p6mrc3pels73a3k1f0","backend":"ibm_fez","timestamp":"2026-03-12T07:29:49.064776Z","entropy":0.8394,"top_state":"00000","total_shots":4224},
)


def _validated_record(index: int) -> dict[str, Any]:
    if type(index) is not int or not 0 <= index < len(IBM_FEZ_REPORTED_SUMMARIES):
        raise ValueError("archive summary index out of range")
    record = dict(IBM_FEZ_REPORTED_SUMMARIES[index])
    entropy = record["entropy"]
    top_state = record["top_state"]
    shots = record["total_shots"]
    if (
        isinstance(entropy, bool)
        or not isinstance(entropy, (int, float))
        or not 0.0 <= float(entropy) <= 1.0
        or not isinstance(top_state, str)
        or len(top_state) != 5
        or set(top_state) - {"0", "1"}
        or type(shots) is not int
        or shots <= 0
    ):
        raise ValueError("invalid published archive summary record")
    return record


def soul_token_from_ibm_fez_summary(index: int) -> SoulToken:
    """Convert one published summary to a new, explicit replay-only SOUL state.

    The normalized vector is newly defined as:
      [normalized Shannon entropy, top_state bit 0, ..., top_state bit 4]

    This does not reconstruct the missing histogram or raw primitive result. It
    is a deterministic encoding of exactly the six values available in the
    published summary and is therefore a new experiment schema.
    """
    record = _validated_record(index)
    normalized = [float(record["entropy"])] + [float(bit) for bit in record["top_state"]]
    source = {
        "repo": SOURCE_REPO,
        "commit": SOURCE_COMMIT,
        "path": SOURCE_PATH,
        "git_blob_sha1": SOURCE_BLOB_SHA1,
    }
    result_digest = sha256_obj({"schema": SCHEMA, "source": source, "record": record})
    state = {
        "qbt_version": SCHEMA,
        "provider": "ibm",
        "backend": record["backend"],
        "execution_mode": "hardware_archive_summary_replay",
        "timestamp": record["timestamp"],
        "job_id": record["job_id"],
        "shots": record["total_shots"],
        "entropy": float(record["entropy"]),
        "normalized_vector": normalized,
        "result_digest": result_digest,
        "provenance": {
            **source,
            "input_class": "PUBLISHED_DECODE_SUMMARY_REPLAY_NOT_RAW_RESULT",
            "transform": "normalized_vector=[entropy]+left_to_right_top_state_bits",
            "source_reported_completed_hardware_job": True,
            "raw_runtime_payload_present": False,
            "full_counts_present": False,
            "current_run_hardware_attested": False,
            "fresh_provider_execution": False,
        },
        "quality": {
            "classification": "ARCHIVE_SUMMARY_REPLAY_ONLY",
            "independent_raw_redecode": False,
        },
    }
    return SoulToken.from_qbt(state, source_type="HARDWARE_ARCHIVE_REPLAY")


def archive_manifest() -> dict[str, Any]:
    """Public, non-secret replay catalog without generating any provider job."""
    return {
        "schema": SCHEMA,
        "source": {
            "repo": SOURCE_REPO,
            "commit": SOURCE_COMMIT,
            "path": SOURCE_PATH,
            "git_blob_sha1": SOURCE_BLOB_SHA1,
        },
        "records": [
            {
                "index": index,
                "job_id": record["job_id"],
                "backend": record["backend"],
                "timestamp": record["timestamp"],
                "entropy": record["entropy"],
                "top_state": record["top_state"],
                "total_shots": record["total_shots"],
            }
            for index, record in enumerate(IBM_FEZ_REPORTED_SUMMARIES)
        ],
        "live_hardware": False,
        "raw_results_present": False,
        "new_paid_job_required": False,
    }
