from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .bridge import BridgePacket
from .cns import CNS
from .config import RuntimeConfig
from .evidence import EvidenceLedger
from .heartbeat import Heartbeat
from .memory import ReconciliationMemory
from .organism import SlowState
from .providers import ReferenceTextProvider, TextProvider
from .quantum_heart import HeartMode, QuantumHeart
from .sensory import SensorySummary, freshness_gate
from .state import MissionState
from .synaptic import SynapticField


DEFAULT_SYSTEM_PROMPT = (
    "You are the local synthesis layer inside an owner-controlled research runtime. "
    "Treat state labels as software instrumentation, not claims of consciousness. "
    "Answer the user input directly."
)


class CosmosRuntime:
    """Small public closed-loop runtime joining the reconstructed subsystems.

    Backbone: perceive -> compress -> expand -> validate -> express -> store.
    A caller may supply a local conversation system prompt; this changes the
    synthesis voice, not host authority or the measured runtime state.
    """

    def __init__(self, config: RuntimeConfig | None = None, provider: TextProvider | None = None) -> None:
        self.config = config or RuntimeConfig()
        Path(self.config.data_dir).mkdir(parents=True, exist_ok=True)
        self.memory = ReconciliationMemory(self.config.memory_db)
        self.provider = provider or ReferenceTextProvider()
        self.cns = CNS()
        self.synaptic = SynapticField()
        try:
            mode = HeartMode(self.config.quantum_heart_mode)
        except ValueError:
            mode = HeartMode.OFF
        self.quantum_heart = QuantumHeart(mode=mode)
        self.slow = SlowState()
        self.heartbeat = Heartbeat()
        self.ledger = EvidenceLedger()
        self.turn = 0
        self.heartbeat.add("memory_consolidation", self.config.heartbeat_every_ticks, self._consolidate)
        self.heartbeat.add("system_health", self.config.heartbeat_every_ticks, self._health_tick)

    def _consolidate(self) -> None:
        made = self.memory.consolidate(min_group=3)
        self.ledger.append("memory_consolidation", {"derived_records": made})

    def _health_tick(self) -> None:
        self.ledger.append(
            "system_health",
            {
                "memory": self.memory.stats(),
                "cns_step": self.cns.step,
                "ledger_valid": self.ledger.verify(),
                "slow_experiences": self.slow.organism.experiences,
            },
        )

    def respond(
        self,
        text: str,
        *,
        sensory: SensorySummary | None = None,
        bridge: BridgePacket | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        self.turn += 1
        fresh = freshness_gate(sensory, max_age_seconds=self.config.sensory_max_age_seconds)
        memories = self.memory.search(text, limit=5)
        packet = bridge or BridgePacket()
        if fresh and fresh.source.startswith("audio") and not packet.audio_features:
            packet.audio_features = [float(v) for v in fresh.features.values() if isinstance(v, (int, float))]

        syn = self.synaptic.step(audio_features=packet.audio_features, quantum_spark=packet.quantum_spark)
        state = MissionState(
            mission_id=f"conversation-{self.turn}",
            objective=text,
            hypothesis="respond using current input, retrieved memory, and fresh bounded state",
            evidence=[m.text for m in memories],
            audio_features=list(packet.audio_features),
            quantum_spark=list(packet.quantum_spark),
            dyn12=list(syn["states"]["dyn12"]),
            provenance={"turn": self.turn, "bridge_hash": packet.safe_dict()["packet_sha256"]},
        )
        cns_state = self.cns.tick(state, packet.safe_dict())
        heart = self.quantum_heart.update(packet.quantum_spark, packet.audio_features)

        memory_block = "\n".join(f"- {m.text}" for m in memories) or "- none"
        synthesis_instructions = (system_prompt or DEFAULT_SYSTEM_PROMPT).strip()
        prompt = (
            f"{synthesis_instructions}\n"
            f"USER INPUT:\n{text}\n\nRETRIEVED MEMORY:\n{memory_block}\n\n"
            f"DYN12 SUMMARY: min={min(state.dyn12):.4f} max={max(state.dyn12):.4f}\n"
            f"QUANTUM HEART MODE: {heart['mode']}\n"
            "Answer the user input directly."
        )
        response = self.provider.generate(prompt)
        memory_id = self.memory.store(text, kind="user_turn", metadata={"turn": self.turn})
        response_id = self.memory.store(response, kind="assistant_turn", metadata={"turn": self.turn}, source_ids=[memory_id])
        self.slow.organism.observe(1.0)
        self.slow.evolution.learn("conversation_turn")
        self.slow.monologue.add(f"turn={self.turn}; evidence={len(memories)}; state={state.digest()[:12]}")
        ran = self.heartbeat.tick()
        self.ledger.append(
            "conversation_turn",
            {
                "turn": self.turn,
                "input_memory_id": memory_id,
                "response_memory_id": response_id,
                "state_hash": state.digest(),
                "fresh_sensory": bool(fresh),
                "cns": cns_state,
                "heartbeat_tasks": ran,
            },
        )
        return {
            "response": response,
            "state_hash": state.digest(),
            "memory_hits": [asdict(m) for m in memories],
            "cns": cns_state,
            "quantum_heart": heart,
            "ledger_head": self.ledger.head,
        }

    def save_evidence(self, path: str | Path) -> None:
        self.ledger.write_jsonl(path)

    def close(self) -> None:
        self.memory.close()
