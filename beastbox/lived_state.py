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
from .lived_hebb import DT_MAX, RULE, RULES, active_rule, initial_weights, recorded_transition
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
CREATE TABLE IF NOT EXISTS lived_exchanges (
  exchange_id TEXT PRIMARY KEY,
  text_sha256 TEXT NOT NULL,
  heard_event_id TEXT,
  spoken_event_id TEXT,
  failure_event_id TEXT,
  status TEXT NOT NULL,
  outbox TEXT,
  acknowledged INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS lived_hebb (
  sequence INTEGER PRIMARY KEY,
  payload TEXT NOT NULL,
  sha256 TEXT NOT NULL
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

    def begin_exchange(
        self, *, exchange_id: str, text: str, now_ms: int, external_transaction: bool = False,
    ) -> dict[str, Any]:
        self._check_clock(now_ms)
        self._owner_only()
        checked_id = _exchange_id(exchange_id)
        checked = _exchange_text(text)
        return self._atomic(
            external_transaction, lambda: self._begin_exchange(checked_id, checked, now_ms),
        )

    def stage_exchange_reply(
        self, exchange_id: str, reply: str, model: str | None, *, external_transaction: bool = False,
    ) -> None:
        checked_id = _exchange_id(exchange_id)
        checked = _exchange_text(reply)
        label = _model_label(model)
        self._atomic(
            external_transaction, lambda: self._stage_reply(checked_id, checked, label),
        )

    def finish_exchange(
        self, *, exchange_id: str, reply: str, now_ms: int, model: str | None = None,
        external_transaction: bool = False,
    ) -> dict[str, Any]:
        self._check_clock(now_ms)
        self._owner_only()
        checked_id = _exchange_id(exchange_id)
        checked = _exchange_text(reply)
        label = _model_label(model)
        return self._atomic(
            external_transaction, lambda: self._finish_exchange(checked_id, checked, now_ms, label),
        )

    def fail_exchange(
        self, *, exchange_id: str, now_ms: int, external_transaction: bool = False,
        code: str = "undelivered",
    ) -> dict[str, Any]:
        self._check_clock(now_ms)
        self._owner_only()
        checked_id = _exchange_id(exchange_id)
        checked_code = code if code in {"undelivered", "invalid", "raw"} else "undelivered"
        return self._atomic(
            external_transaction, lambda: self._fail_exchange(checked_id, now_ms, checked_code),
        )

    def acknowledge_exchange(self, exchange_id: str, *, external_transaction: bool = False) -> None:
        checked_id = _exchange_id(exchange_id)
        self._atomic(external_transaction, lambda: self._acknowledge(checked_id))

    def exchange_row(self, exchange_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT exchange_id, text_sha256, heard_event_id, spoken_event_id, failure_event_id, status, outbox, acknowledged FROM lived_exchanges WHERE exchange_id=?",
            (_exchange_id(exchange_id),),
        ).fetchone()
        if row is None:
            return None
        if isinstance(row, tuple):
            keys = (
                "exchange_id", "text_sha256", "heard_event_id", "spoken_event_id",
                "failure_event_id", "status", "outbox", "acknowledged",
            )
            return dict(zip(keys, row))
        return {key: row[key] for key in row.keys()}

    def staged_reply(self, exchange_id: str) -> dict[str, Any] | None:
        row = self.exchange_row(exchange_id)
        if row is None or not row.get("outbox") or row.get("spoken_event_id") or row.get("failure_event_id"):
            return None
        payload = self._load(str(row["outbox"]))
        reply = payload.get("reply")
        if type(reply) is not str:
            return None
        model = payload.get("model")
        return {"reply": reply, "model": model if type(model) is str else None}

    def exchange_reply(self, event_id: str) -> str:
        body = self._event_body(event_id)
        text = body.get("text")
        if type(text) is not str:
            raise ChainRejected("chain", "recorded exchange has no private text")
        return text

    def exchange_receipt(self, event_id: str) -> dict[str, Any]:
        body = self._event_body(event_id)
        snap = self._snapshot_at(int(body["sequence"]))
        if snap is None:
            raise ChainRejected("history", "refusing zero reconstruction of missing snapshot history")
        status = "failed" if body.get("kind") == "exchange_failure" else "lived"
        return _public_exchange(body, event_id, snap, status=status)

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
        weights = initial_weights()
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
            if body.get("kind") == "exchange" and body.get("hebb_rule") in RULES:
                weights, replayed = self._replay_recorded(current, body, weights, int(sequence))
                recomputed = self._carry_snapshot(
                    current, int(body["sequence"]), event_id, state12=replayed,
                )
            else:
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
        if kind in {"feed_off", "study_request", "study_lesson", "study_arc", "exchange", "exchange_failure"}:
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

    def _owner_only(self) -> None:
        if self.scope != "owner":
            raise IdentityRejected("identity", "this chain does not accept another scope")

    def _begin_exchange(self, exchange_id: str, text: str, now_ms: int) -> dict[str, Any]:
        row = self.exchange_row(exchange_id)
        if row is not None and row.get("heard_event_id"):
            return self.exchange_receipt(str(row["heard_event_id"]))
        previous = self.read_lived_snapshot(self.scope)
        sequence = int(previous["sequence"]) + 1
        body, stepped = self._recorded_body(
            "heard", exchange_id, text, previous, sequence, now_ms,
        )
        event_id = self._insert_event(body)
        self._insert_hebb(sequence, stepped, previous["presence_mask"])
        self.db.execute(
            "INSERT INTO lived_exchanges(exchange_id, text_sha256, heard_event_id, spoken_event_id, failure_event_id, status, outbox, acknowledged) VALUES(?, ?, ?, NULL, NULL, 'open', NULL, 0)",
            (exchange_id, sha256_text(text), event_id),
        )
        snapshot = self._carry_snapshot(previous, sequence, event_id, state12=stepped["state12"])
        self._insert_snapshot(snapshot)
        return _public_exchange(body, event_id, snapshot, status="lived")

    def _stage_reply(self, exchange_id: str, reply: str, model: str | None) -> None:
        row = self.exchange_row(exchange_id)
        if row is None or not row.get("heard_event_id") or row.get("spoken_event_id") or row.get("failure_event_id"):
            raise ChainRejected("chain", "an exchange reply needs an open heard line")
        payload = {"reply": reply}
        if model is not None:
            payload["model"] = model
        self.db.execute(
            "UPDATE lived_exchanges SET outbox=? WHERE exchange_id=? AND spoken_event_id IS NULL AND failure_event_id IS NULL",
            (canonical_json(payload), exchange_id),
        )

    def _finish_exchange(self, exchange_id: str, reply: str, now_ms: int, model: str | None) -> dict[str, Any]:
        row = self.exchange_row(exchange_id)
        if row is None or not row.get("heard_event_id"):
            raise ChainRejected("chain", "a spoken line needs the heard line first")
        if row.get("spoken_event_id"):
            return self.exchange_receipt(str(row["spoken_event_id"]))
        if row.get("failure_event_id"):
            raise ChainRejected("chain", "a failed exchange cannot be rewritten as speech")
        previous = self.read_lived_snapshot(self.scope)
        sequence = int(previous["sequence"]) + 1
        causation = {
            "heard_event_id": str(row["heard_event_id"]),
            "snapshot_sequence": int(previous["sequence"]),
            "state_sha256": previous["state_sha256"],
        }
        body, stepped = self._recorded_body(
            "spoken", exchange_id, reply, previous, sequence, now_ms,
            model=model, causation=causation,
        )
        event_id = self._insert_event(body)
        self._insert_hebb(sequence, stepped, previous["presence_mask"])
        self.db.execute(
            "UPDATE lived_exchanges SET spoken_event_id=?, status='spoken' WHERE exchange_id=?",
            (event_id, exchange_id),
        )
        snapshot = self._carry_snapshot(previous, sequence, event_id, state12=stepped["state12"])
        self._insert_snapshot(snapshot)
        return _public_exchange(body, event_id, snapshot, status="lived")

    def _fail_exchange(self, exchange_id: str, now_ms: int, code: str = "undelivered") -> dict[str, Any]:
        row = self.exchange_row(exchange_id)
        if row is None or not row.get("heard_event_id"):
            raise ChainRejected("chain", "a failed exchange needs the heard line first")
        if row.get("failure_event_id"):
            return self.exchange_receipt(str(row["failure_event_id"]))
        if row.get("spoken_event_id"):
            raise ChainRejected("chain", "a spoken exchange cannot be rewritten as a failure")
        previous = self.read_lived_snapshot(self.scope)
        sequence = int(previous["sequence"]) + 1
        body = _exchange_event(
            "exchange_failure", "failed", None, exchange_id, None, previous, sequence, now_ms, self,
        )
        body["code"] = code
        event_id = self._insert_event(body)
        self.db.execute(
            "UPDATE lived_exchanges SET failure_event_id=?, status='failed', outbox=NULL WHERE exchange_id=?",
            (event_id, exchange_id),
        )
        snapshot = self._carry_snapshot(previous, sequence, event_id)
        self._insert_snapshot(snapshot)
        return _public_exchange(body, event_id, snapshot, status="failed")

    def _acknowledge(self, exchange_id: str) -> None:
        self.db.execute(
            "UPDATE lived_exchanges SET acknowledged=1, outbox=? WHERE exchange_id=? AND spoken_event_id IS NOT NULL",
            (canonical_json({"ack": True}), exchange_id),
        )

    def hebb_checkpoint(self) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT payload FROM lived_hebb ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        if row is None:
            snap = self.read_lived_snapshot(self.scope)
            weights = initial_weights()
            return {
                "rule": RULE,
                "basis": "dyn12-v1",
                "version": 1,
                "weights": weights,
                "prior_activation": [abs(float(item)) for item in snap["state12"]],
                "weights_sha256": sha256_obj(weights),
                "source_mask": dict(snap["presence_mask"]),
            }
        return self._load(row["payload"] if not isinstance(row, tuple) else row[0])

    def _weight_matrix(self) -> list[list[float]]:
        row = self.db.execute(
            "SELECT payload FROM lived_hebb ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return initial_weights()
        return self._load(row["payload"] if not isinstance(row, tuple) else row[0])["weights"]

    def _recorded_body(
        self, role: str, exchange_id: str, text: str, previous: Mapping[str, Any],
        sequence: int, now_ms: int, *, model: str | None = None,
        causation: Mapping[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        stepped = recorded_transition(
            previous["state12"], self._weight_matrix(), text, DT_MAX, sequence, rule=active_rule(),
        )
        body = _exchange_event(
            "exchange", role, "RECORDED", exchange_id, text, previous, sequence, now_ms, self,
            model=model, causation=causation,
        )
        body["state12"] = [float(item) for item in stepped["state12"]]
        body["state_sha256"] = sha256_obj(body["state12"])
        body["hebb_rule"] = stepped["rule"]
        body["projection"] = stepped["projection"]
        body["drive_label"] = stepped["drive_label"]
        body["dt"] = stepped["dt"]
        body["drive_sha256"] = sha256_obj(stepped["drive"])
        body["pre_activation"] = stepped["pre_activation"]
        body["weights_sha256"] = sha256_obj(stepped["weights"])
        return body, stepped

    def _insert_hebb(self, sequence: int, stepped: Mapping[str, Any], mask: Mapping[str, Any]) -> None:
        payload = {
            "schema": "lived-hebb-v1",
            "rule": stepped["rule"],
            "basis": stepped["basis"],
            "version": stepped["version"],
            "sequence": sequence,
            "weights": stepped["weights"],
            "prior_activation": stepped["pre_activation"],
            "weights_sha256": sha256_obj(stepped["weights"]),
            "source_mask": {key: int(mask[key]) for key in mask},
            "projection": stepped["projection"],
            "dt": stepped["dt"],
        }
        raw = canonical_json(payload)
        self.db.execute(
            "INSERT INTO lived_hebb(sequence, payload, sha256) VALUES(?, ?, ?)",
            (sequence, raw, sha256_text(raw)),
        )

    def _hebb_at(self, sequence: int) -> dict[str, Any] | None:
        row = self.db.execute(
            "SELECT payload FROM lived_hebb WHERE sequence=?", (sequence,)
        ).fetchone()
        if row is None:
            return None
        return self._load(row["payload"] if not isinstance(row, tuple) else row[0])

    def _replay_recorded(
        self, previous: Mapping[str, Any], body: Mapping[str, Any],
        weights: list[list[float]], sequence: int,
    ) -> tuple[list[list[float]], list[float]]:
        stepped = recorded_transition(
            previous["state12"], weights, str(body.get("text") or ""), body.get("dt", 0.0), sequence,
            rule=str(body.get("hebb_rule")),
        )
        if sha256_obj(stepped["state12"]) != body.get("state_sha256"):
            raise ChainRejected("chain", "replay did not reproduce the committed state")
        if sha256_obj(stepped["drive"]) != body.get("drive_sha256"):
            raise ChainRejected("chain", "replay did not reproduce the computed drive")
        if sha256_obj(stepped["weights"]) != body.get("weights_sha256"):
            raise ChainRejected("chain", "replay did not reproduce the co-firing weights")
        stored = self._hebb_at(sequence)
        if stored is None or sha256_obj(stored["weights"]) != body.get("weights_sha256"):
            raise ChainRejected("chain", "stored co-firing does not match the replay")
        return stepped["weights"], stepped["state12"]

    def _carry_snapshot(
        self, previous: Mapping[str, Any], sequence: int, event_id: str,
        state12: list[float] | None = None,
    ) -> dict[str, Any]:
        return make_snapshot(
            subject_id=self.subject_id,
            scope=self.scope,
            sequence=sequence,
            state12=list(previous["state12"] if state12 is None else state12),
            chain_head=event_id,
            origin_commitment=self.attachment["origin_commitment"],
            prior_head=self.attachment["prior_head"],
            channels=previous["channels"],
            face=previous["face"],
            feelings=previous["feelings"],
            presence_mask=previous["presence_mask"],
            initial_state_kind=str(previous["initial_state_kind"]),
        )

    def _event_body(self, event_id: str) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT payload FROM lived_events WHERE event_id=?", (event_id,)
        ).fetchone()
        if row is None:
            raise ChainRejected("chain", "lived exchange event is missing")
        return self._load(row["payload"] if not isinstance(row, tuple) else row[0])

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


def _exchange_id(value: str) -> str:
    if type(value) is not str or len(value) not in (32, 64):
        raise SampleRejected("invalid", "exchange id must be a hex digest")
    if any(ch not in "0123456789abcdef" for ch in value):
        raise SampleRejected("invalid", "exchange id must be a hex digest")
    return value


def _exchange_text(value: str) -> str:
    if type(value) is not str or not value.strip() or len(value) > 8192 or "\x00" in value:
        raise SampleRejected("invalid", "exchange text is empty or too long")
    lowered = value.lower()
    if "<html" in lowered or "<!doctype" in lowered:
        raise SampleRejected("raw", "exchange text cannot carry raw web text")
    return value


def _model_label(value: str | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise SampleRejected("invalid", "model label must be text")
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 180 or any(ord(ch) < 33 for ch in cleaned):
        raise SampleRejected("invalid", "model label is empty or too long")
    return cleaned


def _exchange_event(
    kind: str, role: str, label: str | None, exchange_id: str, text: str | None,
    previous: Mapping[str, Any], sequence: int, now_ms: int, store: LivedStore, *,
    model: str | None = None, causation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema": "lived-event-v1",
        "kind": kind,
        "role": role,
        "sequence": sequence,
        "previous": previous["chain_head"],
        "subject_id": store.subject_id,
        "scope": store.scope,
        "basis": "dyn12-v1",
        "origin_commitment": store.attachment["origin_commitment"],
        "admitted_at_ms": now_ms,
        "exchange_id": exchange_id,
        "state12": [float(item) for item in previous["state12"]],
        "state_sha256": previous["state_sha256"],
    }
    if label is not None:
        body["label"] = label
    if text is not None:
        body["text"] = text
        body["text_sha256"] = sha256_text(text)
        body["counts"] = {"chars": len(text), "utf8_bytes": len(text.encode("utf-8"))}
    if model is not None:
        body["model"] = model
    if causation is not None:
        body["causation"] = {
            "heard_event_id": causation["heard_event_id"],
            "snapshot_sequence": int(causation["snapshot_sequence"]),
            "state_sha256": causation["state_sha256"],
        }
    return body


def _public_exchange(body: Mapping[str, Any], event_id: str, snapshot: Mapping[str, Any], *, status: str) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": "lived-exchange-receipt-v1",
        "status": status,
        "role": body.get("role"),
        "exchange_id": body["exchange_id"],
        "event_id": event_id,
        "sequence": snapshot["sequence"],
        "previous": body["previous"],
        "chain_head": snapshot["chain_head"],
        "state_sha256": snapshot["state_sha256"],
        "scope": snapshot["scope"],
        "wrote": True,
    }
    if body.get("label"):
        receipt["label"] = body["label"]
    if body.get("text_sha256"):
        receipt["text_sha256"] = body["text_sha256"]
        receipt["counts"] = dict(body["counts"])
    if body.get("model"):
        receipt["model"] = body["model"]
    if body.get("causation"):
        receipt["causation"] = {
            "heard_event_id": body["causation"]["heard_event_id"],
            "snapshot_sequence": body["causation"]["snapshot_sequence"],
            "state_sha256": body["causation"]["state_sha256"],
        }
    return receipt
