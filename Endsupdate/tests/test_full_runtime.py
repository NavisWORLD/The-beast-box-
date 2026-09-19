from pathlib import Path

from beastbox.attention import mechanism_preflight, mixture_of_states_attention
from beastbox.bridge import BridgePacket
from beastbox.memory import ReconciliationMemory
from beastbox.providers import ReferenceTextProvider
from beastbox.runtime import CosmosRuntime
from beastbox.state_family import StateFamily


def test_memory_persists_and_retrieves(tmp_path: Path):
    db = tmp_path / "m.sqlite3"
    m = ReconciliationMemory(db)
    m.store("quantum bridge keeps raw credentials outside the state capsule")
    m.store("sunflowers grow toward light")
    hits = m.search("state capsule credentials quantum", limit=1)
    assert hits and "credentials" in hits[0].text
    assert m.stats()["memories"] == 2
    m.close()


def test_state_family_dimensions_and_preflight():
    s = StateFamily()
    out = s.update([0.2, -0.5, 0.8])
    assert len(out["dyn12"]) == 12
    assert len(out["dyn42"]) == 42
    assert len(out["dyn54"]) == 54
    assert len(out["static54"]) == 54
    assert len(out["tri3"]) == 108
    assert s.preflight()["dyn12"]["live"] is True


def test_mixture_attention_rows_sum_to_one():
    logits = [[1.0, 0.0], [0.5, 0.5]]
    states = [[0.0, 0.0], [0.5, -0.25]]
    matrix = mixture_of_states_attention(logits, states, gate=0.3, sigma=0.75)
    assert all(abs(sum(row) - 1.0) < 1e-9 for row in matrix)
    assert mechanism_preflight(matrix)["live"] is True


def test_closed_loop_runtime(tmp_path: Path):
    from beastbox.config import RuntimeConfig

    cfg = RuntimeConfig(
        data_dir=str(tmp_path),
        memory_db=str(tmp_path / "memory.sqlite3"),
        evidence_dir=str(tmp_path / "evidence"),
        proposals_dir=str(tmp_path / "proposals"),
    )
    r = CosmosRuntime(cfg, provider=ReferenceTextProvider())
    try:
        first = r.respond("remember that the evidence ledger must preserve nulls", bridge=BridgePacket(quantum_spark=[0.1, -0.1]))
        second = r.respond("what should the evidence ledger preserve?")
        assert first["state_hash"]
        assert second["memory_hits"]
        assert r.ledger.verify()
    finally:
        r.close()
