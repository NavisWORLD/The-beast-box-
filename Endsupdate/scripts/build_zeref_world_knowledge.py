#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from beastbox.world_knowledge import WorldKnowledgeStore, normalize_world_text

_SENTENCE_RE = re.compile(r".+?[.!?](?:\s|$)")


def _compact_prefix(text: str, max_chars: int) -> str | None:
    normalized = normalize_world_text(text)
    if not normalized:
        return None
    if len(normalized) <= max_chars:
        return normalized
    prefix = normalized[: max_chars + 1]
    cut = prefix.rfind(" ", 0, max_chars + 1)
    if cut < max(8, max_chars // 2):
        cut = max_chars
    return normalized[:cut].rstrip(" ,;:-")


def first_factual_sentence(text: str, *, max_chars: int = 34) -> str | None:
    normalized = normalize_world_text(text)
    if not normalized:
        return None
    match = _SENTENCE_RE.match(normalized + " ")
    sentence = match.group(0).strip() if match else normalized
    if len(sentence) <= int(max_chars):
        return sentence
    return _compact_prefix(sentence, int(max_chars))


def _source_id(row: Mapping[str, Any], index: int) -> str:
    for key in ("id", "source_id", "pageid", "page_id"):
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    title = normalize_world_text(str(row.get("title") or ""))
    return f"stream-{index}-{title[:24]}"


def ingest_records(
    rows: Iterable[Mapping[str, Any]],
    *,
    db_path: Path,
    evidence_jsonl: Path,
    rejected_jsonl: Path,
    accepted_limit: int,
    source_dataset: str,
    revision_label: str,
    license_label: str,
) -> dict[str, Any]:
    if int(accepted_limit) <= 0:
        raise ValueError("accepted_limit must be positive")
    rejected_jsonl.parent.mkdir(parents=True, exist_ok=True)
    accepted_ids: list[str] = []
    accepted_hashes: list[str] = []
    examined = 0
    rejected = 0
    store = WorldKnowledgeStore(db_path, evidence_jsonl)
    try:
        for index, raw in enumerate(rows, 1):
            if len(accepted_ids) >= int(accepted_limit):
                break
            examined += 1
            row = dict(raw)
            title = normalize_world_text(str(row.get("title") or ""))
            text = normalize_world_text(str(row.get("text") or ""))
            source_id = _source_id(row, index)
            source_url = str(row.get("url") or row.get("source_url") or "").strip()
            fact = first_factual_sentence(text, max_chars=34)
            reason = None
            if not title:
                reason = "missing_title"
            elif not text:
                reason = "missing_text"
            elif fact is None or len(fact.split()) < 3:
                reason = "insufficient_fact"
            if reason:
                rejected += 1
                with rejected_jsonl.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(json.dumps({"index": index, "source_id": source_id, "reason": reason}, sort_keys=True) + "\n")
                continue
            try:
                receipt = store.add_record(
                    source_dataset=source_dataset,
                    source_id=source_id,
                    source_url=source_url,
                    title=title,
                    text=text,
                    license_label=license_label,
                    revision_label=revision_label,
                )
            except ValueError as exc:
                rejected += 1
                with rejected_jsonl.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(json.dumps({"index": index, "source_id": source_id, "reason": str(exc)}, sort_keys=True) + "\n")
                continue
            accepted_ids.append(str(receipt["source_id"]))
            accepted_hashes.append(str(receipt["source_sha256"]))
    finally:
        store.close()
    return {
        "schema": "zeref-world-ingestion-summary-v1",
        "source_dataset": str(source_dataset),
        "revision_label": str(revision_label),
        "accepted_limit": int(accepted_limit),
        "examined": examined,
        "accepted": len(accepted_ids),
        "rejected": rejected,
        "accepted_source_ids": accepted_ids,
        "accepted_source_sha256": accepted_hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="wikimedia/wikipedia")
    parser.add_argument("--config", default="20231101.en")
    parser.add_argument("--split", default="train")
    parser.add_argument("--accepted", type=int, default=4096)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--rejected", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--license-label", default="CC BY-SA 3.0 / GFDL")
    args = parser.parse_args()

    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit("Hugging Face datasets is required for live world ingestion") from exc

    stream = load_dataset(args.dataset, args.config, split=args.split, streaming=True)
    summary = ingest_records(
        stream,
        db_path=args.db,
        evidence_jsonl=args.evidence,
        rejected_jsonl=args.rejected,
        accepted_limit=args.accepted,
        source_dataset=args.dataset,
        revision_label=args.config,
        license_label=args.license_label,
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
