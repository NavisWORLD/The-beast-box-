from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest

from beastbox.dad_son import DadSonLedger
from beastbox.refractive_memory import RefractiveMemoryRouter, WEIGHTS

PARENT = "a" * 64


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ledger(tmp_path: Path) -> DadSonLedger:
    return DadSonLedger(tmp_path / "memory.sqlite3", tmp_path / "ledger.jsonl", parent_sha256=PARENT)


def _r12(*, rho: float) -> dict:
    names = (
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
    values = [0.9, 0.6, 0.8, 0.3, 0.7, 0.4, 0.2, 0.8, 0.9, 0.0, 0.95, rho]
    return {
        "sequence": 7,
        "state_sha256": _sha(f"r12:{rho}"),
        "vector": dict(zip(names, values, strict=True)),
    }


def test_query_and_memory_geometry_are_deterministic_and_normalized(tmp_path: Path):
    ledger = _ledger(tmp_path)
    router = RefractiveMemoryRouter(ledger)
    dyn12 = [0.1] * 12

    q1 = router.query_position("same query", sequence=7, dyn12=dyn12)
    q2 = router.query_position("same query", sequence=7, dyn12=dyn12)
    q3 = router.query_position("same query", sequence=8, dyn12=dyn12)
    m1 = router.memory_position(11, "memory text", sequence=7, dyn12=dyn12)
    m2 = router.memory_position(11, "memory text", sequence=7, dyn12=dyn12)

    assert q1 == q2
    assert m1 == m2
    assert q1 != q3
    assert len(q1) == len(m1) == 12
    assert all(math.isfinite(v) for v in q1 + m1)
    assert math.isclose(sum(v * v for v in q1), 1.0, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(sum(v * v for v in m1), 1.0, rel_tol=0.0, abs_tol=1e-9)
    ledger.close()


def test_refractive_reflection_uses_bounded_r12_coordinate(tmp_path: Path):
    ledger = _ledger(tmp_path)
    router = RefractiveMemoryRouter(ledger)
    query = router.query_position("orbit", sequence=7, dyn12=[0.1] * 12)

    plain, rho0 = router.refract(query, _r12(rho=0.0)["vector"])
    reflected, rho1 = router.refract(query, _r12(rho=1.0)["vector"])
    clamped, rho2 = router.refract(query, _r12(rho=2.0)["vector"])

    assert rho0 == 0.0
    assert rho1 == 1.0
    assert rho2 == 1.0
    assert plain == pytest.approx(query, abs=1e-12)
    assert reflected != pytest.approx(query, abs=1e-6)
    assert clamped == pytest.approx(reflected, abs=1e-12)
    assert math.isclose(sum(v * v for v in reflected), 1.0, abs_tol=1e-9)

    bad = _r12(rho=0.5)["vector"]
    bad["reality_coupling"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        router.refract(query, bad)
    ledger.close()


def test_live_epoch_lane_requires_exact_current_hash_binding(tmp_path: Path):
    ledger = _ledger(tmp_path)
    router = RefractiveMemoryRouter(ledger)

    common = {
        "source_sha256": _sha("source"),
        "r12_state_sha256": _sha("r12"),
        "dyn12_sha256": _sha("d12"),
        "dyn42_sha256": _sha("d42"),
        "dyn54_sha256": _sha("d54"),
        "provenance_class": "derived",
        "claim_boundary": "computational lineage/state only",
    }
    for epoch in ("E1", "E2"):
        ledger.append_experience(
            actor="LIVE_SOUL_SOURCE",
            text=f"live source {epoch}",
            kind="live-source-epoch",
            session_id="test",
            metadata={"epoch_id": epoch, "sequence_id": int(epoch[1:]), **common},
        )

    row = router.require_live_epoch(epoch_id="E2", **{k: common[k] for k in common if k.endswith("sha256")})
    assert row["text"] == "live source E2"
    assert row["metadata"]["epoch_id"] == "E2"

    with pytest.raises(RuntimeError, match="live-source"):
        router.require_live_epoch(epoch_id="E3", **{k: common[k] for k in common if k.endswith("sha256")})
    with pytest.raises(RuntimeError, match="live-source"):
        router.require_live_epoch(
            epoch_id="E2",
            source_sha256=_sha("wrong"),
            r12_state_sha256=common["r12_state_sha256"],
            dyn12_sha256=common["dyn12_sha256"],
            dyn42_sha256=common["dyn42_sha256"],
            dyn54_sha256=common["dyn54_sha256"],
        )
    ledger.close()


def test_rank_exposes_frozen_component_scores_and_exact_weighted_total(tmp_path: Path):
    ledger = _ledger(tmp_path)
    router = RefractiveMemoryRouter(ledger)
    for text in (
        "ancient origin waveform archive",
        "current orbital source context",
        "ordinary unrelated dialogue",
    ):
        ledger.append_experience(actor="fixture", text=text, kind="dialogue", session_id="rank")

    hits = router.rank(
        "orbital waveform context",
        sequence=7,
        dyn12=[0.1] * 12,
        r12_state=_r12(rho=0.7),
        limit=3,
    )
    assert len(hits) == 3
    assert WEIGHTS == {
        "spatial": 0.40,
        "lexical": 0.20,
        "hebbian": 0.15,
        "recency": 0.10,
        "integrity": 0.15,
    }
    for hit in hits:
        components = hit["components"]
        assert set(components) == {"spatial", "lexical", "hebbian", "recency", "integrity"}
        assert all(0.0 <= float(v) <= 1.0 for v in components.values())
        expected = sum(WEIGHTS[name] * float(components[name]) for name in WEIGHTS)
        assert math.isclose(hit["score"], expected, rel_tol=0.0, abs_tol=1e-12)
    ledger.close()
