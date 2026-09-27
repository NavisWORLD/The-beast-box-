"""Opt-in embedding retrieval over one active, provenance-preserving product snapshot.

Default durable retrieval remains byte-for-byte on its original lexical/R12 path.
This module never stores embeddings in the continuity database and gives an
embedding provider no model, tool or owner-authority capability.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class SemanticRetrievalError(RuntimeError):
    """Opted-in semantic retrieval failed; do not silently fall back."""


class EmbeddingProvider(Protocol):
    """Explicit host-supplied plugin. local_only is a declaration, not an audit."""

    model_id: str
    local_only: bool

    def embed_many(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


class OfflineSentenceTransformer:
    """Optional learned embedding adapter; requires a PRELOADED local model.

    No model identifier is downloaded on demand. Install the optional embeddings
    extra separately. Trust the local model directory and dependency installation.
    """

    local_only = True

    def __init__(self, model_directory: str | Path):
        path = Path(model_directory).expanduser().resolve(strict=True)
        if not path.is_dir():
            raise ValueError("offline embedding model must be an existing local directory")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise SemanticRetrievalError("install sentence-transformers separately for local learned retrieval") from exc
        try:
            self._model = SentenceTransformer(
                str(path), local_files_only=True, trust_remote_code=False
            )
        except Exception as exc:
            raise SemanticRetrievalError("failed to load the preinstalled offline embedding model") from exc
        # A configured directory label is NOT a model-weight integrity attestation.
        self.model_id = "local-sentence-transformer:" + path.name

    def embed_many(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts), batch_size=32, show_progress_bar=False,
            convert_to_numpy=False, normalize_embeddings=False,
        )
        return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in vectors]


def _normalized_batch(raw: object, count: int, dimension: int | None) -> list[tuple[float, ...]]:
    if isinstance(raw, (str, bytes)):
        raise SemanticRetrievalError("embedding provider returned an invalid batch")
    try:
        vectors = list(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise SemanticRetrievalError("embedding provider returned a non-iterable batch") from exc
    if len(vectors) != count:
        raise SemanticRetrievalError("embedding provider batch count mismatch")
    clean: list[tuple[float, ...]] = []
    for raw_vector in vectors:
        try:
            values = [float(value) for value in raw_vector]
        except (TypeError, ValueError, OverflowError) as exc:
            raise SemanticRetrievalError("embedding provider returned a nonnumeric vector") from exc
        if not 2 <= len(values) <= 4096 or (dimension is not None and len(values) != dimension):
            raise SemanticRetrievalError("embedding provider returned an invalid vector dimension")
        if not all(math.isfinite(value) for value in values):
            raise SemanticRetrievalError("embedding provider returned nonfinite values")
        norm = math.sqrt(sum(value * value for value in values))
        if not math.isfinite(norm) or norm <= 1e-12:
            raise SemanticRetrievalError("embedding provider returned a zero or invalid vector")
        clean.append(tuple(value / norm for value in values))
        dimension = len(values)
    return clean


@dataclass(frozen=True)
class SemanticResult:
    scores: dict[int, float]
    embedded_records: int
    cache_hits: int


class SnapshotSemanticIndex:
    """Ephemeral bounded embeddings keyed by exact source text; no DB migrations.

    Cache is per-runtime, never shared across providers or included in a
    checkpoint. The active snapshot is the sole source of record provenance.
    """

    def __init__(
        self, provider: EmbeddingProvider, *, allow_remote: bool = False,
        min_similarity: float = 0.40, max_records: int = 50_000,
        cache_records: int = 2048, batch_size: int = 32,
    ):
        model_id = getattr(provider, "model_id", None)
        if not isinstance(model_id, str) or not 1 <= len(model_id) <= 256:
            raise ValueError("semantic provider needs a bounded explicit model_id")
        local_only = getattr(provider, "local_only", None)
        if type(local_only) is not bool:
            raise ValueError("semantic provider must declare its local/remote behavior")
        if not local_only and not allow_remote:
            raise ValueError("remote memory embedding requires explicit host opt-in")
        if not isinstance(min_similarity, (int, float)) or not math.isfinite(min_similarity) or not 0 <= min_similarity <= 1:
            raise ValueError("semantic minimum similarity must be finite in 0..1")
        if type(max_records) is not int or not 1 <= max_records <= 50_000:
            raise ValueError("semantic max_records must be within 1..50000")
        if type(cache_records) is not int or not 0 <= cache_records <= 8192:
            raise ValueError("semantic cache_records must be within 0..8192")
        if type(batch_size) is not int or not 1 <= batch_size <= 128:
            raise ValueError("semantic batch_size must be within 1..128")
        self.provider = provider
        self.model_id = model_id
        self.local_only_declared = local_only
        self.min_similarity = float(min_similarity)
        self.max_records = max_records
        self.cache_records = cache_records
        self.batch_size = batch_size
        self._cache: OrderedDict[tuple[int, str], tuple[float, ...]] = OrderedDict()

    def forget_memory(self, memory_id: int) -> None:
        """Drop private vectors promptly when a host archives a source."""
        for key in list(self._cache):
            if key[0] == memory_id:
                del self._cache[key]

    def clear(self) -> None:
        """Discard all ephemeral vectors, including on runtime shutdown."""
        self._cache.clear()

    def _embed(self, texts: Sequence[str], dimension: int | None) -> list[tuple[float, ...]]:
        try:
            raw = self.provider.embed_many(texts)
        except Exception as exc:
            raise SemanticRetrievalError("explicit semantic provider failed; no lexical fallback") from exc
        return _normalized_batch(raw, len(texts), dimension)

    def rank(self, rows: Sequence[Any], query: str) -> SemanticResult:
        if not isinstance(query, str) or not 1 <= len(query) <= 8192:
            raise SemanticRetrievalError("semantic query must contain 1..8192 characters")
        if len(rows) > self.max_records:
            raise SemanticRetrievalError("semantic source corpus exceeds configured record cap")
        # Dropping all active rows must also drop previously cached private vectors.
        if not rows:
            self.clear()
            return SemanticResult({}, 0, 0)
        try:
            active: list[tuple[int, str, tuple[int, str]]] = []
            live_keys: set[tuple[int, str]] = set()
            for row in rows:
                try:
                    metadata = json.loads(row["metadata_json"])
                except (TypeError, ValueError) as exc:
                    raise SemanticRetrievalError("invalid source lifecycle metadata") from exc
                if not isinstance(metadata, dict):
                    raise SemanticRetrievalError("invalid source lifecycle metadata")
                if bool(metadata.get("archived", False)):
                    continue
                memory_id = int(row["id"])
                text = str(row["text"])
                key = (memory_id, hashlib.sha256(text.encode("utf-8")).hexdigest())
                active.append((memory_id, text, key))
                live_keys.add(key)

            # Another runtime may have archived or replaced rows since the last turn.
            # Never retain vectors absent from the authoritative active snapshot.
            for stale_key in list(self._cache):
                if stale_key not in live_keys:
                    del self._cache[stale_key]
            if not active:
                return SemanticResult({}, 0, 0)

            query_vector = self._embed([query], None)[0]
            dimension = len(query_vector)
            scores: dict[int, float] = {}
            misses: list[tuple[int, str, tuple[int, str]]] = []
            hits = 0
            for memory_id, text, key in active:
                vector = self._cache.get(key)
                if vector is not None and len(vector) == dimension:
                    self._cache.move_to_end(key)
                    hits += 1
                    similarity = sum(a * b for a, b in zip(query_vector, vector, strict=True))
                    if similarity >= self.min_similarity:
                        scores[memory_id] = max(0.0, min(1.0, similarity))
                else:
                    self._cache.pop(key, None)
                    misses.append((memory_id, text[:8192], key))
            for start in range(0, len(misses), self.batch_size):
                part = misses[start : start + self.batch_size]
                vectors = self._embed([item[1] for item in part], dimension)
                for (memory_id, _, key), vector in zip(part, vectors, strict=True):
                    similarity = sum(a * b for a, b in zip(query_vector, vector, strict=True))
                    if similarity >= self.min_similarity:
                        scores[memory_id] = max(0.0, min(1.0, similarity))
                    if self.cache_records:
                        self._cache[key] = vector
                        self._cache.move_to_end(key)
                        if len(self._cache) > self.cache_records:
                            self._cache.popitem(last=False)
            return SemanticResult(scores, len(misses), hits)
        except Exception:
            # Failed provider calls never leave a partially refreshed cache.
            self.clear()
            raise


def fuse_r12_semantic(
    r12_records: Sequence[Mapping[str, Any]], scores: Mapping[int, float],
    *, limit: int = 5, semantic_weight: float = 0.65,
) -> list[dict[str, Any]]:
    """Auditable opt-in reciprocal-rank fusion; the frozen R12 scores survive."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("hybrid result limit must be in 1..100")
    if not math.isfinite(semantic_weight) or not 0 <= semantic_weight <= 1:
        raise ValueError("semantic fusion weight must be finite in 0..1")
    semantic_order = sorted(scores, key=lambda key: (scores[key], key), reverse=True)
    semantic_positions = {memory_id: i + 1 for i, memory_id in enumerate(semantic_order)}
    ranked: list[dict[str, Any]] = []
    for r12_position, record in enumerate(r12_records, start=1):
        memory_id = int(record["memory_id"])
        semantic_rank = semantic_positions.get(memory_id)
        fused = (
            (1.0 - semantic_weight) / (60.0 + r12_position)
            + (semantic_weight / (60.0 + semantic_rank) if semantic_rank is not None else 0.0)
        )
        result = dict(record)
        result["r12_score"] = float(result["score"])
        result["semantic_similarity"] = scores.get(memory_id)
        result["score"] = 61.0 * fused
        ranked.append(result)
    ranked.sort(key=lambda item: (item["score"], item["r12_score"], item["memory_id"]), reverse=True)
    return ranked[:limit]
