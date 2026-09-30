"""Stage-level signal trace of real DurableRuntime turns.

Every value in a trace record is read from the running runtime at the stage
boundary where it exists: the normalized event, the dyn12/dyn42 vectors before
and after the state update, the CNS controller values, the R12 ranked records
with their score components, the exact prompt and model output, the authority
decision, the Hebbian association rows touched by this turn (measured before
and after the memory write inside the same SQLite transaction), the memory ids
written, and the committed checkpoint. Nothing is synthesized for display.

Traces are written outside the runtime root, are never checkpointed, and are
hash-chained so an edited or reordered record fails `verify_trace_file`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..durable import DurableRuntime
from ..hashutil import sha256_obj
from ..memory import _tokens

TRACE_SCHEMA = "omega-signal-trace-v1"
GENESIS = "0" * 64
_MAX_TEXT = 4000


def _clip(text: str, limit: int = _MAX_TEXT) -> str:
    return text if len(text) <= limit else text[:limit] + f"…[+{len(text) - limit} chars]"


def _concepts(text: str) -> list[str]:
    """The exact concept list `ReconciliationMemory._hebbian_update` uses."""
    return list(dict.fromkeys(_tokens(text)))[:32]


class TraceWriter:
    """Append-only, hash-chained JSONL trace outside the runtime root."""

    def __init__(self, path: str | Path, runtime_root: str | Path | None = None):
        self.path = Path(path)
        if runtime_root is not None:
            root = Path(runtime_root).resolve()
            if root == self.path.resolve().parent or root in self.path.resolve().parents:
                raise ValueError("trace file must live outside the runtime root")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.head = GENESIS
        self.count = 0
        if self.path.exists():
            records = verify_trace_file(self.path)
            if records:
                self.head = records[-1]["record_sha256"]
                self.count = len(records)

    def append(self, body: dict[str, Any]) -> dict[str, Any]:
        record = {"schema": TRACE_SCHEMA, "index": self.count, "prev_sha256": self.head, **body}
        record["record_sha256"] = sha256_obj(record)
        with self.path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
            out.flush()
        self.head = record["record_sha256"]
        self.count += 1
        return record


def verify_trace_file(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    head = GENESIS
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        record = json.loads(line)
        claimed = record.pop("record_sha256", None)
        if record.get("index") != number or record.get("prev_sha256") != head or sha256_obj(record) != claimed:
            raise ValueError(f"trace chain broken at record {number}")
        record["record_sha256"] = claimed
        head = claimed
        records.append(record)
    return records


class TracedDurableRuntime(DurableRuntime):
    """DurableRuntime whose stage hooks also record the values that flowed through them."""

    def __init__(self, root: str | Path, provider=None, *, trace_path: str | Path, trace_label: str = "", **kwargs):
        self.trace_writer = TraceWriter(trace_path, runtime_root=root)
        self.trace_label = trace_label
        self._signal: dict[str, Any] = {}
        self._assoc_before: dict[tuple[str, str], tuple[float, int]] = {}
        self._assoc_totals_before: tuple[int, float] = (0, 0.0)
        self._pending_text = ""
        self._hebbian_concepts: list[str] = []
        super().__init__(root, provider, **kwargs)

    def _association_rows(self, concepts: list[str]) -> dict[tuple[str, str], tuple[float, int]]:
        if not concepts:
            return {}
        marks = ",".join("?" for _ in concepts)
        rows = self.memory.db.execute(
            f"SELECT a,b,weight,updates FROM associations WHERE a IN ({marks}) AND b IN ({marks})",
            (*concepts, *concepts),
        ).fetchall()
        return {(str(r["a"]), str(r["b"])): (float(r["weight"]), int(r["updates"])) for r in rows}

    def _association_totals(self) -> tuple[int, float]:
        row = self.memory.db.execute("SELECT COUNT(*), COALESCE(SUM(weight),0) FROM associations").fetchone()
        return int(row[0]), float(row[1])

    def _retrieve_memories(self, text):
        hits = super()._retrieve_memories(text)
        self._pending_text = text
        family = self.synaptic.state_family
        self._signal["memory_lookup"] = {
            "lexical_hits": [{"memory_id": h.id, "score": round(h.score, 6), "kind": h.kind} for h in hits],
        }
        self._signal["state_before"] = {
            "family_step": family.step,
            "dyn12": list(family.dyn12),
            "dyn42_sha256": sha256_obj(family.dyn42),
            "cns_step": self.cns.step,
            "cns_dark_matter": dict(self.cns.dark_matter),
            "cns_trust": self.cns.plasticity.get("trust"),
        }
        self._assoc_totals_before = self._association_totals()
        return hits

    def _route_memories(self, text, memories, state):
        family = self.synaptic.state_family
        self._signal["state_after"] = {
            "family_step": family.step,
            "state_family_dyn12": list(family.dyn12),
            "mission_dyn12_after_cns": list(state.dyn12),
            "dyn42_sha256": sha256_obj(family.dyn42),
            "phos_readout": getattr(state, "phos", None),
            "cns_step": self.cns.step,
            "cns_dark_matter": dict(self.cns.dark_matter),
            "cns_trust": self.cns.plasticity.get("trust"),
            "drive_dimension": self.synaptic.last_packet.get("drive_dimension"),
        }
        routed = super()._route_memories(text, memories, state)
        self._signal["r12"] = {
            "router": self._routing.get("router"),
            "r12_state_sha256": self._routing.get("state_sha256"),
            "reality_coupling": float(self.r12_state.get("vector", {}).get("reality_coupling", 0.0)),
            "ranked": [
                {
                    "memory_id": r["memory_id"],
                    "kind": r["kind"],
                    "score": round(float(r["score"]), 6),
                    "components": {k: round(float(v), 6) for k, v in r.get("components", {}).items()},
                    "text": _clip(r["text"], 240),
                }
                for r in self.last_ranked_records
            ],
            "context_sha256": self._routing.get("context_sha256"),
        }
        return routed

    def _validate_response(self, response):
        concepts = set(_concepts(self._pending_text))
        if isinstance(response, str):
            concepts |= set(_concepts(response))
        self._hebbian_concepts = sorted(concepts)
        self._assoc_before = self._association_rows(self._hebbian_concepts)
        super()._validate_response(response)

    def _trace_stage(self, stage):
        super()._trace_stage(stage)
        if stage == "model":
            receipt = getattr(self.provider, "receipt", {}) or {}
            measured = getattr(self.provider, "measurements", {}) or {}
            self._signal["model"] = {
                "provider": receipt.get("provider"),
                "model": receipt.get("model"),
                "prompt": _clip(str(receipt.get("prompt", ""))),
                "prompt_sha256": receipt.get("prompt_sha256"),
                "output_sha256": receipt.get("output_sha256"),
                "provider_ms": measured.get("provider_ms"),
                "input_characters": measured.get("input_characters"),
                "output_characters": measured.get("output_characters"),
            }
        elif stage == "bounded_output":
            self._signal["authority"] = {
                "granted_capabilities": sorted(self.policy.allowed),
                "tool_result": dict(self._tool_result),
            }
        elif stage == "memory_write":
            after_totals = self._association_totals()
            last = self.memory.db.execute(
                "SELECT id,kind,text FROM memories ORDER BY id DESC LIMIT 2"
            ).fetchall()
            after = self._association_rows(self._hebbian_concepts)
            changed = []
            for pair, (weight, updates) in after.items():
                prior = self._assoc_before.get(pair)
                if prior != (weight, updates):
                    changed.append({
                        "a": pair[0], "b": pair[1],
                        "weight_before": prior[0] if prior else 0.0,
                        "weight_after": weight,
                        "updates_before": prior[1] if prior else 0,
                        "updates_after": updates,
                    })
            changed.sort(key=lambda c: (-c["weight_after"], c["a"], c["b"]))
            self._signal["hebbian"] = {
                "rule": "co-occurrence +0.25 per pair per stored text, cap 100 (ReconciliationMemory._hebbian_update)",
                "associations_before": self._assoc_totals_before[0],
                "associations_after": after_totals[0],
                "weight_sum_before": round(self._assoc_totals_before[1], 4),
                "weight_sum_after": round(after_totals[1], 4),
                "pairs_changed": len(changed),
                "top_changed": changed[:24],
                "before_measurement": "read inside the turn transaction after the model returned, before any write",
            }
            self._signal["memory_write"] = {
                "rows": [{"memory_id": int(r["id"]), "kind": r["kind"], "text": _clip(str(r["text"]), 400)}
                         for r in reversed(last)],
                "stats": self.memory.stats(),
            }

    def _respond_event_serial(self, event, *, transient_context: str = ""):
        self._signal = {}
        started = time.time()
        try:
            result = super()._respond_event_serial(event, transient_context=transient_context)
        except BaseException as exc:
            self.trace_writer.append({
                "label": self.trace_label, "status": "FAILED_ROLLED_BACK", "wall_time": started,
                "error_type": type(exc).__name__, "error": str(exc)[:300],
                "partial_signal": self._signal, "system_id": self.system_id,
            })
            raise
        self.trace_writer.append({
            "label": self.trace_label,
            "status": "COMMITTED",
            "wall_time": started,
            "system_id": self.system_id,
            "turn": self.turn,
            "event": result["event"],
            "stages": result["trace"],
            "signal": self._signal,
            "response": _clip(result["response"]),
            "checkpoint": {k: result["checkpoint"].get(k) for k in ("sequence", "sha256")},
            "ledger_head": result["ledger_head"],
            "metrics": result.get("metrics", {}),
        })
        return result
