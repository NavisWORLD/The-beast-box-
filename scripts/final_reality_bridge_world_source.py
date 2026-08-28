#!/usr/bin/env python3
"""Authenticate and canonicalize the historical 4,096-record world source.

The original evidence JSONL is an append-only receipt whose timestamps and
record-chain hashes legitimately differ between ingestion runs.  This module
first authenticates a pinned historical receipt container, verifies its full
chain and ingestion summary, and then removes only those three run-volatile
receipt fields to produce the frozen scientific source bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

from beastbox.world_knowledge import normalize_world_text


ZERO_SHA256 = "0" * 64
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VOLATILE_RECEIPT_FIELDS = frozenset(
    {"created_at", "previous_record_sha256", "record_sha256"}
)
REQUIRED_STABLE_FIELDS = frozenset(
    {
        "schema",
        "namespace",
        "knowledge_id",
        "source_dataset",
        "source_id",
        "source_url",
        "title",
        "text",
        "license_label",
        "revision_label",
        "source_sha256",
    }
)
PLACEHOLDER_MARKERS = ("world source evidence record",)


class WorldSourceValidationError(RuntimeError):
    """Raised when a historical source cannot satisfy its frozen contract."""


@dataclass(frozen=True)
class WorldSourceContract:
    artifact_run_id: int
    artifact_id: int
    artifact_name: str
    evidence_sha256: str
    summary_sha256: str
    canonical_sha256: str
    record_hashes_sha256: str
    source_set_sha256: str
    record_count: int
    record_schema: str
    summary_schema: str
    source_dataset: str
    revision_label: str
    original_evidence_sha256: str | None = None


@dataclass(frozen=True)
class WorldSourceReceipt:
    artifact_run_id: int
    artifact_id: int
    artifact_name: str
    evidence_sha256: str
    summary_sha256: str
    canonical_sha256: str
    record_hashes_sha256: str
    source_set_sha256: str
    record_count: int
    record_schema: str
    summary_schema: str
    source_dataset: str
    revision_label: str
    receipt_chain_tip_sha256: str
    placeholder_records: int
    original_evidence_sha256: str | None
    original_container_bytes_recovered: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PRODUCTION_WORLD_SOURCE_CONTRACT = WorldSourceContract(
    artifact_run_id=33132925890,
    artifact_id=9670957287,
    artifact_name="zeref-world-r12-downstream-diagnostic-v2-33132925890",
    evidence_sha256="cdbc84db988668894a476d51ee42faa591cace77631da7c7daa82831bb1201de",
    summary_sha256="9e2e6cf0965691db9a4ecd3affe9ccb8b33195f6cf7f2341ace1e1f43e549d3b",
    canonical_sha256="a14e5f5bbc37bfda6da6b062e2e101a621386b6af257f71da64e3b4d4d250a85",
    record_hashes_sha256="4c464aa1b72d658460185cb55d932be61a20cfb4172159fc0333406e8acf698c",
    source_set_sha256="07216bb2a4ca979ca1ea4304efb92b09ee8aad74685df43196d694f3bd7ef8ba",
    record_count=4096,
    record_schema="zeref-world-knowledge-record-v1",
    summary_schema="zeref-world-ingestion-summary-v1",
    source_dataset="wikimedia/wikipedia",
    revision_label="20231101.en",
    original_evidence_sha256="5319b876c46bbdb29912b28b8d0b95451a9fbf9cc728cc7989853fe7acd5c821",
)


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise WorldSourceValidationError("world source contains non-canonical JSON values") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise WorldSourceValidationError(f"missing {label}: {path}")


def _verify_file_hash(path: Path, expected: str, label: str) -> None:
    actual = _sha256_file(path)
    if actual != expected:
        raise WorldSourceValidationError(
            f"{label} SHA-256 mismatch: expected {expected}, got {actual}"
        )


def _parse_json_line(raw: str, line_number: int) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise WorldSourceValidationError(
            f"world evidence JSON decoding failed at line {line_number}"
        ) from exc
    if not isinstance(value, dict):
        raise WorldSourceValidationError(
            f"world evidence line {line_number} is not an object"
        )
    return value


def _iter_evidence(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            line_number = 0
            for line_number, raw in enumerate(handle, 1):
                if not raw.strip():
                    raise WorldSourceValidationError(
                        f"blank world evidence row at line {line_number}"
                    )
                yield line_number, _parse_json_line(raw, line_number)
            if line_number == 0:
                raise WorldSourceValidationError("world evidence is empty")
    except UnicodeDecodeError as exc:
        raise WorldSourceValidationError("world evidence is not valid UTF-8") from exc


def canonical_world_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.items()
        if key not in VOLATILE_RECEIPT_FIELDS
    }


@dataclass(frozen=True)
class _ValidatedSource:
    record_count: int
    source_ids: tuple[str, ...]
    source_hashes: tuple[str, ...]
    canonical_sha256: str
    record_hashes_sha256: str
    source_set_sha256: str
    receipt_chain_tip_sha256: str
    record_hash_lines: bytes


def _validate_evidence_records(
    evidence_path: Path,
    contract: WorldSourceContract,
) -> _ValidatedSource:
    expected_previous = ZERO_SHA256
    canonical_digest = hashlib.sha256()
    record_hashes_digest = hashlib.sha256()
    source_set_digest = hashlib.sha256()
    record_hash_lines: list[bytes] = []
    source_ids: list[str] = []
    source_hashes: list[str] = []
    seen_source_ids: set[str] = set()

    for line_number, record in _iter_evidence(evidence_path):
        missing = sorted(REQUIRED_STABLE_FIELDS - set(record))
        if missing:
            raise WorldSourceValidationError(
                f"world evidence line {line_number} missing stable fields: {', '.join(missing)}"
            )
        if record.get("schema") != contract.record_schema:
            raise WorldSourceValidationError(
                f"record schema mismatch at line {line_number}"
            )
        if record.get("namespace") != "world":
            raise WorldSourceValidationError(
                f"world namespace mismatch at line {line_number}"
            )
        if record.get("source_dataset") != contract.source_dataset:
            raise WorldSourceValidationError(
                f"source dataset mismatch at line {line_number}"
            )
        if record.get("revision_label") != contract.revision_label:
            raise WorldSourceValidationError(
                f"source revision mismatch at line {line_number}"
            )
        if record.get("knowledge_id") != line_number:
            raise WorldSourceValidationError(
                f"knowledge ID order mismatch at line {line_number}"
            )

        source_id = str(record.get("source_id") or "").strip()
        title = str(record.get("title") or "").strip()
        text = str(record.get("text") or "").strip()
        license_label = str(record.get("license_label") or "").strip()
        source_sha256 = str(record.get("source_sha256") or "").lower()
        if not source_id or not title or not text or not license_label:
            raise WorldSourceValidationError(
                f"world source provenance is incomplete at line {line_number}"
            )
        normalized_text = " ".join(text.casefold().split()).rstrip(".")
        if any(marker in normalized_text for marker in PLACEHOLDER_MARKERS):
            raise WorldSourceValidationError(
                f"placeholder world source record rejected at line {line_number}"
            )
        if source_id in seen_source_ids:
            raise WorldSourceValidationError(
                f"duplicate world source ID at line {line_number}"
            )
        seen_source_ids.add(source_id)
        if not SHA256_RE.fullmatch(source_sha256):
            raise WorldSourceValidationError(
                f"invalid source SHA-256 at line {line_number}"
            )
        normalized_source_sha256 = hashlib.sha256(
            normalize_world_text(text).encode("utf-8")
        ).hexdigest()
        if normalized_source_sha256 != source_sha256:
            raise WorldSourceValidationError(
                f"source text SHA-256 mismatch at line {line_number}"
            )

        declared_previous = str(record.get("previous_record_sha256") or "").lower()
        if declared_previous != expected_previous:
            raise WorldSourceValidationError(
                f"world evidence receipt chain mismatch at line {line_number}"
            )
        declared_record_hash = str(record.get("record_sha256") or "").lower()
        if not SHA256_RE.fullmatch(declared_record_hash):
            raise WorldSourceValidationError(
                f"invalid receipt record SHA-256 at line {line_number}"
            )
        receipt_body = dict(record)
        receipt_body.pop("record_sha256", None)
        actual_record_hash = hashlib.sha256(_canonical(receipt_body)).hexdigest()
        if actual_record_hash != declared_record_hash:
            raise WorldSourceValidationError(
                f"world evidence receipt record hash mismatch at line {line_number}"
            )
        expected_previous = declared_record_hash

        canonical_blob = _canonical(canonical_world_record(record))
        canonical_digest.update(canonical_blob + b"\n")
        canonical_record_hash = hashlib.sha256(canonical_blob).hexdigest()
        record_hash_line = canonical_record_hash.encode("ascii") + b"\n"
        record_hash_lines.append(record_hash_line)
        record_hashes_digest.update(record_hash_line)
        source_set_digest.update(
            source_id.encode("utf-8")
            + b"\t"
            + source_sha256.encode("ascii")
            + b"\n"
        )
        source_ids.append(source_id)
        source_hashes.append(source_sha256)

    record_count = len(source_ids)
    if record_count != contract.record_count:
        raise WorldSourceValidationError(
            f"world source record count mismatch: expected {contract.record_count}, got {record_count}"
        )
    return _ValidatedSource(
        record_count=record_count,
        source_ids=tuple(source_ids),
        source_hashes=tuple(source_hashes),
        canonical_sha256=canonical_digest.hexdigest(),
        record_hashes_sha256=record_hashes_digest.hexdigest(),
        source_set_sha256=source_set_digest.hexdigest(),
        receipt_chain_tip_sha256=expected_previous,
        record_hash_lines=b"".join(record_hash_lines),
    )


def _load_and_validate_summary(
    summary_path: Path,
    contract: WorldSourceContract,
    source: _ValidatedSource,
) -> None:
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise WorldSourceValidationError("world ingestion summary is not valid JSON") from exc
    if not isinstance(summary, dict):
        raise WorldSourceValidationError("world ingestion summary is not an object")
    if summary.get("schema") != contract.summary_schema:
        raise WorldSourceValidationError("ingestion summary schema mismatch")
    if summary.get("source_dataset") != contract.source_dataset:
        raise WorldSourceValidationError("ingestion summary source dataset mismatch")
    if summary.get("revision_label") != contract.revision_label:
        raise WorldSourceValidationError("ingestion summary revision mismatch")
    if summary.get("accepted") != contract.record_count:
        raise WorldSourceValidationError("ingestion summary record count mismatch")
    summary_ids = tuple(str(value) for value in summary.get("accepted_source_ids") or ())
    summary_hashes = tuple(
        str(value).lower() for value in summary.get("accepted_source_sha256") or ()
    )
    if summary_ids != source.source_ids:
        raise WorldSourceValidationError("ingestion summary ordered source IDs mismatch")
    if summary_hashes != source.source_hashes:
        raise WorldSourceValidationError("ingestion summary ordered source hashes mismatch")


def _verify_derived_hashes(
    source: _ValidatedSource,
    contract: WorldSourceContract,
) -> None:
    comparisons = (
        ("canonical world source", source.canonical_sha256, contract.canonical_sha256),
        (
            "canonical record-hash list",
            source.record_hashes_sha256,
            contract.record_hashes_sha256,
        ),
        ("semantic source set", source.source_set_sha256, contract.source_set_sha256),
    )
    for label, actual, expected in comparisons:
        if actual != expected:
            raise WorldSourceValidationError(
                f"{label} SHA-256 mismatch: expected {expected}, got {actual}"
            )


def _atomic_write(path: Path, payload_writer) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            payload_writer(handle)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def canonicalize_world_source(evidence_path: Path, output_path: Path) -> None:
    def write(handle) -> None:
        for _, record in _iter_evidence(evidence_path):
            handle.write(_canonical(canonical_world_record(record)) + b"\n")

    _atomic_write(output_path, write)


def validate_world_source(
    evidence_path: str | Path,
    summary_path: str | Path,
    contract: WorldSourceContract = PRODUCTION_WORLD_SOURCE_CONTRACT,
    *,
    canonical_output: str | Path | None = None,
    record_hashes_output: str | Path | None = None,
) -> WorldSourceReceipt:
    evidence_path = Path(evidence_path)
    summary_path = Path(summary_path)
    _require_file(evidence_path, "world evidence")
    _require_file(summary_path, "world ingestion summary")
    _verify_file_hash(evidence_path, contract.evidence_sha256, "evidence")
    _verify_file_hash(summary_path, contract.summary_sha256, "summary")

    source = _validate_evidence_records(evidence_path, contract)
    _load_and_validate_summary(summary_path, contract, source)
    _verify_derived_hashes(source, contract)

    if canonical_output is not None:
        canonicalize_world_source(evidence_path, Path(canonical_output))
        if _sha256_file(Path(canonical_output)) != contract.canonical_sha256:
            raise WorldSourceValidationError("written canonical world source hash mismatch")
    if record_hashes_output is not None:
        _atomic_write(Path(record_hashes_output), lambda handle: handle.write(source.record_hash_lines))
        if _sha256_file(Path(record_hashes_output)) != contract.record_hashes_sha256:
            raise WorldSourceValidationError("written canonical record hashes mismatch")

    return WorldSourceReceipt(
        artifact_run_id=contract.artifact_run_id,
        artifact_id=contract.artifact_id,
        artifact_name=contract.artifact_name,
        evidence_sha256=contract.evidence_sha256,
        summary_sha256=contract.summary_sha256,
        canonical_sha256=source.canonical_sha256,
        record_hashes_sha256=source.record_hashes_sha256,
        source_set_sha256=source.source_set_sha256,
        record_count=source.record_count,
        record_schema=contract.record_schema,
        summary_schema=contract.summary_schema,
        source_dataset=contract.source_dataset,
        revision_label=contract.revision_label,
        receipt_chain_tip_sha256=source.receipt_chain_tip_sha256,
        placeholder_records=0,
        original_evidence_sha256=contract.original_evidence_sha256,
        original_container_bytes_recovered=(
            contract.original_evidence_sha256 == contract.evidence_sha256
            if contract.original_evidence_sha256 is not None
            else False
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--canonical-output", type=Path, required=True)
    parser.add_argument("--record-hashes-output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    args = parser.parse_args()

    receipt = validate_world_source(
        args.evidence,
        args.summary,
        PRODUCTION_WORLD_SOURCE_CONTRACT,
        canonical_output=args.canonical_output,
        record_hashes_output=args.record_hashes_output,
    )
    receipt_payload = json.dumps(
        {"schema": "cosmos-historical-world-source-receipt-v1", **receipt.to_dict()},
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    _atomic_write(args.receipt_output, lambda handle: handle.write(receipt_payload))
    print(
        json.dumps(
            {
                "canonical_sha256": receipt.canonical_sha256,
                "record_count": receipt.record_count,
                "source_set_sha256": receipt.source_set_sha256,
                "status": "VERIFIED_GENUINE_HISTORICAL_SOURCE",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
