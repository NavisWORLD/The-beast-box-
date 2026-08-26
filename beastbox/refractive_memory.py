from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .dad_son import DadSonLedger

PHASE = 0.17320508075688773
LIVE_KIND = "live-source-epoch"
WEIGHTS: dict[str, float] = {
    "spatial": 0.40,
    "lexical": 0.20,
    "hebbian": 0.15,
    "recency": 0.10,
    "integrity": 0.15,
}

R12_NAMES = (
    "source_integrity",
    "temporal_novelty",
    "measurement_confidence",
    "distribution_energy",
    "cross_condition_agreement",
    "distribution_entropy",
    "surprise",
    "memory_relevance",
    "retention_pressure",
    "contradiction_pressure",
    "adaptation_stability",
    "reality_coupling",
)

_TOKEN_RE = re.compile(r"[A-Za-z0-9_']+")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(str(text))]


def _cosine_counts(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    lnorm = math.sqrt(sum(value * value for value in left.values()))
    rnorm = math.sqrt(sum(value * value for value in right.values()))
    return dot / max(lnorm * rnorm, 1e-12)


def _hash_unit(text: str) -> float:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float((1 << 64) - 1)


def _clamp01(value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("refractive values must be finite")
    return max(0.0, min(1.0, value))


def _normalize12(values: Sequence[float]) -> list[float]:
    if len(values) != 12:
        raise ValueError("spatial vector must contain exactly 12 values")
    vec = [float(value) for value in values]
    if not all(math.isfinite(value) for value in vec):
        raise ValueError("spatial vector values must be finite")
    norm = math.sqrt(sum(value * value for value in vec))
    if norm <= 1e-15:
        return [1.0] + [0.0] * 11
    return [value / norm for value in vec]


def _cosine12(left: Sequence[float], right: Sequence[float]) -> float:
    lvec = _normalize12(left)
    rvec = _normalize12(right)
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(lvec, rvec, strict=True))))


def _is_sha256(value: object) -> bool:
    return bool(_SHA_RE.fullmatch(str(value or "").lower()))


class RefractiveMemoryRouter:
    """Deterministic 12D memory routing layered over an existing Dad/Son ledger.

    `LIVE_SOUL_SOURCE` is treated only as a computational lineage/state stream.
    This router changes retrieval context; it does not alter model weights or
    claim biological, conscious, metaphysical, or physical properties.
    """

    def __init__(self, ledger: DadSonLedger) -> None:
        self.ledger = ledger

    @staticmethod
    def _validate_dyn12(dyn12: Sequence[float]) -> list[float]:
        if len(dyn12) != 12:
            raise ValueError("dyn12 must contain exactly 12 values")
        values = [float(value) for value in dyn12]
        if not all(math.isfinite(value) for value in values):
            raise ValueError("dyn12 values must be finite")
        return values

    def query_position(self, query: str, *, sequence: int, dyn12: Sequence[float]) -> list[float]:
        drive = self._validate_dyn12(dyn12)
        values: list[float] = []
        for index in range(12):
            base = 2.0 * _hash_unit(f"query:{query}:{index}") - 1.0
            orbit = 0.25 * math.sin((int(sequence) + 1) * (index + 1) * PHASE)
            values.append(math.tanh(base + orbit + 0.20 * drive[index]))
        return _normalize12(values)

    def memory_position(
        self,
        memory_id: int,
        text: str,
        *,
        sequence: int,
        dyn12: Sequence[float],
    ) -> list[float]:
        drive = self._validate_dyn12(dyn12)
        text_sha = hashlib.sha256(str(text).encode("utf-8")).hexdigest()
        values: list[float] = []
        for index in range(12):
            base = 2.0 * _hash_unit(f"memory:{int(memory_id)}:{text_sha}:{index}") - 1.0
            identity_phase = 2.0 * math.pi * _hash_unit(f"phase:{int(memory_id)}:{text_sha}:{index}")
            orbit = 0.25 * math.sin(identity_phase + (int(sequence) + 1) * (index + 1) * PHASE)
            values.append(math.tanh(base + orbit + 0.20 * drive[index]))
        return _normalize12(values)

    def refract(
        self,
        query12: Sequence[float],
        r12_vector: Mapping[str, float],
    ) -> tuple[list[float], float]:
        query = _normalize12(query12)
        raw_axis = [float(r12_vector.get(name, 0.0)) for name in R12_NAMES]
        if not all(math.isfinite(value) for value in raw_axis):
            raise ValueError("R12 vector values must be finite")
        axis = _normalize12(raw_axis)
        rho = _clamp01(float(r12_vector.get("reality_coupling", 0.0)))
        dot = sum(q * u for q, u in zip(query, axis, strict=True))
        mirrored = [2.0 * dot * u - q for q, u in zip(query, axis, strict=True)]
        refracted = [(1.0 - rho) * q + rho * m for q, m in zip(query, mirrored, strict=True)]
        return _normalize12(refracted), rho

    def _hebbian_score(self, query: str, candidate_text: str) -> float:
        query_tokens = set(_tokens(query))
        candidate_tokens = set(_tokens(candidate_text))
        if not query_tokens or not candidate_tokens:
            return 0.0
        pulls: list[float] = []
        for token in sorted(query_tokens):
            neighbors = self.ledger.memory.associations(token, limit=10)
            for neighbor, weight in neighbors:
                if neighbor in candidate_tokens:
                    pulls.append(min(1.0, float(weight) / 5.0))
        direct = len(query_tokens & candidate_tokens) / max(1, len(query_tokens | candidate_tokens))
        assoc = sum(pulls) / len(pulls) if pulls else 0.0
        return max(0.0, min(1.0, 0.5 * direct + 0.5 * assoc))

    @staticmethod
    def _integrity_score(kind: str, metadata: Mapping[str, Any]) -> float:
        declared = {key: value for key, value in metadata.items() if str(key).endswith("sha256")}
        if not declared:
            return 0.5
        if any(not _is_sha256(value) for value in declared.values()):
            return 0.0
        if str(kind) == LIVE_KIND:
            required = {
                "source_sha256",
                "r12_state_sha256",
                "dyn12_sha256",
                "dyn42_sha256",
                "dyn54_sha256",
            }
            if not required.issubset(metadata):
                return 0.0
        return 1.0

    def rank(
        self,
        query: str,
        *,
        sequence: int,
        dyn12: Sequence[float],
        r12_state: Mapping[str, Any],
        limit: int,
    ) -> list[dict[str, Any]]:
        if int(limit) <= 0:
            return []
        vector = r12_state.get("vector")
        if not isinstance(vector, Mapping):
            raise ValueError("r12_state.vector must be a mapping")
        query12 = self.query_position(query, sequence=int(sequence), dyn12=dyn12)
        refracted, rho = self.refract(query12, vector)
        qcounts = Counter(_tokens(query))
        now = time.time()
        half_life = 30.0 * 86400.0
        rows = self.ledger.memory.db.execute(
            "SELECT id,created_at,kind,text,metadata_json,source_ids_json FROM memories ORDER BY id DESC"
        ).fetchall()
        ranked: list[dict[str, Any]] = []
        for row in rows:
            memory_id = int(row["id"])
            text = str(row["text"])
            kind = str(row["kind"])
            try:
                metadata = dict(json.loads(row["metadata_json"] or "{}"))
            except (TypeError, json.JSONDecodeError):
                metadata = {}
            try:
                source_ids = list(json.loads(row["source_ids_json"] or "[]"))
            except (TypeError, json.JSONDecodeError):
                source_ids = []
            memory12 = self.memory_position(memory_id, text, sequence=int(sequence), dyn12=dyn12)
            spatial = (1.0 + _cosine12(refracted, memory12)) / 2.0
            lexical = max(0.0, min(1.0, _cosine_counts(qcounts, Counter(_tokens(text)))))
            hebbian = self._hebbian_score(query, text)
            age = max(0.0, now - float(row["created_at"]))
            recency = math.exp(-math.log(2.0) * age / half_life)
            integrity = self._integrity_score(kind, metadata)
            components = {
                "spatial": max(0.0, min(1.0, spatial)),
                "lexical": lexical,
                "hebbian": hebbian,
                "recency": max(0.0, min(1.0, recency)),
                "integrity": integrity,
            }
            score = sum(WEIGHTS[name] * components[name] for name in WEIGHTS)
            ranked.append(
                {
                    "memory_id": memory_id,
                    "text": text,
                    "kind": kind,
                    "created_at": float(row["created_at"]),
                    "metadata": metadata,
                    "source_ids": source_ids,
                    "rho": rho,
                    "components": components,
                    "score": score,
                }
            )
        ranked.sort(key=lambda item: (float(item["score"]), int(item["memory_id"])), reverse=True)
        return ranked[: int(limit)]

    def require_live_epoch(
        self,
        *,
        epoch_id: str,
        source_sha256: str,
        r12_state_sha256: str,
        dyn12_sha256: str,
        dyn42_sha256: str,
        dyn54_sha256: str,
    ) -> dict[str, Any]:
        expected = {
            "epoch_id": str(epoch_id),
            "source_sha256": str(source_sha256).lower(),
            "r12_state_sha256": str(r12_state_sha256).lower(),
            "dyn12_sha256": str(dyn12_sha256).lower(),
            "dyn42_sha256": str(dyn42_sha256).lower(),
            "dyn54_sha256": str(dyn54_sha256).lower(),
        }
        if any(key.endswith("sha256") and not _is_sha256(value) for key, value in expected.items()):
            raise RuntimeError("live-source hash binding is invalid")
        rows = self.ledger.memory.db.execute(
            "SELECT id,created_at,kind,text,metadata_json,source_ids_json FROM memories WHERE kind=? ORDER BY id DESC",
            (LIVE_KIND,),
        ).fetchall()
        matches: list[dict[str, Any]] = []
        for row in rows:
            try:
                metadata = dict(json.loads(row["metadata_json"] or "{}"))
            except (TypeError, json.JSONDecodeError):
                continue
            if all(str(metadata.get(key, "")).lower() == str(value).lower() for key, value in expected.items()):
                matches.append(
                    {
                        "memory_id": int(row["id"]),
                        "text": str(row["text"]),
                        "kind": str(row["kind"]),
                        "created_at": float(row["created_at"]),
                        "metadata": metadata,
                        "source_ids": list(json.loads(row["source_ids_json"] or "[]")),
                    }
                )
        if len(matches) != 1:
            raise RuntimeError(
                f"live-source epoch integrity failure for {epoch_id}: expected exactly one bound record, found {len(matches)}"
            )
        return matches[0]
