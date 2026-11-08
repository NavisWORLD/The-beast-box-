"""One append-only lived chain per creature subject.

The writer commits a sample, its event, and the snapshot together. It does not
call a model, a knowledge bank, or a quantum device. Study records share the
chain so a later study loop can land here; this module does not run that loop.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .hashutil import canonical_json, sha256_obj, sha256_text
from .lived_events import (
    STALE_MS,
    ChainRejected,
    IdentityRejected,
    SampleRejected,
    blank_channels,
    blank_mask,
    make_snapshot,
    reduce_sensor,
    validate_attachment,
    validate_sample,
    validate_study_arc,
    validate_study_lesson,
    validate_study_request,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS lived_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lived_events (
  sequence INTEGER PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE,
  payload TEXT NOT NULL,
  sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lived_snapshots (
  sequence INTEGER PRIMARY KEY,
  payload TEXT NOT NULL,
  sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lived_dedup (
  session_id TEXT NOT NULL,
  consent_epoch INTEGER NOT NULL,
  source_seq INTEGER NOT NULL,
  event_id TEXT NOT NULL,
  PRIMARY KEY (session_id, consent_epoch, source_seq)
);
CREATE TABLE IF NOT EXISTS lived_revocations (
  session_id TEXT NOT NULL,
  consent_epoch INTEGER NOT NULL,
  event_id TEXT NOT NULL,
  PRIMARY KEY (session_id, consent_epoch)
);
"""


class _Writer:
    """Connection facade whose trace callback can abort a write.

    sqlite3 prints and ignores exceptions raised from its own trace hook, so a
    failed snapshot insert would otherwise commit the event beside it.
    """

    def __init__(self, db: sqlite3.Connection):
        self._db = db
        self._trace = None

    def set_trace_callback(self, callback):
        self._trace = callback
        return self._db.set_trace_callback(callback)

    def execute(self, sql, params=()):
        if self._trace is not None:
            self._trace(sql)
        return self._db.execute(sql, params)

    def executemany(self, sql, seq):
        if self._trace is not None:
            self._trace(sql)
        return self._db.executemany(sql, seq)

    def commit(self):
        return self._db.commit()

    def rollback(self):
        return self._db.rollback()

    def close(self):
        return self._db.close()


class LivedStore:
    def __init__(self, db: sqlite3.Connection | _Writer, attachment: Mapping[str, Any], *, owned: bool):
        self.db = db if isinstance(db, _Writer) else _Writer(db)
        self.attachment = dict(attachment)
        self.subject_id = str(attachment["subject_id"])
        self.scope = str(attachment["scope"])
        self._owned = owned

    @classmethod
    def open(cls, path: str | Path, attachment: Mapping[str, Any]) -> "LivedStore":
        checked = validate_attachment(attachment)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(target)
        db.row_factory = sqlite3.Row
        try:
            store = cls.attach(db, checked, owned=True)
            db.commit()
            return store
        except BaseException:
            db.rollback()
            db.close()
            raise

    @classmethod
    def attach(
        cls, db: sqlite3.Connection, attachment: Mapping[str, Any], *, owned: bool = False,
    ) -> "LivedStore":
        checked = attachment if "initial_state_kind" in attachment else validate_attachment(attachment)
        store = cls(db, checked, owned=owned)
        store._ensure_schema()
        store._verify_or_create()
        return store

    def close(self) -> None:
        if self._owned:
            self.db.close()

    def read_lived_snapshot(self, scope: str) -> dict[str, Any]:
        if scope != self.scope:
            raise IdentityRejected("identity", "this chain does not serve that scope")
        row = self.db.execute(
            "SELECT payload FROM lived_snapshots ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise ChainRejected("history", "refusing zero reconstruction of missing snapshot history")
        payload = self._load(row["payload"] if not isinstance(row, tuple) else row[0])
        if payload.get("subject_id") != self.subject_id:
            raise IdentityRejected("identity", "snapshot subject does not match this chain")
        return payload

    def events(self) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT payload FROM lived_events ORDER BY sequence"
        ).fetchall()
        return [self._load(row["payload"] if not isinstance(row, tuple) else row[0]) for row in rows]

    def admit_sensor(
        self, sample: Mapping[str, Any], *, now_ms: int, external_transaction: bool = False,
    ) -> dict[str, Any]:
        canonical = validate_sample(sample)
        self._check_clock(now_ms)
        return self._atomic(external_transaction, lambda: self._admit(canonical, now_ms))

    def revoke_feed(
        self, *, session_id: str, consent_epoch: int, now_ms: int, external_transaction: bool = False,
    ) -> dict[str, Any]:
        self._check_clock(now_ms)
        if type(session_id) is not str or type(consent_epoch) is not int or consent_epoch < 0:
            raise SampleRejected("invalid", "revocation needs a session and consent epoch")
        return self._atomic(
            external_transaction, lambda: self._revoke(session_id, consent_epoch, now_ms),
        )

    def append_study_request(
        self, *, topic: str, now_ms: int, subject_id: str | None = None, external_transaction: bool = False,
    ) -> dict[str, Any]:
        body = validate_study_request({"topic": topic, **({} if subject_id is None else {"subject_id": subject_id})}, subject_id=self.subject_id)
        return self._atomic(external_transaction, lambda: self._append_study("study_request", body, now_ms))

    def append_study_lesson(
        self, *, topic: str, narration: str, source: str, license: str, now_ms: int,
        label: str = "TAUGHT", subject_id: str | None = None, external_transaction: bool = False,
        **extra: Any,
    ) -> dict[str, Any]:
        raw = {
            "topic": topic, "narration": narration, "source": source, "license": license, "label": label,
            **({} if subject_id is None else {"subject_id": subject_id}),
            **extra,
        }
        body = validate_study_lesson(raw, subject_id=self.subject_id)
        return self._atomic(external_transaction, lambda: self._append_study("study_lesson", body, now_ms))

    def append_study_arc(
        self, *, stage: str, topic: str, now_ms: int, subject_id: str | None = None,
        request_event_id: str | None = None, lesson_event_id: str | None = None,
        external_transaction: bool = False,
    ) -> dict[str, Any]:
        raw: dict[str, Any] = {"stage": stage, "topic": topic}
        if subject_id is not None:
            raw["subject_id"] = subject_id
        if request_event_id is not None:
            raw["request_event_id"] = request_event_id
        if lesson_event_id is not None:
            raw["lesson_event_id"] = lesson_event_id
        body = validate_study_arc(raw, subject_id=self.subject_id)
        return self._atomic(external_transaction, lambda: self._append_study("study_arc", body, now_ms))

    def _atomic(self, external: bool, work):
        if external:
            return work()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            result = work()
            self.db.commit()
            return result
        except BaseException:
            self.db.rollback()
            raise

    def _ensure_schema(self) -> None:
        for statement in _SCHEMA.split(";"):
            sql = statement.strip()
            if sql:
                self.db.execute(sql)

    def _verify_or_create(self) -> None:
        rows = self.db.execute("SELECT key, value FROM lived_meta").fetchall()
        if not rows:
            self._create_segment()
            return
        meta = {row["key"] if not isinstance(row, tuple) else row[0]: row["value"] if not isinstance(row, tuple) else row[1] for row in rows}
        self._matches(meta)
        self._replay()

    def _create_segment(self) -> None:
        att = self.attachment
        meta = {
            "subject_id": att["subject_id"],
            "scope": att["scope"],
            "basis": att["basis"],
            "origin_commitment": att["origin_commitment"],
            "prior_head": att["prior_head"],
            "segment": "continuation",
            "initial_state_json": canonical_json(att["initial_state12"]),
            "initial_state_kind": att["initial_state_kind"],
            "projection": "sensor-drive-dyn12-v1",
        }
        self.db.executemany("INSERT INTO lived_meta(key, value) VALUES(?, ?)", meta.items())
        snapshot = make_snapshot(
            subject_id=self.subject_id,
            scope=self.scope,
            sequence=0,
            state12=list(att["initial_state12"]),
            chain_head=att["prior_head"],
            origin_commitment=att["origin_commitment"],
            prior_head=att["prior_head"],
            channels=blank_channels(),
            face=None,
            feelings=None,
            presence_mask=blank_mask(),
            initial_state_kind=att["initial_state_kind"],
        )
        self._insert_snapshot(snapshot)

    def _matches(self, meta: Mapping[str, str]) -> None:
        att = self.attachment
        if meta.get("subject_id") != att["subject_id"] or meta.get("scope") != att["scope"]:
            raise IdentityRejected("identity", "this chain belongs to a different subject")
        if meta.get("origin_commitment") != att["origin_commitment"] or meta.get("prior_head") != att["prior_head"]:
            raise ChainRejected("origin", "configured origin or prior head does not match the continuation")
        if meta.get("basis") != att["basis"] or meta.get("segment") != "continuation":
            raise ChainRejected("origin", "continuation segment does not match the attachment")
        stored_initial = json.loads(meta["initial_state_json"])
        if not isinstance(stored_initial, list):
            raise ChainRejected("history", "refusing zero reconstruction of missing snapshot history")
        if att["initial_state_kind"] == "configured" and stored_initial != att["initial_state12"]:
            raise ChainRejected("history", "refusing to replace committed initial state with a new vector")
        if not self.db.execute("SELECT 1 FROM lived_snapshots LIMIT 1").fetchone():
            raise ChainRejected("history", "refusing zero reconstruction of missing snapshot history")

    def _replay(self) -> None:
        initial = self._snapshot_at(0)
        if initial is None:
            raise ChainRejected("history", "refusing zero reconstruction of missing snapshot history")
        head = self.attachment["prior_head"]
        current = initial
        rows = self.db.execute(
            "SELECT sequence, event_id, payload, sha256 FROM lived_events ORDER BY sequence"
        ).fetchall()
        for row in rows:
            payload = row["payload"] if not isinstance(row, tuple) else row[2]
            event_id = row["event_id"] if not isinstance(row, tuple) else row[1]
            digest = row["sha256"] if not isinstance(row, tuple) else row[3]
            sequence = row["sequence"] if not isinstance(row, tuple) else row[0]
            if sha256_text(payload) != digest or event_id != digest:
                raise ChainRejected("chain", "lived event hash does not match its payload")
            body = self._load(payload)
            if body.get("previous") != head or body.get("subject_id") != self.subject_id:
                raise ChainRejected("chain", "lived chain broke or crossed subjects")
            recomputed = self._transition(current, body)
            if recomputed["state_sha256"] != body["state_sha256"]:
                raise ChainRejected("chain", "replay did not reproduce the committed state")
            stored = self._snapshot_at(int(sequence))
            if stored is None or stored["state_sha256"] != recomputed["state_sha256"] or stored["chain_head"] != event_id:
                raise ChainRejected("history", "refusing zero reconstruction of missing snapshot history")
            current = stored
            head = event_id
        latest = self.read_lived_snapshot(self.scope)
        if latest["sequence"] != current["sequence"] or latest["chain_head"] != current["chain_head"]:
            raise ChainRejected("chain", "snapshot head does not match the replay")

    def _transition(self, previous: Mapping[str, Any], body: Mapping[str, Any]) -> dict[str, Any]:
        kind = body["kind"]
        if kind == "sensor":
            feelings, drive, state12, mask = reduce_sensor(previous, body["sample"], step=int(body["sequence"]))
            if feelings != body.get("feelings") or sha256_obj(drive) != body.get("drive_sha256"):
                raise ChainRejected("chain", "sensor replay did not reproduce the drive")
            return make_snapshot(
                subject_id=self.subject_id,
                scope=self.scope,
                sequence=int(body["sequence"]),
                state12=state12,
                chain_head=sha256_obj(dict(body)),
                origin_commitment=self.attachment["origin_commitment"],
                prior_head=self.attachment["prior_head"],
                channels=body["sample"]["channels"],
                face=body["sample"]["face"],
                feelings=feelings,
                presence_mask=mask,
                initial_state_kind=str(previous["initial_state_kind"]),
            )
        if kind in {"feed_off", "study_request", "study_lesson", "study_arc"}:
            channels = blank_channels() if kind == "feed_off" else previous["channels"]
            face = None if kind == "feed_off" else previous["face"]
            feelings = None if kind == "feed_off" else previous["feelings"]
            mask = blank_mask() if kind == "feed_off" else previous["presence_mask"]
            return make_snapshot(
                subject_id=self.subject_id,
                scope=self.scope,
                sequence=int(body["sequence"]),
                state12=list(previous["state12"]),
                chain_head=sha256_obj(dict(body)),
                origin_commitment=self.attachment["origin_commitment"],
                prior_head=self.attachment["prior_head"],
                channels=channels,
                face=face,
                feelings=feelings,
                presence_mask=mask,
                initial_state_kind=str(previous["initial_state_kind"]),
            )
        raise ChainRejected("chain", "unknown lived event kind")

    def _admit(self, sample: dict[str, Any], now_ms: int) -> dict[str, Any]:
        captured = int(sample["captured_at_ms"])
        if captured > now_ms:
            raise SampleRejected("future", "sample timestamp is in the future")
        if now_ms - captured > STALE_MS:
            raise SampleRejected("stale", "sample is older than the freshness window")
        session_id = sample["session_id"]
        epoch = int(sample["consent_epoch"])
        source_seq = int(sample["source_seq"])
        if self._revoked_epoch(session_id) is not None and epoch <= int(self._revoked_epoch(session_id)):
            raise SampleRejected("revoked", "consent epoch was revoked")
        existing = self.db.execute(
            "SELECT event_id FROM lived_dedup WHERE session_id=? AND consent_epoch=? AND source_seq=?",
            (session_id, epoch, source_seq),
        ).fetchone()
        if existing is not None:
            return self._duplicate(existing["event_id"] if not isinstance(existing, tuple) else existing[0])
        last = self.db.execute(
            "SELECT MAX(source_seq) FROM lived_dedup WHERE session_id=? AND consent_epoch=?",
            (session_id, epoch),
        ).fetchone()
        last_seq = last[0]
        if last_seq is not None and source_seq < int(last_seq):
            raise SampleRejected("reordered", "sample source sequence went backwards")
        previous = self.read_lived_snapshot(self.scope)
        sequence = int(previous["sequence"]) + 1
        feelings, drive, state12, mask = reduce_sensor(previous, sample, step=sequence)
        body = {
            "schema": "lived-event-v1",
            "kind": "sensor",
            "sequence": sequence,
            "previous": previous["chain_head"],
            "subject_id": self.subject_id,
            "scope": self.scope,
            "basis": "dyn12-v1",
            "projection": "sensor-drive-dyn12-v1",
            "origin_commitment": self.attachment["origin_commitment"],
            "admitted_at_ms": now_ms,
            "sample": sample,
            "feelings": feelings,
            "drive_sha256": sha256_obj(drive),
            "state12": [float(item) for item in state12],
            "state_sha256": sha256_obj([float(item) for item in state12]),
        }
        event_id = self._insert_event(body)
        self.db.execute(
            "INSERT INTO lived_dedup(session_id, consent_epoch, source_seq, event_id) VALUES(?, ?, ?, ?)",
            (session_id, epoch, source_seq, event_id),
        )
        snapshot = make_snapshot(
            subject_id=self.subject_id,
            scope=self.scope,
            sequence=sequence,
            state12=state12,
            chain_head=event_id,
            origin_commitment=self.attachment["origin_commitment"],
            prior_head=self.attachment["prior_head"],
            channels=sample["channels"],
            face=sample["face"],
            feelings=feelings,
            presence_mask=mask,
            initial_state_kind=str(previous["initial_state_kind"]),
        )
        self._insert_snapshot(snapshot)
        return self._receipt("admitted", "ok", event_id, body["previous"], snapshot)

    def _revoke(self, session_id: str, consent_epoch: int, now_ms: int) -> dict[str, Any]:
        current = self._revoked_epoch(session_id)
        if current is not None and consent_epoch < int(current):
            raise SampleRejected("revoked", "a newer consent epoch was already revoked")
        if current is not None and consent_epoch == int(current):
            row = self.db.execute(
                "SELECT event_id FROM lived_revocations WHERE session_id=? AND consent_epoch=?",
                (session_id, consent_epoch),
            ).fetchone()
            return self._duplicate(row["event_id"] if not isinstance(row, tuple) else row[0])
        previous = self.read_lived_snapshot(self.scope)
        sequence = int(previous["sequence"]) + 1
        body = {
            "schema": "lived-event-v1",
            "kind": "feed_off",
            "sequence": sequence,
            "previous": previous["chain_head"],
            "subject_id": self.subject_id,
            "scope": self.scope,
            "session_id": session_id,
            "consent_epoch": consent_epoch,
            "origin_commitment": self.attachment["origin_commitment"],
            "admitted_at_ms": now_ms,
            "state12": list(previous["state12"]),
            "state_sha256": previous["state_sha256"],
        }
        event_id = self._insert_event(body)
        self.db.execute(
            "INSERT INTO lived_revocations(session_id, consent_epoch, event_id) VALUES(?, ?, ?)",
            (session_id, consent_epoch, event_id),
        )
        snapshot = make_snapshot(
            subject_id=self.subject_id,
            scope=self.scope,
            sequence=sequence,
            state12=list(previous["state12"]),
            chain_head=event_id,
            origin_commitment=self.attachment["origin_commitment"],
            prior_head=self.attachment["prior_head"],
            channels=blank_channels(),
            face=None,
            feelings=None,
            presence_mask=blank_mask(),
            initial_state_kind=str(previous["initial_state_kind"]),
        )
        self._insert_snapshot(snapshot)
        receipt = self._receipt("admitted", "ok", event_id, body["previous"], snapshot)
        receipt["kind"] = "feed_off"
        return receipt

    def _append_study(self, kind: str, fields: Mapping[str, Any], now_ms: int) -> dict[str, Any]:
        self._check_clock(now_ms)
        previous = self.read_lived_snapshot(self.scope)
        sequence = int(previous["sequence"]) + 1
        body = {
            "schema": "lived-event-v1",
            "kind": kind,
            "sequence": sequence,
            "previous": previous["chain_head"],
            "subject_id": self.subject_id,
            "scope": self.scope,
            "origin_commitment": self.attachment["origin_commitment"],
            "admitted_at_ms": now_ms,
            "state12": list(previous["state12"]),
            "state_sha256": previous["state_sha256"],
            **dict(fields),
        }
        event_id = self._insert_event(body)
        snapshot = make_snapshot(
            subject_id=self.subject_id,
            scope=self.scope,
            sequence=sequence,
            state12=list(previous["state12"]),
            chain_head=event_id,
            origin_commitment=self.attachment["origin_commitment"],
            prior_head=self.attachment["prior_head"],
            channels=previous["channels"],
            face=previous["face"],
            feelings=previous["feelings"],
            presence_mask=previous["presence_mask"],
            initial_state_kind=str(previous["initial_state_kind"]),
        )
        self._insert_snapshot(snapshot)
        receipt = self._receipt("admitted", "ok", event_id, body["previous"], snapshot)
        receipt["kind"] = kind
        return receipt

    def _insert_event(self, body: dict[str, Any]) -> str:
        payload = canonical_json(body)
        digest = sha256_text(payload)
        self.db.execute(
            "INSERT INTO lived_events(sequence, event_id, payload, sha256) VALUES(?, ?, ?, ?)",
            (body["sequence"], digest, payload, digest),
        )
        return digest

    def _insert_snapshot(self, snapshot: dict[str, Any]) -> None:
        payload = canonical_json(snapshot)
        self.db.execute(
            "INSERT INTO lived_snapshots(sequence, payload, sha256) VALUES(?, ?, ?)",
            (snapshot["sequence"], payload, sha256_text(payload)),
        )

    def _snapshot_at(self, sequence: int) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT payload FROM lived_snapshots WHERE sequence=?", (sequence,)
        ).fetchone()
        if row is None:
            return None
        return self._load(row["payload"] if not isinstance(row, tuple) else row[0])

    def _revoked_epoch(self, session_id: str) -> int | None:
        row = self.db.execute(
            "SELECT MAX(consent_epoch) FROM lived_revocations WHERE session_id=?", (session_id,)
        ).fetchone()
        if row is None or row[0] is None:
            return None
        return int(row[0])

    def _duplicate(self, event_id: str) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT payload FROM lived_events WHERE event_id=?", (event_id,)
        ).fetchone()
        body = self._load(row["payload"] if not isinstance(row, tuple) else row[0])
        snap = self.read_lived_snapshot(self.scope)
        return self._receipt("duplicate", "duplicate", event_id, body["previous"], snap)

    def _receipt(self, status: str, code: str, event_id: str, previous: str, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema": "lived-admit-receipt-v1",
            "status": status,
            "code": code,
            "event_id": event_id,
            "sequence": snapshot["sequence"] if status == "duplicate" else snapshot["sequence"],
            "previous": previous,
            "chain_head": snapshot["chain_head"],
            "state_sha256": snapshot["state_sha256"],
            "subject_id": self.subject_id,
            "scope": self.scope,
        }

    def _check_clock(self, now_ms: int) -> None:
        if type(now_ms) is not int or now_ms < 0:
            raise SampleRejected("invalid", "now_ms must be an injected non-negative integer")

    @staticmethod
    def _load(payload: str) -> dict[str, Any]:
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise ChainRejected("chain", "lived payload was not an object")
        return value
