"""DIRECTIVE 001 — recover everything.

Programmatic inventory of the actual existing architecture. Distinguishes
declared capabilities from executed capabilities by checking source presence,
importability, and (where cheap) executability.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ComponentStatus:
    id: str
    names: list[str]
    paths: list[str]
    present: bool
    importable: bool
    executable: bool
    state: str  # CONNECTED | DORMANT | DUPLICATED | BROKEN | MISSING
    notes: str


_CATALOG: list[tuple[str, list[str], list[str], str]] = [
    ("cosmos-substrate", ["COSMOS persistent substrate"], ["beastbox/durable.py", "beastbox/continuity.py"], "durable"),
    ("cosmos-runtime", ["CosmosRuntime"], ["beastbox/runtime.py"], "runtime loop"),
    ("cst", ["Cosmic Synapse Theory"], ["docs/COSMIC_SYNAPSE_THEORY.md", "beastbox/attention.py"], "theory+reference"),
    ("dyn12", ["12D state"], ["beastbox/dyn12.py", "beastbox/state_family.py"], "12 scalars"),
    ("dyn42", ["42D state"], ["beastbox/state_family.py"], "42 scalars"),
    ("dyn54", ["54D state"], ["beastbox/state_family.py"], "54 scalars"),
    ("rawrphos", ["RAWRPHOS"], ["beastbox/rawrphos_local.py", "beastbox/rawrphos_hf.py"], "checkpoints/adapters"),
    ("phos", ["PHOS"], ["beastbox/models/phos_reference.py", "beastbox/training/phos_descendant.py"], "reference scalar"),
    ("samgo", ["SAMGO"], ["beastbox/training", "beastbox/descendant"], "lineage material"),
    ("cosmic-cypher", ["COSMIC.CYPHER"], ["beastbox/cypher"], "legacy surface"),
    ("cns7", ["CNS7"], ["beastbox/cns.py", "beastbox/state.py"], "seven-role controller"),
    ("synapse", ["SYNAPSE"], ["beastbox/synaptic.py"], "state binding"),
    ("r12", ["R12 routing"], ["beastbox/world_r12.py", "beastbox/refractive_memory.py", "beastbox/reality_memory.py"], "routing"),
    ("hebbian", ["Hebbian learning"], ["beastbox/memory.py"], "co-occurrence tables"),
    ("monologue", ["internal monologue"], ["beastbox/organism.py"], "bounded thought list"),
    ("sensors", ["sensors"], ["beastbox/sensor_inputs.py", "beastbox/events.py"], "bounded events"),
    ("evolution", ["Evolution Engine"], ["beastbox/organism.py"], "pattern counts"),
    ("autonomy", ["autonomous execution"], ["beastbox/autonomy", "beastbox/arms"], "bounded supervisor"),
    ("providers", ["model integrations"], ["beastbox/providers.py", "beastbox/ollama_models.py"], "replaceable inference"),
    ("model-router", ["model routing"], ["beastbox/model_router.py"], "host-approved routing"),
    ("heartbeat", ["heartbeat/maintenance"], ["beastbox/heartbeat.py"], "scheduled tasks"),
    ("cosmic-ui", ["visual control deck"], ["beastbox/cosmic_web.py", "beastbox/cosmic_ui.py"], "browser surface"),
]


def _try_import(mod: str) -> bool:
    try:
        importlib.import_module(f"beastbox.{mod}")
        return True
    except Exception:  # noqa: BLE001 -- probe importability
        return False


def recover_substrate_map(repo_root: str | Path = ".") -> dict:
    root = Path(repo_root)
    components: list[dict] = []
    for cid, names, paths, notes in _CATALOG:
        present = all((root / p).exists() for p in paths)
        importable = False
        executable = False
        # Map component to a probe import.
        probe = {
            "cosmos-substrate": "durable",
            "cosmos-runtime": "runtime",
            "cst": "attention",
            "dyn12": "dyn12",
            "dyn42": "state_family",
            "dyn54": "state_family",
            "rawrphos": "rawrphos_local",
            "phos": "models.phos_reference",
            "samgo": "training.lineage",
            "cosmic-cypher": "cypher",
            "cns7": "cns",
            "synapse": "synaptic",
            "r12": "refractive_memory",
            "hebbian": "memory",
            "monologue": "organism",
            "sensors": "events",
            "evolution": "organism",
            "autonomy": "autonomy.supervisor",
            "providers": "providers",
            "model-router": "model_router",
            "heartbeat": "heartbeat",
            "cosmic-ui": "cosmic_web",
        }.get(cid, "")
        if probe:
            importable = _try_import(probe)
        if importable and cid in {"dyn12", "cns7", "hebbian", "sensors", "synapse", "r12"}:
            try:
                if cid == "dyn12":
                    from beastbox.dyn12 import update_dyn12
                    update_dyn12([0.0] * 12, [0.1], step=1)
                elif cid == "cns7":
                    from beastbox.cns import CNS
                    CNS()
                elif cid == "hebbian":
                    from beastbox.memory import ReconciliationMemory
                    assert hasattr(ReconciliationMemory, "_hebbian_update")
                elif cid == "sensors":
                    from beastbox.events import normalize_event
                    normalize_event({"schema": "sensor-event-v1", "source": "text", "text": "probe"})
                elif cid == "synapse":
                    from beastbox.synaptic import SynapticField
                    SynapticField().step()
                elif cid == "r12":
                    from beastbox.refractive_memory import RefractiveMemoryRouter
                    assert hasattr(RefractiveMemoryRouter, "rank")
                executable = True
            except Exception:  # noqa: BLE001 -- smoke probe; any failure means not executable
                executable = False
        if not present:
            state = "MISSING"
        elif present and executable:
            state = "CONNECTED"
        elif present and importable:
            state = "DORMANT"
        else:
            state = "BROKEN"
        # Duplication note for known duplicated surfaces.
        if cid in {"cosmos-substrate", "cosmos-runtime"}:
            notes += "; durable+cosmos runtimes overlap by design (durable is canonical)"
        components.append(
            {
                "id": cid,
                "names": names,
                "paths": paths,
                "present": present,
                "importable": importable,
                "executable": executable,
                "state": state,
                "notes": notes,
            }
        )
    connected = sum(1 for c in components if c["state"] == "CONNECTED")
    return {
        "schema": "omega-recovery-map-v1",
        "connected": connected,
        "total": len(components),
        "components": components,
        "interpretation": (
            "CONNECTED means source present, importable, and a smoke call executed. "
            "DORMANT means present/importable but no smoke execution. "
            "Declared capabilities without executed capabilities are not counted as connected."
        ),
    }
