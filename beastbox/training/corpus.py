from __future__ import annotations

import hashlib
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence

from beastbox.hashutil import canonical_json, sha256_obj

from .lineage import sha256_file, write_canonical_json

CorpusKind = Literal["lexical", "world"]
_SPLITS = ("train", "validation", "test")


def _text(value: Any, field: str, *, casefold: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = unicodedata.normalize("NFC", value)
    normalized = " ".join(normalized.split())
    if casefold:
        normalized = normalized.casefold()
    if not normalized:
        raise ValueError(f"{field} must be non-empty")
    return normalized


def _string_list(value: Any, field: str, *, casefold: bool) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a list")
    normalized = {_text(item, field, casefold=casefold) for item in value}
    return sorted(normalized, key=lambda item: (item.casefold(), item))


def normalize_lexical_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ValueError("lexical record must be an object")
    return {
        "lemma": _text(record.get("lemma"), "lemma", casefold=True),
        "part_of_speech": _text(record.get("part_of_speech"), "part_of_speech", casefold=True),
        "definition": _text(record.get("definition"), "definition"),
        "synonyms": _string_list(record.get("synonyms", []), "synonyms", casefold=True),
        "antonyms": _string_list(record.get("antonyms", []), "antonyms", casefold=True),
        "examples": _string_list(record.get("examples", []), "examples", casefold=False),
        "source_id": _text(record.get("source_id"), "source_id"),
    }


def normalize_world_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ValueError("world record must be an object")
    return {
        "title": _text(record.get("title"), "title"),
        "text": _text(record.get("text"), "text"),
        "source_id": _text(record.get("source_id"), "source_id"),
    }


def _normalize_sources(sources: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    normalized_by_id: dict[str, dict[str, str]] = {}
    for source in sources:
        if not isinstance(source, Mapping):
            raise ValueError("source manifest entries must be objects")
        normalized = {
            "source_id": _text(source.get("source_id"), "source_id"),
            "uri": _text(source.get("uri"), "uri"),
            "license": _text(source.get("license"), "license"),
        }
        source_id = normalized["source_id"]
        if source_id in normalized_by_id and normalized_by_id[source_id] != normalized:
            raise ValueError(f"duplicate source_id has conflicting metadata: {source_id}")
        normalized_by_id[source_id] = normalized
    if not normalized_by_id:
        raise ValueError("at least one source is required")
    return [normalized_by_id[key] for key in sorted(normalized_by_id)]


def _split_for(*, kind: CorpusKind, record: Mapping[str, Any], split_salt: str) -> str:
    if kind == "lexical":
        stable_key = str(record["lemma"]).casefold()
    else:
        stable_key = f"{record['source_id']}:{str(record['title']).casefold()}"
    material = f"{split_salt}:{stable_key}".encode("utf-8")
    bucket = int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % 100
    if bucket < 90:
        return "train"
    if bucket < 95:
        return "validation"
    return "test"


def _render_lexical(record: Mapping[str, Any]) -> str:
    synonyms = ", ".join(record["synonyms"]) if record["synonyms"] else "[NONE]"
    antonyms = ", ".join(record["antonyms"]) if record["antonyms"] else "[NONE]"
    examples = " | ".join(record["examples"]) if record["examples"] else "[NONE]"
    return (
        f"TERM: {record['lemma']}\n"
        f"PART_OF_SPEECH: {record['part_of_speech']}\n"
        f"DEFINITION: {record['definition']}\n"
        f"SYNONYMS: {synonyms}\n"
        f"ANTONYMS: {antonyms}\n"
        f"EXAMPLES: {examples}\n\n"
    )


def _render_world(record: Mapping[str, Any]) -> str:
    return f"TITLE: {record['title']}\nTEXT: {record['text']}\nSOURCE: {record['source_id']}\n\n"


def _write_split(output_dir: Path, split: str, rows: list[dict[str, Any]], *, kind: CorpusKind) -> dict[str, str]:
    jsonl = output_dir / f"{split}.jsonl"
    text = output_dir / f"{split}.txt"
    jsonl.write_text(
        "".join(canonical_json(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    renderer = _render_lexical if kind == "lexical" else _render_world
    text.write_text("".join(renderer(row) for row in rows), encoding="utf-8")
    return {
        jsonl.name: sha256_file(jsonl),
        text.name: sha256_file(text),
    }


def build_corpus(
    *,
    kind: CorpusKind,
    records: Iterable[Mapping[str, Any]],
    sources: Sequence[Mapping[str, str]],
    output_dir: str | Path,
    split_salt: str = "zeref-phos-v1",
) -> dict[str, Any]:
    if kind not in ("lexical", "world"):
        raise ValueError("kind must be lexical or world")
    salt = _text(split_salt, "split_salt")
    normalized_sources = _normalize_sources(sources)
    known_sources = {source["source_id"] for source in normalized_sources}
    normalizer = normalize_lexical_record if kind == "lexical" else normalize_world_record

    unique: dict[str, dict[str, Any]] = {}
    for raw in records:
        record = normalizer(raw)
        if record["source_id"] not in known_sources:
            raise ValueError(f"unknown source_id: {record['source_id']}")
        unique[sha256_obj(record)] = record
    normalized_records = [unique[key] for key in sorted(unique)]

    target = Path(output_dir)
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"output directory already contains artifacts: {target}")
    target.mkdir(parents=True, exist_ok=True)

    split_rows: dict[str, list[dict[str, Any]]] = {split: [] for split in _SPLITS}
    for record in normalized_records:
        split = _split_for(kind=kind, record=record, split_salt=salt)
        split_rows[split].append(record)

    artifacts: dict[str, str] = {}
    for split in _SPLITS:
        artifacts.update(_write_split(target, split, split_rows[split], kind=kind))
    artifacts = {name: artifacts[name] for name in sorted(artifacts)}

    dataset_sha256 = sha256_obj(
        {
            "kind": kind,
            "records": normalized_records,
            "sources": normalized_sources,
            "split_salt": salt,
        }
    )
    manifest: dict[str, Any] = {
        "schema": "zeref-phos-corpus-manifest-v1",
        "kind": kind,
        "split_salt": salt,
        "record_count": len(normalized_records),
        "split_counts": {split: len(split_rows[split]) for split in _SPLITS},
        "sources": normalized_sources,
        "dataset_sha256": dataset_sha256,
        "artifacts": artifacts,
    }
    manifest_sha256 = write_canonical_json(target / "manifest.json", manifest)
    return {**manifest, "manifest_sha256": manifest_sha256}
