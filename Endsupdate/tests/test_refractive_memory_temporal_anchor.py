from __future__ import annotations

import hashlib
from pathlib import Path

from beastbox.dad_son import DadSonLedger
from beastbox.refractive_memory import RefractiveMemoryRouter


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _r12() -> dict:
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
    values = [0.9, 0.6, 0.8, 0.3, 0.7, 0.4, 0.2, 0.8, 0.9, 0.0, 0.95, 0.7]
    return {"sequence": 7, "state_sha256": _sha("r12"), "vector": dict(zip(names, values, strict=True))}


def test_rank_accepts_frozen_temporal_anchor_for_reproducible_scores(tmp_path: Path):
    ledger = DadSonLedger(tmp_path / "memory.sqlite3", tmp_path / "ledger.jsonl", parent_sha256="a" * 64)
    ledger.append_experience(actor="fixture", text="Dad memory alpha", kind="dialogue", session_id="anchor")
    ledger.append_experience(actor="fixture", text="Dad memory beta", kind="dialogue", session_id="anchor")
    router = RefractiveMemoryRouter(ledger)

    anchor = float(ledger.memory.db.execute("SELECT MAX(created_at) AS t FROM memories").fetchone()["t"])
    kwargs = {
        "sequence": 2,
        "dyn12": [0.1] * 12,
        "r12_state": _r12(),
        "limit": 2,
        "profile": "quality",
        "now": anchor,
    }
    first = router.rank("Dad memory", **kwargs)
    second = router.rank("Dad memory", **kwargs)

    assert first == second
    assert first[0]["components"]["recency"] <= 1.0
    ledger.close()
