"""One persistent computational substrate shared across replaceable models."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import quote

from beastbox.dad_son import DadSonLedger
from beastbox.reality_memory import (
    CLAIM_BOUNDARY,
    RealityLedger,
    derive_r12_transition,
    sha256_json as reality_sha256_json,
)
from beastbox.refractive_memory import RefractiveMemoryRouter
from beastbox.state_family import StateFamily
from beastbox.world_knowledge import normalize_world_text
from beastbox.world_r12 import WorldR12Router

from .ledger import (
    LedgerReceipt,
    StateEventLedger,
    assemble_canonical_memory,
    get_verified_memory_record,
    verify_memory_chain,
)
from .protocol import (
    EXPERIMENT_ID,
    DeterministicLogicalClock,
    canonical_json_bytes,
    sha256_file,
    sha256_json,
)


ZERO_SHA256 = "0" * 64


def _tokens(text: str) -> list[str]:
    token = []
    tokens: list[str] = []
    for character in str(text):
        if character.isalnum() or character in "_'":
            token.append(character)
        elif token:
            tokens.append("".join(token).lower())
            token = []
    if token:
        tokens.append("".join(token).lower())
    return tokens


def _lexical_score(query: str, title: str, text: str) -> float:
    query_tokens = set(_tokens(query))
    document_tokens = set(_tokens(f"{title} {text}"))
    if not query_tokens or not document_tokens:
        return 0.0
    return max(0.0, min(1.0, len(query_tokens & document_tokens) / len(query_tokens)))


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label} is not a readable JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object: {path}")
    return value


def _load_json_or_jsonl(path: Path, *, label: str) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"{label} is not readable UTF-8: {path}") from exc
    if not text.strip():
        return []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        values: list[dict[str, Any]] = []
        for line_number, raw_line in enumerate(text.splitlines(), 1):
            if not raw_line.strip():
                raise RuntimeError(f"{label} contains blank line {line_number}")
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{label} contains invalid JSON at line {line_number}") from exc
            if not isinstance(row, dict):
                raise RuntimeError(f"{label} line {line_number} is not an object")
            values.append(row)
        return values
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return [dict(item) for item in value]
    if isinstance(value, dict):
        return [value]
    raise RuntimeError(f"{label} must contain an object, object list, or JSONL objects")


class ReadOnlyWorldKnowledgeStore:
    """Verified world-knowledge access with no writable SQLite path."""

    def __init__(self, db_path: str | Path, evidence_jsonl: str | Path) -> None:
        self.db_path = Path(db_path).resolve()
        self.evidence_jsonl = Path(evidence_jsonl).resolve()
        if not self.db_path.is_file():
            raise RuntimeError(f"world SQLite database is missing: {self.db_path}")
        if not self.evidence_jsonl.is_file():
            raise RuntimeError(f"world evidence ledger is missing: {self.evidence_jsonl}")
        uri_path = quote(self.db_path.as_posix(), safe="/:")
        self.db = sqlite3.connect(f"file:{uri_path}?mode=ro&immutable=1", uri=True)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA query_only=ON")
        self._evidence_by_id: dict[int, dict[str, Any]] = {}
        self.record_count = 0
        self.evidence_tip_sha256 = ZERO_SHA256
        self.semantic_source_set_sha256 = ZERO_SHA256
        self.semantic_row_root_sha256 = ZERO_SHA256
        self._verify_and_index()

    @staticmethod
    def _db_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "namespace": "world",
            "knowledge_id": int(row["id"]),
            "source_dataset": str(row["source_dataset"]),
            "source_id": str(row["source_id"]),
            "source_url": str(row["source_url"]),
            "title": str(row["title"]),
            "text": str(row["text"]),
            "license_label": str(row["license_label"]),
            "revision_label": str(row["revision_label"]),
            "source_sha256": str(row["source_sha256"]).lower(),
            "created_at": str(row["created_at"]),
        }

    def _verify_and_index(self) -> None:
        try:
            text = self.evidence_jsonl.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise RuntimeError("world evidence is not valid readable UTF-8") from exc
        previous = ZERO_SHA256
        indexed: dict[int, dict[str, Any]] = {}
        source_set_digest = hashlib.sha256()
        row_root_digest = hashlib.sha256()
        for line_number, raw_line in enumerate(text.splitlines(), 1):
            if not raw_line.strip():
                raise RuntimeError(f"world evidence contains blank line {line_number}")
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"world evidence contains invalid JSON at line {line_number}") from exc
            if not isinstance(row, dict) or row.get("schema") != "zeref-world-knowledge-record-v1":
                raise RuntimeError(f"world evidence schema mismatch at line {line_number}")
            if row.get("namespace") != "world" or int(row.get("knowledge_id") or 0) != line_number:
                raise RuntimeError(f"world evidence knowledge ID order mismatch at line {line_number}")
            declared_previous = str(row.get("previous_record_sha256") or "").lower()
            if declared_previous != previous:
                raise RuntimeError(f"world evidence chain mismatch at line {line_number}")
            declared_record = str(row.get("record_sha256") or "").lower()
            unsigned = dict(row)
            unsigned.pop("record_sha256", None)
            actual_record = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()
            if declared_record != actual_record:
                raise RuntimeError(f"world evidence record hash mismatch at line {line_number}")
            source_id = str(row.get("source_id") or "")
            source_sha256 = str(row.get("source_sha256") or "").lower()
            actual_source_sha256 = hashlib.sha256(normalize_world_text(str(row.get("text") or "")).encode("utf-8")).hexdigest()
            if source_sha256 != actual_source_sha256:
                raise RuntimeError(f"world evidence source text hash mismatch at line {line_number}")
            source_set_digest.update(source_id.encode("utf-8") + b"\t" + source_sha256.encode("ascii") + b"\n")
            semantic_row = {
                "knowledge_id": line_number,
                "source_id": source_id,
                "source_sha256": source_sha256,
                "title_sha256": hashlib.sha256(str(row.get("title") or "").encode("utf-8")).hexdigest(),
                "text_sha256": hashlib.sha256(str(row.get("text") or "").encode("utf-8")).hexdigest(),
            }
            row_root_digest.update(canonical_json_bytes(semantic_row) + b"\n")
            indexed[line_number] = dict(row)
            previous = declared_record

        database_rows = self.db.execute("SELECT * FROM knowledge ORDER BY id").fetchall()
        if len(database_rows) != len(indexed):
            raise RuntimeError("world SQLite/evidence record count mismatch")
        comparable_fields = (
            "source_dataset",
            "source_id",
            "source_url",
            "title",
            "text",
            "license_label",
            "revision_label",
            "source_sha256",
            "created_at",
        )
        for expected_id, database_row in enumerate(database_rows, 1):
            item = self._db_row(database_row)
            evidence = indexed[expected_id]
            if item["knowledge_id"] != expected_id:
                raise RuntimeError(f"world SQLite ID order mismatch at row {expected_id}")
            if any(str(item[field]) != str(evidence.get(field) or "") for field in comparable_fields):
                raise RuntimeError(f"world SQLite/evidence semantic mismatch at row {expected_id}")

        self._evidence_by_id = indexed
        self.record_count = len(indexed)
        self.evidence_tip_sha256 = previous
        self.semantic_source_set_sha256 = source_set_digest.hexdigest()
        self.semantic_row_root_sha256 = row_root_digest.hexdigest()

    def get(self, knowledge_id: int) -> dict[str, Any]:
        target_id = int(knowledge_id)
        row = self.db.execute("SELECT * FROM knowledge WHERE id=?", (target_id,)).fetchone()
        if row is None:
            raise LookupError(f"world knowledge id not found: {target_id}")
        result = self._db_row(row)
        result["record_sha256"] = str(self._evidence_by_id[target_id]["record_sha256"])
        return result

    def search_lexical(self, query: str, *, limit: int = 128) -> list[dict[str, Any]]:
        if int(limit) <= 0:
            return []
        tokens = _tokens(query)
        if not tokens:
            return []
        expression = " OR ".join(f'"{token}"' for token in dict.fromkeys(tokens))
        rows = self.db.execute(
            """
            SELECT k.*
            FROM knowledge_fts f
            JOIN knowledge k ON k.id=f.rowid
            WHERE knowledge_fts MATCH ?
            ORDER BY bm25(knowledge_fts)
            LIMIT ?
            """,
            (expression, int(limit)),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = self._db_row(row)
            item["record_sha256"] = str(self._evidence_by_id[item["knowledge_id"]]["record_sha256"])
            item["lexical_score"] = _lexical_score(query, item["title"], item["text"])
            result.append(item)
        result.sort(key=lambda item: (float(item["lexical_score"]), -int(item["knowledge_id"])), reverse=True)
        return result

    def snapshot_receipt(self) -> dict[str, Any]:
        self._verify_and_index()
        return {
            "db_sha256": sha256_file(self.db_path),
            "db_bytes": self.db_path.stat().st_size,
            "evidence_sha256": sha256_file(self.evidence_jsonl),
            "evidence_bytes": self.evidence_jsonl.stat().st_size,
            "record_count": self.record_count,
            "evidence_tip_sha256": self.evidence_tip_sha256,
            "semantic_source_set_sha256": self.semantic_source_set_sha256,
            "semantic_row_root_sha256": self.semantic_row_root_sha256,
            "read_only": True,
        }

    def close(self) -> None:
        self.db.close()


@dataclass(frozen=True)
class SubstrateInputPaths:
    repo_root: Path
    memory_manifest: Path
    world_db: Path
    world_evidence: Path
    world_summary: Path
    routing_config: Path
    r12_state: Path
    r12_history: Path
    reality_events: Path

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            object.__setattr__(self, field_name, Path(getattr(self, field_name)).resolve())


class PersistentSubstrate:
    """Persistent memory/state/routing object graph; model objects never belong here."""

    def __init__(
        self,
        *,
        inputs: SubstrateInputPaths,
        workspace: Path,
        condition_id: str,
        clock: DeterministicLogicalClock,
        memory_ledger: DadSonLedger,
        memory_parent_sha256: str,
        canonical_prefix_bytes: bytes,
        world_store: ReadOnlyWorldKnowledgeStore,
        routing_config: dict[str, Any],
        r12_state: dict[str, Any],
        r12_history: list[dict[str, Any]],
        reality_events: list[dict[str, Any]],
    ) -> None:
        self.inputs = inputs
        self.workspace = workspace
        self.condition_id = str(condition_id)
        self.clock = clock
        self.memory_ledger = memory_ledger
        self.memory_parent_sha256 = memory_parent_sha256
        self._canonical_prefix_bytes = canonical_prefix_bytes
        self.world_store = world_store
        self.routing_config = routing_config
        self.r12_state = r12_state
        self.r12_history = r12_history
        self.reality_events = reality_events
        self.run_r12_events: list[dict[str, Any]] = []
        self.state_family = StateFamily()
        self.state_ledger = StateEventLedger(workspace / "state-ledger.jsonl")
        self.personal_router = RefractiveMemoryRouter(memory_ledger)
        self.world_router = WorldR12Router(world_store)
        self._closed = False
        self._stores = {
            role: sha256_json(
                {"experiment_id": EXPERIMENT_ID, "condition_id": self.condition_id, "role": role}
            )
            for role in (
                "substrate_id",
                "memory_store_id",
                "state_store_id",
                "routing_store_id",
                "knowledge_store_id",
                "provenance_store_id",
            )
        }
        self._object_roles = {
            "memory_ledger": self.memory_ledger,
            "state_ledger": self.state_ledger,
            "state_family": self.state_family,
            "r12_state": self.r12_state,
            "r12_history": self.r12_history,
            "reality_events": self.reality_events,
            "routing_config": self.routing_config,
            "personal_router": self.personal_router,
            "world_router": self.world_router,
            "world_store": self.world_store,
        }
        self._object_ids = {role: id(value) for role, value in self._object_roles.items()}
        self._object_tokens = {
            role: sha256_json(
                {
                    "experiment_id": EXPERIMENT_ID,
                    "condition_id": self.condition_id,
                    "object_role": role,
                    "instance": 1,
                }
            )
            for role in self._object_roles
        }
        self._immutable_inputs = self._capture_immutable_inputs()
        self._implementation_hashes = self._capture_implementation_hashes()

    @classmethod
    def restore_primary(
        cls,
        inputs: SubstrateInputPaths,
        *,
        workspace: str | Path,
        clock: DeterministicLogicalClock | None = None,
        condition_id: str = "primary",
    ) -> "PersistentSubstrate":
        return cls._restore(
            inputs,
            workspace=Path(workspace),
            clock=clock or DeterministicLogicalClock(),
            condition_id=condition_id,
            empty_memory=False,
        )

    @classmethod
    def create_empty_control(
        cls,
        inputs: SubstrateInputPaths,
        *,
        workspace: str | Path,
        clock: DeterministicLogicalClock | None = None,
        condition_id: str = "fresh-empty-memory",
    ) -> "PersistentSubstrate":
        return cls._restore(
            inputs,
            workspace=Path(workspace),
            clock=clock or DeterministicLogicalClock(),
            condition_id=condition_id,
            empty_memory=True,
        )

    @classmethod
    def _restore(
        cls,
        inputs: SubstrateInputPaths,
        *,
        workspace: Path,
        clock: DeterministicLogicalClock,
        condition_id: str,
        empty_memory: bool,
    ) -> "PersistentSubstrate":
        workspace = workspace.resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        required_paths = (
            inputs.memory_manifest,
            inputs.world_db,
            inputs.world_evidence,
            inputs.world_summary,
            inputs.routing_config,
            inputs.r12_state,
            inputs.r12_history,
            inputs.reality_events,
        )
        missing = [str(path) for path in required_paths if not path.is_file()]
        if missing:
            raise RuntimeError(f"persistent substrate inputs are missing: {', '.join(missing)}")

        manifest = _load_json_object(inputs.memory_manifest, label="memory manifest")
        parent_sha256 = str(manifest.get("parent_gguf_sha256") or "").lower()
        memory_path = workspace / "memory-ledger.jsonl"
        if empty_memory:
            memory_path.write_bytes(b"")
            canonical_prefix = b""
        else:
            assemble_canonical_memory(inputs.repo_root, inputs.memory_manifest, memory_path)
            canonical_prefix = memory_path.read_bytes()
        memory_ledger = DadSonLedger(
            workspace / "memory.sqlite3",
            memory_path,
            parent_sha256=parent_sha256,
            timestamp_factory=clock.take,
        )
        try:
            restored = memory_ledger.restore_snapshot()
            expected_count = 0 if empty_memory else int(manifest.get("record_count") or 0)
            if int(restored["restored_records"]) != expected_count:
                raise RuntimeError("restored personal memory record count mismatch")
            world_store = ReadOnlyWorldKnowledgeStore(inputs.world_db, inputs.world_evidence)
            routing_config = _load_json_object(inputs.routing_config, label="routing config")
            r12_state = _load_json_object(inputs.r12_state, label="R12 state")
            vector = r12_state.get("vector")
            if not isinstance(vector, dict) or len(vector) != 12:
                raise RuntimeError("R12 state must contain a 12-value vector")
            if "state_sha256" in r12_state:
                unsigned_state = dict(r12_state)
                declared_state_sha256 = str(unsigned_state.pop("state_sha256"))
                if reality_sha256_json(unsigned_state) != declared_state_sha256:
                    raise RuntimeError("R12 state internal hash mismatch")
            r12_history = _load_json_or_jsonl(inputs.r12_history, label="R12 history")
            reality_ledger = RealityLedger(inputs.reality_events)
            reality_ledger.verify()
            reality_events = reality_ledger.events()
            return cls(
                inputs=inputs,
                workspace=workspace,
                condition_id=condition_id,
                clock=clock,
                memory_ledger=memory_ledger,
                memory_parent_sha256=parent_sha256,
                canonical_prefix_bytes=canonical_prefix,
                world_store=world_store,
                routing_config=routing_config,
                r12_state=r12_state,
                r12_history=r12_history,
                reality_events=reality_events,
            )
        except BaseException:
            memory_ledger.close()
            raise

    @property
    def stores(self) -> dict[str, str]:
        return dict(self._stores)

    @property
    def memory_path(self) -> Path:
        return self.memory_ledger.evidence_jsonl

    def _capture_immutable_inputs(self) -> dict[str, dict[str, Any]]:
        roles = {
            "memory_manifest": self.inputs.memory_manifest,
            "world_db": self.inputs.world_db,
            "world_evidence": self.inputs.world_evidence,
            "world_summary": self.inputs.world_summary,
            "routing_config": self.inputs.routing_config,
            "r12_state": self.inputs.r12_state,
            "r12_history": self.inputs.r12_history,
            "reality_events": self.inputs.reality_events,
        }
        return {
            role: {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for role, path in roles.items()
        }

    def _capture_implementation_hashes(self) -> dict[str, str]:
        relative_paths = (
            "beastbox/dad_son.py",
            "beastbox/dyn12.py",
            "beastbox/refractive_memory.py",
            "beastbox/state_family.py",
            "beastbox/world_knowledge.py",
            "beastbox/world_r12.py",
            "beastbox/persistent_substrate/ledger.py",
            "beastbox/persistent_substrate/protocol.py",
            "beastbox/persistent_substrate/substrate.py",
        )
        return {relative: sha256_file(self.inputs.repo_root / relative) for relative in relative_paths}

    def _verify_immutable_inputs(self) -> None:
        current = self._capture_immutable_inputs()
        if current != self._immutable_inputs:
            raise RuntimeError("persistent substrate immutable input changed")
        implementations = self._capture_implementation_hashes()
        if implementations != self._implementation_hashes:
            raise RuntimeError("persistent substrate implementation changed")

    def _verify_object_graph(self) -> None:
        for role, expected_id in self._object_ids.items():
            if id(self._object_roles[role]) != expected_id:
                raise RuntimeError(f"persistent substrate object changed: {role}")

    def _memory_receipt(self) -> LedgerReceipt:
        return verify_memory_chain(
            self.memory_path,
            parent_sha256=self.memory_parent_sha256,
            immutable_prefix=self._canonical_prefix_bytes,
        )

    def append_memory(
        self,
        *,
        actor: str,
        text: str,
        kind: str,
        session_id: str,
        source_hashes: Iterable[str] = (),
        recall_memory_ids: Iterable[int] = (),
        descendant_sha256: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._memory_receipt()
        row = self.memory_ledger.append_experience(
            actor=actor,
            text=text,
            kind=kind,
            session_id=session_id,
            source_hashes=source_hashes,
            recall_memory_ids=recall_memory_ids,
            descendant_sha256=descendant_sha256,
            metadata=metadata,
        )
        receipt = self._memory_receipt()
        if receipt.tip_sha256 != row["record_sha256"]:
            raise RuntimeError("memory append receipt tip mismatch")
        return row

    def get_memory_record(
        self,
        memory_id: int,
        *,
        expected_record_sha256: str | None = None,
    ) -> dict[str, Any]:
        return get_verified_memory_record(
            self.memory_path,
            memory_id,
            parent_sha256=self.memory_parent_sha256,
            expected_record_sha256=expected_record_sha256,
        )

    @staticmethod
    def _drive(operation_sha256: str) -> list[float]:
        drive: list[float] = []
        for index in range(54):
            digest = hashlib.sha256(f"{operation_sha256}:{index}".encode("ascii")).digest()
            unit = int.from_bytes(digest[:8], "big") / float((1 << 64) - 1)
            drive.append(2.0 * unit - 1.0)
        return drive

    def advance_state(self, kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        normalized_kind = str(kind).strip()
        if not normalized_kind:
            raise ValueError("state transition kind must be non-empty")
        operation = {"kind": normalized_kind, "payload": dict(payload)}
        operation_sha256 = sha256_json(operation)
        logical_timestamp = self.clock.take()
        previous_family = copy.deepcopy(self.state_family.as_dict())
        previous_step = self.state_family.step
        family_state = self.state_family.update(self._drive(operation_sha256))
        event_payload = {
            "operation_kind": normalized_kind,
            "operation_payload_sha256": sha256_json(dict(payload)),
            "state_family_step": self.state_family.step,
            "state_family_sha256": sha256_json(family_state),
        }
        all_prior_events = list(self.reality_events) + list(self.run_r12_events)
        parent_event_sha256 = str(all_prior_events[-1].get("event_sha256") or ZERO_SHA256) if all_prior_events else ZERO_SHA256
        event_body = {
            "schema": "zeref-reality-event-v1",
            "event_id": f"persistent-substrate-{len(self.run_r12_events) + 1:08d}",
            "created_at_utc": logical_timestamp,
            "provenance_class": "synthetic",
            "source_type": "deterministic_software_state_transition",
            "source_id": f"{EXPERIMENT_ID}:{self.condition_id}:{self.state_family.step}",
            "source_sha256": operation_sha256,
            "payload_sha256": reality_sha256_json(event_payload),
            "payload": event_payload,
            "parent_event_sha256": parent_event_sha256,
            "transform": "sha256-derived-54-value-drive",
            "confidence": 0.0,
            "claim_boundary": CLAIM_BOUNDARY,
        }
        event = {**event_body, "event_sha256": reality_sha256_json(event_body)}
        next_r12 = derive_r12_transition(all_prior_events, event, self.r12_state, query=normalized_kind)
        state_payload = {
            "operation": operation,
            "operation_sha256": operation_sha256,
            "state_family": family_state,
            "state_family_sha256": sha256_json(family_state),
            "r12_state": next_r12,
            "r12_state_sha256": str(next_r12["state_sha256"]),
            "synthetic_event_sha256": event["event_sha256"],
        }
        try:
            state_row = self.state_ledger.append(normalized_kind, state_payload, logical_timestamp)
        except BaseException:
            self.state_family.step = previous_step
            for name, values in previous_family.items():
                setattr(self.state_family, name, values)
            raise
        self.r12_state.clear()
        self.r12_state.update(next_r12)
        self.r12_history.append(copy.deepcopy(next_r12))
        self.run_r12_events.append(event)
        return state_row

    def query_knowledge_sentinel(self, query: str, *, knowledge_id: int = 1) -> dict[str, Any]:
        fusion = dict(self.routing_config.get("fusion") or {})
        ranked = self.world_router.rank(
            str(query),
            sequence=int(self.r12_state.get("sequence") or 0),
            dyn12=self.state_family.dyn12,
            r12_state=self.r12_state,
            limit=int(fusion.get("rank_limit") or 8),
            lexical_prefilter=int(fusion.get("lexical_prefilter") or 128),
        )
        selected = dict(ranked[0]) if ranked else None
        return {
            "query": str(query),
            "query_sha256": hashlib.sha256(str(query).encode("utf-8")).hexdigest(),
            "expected_knowledge_id": int(knowledge_id),
            "selected": selected,
            "candidates": [dict(item) for item in ranked],
        }

    def snapshot(self, stage: str, *, active_model_identity: Mapping[str, Any] | None) -> dict[str, Any]:
        if self._closed:
            raise RuntimeError("persistent substrate is closed")
        self._verify_object_graph()
        self._verify_immutable_inputs()
        memory = self._memory_receipt()
        state = self.state_ledger.verify()
        knowledge = self.world_store.snapshot_receipt()
        return {
            "experiment_id": EXPERIMENT_ID,
            "condition_id": self.condition_id,
            "stage": str(stage),
            "stores": dict(self._stores),
            "object_tokens": dict(self._object_tokens),
            "object_identity_verified": True,
            "memory": {
                "path": str(self.memory_path),
                "sha256": memory.sha256,
                "bytes": memory.byte_length,
                "record_count": memory.record_count,
                "tip_sha256": memory.tip_sha256,
                "parent_sha256": memory.parent_sha256,
                "prefix_bytes": len(self._canonical_prefix_bytes),
                "prefix_sha256": hashlib.sha256(self._canonical_prefix_bytes).hexdigest(),
            },
            "state": {
                "path": str(self.state_ledger.path),
                "sha256": state.sha256,
                "bytes": state.byte_length,
                "event_count": state.record_count,
                "tip_sha256": state.tip_sha256,
                "state_family_step": self.state_family.step,
                "state_family": self.state_family.as_dict(),
                "r12_state": copy.deepcopy(self.r12_state),
                "r12_history_records": len(self.r12_history),
                "run_r12_event_count": len(self.run_r12_events),
            },
            "routing": {
                "config_sha256": self._immutable_inputs["routing_config"]["sha256"],
                "config": copy.deepcopy(self.routing_config),
                "personal_router": type(self.personal_router).__name__,
                "world_router": type(self.world_router).__name__,
            },
            "knowledge": knowledge,
            "immutable_inputs": copy.deepcopy(self._immutable_inputs),
            "implementation_hashes": dict(self._implementation_hashes),
            "active_model_identity": dict(active_model_identity) if active_model_identity is not None else None,
        }

    def close(self) -> None:
        if self._closed:
            return
        self.memory_ledger.close()
        self.world_store.close()
        self._closed = True
