"""Growing local memory for one companion.

Keyword overlap plus a hashing-trick vector. The store is a JSON file. Export
writes a QBEAST1 snapshot: the Spark card stays event 0, and later events are
public text summaries. Raw camera frames and audio are never records.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .spark_bridge import load

MAX_RECORDS = 200
SCHEMA = "companion-memory-v1"


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{2,}", text.lower())


def embed(text: str, dim: int = 64) -> list[float]:
    values = [0.0] * dim
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode()).digest()
        index = digest[0] % dim
        values[index] += 1.0 if digest[1] & 1 else -1.0
    norm = math_sqrt(sum(value * value for value in values))
    if norm <= 1e-12:
        return values
    return [value / norm for value in values]


def math_sqrt(value: float) -> float:
    return value ** 0.5


def search_records(records: list[dict], query: str, k: int = 4) -> list[dict]:
    query_tokens = set(_tokens(query))
    query_vector = embed(query)
    scored = []
    for record in records:
        overlap = len(query_tokens & set(_tokens(record["text"])))
        vector = record.get("vector") or embed(record["text"])
        cosine = sum(left * right for left, right in zip(query_vector, vector))
        score = overlap + cosine
        if score > 0:
            scored.append((score, record))
    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [record for _, record in scored[:k]]


class CompanionMemory:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.records: list[dict] = []
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("schema") != SCHEMA or not isinstance(data.get("records"), list):
                raise ValueError("companion memory file is not companion-memory-v1")
            self.records = data["records"]

    def add(self, text: str, kind: str, source: str, created: str = "1970-01-01T00:00:00Z") -> dict:
        private = load()["PRIVATE"]
        clean = " ".join(str(text).split())
        if not clean or len(clean) > 500:
            raise ValueError("memory text must be 1 to 500 characters")
        if kind not in {"chat", "vision", "hearing", "note"}:
            raise ValueError("unknown memory kind")
        if private.search(clean) or "data:image" in clean or "base64," in clean:
            raise ValueError("refusing private or raw-media memory")
        record = {
            "id": hashlib.sha256(f"{kind}:{len(self.records)}:{clean}".encode()).hexdigest()[:16],
            "text": clean,
            "kind": kind,
            "source": source[:96],
            "created": created,
            "vector": embed(clean),
        }
        self.records.append(record)
        if len(self.records) > MAX_RECORDS:
            self.records = self.records[-MAX_RECORDS:]
        self.save()
        return record

    def search(self, query: str, k: int = 4) -> list[dict]:
        return search_records(self.records, query, k)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": SCHEMA, "records": self.records}
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def export_qbeast(self, genome: dict) -> str:
        mods = load()
        snapshot = mods["build_qbeast"](genome)
        parent = snapshot["lineage_head"]
        events = list(snapshot["events"])
        for record in self.records:
            summary = public_summary(record)
            generation = len(events) + 1
            proposal = mods["sha256_text"]("companion-memory:" + record["id"])
            payload = {"summary": summary, "source_ref": "public:companion-memory"}
            body = {
                "domain": "event",
                "generation": generation,
                "kind": "memory",
                "parent": parent,
                "payload": payload,
                "proposal_id": proposal,
            }
            event = {
                "generation": generation,
                "parent": parent,
                "proposal_id": proposal,
                "kind": "memory",
                "payload": payload,
                "hash": mods["hash_object"](body),
            }
            events.append(event)
            parent = event["hash"]
        snapshot["events"] = events
        snapshot["generation"] = len(events)
        snapshot["lineage_head"] = parent
        snapshot["digest"] = "0" * 64
        body = {key: value for key, value in snapshot.items() if key != "digest"}
        snapshot["digest"] = mods["hash_object"](body)
        return mods["serialize_qbeast"](snapshot)


def public_summary(record: dict) -> str:
    prefix = {"chat": "chat", "vision": "saw", "hearing": "heard", "note": "note"}[record["kind"]]
    text = f"{prefix}: {record['text']}"
    text = re.sub(r"[\u0000-\u001f\u007f]", "", text)
    if len(text) > 240:
        text = text[:237] + "..."
    if load()["PRIVATE"].search(text):
        raise ValueError("public summary looked private")
    return text
