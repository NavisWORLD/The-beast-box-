from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .refractive_memory import PHASE, QUALITY_WEIGHTS, R12_NAMES, _clamp01, _cosine12, _hash_unit, _normalize12
from .world_knowledge import WorldKnowledgeStore


def _validate_dyn12(dyn12: Sequence[float]) -> list[float]:
    if len(dyn12) != 12:
        raise ValueError("dyn12 must contain exactly 12 values")
    values = [float(value) for value in dyn12]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("dyn12 values must be finite")
    return values


def _query_position(query: str, *, sequence: int, dyn12: Sequence[float]) -> list[float]:
    drive = _validate_dyn12(dyn12)
    values: list[float] = []
    for index in range(12):
        base = 2.0 * _hash_unit(f"query:{query}:{index}") - 1.0
        orbit = 0.25 * math.sin((int(sequence) + 1) * (index + 1) * PHASE)
        values.append(math.tanh(base + orbit + 0.20 * drive[index]))
    return _normalize12(values)


def _world_position(
    knowledge_id: int,
    source_sha256: str,
    *,
    sequence: int,
    dyn12: Sequence[float],
) -> list[float]:
    drive = _validate_dyn12(dyn12)
    values: list[float] = []
    for index in range(12):
        identity = f"world:{int(knowledge_id)}:{source_sha256}:{index}"
        base = 2.0 * _hash_unit(identity) - 1.0
        phase = 2.0 * math.pi * _hash_unit(f"phase:{identity}")
        orbit = 0.25 * math.sin(phase + (int(sequence) + 1) * (index + 1) * PHASE)
        values.append(math.tanh(base + orbit + 0.20 * drive[index]))
    return _normalize12(values)


def _refract(query12: Sequence[float], r12_vector: Mapping[str, float]) -> tuple[list[float], float]:
    query = _normalize12(query12)
    axis = _normalize12([_clamp01(float(r12_vector.get(name, 0.0))) for name in R12_NAMES])
    rho = _clamp01(float(r12_vector.get("reality_coupling", 0.0)))
    dot = sum(q * u for q, u in zip(query, axis, strict=True))
    mirrored = [2.0 * dot * u - q for q, u in zip(query, axis, strict=True)]
    refracted = [(1.0 - rho) * q + rho * m for q, m in zip(query, mirrored, strict=True)]
    return _normalize12(refracted), rho


def world_source_quality(record: Mapping[str, Any]) -> float:
    required = ("source_dataset", "source_id", "title", "text", "license_label", "revision_label", "source_sha256")
    if any(not str(record.get(name) or "").strip() for name in required):
        return 0.0
    digest = str(record["source_sha256"]).lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        return 0.0
    if hashlib.sha256(str(record["text"]).encode("utf-8")).hexdigest() != digest:
        return 0.0
    words = str(record["text"]).split()
    if len(words) < 4:
        return 0.45
    return 0.95


class WorldR12Router:
    """R12 ranking over the separate world-knowledge namespace.

    FTS5 performs the scalable lexical prefilter; R12 then re-ranks only that
    bounded candidate set. This keeps the geometry useful without scanning a
    multi-million-record corpus on every query.
    """

    def __init__(self, store: WorldKnowledgeStore) -> None:
        self.store = store

    def rank(
        self,
        query: str,
        *,
        sequence: int,
        dyn12: Sequence[float],
        r12_state: Mapping[str, Any],
        limit: int = 8,
        lexical_prefilter: int = 128,
    ) -> list[dict[str, Any]]:
        if int(limit) <= 0 or int(lexical_prefilter) <= 0:
            return []
        vector = r12_state.get("vector")
        if not isinstance(vector, Mapping):
            raise ValueError("r12_state.vector must be a mapping")
        query12 = _query_position(query, sequence=int(sequence), dyn12=dyn12)
        refracted, rho = _refract(query12, vector)
        candidates = self.store.search_lexical(query, limit=int(lexical_prefilter))
        ranked: list[dict[str, Any]] = []
        for candidate in candidates:
            quality = world_source_quality(candidate)
            integrity = 1.0 if quality > 0.0 else 0.0
            position = _world_position(
                int(candidate["knowledge_id"]),
                str(candidate["source_sha256"]),
                sequence=int(sequence),
                dyn12=dyn12,
            )
            components = {
                "spatial": (1.0 + _cosine12(refracted, position)) / 2.0,
                "lexical": _clamp01(float(candidate.get("lexical_score", 0.0))),
                "hebbian": 0.0,
                "recency": 1.0,
                "integrity": integrity,
                "quality": quality,
            }
            score = sum(QUALITY_WEIGHTS[name] * components[name] for name in QUALITY_WEIGHTS)
            ranked.append({**dict(candidate), "rho": rho, "components": components, "score": _clamp01(score)})
        ranked.sort(key=lambda item: (float(item["score"]), -int(item["knowledge_id"])), reverse=True)
        return ranked[: int(limit)]


def _personal_support(record: Mapping[str, Any]) -> float:
    c = dict(record.get("components") or {})
    return _clamp01(
        0.50 * float(c.get("lexical", 0.0))
        + 0.30 * float(c.get("hebbian", 0.0))
        + 0.20 * float(c.get("integrity", 0.5))
    )


def _world_support(record: Mapping[str, Any]) -> float:
    c = dict(record.get("components") or {})
    return _clamp01(
        0.55 * float(c.get("lexical", 0.0))
        + 0.25 * float(c.get("quality", 0.0))
        + 0.20 * float(c.get("integrity", 0.0))
    )


def select_primary_evidence(
    *,
    personal: Sequence[Mapping[str, Any]],
    world: Sequence[Mapping[str, Any]],
    confidence_floor: float = 0.56,
    namespace_margin: float = 0.03,
) -> dict[str, Any]:
    floor = _clamp01(float(confidence_floor))
    margin = max(0.0, float(namespace_margin))
    p = dict(personal[0]) if personal else None
    w = dict(world[0]) if world else None
    ps = float(p.get("score", 0.0)) if p else 0.0
    ws = float(w.get("score", 0.0)) if w else 0.0
    best = max(ps, ws)
    if best < floor:
        return {"namespace": "none", "record": None, "score": best, "personal_score": ps, "world_score": ws}

    if p is None:
        return {"namespace": "world", "record": w, "score": ws, "personal_score": ps, "world_score": ws}
    if w is None:
        return {"namespace": "personal", "record": p, "score": ps, "personal_score": ps, "world_score": ws}
    if ps - ws >= margin:
        namespace, record, score = "personal", p, ps
    elif ws - ps >= margin:
        namespace, record, score = "world", w, ws
    else:
        p_support = _personal_support(p)
        w_support = _world_support(w)
        if w_support > p_support:
            namespace, record, score = "world", w, ws
        else:
            namespace, record, score = "personal", p, ps
    return {
        "namespace": namespace,
        "record": record,
        "score": score,
        "personal_score": ps,
        "world_score": ws,
        "personal_support": _personal_support(p),
        "world_support": _world_support(w),
    }
