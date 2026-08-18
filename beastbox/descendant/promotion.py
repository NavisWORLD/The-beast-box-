"""Leakage-safe training promotion records for Descendant-001."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

_SPLITS = ("train", "validation", "holdout")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _valid_sha(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


@dataclass(frozen=True)
class PromotionCandidate:
    source_hashes: tuple[str, ...]
    group_id: str
    text: str
    reason: str
    reviewer: str
    policy_version: str
    source_disposition: str
    source_validity: str
    provenance_class: str
    transformations: tuple[str, ...] = ()
    contamination_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_hashes or any(not _valid_sha(v) for v in self.source_hashes):
            raise ValueError("valid source hashes are required")
        for name in ("group_id", "text", "reason", "reviewer", "policy_version"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")


@dataclass(frozen=True)
class PromotionRecord:
    source_hashes: tuple[str, ...]
    group_id: str
    partition: str
    text: str
    reason: str
    reviewer: str
    policy_version: str
    transformations: tuple[str, ...]
    contamination_flags: tuple[str, ...]
    example_sha256: str

    def __post_init__(self) -> None:
        if self.partition not in _SPLITS:
            raise ValueError("invalid partition")
        if not _valid_sha(self.example_sha256):
            raise ValueError("example_sha256 is invalid")

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["source_hashes"] = list(self.source_hashes)
        value["transformations"] = list(self.transformations)
        value["contamination_flags"] = list(self.contamination_flags)
        return value


def assign_split(group_id: str, *, seed: str, train_fraction: float = 0.8, validation_fraction: float = 0.1) -> str:
    if not group_id or not seed:
        raise ValueError("group_id and seed are required")
    if train_fraction <= 0 or validation_fraction < 0 or train_fraction + validation_fraction >= 1:
        raise ValueError("invalid split fractions")
    digest = hashlib.sha256(f"{seed}\0{group_id}".encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big") / float(2**64)
    if value < train_fraction:
        return "train"
    if value < train_fraction + validation_fraction:
        return "validation"
    return "holdout"


def promote(candidate: PromotionCandidate, *, split_seed: str) -> PromotionRecord:
    if candidate.source_disposition.upper() == "QUARANTINE":
        raise ValueError("quarantined source cannot be promoted")
    if candidate.source_disposition.upper() not in {"CLEAN", "APPROVED"}:
        raise ValueError("source disposition is not promotion-approved")
    if candidate.source_validity.upper() != "VALID":
        raise ValueError("invalid source cannot be promoted")
    if candidate.provenance_class.lower() not in {"verified", "verified_measurement", "project_origin"}:
        raise ValueError("provenance is not sufficient for promotion")

    partition = assign_split(candidate.group_id, seed=split_seed)
    body = {
        "source_hashes": list(candidate.source_hashes),
        "group_id": candidate.group_id,
        "partition": partition,
        "text": candidate.text,
        "reason": candidate.reason,
        "reviewer": candidate.reviewer,
        "policy_version": candidate.policy_version,
        "transformations": list(candidate.transformations),
        "contamination_flags": list(candidate.contamination_flags),
    }
    return PromotionRecord(
        source_hashes=candidate.source_hashes,
        group_id=candidate.group_id,
        partition=partition,
        text=candidate.text,
        reason=candidate.reason,
        reviewer=candidate.reviewer,
        policy_version=candidate.policy_version,
        transformations=candidate.transformations,
        contamination_flags=candidate.contamination_flags,
        example_sha256=_sha(body),
    )


def audit_leakage(records: Sequence[PromotionRecord]) -> dict[str, object]:
    source_partitions: dict[str, set[str]] = {}
    source_counts: dict[str, int] = {}
    group_partitions: dict[str, set[str]] = {}
    example_hashes: set[str] = set()
    duplicate_examples: list[str] = []

    for record in records:
        for source_hash in record.source_hashes:
            source_partitions.setdefault(source_hash, set()).add(record.partition)
            source_counts[source_hash] = source_counts.get(source_hash, 0) + 1
        group_partitions.setdefault(record.group_id, set()).add(record.partition)
        if record.example_sha256 in example_hashes:
            duplicate_examples.append(record.example_sha256)
        example_hashes.add(record.example_sha256)

    source_hash_leaks = sorted(key for key, parts in source_partitions.items() if len(parts) > 1)
    group_leaks = sorted(key for key, parts in group_partitions.items() if len(parts) > 1)
    duplicate_source_hashes = sorted(key for key, count in source_counts.items() if count > 1)
    valid = not source_hash_leaks and not group_leaks and not duplicate_source_hashes and not duplicate_examples
    return {
        "valid": valid,
        "records": len(records),
        "source_hash_leaks": source_hash_leaks,
        "group_leaks": group_leaks,
        "duplicate_source_hashes": duplicate_source_hashes,
        "duplicate_example_hashes": sorted(set(duplicate_examples)),
    }
