"""Measured values from one durable turn.

The numbers come from the runtime objects that just updated. This module does
not synthesize activity, animate missing stages, or interpret a change as an
intelligence advantage.
"""

from __future__ import annotations

from typing import Any

from .hashutil import sha256_obj


def _linf(before: list[float], after: list[float]) -> float:
    if len(before) != len(after) or not before:
        raise ValueError("signal vectors must be the same non-empty length")
    return max(abs(float(left) - float(right)) for left, right in zip(before, after))


def capture_signal_baseline(runtime: Any) -> dict[str, Any]:
    """Snapshot substrate fields after checkpoint restore and before the turn."""
    memory = runtime.memory
    family = runtime.synaptic.state_family
    stats = memory.stats()
    weight = memory.db.execute("SELECT COALESCE(SUM(weight), 0.0) FROM associations").fetchone()[0]
    max_id = memory.db.execute("SELECT COALESCE(MAX(id), 0) FROM memories").fetchone()[0]
    return {
        "dyn12": [float(value) for value in family.dyn12],
        "dyn42": [float(value) for value in family.dyn42],
        "associations": int(stats["associations"]),
        "salience": int(stats["salience_concepts"]),
        "memories": int(stats["memories"]),
        "association_weight_sum": float(weight),
        "max_memory_id": int(max_id),
    }


def build_turn_signals(
    runtime: Any,
    before: dict[str, Any],
    result: dict[str, Any],
    *,
    event_sha256: str,
    feature_count: int,
) -> dict[str, Any]:
    """Assemble the receipt payload from the turn that just finished."""
    family = runtime.synaptic.state_family
    synaptic_after = [float(value) for value in family.dyn12]
    dyn42_after = [float(value) for value in family.dyn42]
    dyn54 = [float(value) for value in family.dyn54]
    cns = result.get("cns")
    if not isinstance(cns, dict) or not isinstance(cns.get("dyn12"), list):
        raise TypeError("durable turn did not return a CNS dyn12 state")
    cns_after = [float(value) for value in cns["dyn12"]]
    if len(synaptic_after) != 12 or len(cns_after) != 12 or len(dyn42_after) != 42 or len(dyn54) != 54:
        raise RuntimeError("state family lengths are not the implemented 12/42/54 layout")
    stats = runtime.memory.stats()
    weight = runtime.memory.db.execute("SELECT COALESCE(SUM(weight), 0.0) FROM associations").fetchone()[0]
    rows = runtime.memory.db.execute(
        "SELECT id FROM memories WHERE id > ? ORDER BY id",
        (int(before["max_memory_id"]),),
    ).fetchall()
    measured = getattr(runtime.provider, "receipt", {})
    if not isinstance(measured, dict):
        measured = {}
    tool = runtime._tool_result if isinstance(runtime._tool_result, dict) else {}
    note = runtime.slow.monologue.thoughts[-1] if runtime.slow.monologue.thoughts else ""
    plasticity = cns.get("plasticity")
    trust = plasticity.get("trust") if isinstance(plasticity, dict) else None
    return {
        "schema": "substrate-signal-v1",
        "provenance": "measured-during-durable-turn",
        "event_sha256": event_sha256,
        "feature_count": int(feature_count),
        "dyn12": {
            "before": list(before["dyn12"]),
            "synaptic_after": synaptic_after,
            "cns_after": cns_after,
            "linf_synaptic": _linf(list(before["dyn12"]), synaptic_after),
            "linf_cns_from_before": _linf(list(before["dyn12"]), cns_after),
            "sha256": sha256_obj(cns_after),
        },
        "dyn42": {
            "length": 42,
            "linf": _linf(list(before["dyn42"]), dyn42_after),
            "min": min(dyn42_after),
            "max": max(dyn42_after),
        },
        "dyn54": {
            "length": 54,
            "equals_dyn12_plus_dyn42": dyn54 == synaptic_after + dyn42_after,
        },
        "hebbian": {
            "associations_before": int(before["associations"]),
            "associations_after": int(stats["associations"]),
            "weight_sum_before": float(before["association_weight_sum"]),
            "weight_sum_after": float(weight),
            "salience_before": int(before["salience"]),
            "salience_after": int(stats["salience_concepts"]),
            "memories_before": int(before["memories"]),
            "memories_after": int(stats["memories"]),
        },
        "memory_writes": [int(row["id"]) for row in rows],
        "routing_memory_ids": list(runtime._routing.get("memory_ids", [])),
        "cns": {
            "step": int(runtime.cns.step),
            "plasticity_trust": None if trust is None else float(trust),
            "phos": None if cns.get("phos") is None else float(cns["phos"]),
            "roles": ["quantum", "dark_matter", "emeth", "plasticity", "awareness", "daemons", "surgeon"],
        },
        "model": {
            "provider": measured.get("provider"),
            "model": measured.get("model"),
            "identity_kind": measured.get("identity_kind"),
        },
        "authorization": {
            "authorized": bool(tool.get("authorized", False)),
            "status": tool.get("status"),
        },
        "slow": {
            "experiences": int(runtime.slow.organism.experiences),
            "evolution_cycles": int(runtime.slow.evolution.cycles),
            "monologue_records": len(runtime.slow.monologue.thoughts),
            "software_note": str(note)[:180],
        },
        "stages_ms": {str(key): float(value) for key, value in runtime._stages_ms.items()},
        "advantage_claimed": False,
    }
