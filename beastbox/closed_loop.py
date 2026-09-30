"""Host-authorized CNS→nonphysical R12→reviewed adaptive rank handoff.

This module never grants model/tool authority, automatically learns from model
text, fabricates measured hardware data, modifies a pretrained checkpoint, or
relabels a synthetic observation as an external measurement.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .hashutil import sha256_obj, sha256_text
from .reality_memory import (
    CLAIM_BOUNDARY, ZERO_SHA256, derive_r12_transition, sha256_json,
)
from .refractive_memory import WEIGHTS
from .unicode_text import checked_utf8

PROFILE = "cosmos-software-closed-loop-v1"
FIT_SCHEMA = "finisher-adaptive-feedback-control-v1"


def reviewed_weights(receipt: Mapping[str, Any] | None) -> dict[str, float] | None:
    """Validate a host-injected receipt from the existing product fit method.

    This validates form, NOT signatures or whether a person actually reviewed
    the labels. Only trusted host configuration may supply a receipt.
    """
    if receipt is None:
        return None
    if not isinstance(receipt, Mapping):
        raise ValueError("host adaptive receipt must be a mapping")
    if receipt.get("schema") != FIT_SCHEMA or receipt.get("algorithm") != "bounded-reviewed-pairwise-reweighting":
        raise ValueError("use an original host supplied AdaptiveControl.fit receipt")
    if type(receipt.get("examples")) is not int or not 2 <= receipt["examples"] <= 256:
        raise ValueError("adaptive weights require 2..256 claimed reviewed examples")
    if receipt.get("trained_model_weights") is not False:
        raise ValueError("adaptive routing may not alter model parameters")
    if receipt.get("frozen_weights") != dict(WEIGHTS):
        raise ValueError("adaptive router original component contract does not match")
    weights = receipt.get("learned_weights")
    if not isinstance(weights, Mapping) or set(weights) != set(WEIGHTS):
        raise ValueError("adaptive router missing original component")
    if any(type(x) not in (float, int) or not math.isfinite(x) or x <= 0 or x > 1 for x in weights.values()):
        raise ValueError("adaptive weights must be strictly positive finite fractions")
    if abs(sum(weights.values()) - 1) > 1e-6:
        raise ValueError("adaptive weights must be normalized to unit sum")
    return {key:float(weights[key]) for key in WEIGHTS}


def host_software_event(
    normalized: Mapping[str, Any], *, turn: int,
    prior_state: Mapping[str, Any], cns_dyn12: Sequence[float],
) -> dict[str, Any]:
    """Verified nonphysical event derived entirely from one normalized input.

    A normalized sensor-event-v1 text/software/synthetic-demo source provides
    NO independently verified physical measurement. Other physical adapters
    must supply a separate, validated measured ledger event; never infer one.
    """
    source = normalized.get("source")
    text = normalized.get("text")
    if source not in {"text", "synthetic-demo", "software-event"}:
        raise ValueError("closed-loop source is not an authenticated normalized software event")
    if not isinstance(text, str) or not 1 <= len(text) <= 8192:
        raise ValueError("closed-loop requires bounded normalized Unicode text")
    checked_utf8(text)
    if type(turn) is not int or turn <= 0 or len(cns_dyn12) != 12:
        raise ValueError("closed-loop requires real positive turn and twelve-dimensional CNS")
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in cns_dyn12):
        raise ValueError("closed-loop state must be finite")
    if normalized.get("schema") != "normalized-event-v1":
        raise ValueError("only original normalized host events may be routed")
    if normalized.get("sha256") != sha256_obj({
        "schema":"normalized-event-v1",
        "source":source,"text":text,"features":normalized.get("features"),
    }):
        raise ValueError("invalid normalized input digest")
    parent = prior_state.get("triggering_event_sha256")
    if not isinstance(parent, str) or len(parent) != 64:
        raise ValueError("missing prior hash-linked R12 event")
    payload = {
        "condition": "nonphysical_software_input",
        "normalized_event_sha256": normalized["sha256"],
        "cns_dyn12_sha256": sha256_obj(list(cns_dyn12)),
    }
    # The environment's canonical event hash includes its creation timestamp;
    # the entire sanitized event is preserved in the durable provenance receipt.
    body = {
        "schema":"zeref-reality-event-v1",
        "event_id":f"software-turn-{turn:010d}-{normalized['sha256'][:12]}",
        "created_at_utc":datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provenance_class":"synthetic" if source=="synthetic-demo" else "derived",
        "source_type":"normalized-software-input",
        "source_id":f"software-turn-{turn}",
        "source_sha256":sha256_text(text),
        "payload":payload,
        "parent_event_sha256":parent,
        "transform":"host-CNS-derived-nonphysical-R12; NO hardware measurement",
        "confidence":0.0,
        "claim_boundary":CLAIM_BOUNDARY,
    }
    body["payload_sha256"] = sha256_json(payload)
    return {**body, "event_sha256":sha256_json(body)}


def advance_nonphysical_r12(
    previous: Mapping[str, Any], event: Mapping[str, Any], query: str,
) -> dict[str, Any]:
    """Only valid hash-bound nonphysical events may advance software R12."""
    if event.get("provenance_class") not in {"synthetic", "derived"}:
        raise ValueError("unprivileged host adapter refuses measured reality events")
    if event.get("confidence") != 0.0:
        raise ValueError("nonphysical input may not invent measurement confidence")
    if event.get("parent_event_sha256") != previous.get("triggering_event_sha256"):
        raise ValueError("R12 event parent SHA mismatch")
    state = derive_r12_transition([], event, previous, query=query)
    if (state["sequence"] != previous["sequence"] + 1
        or state["previous_state_sha256"] != previous["state_sha256"]
        or state["triggering_event_sha256"] != event["event_sha256"]
        or state["vector"]["reality_coupling"] >
            float(previous["vector"]["reality_coupling"])+1e-12):
        raise RuntimeError("nonphysical R12 transition violated original reality limits")
    return state


def rerank_with_host_review(
    candidates: Sequence[dict[str, Any]], weights: Mapping[str, float],
) -> list[dict[str, Any]]:
    """Only original immutable per-memory feature components, no hidden magic."""
    if set(weights) != set(WEIGHTS):
        raise ValueError("unknown original router feature mapping")
    rescored = []
    for original in candidates:
        item = dict(original)
        components = item.get("components")
        if not isinstance(components, Mapping) or set(WEIGHTS) - set(components):
            raise RuntimeError("frozen R12 component scores are incomplete")
        score = sum(float(weights[key]) * float(components[key]) for key in WEIGHTS)
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise RuntimeError("nonfinite or out-of-bound trained R12 routing score")
        item["score"] = score
        rescored.append(item)
    rescored.sort(key=lambda x:(x["score"],x["memory_id"]),reverse=True)
    return rescored


class ReviewedSnapshotDB:
    """Allow exactly the two historical read queries from AdaptiveControl.fit.

    Fit sees the SAME active-only source snapshot as the real R12 inference
    router. Archived records cannot silently participate as training rivals.
    No writes, general SQL, attached databases or second source scans.
    """

    def __init__(self, rows: Sequence[Any]):
        from .retrieval_snapshot import ReadOnlySnapshotDB
        self._count = len(rows)
        self._snapshot = ReadOnlySnapshotDB(list(rows))

    def execute(self, sql: str, *args: Any):
        if sql == "SELECT COUNT(*) FROM memories" and not args:
            class CountCursor:
                def fetchone(self_inner):
                    return (self._count,)
            return CountCursor()
        return self._snapshot.execute(sql, *args)
