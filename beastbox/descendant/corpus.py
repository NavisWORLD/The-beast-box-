"""Deterministic corpus fingerprinting and contamination quarantine for D001."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping

_STRONG_ZELDA_MARKERS = (
    "the legend of zelda",
    "majora s mask",
    "hyrule",
    "ganondorf",
    "triforce",
    "clock town",
    "deku scrub",
    "master sword",
    "termina",
    "princess zelda",
)
_AMBIGUOUS_GAME_TERMS = ("link", "game", "mask", "controller", "temple", "quest")


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class CorpusFingerprint:
    source_ref: str
    byte_sha256: str
    normalized_text_sha256: str
    size_bytes: int
    contamination_labels: tuple[str, ...]
    contamination_score: float
    disposition: str
    license_id: str | None = None
    source_metadata: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        value = asdict(self)
        value["contamination_labels"] = list(self.contamination_labels)
        value["source_metadata"] = dict(sorted(self.source_metadata.items()))
        return value


def fingerprint_record(
    *,
    source_ref: str,
    data: bytes,
    license_id: str | None = None,
    source_metadata: Mapping[str, str] | None = None,
) -> CorpusFingerprint:
    if not source_ref.strip():
        raise ValueError("source_ref is required")
    text = data.decode("utf-8", errors="replace")
    normalized = normalize_text(text)
    strong_hits = tuple(marker for marker in _STRONG_ZELDA_MARKERS if marker in normalized)
    tokens = set(normalized.split())
    ambiguous_hits = tuple(term for term in _AMBIGUOUS_GAME_TERMS if term in tokens)

    labels: list[str] = []
    if strong_hits:
        labels.append("ZELDA_FRANCHISE_EXPLICIT")
    if len(strong_hits) >= 2:
        labels.append("ZELDA_HIGH_OVERLAP")
    if not strong_hits and len(ambiguous_hits) >= 2:
        labels.append("AMBIGUOUS_GAME_TERMS")

    score = min(1.0, len(strong_hits) / 3.0)
    if strong_hits:
        disposition = "QUARANTINE"
    elif labels:
        disposition = "REVIEW"
    else:
        disposition = "CLEAN"

    return CorpusFingerprint(
        source_ref=source_ref,
        byte_sha256=_sha256(data),
        normalized_text_sha256=_sha256(normalized.encode("utf-8")),
        size_bytes=len(data),
        contamination_labels=tuple(labels),
        contamination_score=score,
        disposition=disposition,
        license_id=license_id,
        source_metadata=dict(source_metadata or {}),
    )


def write_manifests(records: list[CorpusFingerprint], out_dir: str | Path) -> dict[str, int]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "source": out / "source-corpus-manifest.jsonl",
        "clean": out / "clean-corpus-manifest.jsonl",
        "quarantine": out / "quarantine-manifest.jsonl",
        "review": out / "review-manifest.jsonl",
    }
    for path in paths.values():
        path.write_text("", encoding="utf-8")

    counts = {"source": 0, "clean": 0, "quarantine": 0, "review": 0}
    for rec in sorted(records, key=lambda item: item.source_ref):
        row = json.dumps(rec.to_dict(), sort_keys=True, ensure_ascii=False) + "\n"
        with paths["source"].open("a", encoding="utf-8") as handle:
            handle.write(row)
        counts["source"] += 1
        key = rec.disposition.lower()
        with paths[key].open("a", encoding="utf-8") as handle:
            handle.write(row)
        counts[key] += 1

    if counts["source"] != counts["clean"] + counts["quarantine"] + counts["review"]:
        raise RuntimeError("corpus manifest counts do not conserve source records")
    return counts
